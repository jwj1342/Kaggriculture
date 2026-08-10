#!/usr/bin/env python
"""Run tournaments over the strategy library and persist every episode.

Two shapes:

  panel       every strategy plays a small fixed panel of anchors. Cost is
              O(n) rather than O(n^2), which is what makes a 594-strategy sweep
              affordable. Use this to screen the library.
  roundrobin  every pair plays. Exact, but O(n^2) -- use it on the survivors.

Both persist to data/arena.sqlite and fit Bradley-Terry strengths, the same
estimator Kaggle uses for the final leaderboard.

    python tools/tournament.py panel --lib agents/lib --seeds 8 -j 32
    python tools/tournament.py roundrobin --agents a.py b.py --seeds 24 -j 32
    python tools/tournament.py roundrobin --from-run latest --top 24 --seeds 24
"""

import argparse
import itertools
import json
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB  # noqa: E402

# Anchors span the strategy space so a panel score is informative: a strong
# metered farm, a flooder, a hoarder, a land-light farm, and two weak controls.
DEFAULT_PANEL = [
    "agents/lib/estate-crew-mixedfarm-metered-blind-muck.py",
    "agents/lib/homestead-crew-mixedfarm-metered-blind-muck.py",
    "agents/lib/homestead-crew-mixedfarm-flood-blind-muck.py",
    "agents/lib/estate-crew-mixedfarm-vault-blind-muck.py",
    "agents/lib/estate-crew-ranchmix-metered-blind-muck.py",
    "starter",
]


