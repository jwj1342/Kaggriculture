#!/usr/bin/env python
"""The unified TorchRL trainer: one entrypoint for the CPU and GPU lines.

    python rl/train.py --device cuda --B 1024 --iters 60          # A/B size
    python rl/train.py --device cpu  --B 128  --iters 12          # gate size
    python rl/train.py --algo a2c ...                             # swap loss

Supersedes rl/train_ppo.py (CPU, hand-written PPO over episode_pool) and
rl/tensor_env/train_t.py (GPU, hand-written PPO over EpisodeT): collection
is a TorchRL SyncDataCollector over trl_env.KGTensorEnv (EpisodeT is
device-agnostic, so --device is the whole CPU/GPU switch), advantages come
from torchrl.objectives.value.GAE, and the update is a swappable loss module
(--algo ppo -> ClipPPOLoss, --algo a2c -> A2CLoss). Adding an algorithm is
adding an entry to _LOSSES, not writing an update loop.

Coefficients are train_t.py's (which are rl-baseline train_ppo.py's): GAE
gamma 0.999 lambda 0.95 with zero terminal bootstrap (fixed-length episodes,
lockstep termination), whole-batch advantage normalisation, clip 0.2,
entropy 0.003, Adam(lr, eps=1e-5), grad-norm clip 0.5. The hand loops used
vf_coef * 0.5 * MSE; torchrl's "l2" distance is a plain squared error, so
the module gets critic_coeff = 0.5 * vf_coef for the same effective weight.

Checkpoints save {"model": <PolicyT-compatible state_dict>, "hidden", ...}:
rl/export_agent.py consumes them unchanged (actor submodule names match
rl/policy.py's Policy), which is the bridge into slurm/rl_eval.sh's
export -> roster h2h -> eval_summary pipeline.
"""

import argparse
import csv
import inspect
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_TENSOR = os.path.join(_HERE, "tensor_env")
for _p in (_TENSOR, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch

import actions as A
import obs as O
from trl_env import KGTensorEnv
from trl_policy import build_actor_critic, merged_state_dict

try:  # torchrl >= 0.12 name; SyncDataCollector is deprecated for removal in 0.13
    from torchrl.collectors import Collector as SyncDataCollector
except ImportError:
    from torchrl.collectors import SyncDataCollector
from torchrl.data import LazyTensorStorage, ReplayBuffer
from torchrl.data.replay_buffers.samplers import SamplerWithoutReplacement
from torchrl.objectives import A2CLoss, ClipPPOLoss
from torchrl.objectives.value import GAE

_LOSSES = {"ppo": ClipPPOLoss, "a2c": A2CLoss}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--algo", choices=sorted(_LOSSES), default="ppo")
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
                    help="learner seat: fixed 0 / 1, or alternating per episode batch")
    ap.add_argument("--opponent", default="starter",
                    help='"starter", or a checkpoint .pt / weights .npz played greedily')
    ap.add_argument("--steps", type=int, default=720, help="episode length")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = leave)")
    ap.add_argument("--max-minutes", type=float, default=0.0,
                    help="stop after this wall time (0 = only --iters)")
    ap.add_argument("--log", default="", help="CSV of per-iteration records")
    ap.add_argument("--save", default="", help="checkpoint path after each iteration")
    ap.add_argument("--quiet", action="store_true")
    return ap


def _filtered(cls, **kw):
    """Instantiate cls with only the kwargs its signature accepts (absorbs
    torchrl arg renames such as critic_coef -> critic_coeff across versions)."""
    sig = inspect.signature(cls.__init__).parameters
    return cls(**{k: v for k, v in kw.items() if k in sig})


def make_loss(algo, actor, critic, args):
    common = dict(
        actor_network=actor, critic_network=critic,
        entropy_bonus=True,
        entropy_coeff=args.ent_coef, entropy_coef=args.ent_coef,
        # hand loops: vf_coef * 0.5 * (v - ret)^2; torchrl l2 has no 0.5
        critic_coeff=0.5 * args.vf_coef, critic_coef=0.5 * args.vf_coef,
        loss_critic_type="l2",
        normalize_advantage=False,  # normalised whole-batch below, hand-loop style
    )
    if algo == "ppo":
        loss = _filtered(ClipPPOLoss, clip_epsilon=args.clip, **common)
    else:
        loss = _filtered(_LOSSES[algo], **common)
    loss.set_keys(action="action", sample_log_prob="sample_log_prob",
                  advantage="advantage", value_target="value_target",
                  value="state_value")
    return loss


