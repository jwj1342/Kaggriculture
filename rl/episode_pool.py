"""Episode-level collection pool: workers play WHOLE episodes autonomously.

The lockstep VecEnv pays two pipe round-trips plus a master-side torch forward
per env-step (~18 ms) while the engine+features are ~0.2 ms (KGEnvNP + the
fused analysis). Here each worker runs complete episodes on its own -- numpy
policy inference in-process, no per-step IPC -- and ships one message per
finished episode. The master only publishes weights and learns.

Weights travel by file, not pipe: `publish(state_dict_np, gen)` writes
`weights_dir/weights-<gen>.npz` atomically (tmp + rename; same keys as
policy.export_npz: l1w,l1b,l2w,l2b,fw,fb,mw,mb) and workers reload at every
episode boundary iff the newest gen changed. `collect(min_steps)` blocks until
it has that many steps from episodes of gen >= current_gen - 1; older episodes
(a worker that sat blocked while the master iterated twice) are discarded and
counted in `.dropped`.

Consequences the trainer must accept:
- Trajectories lag the learner by up to one generation (PPO's collected
  old-logp keeps the ratios honest; drift is clipped like any off-policy dust).
- Rewards are computed exactly as rl/vec_env.py computes them (base-price
  net_worth delta / 3000 * shape_w, optional opp_lambda term, terminal
  +-win_bonus), but arrive as complete episodes: GAE needs no bootstrap value,
  the terminal next-value is 0 by construction.
- `set_pool` is fire-and-forget; episodes already in flight finished against
  the old pool (the league accepts the same staleness from its file-swapped
  mirror).

Training seeds stay below 10_000 -- tools/eval.py evaluates at 10_000+, and
that separation is deliberate (README §7).
"""

import multiprocessing as mp
from multiprocessing.connection import wait as _mpc_wait
import os
import sys
import time

# Spawn, not fork: the master holds torch (thread pools, BLAS locks) and a
# forked child inherits locked mutexes without their owners. Pure-Python
# workers survived that; the first numpy matmul inside a worker (a league
# mirror opponent) deadlocked it. Reproduced: fresh process fine, forked
# worker hangs on the same episode. (Same rationale as rl/vec_env.py -- and
# this pool's workers matmul on every single step.)
_CTX = mp.get_context("spawn")

import numpy as np

_RL = os.path.dirname(os.path.abspath(__file__))
if _RL not in sys.path:
    sys.path.insert(0, _RL)

_WEIGHT_KEYS = ("l1w", "l1b", "l2w", "l2b", "fw", "fb", "mw", "mb")
_KEEP_GENS = 3  # newest snapshots kept on disk; older ones are pruned


def _newest_weights(weights_dir):
    """(gen, path) of the highest-gen snapshot, or (-1, None)."""
    best_gen, best_path = -1, None
    try:
        names = os.listdir(weights_dir)
    except FileNotFoundError:
        return best_gen, best_path
    for fn in names:
        if fn.startswith("weights-") and fn.endswith(".npz"):
            try:
                g = int(fn[len("weights-"):-len(".npz")])
            except ValueError:
                continue
            if g > best_gen:
                best_gen, best_path = g, os.path.join(weights_dir, fn)
    return best_gen, best_path


