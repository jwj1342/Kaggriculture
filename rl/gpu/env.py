"""Batched GPU training environment wrapping the tensor engine."""

import torch

from . import constants as C
from .decode import decode_scripted, decode_starter, decode_tasks, merge_actions
from .engine import step
from .obs import encode, relative_phi, shaped_reward
from .state import new_state
from .tables import Tables


class KaggGpuEnv:
    """B parallel games on `device`. Player 0 is the learner.

    Day-end weeds/shops match the official Random stream. Farm-hand count can
    follow recorded actions up to ENGINE_HAND_CAP (32; official is uncapped).
    Submissions still run the official interpreter; GPU win rate is not a
    ladder score until verify.py is green on the agents you care about.
    """

    def __init__(self, batch=256, device="cpu", opponent="starter"):
        self.batch = int(batch)
        self.device = torch.device(device)
        self.opponent = opponent
        self.T = Tables(self.device)
        self.st = None

    def reset(self, seeds=None):
        self.st = new_state(self.batch, self.device, seeds=seeds)
        self.st.phi = relative_phi(self.st, self.T, player=0)
        obs = encode(self.st, self.T, player=0)
        # Clone: st.n_hands is mutated in-place. A view kept across 720 steps
        # would all read the terminal count (0 after end-of-day fire).
        return obs, self.st.n_hands[:, 0].clone()

    def _opp_actions(self):
        if self.opponent == "scripted":
            return decode_scripted(self.st, 1, self.T)
        return decode_starter(self.st, 1, self.T)

    def step(self, tasks):
        """tasks: [B, 14] int64 (farmer + 12 hands + market_mode) for player 0."""
        if self.st is None:
            raise RuntimeError("call reset() first")
        tasks = tasks.to(self.device)
        a0 = decode_tasks(self.st, tasks, 0, self.T)
        a1 = self._opp_actions()
        act = merge_actions(a0, a1)
        step(self.st, act, self.T)
        rew, phi = shaped_reward(self.st, self.st.phi, self.T, player=0)
        self.st.phi = phi
        obs = encode(self.st, self.T, player=0)
        info = {
            "n_hands": self.st.n_hands[:, 0].clone(),
            "money": self.st.money.clone(),
        }
        return obs, rew, self.st.done, info
