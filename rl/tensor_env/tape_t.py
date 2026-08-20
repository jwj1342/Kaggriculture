#!/usr/bin/env python
"""Recorded tapes as tensor training opponents (TODO #1's second half).

A wrapped/champ agent embeds a per-step action-dict list (_TRACE). This
converts it ONCE into step_idx override tables -- (T,) farmer codes,
(T, H) hand codes, (T, S) market slots -- and replays it on any lane of
an EpisodeT batch by indexing ep._step. Open loop by construction: the
tape does what it did regardless of the board (illegal actions are the
engine's silent no-ops), so it never reacts -- which is exactly why it
was NOT usable as a kickstart teacher, and why its pool mass should stay
moderate (a policy can learn degenerate exploits against a non-reactor).
What it DOES carry is the top meta's economy: production volume and
market pressure at 95-158k a season.

NOT ported: the adaptive SELL-reorder wrapper around the tape (w49/k-line
agents shuffle sell slots by a front-run horizon). The gate therefore
compares against a PURE-TRACE python replay, not the wrapped agent.

    python rl/tensor_env/tape_t.py agents/wrapped/w49.py     # gate
Training spec:  --opponents tape:agents/wrapped/w49.py
"""

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

try:
    from . import engine_t as ET
    from . import engine_t_idx as X
except ImportError:
    import engine_t as ET
    import engine_t_idx as X

import actions as A  # puts agents/ (kg_rules) on sys.path

_UOP = {"PASS": X.U_PASS, "NORTH": X.U_MOVE_N, "SOUTH": X.U_MOVE_S,
        "EAST": X.U_MOVE_E, "WEST": X.U_MOVE_W, "WATER": X.U_WATER,
        "HARVEST": X.U_HARVEST, "FEED": X.U_FEED, "CARE": X.U_CARE,
        "COLLECT_FERTILIZER": X.U_COLLECT, "FERTILIZE": X.U_FERTILIZE,
        "DIG": X.U_DIG, "BUILD_COOP": X.U_BUILD_COOP,
        "BUILD_PASTURE": X.U_BUILD_PASTURE, "DROP": X.U_DROP,
        "PLANT": X.U_PLANT, "PLACE": X.U_PLACE, "PICKUP": X.U_PICKUP}
_CROP_IDX = {c: i for i, c in enumerate(ET.CROP_NAMES)}
_ANIMAL_IDX = {a: i for i, a in enumerate(ET.ANIMAL_NAMES)}
_ITEM_IDX = {n: i for i, n in enumerate(ET.ITEMS)}
_MOP = {"SELL": ET.OP_SELL, "BUY_PRODUCT": ET.OP_BUYP,
        "BUY_SEED": ET.OP_SEED, "BUY_ANIMAL": ET.OP_ANIMAL,
        "BUY_LAND": X.OP_LAND, "HIRE": X.OP_HIRE}


def load_trace(agent_path):
    name = "tape_src_" + os.path.basename(agent_path).replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, agent_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._TRACE


def _unit(act):
    """One unit's action list -> (op, arg, qty)."""
    if not act:
        return X.U_PASS, 0, 0
    op = _UOP.get(act[0], X.U_PASS)
    arg = qty = 0
    if act[0] == "PLANT" and len(act) > 1:
        arg = _CROP_IDX.get(act[1], 0)
    elif act[0] == "PLACE" and len(act) > 1:
        arg = _ANIMAL_IDX.get(act[1], 0)
    elif act[0] == "PICKUP" and len(act) > 1:
        arg = _ITEM_IDX.get(act[1], 0)
        qty = int(act[2]) if len(act) > 2 else 1
    return op, arg, qty