def _sample_head(logits, rng):
    """Sample one masked-softmax head. logits float32, masked entries -1e9.
    Returns (index, logp). Max subtracted before exp; masked entries underflow
    to exactly 0, so a masked action has probability 0 and can never be the
    *first* cumsum entry exceeding r (side='right' skips zero-width bins)."""
    z = logits - logits.max()
    p = np.exp(z)
    c = np.cumsum(p)
    i = int(np.searchsorted(c, rng.random() * c[-1], side="right"))
    if i >= c.shape[0]:          # r == c[-1] cannot happen in exact math;
        i = c.shape[0] - 1       # belt-and-braces for float dust
    return i, float(z[i] - np.log(c[-1]))


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
    # Always the verified np port: episode mode exists to amortise IPC, and the
    # kaggle env would put the framework's deepcopy back into every step.
    sys.path.insert(0, os.path.join(_RL, "tensor_env"))
    import adapter as AD

    rng = np.random.default_rng(wcfg["rng_seed"])
    pool = list(wcfg["pool"])            # [(opponent, weight), ...]
    shape_w = wcfg["shape_w"]
    win_bonus = wcfg["win_bonus"]
    opp_lambda = wcfg.get("opp_lambda", 0.0)
    seed_lo, seed_hi = wcfg["seed_range"]
    weights_dir = wcfg["weights_dir"]
    steps = int(wcfg.get("steps", 720))
    t_max = steps - 1                    # agent acts episode_steps-1 times

    W = None
    loaded_gen = -1
    ep_counter = wcfg["rng_seed"]        # offset so workers alternate out of phase
    fcount = np.zeros(A.N_FARMER, dtype=np.float64)
    mcount = np.zeros(A.N_MARKET, dtype=np.float64)

    # Registered names ("starter", ...) are immutable scripted agents: load the
    # reference module once instead of re-exec'ing it every episode. File-path
    # opponents are re-exec'd per episode ON PURPOSE -- the league mirror swaps
    # weights.npz under a fixed main.py and relies on the re-exec to pick the
    # new net up (league.py refresh_mirror).
    name_cache = {}

    def opponent_fn(opp):
        if os.path.sep in str(opp) or str(opp).endswith(".py"):
            return AD.load_agent(opp)
        fn = name_cache.get(opp)
        if fn is None:
            fn = AD.load_agent(opp)
            name_cache[opp] = fn
        return fn

    while True:
        # Commands are only consumed between episodes; the master never waits
        # on an ack, so a mid-episode worker delays nothing.
        closing = False
        while remote.poll():
            cmd, data = remote.recv()
            if cmd == "close":
                closing = True
            elif cmd == "set_pool":
                pool = list(data)
        if closing:
            remote.close()
            return

        # Newest weights snapshot, (re)loaded iff the gen changed. A snapshot
        # appears only via tmp+rename, so a visible file is complete; a
        # FileNotFoundError can still race the master's pruning -- rescan.
        gen, path = _newest_weights(weights_dir)
        if gen < 0:
            time.sleep(0.05)
            continue
        if gen != loaded_gen:
            try:
                with np.load(path) as z:
                    W = {k: np.ascontiguousarray(z[k], dtype=np.float32)
                         for k in z.files}
                loaded_gen = gen
            except (FileNotFoundError, OSError, ValueError):
                time.sleep(0.02)
                continue

        # ---- one full episode -------------------------------------------
        opps, weights = zip(*pool)
        pw = np.asarray(weights, dtype=float)
        opp = opps[int(rng.choice(len(opps), p=pw / pw.sum()))]
        # Strict seat alternation, not random: the engine is not perfectly
        # seat-symmetric, and alternation makes every stats window (promotion
        # gates especially) seat-balanced by construction.
        ep_counter += 1
        seat = ep_counter % 2
        seed = int(rng.integers(seed_lo, seed_hi))
        env = AD.KGEnvNP(opponent=opponent_fn(opp), steps=steps, seat=seat)
        raw = env.reset(seed=seed)
        prev_worth = O.net_worth(raw)
        prev_opp = O.opp_visible_worth(raw) if opp_lambda else 0.0
        fcount[:] = 0.0
        mcount[:] = 0.0

        ep_obs = np.empty((t_max, O.OBS_DIM), dtype=np.float16)
        ep_fm = np.empty((t_max, A.N_FARMER), dtype=bool)
        ep_mm = np.empty((t_max, A.N_MARKET), dtype=bool)
        ep_fa = np.empty(t_max, dtype=np.int16)
        ep_ma = np.empty(t_max, dtype=np.int16)
        ep_logp = np.empty(t_max, dtype=np.float32)
        ep_rew = np.empty(t_max, dtype=np.float32)

        l1w, l1b = W["l1w"], W["l1b"]
        l2w, l2b = W["l2w"], W["l2b"]
        fw, fb = W["fw"], W["fb"]
        mw, mb = W["mw"], W["mb"]

        t = 0
        done = False
        win = 0.5
        mine = theirs = 0.0
        while not done and t < t_max:
            vec = O.encode(raw)                      # float32, fused analysis
            fm = A.farmer_mask(raw)
            mm = A.market_mask(raw)
            h = np.maximum(0.0, l1w @ vec + l1b)
            h = np.maximum(0.0, l2w @ h + l2b)
            flog = fw @ h + fb
            mlog = mw @ h + mb
            flog[~fm] = -1e9
            mlog[~mm] = -1e9
            fa, flp = _sample_head(flog, rng)
            ma, mlp = _sample_head(mlog, rng)

            ep_obs[t] = vec
            ep_fm[t] = fm
            ep_mm[t] = mm
            ep_fa[t] = fa
            ep_ma[t] = ma
            ep_logp[t] = np.float32(flp + mlp)
            fcount[fa] += 1
            mcount[ma] += 1

            raw, done = env.step(A.decode(raw, fa, ma))
            worth = O.net_worth(raw)
            reward = (worth - prev_worth) / 3000.0 * shape_w
            prev_worth = worth
            if opp_lambda:
                ow = O.opp_visible_worth(raw)
                reward -= opp_lambda * (ow - prev_opp) / 3000.0 * shape_w
                prev_opp = ow
            if done:
                mine, theirs = env.final_money()
                win = 1.0 if mine > theirs else 0.0 if mine < theirs else 0.5
                reward += win_bonus * (1.0 if win == 1.0
                                       else -1.0 if win == 0.0 else 0.0)
            ep_rew[t] = reward
            t += 1

        n_acts = max(1.0, fcount.sum())
        fp = np.concatenate([fcount / n_acts, mcount / n_acts]).astype(np.float32)
        # This send blocks once the pipe is full -- natural backpressure while
        # the master is inside its update; the worker resumes (and re-checks
        # weights) as soon as the next collect() drains.
        remote.send({
            "obs": ep_obs[:t], "fmask": ep_fm[:t], "mmask": ep_mm[:t],
            "fa": ep_fa[:t], "ma": ep_ma[:t],
            "logp": ep_logp[:t], "rew": ep_rew[:t],
            "gen": loaded_gen, "seed": seed,
            "money": mine, "opp_money": theirs, "win": win,
            "opponent": opp, "seat": seat, "fp": fp,
        })


