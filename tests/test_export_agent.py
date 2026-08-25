"""Regression tests for optional controllers baked into exported RL agents."""

import copy
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rl"))

import export_agent  # noqa: E402
from kg_env import KGEnv  # noqa: E402


class _DummyPolicy:
    def export_npz(self, path):
        # The option controller does not call the network forward pass.  A
        # placeholder archive is enough to load and exercise generated code.
        np.savez(path, placeholder=np.zeros(1, dtype=np.float32))


def _namespace(path):
    env = {}
    sys.path.append(os.path.dirname(path))
    try:
        with open(path) as fh:
            exec(compile(fh.read(), path, "exec"), env)
    finally:
        sys.path.pop()
    return env


def _eligible_obs():
    obs = copy.deepcopy(KGEnv(opponent="starter").reset(seed=123))
    obs["step"] = 4 * 24
    obs["day"] = 4
    obs["farms"][obs["player"]]["money"] = 1800.0
    return obs


def test_sheep_option_lifecycle():
    base_action = {"farmer": ["PASS"], "hands": [], "market": []}
    with tempfile.TemporaryDirectory() as tmp:
        disabled = export_agent.write_agent_dir(
            _DummyPolicy(), os.path.join(tmp, "disabled"))
        off = _namespace(disabled)
        malformed = {"step": 96}
        assert off["_sheep_option"](malformed, base_action) is base_action

        enabled = export_agent.write_agent_dir(
            _DummyPolicy(), os.path.join(tmp, "enabled"),
            sheep_cash_max=1900, sheep_min_day=4, sheep_timeout=96)
        on = _namespace(enabled)

        obs = _eligible_obs()
        chosen = on["_sheep_option"](obs, base_action)
        assert chosen["market"] == [["BUY_ANIMAL", "SHEEP", 1]]
        assert base_action == {"farmer": ["PASS"], "hands": [], "market": []}

        # Once a sheep appears on the board, the one-shot option terminates
        # and the learned policy owns both heads again.
        done = copy.deepcopy(obs)
        done["step"] += 1
        done["farms"][done["player"]]["tiles"][0][0] = {"animal": "SHEEP"}
        resumed = {"farmer": ["MOVE_E"], "hands": [], "market": [["HIRE"]]}
        assert on["_sheep_option"](done, resumed) is resumed


def test_sheep_option_threshold_skip_is_final():
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    with tempfile.TemporaryDirectory() as tmp:
        path = export_agent.write_agent_dir(
            _DummyPolicy(), os.path.join(tmp, "threshold"),
            sheep_cash_max=1900, sheep_min_day=4, sheep_timeout=96)
        ns = _namespace(path)
        obs = _eligible_obs()
        obs["farms"][obs["player"]]["money"] = 2000.0
        assert ns["_sheep_option"](obs, action) is action

        # The controller makes one decision at the first eligible state; it
        # must not reconsider later merely because cash fell below the cut.
        obs["step"] += 1
        obs["farms"][obs["player"]]["money"] = 1800.0
        assert ns["_sheep_option"](obs, action) is action


def test_sheep_option_can_reconsider_after_success():
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    with tempfile.TemporaryDirectory() as tmp:
        path = export_agent.write_agent_dir(
            _DummyPolicy(), os.path.join(tmp, "repeat"),
            sheep_cash_max=1900, sheep_min_day=4, sheep_timeout=96,
            sheep_max_additions=2)
        ns = _namespace(path)
        obs = _eligible_obs()
        assert ns["_sheep_option"](obs, action)["market"] == [
            ["BUY_ANIMAL", "SHEEP", 1]]

        first_done = copy.deepcopy(obs)
        first_done["step"] += 1
        first_done["farms"][0]["tiles"][0][0] = {
            "kind": "PASTURE", "animal": "SHEEP", "yield_units": 0,
            "fed_today": True, "cared_today": True,
            "fertilizer_available": False,
        }
        assert ns["_sheep_option"](first_done, action) is action

        second = copy.deepcopy(first_done)
        second["step"] += 1
        second["farms"][0]["money"] = 1800.0
        assert ns["_sheep_option"](second, action)["market"] == [
            ["BUY_ANIMAL", "SHEEP", 1]]

        second_done = copy.deepcopy(second)
        second_done["step"] += 1
        second_done["farms"][0]["tiles"][0][1] = {
            "kind": "PASTURE", "animal": "SHEEP", "yield_units": 0,
            "fed_today": True, "cared_today": True,
            "fertilizer_available": False,
        }
        assert ns["_sheep_option"](second_done, action) is action

        # The configured addition budget is exhausted.
        later = copy.deepcopy(second_done)
        later["step"] += 1
        assert ns["_sheep_option"](later, action) is action

def test_sheep_option_parameter_validation():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            export_agent.write_agent_dir(
                _DummyPolicy(), tmp, sheep_cash_max=-1)
        except ValueError:
            pass
        else:
            raise AssertionError("negative cash threshold was accepted")


if __name__ == "__main__":
    test_sheep_option_lifecycle()
    test_sheep_option_threshold_skip_is_final()
    test_sheep_option_can_reconsider_after_success()
    test_sheep_option_parameter_validation()
    print("export agent tests passed")
