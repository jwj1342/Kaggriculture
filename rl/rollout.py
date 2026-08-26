"""Parallel episode rollout for PPO training.

Provides a worker function that can be run in a subprocess to collect
one episode trajectory. This enables parallel environment stepping
via ProcessPoolExecutor, which is the main bottleneck in RL training.
"""

import os
import sys


def _ensure_project_root():
    """Make sure the project root is in sys.path for imports in worker processes."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    if root not in sys.path:
        sys.path.insert(0, root)


def worker_init():
    """Import heavy modules once per persistent worker process."""
    _ensure_project_root()
    os.environ.setdefault("KG_FAST_ENV", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    import rl.env  # noqa: F401
    import rl.ppo  # noqa: F401
    try:
        import torch
        torch.set_num_threads(1)
        import rl.spatial_policy  # noqa: F401
        import rl.board_obs  # noqa: F401
    except Exception:
        pass


def run_episode_worker(args):
    """Run one episode in a worker process.

    Args:
        args: (opponent, seed, weights_dict, arch, plan_turns[, net])
              arch ∈ {"single", "multi", "market"}
              net  ∈ {"mlp", "cnn", "transformer"}; default mlp

    Returns:
        (obs, act, logp, rew, val, done, n_hands, total_r, steps, money, omoney) or None.
    """
    _ensure_project_root()
    os.environ.setdefault("KG_FAST_ENV", "1")

    import numpy as np
    from rl.env import KaggEnv, KaggEnvMulti, PlanMarketEnv, terminal_money
    from rl.ppo import MLP, MarketMLP, MultiHeadMLP

    net = "mlp"
    if len(args) >= 6:
        opponent, seed, weights_dict, arch, plan_turns, net = args[:6]
    else:
        opponent, seed, weights_dict, arch, plan_turns = args[:5]

    if net in ("cnn", "transformer"):
        return _run_spatial_episode(opponent, seed, weights_dict, net)

    if arch == "market":
        mlp = MarketMLP(seed=0)
    elif arch == "multi":
        mlp = MultiHeadMLP(seed=0)
    else:
        mlp = MLP(seed=0)
    for k, v in weights_dict.items():
        if k in mlp.params:
            arr = np.asarray(v, dtype=np.float64)
            if arr.shape == mlp.params[k].shape:
                mlp.params[k] = arr

    try:
        if arch == "market":
            env = PlanMarketEnv(plan_turns=plan_turns, opponent=opponent, seed=seed)
        elif arch == "multi":
            env = KaggEnvMulti(opponent=opponent, seed=seed)
        else:
            env = KaggEnv(opponent=opponent, seed=seed)

        rng = np.random.default_rng(int(seed) + 17)
        obs = env.reset()
        n_hands = int(getattr(env, "n_hands", 0) or 0)
        done = False
        obs_buf, act_buf, logp_buf = [], [], []
        rew_buf, val_buf, done_buf, nh_buf = [], [], [], []
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
        mine, opp_m = terminal_money(getattr(env, "obs", None))
        env.close()
        return obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf, nh_buf, total_r, steps, mine, opp_m
    except Exception as e:
        print(f"worker error seed={seed} opp={opponent}: {e}")
        return None


def _run_spatial_episode(opponent, seed, weights_dict, net, sample=True):
    """Official-engine episode with a CNN / Transformer SpatialActor."""
    import numpy as np
    import torch

    from rl.board_obs import pack_obs
    from rl.env import KaggEnvMulti, terminal_money
    from rl.spatial_policy import SpatialActor

    model = SpatialActor(net=net)
    model.load_numpy_state(weights_dict)
    model.eval()

    try:
        env = KaggEnvMulti(opponent=opponent, seed=seed)
        rng_seed = int(seed) + 17
        torch.manual_seed(rng_seed)
        obs_raw = env.reset()
        n_hands = int(getattr(env, "n_hands", 0) or 0)
        packed = pack_obs(env.obs, global_feats=obs_raw)
        done = False
        obs_buf, act_buf, logp_buf = [], [], []
        rew_buf, val_buf, done_buf, nh_buf = [], [], [], []
        total_r = 0.0
        steps = 0
        while not done and steps < 800:
            xt = torch.tensor(packed, dtype=torch.float32).unsqueeze(0)
            nh = torch.tensor([n_hands], dtype=torch.int64)
            tasks, logp, val = model.act(xt, nh, sample=sample)
            act = [int(v) for v in tasks[0].tolist()]
            obs_buf.append(packed)
            act_buf.append(act)
            logp_buf.append(float(logp[0]))
            val_buf.append(float(val[0]))
            nh_buf.append(n_hands)
            obs_raw, r, done, info = env.step(act)
            n_hands = int((info or {}).get("n_hands", n_hands) or 0)
            packed = pack_obs(env.obs, global_feats=obs_raw)
            rew_buf.append(r)
            done_buf.append(done)
            total_r += r
            steps += 1
        if done:
            val_buf.append(0.0)
        else:
            xt = torch.tensor(packed, dtype=torch.float32).unsqueeze(0)
            nh = torch.tensor([n_hands], dtype=torch.int64)
            val_buf.append(float(model.act(xt, nh, sample=False)[2][0]))
        mine, opp_m = terminal_money(getattr(env, "obs", None))
        env.close()
        return obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf, nh_buf, total_r, steps, mine, opp_m
    except Exception as e:
        import traceback
        print(f"spatial worker error seed={seed} opp={opponent}: {e}")
        traceback.print_exc()
        return None
