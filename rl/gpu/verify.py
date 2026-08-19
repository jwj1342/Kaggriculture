"""Record official episodes and replay them on the GPU engine.

The bar is the same as tools/tracelib.py verify: both sides' money to the
dollar, and the shop unlock sequence. The first diverging step is the bug.

Snapshots also compare board care fields (unwatered/unfed/pending/fert_until),
unlocked quadrants, hires_today, and backpack insertion order. Official has
no hand cap; the tensor engine stores at most ENGINE_HAND_CAP (32). A
n_hands mismatch at that cap is a known fork, not a silent pass.

    python -m rl.gpu.verify --seeds 7,13 --left starter --right starter
    python -m rl.gpu.verify --seeds 7 --left agents/barnyard.py --right starter
    python -m rl.gpu.verify --suite --jobs 3
    python -m rl.gpu.verify --extra --jobs 3
"""

import argparse
import json
import os
import sys

os.environ.setdefault("KG_FAST_ENV", "1")

import torch

from . import constants as C
from .engine import step
from .official_codec import encode_turn, first_diff, snapshot_gpu, snapshot_official
from .state import new_state
from .tables import Tables


def _short(path):
    if path == "starter":
        return "starter"
    return os.path.splitext(os.path.basename(str(path)))[0]


# Diverse traces: seats, lockstep market, hire cap, land, animals, dump, hoard.
# Each entry is (left, right, seeds). Keep this short — recording is ~1 min/ep.
SUITE = [
    ("agents/barnyard.py", "starter", (1, 2, 8, 17, 99, 12345)),
    ("starter", "agents/barnyard.py", (7,)),
    ("agents/barnyard.py", "agents/barnyard.py", (7, 99)),
    ("agents/legacy/probes/no_hire.py", "starter", (7,)),
    ("agents/legacy/probes/hire_max.py", "starter", (7,)),
    ("agents/legacy/probes/dump_all.py", "starter", (7,)),
    ("agents/legacy/probes/one_quadrant.py", "starter", (7,)),
    ("agents/legacy/probes/four_quadrant.py", "starter", (7,)),
    ("agents/legacy/probes/mono_cow.py", "starter", (7,)),
    ("agents/legacy/probes/mono_melon.py", "starter", (7,)),
    ("agents/legacy/probes/fert_only.py", "starter", (7,)),
    ("agents/legacy/probes/hoarder.py", "starter", (7,)),
    ("agents/rl_agent.py", "starter", (7,)),
]

# Scripts not in SUITE. Remaining crop/animal/land/hire probes, a recorded
# ladder plan, and opponent-aware sellers.
EXTRA = [
    ("starter", "starter", (7, 13)),
    ("agents/legacy/probes/mixed_ref.py", "starter", (7,)),
    ("agents/legacy/probes/few_hands.py", "starter", (7,)),
    ("agents/legacy/probes/two_quadrant.py", "starter", (7,)),
    ("agents/legacy/probes/product_only.py", "starter", (7,)),
    ("agents/legacy/probes/mono_wheat.py", "starter", (7,)),
    ("agents/legacy/probes/mono_carrot.py", "starter", (7,)),
    ("agents/legacy/probes/mono_tomato.py", "starter", (7,)),
    ("agents/legacy/probes/mono_strawberry.py", "starter", (7,)),
    ("agents/legacy/probes/mono_sheep.py", "starter", (7,)),
    ("agents/legacy/probes/mono_goose.py", "starter", (7,)),
    ("agents/legacy/adv/frontrun.py", "starter", (7,)),
    ("agents/legacy/adv/avoid.py", "starter", (7,)),
    ("benchmarks/strongest.py", "starter", (7,)),
    ("benchmarks/strongest.py", "agents/barnyard.py", (7,)),
    ("agents/legacy/adv/spite.py", "starter", (7,)),
    ("agents/legacy/probes/mixed_ref.py", "agents/barnyard.py", (7,)),
]


