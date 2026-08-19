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
    import rl.env  # noqa: F401
    import rl.ppo  # noqa: F401


def run_episode_worker(args):
    """Run one episode in a worker process.

    Args:
        args: tuple of (opponent, seed, weights_dict, arch, plan_turns)
              arch ∈ {"single", "multi", "market"}

    Returns:
        (obs, act, logp, rew, val, done, n_hands, total_r, steps) or None.
    """
    _ensure_project_root()
    os.environ.setdefault("KG_FAST_ENV", "1")

    import numpy as np
    from rl.env import KaggEnv, KaggEnvMulti, PlanMarketEnv
    from rl.ppo import MLP, MarketMLP, MultiHeadMLP

    opponent, seed, weights_dict, arch, plan_turns = args

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
        env.close()
        return obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf, nh_buf, total_r, steps
    except Exception as e:
        print(f"worker error seed={seed} opp={opponent}: {e}")
        return None
