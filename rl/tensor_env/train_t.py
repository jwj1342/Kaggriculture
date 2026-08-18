#!/usr/bin/env python
"""B4c: the on-device training loop -- collect + PPO on one device.

    python rl/tensor_env/train_t.py --device cuda --B 2048 --iters 200
    python rl/tensor_env/train_t.py --device cpu  --B 128  --iters 12   # gate size

One iteration = one batch of B full episodes (720 turns, lockstep) against
the tensor starter, then a PPO update over the (T, B) on-device buffers.
Per turn, everything is tensor work on ep.device: features_t.encode_t /
masks_t for the learner seat, the actor forward + masked sampling
(policy_t.PolicyT.act), opponents_t.starter_indices for the starter seat,
engine_t_idx.step_idx with the (learner, starter) index pairs, and
potential_t.net_worth_t for the shaped reward. Host round trips per turn are
the ones the consumed modules already make (step_idx's small presence
tables and lockstep-termination bools, encode_t's documented log1p slots);
this file adds none of its own inside the turn loop.

Reward (rl-baseline vec_env semantics, computed on device):
    r_t = (net_worth_t(s_{t+1}) - net_worth_t(s_t)) / 3000
        + [terminal] win_bonus * (+1 win / -1 loss / 0 tie), by final money.
PPO (rl-baseline train_ppo coefficients): GAE gamma 0.999 lambda 0.95 with a
zero terminal bootstrap (episodes are complete and fixed-length), advantage
normalisation, clip 0.2, value MSE * 0.5, entropy 0.003, Adam (lr flag),
grad-norm clip 0.5, --epochs x --minibatches minibatches per iteration.

Logged per iteration: sps (learner lane-steps per second, end to end:
collection + update), win rate vs the starter, mean learner money, mean
starter money, PPO losses / entropy. `train(args)` returns the per-iteration
records so test_b4c.py can assert on the learning curve.

Buffer note: the observation buffer is (T, B, 4867) float32 = 1.79 GB at
B=128 and 14 MB per lane in general; --obs-half stores it as float16 (the
actor still sees float32 at collection time; only the PPO replay reads the
rounded copy) for large-B GPU runs.
"""

import argparse
import csv
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch

import actions as A
import obs as O
import engine_t
import engine_t_idx  # noqa: F401  (attaches EpisodeT.step_idx)
import features_t
import opponents_t
import potential_t
from policy_t import PolicyT


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--B", type=int, default=128, help="episodes per iteration")
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--hidden", type=int, nargs=2, default=[512, 256],
                    metavar=("H1", "H2"), help="actor trunk widths")
    ap.add_argument("--v-hidden", type=int, default=256, help="critic width")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0,
                    help="policy init + sampling seed; episode seeds derive from it")
    ap.add_argument("--gamma", type=float, default=0.999)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--minibatches", type=int, default=8)
    ap.add_argument("--ent-coef", type=float, default=0.003)
    ap.add_argument("--vf-coef", type=float, default=0.5)
    ap.add_argument("--win-bonus", type=float, default=3.0)
    ap.add_argument("--seat", choices=("0", "1", "alt"), default="0",
                    help="learner seat: fixed 0 / 1, or alternating per iteration")
    ap.add_argument("--steps", type=int, default=720, help="episode length")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = leave)")
    ap.add_argument("--max-minutes", type=float, default=0.0,
                    help="stop after this wall time (0 = only --iters)")
    ap.add_argument("--obs-half", action="store_true",
                    help="store the replay observation buffer as float16")
    ap.add_argument("--log", default="", help="CSV of per-iteration records")
    ap.add_argument("--save", default="", help="checkpoint path (state_dict) after each iteration")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--verbose", action="store_true",
                    help="also log top-5 farmer / market action frequencies")
    return ap


# ---------------------------------------------------------------------------
# collection: one batch of B complete episodes, learner vs tensor starter
# ---------------------------------------------------------------------------

class Rollout:
    """On-device (T, B, ...) buffers for one iteration."""

    def __init__(self, T, B, device, obs_dtype):
        self.obs = torch.empty((T, B, O.OBS_DIM), dtype=obs_dtype, device=device)
        self.fm = torch.empty((T, B, A.N_FARMER), dtype=torch.bool, device=device)
        self.mm = torch.empty((T, B, A.N_MARKET), dtype=torch.bool, device=device)
        self.fa = torch.empty((T, B), dtype=torch.int64, device=device)
        self.ma = torch.empty((T, B), dtype=torch.int64, device=device)
        self.logp = torch.empty((T, B), dtype=torch.float32, device=device)
        self.val = torch.empty((T, B), dtype=torch.float32, device=device)
        self.rew = torch.empty((T, B), dtype=torch.float32, device=device)
        self.T = 0


