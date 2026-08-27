"""Lightweight Semi-MDP over frozen low-level Kaggriculture controllers.

The high-level policy acts only at six strategic milestones plus the closing
phase.  Its actions are
explicit categoricals: keep following the frozen RL policy, or commit to one
of two validated state-closed route executors until the next milestone.  This
module owns the persistent Option lifecycle and emits variable-duration
transitions with an exact ``gamma ** tau`` discount.
"""

from __future__ import annotations

import enum
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn
from torch.distributions import Categorical

_HERE = Path(__file__).resolve().parent
_TENSOR = _HERE / "tensor_env"
for _path in (_HERE, _TENSOR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import barnyard_t  # noqa: E402
import engine_t  # noqa: E402
import features_t  # noqa: E402
import macro_audit  # noqa: E402
from trl_env import KGTensorEnv  # noqa: E402


class Option(enum.IntEnum):
    FOLLOW_POLICY = 0
    K01_ROUTE = 1
    K01_ROUTE_S34 = 2


OPTION_NAMES = tuple(option.name for option in Option)
N_OPTIONS = len(OPTION_NAMES)


class Termination(enum.IntEnum):
    NONE = 0
    STRATEGIC_TRIGGER = 1
    MILESTONE = 2
    TIMEOUT = 3
    EPISODE_END = 4


TERMINATION_NAMES = tuple(reason.name for reason in Termination)


@dataclass(frozen=True)
class Milestone:
    day: int
    land: int
    crops: int
    herd: int


# Measured from held-out k01_route_s34 seasons, not copied from the tape.  A
# route must meet both the calendar floor and the asset floor; FOLLOW_POLICY is
# evaluated over the same strategic interval and terminates at its calendar
# trigger so the controller receives a clean counterfactual choice.
MILESTONES = (
    Milestone(1, 1, 16, 4),
    Milestone(8, 2, 27, 7),
    Milestone(12, 3, 36, 12),
    Milestone(15, 3, 47, 13),
    Milestone(20, 3, 50, 13),
    Milestone(25, 3, 45, 13),
)


def _state_counts(ep, seat):
    return {
        "land": 1 + ep.quad_unlocked[:, seat].sum(-1).to(torch.int64),
        "crops": (ep.kind[:, seat] == engine_t.K_PLANT).sum(
            (-1, -2)).to(torch.int64),
        "herd": (ep.animal[:, seat] >= 0).sum(
            (-1, -2)).to(torch.int64),
    }


class OptionLifecycle:
    """Batched persistent state for one active Option per environment lane."""

    def __init__(self, lanes, obs_dim, device, gamma=0.999, timeout=240):
        self.B = int(lanes)
        self.device = torch.device(device)
        self.gamma = float(gamma)
        self.timeout = int(timeout)
        self.option_id = torch.full(
            (self.B,), -1, dtype=torch.int64, device=self.device)
        self.start_state = torch.zeros(
            (self.B, obs_dim), dtype=torch.float32, device=self.device)
        self.start_mask = torch.zeros(
            (self.B, N_OPTIONS), dtype=torch.bool, device=self.device)
        self.start_log_prob = torch.zeros(
            self.B, dtype=torch.float32, device=self.device)
        self.start_value = torch.zeros_like(self.start_log_prob)
        self.start_probs = torch.zeros(
            (self.B, N_OPTIONS), dtype=torch.float32, device=self.device)
        self.start_step = torch.zeros(
            self.B, dtype=torch.int64, device=self.device)
        self.elapsed = torch.zeros_like(self.start_step)
        self.discounted_reward = torch.zeros_like(self.start_log_prob)
        self.discount = torch.ones_like(self.start_log_prob)
        self.termination_reason = torch.full(
            (self.B,), int(Termination.NONE), dtype=torch.int64,
            device=self.device)
        self.stage = torch.zeros_like(self.start_step)
        self.last_option = torch.full_like(self.option_id, -1)
        self._target_day = torch.tensor(
            [m.day for m in MILESTONES], dtype=torch.int64,
            device=self.device)
        self._target_land = torch.tensor(
            [m.land for m in MILESTONES], dtype=torch.int64,
            device=self.device)
        self._target_crops = torch.tensor(
            [m.crops for m in MILESTONES], dtype=torch.int64,
            device=self.device)
        self._target_herd = torch.tensor(
            [m.herd for m in MILESTONES], dtype=torch.int64,
            device=self.device)

    @property
    def active(self):
        return self.option_id >= 0

    def start(self, lane_mask, option_id, state, action_mask, log_prob, value,
              probs, step):
        lane_mask = torch.as_tensor(
            lane_mask, dtype=torch.bool, device=self.device).view(self.B)
        if bool((self.active & lane_mask).any()):
            raise RuntimeError("cannot replace an Option before termination")
        self.option_id[lane_mask] = option_id[lane_mask]
        self.last_option[lane_mask] = option_id[lane_mask]
        self.start_state[lane_mask] = state[lane_mask]
        self.start_mask[lane_mask] = action_mask[lane_mask]
        self.start_log_prob[lane_mask] = log_prob[lane_mask]
        self.start_value[lane_mask] = value[lane_mask]
        self.start_probs[lane_mask] = probs[lane_mask]
        self.start_step[lane_mask] = int(step)
        self.elapsed[lane_mask] = 0
        self.discounted_reward[lane_mask] = 0.0
        self.discount[lane_mask] = 1.0
        self.termination_reason[lane_mask] = int(Termination.NONE)

    def add_reward(self, reward):
        active = self.active
        reward = torch.as_tensor(
            reward, dtype=torch.float32, device=self.device).view(self.B)
        self.discounted_reward[active] += self.discount[active] * reward[active]
        self.discount[active] *= self.gamma
        self.elapsed[active] += 1

    def termination(self, ep, seat):
        active = self.active
        reason = torch.full_like(self.option_id, int(Termination.NONE))
        if not bool(active.any()):
            return active, reason

        final_stage = self.stage >= len(MILESTONES)
        stage = self.stage.clamp(max=len(MILESTONES) - 1)
        target_day = self._target_day[stage]
        target_land = self._target_land[stage]
        target_crops = self._target_crops[stage]
        target_herd = self._target_herd[stage]
        counts = _state_counts(ep, seat)
        calendar = (ep._step >= target_day * ep.turns_per_day) & ~final_stage
        assets = ((counts["land"] >= target_land)
                  & (counts["crops"] >= target_crops)
                  & (counts["herd"] >= target_herd))
        follow = self.option_id == int(Option.FOLLOW_POLICY)
        route = active & ~follow
        trigger = active & follow & calendar
        milestone = route & calendar & assets
        timeout = active & (self.elapsed >= self.timeout)
        if ep.done:
            reason[active] = int(Termination.EPISODE_END)
        else:
            reason[trigger] = int(Termination.STRATEGIC_TRIGGER)
            reason[milestone] = int(Termination.MILESTONE)
            unresolved = reason == int(Termination.NONE)
            reason[timeout & unresolved] = int(Termination.TIMEOUT)
        return active & (reason != int(Termination.NONE)), reason

    def finish(self, lane_mask, reason):
        lane_mask = torch.as_tensor(
            lane_mask, dtype=torch.bool, device=self.device).view(self.B)
        self.termination_reason[lane_mask] = reason[lane_mask]
        nonterminal = lane_mask & (
            reason != int(Termination.EPISODE_END))
        self.stage[nonterminal] = torch.clamp(
            self.stage[nonterminal] + 1, max=len(MILESTONES))
        self.option_id[lane_mask] = -1


def macro_observation(ep, seat, lifecycle, executors):
    """Full game observation plus the persistent high-level Markov state."""
    base = features_t.encode_t(ep, seat)
    stage = torch.nn.functional.one_hot(
        lifecycle.stage.clamp(max=len(MILESTONES)),
        len(MILESTONES) + 1).to(torch.float32)
    previous = torch.nn.functional.one_hot(
        torch.where(lifecycle.last_option < 0,
                    torch.full_like(lifecycle.last_option, N_OPTIONS),
                    lifecycle.last_option),
        N_OPTIONS + 1).to(torch.float32)
    reason = torch.nn.functional.one_hot(
        lifecycle.termination_reason, len(TERMINATION_NAMES)).to(torch.float32)
    planted = torch.maximum(
        executors[Option.K01_ROUTE].planted_total,
        executors[Option.K01_ROUTE_S34].planted_total).to(torch.float32) / 40.0
    return torch.cat([base, stage, previous, reason, planted], -1)


MACRO_OBS_DIM = (features_t.OBS_DIM + len(MILESTONES) + 1 + N_OPTIONS + 1
                 + len(TERMINATION_NAMES) + len(engine_t.CROP_NAMES))


class MacroActorCritic(nn.Module):
    """Small categorical controller and macro critic over decision states."""

    def __init__(self, obs_dim=MACRO_OBS_DIM, hidden=(256, 128),
                 route_bias=1.5):
        super().__init__()
        h1, h2 = (int(value) for value in hidden)
        self.trunk = nn.Sequential(
            nn.Linear(obs_dim, h1), nn.ReLU(),
            nn.Linear(h1, h2), nn.ReLU())
        self.actor = nn.Linear(h2, N_OPTIONS)
        self.critic = nn.Linear(h2, 1)
        for layer in self.trunk:
            if isinstance(layer, nn.Linear):
                nn.init.orthogonal_(layer.weight, math.sqrt(2))
                nn.init.zeros_(layer.bias)
        nn.init.orthogonal_(self.actor.weight, 0.01)
        nn.init.zeros_(self.actor.bias)
        with torch.no_grad():
            self.actor.bias[int(Option.K01_ROUTE)] = route_bias * 0.5
            self.actor.bias[int(Option.K01_ROUTE_S34)] = route_bias
        nn.init.orthogonal_(self.critic.weight, 1.0)
        nn.init.zeros_(self.critic.bias)

    def forward(self, observation):
        hidden = self.trunk(observation)
        return self.actor(hidden), self.critic(hidden).squeeze(-1)


def masked_categorical(logits, mask):
    if not bool(mask.any(-1).all()):
        raise ValueError("every macro decision needs at least one legal Option")
    return Categorical(logits=logits.masked_fill(~mask, -1e9))


@torch.no_grad()
def greedy_low_action(actor_net, td, multi, lane_mask=None):
    lanes = td["observation"].shape[0]
    if lane_mask is None:
        lane_mask = torch.ones(
            lanes, dtype=torch.bool, device=td["observation"].device)
    action_width = 2 + (td["hand_mask"].shape[-2] if multi else 0)
    action = torch.zeros(
        (lanes, action_width), dtype=torch.int64,
        device=td["observation"].device)
    if not bool(lane_mask.any()):
        return action
    outputs = actor_net(td["observation"][lane_mask])
    farmer_mask = td["farmer_mask"][lane_mask]
    market_mask = td["market_mask"][lane_mask]
    farmer = outputs[0].masked_fill(~farmer_mask, -1e9).argmax(-1)
    market = outputs[1].masked_fill(~market_mask, -1e9).argmax(-1)
    if not multi:
        action[lane_mask] = torch.stack([farmer, market], -1)
        return action
    hand_mask = td["hand_mask"][lane_mask]
    hands = outputs[2].masked_fill(~hand_mask, -1e9).argmax(-1)
    action[lane_mask] = torch.cat(
        [farmer.unsqueeze(-1), market.unsqueeze(-1), hands], -1)
    return action


class MacroGame:
    """One batched season with asynchronous persistent Option decisions."""

    def __init__(self, checkpoint, opponent, lanes, seed, device="cpu", seat=0,
                 gamma=0.999, option_timeout=240, steps_override=0):
        _, saved, actor, _, multi = macro_audit._load_checkpoint(
            checkpoint, device)
        self.low_actor = actor
        self.multi = multi
        env_kwargs = macro_audit._env_kwargs(saved)
        if steps_override:
            env_kwargs["episode_steps"] = int(steps_override)
        self.env = KGTensorEnv(
            lanes, device=device, seat=seat, base_seed=seed,
            opponent=opponent, multi_head=multi,
            **env_kwargs)
        self.gamma = float(gamma)
        self.option_timeout = int(option_timeout)
        self.td = None
        self.lifecycle = None
        self.executors = None
        self.last_route = None

    @property
    def device(self):
        return self.env.device

    @property
    def B(self):
        return self.env.B

    def reset(self):
        self.td = self.env.reset()
        self.executors = {
            Option.K01_ROUTE: barnyard_t.BarnyardOpponent("k01_route"),
            Option.K01_ROUTE_S34: barnyard_t.BarnyardOpponent(
                "k01_route_s34"),
        }
        for executor in self.executors.values():
            executor.reset(self.env._ep, self.env.seat)
        self.lifecycle = OptionLifecycle(
            self.B, MACRO_OBS_DIM, self.device, self.gamma,
            self.option_timeout)
        self.last_route = torch.full(
            (self.B,), -1, dtype=torch.int64, device=self.device)
        return self.observation()

    def observation(self):
        return macro_observation(
            self.env._ep, self.env.seat, self.lifecycle, self.executors)

    def action_mask(self):
        return torch.ones(
            (self.B, N_OPTIONS), dtype=torch.bool, device=self.device)

    def start_options(self, lane_mask, option_id, state, action_mask, log_prob,
                      value, probs):
        lane_mask = torch.as_tensor(
            lane_mask, dtype=torch.bool, device=self.device).view(self.B)
        ep, seat = self.env._ep, self.env.seat
        for option in (Option.K01_ROUTE, Option.K01_ROUTE_S34):
            chosen = lane_mask & (option_id == int(option))
            if not bool(chosen.any()):
                continue
            other = (Option.K01_ROUTE_S34
                     if option == Option.K01_ROUTE else Option.K01_ROUTE)
            switched = chosen & (self.last_route == int(other))
            fresh = chosen & (self.last_route < 0)
            if bool(switched.any()):
                self.executors[option].sync_lanes_from(
                    self.executors[other], switched)
            if bool(fresh.any()):
                self.executors[option].sync_current_plants(ep, seat, fresh)
            self.last_route[chosen] = int(option)
        self.lifecycle.start(
            lane_mask, option_id, state, action_mask, log_prob, value, probs,
            ep._step)

    def step(self):
        if not bool(self.lifecycle.active.all()):
            raise RuntimeError("every live lane must have an active Option")
        follow = self.lifecycle.option_id == int(Option.FOLLOW_POLICY)
        action = greedy_low_action(
            self.low_actor, self.td, self.multi, lane_mask=follow)
        for option in (Option.K01_ROUTE, Option.K01_ROUTE_S34):
            lane_mask = self.lifecycle.option_id == int(option)
            if bool(lane_mask.any()):
                ops = self.executors[option](
                    self.env._ep, self.env.seat, lane_mask=lane_mask)
                self.env.queue_step_override(self.env.seat, ops, lane_mask)
        self.td["action"] = action
        nxt = self.env.step(self.td)["next"]
        self.lifecycle.add_reward(nxt["reward"].squeeze(-1))
        finished, reason = self.lifecycle.termination(
            self.env._ep, self.env.seat)
        chunks = []
        if bool(finished.any()):
            lanes = finished.nonzero(as_tuple=False).squeeze(-1)
            start = {
                "state": self.lifecycle.start_state[lanes].clone(),
                "action_mask": self.lifecycle.start_mask[lanes].clone(),
                "action": self.lifecycle.option_id[lanes].clone(),
                "old_log_prob": self.lifecycle.start_log_prob[lanes].clone(),
                "old_value": self.lifecycle.start_value[lanes].clone(),
                "old_probs": self.lifecycle.start_probs[lanes].clone(),
                "reward": self.lifecycle.discounted_reward[lanes].clone(),
                "gamma_tau": self.lifecycle.discount[lanes].clone(),
                "tau": self.lifecycle.elapsed[lanes].clone(),
                "reason": reason[lanes].clone(),
                "lane": lanes.clone(),
                "stage": self.lifecycle.stage[lanes].clone(),
            }
            self.lifecycle.finish(finished, reason)
            start["next_state"] = self.observation()[lanes].clone()
            start["done"] = torch.full(
                (lanes.numel(),), bool(self.env._ep.done), dtype=torch.bool,
                device=self.device)
            chunks.append(start)
        self.td = nxt.exclude("reward")
        return chunks, bool(nxt["done"].all())

    def terminal_metrics(self):
        ep, seat = self.env._ep, self.env.seat
        money = ep.money[:, seat].to(torch.float32)
        opp_money = ep.money[:, 1 - seat].to(torch.float32)
        margin = money - opp_money
        return {
            "money": money,
            "opp_money": opp_money,
            "margin": margin,
            "win": (margin > 0).to(torch.float32)
                   + 0.5 * (margin == 0).to(torch.float32),
        }


def semimdp_gae(reward, value, next_value, gamma_tau, done, trajectory,
                sequence, lam=0.95):
    """GAE over variable-duration transitions.

    Discounting within an Option is already folded into ``reward``.  The
    bootstrap and the link to the next macro advantage use ``gamma ** tau``;
    lambda decays once per strategic decision, not once per game turn.
    """
    reward = torch.as_tensor(reward)
    value = torch.as_tensor(value, device=reward.device)
    next_value = torch.as_tensor(next_value, device=reward.device)
    gamma_tau = torch.as_tensor(gamma_tau, device=reward.device)
    done = torch.as_tensor(done, dtype=torch.bool, device=reward.device)
    trajectory = torch.as_tensor(
        trajectory, dtype=torch.int64, device=reward.device)
    sequence = torch.as_tensor(sequence, dtype=torch.int64, device=reward.device)
    advantage = torch.zeros_like(reward)
    delta = reward + gamma_tau * next_value * (~done) - value
    for trajectory_id in trajectory.unique(sorted=True):
        indices = (trajectory == trajectory_id).nonzero(
            as_tuple=False).squeeze(-1)
        indices = indices[sequence[indices].argsort(descending=True)]
        following = torch.zeros((), dtype=reward.dtype, device=reward.device)
        for index in indices:
            advantage[index] = delta[index] + (
                gamma_tau[index] * float(lam) * following * (~done[index]))
            following = advantage[index]
    return advantage, advantage + value
