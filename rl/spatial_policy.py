"""CNN and Transformer trunks over the packed board observation.

Packed x: [global FEATURE_DIM | own CH*100 | opp CH*100]. Heads match
rl.ppo.MultiHeadMLP (13 tasks × farmer+12 hands, 4 market modes, value)
including the calendar-day phase logit bias.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .action_space import (
    PHASE_EARLY_LAST_DAY, PHASE_LATE_FIRST_DAY, PHASE_MODE_BIAS, PHASE_TASK_BIAS,
    STEP_FEATURE_INDEX,
)
from .board_obs import BOARD, BOARD_FLAT, CH_PER_FARM, N_FARM, PACKED_DIM
from .features import FEATURE_DIM
from .ppo import _MODE, _NHAND, _TASK

_HID = 256
_SPATIAL = 64


def _phase_from_obs(x):
    day = (x[..., STEP_FEATURE_INDEX].clamp(0, 1) * 30.0).floor().long()
    return torch.where(
        day >= PHASE_LATE_FIRST_DAY, 2, torch.where(day <= PHASE_EARLY_LAST_DAY, 0, 1),
    )


def _split(x):
    g = x[..., :FEATURE_DIM]
    board = x[..., FEATURE_DIM:FEATURE_DIM + BOARD_FLAT]
    board = board.reshape(x.shape[0], N_FARM * CH_PER_FARM, BOARD, BOARD)
    return g, board


def _logp(lf, lh, lm, farmer, hands, mode, n_hands):
    lp_f = F.log_softmax(lf, dim=-1).gather(-1, farmer.unsqueeze(-1)).squeeze(-1)
    lp_m = F.log_softmax(lm, dim=-1).gather(-1, mode.unsqueeze(-1)).squeeze(-1)
    lp_h = F.log_softmax(lh, dim=-1).gather(-1, hands.unsqueeze(-1)).squeeze(-1)
    mask = torch.arange(_NHAND, device=lf.device)[None, :] < n_hands[:, None]
    return lp_f + lp_m + (lp_h * mask).sum(-1)


class _CNNEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        cin = N_FARM * CH_PER_FARM
        self.conv1 = nn.Conv2d(cin, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.out = nn.Linear(64, _SPATIAL)
        nn.init.kaiming_uniform_(self.conv1.weight, a=math.sqrt(5))
        nn.init.kaiming_uniform_(self.conv2.weight, a=math.sqrt(5))
        nn.init.zeros_(self.conv1.bias)
        nn.init.zeros_(self.conv2.bias)
        # Zero spatial readout so untrained policy is the IDLE/RESTOCK prior.
        nn.init.zeros_(self.out.weight)
        nn.init.zeros_(self.out.bias)

    def forward(self, board):
        h = torch.tanh(self.conv1(board))
        h = torch.tanh(self.conv2(h))
        h = h.mean(dim=(-1, -2))
        return torch.tanh(self.out(h))


class _TransformerEncoder(nn.Module):
    """100 own tiles + 100 opp tiles as tokens, CLS pooled."""

    def __init__(self, d=32, n_layers=2, n_heads=4):
        super().__init__()
        self.d = d
        n_tok = 1 + 2 * BOARD * BOARD
        self.proj = nn.Linear(CH_PER_FARM, d)
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        self.pos = nn.Parameter(torch.zeros(1, n_tok, d))
        layer = nn.TransformerEncoderLayer(
            d_model=d, nhead=n_heads, dim_feedforward=64,
            dropout=0.0, activation="gelu", batch_first=True, norm_first=True,
        )
        self.enc = nn.TransformerEncoder(
            layer, num_layers=n_layers, enable_nested_tensor=False,
        )
        self.out = nn.Linear(d, _SPATIAL)
        nn.init.orthogonal_(self.proj.weight, gain=math.sqrt(2.0))
        nn.init.zeros_(self.proj.bias)
        nn.init.zeros_(self.out.weight)
        nn.init.zeros_(self.out.bias)
        nn.init.trunc_normal_(self.pos, std=0.02)
        nn.init.zeros_(self.cls)

    def forward(self, board):
        B = board.shape[0]
        own = board[:, :CH_PER_FARM].flatten(2).transpose(1, 2)
        opp = board[:, CH_PER_FARM:].flatten(2).transpose(1, 2)
        tok = torch.cat([own, opp], dim=1)
        h = self.proj(tok)
        cls = self.cls.expand(B, -1, -1)
        h = torch.cat([cls, h], dim=1) + self.pos
        h = self.enc(h)
        return torch.tanh(self.out(h[:, 0]))


class SpatialActor(nn.Module):
    def __init__(self, net="cnn"):
        super().__init__()
        if net not in ("cnn", "transformer"):
            raise ValueError(f"unknown spatial net {net!r}")
        self.net = net
        self.encoder = _CNNEncoder() if net == "cnn" else _TransformerEncoder()
        self.fc1 = nn.Linear(FEATURE_DIM + _SPATIAL, _HID)
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
        nn.init.orthogonal_(self.fc1.weight, gain=math.sqrt(2.0))
        nn.init.orthogonal_(self.fc2.weight, gain=math.sqrt(2.0))
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
        if x.dim() == 1:
            x = x.unsqueeze(0)
        g, board = _split(x)
        z = torch.cat([g, self.encoder(board)], dim=-1)
        h = torch.tanh(self.fc1(z))
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
    def act(self, obs, n_hands, sample=True, greedy_frac=0.0, temperature=1.0):
        lf, lh, lm, lv = self.forward(obs)
        B = obs.shape[0]
        farmer_g = lf.argmax(-1)
        hands_g = lh.argmax(-1)
        mode_g = lm.argmax(-1)
        if not sample:
            farmer, hands, mode = farmer_g, hands_g, mode_g
        else:
            t = max(float(temperature), 1e-5)
            if t != 1.0:
                pf = F.softmax(lf / t, dim=-1)
                ph = F.softmax(lh / t, dim=-1)
                pm = F.softmax(lm / t, dim=-1)
            else:
                pf = F.softmax(lf, dim=-1)
                ph = F.softmax(lh, dim=-1)
                pm = F.softmax(lm, dim=-1)
            farmer = torch.multinomial(pf, 1).squeeze(-1)
            hands = torch.multinomial(ph.reshape(B * _NHAND, _TASK), 1).reshape(B, _NHAND)
            mode = torch.multinomial(pm, 1).squeeze(-1)
            g = float(greedy_frac)
            if g > 0.0:
                pick = torch.rand(B, device=obs.device) < g
                farmer = torch.where(pick, farmer_g, farmer)
                hands = torch.where(pick[:, None], hands_g, hands)
                mode = torch.where(pick, mode_g, mode)
        n_hands = n_hands.long().clamp(0, _NHAND)
        hands = torch.where(
            torch.arange(_NHAND, device=obs.device)[None, :] < n_hands[:, None],
            hands, torch.zeros_like(hands),
        )
        # log π of the taken action (unscaled). Mixture/temp collection is a
        # mild IS bias; PPO clip absorbs it. Exam is still argmax of π.
        logp = _logp(lf, lh, lm, farmer, hands, mode, n_hands)
        tasks = torch.cat([farmer[:, None], hands, mode[:, None]], dim=-1)
        return tasks, logp, lv

    def numpy_state(self):
        return {k: v.detach().cpu().float().numpy() for k, v in self.state_dict().items()}

    def load_numpy_state(self, payload):
        sd = {}
        for k, v in self.state_dict().items():
            if k not in payload:
                continue
            t = torch.as_tensor(payload[k], dtype=v.dtype)
            if tuple(t.shape) != tuple(v.shape):
                continue
            sd[k] = t
        self.load_state_dict(sd, strict=False)


def _policy_loss(logp, old_logp, adv, algo, clip):
    """PPO clipped surrogate, or A2C/REINFORCE ∇θ E[log π A]."""
    if algo == "ppo":
        ratio = (logp - old_logp).exp()
        surr1 = ratio * adv
        surr2 = ratio.clamp(1.0 - clip, 1.0 + clip) * adv
        return -torch.min(surr1, surr2).mean()
    return -(logp * adv).mean()


def policy_update_spatial(model, opt, obs, act, old_logp, adv, ret, n_hands,
                          algo="ppo", clip=0.2, entropy_coef=0.003, value_coef=0.5,
                          epochs=3, minibatch=512, max_grad_norm=0.5):
    N = adv.shape[0]
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)
    farmer = act[:, 0].long()
    hands = act[:, 1:1 + _NHAND].long()
    mode = act[:, 1 + _NHAND].long()
    n_hands = n_hands.long().clamp(0, _NHAND)
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
            pol = _policy_loss(logp, old_logp[b], adv[b], algo, clip)
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


def ppo_update_spatial(model, opt, obs, act, old_logp, adv, ret, n_hands,
                       clip=0.2, entropy_coef=0.003, value_coef=0.5, epochs=3,
                       minibatch=512, max_grad_norm=0.5, algo="ppo"):
    return policy_update_spatial(
        model, opt, obs, act, old_logp, adv, ret, n_hands,
        algo=algo, clip=clip, entropy_coef=entropy_coef, value_coef=value_coef,
        epochs=epochs, minibatch=minibatch, max_grad_norm=max_grad_norm,
    )