def _digest(env, p):
    """Compact per-player summary: composition, sales, money curve."""
    from collections import Counter as C
    steps = env.steps
    final = steps[-1][0].observation
    farm = final["farms"][p]
    crops, animals, structs = C(), C(), C()
    weeds = empty = 0
    for row in farm["tiles"]:
        for t in row:
            if t is None:
                empty += 1
            elif isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    crops[t["crop"]] += 1
                elif t.get("kind") == "WEED":
                    weeds += 1
                elif "animal" in t:
                    animals[t["animal"]] += 1
                else:
                    structs[t["kind"]] += 1
    sold = C()
    bought = C()
    hires = 0
    for st in steps:
        act = st[p].get("action") or {}
        for o in (act.get("market") or []):
            if not isinstance(o, list) or not o:
                continue
            if o[0] == "SELL" and len(o) >= 3:
                sold[o[1]] += int(o[2])
            elif o[0] in ("BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(o) >= 3:
                bought[o[1]] += int(o[2])
            elif o[0] == "HIRE":
                hires += 1
    # Money and herd size at checkpoints. The herd curve matters: a final-state
    # animal count cannot tell deliberate endgame abandonment apart from animals
    # that starved in the opening, and those are very different problems.
    curve, herd, hands = {}, {}, {}
    for d in (5, 10, 15, 20, 25, 29):
        i = d * 24 + 12
        if i < len(steps):
            o = steps[i][0].observation
            f = o["farms"][p]
            curve[str(d)] = round(float(f["money"]), 0)
            herd[str(d)] = sum(1 for row in f["tiles"] for t in row
                               if isinstance(t, dict) and "animal" in t)
            hands[str(d)] = len(f.get("hands") or [])
    return {"crops": dict(crops), "animals": dict(animals), "structs": dict(structs),
            "weeds": weeds, "empty": empty, "land": len(farm["unlocked_quadrants"]),
            "sold": dict(sold), "bought": dict(bought), "hire_orders": hires,
            "money": curve, "herd": herd, "hands": hands}


def _fast_env():
    """Drop the framework overhead that does not change any result.

    Profiled over a full episode: 42% of the wall clock is `deepcopy` of the
    whole game state (twice per step, once per agent), ~12% is
    `jsonschema.validate` on every action, and only ~13% is the strategy under
    test. The deepcopy is load-bearing -- agents must not share mutable state --
    but the schema validation is not: the interpreter ignores malformed actions
    anyway, and illegal actions are silent no-ops by design.

    Measured on three seeds: 3.13s -> 2.61s per episode, **17% faster, with
    byte-identical results**. Verified, not assumed -- see docs/TOOLS.md.

    Local harness only. Nothing here touches a submitted agent.
    """
    import jsonschema
    jsonschema.validate = lambda instance, schema, *a, **k: None


def _play(job):
    left, right, seed, steps = job
    from kaggle_environments import make
    if os.environ.get("KG_FAST_ENV") == "1":
        _fast_env()
    t0 = time.perf_counter()
    try:
        env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
        env.run([left, right])
        fin = env.steps[-1]
        obs = fin[0].observation
        return {"left": left, "right": right, "seed": seed,
                "money": [float(fin[0].reward or 0), float(fin[1].reward or 0)],
                "status": [str(fin[0].status), str(fin[1].status)],
                "shops": list(obs["town"]["unlocked_shops"]),
                "prices": dict(obs["market"]["prices"]),
                "digest": [_digest(env, 0), _digest(env, 1)],
                "wall": time.perf_counter() - t0}
    except Exception as e:
        return {"left": left, "right": right, "seed": seed, "money": [0.0, 0.0],
                "status": ["ERROR", "ERROR"], "shops": [], "prices": {},
                "digest": [{}, {}], "wall": time.perf_counter() - t0,
                "error": repr(e)[:200]}


def bradley_terry(wins, games, names, iters=2000, tol=1e-11):
    p = {n: 1.0 for n in names}
    for _ in range(iters):
        new = {}
        for i in names:
            num = sum(wins.get((i, j), 0.0) for j in names if j != i)
            den = sum(games.get((i, j), 0) / (p[i] + p[j]) for j in names
                      if j != i and games.get((i, j), 0))
            new[i] = num / den if den > 0 else p[i]
        tot = sum(new.values()) or 1.0
        new = {k: max(v, 1e-12) / tot * len(names) for k, v in new.items()}
        if max(abs(new[k] - p[k]) for k in names) < tol:
            return new
        p = new
    return p


def short(path):
    return os.path.splitext(os.path.basename(path))[0] if path.endswith(".py") else path


def _tally(results):
    wins, games, money = defaultdict(float), defaultdict(int), defaultdict(list)
    for r in results:
        L, R = short(r["left"]), short(r["right"])
        ml, mr = r["money"]
        money[L].append(ml)
        money[R].append(mr)
        games[(L, R)] += 1
        games[(R, L)] += 1
        if ml > mr:
            wins[(L, R)] += 1
        elif mr > ml:
            wins[(R, L)] += 1
        else:
            wins[(L, R)] += 0.5
            wins[(R, L)] += 0.5
    return wins, games, money


def _rate(results, names):
    wins, games, money = _tally(results)
    p = bradley_terry(wins, games, names)
    ref = statistics.median(p.values()) or 1e-12
    rows = []
    for n in names:
        g = sum(games.get((n, m), 0) for m in names if m != n)
        w = sum(wins.get((n, m), 0.0) for m in names if m != n)
        ms = money.get(n, [0.0])
        rows.append({"agent": n, "bt_strength": p[n],
                     "bt_elo": 400 * math.log10(max(p[n], 1e-12) / ref),
                     "games": g, "wins": w, "winrate": (w / g) if g else 0.0,
                     "median_money": statistics.median(ms),
                     "sd_money": statistics.pstdev(ms) if len(ms) > 1 else 0.0})
    rows.sort(key=lambda r: -r["bt_elo"])
    return rows


def run_jobs(jobs, workers, progress_every=2000):
    out = []
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_play, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            out.append(f.result())
            if i % progress_every == 0 or i == len(jobs):
                el = time.perf_counter() - t0
                rate = i / el
                print(f"  {i:,}/{len(jobs):,} episodes  {rate:.1f}/s  "
                      f"eta {(len(jobs)-i)/max(rate,1e-9)/60:.1f} min", flush=True)
    return out


def cmd_ingest(args):
    """Fold shard files into one run. The only process that writes the database.

    Sharded runs deliberately do not touch SQLite from the array tasks. Two of
    the three data-integrity incidents in docs/RUNS.md came from concurrent or
    unclosed writers -- a 0-byte database that reported success, and a merge
    that silently wrote into the wrong file. Shards emit append-only JSONL; one
    single-threaded ingest reads them and does all the writing.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    d = args.shards
    meta_path = os.path.join(d, "meta.json")
    if not os.path.exists(meta_path):
        raise SystemExit(f"no meta.json in {d} -- shards not started here?")
    with open(meta_path) as f:
        meta = json.load(f)

    files = sorted(f for f in os.listdir(d) if f.startswith("shard-")
                   and f.endswith(".jsonl"))
    results, seen = [], set()
    for fn in files:
        with open(os.path.join(d, fn)) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                key = (r["left"], r["right"], r["seed"])
                if key in seen:          # a requeued array task reran its shard
                    continue
                seen.add(key)
                results.append(r)
    print(f"{len(files)} shard files, {len(results):,} unique episodes "
          f"(expected {meta['n_jobs']:,})")
    missing = meta["n_jobs"] - len(results)
    if missing:
        print(f"  !! {missing:,} episodes missing -- some shard did not finish. "
              f"Ratings below are over what completed.")

    con = DB.connect()
    manifest_path = os.path.join(meta.get("lib") or "agents/lib", "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            DB.register_agents(con, json.load(f))
    run_id = DB.start_run(con, meta["label"], meta["kind"], meta["seeds"],
                          meta["steps"], meta["n_roster"], meta.get("slurm_job"))
    bad = [r for r in results if any(s != "DONE" for s in r["status"])]
    if bad:
        print(f"  !! {len(bad)} episodes not DONE, e.g. "
              f"{bad[0].get('error') or bad[0]['status']}")
    DB.add_episodes(con, run_id, results)
    DB.finish_run(con, run_id, len(results))
    rows = _rate(results, meta["names"])
    DB.save_ratings(con, run_id, rows)
    _print_table(rows)
    DB.close(con)
    print(f"\nrun #{run_id} stored in {DB.DB_PATH}")
    return 0


def _print_table(rows, n=30):
    print(f"\n{'#':>3}  {'BT-Elo':>8} {'winrate':>8} {'median $':>10}  strategy")
    for i, r in enumerate(rows[:n], 1):
        print(f"{i:>3}  {r['bt_elo']:>+8.0f} {r['winrate']:>8.1%} "
              f"{r['median_money']:>10,.0f}  {r['agent']}")
    if len(rows) > n:
        print(f"     ... {len(rows) - n} more (see tools/db.py top)")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        ap = argparse.ArgumentParser(prog="tournament.py ingest")
        ap.add_argument("ingest")
        ap.add_argument("--shards", required=True)
        return cmd_ingest(ap.parse_args())

    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["panel", "roundrobin", "ghosts"])
    ap.add_argument("--lib", default=None, help="directory of generated strategies")
    ap.add_argument("--agents", nargs="*", default=None)
    ap.add_argument("--panel", nargs="*", default=None)
    ap.add_argument("--from-run", default=None, help="'latest' or a run id")
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=30_000)
    ap.add_argument("-s", "--steps", type=int, default=720)
    ap.add_argument("-j", "--jobs", type=int, default=8)
    ap.add_argument("--label", default=None)
    ap.add_argument("--shard", default=None, metavar="K/N",
                    help="run only this slice of the job list and write JSONL "
                         "instead of the database; fold in with `ingest`")
    ap.add_argument("--shard-dir", default=None,
                    help="where shards are written (default data/shards/<label>)")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    # A shard MUST NOT touch the database. Forty-eight array tasks each opening
    # data/arena.sqlite to register the same manifest corrupted it -- SQLite on
    # a shared Lustre filesystem does not survive that, and the file is the one
    # irreplaceable thing in this project. `--from-run` is the only roster
    # source that needs a read, so it is refused in shard mode rather than
    # quietly opened; pass --agents or --lib instead.
    sharded = bool(args.shard)
    if sharded and args.from_run:
        raise SystemExit("--shard cannot use --from-run: resolve the roster on "
                         "the submitting host and pass --agents explicitly")
    con = None if sharded else DB.connect()

    # ---- roster ----
    if args.from_run:
        run = DB.latest_run(con) if args.from_run == "latest" else {"id": int(args.from_run)}
        rows = con.execute(
            "SELECT agent FROM ratings WHERE run_id=? ORDER BY bt_elo DESC LIMIT ?",
            (run["id"], args.top)).fetchall()
        roster = []
        for r in rows:
            hit = con.execute("SELECT path FROM agents WHERE name=?", (r["agent"],)).fetchone()
            roster.append(hit["path"] if hit else r["agent"])
    elif args.agents:
        roster = args.agents
    elif args.lib:
        roster = sorted(os.path.join(args.lib, f) for f in os.listdir(args.lib)
                        if f.endswith(".py"))
    else:
        raise SystemExit("give --lib, --agents or --from-run")

    manifest_path = os.path.join(args.lib or "agents/lib", "manifest.json")
    if con is not None and os.path.exists(manifest_path):
        with open(manifest_path) as f:
            DB.register_agents(con, json.load(f))

    # ---- job list ----
    if args.kind == "panel":
        panel = args.panel or [p for p in DEFAULT_PANEL
                               if p == "starter" or os.path.exists(p)]
        jobs = []
        panel_short = {short(p) for p in panel}
        for a in roster:
            for b in panel:
                if short(a) == short(b):
                    continue
                for i in range(args.seeds):
                    s = args.seed0 + i
                    jobs.append((a, b, s, args.steps))
                    jobs.append((b, a, s, args.steps))
        names = sorted({short(a) for a in roster} | panel_short)
        label = args.label or f"panel:{os.path.basename(args.lib or 'agents')}"
    elif args.kind == "ghosts":
        # Against recorded trajectories of top-rated players, not against
        # ourselves. A ghost is open-loop and only meaningful on the seed and
        # seat it actually played, so the seed comes from its manifest and the
        # seats are never swapped -- which also means this measurement is not
        # seat-balanced, and is a *field* rather than a duel.
        with open("agents/ghosts/manifest.json") as f:
            gm = json.load(f)
        jobs = []
        for a in roster:
            for g, meta in sorted(gm.items()):
                gp = f"agents/ghosts/{g}.py"
                if meta["seat"] == 0:
                    jobs.append((gp, a, meta["seed"], args.steps))
                else:
                    jobs.append((a, gp, meta["seed"], args.steps))
        names = sorted({short(a) for a in roster} | set(gm))
        label = args.label or f"ghosts:{len(roster)}x{len(gm)}"
    else:
        jobs = []
        for a, b in itertools.combinations(roster, 2):
            for i in range(args.seeds):
                s = args.seed0 + i
                jobs.append((a, b, s, args.steps))
                jobs.append((b, a, s, args.steps))
        names = sorted({short(a) for a in roster})
        label = args.label or f"roundrobin:{len(roster)}"

    if args.shard:
        k, n = (int(x) for x in args.shard.split("/"))
        d = args.shard_dir or os.path.join("data/shards", label.replace(":", "-"))
        os.makedirs(d, exist_ok=True)
        # Every task writes meta.json with the same content, so the ingest step
        # does not depend on which task happens to start first.
        tmp = os.path.join(d, f".meta.{k}.tmp")
        with open(tmp, "w") as f:
            json.dump({"label": label, "kind": args.kind, "seeds": args.seeds,
                       "steps": args.steps, "n_roster": len(roster),
                       "n_jobs": len(jobs), "names": names, "lib": args.lib,
                       "slurm_job": os.environ.get("SLURM_ARRAY_JOB_ID")
                                    or os.environ.get("SLURM_JOB_ID")}, f)
        os.replace(tmp, os.path.join(d, "meta.json"))

        # Stride, not block: consecutive jobs are the same pairing on adjacent
        # seeds, so a block split would give one task all the slow matchups.
        mine = jobs[k::n]
        print(f"{args.kind}: shard {k}/{n} -- {len(mine):,} of {len(jobs):,} "
              f"episodes, {args.jobs} workers")
        results = run_jobs(mine, args.jobs)
        out = os.path.join(d, f"shard-{k:03d}.jsonl")
        part = out + ".part"
        with open(part, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        os.replace(part, out)      # a shard file exists only when it is complete
        bad = [r for r in results if any(s != "DONE" for s in r["status"])]
        print(f"wrote {out} ({len(results):,} episodes, {len(bad)} not DONE)")
        return 0

    print(f"{args.kind}: {len(roster)} strategies, {len(jobs):,} episodes, "
          f"{args.jobs} workers")
    run_id = DB.start_run(con, label, args.kind, args.seeds, args.steps,
                          len(roster), os.environ.get("SLURM_JOB_ID"))
    print(f"run #{run_id}")

    results = run_jobs(jobs, args.jobs)
    bad = [r for r in results if any(s != "DONE" for s in r["status"])]
    if bad:
        print(f"  !! {len(bad)} episodes not DONE, e.g. {bad[0].get('error') or bad[0]['status']}")

    DB.add_episodes(con, run_id, results)
    DB.finish_run(con, run_id, len(results))
    rows = _rate(results, names)
    DB.save_ratings(con, run_id, rows)
    _print_table(rows)
    DB.close(con)
    print(f"\nrun #{run_id} stored in {DB.DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
