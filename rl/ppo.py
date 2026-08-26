"""Pure-numpy PPO (MLP actor-critic) for Kaggriculture.

No external deep-learning framework required. Trains on CPU with Adam and
manual backprop through a 2-hidden-layer tanh MLP.
"""

import json
import math
import os
import zlib

import numpy as np

from . import features  # noqa: E402
from .action_space import (  # noqa: E402
    FARM_TASKS, MARKET_MODES, PHASE_EARLY_LAST_DAY, PHASE_LATE_FIRST_DAY,
    PHASE_MODE_BIAS, PHASE_TASK_BIAS, STEP_FEATURE_INDEX,
)
from .features import FEATURE_DIM  # noqa: E402


_IN = FEATURE_DIM
_HID = 256
_TASK = len(FARM_TASKS)
_MODE = len(MARKET_MODES)
_NHAND = 12
_NHEADS = 1 + _NHAND  # farmer + hands; market is separate
_ACT_MULTI = _NHEADS + 1  # farmer + 12 hands + market
_PHASE_TASK = np.asarray(PHASE_TASK_BIAS, dtype=np.float64)
_PHASE_MODE = np.asarray(PHASE_MODE_BIAS, dtype=np.float64)


def _phase_from_feats(x):
    """0 early / 1 mid / 2 late from feats[..., STEP_FEATURE_INDEX] = step/720."""
    step_n = np.clip(np.asarray(x[..., STEP_FEATURE_INDEX], dtype=np.float64), 0.0, 1.0)
    day = np.floor(step_n * 30.0).astype(np.int64)
    return np.where(day >= PHASE_LATE_FIRST_DAY, 2, np.where(day <= PHASE_EARLY_LAST_DAY, 0, 1))


def _apply_phase_logits(lf, lh, lm, x):
    """Add calendar-day task/mode extras. Must run in both act() and PPO update."""
    ph = _phase_from_feats(x)
    tb = _PHASE_TASK[ph]
    lf = lf + tb
    B = lf.shape[0]
    lh = lh.reshape(B, _NHAND, _TASK) + tb[:, None, :]
    lh = lh.reshape(B, _NHAND * _TASK)
    lm = lm + _PHASE_MODE[ph]
    return lf, lh, lm


def _as_feats(obs):
    """Accept either a raw env observation or an already-encoded feature vector."""
    if isinstance(obs, np.ndarray):
        arr = np.asarray(obs, dtype=np.float64).reshape(-1)
        if arr.size == _IN:
            return arr
    if isinstance(obs, (list, tuple)) and len(obs) == _IN:
        try:
            arr = np.asarray(obs, dtype=np.float64).reshape(-1)
            if arr.size == _IN and np.issubdtype(arr.dtype, np.number):
                return arr
        except (TypeError, ValueError):
            pass
    return np.asarray(features.encode(obs), dtype=np.float64).reshape(-1)


def _softmax(logits):
    z = logits - np.max(logits, axis=-1, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=-1, keepdims=True)


def _rng(rng):
    if rng is None:
        return np.random.default_rng()
    return rng


def _choice(rng, n, p):
    return int(rng.choice(n, p=p))


def _orthogonal(shape, gain=1.0):
    rows, cols = shape
    a = np.random.randn(rows, cols).astype(np.float64)
    u, s, vh = np.linalg.svd(a, full_matrices=False)
    mat = u if u.shape == shape else vh
    return (gain * mat).astype(np.float64)


def _xavier(shape):
    fan_in, fan_out = shape
    limit = math.sqrt(6.0 / (fan_in + fan_out))
    return np.random.uniform(-limit, limit, size=shape).astype(np.float64)


