#!/usr/bin/env python
"""Stress an agent against pathological environment configurations.

A crashed or timed-out agent forfeits the episode, so the only thing that
matters here is: does it always return, always in time, and always DONE?

Real episodes only ever use the defaults, so this is not about realism. It is
about finding hardcoded assumptions -- a board that is not 10x10, a shed that
holds one item, a day that is one turn long, free farm hands -- before the
leaderboard finds them.

    python tools/stress.py agents/barnyard.py
    python tools/stress.py agents/barnyard.py -j 8
"""

import argparse
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

# (label, configuration overrides)
CASES = [
    ("defaults",              {}),
    ("broke: money 0",        {"startingMoney": 0}),
    ("broke: money 1",        {"startingMoney": 1}),
    ("rich: money 1e6",       {"startingMoney": 1_000_000}),
    ("tiny board 4x4",        {"boardSize": 4}),
    ("odd board 7x7",         {"boardSize": 7}),
    ("huge board 20x20",      {"boardSize": 20}),
    ("shed holds 1",          {"shedCapacity": 1}),
    ("shed holds 5",          {"shedCapacity": 5}),
    ("shed holds 5000",       {"shedCapacity": 5000}),
    ("1 turn per day",        {"turnsPerDay": 1}),
    ("2 turns per day",       {"turnsPerDay": 2}),
    ("100 turns per day",     {"turnsPerDay": 100}),
    ("episode of 2 steps",    {"episodeSteps": 2}),
    ("episode of 25 steps",   {"episodeSteps": 25}),
    ("episode of 2000 steps", {"episodeSteps": 2000}),
    ("weeds everywhere",      {"weedSpawnChance": 1.0}),
    ("no weeds",              {"weedSpawnChance": 0.0}),
    ("1 market order/turn",   {"maxMarketOrdersPerTurn": 1}),
    ("free farm hands",       {"farmHandCostMult": 0}),
    ("hands cost 100x",       {"farmHandCostMult": 100}),
    ("all shops by day 8",    {"townShopUnlockInterval": 1}),
    ("shops never unlock",    {"townShopUnlockInterval": 999}),
    ("town never buys",       {"townShopSellInterval": 999, "townCenterSellInterval": 999}),
    ("town buys every turn",  {"townShopSellInterval": 1, "townCenterSellInterval": 1}),
    ("melon worthless",       {"marketParams": {"MELON": {"base": 1}}}),
    ("milk 10x base",         {"marketParams": {"MILK": {"base": 1600}}}),
    ("everything crashes",    {"marketParams": {p: {"above_target": 40.0} for p in
                                                ("MELON", "MILK", "WOOL", "STRAWBERRY",
                                                 "WHEAT", "EGG", "CARROT", "TOMATO",
                                                 "FERTILIZER")}}),
]


def _run(job):
    label, cfg, agent, opponent, seed = job
    from kaggle_environments import make

    conf = {"episodeSteps": 720, "seed": seed}
    conf.update(cfg)
    t0 = time.perf_counter()
    try:
        env = make("kaggriculture", configuration=conf)
        env.run([agent, opponent])
        final = env.steps[-1]
        statuses = [s.status for s in final]
        rewards = [s.reward for s in final]
        # Per-turn durations of seat 0, recorded by the framework.
        durs = [step[0].get("duration", 0.0) if isinstance(step, dict) else 0.0
                for step in []]
        worst = 0.0
        for entry in env.logs or []:
            if entry and isinstance(entry, list) and entry[0]:
                worst = max(worst, float(entry[0].get("duration", 0.0) or 0.0))
        return {"label": label, "ok": statuses[0] == "DONE", "status": statuses[0],
                "reward": rewards[0], "worst_turn": worst,
                "wall": time.perf_counter() - t0, "error": None}
    except Exception:
        return {"label": label, "ok": False, "status": "EXCEPTION", "reward": None,
                "worst_turn": 0.0, "wall": time.perf_counter() - t0,
                "error": traceback.format_exc().strip().splitlines()[-1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--opponent", default="starter")
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    jobs = [(label, cfg, args.agent, args.opponent, args.seed) for label, cfg in CASES]
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(_run, jobs))

    print(f"{'case':24s} {'status':10s} {'reward':>12s} {'worst turn':>11s}  note")
    print("-" * 78)
    bad = 0
    for r in results:
        mark = " " if r["ok"] else "!"
        rew = f"{r['reward']:,.0f}" if isinstance(r["reward"], (int, float)) else str(r["reward"])
        note = r["error"] or ("" if r["ok"] else "NOT DONE")
        if r["worst_turn"] > 0.5:
            note = (note + " SLOW TURN").strip()
        if not r["ok"] or r["worst_turn"] > 0.5:
            bad += 1
        print(f"{mark}{r['label']:23s} {r['status']:10s} {rew:>12s} "
              f"{r['worst_turn']*1000:9.1f}ms  {note}")

    print()
    print(f"{len(results) - bad}/{len(results)} clean")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
