"""Export a trained PPO policy into a single-file Kaggle submission agent.

The torchrl checkpoint exporter is `rl/export_agent.py`. This module exports
the older numpy/multi-head npz weights (`rl.gpu` / `rl.train_ppo`).

Usage (v2 multi-head):
    python -m rl.export_multihead --arch multi --weights rl/ckpt_official/ppo_it0300.npz --out agents/rl_agent.py

Usage (v1 single task+mode):
    python -m rl.export_multihead --arch single --weights rl/weights_bc.npz --out agents/rl_agent.py

Usage (market-only):
    python -m rl.export_multihead --arch market --weights rl/weights_bc_market.npz --plan data/plan.json --out agents/rl_agent.py
"""

import argparse
import base64
import json
import math
import os
import zlib

import numpy as np


_FEATURES_SRC = open(os.path.join(os.path.dirname(__file__), "features.py"), encoding="utf-8").read()
_ACTION_SRC = open(os.path.join(os.path.dirname(__file__), "action_space.py"), encoding="utf-8").read()


def _encode(path):
    with open(path, "rb") as f:
        return base64.b85encode(f.read()).decode("utf-8")


def _safe_action(obs):
    try:
        from .action_space import decode, FARM_TASKS, MARKET_MODES
        step = int(__import__("rl.features", fromlist=["_get"])._get(obs, "step") or 0)
        if step >= 680:
            return decode(FARM_TASKS.index("IDLE"), MARKET_MODES.index("DUMP"), obs, step=step)
        return decode(FARM_TASKS.index("IDLE"), MARKET_MODES.index("METERED"), obs, step=step)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}


