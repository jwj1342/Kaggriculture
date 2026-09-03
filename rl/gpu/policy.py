"""PyTorch multi-head actor-critic matching rl.ppo.MultiHeadMLP."""

import json
import math
import zlib

import torch
import torch.nn as nn
import torch.nn.functional as F

from . import constants as C

from ..action_space import (
    PHASE_EARLY_LAST_DAY, PHASE_LATE_FIRST_DAY, PHASE_MODE_BIAS, PHASE_TASK_BIAS,
    STEP_FEATURE_INDEX,
)

_IN = C.FEATURE_DIM
_HID = 256
_TASK = C.N_TASK
_MODE = C.N_MODE
_NHAND = C.HAND_CAP


def _orthogonal_(w, gain=1.0):
    nn.init.orthogonal_(w, gain=gain)


class MultiHeadActor(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(_IN, _HID)
        self.fc2 = nn.Linear(_HID, _HID)
        self.head_f = nn.Linear(_HID, _TASK)
        self.head_h = nn.Linear(_HID, _TASK * _NHAND)
        self.head_m = nn.Linear(_HID, _MODE)
        self.head_v = nn.Linear(_HID, 1)
        self.register_buffer(
            "phase_task_bias",
            torch.tensor(PHASE_TASK_BIAS, dtype=torch.float32),
        )
        self.register_buffer(
            "phase_mode_bias",
            torch.tensor(PHASE_MODE_BIAS, dtype=torch.float32),
        )
        self.reset_parameters()

    def reset_parameters(self):
        _orthogonal_(self.fc1.weight, gain=math.sqrt(2.0))
        _orthogonal_(self.fc2.weight, gain=math.sqrt(2.0))
        nn.init.zeros_(self.fc1.bias)
        nn.init.zeros_(self.fc2.bias)
        nn.init.xavier_uniform_(self.head_f.weight)
        nn.init.xavier_uniform_(self.head_h.weight)
        nn.init.xavier_uniform_(self.head_m.weight)
        nn.init.xavier_uniform_(self.head_v.weight)
        idle = torch.zeros(_TASK)
        idle[0] = 2.5
        with torch.no_grad():
            self.head_f.bias.copy_(idle)
            self.head_h.bias.copy_(idle.repeat(_NHAND))
            mb = torch.zeros(_MODE)
            mb[3] = 1.5
            self.head_m.bias.copy_(mb)
            self.head_v.bias.zero_()

    def forward(self, x):
        h = torch.tanh(self.fc1(x))
        h = torch.tanh(self.fc2(h))
        lf = self.head_f(h)
        lh = self.head_h(h).view(-1, _NHAND, _TASK)
        lm = self.head_m(h)
        lv = self.head_v(h).squeeze(-1)
        ph = _phase_from_obs(x)
        lf = lf + self.phase_task_bias[ph]
        lh = lh + self.phase_task_bias[ph][:, None, :]
        lm = lm + self.phase_mode_bias[ph]
        return lf, lh, lm, lv

    @torch.no_grad()
    def act(self, obs, n_hands, sample=True):
        lf, lh, lm, lv = self.forward(obs)
        pf = F.softmax(lf, dim=-1)
        ph = F.softmax(lh, dim=-1)
        pm = F.softmax(lm, dim=-1)
        B = obs.shape[0]
        if sample:
            farmer = torch.multinomial(pf, 1).squeeze(-1)
            hands = torch.multinomial(ph.reshape(B * _NHAND, _TASK), 1).reshape(B, _NHAND)
            mode = torch.multinomial(pm, 1).squeeze(-1)
        else:
            farmer = pf.argmax(-1)
            hands = ph.argmax(-1)
            mode = pm.argmax(-1)
        n_hands = n_hands.long().clamp(0, _NHAND)
        hands = torch.where(
            torch.arange(_NHAND, device=obs.device)[None, :] < n_hands[:, None],
            hands, torch.zeros_like(hands),
        )
        logp = _logp(lf, lh, lm, farmer, hands, mode, n_hands)
        tasks = torch.cat([farmer[:, None], hands, mode[:, None]], dim=-1)
        return tasks, logp, lv

    def numpy_params(self):
        """Map to rl.ppo.MultiHeadMLP key layout (W is [in, out])."""
        p = {
            "W1": self.fc1.weight.detach().T.contiguous().cpu().numpy(),
            "b1": self.fc1.bias.detach().cpu().numpy(),
            "W2": self.fc2.weight.detach().T.contiguous().cpu().numpy(),
            "b2": self.fc2.bias.detach().cpu().numpy(),
            "Wf": self.head_f.weight.detach().T.contiguous().cpu().numpy(),
            "bf": self.head_f.bias.detach().cpu().numpy(),
            "Wh": self.head_h.weight.detach().T.contiguous().cpu().numpy(),
            "bh": self.head_h.bias.detach().cpu().numpy(),
            "Wm": self.head_m.weight.detach().T.contiguous().cpu().numpy(),
            "bm": self.head_m.bias.detach().cpu().numpy(),
            "Wv": self.head_v.weight.detach().T.contiguous().cpu().numpy(),
            "bv": self.head_v.bias.detach().cpu().numpy(),
        }
        return p

    def load_numpy(self, payload, allow_partial=True):
        mapping = {
            "W1": (self.fc1.weight, True), "b1": (self.fc1.bias, False),
            "W2": (self.fc2.weight, True), "b2": (self.fc2.bias, False),
            "Wf": (self.head_f.weight, True), "bf": (self.head_f.bias, False),
            "Wh": (self.head_h.weight, True), "bh": (self.head_h.bias, False),
            "Wm": (self.head_m.weight, True), "bm": (self.head_m.bias, False),
            "Wv": (self.head_v.weight, True), "bv": (self.head_v.bias, False),
        }
        aliases = {"Wf": "Wt", "bf": "bt"}
        import numpy as np
        with torch.no_grad():
            for k, (param, transpose) in mapping.items():
                src = k if k in payload else aliases.get(k)
                if src is None or src not in payload:
                    if allow_partial:
                        continue
                    raise KeyError(k)
                arr = np.array(payload[src], dtype="float32")
                t = torch.from_numpy(arr)
                if transpose:
                    t = t.T.contiguous()
                if t.shape != param.shape:
                    if allow_partial:
                        continue
                    raise ValueError(f"{k}: {tuple(t.shape)} vs {tuple(param.shape)}")
                param.copy_(t.to(param.device, dtype=param.dtype))

    def save(self, path):
        payload = {k: v.astype("float64").tolist() for k, v in self.numpy_params().items()}
        payload["t"] = 0
        payload["arch"] = "multi"
        blob = zlib.compress(json.dumps(payload).encode("utf-8"))
        with open(path, "wb") as f:
            f.write(blob)

    def load(self, path, allow_partial=True):
        with open(path, "rb") as f:
            payload = json.loads(zlib.decompress(f.read()).decode("utf-8"))
        self.load_numpy(payload, allow_partial=allow_partial)


def _phase_from_obs(x):
    """0 early / 1 mid / 2 late from obs[..., 4] = step/720."""
    day = (x[..., STEP_FEATURE_INDEX].clamp(0, 1) * 30.0).floor().long()
    return torch.where(
        day >= PHASE_LATE_FIRST_DAY, 2, torch.where(day <= PHASE_EARLY_LAST_DAY, 0, 1),
    )


def _logp(lf, lh, lm, farmer, hands, mode, n_hands):
    lp_f = F.log_softmax(lf, dim=-1).gather(-1, farmer.unsqueeze(-1)).squeeze(-1)
    lp_m = F.log_softmax(lm, dim=-1).gather(-1, mode.unsqueeze(-1)).squeeze(-1)
    lp_h = F.log_softmax(lh, dim=-1).gather(-1, hands.unsqueeze(-1)).squeeze(-1)
    mask = torch.arange(_NHAND, device=lf.device)[None, :] < n_hands[:, None]
    return lp_f + lp_m + (lp_h * mask).sum(-1)


def compute_gae(rew, val, done, gamma=0.997, lam=0.95):
    """rew/val/done: [T, B]. val includes bootstrap at T (zeros if done)."""
    T, B = rew.shape
    adv = torch.zeros_like(rew)
    last = torch.zeros(B, device=rew.device, dtype=rew.dtype)
    # val is [T] or [T+1]
    if val.shape[0] == T + 1:
        v = val
    else:
        v = torch.cat([val, torch.zeros(1, B, device=val.device, dtype=val.dtype)], dim=0)
    for t in reversed(range(T)):
        nxt = torch.where(done[t], torch.zeros_like(last), v[t + 1])
        delta = rew[t] + gamma * nxt - v[t]
        last = delta + gamma * lam * torch.where(done[t], torch.zeros_like(last), last)
        adv[t] = last
    ret = adv + v[:T]
    return adv, ret


def _policy_loss(logp, old_logp, adv, algo="ppo", clip=0.2):
    if algo == "ppo":
        ratio = (logp - old_logp).exp()
        surr1 = ratio * adv
        surr2 = ratio.clamp(1.0 - clip, 1.0 + clip) * adv
        return -torch.min(surr1, surr2).mean()
    return -(logp * adv).mean()


def ppo_update(model, opt, obs, act, old_logp, adv, ret, n_hands,
               clip=0.2, entropy_coef=0.003, value_coef=0.5, epochs=3,
               minibatch=2048, max_grad_norm=0.5, algo="ppo"):
    T, B = adv.shape
    N = T * B
    obs = obs.reshape(N, -1)
    act = act.reshape(N, -1)
    old_logp = old_logp.reshape(N)
    adv = adv.reshape(N)
    ret = ret.reshape(N)
    n_hands = n_hands.reshape(N)
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)

    farmer = act[:, 0].long()
    hands = act[:, 1:1 + _NHAND].long()
    mode = act[:, 1 + _NHAND].long()

    idx = torch.randperm(N, device=obs.device)
    stats = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
    n_upd = 0
    for _ in range(epochs):
        idx = idx[torch.randperm(N, device=obs.device)]
        for start in range(0, N, minibatch):
            b = idx[start:start + minibatch]
            if b.numel() == 0:
                continue
            lf, lh, lm, lv = model(obs[b])
            logp = _logp(lf, lh, lm, farmer[b], hands[b], mode[b], n_hands[b])
            pol = _policy_loss(logp, old_logp[b], adv[b], algo=algo, clip=clip)
            val_loss = ((lv - ret[b]) ** 2).mean()
            ent_f = -(F.softmax(lf, -1) * F.log_softmax(lf, -1)).sum(-1).mean()
            ent_m = -(F.softmax(lm, -1) * F.log_softmax(lm, -1)).sum(-1).mean()
            ent_h = -(F.softmax(lh, -1) * F.log_softmax(lh, -1)).sum(-1)
            hmask = torch.arange(_NHAND, device=obs.device)[None, :] < n_hands[b][:, None]
            ent_h = (ent_h * hmask).sum(-1).mean()
            ent = ent_f + ent_m + ent_h
            loss = pol + value_coef * val_loss - entropy_coef * ent
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            opt.step()
            stats["policy_loss"] += float(pol.detach())
            stats["value_loss"] += float(val_loss.detach())
            stats["entropy"] += float(ent.detach())
            n_upd += 1
    n_upd = max(n_upd, 1)
    return {k: v / n_upd for k, v in stats.items()}
