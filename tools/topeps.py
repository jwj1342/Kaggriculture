#!/usr/bin/env python
"""Digest the *top* of the ladder, from Kaggle's daily episode datasets.

`tools/ladder.py` pulls the episodes **we** played, so its opponents are matched
to our rating. This pulls the episodes Kaggle publishes each day, which are the
highest-scoring games in the competition: the 2026-08-09 dump averages **3,068 to
3,218** across its participants, against our ~790. These are the games we want to
learn from and will never be matched into.

    kaggle/kaggriculture-episodes-index          625 bytes, one row per day
    kaggle/kaggriculture-episodes-<date>         ~690 episodes, one JSON each

Each episode file is ~32 MB and the day's dump is 21 GB uncompressed, so nothing
is kept: download one file, digest it to ~2 KB, delete, next. Same contract as
`tools/ladder.py`.

    python tools/topeps.py index                  # what days exist
    python tools/topeps.py pull --date 2026-08-09 --limit 60
    python tools/topeps.py stats                  # what the top of the field does

The digest carries the **action histogram** as well as the board and the trades.
That is deliberate: the single largest improvement this project has made came
from noticing that the leader spends 1.02 movement actions per action that does
work while we spent 2.4, and that 50% of their work happens without moving. None
of that is visible in a board-state digest.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB  # noqa: E402

WORK = "data/topeps"
INDEX_DS = "kaggle/kaggriculture-episodes-index"
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS top_episodes (
    episode_id  INTEGER PRIMARY KEY,
    day         TEXT,
    team_a      TEXT,
    team_b      TEXT,
    money_a     REAL,
    money_b     REAL,
    digest_a    TEXT,
    digest_b    TEXT,
    fetched_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_top_day ON top_episodes(day);
"""


def _digest(steps, seat):
    """Board, trades, and -- new here -- what the units spent their turns on."""
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
    acts = Counter()
    hires = 0
    land_day = -1
    # Steps between one action that does work and the next, per unit. The
    # distribution of this is the thing worth having: a median of 0 means the
    # unit is working the tile it is standing on.
    gaps = Counter()
    walked = {}
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
        units = [act.get("farmer")] + (act.get("hands") or [])
        for u, a in enumerate(units):
            if not a:
                continue
            acts[a[0]] += 1
            if a[0] in MOVES:
                walked[u] = walked.get(u, 0) + 1
            elif a[0] != "PASS":
                gaps[min(walked.get(u, 0), 9)] += 1
                walked[u] = 0

    total = sum(acts.values()) or 1
    move = sum(v for k, v in acts.items() if k in MOVES)
    idle = acts.get("PASS", 0)
    work = total - move - idle
    nwork = sum(gaps.values()) or 1

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
            "first_land_day": land_day, "money": money, "herd": herd, "hands": hands,
            "acts": dict(acts),
            "move_frac": round(move / total, 4),
            "pass_frac": round(idle / total, 4),
            "work_frac": round(work / total, 4),
            "steps_per_work": round(move / max(work, 1), 3),
            "zero_move_frac": round(gaps.get(0, 0) / nwork, 4),
            "gap_hist": {str(k): v for k, v in sorted(gaps.items())}}


def _files(slug):
    out, token = [], None
    while True:
        cmd = ["kaggle", "datasets", "files", slug, "--page-size", "200"]
        if token:
            cmd += ["--page-token", token]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout
        token = None
        for line in r.splitlines():
            if line.startswith("Next Page Token = "):
                token = line.split(" = ", 1)[1].strip()
                continue
            p = line.split()
            if p and p[0].endswith(".json"):
                out.append(p[0])
        if not token:
            return out


def cmd_index(args):
    os.makedirs(WORK, exist_ok=True)
    subprocess.run(["kaggle", "datasets", "download", INDEX_DS, "--unzip",
                    "-p", WORK, "--force"], capture_output=True, timeout=300)
    path = os.path.join(WORK, "manifest.csv")
    if not os.path.exists(path):
        print("could not fetch the index")
        return 1
    with open(path) as f:
        rows = [l.rstrip("\n").split(",") for l in f]
    hdr = rows[0]
    i_date, i_n = hdr.index("date"), hdr.index("episode_count")
    i_top, i_med = hdr.index("top_avg_score"), hdr.index("median_avg_score")
    print(f"{'date':12s} {'episodes':>9s} {'top avg':>9s} {'median avg':>11s}")
    for r in rows[1:]:
        if len(r) <= i_med:
            continue
        print(f"{r[i_date]:12s} {r[i_n]:>9s} {float(r[i_top]):>9.0f} {float(r[i_med]):>11.0f}")
    return 0


