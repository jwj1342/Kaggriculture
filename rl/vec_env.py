"""Subprocess vector env: N workers, each one KGEnv + encode/mask/decode/reward.

The feature work (encode, masks, macro decode, net_worth) runs *inside* the
worker so it parallelises with the environment itself; the learner only ever
sees float32 vectors. Protocol per step:

    master -> worker: ("step", (f_idx, m_idx))
    worker -> master: (obs_vec, fmask, mmask, reward, done, epinfo|None)

Auto-reset: on done the worker starts the next episode (fresh seed, opponent
sampled from the current pool, random seat) and returns the *new* episode's
first observation. Reward on the terminal step includes the win/loss bonus.

Training seeds stay below 10_000 -- tools/eval.py evaluates at 10_000+, and
that separation is deliberate (README §7).
"""

import multiprocessing as mp
import os
import sys

# Spawn, not fork: the master holds torch (thread pools, BLAS locks) and a
# forked child inherits locked mutexes without their owners. Pure-Python
# workers survived that; the first numpy matmul inside a worker (a league
# mirror opponent) deadlocked it. Reproduced: fresh process fine, forked
# worker hangs on the same episode.
_CTX = mp.get_context("spawn")

import numpy as np

_RL = os.path.dirname(os.path.abspath(__file__))
if _RL not in sys.path:
    sys.path.insert(0, _RL)


def _worker(remote, wcfg):
    try:
        _worker_body(remote, wcfg)
    except Exception:
        import traceback
        try:
            remote.send(("__worker_error__", traceback.format_exc()))
        except Exception:
            pass
        raise


def _worker_body(remote, wcfg):
    sys.path.insert(0, _RL)
    import actions as A
    import obs as O
    if os.environ.get("KG_ENGINE") == "np":
        # Verified byte-exact port (rl/tensor_env/verify.py gate) -- ~13x
        # end-to-end. Evaluation never uses this path; tools/eval.py stays on
        # the reference engine.
        sys.path.insert(0, os.path.join(_RL, "tensor_env"))
        from adapter import KGEnvNP as KGEnv
    else:
        from kg_env import KGEnv

    rng = np.random.default_rng(wcfg["rng_seed"])
    pool = list(wcfg["pool"])            # [(opponent, weight), ...]
    shape_w = wcfg["shape_w"]
    win_bonus = wcfg["win_bonus"]
    opp_lambda = wcfg.get("opp_lambda", 0.0)
    seed_lo, seed_hi = wcfg["seed_range"]

    env = None
    raw = None
    prev_worth = 0.0
    prev_opp = 0.0
    fcount = np.zeros(A.N_FARMER, dtype=np.float64)
    mcount = np.zeros(A.N_MARKET, dtype=np.float64)
    ep_counter = wcfg["rng_seed"]  # offset so workers alternate out of phase

    def new_episode():
        nonlocal env, raw, prev_worth, prev_opp, ep_counter
        opps, weights = zip(*pool)
        p = np.asarray(weights, dtype=float)
        opp = opps[int(rng.choice(len(opps), p=p / p.sum()))]
        # Strict seat alternation, not random: the engine is not perfectly
        # seat-symmetric, and alternation makes every stats window (promotion
        # gates especially) seat-balanced by construction.
        ep_counter += 1
        seat = ep_counter % 2
        env = KGEnv(opponent=opp, seat=seat)
        raw = env.reset(seed=int(rng.integers(seed_lo, seed_hi)))
        prev_worth = O.net_worth(raw)
        prev_opp = O.opp_visible_worth(raw) if opp_lambda else 0.0
        fcount[:] = 0.0
        mcount[:] = 0.0

    def pack():
        return O.encode(raw), A.farmer_mask(raw), A.market_mask(raw)

    new_episode()
    while True:
        cmd, data = remote.recv()
        if cmd == "obs":
            remote.send(pack())
        elif cmd == "step":
            fcount[data[0]] += 1
            mcount[data[1]] += 1
            nonlocal_raw, done = env.step(A.decode(raw, data[0], data[1]))
            raw = nonlocal_raw
            worth = O.net_worth(raw)
            reward = (worth - prev_worth) / 3000.0 * shape_w
            prev_worth = worth
            if opp_lambda:
                ow = O.opp_visible_worth(raw)
                reward -= opp_lambda * (ow - prev_opp) / 3000.0 * shape_w
                prev_opp = ow
            ep = None
            if done:
                mine, theirs = env.final_money()
                win = 1.0 if mine > theirs else 0.0 if mine < theirs else 0.5
                reward += win_bonus * (1.0 if win == 1.0 else -1.0 if win == 0.0 else 0.0)
                n_acts = max(1.0, fcount.sum())
                fp = np.concatenate([fcount / n_acts, mcount / n_acts])
                ep = {"money": mine, "opp_money": theirs, "win": win,
                      "opponent": env.opponent, "seat": env.seat,
                      "fp": fp.astype(np.float32)}
                new_episode()
            vec, fm, mm = pack()
            remote.send((vec, fm, mm, reward, done, ep))
        elif cmd == "set_pool":
            pool = list(data)
            remote.send(True)
        elif cmd == "close":
            remote.close()
            break


class VecEnv:
    def __init__(self, n_envs, pool, shape_w=1.0, win_bonus=3.0,
                 seed_range=(0, 10_000), base_rng_seed=0, opp_lambda=0.0):
        self.n = n_envs
        self.remotes, self.procs = [], []
        for i in range(n_envs):
            parent, child = _CTX.Pipe()
            wcfg = {"pool": pool, "shape_w": shape_w, "win_bonus": win_bonus,
                    "seed_range": seed_range, "opp_lambda": opp_lambda,
                    "rng_seed": base_rng_seed + i * 9973 + 1}
            p = _CTX.Process(target=_worker, args=(child, wcfg), daemon=True)
            p.start()
            child.close()
            self.remotes.append(parent)
            self.procs.append(p)

    def initial_obs(self):
        for r in self.remotes:
            r.send(("obs", None))
        return self._collect_obs([r.recv() for r in self.remotes])

    def step(self, f_idx, m_idx):
        for i, r in enumerate(self.remotes):
            r.send(("step", (int(f_idx[i]), int(m_idx[i]))))
        out = []
        for i, r in enumerate(self.remotes):
            if not r.poll(600):
                raise RuntimeError(
                    f"vec worker {i} unresponsive for 600s -- likely stuck "
                    f"inside its episode; check that worker's opponent")
            msg = r.recv()
            if isinstance(msg, tuple) and len(msg) == 2 \
                    and msg[0] == "__worker_error__":
                raise RuntimeError(f"vec worker {i} crashed:\n{msg[1]}")
            out.append(msg)
        obs, fm, mm = self._collect_obs([(o[0], o[1], o[2]) for o in out])
        rew = np.asarray([o[3] for o in out], dtype=np.float32)
        done = np.asarray([o[4] for o in out], dtype=bool)
        eps = [o[5] for o in out if o[5] is not None]
        return obs, fm, mm, rew, done, eps

    def set_pool(self, pool):
        for r in self.remotes:
            r.send(("set_pool", pool))
        for r in self.remotes:
            r.recv()

    def close(self):
        for r in self.remotes:
            try:
                r.send(("close", None))
            except BrokenPipeError:
                pass
        for p in self.procs:
            p.join(timeout=5)

    @staticmethod
    def _collect_obs(triples):
        obs = np.stack([t[0] for t in triples])
        fm = np.stack([t[1] for t in triples])
        mm = np.stack([t[2] for t in triples])
        return obs, fm, mm
