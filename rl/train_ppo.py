#!/usr/bin/env python
"""Masked two-head PPO for kaggriculture. CPU-only by design (README §2).

    python rl/train_ppo.py --run m1 --n-envs 28 --max-minutes 50

Auto-curriculum: trains against STAGES[k], advancing when the rolling win rate
against the *current* stage crosses --advance-at (over the last --window
finished episodes). After advancing, 30% of episodes still sample earlier
stages so old opponents are not forgotten. Stage index persists in the
checkpoint; chained short Slurm jobs just keep going (--resume is the default).

Everything printed also lands in rl/runs/<run>/log.csv. Training numbers are
for steering only -- reported strength comes from tools/eval.py (README §9).
"""

import argparse
import csv
import os
import sys
import time
from collections import deque

import numpy as np
import torch

_RL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _RL)

from policy import Policy            # noqa: E402
from vec_env import VecEnv           # noqa: E402
import actions as A                  # noqa: E402
import obs as O                      # noqa: E402

# Curriculum. w49/w100 were stages 2-3 until a head-to-head probe showed even
# the weakest wrapped recording making $131k-162k against a non-flooding
# opponent -- an unreachable wall, not a rung. spar reconstructions (23-61k)
# and ledger_lena (73-80k) are the actual gradient toward the top of what this
# repo can field.
STAGES = [
    "starter",
    # Ghost first: a bare ladder replay earns 13-24k without flooding the
    # market, so the +-win bonus is an achievable gradient right after starter
    # (vs barnyard it is a constant -3 for millions of steps). The eval roster
    # holds out a second ghost the policy never trains against.
    os.path.join(_RL, "..", "agents", "ghosts", "ghost-89825016-0.py"),
    os.path.join(_RL, "..", "agents", "barnyard.py"),
    os.path.join(_RL, "..", "agents", "bench3", "ledger_lena.py"),
]