class MLP:
    def __init__(self, seed=0):
        rng = np.random.default_rng(int(seed))
        self.params = {
            "W1": _orthogonal((_IN, _HID), gain=math.sqrt(2.0)),
            "b1": np.zeros(_HID, dtype=np.float64),
            "W2": _orthogonal((_HID, _HID), gain=math.sqrt(2.0)),
            "b2": np.zeros(_HID, dtype=np.float64),
            "Wt": _xavier((_HID, _TASK)),
            "bt": np.zeros(_TASK, dtype=np.float64),
            "Wm": _xavier((_HID, _MODE)),
            "bm": np.zeros(_MODE, dtype=np.float64),
            "Wv": _xavier((_HID, 1)),
            "bv": np.zeros(1, dtype=np.float64),
        }
        self.opt = {
            "m": {k: np.zeros_like(v) for k, v in self.params.items()},
            "v": {k: np.zeros_like(v) for k, v in self.params.items()},
        }
        self.t = 0

    def forward(self, x):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        z1 = x @ self.params["W1"] + self.params["b1"]
        h1 = np.tanh(z1)
        z2 = h1 @ self.params["W2"] + self.params["b2"]
        h2 = np.tanh(z2)
        lt = h2 @ self.params["Wt"] + self.params["bt"]
        lm = h2 @ self.params["Wm"] + self.params["bm"]
        lv = h2 @ self.params["Wv"] + self.params["bv"]
        return {
            "x": x, "z1": z1, "h1": h1, "z2": z2, "h2": h2,
            "lt": lt, "lm": lm, "lv": lv,
        }

    def act(self, obs, sample=True, rng=None):
        f = _as_feats(obs)
        out = self.forward(f.reshape(1, -1))
        pt = _softmax(out["lt"][0])
        pm = _softmax(out["lm"][0])
        rng = _rng(rng)
        if sample:
            t = _choice(rng, _TASK, pt)
            m = _choice(rng, _MODE, pm)
        else:
            t = int(np.argmax(pt))
            m = int(np.argmax(pm))
        logp = float(np.log(pt[t] + 1e-8) + np.log(pm[m] + 1e-8))
        val = float(out["lv"][0, 0])
        return (t, m), logp, val, out

    def backward(self, cache, dlt, dlm, dlv):
        x, z1, h1, z2, h2 = cache["x"], cache["z1"], cache["h1"], cache["z2"], cache["h2"]
        dWt = h2.T @ dlt
        dbt = dlt.sum(axis=0)
        dWm = h2.T @ dlm
        dbm = dlm.sum(axis=0)
        dWv = h2.T @ dlv
        dbv = dlv.sum(axis=0)
        dh2 = dlt @ self.params["Wt"].T + dlm @ self.params["Wm"].T + dlv @ self.params["Wv"].T
        dh2 *= (1.0 - h2 ** 2)
        dW2 = h1.T @ dh2
        db2 = dh2.sum(axis=0)
        dh1 = dh2 @ self.params["W2"].T
        dh1 *= (1.0 - h1 ** 2)
        dW1 = x.T @ dh1
        db1 = dh1.sum(axis=0)
        return {
            "W1": dW1, "b1": db1, "W2": dW2, "b2": db2,
            "Wt": dWt, "bt": dbt, "Wm": dWm, "bm": dbm,
            "Wv": dWv, "bv": dbv,
        }

    def adam_step(self, grads, lr=3e-4, beta1=0.9, beta2=0.999, eps=1e-5, max_grad_norm=0.5):
        self.t += 1
        total_norm = 0.0
        for k, g in grads.items():
            total_norm += float(np.sum(g * g))
        total_norm = math.sqrt(total_norm)
        clip = max_grad_norm / (total_norm + 1e-8)
        if clip < 1.0:
            for k in grads:
                grads[k] *= clip
        for k, g in grads.items():
            self.opt["m"][k] = beta1 * self.opt["m"][k] + (1 - beta1) * g
            self.opt["v"][k] = beta2 * self.opt["v"][k] + (1 - beta2) * (g * g)
            m_hat = self.opt["m"][k] / (1 - beta1 ** self.t)
            v_hat = self.opt["v"][k] / (1 - beta2 ** self.t)
            self.params[k] -= lr * m_hat / (np.sqrt(v_hat) + eps)

    def save(self, path):
        payload = {}
        for k, v in self.params.items():
            payload[k] = v.astype(np.float64).tolist()
        payload["t"] = int(self.t)
        blob = zlib.compress(json.dumps(payload).encode("utf-8"))
        with open(path, "wb") as f:
            f.write(blob)

    def load(self, path, allow_partial=False):
        with open(path, "rb") as f:
            payload = json.loads(zlib.decompress(f.read()).decode("utf-8"))
        _load_params(self, payload, allow_partial=allow_partial)


