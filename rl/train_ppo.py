"""On-policy training loop with curriculum opponents and PGA seed scheduling.

Default update is PPO. ``--algo a2c`` / ``--algo reinforce`` keep the same
collector, GAE (or Monte-Carlo for reinforce), and multi-head action space;
only the policy surrogate changes. Non-PPO algos default to 1 epoch and
all-sample collect (clip cannot hide the greedy-frac mixture).

Default closed-loop ladder: barnyard -> enhanced. Promotion is greedy-probe
win rate (exam-like), not the sampled train win= which stays near 0 under
high entropy. After promoting, --mix-prev keeps a slice vs barnyard so the
exam opponent does not vanish. Do not put starter on this list: that hill
does not transfer (official 300-iter +56 vs starter, then never recovered).

Barnyard-only (no promotion):

    python -m rl.train_ppo --arch multi \\
        --opponents agents/barnyard.py --advance-at 0 --mix-prev 0 \\
        --init-weights rl/ckpt_official/ppo_it0300.npz \\
        --ckpt-dir rl/ckpt_herd --iters 200 --episodes 8 --workers 12

A2C smoke (same env, unclipped GAE policy gradient):

    python -m rl.train_ppo --algo a2c --arch multi \\
        --opponents agents/barnyard.py --advance-at 0 --mix-prev 0 \\
        --ckpt-dir rl/ckpt_a2c --iters 50 --episodes 8 --workers 12

Spatial trunks (CNN / Transformer over the 10×10 farm) keep the same
multi-head action space. They cannot load the 75→256 MLP npz:

    python -m rl.train_ppo --arch multi --net transformer \\
        --init-weights rl/ckpt_transformer_100/ppo_it0070.pt \\
        --ckpt-dir rl/ckpt_transformer_curr --iters 200

A2C + Transformer (from scratch; 1 epoch, all-sample collect). Do not
reuse ``rl/ckpt_a2c`` — that directory is the MLP A2C run:

    python -m rl.train_ppo --algo a2c --arch multi --net transformer \\
        --opponents agents/barnyard.py --advance-at 0 --mix-prev 0 \\
        --init-weights none --ckpt-dir rl/ckpt_a2c_transformer \\
        --iters 40 --episodes 8 --workers 4 --probe-every 10


Collect is half argmax (`--greedy-frac 0.5`) with entropy annealed
0.003 -> 0.0005 so the on-policy data is closer to the greedy exam.
`--greedy-frac 0 --entropy-end 0.003` restores the old all-sample collect.
"""

import argparse
import csv
import json
import os
import sys
import time

from concurrent.futures import ProcessPoolExecutor

import numpy as np

os.environ.setdefault("KG_FAST_ENV", "1")

from .env import KaggEnv, KaggEnvMulti, PlanMarketEnv, terminal_money  # noqa: E402
from .ppo import (  # noqa: E402
    MLP, MarketMLP, MultiHeadMLP, _compute_gae,
    ppo_update, ppo_update_market, ppo_update_multihead,
)
from .rollout import run_episode_worker, worker_init  # noqa: E402


def _run_episode(env, mlp, arch="single", rng=None, sample=True,
                 greedy_frac=0.0, temperature=1.0):
    obs_buf, act_buf, logp_buf = [], [], []
    rew_buf, val_buf, done_buf, nh_buf = [], [], [], []

    obs = env.reset()
    n_hands = int(getattr(env, "n_hands", 0) or 0)
    done = False
    total_r = 0.0
    steps = 0
    gfrac = 0.0 if not sample else greedy_frac
    while not done and steps < 800:
        if arch == "multi":
            act, logp, val, _ = mlp.act(
                obs, n_hands=n_hands, sample=sample, rng=rng,
                greedy_frac=gfrac, temperature=temperature,
            )
        else:
            act, logp, val, _ = mlp.act(obs, sample=sample, rng=rng)
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
    mine, opp = terminal_money(getattr(env, "obs", None))
    return obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf, nh_buf, total_r, steps, mine, opp