def _obs(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.get("observation", obj)
    return getattr(obj, "observation", obj)


def _action(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.get("action") or {}
    return getattr(obj, "action", None) or {}


def _reward(obj):
    if obj is None:
        return 0.0
    if isinstance(obj, dict):
        return float(obj.get("reward") or 0)
    return float(getattr(obj, "reward", 0) or 0)


def record_episode(left, right, seed, episode_steps=720):
    """Run the official engine; return turns[t] = [p0_action, p1_action] and snapshots."""
    from kaggle_environments import make

    env = make("kaggriculture", configuration={
        "episodeSteps": int(episode_steps),
        "seed": int(seed),
    })
    env.run([left, right])
    steps = env.steps
    turns = []
    snaps = []
    for i, st in enumerate(steps):
        if i == 0:
            continue
        turns.append([_action(st[0]), _action(st[1])])
        snaps.append(snapshot_official(_obs(st[0]), _obs(st[1])))
    rewards = [_reward(steps[-1][0]), _reward(steps[-1][1])]
    shops = snaps[-1]["shops"] if snaps else []
    return {
        "seed": int(seed),
        "left": left,
        "right": right,
        "turns": turns,
        "snaps": snaps,
        "rewards": rewards,
        "shops": shops,
    }


def replay_on_gpu(trace, device="cpu"):
    """Apply recorded turns on the tensor engine. Return first mismatch or None."""
    T = Tables(device)
    st = new_state(1, device, seeds=[trace["seed"]])
    for t, pair in enumerate(trace["turns"]):
        act = encode_turn(pair, device=device)
        step(st, act, T)
        gpu = snapshot_gpu(st, 0)
        official = trace["snaps"][t]
        diff = first_diff(official, gpu)
        if diff is not None:
            key, want, got = diff
            return {
                "ok": False,
                "step": t,
                "field": key,
                "official": want,
                "gpu": got,
                "day": gpu["day"],
                "hour": gpu["hour"],
                "official_n_hands": official.get("n_hands"),
                "gpu_n_hands": gpu.get("n_hands"),
                "official_market": official.get("market_inv"),
                "gpu_market": gpu.get("market_inv"),
            }
    gpu = snapshot_gpu(st, 0)
    want_money = [int(round(x)) for x in trace["rewards"]]
    if gpu["money"] != want_money or gpu["shops"] != trace["shops"]:
        return {
            "ok": False,
            "step": len(trace["turns"]) - 1,
            "field": "final",
            "official": {"money": want_money, "shops": trace["shops"]},
            "gpu": {"money": gpu["money"], "shops": gpu["shops"]},
        }
    return {"ok": True, "steps": len(trace["turns"]), "money": gpu["money"], "shops": gpu["shops"]}


def run_case(left, right, seed, episode_steps=720, device="cpu"):
    label = f"{_short(left)} vs {_short(right)}  seed={seed}"
    try:
        tr = record_episode(left, right, seed, episode_steps)
    except Exception as e:
        return {
            "ok": False, "record_fail": str(e),
            "left": left, "right": right, "seed": seed, "label": label,
        }
    result = replay_on_gpu(tr, device=device)
    result.update(left=left, right=right, seed=seed, label=label)
    return result


def _run_case_star(spec):
    return run_case(*spec)


def _print_result(result):
    label = result.get("label", "")
    if result.get("record_fail"):
        print(f"  RECORD FAIL  {label}  {result['record_fail']}", flush=True)
        return False
    if result["ok"]:
        print(f"  ok  {label}  money={result['money']}  shops={result['shops']}", flush=True)
        return True
    extra = ""
    if "gpu_n_hands" in result:
        extra = (
            f"\n    n_hands official={result.get('official_n_hands')} "
            f"gpu={result.get('gpu_n_hands')}"
            f"\n    market_inv official={result.get('official_market')} "
            f"gpu={result.get('gpu_market')}"
        )
    if result.get("field") == "n_hands":
        off = result.get("official") or []
        try:
            if any(int(x) > C.ENGINE_HAND_CAP for x in off):
                extra += (
                    f"\n    known fork: official has no hand cap; "
                    f"tensor engine caps at {C.ENGINE_HAND_CAP}"
                )
        except (TypeError, ValueError):
            pass
    print(
        f"  FAIL  {label}  step {result['step']} "
        f"(day {result.get('day')} hour {result.get('hour')})  "
        f"field={result['field']}\n"
        f"    official={result['official']}\n"
        f"    gpu     ={result['gpu']}"
        f"{extra}",
        flush=True,
    )
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7,13,42")
    ap.add_argument("--left", default="starter")
    ap.add_argument("--right", default="starter")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--save", default=None, help="optional json path for the first trace")
    ap.add_argument("--suite", action="store_true",
                    help="run the built-in diversity suite (ignores --left/--right/--seeds)")
    ap.add_argument("--extra", action="store_true",
                    help="remaining probes, starter/starter, adv, strongest (ignores --left/--right/--seeds)")
    ap.add_argument("--jobs", type=int, default=1, help="parallel recordings (suite or many seeds)")
    args = ap.parse_args()

    if args.suite or args.extra:
        tables = []
        if args.suite:
            tables.append(("suite", SUITE))
        if args.extra:
            tables.append(("extra", EXTRA))
        specs = [
            (left, right, seed, args.steps, args.device)
            for _, table in tables
            for left, right, seeds in table
            for seed in seeds
        ]
        label = "+".join(name for name, _ in tables)
        print(f"{label}  {len(specs)} traces  jobs={args.jobs}", flush=True)
    else:
        seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
        specs = [(args.left, args.right, seed, args.steps, args.device) for seed in seeds]

    n_ok = n_bad = 0
    if args.jobs > 1 and len(specs) > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futs = {pool.submit(_run_case_star, spec): spec for spec in specs}
            for fut in as_completed(futs):
                result = fut.result()
                if _print_result(result):
                    n_ok += 1
                else:
                    n_bad += 1
    else:
        for i, spec in enumerate(specs):
            left, right, seed, steps, device = spec
            print(f"record seed={seed}  {left} vs {right} ...", flush=True)
            result = run_case(left, right, seed, steps, device)
            if _print_result(result):
                n_ok += 1
            else:
                n_bad += 1
    print(f"\n{n_ok} exact, {n_bad} not")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