def _load_params(mlp, payload, allow_partial=False, aliases=None):
    """Copy matching-shape arrays from a checkpoint payload into mlp.params."""
    aliases = aliases or {}
    for k in mlp.params:
        src = k
        if src not in payload and k in aliases:
            src = aliases[k]
        if src not in payload:
            if allow_partial:
                continue
            raise KeyError(f"checkpoint missing param {k}")
        arr = np.array(payload[src], dtype=np.float64)
        if arr.shape != mlp.params[k].shape:
            if allow_partial:
                continue
            raise ValueError(f"shape mismatch for {k}: {arr.shape} vs {mlp.params[k].shape}")
        mlp.params[k] = arr
    mlp.t = int(payload.get("t", mlp.t))


def _compute_gae(rewards, values, dones, episode_lengths=None, gamma=0.99, lam=0.95):
    """GAE. `values` is length T, or T + n_episodes if a bootstrap value was appended per episode."""
    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    dones = np.asarray(dones, dtype=np.float64)
    T = len(rewards)
    adv = np.zeros(T, dtype=np.float64)
    ret = np.zeros(T, dtype=np.float64)
    if episode_lengths is None:
        episode_lengths = [T]
    n_ep = len(episode_lengths)
    has_boot = len(values) == T + n_ep
    off = 0
    voff = 0
    for T_ep in episode_lengths:
        last_gae = 0.0
        for t in reversed(range(T_ep)):
            idx = off + t
            v_t = float(values[voff + t] if has_boot else values[idx])
            if dones[idx]:
                next_val = 0.0
            elif has_boot:
                next_val = float(values[voff + t + 1])
            elif t + 1 < T_ep:
                next_val = float(values[idx + 1])
            else:
                next_val = 0.0
            delta = float(rewards[idx]) + gamma * next_val - v_t
            last_gae = delta + gamma * lam * (0.0 if dones[idx] else 1.0) * last_gae
            adv[idx] = last_gae
            ret[idx] = last_gae + v_t
        off += T_ep
        voff += T_ep + (1 if has_boot else 0)
    return adv, ret


def _ppo_logits_grad(probs, actions, advantages, logp, old_logp, clip, entropy_coef):
    """dL/d(logits) for clipped PPO surrogate + entropy, L averaged over batch."""
    B = probs.shape[0]
    ratio = np.exp(logp - old_logp)
    surr1 = ratio * advantages
    surr2 = np.clip(ratio, 1.0 - clip, 1.0 + clip) * advantages
    unclipped = surr1 <= surr2
    dlogp = np.where(unclipped, -ratio * advantages, 0.0) / max(B, 1)
    one_hot = np.zeros_like(probs)
    one_hot[np.arange(B), actions] = 1.0
    dlogits = dlogp[:, None] * (one_hot - probs)
    log_probs = np.log(probs + 1e-8)
    H = -(probs * log_probs).sum(axis=1, keepdims=True)
    dH = -probs * (log_probs + H)
    dlogits += (-entropy_coef / max(B, 1)) * dH
    policy_loss = -np.minimum(surr1, surr2).mean()
    entropy = float(H.mean())
    return dlogits, policy_loss, entropy, ratio