def generate(weights_path, out_path, plan_path=None, arch="single"):
    weights_blob = _encode(weights_path)
    plan_blob = ""
    plan_turns = []
    if plan_path:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_turns = json.load(f)
        plan_blob = base64.b85encode(zlib.compress(json.dumps(plan_turns).encode("utf-8"))).decode("utf-8")

    def strip_relative_imports(src):
        lines = []
        for line in src.splitlines():
            if line.startswith("from .") or line.startswith("import ."):
                continue
            lines.append(line)
        return "\n".join(lines)

    features_body = strip_relative_imports(_FEATURES_SRC)
    action_body = strip_relative_imports(_ACTION_SRC)

    if plan_path or arch == "market":
        agent_src = f'''# SPDX-License-Identifier: MIT
# Auto-generated RL agent (market-only mode).
# Farm actions come from an embedded mined plan; RL controls only market_mode.
import base64
import json
import math
import zlib

_PLAN_BLOB = zlib.decompress(base64.b85decode("{plan_blob}")).decode("utf-8")
_PLAN = json.loads(_PLAN_BLOB)

_WEIGHTS_BLOB = """{weights_blob}"""
_P = json.loads(zlib.decompress(base64.b85decode(_WEIGHTS_BLOB)).decode("utf-8"))
for _k, _v in list(_P.items()):
    if isinstance(_v, list):
        if isinstance(_v[0], list):
            _P[_k] = [[float(x) for x in row] for row in _v]
        else:
            _P[_k] = [float(x) for x in _v]

{features_body}

{action_body}

_STEP = 0


def _matmul(a, b):
    if len(a) == 0 or len(b) == 0 or len(b[0]) == 0:
        return [0.0] * len(b[0]) if b else []
    ra = len(a)
    rb = len(b)
    rc = len(b[0])
    out = [0.0] * rc
    for i in range(ra):
        ai = float(a[i])
        row = b[i]
        if len(row) != rc:
            continue
        for j in range(rc):
            out[j] += ai * row[j]
    return out


def _tanh_vec(x):
    return [math.tanh(float(v)) for v in x]


def _softmax(x):
    m = max(x)
    ex = [math.exp(float(v) - m) for v in x]
    s = sum(ex)
    return [v / s for v in ex] if s > 0 else [1.0 / len(x)] * len(x)


def _forward(feats):
    x = [float(v) for v in feats]
    W1 = _P["W1"]; b1 = _P["b1"]
    W2 = _P["W2"]; b2 = _P["b2"]
    Wm = _P["Wm"]; bm = _P["bm"]

    z1 = _matmul(x, W1)
    for i in range(len(z1)):
        z1[i] += float(b1[i])
    h1 = _tanh_vec(z1)

    z2 = _matmul(h1, W2)
    for i in range(len(z2)):
        z2[i] += float(b2[i])
    h2 = _tanh_vec(z2)

    lm = _matmul(h2, Wm)
    for i in range(len(lm)):
        lm[i] += float(bm[i])
    pm = _softmax(lm)

    mode = max(range(len(pm)), key=lambda i: pm[i])
    return mode


def agent(obs):
    global _STEP
    try:
        plan_turn = _PLAN[_STEP] if _STEP < len(_PLAN) else {{"farmer": ["PASS"], "hands": []}}
        feats = encode(obs)
        mode = _forward(feats)
        step = int(_get(obs, "step") or 0)
        market_orders = decode_market_only(mode, obs, step=step)
        _STEP += 1
        return {{
            "farmer": plan_turn.get("farmer", ["PASS"]),
            "hands": plan_turn.get("hands", []) or [],
            "market": market_orders,
        }}
    except Exception:
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
'''
    elif arch == "multi":
        agent_src = f'''# SPDX-License-Identifier: MIT
# Auto-generated RL agent (multi-head PPO: farmer + 12 hands + market).
import base64
import json
import math
import zlib

_WEIGHTS_BLOB = """{weights_blob}"""

_P = json.loads(zlib.decompress(base64.b85decode(_WEIGHTS_BLOB)).decode("utf-8"))
for _k, _v in list(_P.items()):
    if isinstance(_v, list):
        if _v and isinstance(_v[0], list):
            _P[_k] = [[float(x) for x in row] for row in _v]
        elif _v and isinstance(_v[0], (int, float)):
            _P[_k] = [float(x) for x in _v]

{features_body}

{action_body}

_NHAND = 12


def _matmul(a, b):
    if len(a) == 0 or len(b) == 0 or len(b[0]) == 0:
        return [0.0] * len(b[0]) if b else []
    rc = len(b[0])
    out = [0.0] * rc
    for i in range(len(a)):
        ai = float(a[i])
        row = b[i]
        if len(row) != rc:
            continue
        for j in range(rc):
            out[j] += ai * row[j]
    return out


def _tanh_vec(x):
    return [math.tanh(float(v)) for v in x]


def _softmax(x):
    m = max(x)
    ex = [math.exp(float(v) - m) for v in x]
    s = sum(ex)
    return [v / s for v in ex] if s > 0 else [1.0 / len(x)] * len(x)


def _argmax(p):
    return max(range(len(p)), key=lambda i: p[i])


def _forward(feats):
    x = [float(v) for v in feats]
    W1 = _P["W1"]; b1 = _P["b1"]
    W2 = _P["W2"]; b2 = _P["b2"]
    Wf = _P["Wf"]; bf = _P["bf"]
    Wh = _P["Wh"]; bh = _P["bh"]
    Wm = _P["Wm"]; bm = _P["bm"]

    z1 = _matmul(x, W1)
    for i in range(len(z1)):
        z1[i] += float(b1[i])
    h1 = _tanh_vec(z1)

    z2 = _matmul(h1, W2)
    for i in range(len(z2)):
        z2[i] += float(b2[i])
    h2 = _tanh_vec(z2)

    lf = _matmul(h2, Wf)
    for i in range(len(lf)):
        lf[i] += float(bf[i])
    farmer = _argmax(_softmax(lf))

    lh = _matmul(h2, Wh)
    for i in range(len(lh)):
        lh[i] += float(bh[i])
    n_task = len(FARM_TASKS)
    hands = []
    for i in range(_NHAND):
        sl = lh[i * n_task:(i + 1) * n_task]
        hands.append(_argmax(_softmax(sl)) if sl else 0)

    lm = _matmul(h2, Wm)
    for i in range(len(lm)):
        lm[i] += float(bm[i])
    mode = _argmax(_softmax(lm))
    return farmer, hands, mode


def agent(obs):
    try:
        feats = encode(obs)
        farmer, hands, mode = _forward(feats)
        step = int(_get(obs, "step") or 0)
        player = int(_get(obs, "player") or 0)
        farms = _get(obs, "farms") or []
        farm = farms[player] if player < len(farms) else {{}}
        n_hands = len(_get(farm, "hands") or [])
        tasks = [farmer] + list(hands)
        for i in range(n_hands, _NHAND):
            if 1 + i < len(tasks):
                tasks[1 + i] = 0
        return decode_per_unit(tasks, mode, obs, step=step, hand_cap=_NHAND)
    except Exception:
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
'''
    else:
        agent_src = f'''# SPDX-License-Identifier: MIT
# Auto-generated RL agent (PPO policy + fallback scheduler).
# Weights from training run; feature encoder and decoder are frozen copies
# of rl/features.py and rl/action_space.py.
import base64
import json
import math
import zlib

_WEIGHTS_BLOB = """{weights_blob}"""

_P = json.loads(zlib.decompress(base64.b85decode(_WEIGHTS_BLOB)).decode("utf-8"))
for _k, _v in list(_P.items()):
    if isinstance(_v, list):
        if isinstance(_v[0], list):
            _P[_k] = [[float(x) for x in row] for row in _v]
        else:
            _P[_k] = [float(x) for x in _v]

{features_body}

{action_body}

def _matmul(a, b):
    if len(a) == 0 or len(b) == 0 or len(b[0]) == 0:
        return [0.0] * len(b[0]) if b else []
    ra = len(a)
    rb = len(b)
    rc = len(b[0])
    out = [0.0] * rc
    for i in range(ra):
        ai = float(a[i])
        row = b[i]
        if len(row) != rc:
            continue
        for j in range(rc):
            out[j] += ai * row[j]
    return out


def _tanh_vec(x):
    return [math.tanh(float(v)) for v in x]


def _softmax(x):
    m = max(x)
    ex = [math.exp(float(v) - m) for v in x]
    s = sum(ex)
    return [v / s for v in ex] if s > 0 else [1.0 / len(x)] * len(x)


def _forward(feats):
    x = [float(v) for v in feats]
    W1 = _P["W1"]; b1 = _P["b1"]
    W2 = _P["W2"]; b2 = _P["b2"]
    Wt = _P["Wt"]; bt = _P["bt"]
    Wm = _P["Wm"]; bm = _P["bm"]

    z1 = _matmul(x, W1)
    for i in range(len(z1)):
        z1[i] += float(b1[i])
    h1 = _tanh_vec(z1)

    z2 = _matmul(h1, W2)
    for i in range(len(z2)):
        z2[i] += float(b2[i])
    h2 = _tanh_vec(z2)

    lt = _matmul(h2, Wt)
    for i in range(len(lt)):
        lt[i] += float(bt[i])
    pt = _softmax(lt)

    lm = _matmul(h2, Wm)
    for i in range(len(lm)):
        lm[i] += float(bm[i])
    pm = _softmax(lm)

    task = max(range(len(pt)), key=lambda i: pt[i])
    mode = max(range(len(pm)), key=lambda i: pm[i])
    return task, mode


def agent(obs):
    try:
        feats = encode(obs)
        task, mode = _forward(feats)
        step = int(_get(obs, "step") or 0)
        return decode(task, mode, obs, step=step)
    except Exception:
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
'''

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(agent_src)
    print(f"wrote {out_path}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--arch", choices=["single", "multi", "market"], default="single")
    args = ap.parse_args()
    generate(args.weights, args.out, plan_path=args.plan, arch=args.arch)
