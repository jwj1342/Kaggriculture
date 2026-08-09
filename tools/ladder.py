#!/usr/bin/env python
"""Pull our own ladder replays, digest them, and throw the raw files away.

Why this is the most valuable data source we have: these are episodes *we*
played, so the opponents are real competitors matched to our rating -- not the
594 strategies we wrote ourselves. Everything measured locally so far was
measured in an echo chamber.

Why the raw files cannot be kept: a replay is **19.3 MB**, and all of it is
`steps`. The format stores the *complete* 10x10 board for both players in every
one of the 720 steps, for each of the two agents -- 5.7 MB of tiles alone. The
actual information, the actions taken, is 0.2 KB per step per agent, about
0.3 MB for the whole episode. The rest is the same board re-serialised 1,440
times.

So each replay is downloaded, reduced to a ~3 KB digest, written to
`data/arena.sqlite`, and deleted. 100 episodes go from 1.9 GB to about 300 KB.

    python tools/ladder.py pull                 # all submissions
    python tools/ladder.py pull --submission 55358912
    python tools/ladder.py stats                # what the real field looks like

Only our own agent's logs are fetchable (`logs <ep> <our_seat>`); the opponent's
return 403. The replay carries both players' actions anyway, which is what
matters.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB  # noqa: E402

WORK = "data/ladder"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ladder_episodes (
    episode_id    INTEGER PRIMARY KEY,
    submission_id INTEGER,
    created_at    TEXT,
    our_seat      INTEGER,
    our_money     REAL,
    their_money   REAL,
    our_status    TEXT,
    their_status  TEXT,
    won           INTEGER,
    shops         TEXT,
    prices        TEXT,
    our_digest    TEXT,
    their_digest  TEXT,
    fetched_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_ladder_sub ON ladder_episodes(submission_id);
"""


def _digest(steps, seat):
    """The same shape as tools/tournament.py's digest, from a replay instead."""
    final = steps[-1][0]["observation"]
    farm = final["farms"][seat]
    crops, animals, structs = Counter(), Counter(), Counter()
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

    sold, bought = Counter(), Counter()
    hires = 0
    land_day = -1
    for i, step in enumerate(steps):
        act = (step[seat].get("action") or {})
        for o in (act.get("market") or []):
            if not isinstance(o, list) or not o:
                continue
            if o[0] == "SELL" and len(o) >= 3:
                sold[o[1]] += int(o[2])
            elif o[0] in ("BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(o) >= 3:
                bought[o[1]] += int(o[2])
            elif o[0] == "HIRE":
                hires += 1
            elif o[0] == "BUY_LAND" and land_day < 0:
                land_day = i // 24

    money, herd, hands = {}, {}, {}
    for d in (5, 10, 15, 20, 25, 29):
        i = d * 24 + 12
        if i < len(steps):
            f = steps[i][0]["observation"]["farms"][seat]
            money[str(d)] = round(float(f["money"]), 0)
            herd[str(d)] = sum(1 for row in f["tiles"] for t in row
                               if isinstance(t, dict) and "animal" in t)
            hands[str(d)] = len(f.get("hands") or [])

    return {"crops": dict(crops), "animals": dict(animals), "structs": dict(structs),
            "weeds": weeds, "empty": empty, "land": len(farm["unlocked_quadrants"]),
            "sold": dict(sold), "bought": dict(bought), "hire_orders": hires,
            "first_land_day": land_day, "money": money, "herd": herd, "hands": hands}


def _episode_ids(submission):
    out = subprocess.run(["kaggle", "competitions", "episodes", str(submission)],
                         capture_output=True, text=True, timeout=180).stdout
    ids = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].isdigit() and "COMPLETED" in line:
            if "VALIDATION" in line:
                continue
            ids.append((int(parts[0]), parts[1] + " " + parts[2]))
    return ids


def _submissions():
    out = subprocess.run(["kaggle", "competitions", "submissions", "kaggriculture"],
                         capture_output=True, text=True, timeout=180).stdout
    subs = []
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0].isdigit() and "COMPLETE" in line:
            subs.append(int(parts[0]))
    return subs


