#!/usr/bin/env python
"""Deterministic gates for the option-lite Semi-MDP implementation."""

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "rl", ROOT / "rl" / "tensor_env"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import macro_audit as A  # noqa: E402
import macro_hierarchy as M  # noqa: E402
import verify  # noqa: E402
from trl_env import KGTensorEnv  # noqa: E402


def test_masked_categorical():
    logits = torch.tensor([[0.0, 5.0, 1.0]])
    mask = torch.tensor([[True, False, True]])
    distribution = M.masked_categorical(logits, mask)
    assert int(distribution.probs.argmax(-1)) == 2
    assert float(distribution.probs[0, 1]) == 0.0


def test_semimdp_gae_uses_gamma_to_tau():
    reward = torch.tensor([1.0, 2.0, 4.0])
    value = torch.tensor([0.5, 0.7, 1.0])
    next_value = torch.tensor([0.7, 1.0, 0.0])
    gamma_tau = torch.tensor([0.9**2, 0.9**3, 0.9])
    done = torch.tensor([False, False, True])
    trajectory = torch.tensor([4, 4, 4])
    sequence = torch.tensor([0, 1, 2])
    advantage, target = M.semimdp_gae(
        reward, value, next_value, gamma_tau, done, trajectory, sequence,
        lam=0.8)
    delta2 = 4.0 - 1.0
    delta1 = 2.0 + 0.9**3 * 1.0 - 0.7
    delta0 = 1.0 + 0.9**2 * 0.7 - 0.5
    want2 = delta2
    want1 = delta1 + 0.9**3 * 0.8 * want2
    want0 = delta0 + 0.9**2 * 0.8 * want1
    assert torch.allclose(advantage, torch.tensor([want0, want1, want2]))
    assert torch.allclose(target, advantage + value)


def _force_option(game, option):
    inactive = ~game.lifecycle.active
    state = game.observation()
    mask = game.action_mask()
    action = torch.full(
        (game.B,), int(option), dtype=torch.int64, device=game.device)
    probability = torch.zeros(
        (game.B, M.N_OPTIONS), dtype=torch.float32, device=game.device)
    probability[:, int(option)] = 1.0
    game.start_options(
        inactive, action, state, mask,
        torch.zeros(game.B, device=game.device),
        torch.zeros(game.B, device=game.device), probability)


def _direct_game(checkpoint, seed, steps):
    _, saved, actor, _, multi = A._load_checkpoint(checkpoint, "cpu")
    kwargs = A._env_kwargs(saved)
    kwargs["episode_steps"] = steps
    env = KGTensorEnv(
        1, device="cpu", seat=0, base_seed=seed, opponent="starter",
        multi_head=multi, **kwargs)
    return env, actor, multi


def test_follow_policy_is_exact_low_level_baseline():
    checkpoint = str(ROOT / "rl" / "runs" / "anvil" / "latest.pt")
    seed, steps = 771, 24
    game = M.MacroGame(
        checkpoint, "starter", 1, seed, steps_override=steps)
    game.reset()
    while True:
        if not bool(game.lifecycle.active.all()):
            _force_option(game, M.Option.FOLLOW_POLICY)
        _, done = game.step()
        if done:
            break

    env, actor, multi = _direct_game(checkpoint, seed, steps)
    td = env.reset()
    while True:
        td["action"] = M.greedy_low_action(actor, td, multi)
        nxt = env.step(td)["next"]
        if bool(nxt["done"].all()):
            break
        td = nxt.exclude("reward")
    assert verify.first_diff(game.env._ep.snapshot(0), env._ep.snapshot(0)) is None


def test_reselecting_route_preserves_exact_executor_behavior():
    checkpoint = str(ROOT / "rl" / "runs" / "anvil" / "latest.pt")
    seed, steps = 881, 30
    game = M.MacroGame(
        checkpoint, "starter", 1, seed, steps_override=steps)
    game.reset()
    while True:
        if not bool(game.lifecycle.active.all()):
            _force_option(game, M.Option.K01_ROUTE_S34)
        _, done = game.step()
        if done:
            break

    env, actor, multi = _direct_game(checkpoint, seed, steps)
    td = env.reset()
    executor = M.barnyard_t.BarnyardOpponent("k01_route_s34")
    full = torch.ones(1, dtype=torch.bool)
    while True:
        td["action"] = M.greedy_low_action(actor, td, multi)
        env.queue_step_override(env.seat, executor(env._ep, env.seat), full)
        nxt = env.step(td)["next"]
        if bool(nxt["done"].all()):
            break
        td = nxt.exclude("reward")
    assert verify.first_diff(game.env._ep.snapshot(0), env._ep.snapshot(0)) is None


if __name__ == "__main__":
    test_masked_categorical()
    test_semimdp_gae_uses_gamma_to_tau()
    test_follow_policy_is_exact_low_level_baseline()
    test_reselecting_route_preserves_exact_executor_behavior()
    print("macro hierarchy tests passed")

