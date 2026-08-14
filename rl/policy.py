"""Two-head masked MLP policy + value, and its numpy export.

Policy trunk:  obs (OBS_DIM) -> 512 -> 256 -> farmer / market logits
Value net:     obs (OBS_DIM) -> 256 -> 256 -> value (1), fully separate.

The value net shares NOTHING with the policy trunk, deliberately: with a
shared trunk, a value-only warm-up after behaviour cloning still backprops
through the trunk and silently destroys the cloned policy -- measured here as
a 30k-money teacher collapsing to ~$200 after five value iterations. Separate
parameters make --freeze-policy-until actually freeze the policy.

Heads are near-zero-init so an untrained policy is uniform over *legal*
actions. export_npz writes exactly what the numpy forward in the exported
agent expects (policy side only; the value net never ships).
"""

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Categorical


def _ortho(layer, gain):
    nn.init.orthogonal_(layer.weight, gain)
    nn.init.constant_(layer.bias, 0.0)
    return layer


class Policy(nn.Module):
    def __init__(self, obs_dim, n_farmer, n_market, hidden1=512, hidden2=256):
        super().__init__()
        self.l1 = _ortho(nn.Linear(obs_dim, hidden1), np.sqrt(2))
        self.l2 = _ortho(nn.Linear(hidden1, hidden2), np.sqrt(2))
        self.farmer = _ortho(nn.Linear(hidden2, n_farmer), 1e-4)
        self.market = _ortho(nn.Linear(hidden2, n_market), 1e-4)
        self.v1 = _ortho(nn.Linear(obs_dim, 256), np.sqrt(2))
        self.v2 = _ortho(nn.Linear(256, 256), np.sqrt(2))
        self.value = _ortho(nn.Linear(256, 1), 1.0)

    def trunk(self, x):
        h = torch.relu(self.l1(x))
        return torch.relu(self.l2(h))

    def value_of(self, x):
        h = torch.relu(self.v1(x))
        h = torch.relu(self.v2(h))
        return self.value(h).squeeze(-1)

    def forward(self, x, fmask, mmask):
        h = self.trunk(x)
        flog = self.farmer(h).masked_fill(~fmask, -1e9)
        mlog = self.market(h).masked_fill(~mmask, -1e9)
        return Categorical(logits=flog), Categorical(logits=mlog), self.value_of(x)

    @torch.no_grad()
    def act(self, x, fmask, mmask, deterministic=False):
        fd, md, v = self(x, fmask, mmask)
        if deterministic:
            fa, ma = fd.logits.argmax(-1), md.logits.argmax(-1)
        else:
            fa, ma = fd.sample(), md.sample()
        logp = fd.log_prob(fa) + md.log_prob(ma)
        return fa, ma, logp, v

    def evaluate(self, x, fmask, mmask, fa, ma):
        fd, md, v = self(x, fmask, mmask)
        logp = fd.log_prob(fa) + md.log_prob(ma)
        entropy = fd.entropy() + md.entropy()
        return logp, entropy, v

    def export_npz(self, path):
        w = {
            "l1w": self.l1.weight.detach().cpu().numpy(),
            "l1b": self.l1.bias.detach().cpu().numpy(),
            "l2w": self.l2.weight.detach().cpu().numpy(),
            "l2b": self.l2.bias.detach().cpu().numpy(),
            "fw": self.farmer.weight.detach().cpu().numpy(),
            "fb": self.farmer.bias.detach().cpu().numpy(),
            "mw": self.market.weight.detach().cpu().numpy(),
            "mb": self.market.bias.detach().cpu().numpy(),
        }
        np.savez(path, **{k: v.astype(np.float32) for k, v in w.items()})