def ppo_update(mlp, obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf,
               episode_lengths=None, gamma=0.99, lam=0.95, clip=0.2, epochs=4, minibatch=256,
               lr=3e-4, entropy_coef=0.01, value_coef=0.5, max_grad_norm=0.5):
    T = len(rew_buf)
    adv, ret = _compute_gae(rew_buf, val_buf, done_buf, episode_lengths, gamma, lam)
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)

    total_policy = 0.0
    total_value = 0.0
    total_entropy = 0.0
    n_updates = 0

    obs = np.array(obs_buf, dtype=np.float64)
    act_t = np.array([a[0] for a in act_buf], dtype=np.int64)
    act_m = np.array([a[1] for a in act_buf], dtype=np.int64)
    old_logp = np.array(logp_buf, dtype=np.float64)

    idx = np.arange(T)
    for _ in range(epochs):
        np.random.shuffle(idx)
        for start in range(0, T, minibatch):
            batch = idx[start:start + minibatch]
            if len(batch) == 0:
                continue
            bx = obs[batch]
            bat = act_t[batch]
            bam = act_m[batch]
            bold = old_logp[batch]
            badv = adv[batch]
            bret = ret[batch]

            out = mlp.forward(bx)
            h2 = out["h2"]
            lt, lm = out["lt"], out["lm"]
            lv = out["lv"]

            lt -= lt.max(axis=1, keepdims=True)
            pt = np.exp(lt) / np.exp(lt).sum(axis=1, keepdims=True)
            logp_t = np.log(pt[np.arange(len(batch)), bat] + 1e-8)
            lm -= lm.max(axis=1, keepdims=True)
            pm = np.exp(lm) / np.exp(lm).sum(axis=1, keepdims=True)
            logp_m = np.log(pm[np.arange(len(batch)), bam] + 1e-8)
            logp = logp_t + logp_m
            ratio = np.exp(logp - bold)

            clip_adv = np.clip(ratio, 1.0 - clip, 1.0 + clip) * badv[:, None]
            policy_loss = -np.minimum(ratio[:, None] * badv[:, None], clip_adv).mean()

            value_pred = lv[:, 0]
            value_loss = ((value_pred - bret) ** 2).mean()

            entropy = -(pt * np.log(pt + 1e-8)).sum(axis=1).mean() - (pm * np.log(pm + 1e-8)).sum(axis=1).mean()

            loss = policy_loss + value_coef * value_loss - entropy_coef * entropy
            loss_val = float(loss)

            d_policy = np.zeros_like(lt)
            d_policy[np.arange(len(batch)), bat] = -1.0 * badv / max(len(batch), 1)
            d_policy2 = np.zeros_like(lm)
            d_policy2[np.arange(len(batch)), bam] = -1.0 * badv / max(len(batch), 1)

            dlt = d_policy.copy()
            dlm = d_policy2.copy()
            dlv = 2.0 * (value_pred - bret) / max(len(batch), 1)

            grads = mlp.backward(out, dlt, dlm, dlv.reshape(-1, 1))
            mlp.adam_step(grads, lr=lr, max_grad_norm=max_grad_norm)

            total_policy += float(policy_loss)
            total_value += float(value_loss)
            total_entropy += float(entropy)
            n_updates += 1

    return {
        "policy_loss": total_policy / max(n_updates, 1),
        "value_loss": total_value / max(n_updates, 1),
        "entropy": total_entropy / max(n_updates, 1),
        "loss": loss_val,
    }