def cmd_pull(args):
    con = DB.connect()
    con.executescript(SCHEMA)
    os.makedirs(WORK, exist_ok=True)
    have = {r[0] for r in con.execute("SELECT episode_id FROM ladder_episodes")}

    subs = [args.submission] if args.submission else _submissions()
    print(f"submissions: {subs}")
    total_new = 0
    for sub in subs:
        eps = _episode_ids(sub)
        todo = [(e, t) for e, t in eps if e not in have][:args.limit]
        print(f"  submission {sub}: {len(eps)} listed, {len(todo)} new")
        for n, (ep, created) in enumerate(todo, 1):
            path = os.path.join(WORK, f"episode-{ep}-replay.json")
            r = subprocess.run(["kaggle", "competitions", "replay", str(ep),
                                "-p", WORK], capture_output=True, text=True, timeout=600)
            if not os.path.exists(path):
                print(f"    {ep}: download failed -- {r.stdout.strip()[:90]}")
                continue
            size = os.path.getsize(path)
            try:
                with open(path) as f:
                    data = json.load(f)
                steps = data["steps"]
                rewards = data.get("rewards") or [
                    steps[-1][0].get("reward"), steps[-1][1].get("reward")]
                statuses = data.get("statuses") or [
                    steps[-1][0].get("status"), steps[-1][1].get("status")]
                # Which seat were we? The submission's own logs are only
                # fetchable for our seat, but the cheap tell is that our digest
                # should match a farm -- instead, use `info` when present and
                # otherwise record both and mark seat as unknown.
                seat = args.seat
                if seat is None:
                    seat = _our_seat(ep)
                if seat is None:
                    print(f"    {ep}: could not determine our seat, skipping")
                    continue
                other = 1 - seat
                obs = steps[-1][0]["observation"]
                con.execute(
                    "INSERT OR REPLACE INTO ladder_episodes(episode_id, submission_id,"
                    " created_at, our_seat, our_money, their_money, our_status,"
                    " their_status, won, shops, prices, our_digest, their_digest)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ep, sub, created, seat,
                     float(rewards[seat] or 0), float(rewards[other] or 0),
                     str(statuses[seat]), str(statuses[other]),
                     1 if (rewards[seat] or 0) > (rewards[other] or 0) else 0,
                     json.dumps(obs["town"]["unlocked_shops"]),
                     json.dumps(obs["market"]["prices"]),
                     json.dumps(_digest(steps, seat)),
                     json.dumps(_digest(steps, other))))
                con.commit()
                total_new += 1
                print(f"    [{n}/{len(todo)}] {ep} {size/1e6:>5.1f} MB -> digest, "
                      f"seat {seat}, {'WIN ' if (rewards[seat] or 0) > (rewards[other] or 0) else 'LOSS'} "
                      f"{float(rewards[seat] or 0):>8,.0f} vs {float(rewards[other] or 0):>8,.0f}",
                      flush=True)
            except Exception as e:
                print(f"    {ep}: parse failed {type(e).__name__}: {e}")
            finally:
                # The raw replay is 19 MB of re-serialised board state. Never keep it.
                if os.path.exists(path):
                    os.remove(path)
    DB.close(con)
    print(f"\n{total_new} new episodes digested into {DB.DB_PATH}")
    return 0


def _our_seat(episode_id):
    """Which seat was ours, determined rather than guessed.

    The replay does not say. But agent logs are only fetchable for your own
    agent -- the opponent's return HTTP 403 -- so asking for seat 0's logs
    answers it definitively. One extra call per episode, and worth it: guessing
    wrong would mirror every opponent statistic in the dataset.
    """
    r = subprocess.run(["kaggle", "competitions", "logs", str(episode_id), "0",
                        "-p", WORK], capture_output=True, text=True, timeout=180)
    blob = (r.stdout or "") + (r.stderr or "")
    for f in os.listdir(WORK):
        if f.startswith(f"episode-{episode_id}-agent-"):
            os.remove(os.path.join(WORK, f))
    if "403" in blob or "Forbidden" in blob:
        return 1
    if "downloaded" in blob.lower():
        return 0
    return None          # undetermined; caller decides


def cmd_stats(args):
    con = DB.connect()
    con.executescript(SCHEMA)
    rows = [dict(r) for r in con.execute("SELECT * FROM ladder_episodes")]
    if not rows:
        print("no ladder episodes yet -- run `pull`")
        return 0
    import statistics
    wins = sum(r["won"] for r in rows)
    print(f"{len(rows)} ladder episodes, {wins} won ({wins/len(rows):.0%})")
    print(f"  our money   median {statistics.median([r['our_money'] for r in rows]):>9,.0f}")
    print(f"  their money median {statistics.median([r['their_money'] for r in rows]):>9,.0f}")

    print("\n=== what the real field actually builds (opponent digests) ===")
    ds = [json.loads(r["their_digest"]) for r in rows if r["their_digest"]]
    if not ds:
        return 0

    def med(f):
        v = [f(d) for d in ds if f(d) is not None]
        return statistics.median(v) if v else 0

    print(f"  quadrants owned   median {med(lambda d: d.get('land')):>5.1f}")
    print(f"  animals at end    median {med(lambda d: sum(d.get('animals', {}).values())):>5.1f}")
    print(f"  crops at end      median {med(lambda d: sum(d.get('crops', {}).values())):>5.1f}")
    print(f"  weeds left        median {med(lambda d: d.get('weeds', 0)):>5.1f}")
    print(f"  idle tiles        median {med(lambda d: d.get('empty', 0)):>5.1f}")
    print(f"  HIRE orders       median {med(lambda d: d.get('hire_orders', 0)):>5.0f}")
    print("  sold, median per episode:")
    for p in ("MELON", "MILK", "WOOL", "STRAWBERRY", "EGG", "WHEAT", "CARROT",
              "TOMATO", "FERTILIZER"):
        v = med(lambda d, p=p: d.get("sold", {}).get(p, 0))
        if v:
            print(f"    {p:12s} {v:>6.0f}")
    comp = Counter()
    for d in ds:
        key = (tuple(sorted(d.get("animals", {}).items())),
               tuple(sorted(d.get("crops", {}).items())), d.get("land"))
        comp[key] += 1
    print("\n  most common opponent shapes:")
    for (an, cr, land), n in comp.most_common(5):
        print(f"    x{n:<3} land {land}  animals {dict(an)}  crops {dict(cr)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pull")
    p.add_argument("--submission", type=int, default=None)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--seat", type=int, default=None,
                   help="our seat, if known; otherwise assumed 0")
    p.set_defaults(fn=cmd_pull)
    s = sub.add_parser("stats")
    s.set_defaults(fn=cmd_stats)
    args = ap.parse_args()
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