def collect(policy, seeds, seat, args, gen, roll):
    """Play B episodes; fill roll (T actual steps). Returns per-lane final
    (learner money, starter money) float64 tensors."""
    dev = torch.device(args.device)
    ep = engine_t.EpisodeT(seeds, episode_steps=args.steps, device=args.device)
    B = ep.B
    opp = 1 - seat
    prev_w = potential_t.net_worth_t(ep, seat)
    scale = 1.0 / 3000.0
    t = 0
    while not ep.done:
        x = features_t.encode_t(ep, seat)
        fm, mm = features_t.masks_t(ep, seat)
        fa, ma, logp = policy.act(x, fm, mm, generator=gen)
        with torch.no_grad():
            v = policy.value(x)
        ofa, oma = opponents_t.starter_indices(ep, opp)
        if seat == 0:
            f_idx = torch.stack([fa, ofa], 1)
            m_idx = torch.stack([ma, oma], 1)
        else:
            f_idx = torch.stack([ofa, fa], 1)
            m_idx = torch.stack([oma, ma], 1)
        ep.step_idx(f_idx, m_idx)
        w = potential_t.net_worth_t(ep, seat)
        r = (w - prev_w) * scale
        prev_w = w
        if ep.done:
            mine, theirs = ep.money[:, seat], ep.money[:, opp]
            win = (mine > theirs).to(torch.float64) - (mine < theirs).to(torch.float64)
            r = r + args.win_bonus * win
        roll.obs[t].copy_(x)
        roll.fm[t].copy_(fm)
        roll.mm[t].copy_(mm)
        roll.fa[t].copy_(fa)
        roll.ma[t].copy_(ma)
        roll.logp[t].copy_(logp)
        roll.val[t].copy_(v)
        roll.rew[t].copy_(r)
        t += 1
    roll.T = t
    return ep.money[:, seat].clone(), ep.money[:, opp].clone()


def action_freq(roll, k=5):
    """Top-k farmer / market action frequencies over the rollout (diagnostic)."""
    T = roll.T
    out = []
    for buf, names in ((roll.fa, A.FARMER_ACTIONS), (roll.ma, A.MARKET_ACTIONS)):
        cnt = torch.bincount(buf[:T].reshape(-1), minlength=len(names)).float()
        cnt = cnt / cnt.sum()
        top = torch.topk(cnt, k)
        out.append(" ".join(f"{names[i]}:{cnt[i]:.2f}" for i in top.indices.tolist()))
    return out


# ---------------------------------------------------------------------------
# PPO update
# ---------------------------------------------------------------------------

def gae(rew, val, gamma, lam):
    """(T, B) rewards / values -> (advantages, returns); terminal bootstrap 0."""
    T = rew.shape[0]
    adv = torch.zeros_like(rew)
    last = torch.zeros_like(rew[0])
    for t in range(T - 1, -1, -1):
        nxt = val[t + 1] if t < T - 1 else torch.zeros_like(last)
        delta = rew[t] + gamma * nxt - val[t]
        last = delta + gamma * lam * last
        adv[t] = last
    return adv, adv + val