def _ingest_episode(result, batch_obs, batch_act, batch_logp, batch_rew, batch_val,
                    batch_done, batch_nh, ep_lengths, ep_rewards, ep_steps,
                    ep_mine, ep_opp):
    if not result or not result[0]:
        return
    obs_b, act_b, logp_b, rew_b, val_b, done_b, nh_b, total_r, steps = result[:9]
    mine = float(result[9]) if len(result) > 9 else float("nan")
    opp_m = float(result[10]) if len(result) > 10 else float("nan")
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
    ep_mine.append(mine)
    ep_opp.append(opp_m)


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


def _spatial_ppo_update(model, opt, batch_obs, batch_act, batch_logp, batch_rew,
                        batch_val, batch_done, batch_nh, ep_lengths, args,
                        entropy_coef=None):
    import torch
    from .spatial_policy import ppo_update_spatial

    adv, ret = _compute_gae(
        batch_rew, batch_val, batch_done, ep_lengths, args.gamma, args.lam,
    )
    obs = torch.tensor(np.asarray(batch_obs, dtype=np.float32), device=args.device)
    act = torch.tensor(np.asarray(batch_act, dtype=np.int64), device=args.device)
    old_logp = torch.tensor(np.asarray(batch_logp, dtype=np.float32), device=args.device)
    adv_t = torch.tensor(adv.astype(np.float32), device=args.device)
    ret_t = torch.tensor(ret.astype(np.float32), device=args.device)
    nh = torch.tensor(np.asarray(batch_nh, dtype=np.int64), device=args.device)
    ent = args.entropy if entropy_coef is None else entropy_coef
    return ppo_update_spatial(
        model, opt, obs, act, old_logp, adv_t, ret_t, nh,
        clip=args.clip, entropy_coef=ent, value_coef=args.value_coef,
        epochs=args.epochs, minibatch=args.minibatch, max_grad_norm=args.max_grad_norm,
        algo=args.algo,
    )


def _entropy_at(it, args):
    start = float(args.entropy)
    end = float(args.entropy_end)
    if int(args.iters) <= 1:
        return start
    t = (it - 1) / max(int(args.iters) - 1, 1)
    return (1.0 - t) * start + t * end


def _rollout_args(opp, seed, weights, args, plan_turns, sample=True):
    gfrac = 0.0 if not sample else float(args.greedy_frac)
    return (opp, seed, weights, args.arch, plan_turns, args.net,
            sample, gfrac, float(args.temperature))


