"""Two-head masked MLP policy + separate value net for the on-device loop (B4c).

Same structure as rl-baseline rl/policy.py (Policy): actor trunk
obs -> hidden1 -> hidden2 -> {farmer logits (23), market logits (22)} with
illegal actions masked to -1e9; critic obs -> 256 -> 256 -> 1 sharing NOTHING
with the actor (a value-only phase must not disturb the policy -- rl-baseline
measured a shared trunk destroying a cloned policy). Orthogonal init, gain
sqrt(2) on hidden layers, 1e-4 on the two heads (an untrained policy is
uniform over *legal* actions), 1.0 on the value head.

API (everything stays on the input tensors' device):
    act(x, fm, mm, generator=None) -> (fa, ma, logp)      masked sampling
    evaluate(x, fm, mm, fa, ma)    -> (logp, entropy)      for the PPO ratio
    value(x)                       -> (B,)
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


def _ortho(layer, gain):
    nn.init.orthogonal_(layer.weight, gain)
    nn.init.constant_(layer.bias, 0.0)
    return layer


NEG = -1e9


class PolicyT(nn.Module):
    def __init__(self, obs_dim, n_farmer, n_market, hidden1=512, hidden2=256,
                 v_hidden=256):
        super().__init__()
        self.obs_dim, self.n_farmer, self.n_market = obs_dim, n_farmer, n_market
        self.l1 = _ortho(nn.Linear(obs_dim, hidden1), math.sqrt(2))
        self.l2 = _ortho(nn.Linear(hidden1, hidden2), math.sqrt(2))
        self.farmer = _ortho(nn.Linear(hidden2, n_farmer), 1e-4)
        self.market = _ortho(nn.Linear(hidden2, n_market), 1e-4)
        self.v1 = _ortho(nn.Linear(obs_dim, v_hidden), math.sqrt(2))
        self.v2 = _ortho(nn.Linear(v_hidden, v_hidden), math.sqrt(2))
        self.vout = _ortho(nn.Linear(v_hidden, 1), 1.0)

    # -- actor --------------------------------------------------------------
    def logits(self, x, fm, mm):
        h = torch.relu(self.l1(x))
        h = torch.relu(self.l2(h))
        flog = self.farmer(h).masked_fill(~fm, NEG)
        mlog = self.market(h).masked_fill(~mm, NEG)
        return flog, mlog

    @torch.no_grad()
    def act(self, x, fm, mm, generator=None, deterministic=False):
        flog, mlog = self.logits(x, fm, mm)
        flp = F.log_softmax(flog, -1)
        mlp = F.log_softmax(mlog, -1)
        if deterministic:
            fa, ma = flog.argmax(-1), mlog.argmax(-1)
        else:
            fa = torch.multinomial(flp.exp(), 1, generator=generator).squeeze(-1)
            ma = torch.multinomial(mlp.exp(), 1, generator=generator).squeeze(-1)
        logp = (flp.gather(-1, fa.unsqueeze(-1)).squeeze(-1)
                + mlp.gather(-1, ma.unsqueeze(-1)).squeeze(-1))
        return fa, ma, logp

    def evaluate(self, x, fm, mm, fa, ma):
        flog, mlog = self.logits(x, fm, mm)
        flp = F.log_softmax(flog, -1)
        mlp = F.log_softmax(mlog, -1)
        logp = (flp.gather(-1, fa.unsqueeze(-1)).squeeze(-1)
                + mlp.gather(-1, ma.unsqueeze(-1)).squeeze(-1))
        # masked entries: p = exp(-1e9 - lse) == 0 exactly, so p*logp == -0.0
        entropy = -(flp.exp() * flp).sum(-1) - (mlp.exp() * mlp).sum(-1)
        return logp, entropy

    # -- critic -------------------------------------------------------------
    def value(self, x):
        h = torch.relu(self.v1(x))
        h = torch.relu(self.v2(h))
        return self.vout(h).squeeze(-1)

    # -- export (rl-baseline export_agent contract: policy side only) ------
    def state_np(self):
        w = {
            "l1w": self.l1.weight, "l1b": self.l1.bias,
            "l2w": self.l2.weight, "l2b": self.l2.bias,
            "fw": self.farmer.weight, "fb": self.farmer.bias,
            "mw": self.market.weight, "mb": self.market.bias,
        }
        return {k: v.detach().cpu().float().numpy() for k, v in w.items()}