def ppo_update(policy, optim, roll, args, gen):
    T, B = roll.T, roll.obs.shape[1]
    n = T * B
    rew, val = roll.rew[:T], roll.val[:T]
    adv, ret = gae(rew, val, args.gamma, args.lam)
    f_adv = adv.reshape(n)
    f_adv = (f_adv - f_adv.mean()) / (f_adv.std() + 1e-8)
    f_ret = ret.reshape(n)
    f_obs = roll.obs[:T].reshape(n, -1)
    f_fm = roll.fm[:T].reshape(n, -1)
    f_mm = roll.mm[:T].reshape(n, -1)
    f_fa = roll.fa[:T].reshape(n)
    f_ma = roll.ma[:T].reshape(n)
    f_logp = roll.logp[:T].reshape(n)

    pg_l = vf_l = ent_l = 0.0
    kl_l = clipfrac = 0.0
    n_mb = 0
    for _ in range(args.epochs):
        perm = torch.randperm(n, generator=gen, device=f_adv.device)
        for mb in perm.chunk(args.minibatches):
            x = f_obs[mb]
            if x.dtype != torch.float32:
                x = x.float()
            logp, ent = policy.evaluate(x, f_fm[mb], f_mm[mb], f_fa[mb], f_ma[mb])
            v = policy.value(x)
            ratio = (logp - f_logp[mb]).exp()
            a = f_adv[mb]
            pg = -torch.min(ratio * a,
                            ratio.clamp(1 - args.clip, 1 + args.clip) * a).mean()
            vf = 0.5 * (v - f_ret[mb]).pow(2).mean()
            entm = ent.mean()
            loss = pg - args.ent_coef * entm + args.vf_coef * vf
            optim.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            optim.step()
            with torch.no_grad():
                pg_l += pg.item()
                vf_l += vf.item()
                ent_l += entm.item()
                kl_l += (f_logp[mb] - logp).mean().item()
                clipfrac += ((ratio - 1.0).abs() > args.clip).float().mean().item()
            n_mb += 1
    n_mb = max(1, n_mb)
    return {"pg": pg_l / n_mb, "vf": vf_l / n_mb, "ent": ent_l / n_mb,
            "kl": kl_l / n_mb, "clipfrac": clipfrac / n_mb}


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def train(args, log_fn=None):
    if log_fn is None:
        log_fn = lambda s: print(s, flush=True)
    if args.threads > 0:
        torch.set_num_threads(args.threads)
    dev = torch.device(args.device)
    torch.manual_seed(args.seed)
    gen = torch.Generator(device=dev).manual_seed(args.seed + 1)
    policy = PolicyT(O.OBS_DIM, A.N_FARMER, A.N_MARKET,
                     hidden1=args.hidden[0], hidden2=args.hidden[1],
                     v_hidden=args.v_hidden).to(dev)
    optim = torch.optim.Adam(policy.parameters(), lr=args.lr, eps=1e-5)
    T_max = args.steps
    roll = Rollout(T_max, args.B, dev,
                   torch.float16 if args.obs_half else torch.float32)
    records = []
    writer = None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        fh = open(args.log, "w", newline="")
        writer = csv.writer(fh)
        writer.writerow(["iter", "steps", "sps", "win", "money", "opp_money",
                         "pg", "vf", "ent", "kl", "clipfrac", "sec"])
    t_start = time.time()
    total_steps = 0
    for it in range(args.iters):
        if args.max_minutes > 0 and (time.time() - t_start) / 60.0 >= args.max_minutes:
            break
        t0 = time.time()
        seat = {"0": 0, "1": 1, "alt": it % 2}[args.seat]
        seeds = [args.seed * 1_000_003 + it * args.B + i for i in range(args.B)]
        money, omoney = collect(policy, seeds, seat, args, gen, roll)
        t_col = time.time() - t0
        freq_f, freq_m = action_freq(roll)
        stats = ppo_update(policy, optim, roll, args, gen)
        if dev.type == "cuda":
            torch.cuda.synchronize()
        sec = time.time() - t0
        n_steps = roll.T * args.B
        total_steps += n_steps
        win = ((money > omoney).float().mean() + 0.5 * (money == omoney).float().mean()).item()
        rec = {"iter": it, "steps": total_steps, "n_steps": n_steps, "sps": n_steps / sec,
               "win": win, "money": money.mean().item(),
               "opp_money": omoney.mean().item(), "sec": sec, "t_collect": t_col,
               **stats}
        records.append(rec)
        log_fn(f"it {it:3d}  steps {total_steps:>9,}  sps {rec['sps']:>8,.0f}  "
               f"win {win:5.3f}  money {rec['money']:>9,.0f}  opp {rec['opp_money']:>8,.0f}  "
               f"pg {stats['pg']:+.4f}  vf {stats['vf']:.4f}  ent {stats['ent']:.3f}  "
               f"kl {stats['kl']:.4f}  {sec:5.1f}s (collect {t_col:4.1f}s)")
        if args.verbose:
            log_fn(f"      farmer {freq_f}\n      market {freq_m}")
        if writer:
            writer.writerow([it, total_steps, round(rec["sps"]), round(win, 4),
                             round(rec["money"]), round(rec["opp_money"]),
                             round(stats["pg"], 5), round(stats["vf"], 5),
                             round(stats["ent"], 4), round(stats["kl"], 5),
                             round(stats["clipfrac"], 4), round(sec, 2)])
            fh.flush()
        if args.save:
            torch.save({"state_dict": policy.state_dict(), "args": vars(args),
                        "iter": it, "records": records}, args.save)
    if writer:
        fh.close()
    return policy, records


def main(argv=None):
    args = build_parser().parse_args(argv)
    _, records = train(args, log_fn=(lambda *a, **k: None) if args.quiet else None)
    if records:
        r = records[-1]
        print(f"done: {len(records)} iters, {r['steps']:,} learner lane-steps, "
              f"final win {r['win']:.3f}, mean sps {sum(x['sps'] for x in records)/len(records):,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
