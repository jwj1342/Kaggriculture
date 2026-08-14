"""Two-head masked MLP policy + value, and its numpy export.

Trunk:  obs (OBS_DIM) -> 512 -> 256
Heads:  farmer logits (N_FARMER), market logits (N_MARKET), value (1)

Heads are zero-init so an untrained policy is uniform over *legal* actions --
exploration starts where the masks point, not at a random corner of logit
space. Export writes the exact arrays the numpy forward in the exported agent
expects; keep the two in sync by construction (export_agent.py owns both).
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
        self.value = _ortho(nn.Linear(hidden2, 1), 1.0)

    def trunk(self, x):
        h = torch.relu(self.l1(x))
        return torch.relu(self.l2(h))

    def forward(self, x, fmask, mmask):
        h = self.trunk(x)
        flog = self.farmer(h).masked_fill(~fmask, -1e9)
        mlog = self.market(h).masked_fill(~mmask, -1e9)
        return Categorical(logits=flog), Categorical(logits=mlog), self.value(h).squeeze(-1)

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