class EpisodePool:
    """Master-side handle. publish() then collect(); workers do the rest."""

    def __init__(self, n_workers, pool, shape_w=1.0, win_bonus=3.0,
                 opp_lambda=0.0, seed_range=(0, 10_000), base_rng_seed=0,
                 weights_dir=None):
        assert weights_dir, "EpisodePool needs a weights_dir"
        self.weights_dir = weights_dir
        os.makedirs(weights_dir, exist_ok=True)
        # Stale snapshots from an earlier run would out-gen the first publish
        # and pin every worker to a dead policy; start from a clean directory.
        for g in self._gens():
            try:
                os.remove(os.path.join(weights_dir, f"weights-{g}.npz"))
            except OSError:
                pass
        self.gen = None
        self.dropped = 0
        self.n = n_workers
        self.remotes, self.procs = [], []
        for i in range(n_workers):
            parent, child = _CTX.Pipe()
            wcfg = {"pool": pool, "shape_w": shape_w, "win_bonus": win_bonus,
                    "seed_range": seed_range, "opp_lambda": opp_lambda,
                    "weights_dir": weights_dir,
                    "rng_seed": base_rng_seed + i * 9973 + 1}
            p = _CTX.Process(target=_worker, args=(child, wcfg), daemon=True)
            p.start()
            child.close()
            self.remotes.append(parent)
            self.procs.append(p)

    def _gens(self):
        out = []
        try:
            names = os.listdir(self.weights_dir)
        except FileNotFoundError:
            return out
        for fn in names:
            if fn.startswith("weights-") and fn.endswith(".npz"):
                try:
                    out.append(int(fn[len("weights-"):-len(".npz")]))
                except ValueError:
                    pass
        return out

    def publish(self, state_dict_np, gen):
        """Write weights_dir/weights-<gen>.npz atomically (tmp + rename) and
        make <gen> the current generation for collect()'s staleness cut."""
        assert set(state_dict_np) == set(_WEIGHT_KEYS), \
            f"expected keys {_WEIGHT_KEYS}, got {sorted(state_dict_np)}"
        path = os.path.join(self.weights_dir, f"weights-{int(gen)}.npz")
        tmp = path + ".tmp.npz"          # keeps np.savez from appending .npz
        np.savez(tmp, **{k: np.asarray(v, dtype=np.float32)
                         for k, v in state_dict_np.items()})
        os.replace(tmp, path)
        self.gen = int(gen)
        for g in sorted(self._gens(), reverse=True)[_KEEP_GENS:]:
            try:
                os.remove(os.path.join(self.weights_dir, f"weights-{g}.npz"))
            except OSError:
                pass

    def collect(self, min_steps):
        """Block until >= min_steps env-steps of fresh episodes (gen >=
        current_gen - 1) have arrived; return them as a list of episode dicts.
        Stale episodes are discarded and counted in .dropped."""
        out, got = [], 0
        while got < min_steps:
            ready = _mpc_wait(self.remotes, timeout=600.0)
            if not ready:
                raise RuntimeError(
                    "no finished episode from any pool worker for 600s -- "
                    "likely a stuck opponent or a worker that died before "
                    "reporting")
            for r in ready:
                try:
                    msg = r.recv()
                except EOFError:
                    i = self.remotes.index(r)
                    raise RuntimeError(
                        f"episode worker {i} died (exitcode "
                        f"{self.procs[i].exitcode})")
                if isinstance(msg, tuple) and len(msg) == 2 \
                        and msg[0] == "__worker_error__":
                    raise RuntimeError(f"episode worker crashed:\n{msg[1]}")
                if self.gen is not None and msg["gen"] < self.gen - 1:
                    self.dropped += 1
                    continue
                out.append(msg)
                got += int(msg["rew"].shape[0])
        return out

    def set_pool(self, pool):
        """Fire-and-forget: workers apply it at their next episode boundary.
        Episodes already in flight were sampled from the old pool."""
        for r in self.remotes:
            try:
                r.send(("set_pool", list(pool)))
            except BrokenPipeError:
                pass

    def close(self):
        for r in self.remotes:
            try:
                r.send(("close", None))
            except (BrokenPipeError, OSError):
                pass
        # Workers only see "close" between episodes, and one may be blocked
        # mid-send on a full pipe -- keep draining so it can get there.
        t0 = time.time()
        while time.time() - t0 < 10 and any(p.is_alive() for p in self.procs):
            for r in self.remotes:
                try:
                    while r.poll():
                        r.recv()
                except (EOFError, OSError):
                    pass
            time.sleep(0.05)
        for p in self.procs:
            p.join(timeout=2)
            if p.is_alive():
                p.terminate()
