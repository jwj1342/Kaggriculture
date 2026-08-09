#!/usr/bin/env python
"""SQLite store for every episode this project has ever run.

One file, no server, queryable from anything. The point is that a result never
has to be re-derived: any past claim can be re-checked with a query, and a new
tournament can reuse episodes it has already paid for.

Episodes keep a **digest**, not a full replay. A raw replay is ~27 MB; the digest
is ~1 KB and holds what analysis actually needs -- final composition, per-product
sales, the money curve, the shop draw.

    python tools/db.py init
    python tools/db.py stats
    python tools/db.py top --run latest
"""

import argparse
import json
import os
import sqlite3
import sys

# `KG_DB` redirects every writer in the project at once. It exists so a test can
# be run against a scratch database without editing anything: a test that meant
# to write elsewhere and wrote here instead is what duplicated runs #1 and #2
# into 170,128 episodes (docs/RUNS.md, data integrity incidents).
DB_PATH = os.environ.get("KG_DB") or "data/arena.sqlite"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS agents (
    name        TEXT PRIMARY KEY,
    alias       TEXT,
    path        TEXT,
    atoms       TEXT,          -- JSON: {land, labour, produce, market, intel, muck}
    sha         TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT,
    kind        TEXT,          -- panel | roundrobin | h2h
    seeds       INTEGER,
    steps       INTEGER,
    n_agents    INTEGER,
    n_episodes  INTEGER,
    slurm_job   TEXT,
    started_at  TEXT DEFAULT (datetime('now')),
    finished_at TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS episodes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER REFERENCES runs(id),
    seed        INTEGER,
    left_agent  TEXT,
    right_agent TEXT,
    left_money  REAL,
    right_money REAL,
    left_status TEXT,
    right_status TEXT,
    shops       TEXT,          -- JSON list
    prices      TEXT,          -- JSON final price vector
    left_digest TEXT,          -- JSON: composition, sales, money curve
    right_digest TEXT,
    wall        REAL
);

CREATE INDEX IF NOT EXISTS ix_ep_run   ON episodes(run_id);
CREATE INDEX IF NOT EXISTS ix_ep_left  ON episodes(left_agent);
CREATE INDEX IF NOT EXISTS ix_ep_right ON episodes(right_agent);
CREATE INDEX IF NOT EXISTS ix_ep_pair  ON episodes(left_agent, right_agent);

CREATE TABLE IF NOT EXISTS ratings (
    run_id       INTEGER REFERENCES runs(id),
    agent        TEXT,
    bt_strength  REAL,
    bt_elo       REAL,
    games        INTEGER,
    wins         REAL,
    winrate      REAL,
    median_money REAL,
    sd_money     REAL,
    computed_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (run_id, agent)
);
"""


def connect(path=None):
    # Resolve DB_PATH at call time, not at import time. `def connect(path=DB_PATH)`
    # binds the default once, so reassigning DB_PATH afterwards silently had no
    # effect while log messages still reported the new path -- which once wrote a
    # test merge into the real database.
    path = path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path, timeout=120)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def register_agents(con, manifest):
    """manifest: list of {name, alias, path, atoms, sha}."""
    con.executemany(
        "INSERT INTO agents(name, alias, path, atoms, sha) VALUES(?,?,?,?,?) "
        "ON CONFLICT(name) DO UPDATE SET alias=excluded.alias, path=excluded.path, "
        "atoms=excluded.atoms, sha=excluded.sha",
        [(m["name"], m.get("alias"), m["path"], json.dumps(m.get("atoms", {})), m.get("sha"))
         for m in manifest])
    con.commit()


def start_run(con, label, kind, seeds, steps, n_agents, slurm_job=None, notes=None):
    cur = con.execute(
        "INSERT INTO runs(label, kind, seeds, steps, n_agents, slurm_job, notes) "
        "VALUES(?,?,?,?,?,?,?)", (label, kind, seeds, steps, n_agents, slurm_job, notes))
    con.commit()
    return cur.lastrowid


def add_episodes(con, run_id, rows):
    con.executemany(
        "INSERT INTO episodes(run_id, seed, left_agent, right_agent, left_money, "
        "right_money, left_status, right_status, shops, prices, left_digest, "
        "right_digest, wall) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(run_id, r["seed"], r["left"], r["right"], r["money"][0], r["money"][1],
          r["status"][0], r["status"][1], json.dumps(r["shops"]),
          json.dumps(r["prices"]), json.dumps(r["digest"][0]),
          json.dumps(r["digest"][1]), r.get("wall", 0.0)) for r in rows])
    con.commit()


def finish_run(con, run_id, n_episodes):
    con.execute("UPDATE runs SET finished_at=datetime('now'), n_episodes=? WHERE id=?",
                (n_episodes, run_id))
    con.commit()


def save_ratings(con, run_id, rows):
    con.executemany(
        "INSERT INTO ratings(run_id, agent, bt_strength, bt_elo, games, wins, "
        "winrate, median_money, sd_money) VALUES(?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(run_id, agent) DO UPDATE SET bt_strength=excluded.bt_strength, "
        "bt_elo=excluded.bt_elo, games=excluded.games, wins=excluded.wins, "
        "winrate=excluded.winrate, median_money=excluded.median_money, "
        "sd_money=excluded.sd_money",
        [(run_id, r["agent"], r["bt_strength"], r["bt_elo"], r["games"], r["wins"],
          r["winrate"], r["median_money"], r["sd_money"]) for r in rows])
    con.commit()


def close(con):
    """Checkpoint and close. The database is in WAL mode, so committed rows sit
    in the -wal file until a checkpoint; a writer that exits without one can
    leave a 0-byte database that reported success."""
    try:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        con.close()


def latest_run(con, kind=None):
    q = "SELECT * FROM runs WHERE finished_at IS NOT NULL"
    if kind:
        q += f" AND kind='{kind}'"
    q += " ORDER BY id DESC LIMIT 1"
    r = con.execute(q).fetchone()
    return dict(r) if r else None


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("stats")
    t = sub.add_parser("top")
    t.add_argument("--run", default="latest")
    t.add_argument("-n", type=int, default=25)
    q = sub.add_parser("sql")
    q.add_argument("query")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    con = connect()

    if args.cmd == "init":
        print(f"initialised {DB_PATH}")
    elif args.cmd == "stats":
        for tbl in ("agents", "runs", "episodes", "ratings"):
            n = con.execute(f"SELECT COUNT(*) c FROM {tbl}").fetchone()["c"]
            print(f"  {tbl:10s} {n:>9,}")
        print("\n  runs:")
        for r in con.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 10"):
            print(f"    #{r['id']:<4} {r['label'][:34]:34s} {r['kind']:11s} "
                  f"{r['n_agents'] or 0:>5} agents {r['n_episodes'] or 0:>8,} eps  "
                  f"{r['finished_at'] or 'RUNNING'}")
        sz = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        print(f"\n  file size {sz/1e6:.1f} MB")
    elif args.cmd == "top":
        run = latest_run(con) if args.run == "latest" else {"id": int(args.run)}
        if not run:
            print("no finished runs")
            return 1
        print(f"run #{run['id']}")
        for r in con.execute(
                "SELECT * FROM ratings WHERE run_id=? ORDER BY bt_elo DESC LIMIT ?",
                (run["id"], args.n)):
            print(f"  {r['bt_elo']:>+8.0f}  {r['winrate']:>6.1%}  "
                  f"{r['median_money']:>10,.0f}  {r['agent']}")
    elif args.cmd == "sql":
        for row in con.execute(args.query):
            print(dict(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