class MarketMLP:
    def __init__(self, seed=0):
        rng = np.random.default_rng(int(seed))
        self.params = {
            "W1": _orthogonal((_IN, _HID), gain=math.sqrt(2.0)),
            "b1": np.zeros(_HID, dtype=np.float64),
            "W2": _orthogonal((_HID, _HID), gain=math.sqrt(2.0)),
            "b2": np.zeros(_HID, dtype=np.float64),
            "Wm": _xavier((_HID, _MODE)),
            "bm": np.zeros(_MODE, dtype=np.float64),
            "Wv": _xavier((_HID, 1)),
            "bv": np.zeros(1, dtype=np.float64),
        }
        self.opt = {
            "m": {k: np.zeros_like(v) for k, v in self.params.items()},
            "v": {k: np.zeros_like(v) for k, v in self.params.items()},
        }
        self.t = 0

    def forward(self, x):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        z1 = x @ self.params["W1"] + self.params["b1"]
        h1 = np.tanh(z1)
        z2 = h1 @ self.params["W2"] + self.params["b2"]
        h2 = np.tanh(z2)
        lm = h2 @ self.params["Wm"] + self.params["bm"]
        lv = h2 @ self.params["Wv"] + self.params["bv"]
        return {"x": x, "z1": z1, "h1": h1, "z2": z2, "h2": h2, "lm": lm, "lv": lv}

    def act(self, obs, sample=True, rng=None):
        f = _as_feats(obs)
        out = self.forward(f.reshape(1, -1))
        pm = _softmax(out["lm"][0])
        rng = _rng(rng)
        m = _choice(rng, _MODE, pm) if sample else int(np.argmax(pm))
        logp = float(np.log(pm[m] + 1e-8))
        val = float(out["lv"][0, 0])
        return m, logp, val, out

    def backward(self, cache, dlm, dlv):
        x, z1, h1, z2, h2 = cache["x"], cache["z1"], cache["h1"], cache["z2"], cache["h2"]
        dWm = h2.T @ dlm
        dbm = dlm.sum(axis=0)
        dWv = h2.T @ dlv
        dbv = dlv.sum(axis=0)
        dh2 = dlm @ self.params["Wm"].T + dlv @ self.params["Wv"].T
        dh2 *= (1.0 - h2 ** 2)
        dW2 = h1.T @ dh2
        db2 = dh2.sum(axis=0)
        dh1 = dh2 @ self.params["W2"].T
        dh1 *= (1.0 - h1 ** 2)
        dW1 = x.T @ dh1
        db1 = dh1.sum(axis=0)
        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2, "Wm": dWm, "bm": dbm, "Wv": dWv, "bv": dbv}

    def adam_step(self, grads, lr=3e-4, beta1=0.9, beta2=0.999, eps=1e-5, max_grad_norm=0.5):
        self.t += 1
        total_norm = 0.0
        for k, g in grads.items():
            total_norm += float(np.sum(g * g))
        total_norm = math.sqrt(total_norm)
        clip = max_grad_norm / (total_norm + 1e-8)
        if clip < 1.0:
            for k in grads:
                grads[k] *= clip
        for k, g in grads.items():
            self.opt["m"][k] = beta1 * self.opt["m"][k] + (1 - beta1) * g
            self.opt["v"][k] = beta2 * self.opt["v"][k] + (1 - beta2) * (g * g)
            m_hat = self.opt["m"][k] / (1 - beta1 ** self.t)
            v_hat = self.opt["v"][k] / (1 - beta2 ** self.t)
            self.params[k] -= lr * m_hat / (np.sqrt(v_hat) + eps)

    def save(self, path):
        payload = {}
        for k, v in self.params.items():
            payload[k] = v.astype(np.float64).tolist()
        payload["t"] = int(self.t)
        blob = zlib.compress(json.dumps(payload).encode("utf-8"))
        with open(path, "wb") as f:
            f.write(blob)

    def load(self, path, allow_partial=False):
        with open(path, "rb") as f:
            payload = json.loads(zlib.decompress(f.read()).decode("utf-8"))
        _load_params(self, payload, allow_partial=allow_partial)


def ppo_update_market(mlp, obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf,
                      episode_lengths=None, gamma=0.99, lam=0.95, clip=0.2, epochs=4,
                      minibatch=256, lr=3e-4, entropy_coef=0.01, value_coef=0.5, max_grad_norm=0.5):
    T = len(rew_buf)
    adv, ret = _compute_gae(rew_buf, val_buf, done_buf, episode_lengths, gamma, lam)
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)

    total_policy = 0.0
    total_value = 0.0
    total_entropy = 0.0
    n_updates = 0

    obs = np.array(obs_buf, dtype=np.float64)
    act = np.array(act_buf, dtype=np.int64)
    old_logp = np.array(logp_buf, dtype=np.float64)

    idx = np.arange(T)
    for _ in range(epochs):
        np.random.shuffle(idx)
        for start in range(0, T, minibatch):
            batch = idx[start:start + minibatch]
            if len(batch) == 0:
                continue
            bx = obs[batch]
            ba = act[batch]
            bold = old_logp[batch]
            badv = adv[batch]
            bret = ret[batch]

            out = mlp.forward(bx)
            h2 = out["h2"]
            lm = out["lm"]
            lv = out["lv"]

            lm -= lm.max(axis=1, keepdims=True)
            pm = np.exp(lm) / np.exp(lm).sum(axis=1, keepdims=True)
            logp = np.log(pm[np.arange(len(batch)), ba] + 1e-8)
            ratio = np.exp(logp - bold)

            clip_adv = np.clip(ratio, 1.0 - clip, 1.0 + clip) * badv[:, None]
            policy_loss = -np.minimum(ratio[:, None] * badv[:, None], clip_adv).mean()

            value_pred = lv[:, 0]
            value_loss = ((value_pred - bret) ** 2).mean()
            entropy = -(pm * np.log(pm + 1e-8)).sum(axis=1).mean()

            loss = policy_loss + value_coef * value_loss - entropy_coef * entropy
            loss_val = float(loss)

            d_policy = np.zeros_like(lm)
            d_policy[np.arange(len(batch)), ba] = -1.0 * badv / max(len(batch), 1)
            dlv = 2.0 * (value_pred - bret) / max(len(batch), 1)

            grads = mlp.backward(out, d_policy, dlv.reshape(-1, 1))
            mlp.adam_step(grads, lr=lr, max_grad_norm=max_grad_norm)

            total_policy += float(policy_loss)
            total_value += float(value_loss)
            total_entropy += float(entropy)
            n_updates += 1

    return {
        "policy_loss": total_policy / max(n_updates, 1),
        "value_loss": total_value / max(n_updates, 1),
        "entropy": total_entropy / max(n_updates, 1),
        "loss": loss_val,
    }


