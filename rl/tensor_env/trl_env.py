"""TorchRL EnvBase over engine_t.EpisodeT: the device-agnostic batched env.

One KGTensorEnv is B lockstep two-player episodes with the learner on one
seat and a scripted/frozen opponent on the other, exposed as a single-agent
TorchRL environment of batch_size [B] (the VMAS/Brax pattern: the simulator
itself is the vectorization; no ParallelEnv processes anywhere). The same
class runs on CPU and CUDA -- `device` is the only switch, which is what
finally merges the rl-baseline (CPU) and tensorize (GPU) lines.

Semantics are train_t.py's collect() verbatim:
  * obs        = features_t.encode_t(ep, seat)            (B, 4867) float32
  * masks      = features_t.masks_t(ep, seat)             (B, 23/22) bool
  * action     = (farmer, market) int64 head indices, stacked (B, 2)
  * opponent   = opponents_t.starter_indices (or a frozen ActorNet, argmax
                 over masked logits -- the exported-agent behaviour)
  * reward     = (net_worth_t(s') - net_worth_t(s)) / 3000, float64 math
                 rounded once to float32, plus win_bonus * {+1,-1,0} by
                 final money at the terminal step
  * episodes are fixed-length (episode_steps), all lanes terminate together,
    so the terminal bootstrap is exactly zero and every _reset is global.
  * seeds: base_seed * 1_000_003 + episode_index * B + lane, the train_t
    derivation, so runs are reproducible given (base_seed, B).

`money` / `opp_money` ride along as observation entries (never fed to the
network) so the trainer can read win rates off the collected batch.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import torch
from tensordict import TensorDict
from torchrl.data import Binary, Composite, MultiCategorical, Unbounded
from torchrl.envs import EnvBase

import actions as A
import obs as O
import engine_t
import engine_t_idx  # noqa: F401  (attaches EpisodeT.step_idx)
import features_t
import opponents_t
import potential_t
from trl_policy import ActorNet, NEG


class FrozenPolicyOpponent:
    """A past checkpoint / exported weights.npz played greedily (argmax over
    masked logits) -- the behaviour of an exported numpy agent, so league
    members and submissions are represented faithfully on device."""

    def __init__(self, path, device="cpu"):
        if path.endswith(".npz"):
            w = dict(np.load(path))
            sd = {"l1.weight": w["l1w"], "l1.bias": w["l1b"],
                  "l2.weight": w["l2w"], "l2.bias": w["l2b"],
                  "farmer.weight": w["fw"], "farmer.bias": w["fb"],
                  "market.weight": w["mw"], "market.bias": w["mb"]}
            sd = {k: torch.as_tensor(v) for k, v in sd.items()}
        else:
            ck = torch.load(path, map_location="cpu", weights_only=False)
            full = ck.get("model") or ck.get("state_dict")
            sd = {k: v for k, v in full.items()
                  if k.split(".")[0] in ("l1", "l2", "farmer", "market")}
        h1, obs_dim = sd["l1.weight"].shape
        h2 = sd["l2.weight"].shape[0]
        net = ActorNet(obs_dim, sd["farmer.weight"].shape[0],
                       sd["market.weight"].shape[0], h1, h2)
        net.load_state_dict(sd)
        self.net = net.to(device).eval()

    @torch.no_grad()
    def __call__(self, ep, player):
        x = features_t.encode_t(ep, player)
        fm, mm = features_t.masks_t(ep, player)
        fl, ml = self.net(x)
        fa = fl.masked_fill(~fm, NEG).argmax(-1)
        ma = ml.masked_fill(~mm, NEG).argmax(-1)
        return fa, ma


def _make_opponent(spec, device):
    if spec == "starter" or spec is None:
        return opponents_t.starter_indices
    return FrozenPolicyOpponent(spec, device)


class KGTensorEnv(EnvBase):
    batch_locked = True

    def __init__(self, B, device="cpu", seat=0, alternate_seat=False,
                 episode_steps=720, base_seed=0, opponent="starter",
                 win_bonus=3.0):
        super().__init__(device=torch.device(device),
                         batch_size=torch.Size([int(B)]))
        self.B = int(B)
        self.seat = int(seat)
        self.alternate_seat = bool(alternate_seat)
        self.episode_steps = int(episode_steps)
        self.base_seed = int(base_seed)
        self.win_bonus = float(win_bonus)
        self.opp_fn = _make_opponent(opponent, self.device)
        self._ep = None
        self._episode_index = 0
        self._prev_w = None

        bs, dev = self.batch_size, self.device
        self.observation_spec = Composite(
            observation=Unbounded(shape=(*bs, O.OBS_DIM),
                                  dtype=torch.float32, device=dev),
            farmer_mask=Binary(n=A.N_FARMER, shape=(*bs, A.N_FARMER),
                               dtype=torch.bool, device=dev),
            market_mask=Binary(n=A.N_MARKET, shape=(*bs, A.N_MARKET),
                               dtype=torch.bool, device=dev),
            money=Unbounded(shape=(*bs,), dtype=torch.float64, device=dev),
            opp_money=Unbounded(shape=(*bs,), dtype=torch.float64, device=dev),
            shape=bs, device=dev)
        self.action_spec = MultiCategorical(
            nvec=[A.N_FARMER, A.N_MARKET], shape=(*bs, 2),
            dtype=torch.int64, device=dev)
        self.reward_spec = Unbounded(shape=(*bs, 1), dtype=torch.float32,
                                     device=dev)
        self.full_done_spec = Composite(
            done=Binary(n=1, shape=(*bs, 1), dtype=torch.bool, device=dev),
            terminated=Binary(n=1, shape=(*bs, 1), dtype=torch.bool,
                              device=dev),
            shape=bs, device=dev)

    # -- helpers -------------------------------------------------------------

    def _obs_td(self):
        ep, seat = self._ep, self.seat
        x = features_t.encode_t(ep, seat)
        fm, mm = features_t.masks_t(ep, seat)
        return TensorDict(
            {"observation": x, "farmer_mask": fm, "market_mask": mm,
             "money": ep.money[:, seat].clone(),
             "opp_money": ep.money[:, 1 - seat].clone()},
            batch_size=self.batch_size, device=self.device)

    # -- EnvBase hooks -------------------------------------------------------

    def _reset(self, tensordict, **kwargs):
        if tensordict is not None and "_reset" in tensordict.keys():
            assert bool(tensordict["_reset"].all()), \
                "lanes terminate in lockstep; partial resets cannot happen"
        if self.alternate_seat and self._episode_index > 0:
            self.seat = 1 - self.seat
        seeds = [self.base_seed * 1_000_003 + self._episode_index * self.B + i
                 for i in range(self.B)]
        self._episode_index += 1
        self._ep = engine_t.EpisodeT(seeds, episode_steps=self.episode_steps,
                                     device=self.device)
        self._prev_w = potential_t.net_worth_t(self._ep, self.seat)
        return self._obs_td()

    def _step(self, tensordict):
        ep, seat = self._ep, self.seat
        opp = 1 - seat
        action = tensordict["action"]
        fa, ma = action[..., 0], action[..., 1]
        ofa, oma = self.opp_fn(ep, opp)
        if seat == 0:
            f_idx = torch.stack([fa, ofa], 1)
            m_idx = torch.stack([ma, oma], 1)
        else:
            f_idx = torch.stack([ofa, fa], 1)
            m_idx = torch.stack([oma, ma], 1)
        ep.step_idx(f_idx, m_idx)
        w = potential_t.net_worth_t(ep, seat)
        r = (w - self._prev_w) * (1.0 / 3000.0)
        self._prev_w = w
        if ep.done:
            mine, theirs = ep.money[:, seat], ep.money[:, opp]
            win = ((mine > theirs).to(torch.float64)
                   - (mine < theirs).to(torch.float64))
            r = r + self.win_bonus * win
        out = self._obs_td()
        done = torch.full((*self.batch_size, 1), ep.done, dtype=torch.bool,
                          device=self.device)
        out["reward"] = r.to(torch.float32).unsqueeze(-1)
        out["done"] = done
        out["terminated"] = done
        return out

    def _set_seed(self, seed):
        if seed is not None:
            self.base_seed = int(seed)
        return seed
