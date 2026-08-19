"""IDLE + RESTOCK decoder baseline (no neural net). Used for local eval."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rl.action_space import MODE_IDX, decode_per_unit  # noqa: E402


def agent(obs):
    try:
        return decode_per_unit([0] * 13, MODE_IDX["RESTOCK"], obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