class MultiHeadMLP:
    """Trunk 75→256→256, then farmer + 12 hand task heads + market + value."""

    def __init__(self, seed=0):
        idle_bias = np.zeros(_TASK, dtype=np.float64)
        idle_bias[0] = 2.5  # strong IDLE prior → default scheduler
        # RESTOCK stays on the learned prior year-round; late DUMP is a
        # forward-time extra in _apply_phase_logits, not a second init bias.
        hand_bias = np.tile(idle_bias, _NHAND)
        market_bias = np.zeros(_MODE, dtype=np.float64)
        market_bias[3] = 1.5  # RESTOCK (buy seeds) over HOLD/DUMP
        self.params = {
            "W1": _orthogonal((_IN, _HID), gain=math.sqrt(2.0)),
            "b1": np.zeros(_HID, dtype=np.float64),
            "W2": _orthogonal((_HID, _HID), gain=math.sqrt(2.0)),
            "b2": np.zeros(_HID, dtype=np.float64),
            "Wf": _xavier((_HID, _TASK)),
            "bf": idle_bias.copy(),
            "Wh": _xavier((_HID, _TASK * _NHAND)),
            "bh": hand_bias,
            "Wm": _xavier((_HID, _MODE)),
            "bm": market_bias,
            "Wv": _xavier((_HID, 1)),
            "bv": np.zeros(1, dtype=np.float64),
        }
        self.opt = {
            "m": {k: np.zeros_like(v) for k, v in self.params.items()},
            "v": {k: np.zeros_like(v) for k, v in self.params.items()},
        }
        self.t = 0

    def forward(self, x):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        z1 = x @ self.params["W1"] + self.params["b1"]
        h1 = np.tanh(z1)
        z2 = h1 @ self.params["W2"] + self.params["b2"]
        h2 = np.tanh(z2)
        lf = h2 @ self.params["Wf"] + self.params["bf"]
        lh = h2 @ self.params["Wh"] + self.params["bh"]
        lm = h2 @ self.params["Wm"] + self.params["bm"]
        lf, lh, lm = _apply_phase_logits(lf, lh, lm, x)
        lv = h2 @ self.params["Wv"] + self.params["bv"]
        return {
            "x": x, "z1": z1, "h1": h1, "z2": z2, "h2": h2,
            "lf": lf, "lh": lh, "lm": lm, "lv": lv,
        }

    def act(self, obs, n_hands=12, sample=True, rng=None):
        f = _as_feats(obs)
        out = self.forward(f.reshape(1, -1))
        pf = _softmax(out["lf"][0])
        ph = _softmax(out["lh"][0].reshape(_NHAND, _TASK))
        pm = _softmax(out["lm"][0])
        rng = _rng(rng)
        n_hands = int(max(0, min(_NHAND, n_hands)))
        if sample:
            farmer = _choice(rng, _TASK, pf)
            hands = [_choice(rng, _TASK, ph[i]) for i in range(_NHAND)]
            mode = _choice(rng, _MODE, pm)
        else:
            farmer = int(np.argmax(pf))
            hands = [int(np.argmax(ph[i])) for i in range(_NHAND)]
            mode = int(np.argmax(pm))
        logp = float(np.log(pf[farmer] + 1e-8) + np.log(pm[mode] + 1e-8))
        for i in range(n_hands):
            logp += float(np.log(ph[i, hands[i]] + 1e-8))
        for i in range(n_hands, _NHAND):
            hands[i] = 0
        action = [farmer] + hands + [mode]
        val = float(out["lv"][0, 0])
        return action, logp, val, out

    def backward(self, cache, dlf, dlh, dlm, dlv):
        x, h1, h2 = cache["x"], cache["h1"], cache["h2"]
        dWf = h2.T @ dlf
        dbf = dlf.sum(axis=0)
        dWh = h2.T @ dlh
        dbh = dlh.sum(axis=0)
        dWm = h2.T @ dlm
        dbm = dlm.sum(axis=0)
        dWv = h2.T @ dlv
        dbv = dlv.sum(axis=0)
        dh2 = (dlf @ self.params["Wf"].T
               + dlh @ self.params["Wh"].T
               + dlm @ self.params["Wm"].T
               + dlv @ self.params["Wv"].T)
        dh2 *= (1.0 - h2 ** 2)
        dW2 = h1.T @ dh2
        db2 = dh2.sum(axis=0)
        dh1 = dh2 @ self.params["W2"].T
        dh1 *= (1.0 - h1 ** 2)
        dW1 = x.T @ dh1
        db1 = dh1.sum(axis=0)
        return {
            "W1": dW1, "b1": db1, "W2": dW2, "b2": db2,
            "Wf": dWf, "bf": dbf, "Wh": dWh, "bh": dbh,
            "Wm": dWm, "bm": dbm, "Wv": dWv, "bv": dbv,
        }

    def adam_step(self, grads, lr=3e-4, beta1=0.9, beta2=0.999, eps=1e-5, max_grad_norm=0.5):
        self.t += 1
        total_norm = 0.0
        for g in grads.values():
            total_norm += float(np.sum(g * g))
        total_norm = math.sqrt(total_norm)
        clip = max_grad_norm / (total_norm + 1e-8)
        if clip < 1.0:
            for k in grads:
                grads[k] *= clip
        for k, g in grads.items():
            self.opt["m"][k] = beta1 * self.opt["m"][k] + (1 - beta1) * g
            self.opt["v"][k] = beta2 * self.opt["v"][k] + (1 - beta2) * (g * g)
            m_hat = self.opt["m"][k] / (1 - beta1 ** self.t)
            v_hat = self.opt["v"][k] / (1 - beta2 ** self.t)
            self.params[k] -= lr * m_hat / (np.sqrt(v_hat) + eps)

    def save(self, path):
        payload = {k: v.astype(np.float64).tolist() for k, v in self.params.items()}
        payload["t"] = int(self.t)
        payload["arch"] = "multi"
        blob = zlib.compress(json.dumps(payload).encode("utf-8"))
        with open(path, "wb") as f:
            f.write(blob)

    def load(self, path, allow_partial=True):
        with open(path, "rb") as f:
            payload = json.loads(zlib.decompress(f.read()).decode("utf-8"))
        _load_params(self, payload, allow_partial=allow_partial,
                     aliases={"Wf": "Wt", "bf": "bt"})