def stage_pool(idx):
    """Current stage 50%, earlier stages share 50%: a stage transition is a
    distribution cliff (barnyard floods the shared market), and a 70/30 mix
    measurably eroded mastered skills instead of building new ones."""
    if idx == 0:
        return [(STAGES[0], 1.0)]
    pool = [(STAGES[idx], 0.5)]
    w = 0.5 / idx
    for j in range(idx):
        pool.append((STAGES[j], w))
    return pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="m1")
    ap.add_argument("--n-envs", type=int, default=28)
    ap.add_argument("--rollout", type=int, default=240)
    ap.add_argument("--max-minutes", type=float, default=50)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--gamma", type=float, default=0.999)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--minibatches", type=int, default=8)
    ap.add_argument("--ent-coef", type=float, default=0.003)
    ap.add_argument("--vf-coef", type=float, default=0.5)
    ap.add_argument("--shape-w", type=float, default=1.0)
    ap.add_argument("--win-bonus", type=float, default=3.0)
    ap.add_argument("--advance-at", type=float, default=0.85)
    ap.add_argument("--freeze-policy-until", type=int, default=0,
                    help="global_step below which only the value head trains "
                         "(warm-up after a BC init)")
    ap.add_argument("--league", action="store_true",
                    help="population self-play (league.py) instead of the "
                         "stage curriculum")
    ap.add_argument("--league-dir", default=os.path.join(_RL, "league"))
    ap.add_argument("--opp-lambda", type=float, default=0.0,
                    help="competitive shaping: subtract this fraction of the "
                         "opponent's visible-worth delta from the reward")
    ap.add_argument("--window", type=int, default=200)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    run_dir = os.path.join(_RL, "runs", args.run)
    os.makedirs(run_dir, exist_ok=True)
    ckpt_path = os.path.join(run_dir, "latest.pt")
    best_path = os.path.join(run_dir, "best.pt")
    csv_path = os.path.join(run_dir, "log.csv")
    best_win = -1.0
    if os.path.exists(best_path):
        try:
            best_win = float(torch.load(best_path, map_location="cpu",
                                        weights_only=False).get("win", -1.0))
        except Exception:
            pass

    policy = Policy(O.OBS_DIM, A.N_FARMER, A.N_MARKET)
    optim = torch.optim.Adam(policy.parameters(), lr=args.lr, eps=1e-5)
    global_step, stage, it0 = 0, 0, 0
    if not args.no_resume and os.path.exists(ckpt_path):
        ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        missing, unexpected = policy.load_state_dict(ck["model"], strict=False)
        if missing or unexpected:
            print(f"arch drift on resume: missing {missing} unexpected {unexpected}",
                  flush=True)
        try:
            optim.load_state_dict(ck["optim"])
        except ValueError:
            print("optimiser state incompatible, starting it fresh", flush=True)
        global_step, stage, it0 = ck["global_step"], ck["stage"], ck["iter"] + 1
        print(f"resumed: step {global_step:,} stage {stage} iter {it0}", flush=True)

    league = None
    if args.league:
        from league import League
        league = League(args.league_dir)
        pool0 = league.pool()
    else:
        pool0 = stage_pool(stage)
    venv = VecEnv(args.n_envs, pool0, shape_w=args.shape_w,
                  win_bonus=args.win_bonus, base_rng_seed=global_step % 100_000,
                  opp_lambda=args.opp_lambda)
    obs, fm, mm = venv.initial_obs()

    N, T = args.n_envs, args.rollout
    b_obs = np.zeros((T, N, O.OBS_DIM), dtype=np.float32)
    b_fm = np.zeros((T, N, A.N_FARMER), dtype=bool)
    b_mm = np.zeros((T, N, A.N_MARKET), dtype=bool)
    b_fa = np.zeros((T, N), dtype=np.int64)
    b_ma = np.zeros((T, N), dtype=np.int64)
    b_logp = np.zeros((T, N), dtype=np.float32)
    b_val = np.zeros((T, N), dtype=np.float32)
    b_rew = np.zeros((T, N), dtype=np.float32)
    b_done = np.zeros((T, N), dtype=bool)

    recent = deque(maxlen=args.window)          # episodes vs current stage
    recent_all = deque(maxlen=args.window)      # every episode
    fp_ema = None                               # behavioural fingerprint (league)
    new_csv = not os.path.exists(csv_path)
    csv_f = open(csv_path, "a", newline="")
    csv_w = csv.writer(csv_f)
    if new_csv:
        csv_w.writerow(["iter", "step", "stage", "sps", "win", "money",
                        "opp_money", "eps", "pg", "vf", "ent"])

    t_start = time.time()
    it = it0
    while (time.time() - t_start) / 60 < args.max_minutes:
        t_iter = time.time()
        for t in range(T):
            xt = torch.from_numpy(obs)
            fa, ma, logp, val = policy.act(
                xt, torch.from_numpy(fm), torch.from_numpy(mm))
            b_obs[t], b_fm[t], b_mm[t] = obs, fm, mm
            b_fa[t], b_ma[t] = fa.numpy(), ma.numpy()
            b_logp[t], b_val[t] = logp.numpy(), val.numpy()
            obs, fm, mm, rew, done, eps = venv.step(b_fa[t], b_ma[t])
            b_rew[t], b_done[t] = rew, done
            for e in eps:
                recent_all.append(e)
                if league is not None:
                    league.record(e["opponent"], e["win"])
                    recent.append(e)
                    if e.get("fp") is not None:
                        fp_ema = (e["fp"] if fp_ema is None
                                  else 0.98 * fp_ema + 0.02 * e["fp"])
                elif e["opponent"] == STAGES[stage]:
                    recent.append(e)
        global_step += T * N

        with torch.no_grad():
            last_val = policy.act(torch.from_numpy(obs),
                                  torch.from_numpy(fm),
                                  torch.from_numpy(mm))[3].numpy()
        adv = np.zeros((T, N), dtype=np.float32)
        gae = np.zeros(N, dtype=np.float32)
        for t in reversed(range(T)):
            nonterm = ~b_done[t]
            nxt = last_val if t == T - 1 else b_val[t + 1]
            delta = b_rew[t] + args.gamma * nxt * nonterm - b_val[t]
            gae = delta + args.gamma * args.lam * gae * nonterm
            adv[t] = gae
        ret = adv + b_val

        f_obs = torch.from_numpy(b_obs.reshape(T * N, -1))
        f_fm = torch.from_numpy(b_fm.reshape(T * N, -1))
        f_mm = torch.from_numpy(b_mm.reshape(T * N, -1))
        f_fa = torch.from_numpy(b_fa.reshape(-1))
        f_ma = torch.from_numpy(b_ma.reshape(-1))
        f_logp = torch.from_numpy(b_logp.reshape(-1))
        f_adv = torch.from_numpy(adv.reshape(-1))
        f_ret = torch.from_numpy(ret.reshape(-1))
        f_adv = (f_adv - f_adv.mean()) / (f_adv.std() + 1e-8)

        pg_on = 0.0 if global_step < args.freeze_policy_until else 1.0
        idx = np.arange(T * N)
        pg_l = vf_l = ent_l = 0.0
        for _ in range(args.epochs):
            np.random.shuffle(idx)
            for mb in np.array_split(idx, args.minibatches):
                mb = torch.from_numpy(mb)
                logp, ent, val = policy.evaluate(
                    f_obs[mb], f_fm[mb], f_mm[mb], f_fa[mb], f_ma[mb])
                ratio = (logp - f_logp[mb]).exp()
                a = f_adv[mb]
                pg = -torch.min(
                    ratio * a,
                    ratio.clamp(1 - args.clip, 1 + args.clip) * a).mean()
                vf = 0.5 * (val - f_ret[mb]).pow(2).mean()
                loss = pg_on * (pg - args.ent_coef * ent.mean()) + args.vf_coef * vf
                optim.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
                optim.step()
                pg_l, vf_l, ent_l = pg.item(), vf.item(), ent.mean().item()

        sps = T * N / (time.time() - t_iter)
        win = np.mean([e["win"] for e in recent]) if recent else 0.0
        money = np.mean([e["money"] for e in recent_all]) if recent_all else 0.0
        omoney = np.mean([e["opp_money"] for e in recent_all]) if recent_all else 0.0
        print(f"it {it:>4}  step {global_step:>10,}  stage {stage}  "
              f"sps {sps:>6,.0f}  win {win:5.2f}  money {money:>9,.0f}  "
              f"opp {omoney:>9,.0f}  eps {len(recent)}  ent {ent_l:5.2f}", flush=True)
        csv_w.writerow([it, global_step, stage, round(sps), round(win, 3),
                        round(money), round(omoney), len(recent),
                        round(pg_l, 4), round(vf_l, 4), round(ent_l, 3)])
        csv_f.flush()

        # Peak checkpoint: training oscillates (rise, diffuse, re-climb), so
        # the deliverable is the best rolling-win policy at the ghost stage or
        # beyond, never whatever the chain happened to end on.
        if stage >= 1 and len(recent) >= 100 and win > best_win:
            best_win = win
            torch.save({"model": policy.state_dict(), "win": win,
                        "stage": stage, "global_step": global_step},
                       best_path + ".tmp")
            os.replace(best_path + ".tmp", best_path)
            print(f"    best.pt <- win {win:.2f} at step {global_step:,}", flush=True)

        if it % 5 == 0 or (time.time() - t_start) / 60 >= args.max_minutes - 2:
            torch.save({"model": policy.state_dict(), "optim": optim.state_dict(),
                        "global_step": global_step, "stage": stage, "iter": it},
                       ckpt_path + ".tmp")
            os.replace(ckpt_path + ".tmp", ckpt_path)

        if league is not None:
            promoted = league.maybe_promote(policy, global_step, fp_ema)
            if promoted:
                print(f"=== promoted into league: {promoted} ===", flush=True)
            if promoted or it % 10 == 0:
                league.refresh_mirror(policy)
                league._save()
                venv.set_pool(league.pool())
            if it % 25 == 0:
                print(league.summary(), flush=True)
        elif (len(recent) >= args.window // 2 and win >= args.advance_at
                and stage < len(STAGES) - 1):
            stage += 1
            recent.clear()
            venv.set_pool(stage_pool(stage))
            # Re-freeze across the cliff: returns change scale at a stage
            # switch, and letting the policy update against a value net that
            # has not seen the new distribution tears down what stage k built.
            args.freeze_policy_until = max(args.freeze_policy_until,
                                           global_step + 100_000)
            print(f"=== advancing to stage {stage}: {STAGES[stage]} "
                  f"(policy frozen until {args.freeze_policy_until:,}) ===",
                  flush=True)
        it += 1

    venv.close()
    csv_f.close()
    print(f"clean exit at {(time.time() - t_start) / 60:.1f} min, "
          f"step {global_step:,}", flush=True)


if __name__ == "__main__":
    main()
