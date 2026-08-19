"""PPO training loop with curriculum opponents and PGA seed scheduling.

Default (v2): multi-head per-unit policy, potential-based shaping, γ=0.997.

    python -m rl.train_ppo --arch multi \\
        --iters 200 --episodes 8 --workers 12 \\
        --opponents starter,agents/barnyard.py \\
        --switch-after 40 --mix-prev 0.3 --pga-frac 0.3 \\
        --gamma 0.997 --entropy 0.003 --lr 3e-4 \\
        --ckpt-dir rl/ckpt_official
"""

import argparse
import json
import os
import time

from concurrent.futures import ProcessPoolExecutor

import numpy as np

os.environ.setdefault("KG_FAST_ENV", "1")

from .env import KaggEnv, KaggEnvMulti, PlanMarketEnv  # noqa: E402
from .ppo import (  # noqa: E402
    MLP, MarketMLP, MultiHeadMLP,
    ppo_update, ppo_update_market, ppo_update_multihead,
)
from .rollout import run_episode_worker, worker_init  # noqa: E402


def _run_episode(env, mlp, arch="single", rng=None):
    obs_buf, act_buf, logp_buf = [], [], []
    rew_buf, val_buf, done_buf, nh_buf = [], [], [], []

    obs = env.reset()
    n_hands = int(getattr(env, "n_hands", 0) or 0)
    done = False
    total_r = 0.0
    steps = 0
    while not done and steps < 800:
        if arch == "multi":
            act, logp, val, _ = mlp.act(obs, n_hands=n_hands, sample=True, rng=rng)
        else:
            act, logp, val, _ = mlp.act(obs, sample=True, rng=rng)
        obs_buf.append(obs)
        act_buf.append(act)
        logp_buf.append(logp)
        val_buf.append(val)
        nh_buf.append(n_hands)
        obs, r, done, info = env.step(act)
        n_hands = int((info or {}).get("n_hands", n_hands) or 0)
        rew_buf.append(r)
        done_buf.append(done)
        total_r += r
        steps += 1
    if done:
        val_buf.append(0.0)
    elif arch == "multi":
        val_buf.append(float(mlp.act(obs, n_hands=n_hands, sample=False)[2]))
    else:
        val_buf.append(float(mlp.act(obs, sample=False)[2]))
    return obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf, nh_buf, total_r, steps


def _make_mlp(arch, seed):
    if arch == "market":
        return MarketMLP(seed=seed)
    if arch == "multi":
        return MultiHeadMLP(seed=seed)
    return MLP(seed=seed)