def _greedy_probe(opponent, n, arch, net, spatial, mlp, plan_turns):
    """n greedy episodes vs opponent. Returns (win, money, omoney)."""
    from .rollout import _run_spatial_episode

    mines, opps = [], []
    for i in range(max(int(n), 1)):
        seed = 10_000 + i
        if spatial is not None:
            result = _run_spatial_episode(opponent, seed, spatial.numpy_state(), net,
                                          sample=False)
        else:
            try:
                env = _make_env(arch, opponent, seed, plan_turns)
                rng = np.random.default_rng(seed + 17)
                result = _run_episode(env, mlp, arch=arch, rng=rng, sample=False)
            except Exception as e:
                print(f"  probe env failed seed={seed} opp={opponent}: {e}")
                continue
            try:
                env.close()
            except Exception:
                pass
        if not result:
            continue
        if len(result) > 9:
            mines.append(float(result[9]))
            opps.append(float(result[10]))
    if not mines:
        return float("nan"), float("nan"), float("nan")
    wins = [float(a > b) for a, b in zip(mines, opps) if a == a and b == b]
    win = float(np.mean(wins)) if wins else float("nan")
    return win, float(np.nanmean(mines)), float(np.nanmean(opps))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=["ppo", "a2c", "reinforce"], default="ppo",
                    help="policy update. a2c = unclipped GAE PG (1 epoch); "
                         "reinforce = Monte-Carlo return + value baseline. "
                         "collector / action space stay the same.")
    ap.add_argument("--arch", choices=["single", "multi", "market"], default="multi")
    ap.add_argument("--net", choices=["mlp", "cnn", "transformer"], default="mlp",
                    help="policy trunk. cnn/transformer need --arch multi and "
                         "cannot warm-start from the 75-d MLP npz.")
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--opponents", default="agents/barnyard.py,agents/enhanced/main.py",
                    help="comma-separated curriculum. Default is barnyard then "
                         "enhanced; starter mix owns a hill the exam does not score.")
    ap.add_argument("--switch-after", type=int, default=10**9,
                    help="advance opponent tier every N iters when --advance-at is 0")
    ap.add_argument("--mix-prev", type=float, default=0.25,
                    help="after promoting, this fraction of episodes still vs the previous opponent")
    ap.add_argument("--advance-at", type=float, default=0.5,
                    help="greedy-probe win rate that promotes to the next opponent. "
                         "0 keeps calendar --switch-after. Sampled train win= is "
                         "near 0 under high entropy and must not gate promotion.")
    ap.add_argument("--advance-window", type=int, default=3,
                    help="consecutive probes at --advance-at before promoting")
    ap.add_argument("--max-stage-iters", type=int, default=80,
                    help="force-promote after this many iters on one opponent "
                         "(0 = no cap). Default 80 so a stuck barnyard stage "
                         "still reaches enhanced.")
    ap.add_argument("--probe-every", type=int, default=0,
                    help="every N iters, greedy episodes vs the current "
                         "opponent (exam-like). 0 disables. Auto-on when "
                         "--advance-at > 0.")
    ap.add_argument("--probe-episodes", type=int, default=4,
                    help="greedy episodes per probe")
    ap.add_argument("--pga-frac", type=float, default=0.3, help="first this fraction of iters use fixed seed set")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--gamma", type=float, default=0.997)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=512)
    ap.add_argument("--entropy", type=float, default=0.003)
    ap.add_argument("--entropy-end", type=float, default=5e-4,
                    help="linear anneal of entropy coef from --entropy to this "
                         "by the last iter. Same value as --entropy disables.")
    ap.add_argument("--greedy-frac", type=float, default=0.5,
                    help="fraction of collect steps that take argmax (exam-like). "
                         "0 is the old all-sample collect.")
    ap.add_argument("--temperature", type=float, default=1.0,
                    help="softmax temperature on sampled collect steps only; "
                         "logp stays on the unscaled policy. 1 is default.")
    ap.add_argument("--value-coef", type=float, default=0.5)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--init-weights", default="rl/ckpt_official/ppo_it0300.npz")
    ap.add_argument("--ckpt-dir", default="rl/ckpt_herd")
    ap.add_argument("--device", default="cpu",
                    help="torch device for --net cnn/transformer (cpu is typical)")
    ap.add_argument("--save-every", type=int, default=5)
    ap.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 2),
                    help="parallel rollout workers")
    ap.add_argument("--market-only", action="store_true",
                    help="(deprecated) same as --arch market")
    ap.add_argument("--plan", default=None,
                    help="path to plan turns JSON for --arch market")
    args = ap.parse_args()

    if args.algo != "ppo":
        if "--epochs" not in sys.argv:
            args.epochs = 1
        if "--greedy-frac" not in sys.argv:
            args.greedy_frac = 0.0
        if args.algo == "reinforce" and "--lam" not in sys.argv:
            args.lam = 1.0

    if args.market_only:
        args.arch = "market"
    if args.net != "mlp":
        if args.arch != "multi":
            raise SystemExit("--net cnn/transformer requires --arch multi")
        if args.init_weights == "rl/ckpt_official/ppo_it0300.npz":
            args.init_weights = "none"

    # Compose the default directory from both knobs. Previously --algo a2c
    # won and wrote transformer checkpoints into the MLP A2C dir.
    if args.ckpt_dir == "rl/ckpt_herd":
        tags = [t for t in (args.algo if args.algo != "ppo" else "",
                            args.net if args.net != "mlp" else "") if t]
        if tags:
            args.ckpt_dir = "rl/ckpt_" + "_".join(tags)

    opponents = [o.strip() for o in args.opponents.split(",") if o.strip()]
    if not opponents:
        opponents = ["agents/barnyard.py", "agents/enhanced/main.py"]
    if args.advance_at > 0 and args.probe_every <= 0:
        args.probe_every = 10
        print("probe-every defaulted to 10 because --advance-at is set")
    if args.mix_prev > 0 and any(o == "starter" or o.endswith("/starter") for o in opponents):
        print("WARNING: --mix-prev with starter owns a reward hill the exam does not "
              "score (official 300-iter +56 vs starter, then never recovered vs barnyard). "
              "Prefer --mix-prev 0.")

    os.makedirs(args.ckpt_dir, exist_ok=True)
    log_path = os.path.join(args.ckpt_dir, "log.csv")
    log_new = not os.path.exists(log_path)
    log_f = open(log_path, "a", newline="", encoding="utf-8")
    log_w = csv.writer(log_f)
    if log_new:
        log_w.writerow([
            "iter", "opp", "ep_reward", "win", "money", "omoney",
            "pol", "val", "ent", "steps", "time_s", "n_ep",
            "probe_win", "probe_money", "probe_omoney", "tier",
        ])
        log_f.flush()
    print(f"logging to {log_path}")
    if args.advance_at > 0:
        print(f"curriculum: {opponents}  promote when greedy probe win>="
              f"{args.advance_at} x{args.advance_window}"
              f"  probe-every={args.probe_every}  max-stage-iters={args.max_stage_iters}")
    else:
        print(f"curriculum: {opponents}  calendar switch-after={args.switch_after}"
              f"  probe-every={args.probe_every}")
    print(f"collect: greedy_frac={args.greedy_frac} temperature={args.temperature} "
          f"entropy {args.entropy} -> {args.entropy_end}")
    print(f"algo={args.algo}  epochs={args.epochs}  lam={args.lam}  clip={args.clip}")

    plan_turns = None
    if args.arch == "market":
        if not args.plan:
            raise SystemExit("--arch market requires --plan (path to plan turns JSON)")
        with open(args.plan, "r", encoding="utf-8") as f:
            plan_turns = json.load(f)

    spatial = None
    spatial_opt = None
    mlp = None
    if args.net != "mlp":
        import torch
        from .spatial_policy import SpatialActor
        torch.manual_seed(args.seed)
        spatial = SpatialActor(net=args.net).to(args.device)
        spatial_opt = torch.optim.Adam(spatial.parameters(), lr=args.lr, eps=1e-5)
        print(f"spatial net={args.net} device={args.device} ckpt_dir={args.ckpt_dir}")
    else:
        mlp = _make_mlp(args.arch, args.seed)
    init_weights = args.init_weights
    if args.arch == "market":
        init_weights = init_weights.replace("weights_bc.npz", "weights_bc_market.npz")
    if init_weights and init_weights.lower() not in ("none", "null", "-") and os.path.exists(init_weights):
        if spatial is not None:
            try:
                ck = torch.load(init_weights, map_location=args.device, weights_only=False)
                sd = ck.get("model") or ck.get("state_dict") or ck
                spatial.load_state_dict(sd, strict=False)
                print(f"loaded spatial weights from {init_weights}")
            except Exception as e:
                print(f"init weights load failed: {e}")
        else:
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
    if spatial is not None:
        if os.name == "nt":
            n_workers = min(n_workers, 4)
        import torch
        torch.set_num_threads(1)
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        extra = " (capped; torch+spawn on Windows)" if os.name == "nt" else ""
        print(f"spatial workers={n_workers}{extra}")
    pool = None
    if n_workers > 1:
        pool = ProcessPoolExecutor(max_workers=n_workers, initializer=worker_init)

    start_time = time.time()
    tier = 0
    stage_iters = 0
    streak = 0
    try:
        for it in range(1, args.iters + 1):
            if args.advance_at <= 0:
                tier = min((it - 1) // max(args.switch_after, 1), len(opponents) - 1)
            opp = opponents[tier]
            stage_iters += 1
            use_fixed = it <= int(args.iters * args.pga_frac)
            batch_obs, batch_act, batch_logp = [], [], []
            batch_rew, batch_val, batch_done, batch_nh = [], [], [], []
            ep_lengths, ep_rewards, ep_steps, ep_mine, ep_omoney = [], [], [], [], []
            t0 = time.time()

            if spatial is not None:
                weights_dict = spatial.numpy_state()
            else:
                weights_dict = {k: v for k, v in mlp.params.items()}

            def _episode_opp(ep_i):
                if tier > 0 and args.mix_prev > 0 and (ep_i / max(args.episodes, 1)) < args.mix_prev:
                    return opponents[tier - 1]
                return opp

            if pool is None:
                for ep in range(args.episodes):
                    seed = fixed_seeds[ep % len(fixed_seeds)] if use_fixed else int(rng.integers(0, 1 << 30))
                    ep_opp = _episode_opp(ep)
                    if spatial is not None:
                        from .rollout import _run_spatial_episode
                        result = _run_spatial_episode(
                            ep_opp, seed, weights_dict, args.net, sample=True,
                            greedy_frac=args.greedy_frac, temperature=args.temperature,
                        )
                    else:
                        try:
                            env = _make_env(args.arch, ep_opp, seed, plan_turns)
                        except Exception as e:
                            print(f"  env make failed seed={seed} opp={ep_opp}: {e}")
                            continue
                        ep_rng = np.random.default_rng(seed + 17)
                        result = _run_episode(
                            env, mlp, arch=args.arch, rng=ep_rng, sample=True,
                            greedy_frac=args.greedy_frac, temperature=args.temperature,
                        )
                        try:
                            env.close()
                        except Exception:
                            pass
                    _ingest_episode(
                        result, batch_obs, batch_act, batch_logp, batch_rew, batch_val,
                        batch_done, batch_nh, ep_lengths, ep_rewards, ep_steps,
                        ep_mine, ep_omoney,
                    )
            else:
                from concurrent.futures.process import BrokenProcessPool
                try:
                    futures = []
                    for ep in range(args.episodes):
                        seed = fixed_seeds[ep % len(fixed_seeds)] if use_fixed else int(rng.integers(0, 1 << 30))
                        ep_opp = _episode_opp(ep)
                        futures.append(pool.submit(
                            run_episode_worker,
                            _rollout_args(ep_opp, seed, weights_dict, args, plan_turns),
                        ))
                    for future in futures:
                        try:
                            result = future.result(timeout=300)
                        except Exception as e:
                            print(f"  episode worker failed: {e}")
                            continue
                        if result is None:
                            continue
                        _ingest_episode(
                            result, batch_obs, batch_act, batch_logp, batch_rew, batch_val,
                            batch_done, batch_nh, ep_lengths, ep_rewards, ep_steps,
                            ep_mine, ep_omoney,
                        )
                except BrokenProcessPool as e:
                    print(f"  process pool broke ({e}); in-process rollouts for the rest")
                    try:
                        pool.shutdown(wait=False)
                    except Exception:
                        pass
                    pool = None
                    if not batch_obs:
                        for ep in range(args.episodes):
                            seed = fixed_seeds[ep % len(fixed_seeds)] if use_fixed else int(rng.integers(0, 1 << 30))
                            ep_opp = _episode_opp(ep)
                            if spatial is not None:
                                from .rollout import _run_spatial_episode
                                result = _run_spatial_episode(
                                    ep_opp, seed, weights_dict, args.net, sample=True,
                                    greedy_frac=args.greedy_frac, temperature=args.temperature,
                                )
                            else:
                                env = _make_env(args.arch, ep_opp, seed, plan_turns)
                                ep_rng = np.random.default_rng(seed + 17)
                                result = _run_episode(
                                    env, mlp, arch=args.arch, rng=ep_rng, sample=True,
                                    greedy_frac=args.greedy_frac, temperature=args.temperature,
                                )
                                env.close()
                            _ingest_episode(
                                result, batch_obs, batch_act, batch_logp, batch_rew, batch_val,
                                batch_done, batch_nh, ep_lengths, ep_rewards, ep_steps,
                                ep_mine, ep_omoney,
                            )

            if not batch_obs:
                print(f"iter {it}/{args.iters}  no episodes collected")
                continue

            ent_coef = _entropy_at(it, args)
            update_kw = dict(
                episode_lengths=ep_lengths,
                gamma=args.gamma, lam=args.lam, clip=args.clip, epochs=args.epochs,
                minibatch=args.minibatch, lr=args.lr, entropy_coef=ent_coef,
                value_coef=args.value_coef, max_grad_norm=args.max_grad_norm,
            )
            if args.arch == "multi":
                update_kw["algo"] = args.algo
            if spatial is not None:
                stats = _spatial_ppo_update(
                    spatial, spatial_opt, batch_obs, batch_act, batch_logp,
                    batch_rew, batch_val, batch_done, batch_nh, ep_lengths, args,
                    entropy_coef=ent_coef,
                )
            elif args.arch == "market":
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
            ep_r = float(np.mean(ep_rewards))
            money = float(np.nanmean(ep_mine)) if ep_mine else float("nan")
            omoney = float(np.nanmean(ep_omoney)) if ep_omoney else float("nan")
            wins = [float(a > b) for a, b in zip(ep_mine, ep_omoney)
                    if a == a and b == b]
            win = float(np.mean(wins)) if wins else float("nan")
            pwin = pmine = pomp = float("nan")
            probed = False
            if args.probe_every > 0 and it % args.probe_every == 0:
                probed = True
                pwin, pmine, pomp = _greedy_probe(
                    opp, args.probe_episodes, args.arch, args.net,
                    spatial, mlp, plan_turns,
                )
                print(f"  probe vs {opp}: win={pwin:.2f}  money={pmine:.0f}/{pomp:.0f}  "
                      f"n={args.probe_episodes} greedy seeds 10000+")
            print(f"iter {it:4d}/{args.iters}  algo={args.algo} arch={args.arch} net={args.net}  "
                  f"stage={tier + 1}/{len(opponents)}  opp={opp}  "
                  f"mix_prev={args.mix_prev if tier else 0:.2f}  fixed={int(use_fixed)}  "
                  f"ep_reward={ep_r:.3f}  win={win:.2f}  money={money:.0f}/{omoney:.0f}  "
                  f"steps={np.mean(ep_steps):.1f}  "
                  f"pol={stats['policy_loss']:.4f} val={stats['value_loss']:.4f} ent={stats['entropy']:.4f}  "
                  f"ent_coef={ent_coef:.5f}  time={elapsed:.1f}s")
            log_w.writerow([
                it, opp, f"{ep_r:.4f}", f"{win:.4f}",
                f"{money:.1f}", f"{omoney:.1f}",
                f"{stats['policy_loss']:.6f}", f"{stats['value_loss']:.6f}",
                f"{stats['entropy']:.6f}", f"{float(np.mean(ep_steps)):.1f}",
                f"{elapsed:.2f}", len(ep_rewards),
                f"{pwin:.4f}" if pwin == pwin else "",
                f"{pmine:.1f}" if pmine == pmine else "",
                f"{pomp:.1f}" if pomp == pomp else "",
                tier,
            ])
            log_f.flush()
            if args.advance_at > 0 and tier < len(opponents) - 1:
                reason = ""
                if args.max_stage_iters > 0 and stage_iters >= args.max_stage_iters:
                    reason = f"max-stage-iters={args.max_stage_iters}"
                elif probed and pwin == pwin:
                    if pwin >= args.advance_at:
                        streak += 1
                    else:
                        streak = 0
                    if streak >= max(int(args.advance_window), 1):
                        reason = f"probe_win>={args.advance_at} x{streak}"
                if reason:
                    old = opp
                    tier += 1
                    streak = 0
                    stage_iters = 0
                    print(f"  curriculum: {old} -> {opponents[tier]}  ({reason})")
            if it % args.save_every == 0 or it == args.iters:
                if spatial is not None:
                    import torch
                    path = os.path.join(args.ckpt_dir, f"{args.algo}_it{it:04d}.pt")
                    torch.save({"net": args.net, "model": spatial.state_dict(), "iter": it}, path)
                else:
                    path = os.path.join(args.ckpt_dir, f"{args.algo}_it{it:04d}.npz")
                    mlp.save(path)
                print(f"  saved {path}  total_time={time.time()-start_time:.1f}s")
    finally:
        try:
            log_f.close()
        except Exception:
            pass
        if pool is not None:
            pool.shutdown(wait=True)


if __name__ == "__main__":
    main()