def train(args, log_fn=None):
    if log_fn is None:
        log_fn = lambda s: print(s, flush=True)
    if args.threads > 0:
        torch.set_num_threads(args.threads)
    dev = torch.device(args.device)
    torch.manual_seed(args.seed)

    env = KGTensorEnv(
        args.B, device=dev,
        seat=0 if args.seat == "alt" else int(args.seat),
        alternate_seat=args.seat == "alt",
        episode_steps=args.steps, base_seed=args.seed,
        opponent=args.opponent, win_bonus=args.win_bonus)
    actor, critic, actor_net, critic_net = build_actor_critic(
        O.OBS_DIM, A.N_FARMER, A.N_MARKET,
        hidden1=args.hidden[0], hidden2=args.hidden[1],
        v_hidden=args.v_hidden, device=dev)
    adv_mod = GAE(gamma=args.gamma, lmbda=args.lam, value_network=critic,
                  average_gae=False)
    loss_mod = make_loss(args.algo, actor, critic, args).to(dev)
    optim = torch.optim.Adam(loss_mod.parameters(), lr=args.lr, eps=1e-5)

    # the engine flags done while executing action index episode_steps - 2
    # (kaggle DONE semantics), so a complete episode is episode_steps - 1
    # actions and one collector batch == one batch of complete episodes
    # (asserted bit-exactly in rl/tensor_env/test_trl.py gate (ii))
    ep_len = args.steps - 1
    frames = args.B * ep_len
    collector = SyncDataCollector(
        env, actor, frames_per_batch=frames,
        total_frames=frames * args.iters, device=dev)
    rb = ReplayBuffer(storage=LazyTensorStorage(frames, device=dev),
                      sampler=SamplerWithoutReplacement(),
                      batch_size=frames // args.minibatches)

    records = []
    writer = fh = None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        fh = open(args.log, "w", newline="")
        writer = csv.writer(fh)
        writer.writerow(["iter", "steps", "sps", "win", "money", "opp_money",
                         "pg", "vf", "ent", "sec"])
    t_start = time.time()
    total_steps = 0
    for it, td in enumerate(collector):
        t0 = time.time()
        t_col = t0 - (records[-1]["_t_end"] if records else t_start)
        with torch.no_grad():
            adv_mod(td)
        adv = td["advantage"]
        td["advantage"] = (adv - adv.mean()) / (adv.std() + 1e-8)

        # only what the loss reads: dropping next.observation / logits halves
        # the replay copy (at B=1024 the full batch is ~29 GB of float32 obs)
        flat = td.reshape(-1).select(
            "observation", "farmer_mask", "market_mask", "action",
            "sample_log_prob", "advantage", "value_target")
        stats = {"pg": 0.0, "vf": 0.0, "ent": 0.0}
        n_mb = 0
        for _ in range(args.epochs):
            rb.empty()
            rb.extend(flat)
            for _ in range(args.minibatches):
                mb = rb.sample()
                loss_td = loss_mod(mb)
                loss = sum(v for k, v in loss_td.items() if k.startswith("loss_"))
                optim.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(loss_mod.parameters(), 0.5)
                optim.step()
                with torch.no_grad():
                    stats["pg"] += loss_td["loss_objective"].item()
                    stats["vf"] += loss_td["loss_critic"].item()
                    stats["ent"] += -loss_td.get(
                        "loss_entropy", torch.zeros(())).item() / max(args.ent_coef, 1e-12)
                n_mb += 1
        for k in stats:
            stats[k] /= max(1, n_mb)

        if dev.type == "cuda":
            torch.cuda.synchronize()
        t_end = time.time()
        money = td["next", "money"][:, -1]
        omoney = td["next", "opp_money"][:, -1]
        win = ((money > omoney).float().mean()
               + 0.5 * (money == omoney).float().mean()).item()
        n_steps = td.numel()
        total_steps += n_steps
        sec = t_end - (records[-1]["_t_end"] if records else t_start)
        rec = {"iter": it, "steps": total_steps, "n_steps": n_steps,
               "sps": n_steps / sec, "win": win,
               "money": money.mean().item(), "opp_money": omoney.mean().item(),
               "sec": sec, "t_collect": t_col, "_t_end": t_end, **stats}
        records.append(rec)
        log_fn(f"it {it:3d}  steps {total_steps:>9,}  sps {rec['sps']:>8,.0f}  "
               f"win {win:5.3f}  money {rec['money']:>9,.0f}  opp {rec['opp_money']:>8,.0f}  "
               f"pg {stats['pg']:+.4f}  vf {stats['vf']:.4f}  ent {stats['ent']:.3f}  "
               f"{sec:5.1f}s (collect {t_col:4.1f}s)")
        if writer:
            writer.writerow([it, total_steps, round(rec["sps"]), round(win, 4),
                             round(rec["money"]), round(rec["opp_money"]),
                             round(stats["pg"], 5), round(stats["vf"], 5),
                             round(stats["ent"], 4), round(sec, 2)])
            fh.flush()
        if args.save:
            torch.save({"model": merged_state_dict(actor_net, critic_net),
                        "hidden": list(args.hidden), "v_hidden": args.v_hidden,
                        "algo": args.algo, "args": vars(args), "iter": it,
                        "records": [{k: v for k, v in r.items() if k != "_t_end"}
                                    for r in records]},
                       args.save)
        if args.max_minutes > 0 and (t_end - t_start) / 60.0 >= args.max_minutes:
            break
    collector.shutdown()
    if fh:
        fh.close()
    return (actor_net, critic_net), records


def main(argv=None):
    args = build_parser().parse_args(argv)
    _, records = train(args, log_fn=(lambda *a, **k: None) if args.quiet else None)
    if records:
        r = records[-1]
        print(f"done: {len(records)} iters, {r['steps']:,} learner lane-steps, "
              f"final win {r['win']:.3f}, mean sps "
              f"{sum(x['sps'] for x in records)/len(records):,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
