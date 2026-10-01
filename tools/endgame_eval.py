#!/usr/bin/env python
"""Frozen, sharded endgame evaluation. Workers never open arena.sqlite.

The manifest fixes source hashes, names, opponents and seeds before execution.
Report each opponent separately, with paired median margin changes and a
bootstrap that resamples seeds with both seats together. This does not estimate
Kaggle ratings or medal probabilities.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import wilson


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def play(job):
    index, left, right, seed = job
    from kaggle_environments import make
    from tournament import _digest, _fast_env
    if os.environ.get("KG_FAST_ENV") == "1":
        _fast_env()
    start = time.perf_counter()
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([left, right])
    final = env.steps[-1]
    status = [str(x.status) for x in final]
    if status != ["DONE", "DONE"]:
        raise RuntimeError(f"Match {index}, seed {seed}: {status}")
    sells = [0, 0]
    contested = 0
    for step in env.steps:
        orders = [(x.get("action") or {}).get("market") or [] for x in step]
        for p in (0, 1):
            sells[p] += sum(isinstance(o, list) and len(o) >= 3 and
                            o[0] == "SELL" and o[2] > 0 for o in orders[p][:10])
        for a, b in zip(orders[0][:10], orders[1][:10]):
            if (isinstance(a, list) and isinstance(b, list) and
                    len(a) >= 3 and len(b) >= 3 and a[0] == b[0] == "SELL"
                    and a[1] == b[1] and a[2] > 0 and b[2] > 0):
                contested += 1
    duration = [0.0, 0.0]
    for entry in env.logs or []:
        for p, log in enumerate(entry[:2] if isinstance(entry, list) else []):
            if isinstance(log, dict):
                duration[p] = max(duration[p], float(log.get("duration", 0) or 0))
    # Read-only diagnostics: preserve the action stream and the opening pasture
    # state so rare repairs can be separated from unchanged episodes later.
    action_hashes = []
    opening_pasture = []
    for p in (0, 1):
        digest = hashlib.sha256()
        for step in env.steps:
            digest.update(json.dumps(step[p].get("action"), sort_keys=True,
                                     separators=(",", ":")).encode())
            digest.update(b"\n")
        action_hashes.append(digest.hexdigest())
        opening_pasture.append({
            "commands": {str(i): env.steps[i][p].action.get("farmer")
                         for i in (70, 71)},
            "before": {str(i): {
                "farmer": env.steps[i][p].observation.farms[p].farmer,
                "carried_cow": env.steps[i][p].observation.private.inventories[0].get("COW", 0),
            } for i in (69, 70)},
            "other_actions_sha256": {str(i): hashlib.sha256(json.dumps({
                k: env.steps[i][p].action.get(k) for k in ("hands", "market")
            }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                for i in (70, 71)},
            "tiles": {str(i): env.steps[i][0].observation.farms[p].tiles[2][4]
                      for i in (69, 70, 71, 96, 120, 719)},
        })
    return {"index": index, "left": left, "right": right, "seed": seed,
            "action_sha256": action_hashes, "opening_pasture": opening_pasture,
            "money": [float(x.reward or 0) for x in final], "status": status,
            "contested_sell_slots": contested, "sell_orders": sells,
            "worst_turn_seconds": duration,
            "shops": list(final[0].observation["town"]["unlocked_shops"]),
            "digest": [_digest(env, 0), _digest(env, 1)],
            "wall": time.perf_counter() - start}


def read_manifest(path):
    manifest = json.loads(Path(path).read_text())
    for file, expected in manifest["sha256"].items():
        if sha(file) != expected:
            raise RuntimeError(f"Source changed after registration: {file}")
    return manifest


def run(args):
    manifest = read_manifest(args.manifest)
    k, n = map(int, args.shard.split("/"))
    if not 0 <= k < n:
        raise ValueError(args.shard)
    out = Path(args.manifest).parent / "results"
    out.mkdir(exist_ok=True)
    target = out / f"shard-{k:03d}.jsonl"
    if target.exists():
        raise RuntimeError(f"Refusing to overwrite {target}")
    jobs = [(i, manifest["agents"][a], manifest["agents"][b], seed)
            for i, (a, b, seed) in enumerate(manifest["matches"]) if i % n == k]
    print(f"shard {k}/{n}: {len(jobs)} matches, {args.jobs} workers", flush=True)
    partial = target.with_suffix(".partial")
    with partial.open("w") as f, ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(play, job) for job in jobs]
        for count, future in enumerate(as_completed(futures), 1):
            f.write(json.dumps(future.result(), separators=(",", ":")) + "\n")
            f.flush()
            if count % 32 == 0 or count == len(jobs):
                print(f"{count}/{len(jobs)} complete", flush=True)
    read_manifest(args.manifest)
    partial.rename(target)


def bootstrap_effect(pairs, iterations=4000, mean=False):
    import numpy as np
    groups = defaultdict(list)
    for seed, value in pairs:
        groups[seed].append(value)
    arrays = [groups[s] for s in sorted(groups)]
    if len({len(v) for v in arrays}) != 1:
        raise RuntimeError("Unbalanced seed clusters")
    values = np.asarray(arrays, dtype=float)
    rng = np.random.default_rng(20260929)
    samples = values[rng.integers(0, len(values), size=(iterations, len(values)))]
    statistic = np.mean if mean else np.median
    estimates = statistic(samples.reshape(iterations, -1), axis=1)
    interval = [float(x) for x in np.quantile(estimates, [0.025, 0.975])]
    result = {"mean" if mean else "median": float(statistic(values)),
              "ci95": interval, "seeds": len(groups),
              "episodes": sum(map(len, arrays))}
    if mean and np.ptp(values.mean(axis=1)) == 0:
        # A bootstrap cannot invent an unseen losing seed. Protect a constant
        # observed win effect using a binomial bound on unseen seed mass, with
        # the worst possible effect in [-1, 1] on those unobserved seeds.
        mass = 1 - 0.025 ** (1 / len(groups))
        center = result["mean"]
        interval[0] = min(interval[0], center - (center + 1) * mass)
        interval[1] = max(interval[1], center + (1 - center) * mass)
        result["constant_seed_guard_mass"] = mass
    return result


def summarize(args):
    manifest = read_manifest(args.manifest)
    results = {}
    for path in sorted((Path(args.manifest).parent / "results").glob("shard-*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            index = row["index"]
            if not isinstance(index, int) or not 0 <= index < len(manifest["matches"]):
                raise RuntimeError(f"Invalid match index: {index}")
            if index in results:
                raise RuntimeError(f"Duplicate match {index}")
            if row["status"] != ["DONE", "DONE"] or not all(math.isfinite(x) for x in row["money"]):
                raise RuntimeError(f"Invalid match outcome: {index}")
            a, b, seed = manifest["matches"][index]
            assert (row["left"], row["right"], row["seed"]) == (
                manifest["agents"][a], manifest["agents"][b], seed)
            results[index] = row
    if len(results) != len(manifest["matches"]):
        raise RuntimeError(f"Incomplete: {len(results)}/{len(manifest['matches'])}")
    by_pair = defaultdict(dict)
    for index, row in results.items():
        a, b, seed = manifest["matches"][index]
        for seat, (me, other) in enumerate(((a, b), (b, a))):
            if (seed, seat) in by_pair[me, other]:
                raise RuntimeError(f"Duplicate semantic match: {me}/{other}/{seed}/{seat}")
            money = row["money"][seat]
            opponent_money = row["money"][1-seat]
            by_pair[me, other][seed, seat] = {
                "margin": money-opponent_money, "money": money,
                "opponent_money": opponent_money,
                "score": float(money > opponent_money) + 0.5*(money == opponent_money),
                "contestation": row["contested_sell_slots"] / max(1, row["sell_orders"][seat])}
    summary = {"matches": len(results), "by_opponent": {}, "paired": {},
               "max_turn_seconds": max(max(x["worst_turn_seconds"]) for x in results.values())}
    for (a, b), records in sorted(by_pair.items()):
        values = list(records.values())
        wins = sum(x["score"] == 1 for x in values)
        ties = sum(x["score"] == 0.5 for x in values)
        score = wins + ties/2
        row = {"games": len(values), "wins": wins, "ties": ties,
               "win_score": score/len(values),
               "median_money": statistics.median(x["money"] for x in values),
               "median_margin": statistics.median(x["margin"] for x in values),
               "median_sell_contestation": statistics.median(x["contestation"] for x in values)}
        row["by_seat"] = {}
        for seat in (0, 1):
            seated = [record for (_, s), record in records.items() if s == seat]
            if seated:
                row["by_seat"][str(seat)] = {
                    "games": len(seated),
                    "wins": sum(x["score"] == 1 for x in seated),
                    "ties": sum(x["score"] == 0.5 for x in seated),
                    "win_score": statistics.mean(x["score"] for x in seated),
                    "median_margin": statistics.median(x["margin"] for x in seated),
                }
        summary["by_opponent"].setdefault(a, {})[b] = row
    baseline = manifest.get("baseline", "n04")
    for candidate in manifest.get("candidates", []):
        if candidate == baseline:
            continue
        for opponent in manifest.get("panel", []):
            a, b = by_pair.get((candidate, opponent)), by_pair.get((baseline, opponent))
            if not a or not b:
                continue
            if set(a) != set(b):
                raise RuntimeError(f"Mismatched paired cells: {candidate}/{opponent}")
            effects = {}
            for metric in ("margin", "money", "opponent_money", "score"):
                pairs = [(seed, a[seed, seat][metric]-b[seed, seat][metric])
                         for seed, seat in sorted(a)]
                effects[metric] = bootstrap_effect(pairs, mean=metric == "score")
            summary["paired"].setdefault(candidate, {})[opponent] = effects
    summary["group_win_effects"] = {}
    summary["group_win_effects_by_seat"] = {}
    for candidate in manifest.get("candidates", []):
        if candidate == baseline:
            continue
        for group, opponents in manifest.get("groups", {}).items():
            pairs = []
            seated_pairs = {0: [], 1: []}
            for opponent in opponents:
                a, b = by_pair.get((candidate, opponent)), by_pair.get((baseline, opponent))
                if not a or not b or set(a) != set(b):
                    raise RuntimeError(f"Missing paired group: {candidate}/{opponent}")
                pairs.extend((seed, a[seed, seat]["score"]-b[seed, seat]["score"])
                             for seed, seat in sorted(a))
                for seed, seat in sorted(a):
                    seated_pairs[seat].append((seed, a[seed, seat]["score"]-b[seed, seat]["score"]))
            summary["group_win_effects"].setdefault(candidate, {})[group] = bootstrap_effect(pairs, mean=True)
            summary["group_win_effects_by_seat"].setdefault(candidate, {})[group] = {
                str(seat): bootstrap_effect(values, mean=True)
                for seat, values in seated_pairs.items()
            }
    output = Path(args.manifest).parent / "summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Complete: {len(results)} matches. {output}")
    for candidate in manifest.get("candidates", []):
        for opponent, row in summary["by_opponent"].get(candidate, {}).items():
            print(f"{candidate:22s} vs {opponent:22s} {row['win_score']:6.1%} "
                  f"({row['games']}) margin {row['median_margin']:+9.0f} "
                  f"contest {row['median_sell_contestation']:5.1%}")
    for candidate, opponents in summary["paired"].items():
        for opponent, effects in opponents.items():
            row = effects["margin"]
            win = effects["score"]
            print(f"{candidate} - {baseline} vs {opponent}: win {win['mean']:+.1%} "
                  f"CI [{win['ci95'][0]:+.1%}, {win['ci95'][1]:+.1%}]; median {row['median']:+.0f} "
                  f"CI [{row['ci95'][0]:+.0f}, {row['ci95'][1]:+.0f}]")
    for candidate, groups in summary["group_win_effects"].items():
        for group, effect in groups.items():
            print(f"GROUP {candidate} - {baseline} / {group}: win {effect['mean']:+.1%} "
                  f"CI [{effect['ci95'][0]:+.1%}, {effect['ci95'][1]:+.1%}]")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["run", "summarize"])
    ap.add_argument("manifest")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("-j", "--jobs", type=int, default=1)
    args = ap.parse_args()
    (run if args.mode == "run" else summarize)(args)


if __name__ == "__main__":
    main()