def _make_env(arch, opponent, seed, plan_turns=None):
    if arch == "market":
        return PlanMarketEnv(plan_turns=plan_turns, opponent=opponent, seed=seed)
    if arch == "multi":
        return KaggEnvMulti(opponent=opponent, seed=seed)
    return KaggEnv(opponent=opponent, seed=seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", choices=["single", "multi", "market"], default="multi")
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--opponents", default="starter,agents/barnyard.py",
                    help="comma-separated curriculum; stay on barnyard until it is beaten")
    ap.add_argument("--switch-after", type=int, default=40,
                    help="advance opponent tier every N iters (iter 1-N vs first opponent)")
    ap.add_argument("--mix-prev", type=float, default=0.3,
                    help="after switching, this fraction of episodes still vs the previous opponent")
    ap.add_argument("--pga-frac", type=float, default=0.3, help="first this fraction of iters use fixed seed set")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--gamma", type=float, default=0.997)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=512)
    ap.add_argument("--entropy", type=float, default=0.003)
    ap.add_argument("--value-coef", type=float, default=0.5)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--init-weights", default="rl/ckpt_official/ppo_it0300.npz")
    ap.add_argument("--ckpt-dir", default="rl/ckpt_official")
    ap.add_argument("--save-every", type=int, default=5)
    ap.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 2),
                    help="parallel rollout workers")
    ap.add_argument("--market-only", action="store_true",
                    help="(deprecated) same as --arch market")
    ap.add_argument("--plan", default=None,
                    help="path to plan turns JSON for --arch market")
    args = ap.parse_args()

    if args.market_only:
        args.arch = "market"

    opponents = [o.strip() for o in args.opponents.split(",") if o.strip()]
    if not opponents:
        opponents = ["starter"]

    os.makedirs(args.ckpt_dir, exist_ok=True)

    plan_turns = None
    if args.arch == "market":
        if not args.plan:
            raise SystemExit("--arch market requires --plan (path to plan turns JSON)")
        with open(args.plan, "r", encoding="utf-8") as f:
            plan_turns = json.load(f)

    mlp = _make_mlp(args.arch, args.seed)
    init_weights = args.init_weights
    if args.arch == "market":
        init_weights = init_weights.replace("weights_bc.npz", "weights_bc_market.npz")
    if init_weights and init_weights.lower() not in ("none", "null", "-") and os.path.exists(init_weights):
        try:
            mlp.load(init_weights, allow_partial=True)
            print(f"loaded init weights from {init_weights} (partial ok for trunk)")
        except TypeError:
            try:
                mlp.load(init_weights)
                print(f"loaded init weights from {init_weights}")
            except Exception as e:
                print(f"init weights load failed: {e}")
        except Exception as e:
            print(f"init weights load failed: {e}")

    rng = np.random.default_rng(args.seed)
    fixed_seeds = [7, 13, 42, 99, 256, 512, 1024]
    n_workers = min(args.episodes, args.workers)
    pool = None
    if n_workers > 1:
        pool = ProcessPoolExecutor(max_workers=n_workers, initializer=worker_init)

    start_time = time.time()
    try:
        for it in range(1, args.iters + 1):
            tier = min((it - 1) // max(args.switch_after, 1), len(opponents) - 1)
            opp = opponents[tier]
            use_fixed = it <= int(args.iters * args.pga_frac)
            batch_obs, batch_act, batch_logp = [], [], []
            batch_rew, batch_val, batch_done, batch_nh = [], [], [], []
            ep_lengths, ep_rewards, ep_steps = [], [], []
            t0 = time.time()

            weights_dict = {k: v for k, v in mlp.params.items()}

            def _episode_opp(ep_i):
                if tier > 0 and args.mix_prev > 0 and (ep_i / max(args.episodes, 1)) < args.mix_prev:
                    return opponents[tier - 1]
                return opp

            if pool is None:
                for ep in range(args.episodes):
                    seed = fixed_seeds[ep % len(fixed_seeds)] if use_fixed else int(rng.integers(0, 1 << 30))
                    ep_opp = _episode_opp(ep)
                    try:
                        env = _make_env(args.arch, ep_opp, seed, plan_turns)
                    except Exception as e:
                        print(f"  env make failed seed={seed} opp={ep_opp}: {e}")
                        continue
                    ep_rng = np.random.default_rng(seed + 17)
                    result = _run_episode(env, mlp, arch=args.arch, rng=ep_rng)
                    try:
                        env.close()
                    except Exception:
                        pass
                    obs_b, act_b, logp_b, rew_b, val_b, done_b, nh_b, total_r, steps = result
                    if not obs_b:
                        continue
                    batch_obs.extend(obs_b)
                    batch_act.extend(act_b)
                    batch_logp.extend(logp_b)
                    batch_rew.extend(rew_b)
                    batch_val.extend(val_b)
                    batch_done.extend(done_b)
                    batch_nh.extend(nh_b)
                    ep_lengths.append(len(rew_b))
                    ep_rewards.append(total_r)
                    ep_steps.append(steps)
            else:
                futures = []
                for ep in range(args.episodes):
                    seed = fixed_seeds[ep % len(fixed_seeds)] if use_fixed else int(rng.integers(0, 1 << 30))
                    ep_opp = _episode_opp(ep)
                    futures.append(pool.submit(
                        run_episode_worker,
                        (ep_opp, seed, weights_dict, args.arch, plan_turns),
                    ))
                for future in futures:
                    try:
                        result = future.result(timeout=180)
                    except Exception as e:
                        print(f"  episode worker failed: {e}")
                        continue
                    if result is None:
                        continue
                    obs_b, act_b, logp_b, rew_b, val_b, done_b, nh_b, total_r, steps = result
                    if not obs_b:
                        continue
                    batch_obs.extend(obs_b)
                    batch_act.extend(act_b)
                    batch_logp.extend(logp_b)
                    batch_rew.extend(rew_b)
                    batch_val.extend(val_b)
                    batch_done.extend(done_b)
                    batch_nh.extend(nh_b)
                    ep_lengths.append(len(rew_b))
                    ep_rewards.append(total_r)
                    ep_steps.append(steps)

            if not batch_obs:
                print(f"iter {it}/{args.iters}  no episodes collected")
                continue

            update_kw = dict(
                episode_lengths=ep_lengths,
                gamma=args.gamma, lam=args.lam, clip=args.clip, epochs=args.epochs,
                minibatch=args.minibatch, lr=args.lr, entropy_coef=args.entropy,
                value_coef=args.value_coef, max_grad_norm=args.max_grad_norm,
            )
            if args.arch == "market":
                stats = ppo_update_market(
                    mlp, batch_obs, batch_act, batch_logp, batch_rew, batch_val, batch_done,
                    **update_kw,
                )
            elif args.arch == "multi":
                stats = ppo_update_multihead(
                    mlp, batch_obs, batch_act, batch_logp, batch_rew, batch_val, batch_done,
                    n_hands_buf=batch_nh, **update_kw,
                )
            else:
                stats = ppo_update(
                    mlp, batch_obs, batch_act, batch_logp, batch_rew, batch_val, batch_done,
                    **update_kw,
                )
            elapsed = time.time() - t0
            print(f"iter {it:4d}/{args.iters}  arch={args.arch}  opp={opp}  mix_prev={args.mix_prev if tier else 0:.2f}  fixed={int(use_fixed)}  "
                  f"ep_reward={np.mean(ep_rewards):.3f}  steps={np.mean(ep_steps):.1f}  "
                  f"pol={stats['policy_loss']:.4f} val={stats['value_loss']:.4f} ent={stats['entropy']:.4f}  "
                  f"time={elapsed:.1f}s")
            if it % args.save_every == 0 or it == args.iters:
                path = os.path.join(args.ckpt_dir, f"ppo_it{it:04d}.npz")
                mlp.save(path)
                print(f"  saved {path}  total_time={time.time()-start_time:.1f}s")
    finally:
        if pool is not None:
            pool.shutdown(wait=True)


if __name__ == "__main__":
    main()