def ppo_update_multihead(mlp, obs_buf, act_buf, logp_buf, rew_buf, val_buf, done_buf,
                         n_hands_buf=None, episode_lengths=None, gamma=0.997, lam=0.95,
                         clip=0.2, epochs=3, minibatch=512, lr=3e-4, entropy_coef=0.003,
                         value_coef=0.5, max_grad_norm=0.5):
    T = len(rew_buf)
    adv, ret = _compute_gae(rew_buf, val_buf, done_buf, episode_lengths, gamma, lam)
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)

    obs = np.array(obs_buf, dtype=np.float64)
    act = np.array(act_buf, dtype=np.int64)
    if act.ndim == 1:
        raise ValueError("multihead actions must be length-14 sequences")
    if act.shape[1] < _ACT_MULTI:
        pad = np.zeros((act.shape[0], _ACT_MULTI - act.shape[1]), dtype=np.int64)
        act = np.concatenate([act, pad], axis=1)
    old_logp = np.array(logp_buf, dtype=np.float64)
    if n_hands_buf is None:
        nh = np.full(T, _NHAND, dtype=np.int64)
    else:
        nh = np.array(n_hands_buf, dtype=np.int64)

    farmer_a = act[:, 0]
    hands_a = act[:, 1:1 + _NHAND]
    mode_a = act[:, 1 + _NHAND]

    total_policy = 0.0
    total_value = 0.0
    total_entropy = 0.0
    n_updates = 0
    loss_val = 0.0

    idx = np.arange(T)
    for _ in range(epochs):
        np.random.shuffle(idx)
        for start in range(0, T, minibatch):
            batch = idx[start:start + minibatch]
            if len(batch) == 0:
                continue
            B = len(batch)
            bx = obs[batch]
            bf_a = farmer_a[batch]
            bh_a = hands_a[batch]
            bm_a = mode_a[batch]
            bnh = np.clip(nh[batch], 0, _NHAND)
            bold = old_logp[batch]
            badv = adv[batch]
            bret = ret[batch]

            out = mlp.forward(bx)
            pf = _softmax(out["lf"])
            ph = _softmax(out["lh"].reshape(B, _NHAND, _TASK))
            pm = _softmax(out["lm"])
            lv = out["lv"]

            logp_f = np.log(pf[np.arange(B), bf_a] + 1e-8)
            logp_m = np.log(pm[np.arange(B), bm_a] + 1e-8)
            logp_h_all = np.log(
                ph[np.arange(B)[:, None], np.arange(_NHAND)[None, :], bh_a] + 1e-8
            )
            hand_mask = (np.arange(_NHAND)[None, :] < bnh[:, None]).astype(np.float64)
            logp_h = (logp_h_all * hand_mask).sum(axis=1)
            logp = logp_f + logp_h + logp_m

            dlf, pl_f, ent_f, _ = _ppo_logits_grad(pf, bf_a, badv, logp, bold, clip, entropy_coef)
            dlm, pl_m, ent_m, _ = _ppo_logits_grad(pm, bm_a, badv, logp, bold, clip, entropy_coef)

            dlh = np.zeros((B, _NHAND * _TASK), dtype=np.float64)
            ent_h = 0.0
            pl_h = 0.0
            for i in range(_NHAND):
                active = hand_mask[:, i]
                dli, pli, enti, _ = _ppo_logits_grad(
                    ph[:, i, :], bh_a[:, i], badv * active, logp, bold, clip, entropy_coef,
                )
                dli *= active[:, None]
                dlh[:, i * _TASK:(i + 1) * _TASK] = dli
                ent_h += enti * float(active.mean())
                pl_h += pli * float(active.mean())

            value_pred = lv[:, 0]
            value_loss = ((value_pred - bret) ** 2).mean()
            dlv = (value_coef * 2.0 * (value_pred - bret) / max(B, 1)).reshape(-1, 1)

            n_active = 2.0 + hand_mask.mean() * _NHAND
            policy_loss = (pl_f + pl_m + pl_h) / max(n_active, 1.0)
            entropy = ent_f + ent_m + ent_h
            loss_val = float(policy_loss + value_coef * value_loss - entropy_coef * entropy)

            grads = mlp.backward(out, dlf, dlh, dlm, dlv)
            mlp.adam_step(grads, lr=lr, max_grad_norm=max_grad_norm)

            total_policy += float(policy_loss)
            total_value += float(value_loss)
            total_entropy += float(entropy)
            n_updates += 1

    return {
        "policy_loss": total_policy / max(n_updates, 1),
        "value_loss": total_value / max(n_updates, 1),
        "entropy": total_entropy / max(n_updates, 1),
        "loss": loss_val,
    }