def cmd_pull(args):
    con = DB.connect()
    con.executescript(SCHEMA)
    os.makedirs(WORK, exist_ok=True)
    have = {r[0] for r in con.execute("SELECT episode_id FROM top_episodes")}
    slug = f"kaggle/kaggriculture-episodes-{args.date}"

    names = _files(slug)
    todo = [n for n in names if int(n[:-5]) not in have][:args.limit]
    print(f"{slug}: {len(names)} files listed, {len(todo)} new")

    n_new = 0
    for k, name in enumerate(todo, 1):
        ep = int(name[:-5])
        path = os.path.join(WORK, name)
        try:
            subprocess.run(["kaggle", "datasets", "download", slug, "-f", name,
                            "-p", WORK, "--force"],
                           capture_output=True, text=True, timeout=900)
            if not os.path.exists(path):          # some CLI versions leave a .zip
                zp = path + ".zip"
                if os.path.exists(zp):
                    import zipfile
                    with zipfile.ZipFile(zp) as z:
                        z.extractall(WORK)
                    os.remove(zp)
            if not os.path.exists(path):
                print(f"    {ep}: download failed")
                continue
            size = os.path.getsize(path)
            with open(path) as f:
                data = json.load(f)
            steps = data["steps"]
            teams = (data.get("info") or {}).get("TeamNames") or ["?", "?"]
            rew = data.get("rewards") or [0, 0]
            con.execute(
                "INSERT OR REPLACE INTO top_episodes(episode_id, day, team_a,"
                " team_b, money_a, money_b, digest_a, digest_b)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (ep, args.date, str(teams[0]), str(teams[1]),
                 float(rew[0] or 0), float(rew[1] or 0),
                 json.dumps(_digest(steps, 0)), json.dumps(_digest(steps, 1))))
            con.commit()
            n_new += 1
            print(f"    [{k}/{len(todo)}] {ep} {size/1e6:>5.1f} MB -> digest | "
                  f"{teams[0][:18]:18s} {rew[0]:>9,.0f}  vs  "
                  f"{teams[1][:18]:18s} {rew[1]:>9,.0f}", flush=True)
        except Exception as e:
            print(f"    {ep}: {type(e).__name__}: {e}")
        finally:
            for p in (path, path + ".zip"):
                if os.path.exists(p):
                    os.remove(p)
    DB.close(con)
    print(f"\n{n_new} new top episodes digested into {DB.DB_PATH}")
    return 0


def cmd_stats(args):
    import statistics as st
    con = DB.connect()
    con.executescript(SCHEMA)
    rows = [dict(r) for r in con.execute("SELECT * FROM top_episodes")]
    if not rows:
        print("nothing yet -- run `pull`")
        return 0
    ds = [json.loads(r[k]) for r in rows for k in ("digest_a", "digest_b")]
    money = [r[k] for r in rows for k in ("money_a", "money_b")]
    print(f"{len(rows)} top episodes, {len(ds)} farms\n")
    print(f"  final money    median {st.median(money):>9,.0f}   "
          f"p90 {sorted(money)[int(len(money)*0.9)]:>9,.0f}")

    def med(f):
        v = [f(d) for d in ds if f(d) is not None]
        return st.median(v) if v else 0

    print("\n=== how the top of the field spends its turns ===")
    print(f"  movement            {med(lambda d: d['move_frac']):>6.1%}")
    print(f"  PASS                {med(lambda d: d['pass_frac']):>6.1%}")
    print(f"  work                {med(lambda d: d['work_frac']):>6.1%}")
    print(f"  steps per work      {med(lambda d: d['steps_per_work']):>6.2f}")
    print(f"  zero-movement work  {med(lambda d: d['zero_move_frac']):>6.1%}")

    print("\n=== what it builds ===")
    for lbl, f in (("quadrants", lambda d: d["land"]),
                   ("animals", lambda d: sum(d["animals"].values())),
                   ("crops standing", lambda d: sum(d["crops"].values())),
                   ("weeds", lambda d: d["weeds"]),
                   ("idle tiles", lambda d: d["empty"]),
                   ("HIRE orders", lambda d: d["hire_orders"]),
                   ("hands at d20", lambda d: d["hands"].get("20", 0))):
        print(f"  {lbl:18s} {med(f):>7.1f}")

    print("\n=== what it sells (median per farm) ===")
    for p in ("STRAWBERRY", "MELON", "MILK", "WOOL", "WHEAT", "FERTILIZER",
              "CARROT", "TOMATO", "EGG"):
        v = med(lambda d, p=p: d["sold"].get(p, 0))
        if v:
            print(f"  {p:12s} {v:>6.0f}")

    print("\n=== strawberry per planting (the fertilizer tell) ===")
    per = [d["sold"].get("STRAWBERRY", 0) / d["bought"]["STRAWBERRY"]
           for d in ds if d["bought"].get("STRAWBERRY", 0) >= 8]
    if per:
        print(f"  median {st.median(per):.1f} over {len(per)} farms "
              f"(unfertilized ceiling 4, fertilized 8)")

    print("\n=== the teams that appear most ===")
    c = Counter()
    for r in rows:
        c[r["team_a"]] += 1
        c[r["team_b"]] += 1
    for t, n in c.most_common(10):
        print(f"  {n:>4d}  {t}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index").set_defaults(fn=cmd_index)
    p = sub.add_parser("pull")
    p.add_argument("--date", required=True)
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(fn=cmd_pull)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    args = ap.parse_args()
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