def compile_trace(trace, device="cpu"):
    """-> dict of (T, ...) int64 tensors in step_idx override layout."""
    T = len(trace)
    H = max((len(t.get("hands") or []) for t in trace), default=0)
    S = 10
    i64 = torch.int64
    f = torch.zeros((T, 3), dtype=i64)
    h = torch.zeros((T, H, 3), dtype=i64)
    m = torch.zeros((T, S, 3), dtype=i64)
    for t, act in enumerate(trace):
        f[t] = torch.tensor(_unit(act.get("farmer")), dtype=i64)
        for u, ha in enumerate((act.get("hands") or [])[:H]):
            h[t, u] = torch.tensor(_unit(ha), dtype=i64)
        for s, o in enumerate((act.get("market") or [])[:S]):
            if not o:
                continue
            mop = _MOP.get(o[0], 0)
            item = qty = 0
            if o[0] == "SELL" or o[0] == "BUY_PRODUCT":
                item = _ITEM_IDX.get(o[1], 0) if len(o) > 1 else 0
                qty = int(o[2]) if len(o) > 2 else 0
            elif o[0] == "BUY_SEED":
                item = _CROP_IDX.get(o[1], 0) if len(o) > 1 else 0
                qty = int(o[2]) if len(o) > 2 else 1
            elif o[0] == "BUY_ANIMAL":
                item = _ANIMAL_IDX.get(o[1], 0) if len(o) > 1 else 0
                qty = int(o[2]) if len(o) > 2 else 1
            m[t, s] = torch.tensor([mop, item, qty], dtype=i64)
    return {"f": f.to(device), "h": h.to(device), "m": m.to(device),
            "T": T, "H": H, "S": S}


class TapeOpponent:
    """step_idx override provider replaying one compiled tape on every
    lane (open loop; ep._step is lockstep across the batch)."""

    provides_ops = True

    def __init__(self, agent_path, device="cpu"):
        self.tab = compile_trace(load_trace(agent_path), device)
        self.name = os.path.basename(agent_path)

    def __call__(self, ep, player):
        t = min(ep._step, self.tab["T"] - 1)
        B = ep.B
        f = self.tab["f"][t]
        h = self.tab["h"][t]
        m = self.tab["m"][t]
        S = ep.max_market_orders
        ms = torch.zeros((B, S, 3), dtype=torch.int64, device=ep.device)
        ms[:, :min(S, self.tab["S"])] = m[:min(S, self.tab["S"])].unsqueeze(0)
        return {"f_op": f[0].expand(B).clone(),
                "f_arg": f[1].expand(B).clone(),
                "f_qty": f[2].expand(B).clone(),
                "h_op": [h[u, 0].expand(B).clone() for u in range(self.tab["H"])],
                "h_arg": [h[u, 1].expand(B).clone() for u in range(self.tab["H"])],
                "h_qty": [h[u, 2].expand(B).clone() for u in range(self.tab["H"])],
                "m_op": ms[..., 0], "m_item": ms[..., 1], "m_rem": ms[..., 2]}


def _gate(agent_path):
    """Pure-trace python replay vs TapeOpponent on the tensor engine,
    both against the scripted starter, same seed: final money must agree
    to the dollar on both seats."""
    import gzip
    import json
    import tempfile

    import engine_t
    import opponents_t
    from verify_t import lane_obs   # noqa: F401 (env parity helpers)

    trace = load_trace(agent_path)
    seed = 424_242
    # reference side: tape as a python agent (tracelib's replay template)
    import base64
    blob = base64.b64encode(gzip.compress(json.dumps(trace).encode())).decode()
    tpl = ('import json,gzip,base64\n'
           '_T=json.loads(gzip.decompress(base64.b64decode("%s")))\n'
           '_P={"farmer":["PASS"],"hands":[],"market":[]}\n'
           'def agent(obs):\n'
           '    try:\n'
           '        i=int(obs.get("step",0) or 0)\n'
           '        return _T[i] if 0<=i<len(_T) else _P\n'
           '    except Exception: return _P\n') % blob
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(tpl)
        tape_py = fh.name
    from kaggle_environments import make
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([tape_py, "starter"])
    want = [env.steps[-1][p].reward for p in (0, 1)]
    os.unlink(tape_py)

    ep = engine_t.EpisodeT([seed], episode_steps=720, device="cpu")
    opp = TapeOpponent(agent_path)
    zero = torch.zeros((1, 2), dtype=torch.int64)
    while not ep.done:
        fi, mi = opponents_t.starter_indices(ep, 1)
        f_idx = zero.clone()
        m_idx = zero.clone()
        f_idx[:, 1] = fi
        m_idx[:, 1] = mi
        ep.step_idx(f_idx, m_idx, override=[(0, opp(ep, 0))])
    got = [float(ep.money[0, p]) for p in (0, 1)]
    ok = all(abs(g - w) < 1.0 for g, w in zip(got, want))
    print(f"reference {want} vs tensor {got} -> "
          f"{'TAPE-PASS' if ok else 'TAPE-FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_gate(sys.argv[1] if len(sys.argv) > 1
                   else os.path.join(os.path.dirname(_RL),
                                     "agents", "wrapped", "w49.py")))
