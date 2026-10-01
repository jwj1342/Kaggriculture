#!/usr/bin/env python
"""Historical tools for the project's Cloudflare D1 mirror.

The 2026-10-01 postmortem moves this mirror to GitHub Release. See
docs/ARCHIVE.md for migration status and offline restore instructions.
The following describes the original development workflow.

D1 is this project's **published mirror**: collaborators query it directly and
never need a cluster account or a downloaded file. `data/arena.sqlite` stays the
source of truth -- tournaments write there, and sync is one-way, local to remote.
See docs/CONTRIBUTING.md "The sync contract".

Four tiers, in increasing size:

    runs / agents      what was run, and what each strategy is        ~600 rows
    ratings            Bradley-Terry standings per run                ~600 rows
    matchups           pairwise aggregate: games, wins, median money  ~4,300 rows
    episodes           one row per played game, with digests        85,000+ rows

The first three go up over the HTTP query API in about two minutes. Episodes go
through D1's **bulk import** endpoint (SQL file -> R2 -> server-side ingest),
which ingested 85,064 rows in 4 s. Do not insert them a statement at a time: the
same data over the query API is ~14,000 requests and roughly 50 minutes.

Two D1 limits caused real failures here and are handled below:

  * **bound parameters** are capped far below SQLite's limit. 900 gives
    `too many SQL variables`; MAX_PARAMS is 90.
  * **statement length** is capped. 200-row `INSERT ... VALUES` statements
    (~280 KB) give `statement too long: SQLITE_TOOBIG`; the dump caps statements
    at MAX_STMT_BYTES.

Credentials come from a git-ignored `*.secret` in the project root:

    ID:  <cloudflare account id>
    API: <api token with D1 edit permission>

`CF_ACCOUNT_ID` / `CF_D1_DATABASE_ID` / `CF_API_TOKEN` override it. The database
id is discovered by name when not given.

    python tools/d1.py check                 # connectivity and row counts
    python tools/d1.py schema                # create tables
    python tools/d1.py push                  # meta + matchups (idempotent)
    python tools/d1.py push --episodes       # also episodes for runs D1 lacks
    python tools/d1.py mirror local.sqlite   # materialise D1 back into a file
    python tools/d1.py query "SELECT ..."
    python tools/d1.py top -n 20

Access control is on you. This database is the whole measurement programme --
85,000 measured episodes and the evidence behind every claim in docs/. Anything
put in front of it must be authenticated.
"""

import argparse
import glob
import hashlib
import json
import os
import sqlite3
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB  # noqa: E402

API = "https://api.cloudflare.com/client/v4"
MAX_PARAMS = 90          # D1 caps bound parameters far below SQLite
MAX_STMT_BYTES = 60_000  # D1 caps statement length; 280 KB was rejected
PAGE = 500               # rows per page when mirroring back out

SECRET_KEYS = {
    "ID": "CF_ACCOUNT_ID", "ACCOUNT": "CF_ACCOUNT_ID", "ACCOUNT_ID": "CF_ACCOUNT_ID",
    "API": "CF_API_TOKEN", "TOKEN": "CF_API_TOKEN", "API_TOKEN": "CF_API_TOKEN",
    "DB": "CF_D1_DATABASE_ID", "DATABASE": "CF_D1_DATABASE_ID",
    "DATABASE_ID": "CF_D1_DATABASE_ID",
}
DB_NAME = os.environ.get("CF_D1_DATABASE_NAME", "kaggriculture")
_CACHE = {}

EPISODE_COLS = ["run_id", "seed", "left_agent", "right_agent", "left_money",
                "right_money", "left_status", "right_status", "shops", "prices",
                "left_digest", "right_digest", "wall"]

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS agents (
         name TEXT PRIMARY KEY, alias TEXT, path TEXT, atoms TEXT, sha TEXT,
         created_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS runs (
         id INTEGER PRIMARY KEY, label TEXT, kind TEXT, seeds INTEGER,
         steps INTEGER, n_agents INTEGER, n_episodes INTEGER, slurm_job TEXT,
         started_at TEXT, finished_at TEXT, notes TEXT)""",
    """CREATE TABLE IF NOT EXISTS ratings (
         run_id INTEGER, agent TEXT, bt_strength REAL, bt_elo REAL,
         games INTEGER, wins REAL, winrate REAL, median_money REAL,
         sd_money REAL, computed_at TEXT,
         PRIMARY KEY (run_id, agent))""",
    # Pairwise aggregate: a tenth the rows of `episodes`, and enough for a win
    # matrix, a head-to-head record or a Bradley-Terry refit. Canonically
    # ordered (agent_a < agent_b) so a pairing is stored once regardless of seat.
    """CREATE TABLE IF NOT EXISTS matchups (
         run_id INTEGER, agent_a TEXT, agent_b TEXT,
         games INTEGER, wins_a REAL, ties INTEGER,
         money_a REAL, money_b REAL,
         PRIMARY KEY (run_id, agent_a, agent_b))""",
    """CREATE TABLE IF NOT EXISTS episodes (
         id INTEGER PRIMARY KEY, run_id INTEGER, seed INTEGER,
         left_agent TEXT, right_agent TEXT, left_money REAL, right_money REAL,
         left_status TEXT, right_status TEXT, shops TEXT, prices TEXT,
         left_digest TEXT, right_digest TEXT, wall REAL)""",
    "CREATE INDEX IF NOT EXISTS ix_ratings_elo ON ratings(run_id, bt_elo DESC)",
    "CREATE INDEX IF NOT EXISTS ix_matchups_a ON matchups(run_id, agent_a)",
    "CREATE INDEX IF NOT EXISTS ix_episodes_run ON episodes(run_id)",
]

TABLES = (
    ("agents", ["name", "alias", "path", "atoms", "sha", "created_at"]),
    ("runs", ["id", "label", "kind", "seeds", "steps", "n_agents",
              "n_episodes", "slurm_job", "started_at", "finished_at", "notes"]),
    ("ratings", ["run_id", "agent", "bt_strength", "bt_elo", "games", "wins",
                 "winrate", "median_money", "sd_money", "computed_at"]),
    ("matchups", ["run_id", "agent_a", "agent_b", "games", "wins_a", "ties",
                  "money_a", "money_b"]),
)

MATCHUP_DDL = """CREATE TABLE IF NOT EXISTS matchups (
    run_id INTEGER, agent_a TEXT, agent_b TEXT, games INTEGER,
    wins_a REAL, ties INTEGER, money_a REAL, money_b REAL,
    PRIMARY KEY (run_id, agent_a, agent_b))"""


# --------------------------------------------------------------------------
# credentials and transport
# --------------------------------------------------------------------------

def _load_secret():
    out = {}
    for path in sorted(glob.glob("*.secret")) + [".secret"]:
        if not os.path.exists(path):
            continue
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, sep, v = line.partition(":")
            if not sep:
                k, sep, v = line.partition("=")
            if not sep:
                continue
            key = SECRET_KEYS.get(k.strip().upper())
            if key:
                out[key] = v.strip().strip('"').strip("'")
        break
    return out


def _cfg():
    if _CACHE:
        return _CACHE["acct"], _CACHE["dbid"], _CACHE["token"]
    vals = _load_secret()
    for k in ("CF_ACCOUNT_ID", "CF_D1_DATABASE_ID", "CF_API_TOKEN"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    acct, token = vals.get("CF_ACCOUNT_ID"), vals.get("CF_API_TOKEN")
    if not acct or not token:
        raise SystemExit(
            "need a Cloudflare account id and API token.\n"
            "  Put them in a git-ignored <name>.secret in the project root:\n"
            "      ID: <account id>\n"
            "      API: <api token>\n"
            "  or export CF_ACCOUNT_ID / CF_API_TOKEN.")
    dbid = vals.get("CF_D1_DATABASE_ID")
    if not dbid:
        import requests
        r = requests.get(f"{API}/accounts/{acct}/d1/database",
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        body = r.json()
        if not body.get("success"):
            raise SystemExit("could not list D1 databases: "
                             f"{json.dumps(body.get('errors') or body)[:300]}")
        dbs = body.get("result", [])
        match = [d for d in dbs if d.get("name") == DB_NAME]
        if not match:
            raise SystemExit("no D1 database with the exact project name; "
                             "see docs/ARCHIVE.md for the archived snapshot")
        if len(match) != 1:
            raise SystemExit("multiple matching D1 databases; set CF_D1_DATABASE_ID explicitly")
        dbid = match[0]["uuid"]
    _CACHE.update(acct=acct, dbid=dbid, token=token)
    return acct, dbid, token


def _base():
    acct, dbid, _ = _cfg()
    return f"{API}/accounts/{acct}/d1/database/{dbid}"


def _headers():
    _, _, token = _cfg()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _post(sql, params=None):
    import requests
    r = requests.post(f"{_base()}/query", headers=_headers(),
                      json={"sql": sql, "params": params or []}, timeout=120)
    try:
        body = r.json()
    except Exception:
        raise SystemExit(f"D1 returned non-JSON (HTTP {r.status_code}): {r.text[:300]}")
    if not body.get("success"):
        raise SystemExit(f"D1 error (HTTP {r.status_code}): "
                         f"{json.dumps(body.get('errors') or body)[:500]}")
    return body["result"]


def _q(sql, params=None):
    out = []
    for block in _post(sql, params):
        out.extend(block.get("results") or [])
    return out


def _short(path):
    return (os.path.splitext(os.path.basename(path))[0]
            if str(path).endswith(".py") else path)


# --------------------------------------------------------------------------
# the small tiers, over the query API
# --------------------------------------------------------------------------

def _matchup_rows():
    """Collapse episodes into one row per (run, unordered pair)."""
    con = DB.connect()
    con.row_factory = sqlite3.Row
    agg = {}
    for e in con.execute("SELECT run_id, left_agent, right_agent, left_money, "
                         "right_money FROM episodes"):
        a, b = _short(e["left_agent"]), _short(e["right_agent"])
        ma, mb = e["left_money"], e["right_money"]
        if a > b:
            a, b, ma, mb = b, a, mb, ma
        d = agg.setdefault((e["run_id"], a, b),
                           {"g": 0, "w": 0.0, "t": 0, "a": [], "b": []})
        d["g"] += 1
        d["a"].append(ma)
        d["b"].append(mb)
        if ma > mb:
            d["w"] += 1
        elif ma == mb:
            d["w"] += 0.5
            d["t"] += 1
    con.close()
    return [[rid, a, b, d["g"], d["w"], d["t"],
             statistics.median(d["a"]), statistics.median(d["b"])]
            for (rid, a, b), d in agg.items()]


def _remote_state():
    """What D1 already holds, so a push can send only the difference.

    The free tier allows 100,000 row writes per day and a full episodes import
    is 85,064 of them, so an unconditional re-push of every tier is not a
    harmless idempotent operation -- it is most of a day's budget.
    """
    tables = {r["name"] for r in
              _q("SELECT name FROM sqlite_master WHERE type='table'")}
    st = {"agents": {}, "runs": set(), "ratings": set(), "matchups": set()}
    if "agents" in tables:
        st["agents"] = {r["name"]: r["sha"] for r in
                        _q("SELECT name, sha FROM agents")}
    if "runs" in tables:
        st["runs"] = {r["id"] for r in _q("SELECT id FROM runs")}
    for t in ("ratings", "matchups"):
        if t in tables:
            st[t] = {r["run_id"] for r in
                     _q(f"SELECT DISTINCT run_id FROM {t}")}
    return st


def _batches(force=False):
    """Multi-row INSERT OR REPLACE statements for the small tiers.

    Without `force`, only rows D1 is missing are emitted: agents whose source
    hash differs, and runs/ratings/matchups for run ids it does not have.
    """
    remote = {} if force else _remote_state()
    con = DB.connect()
    con.row_factory = sqlite3.Row
    out = []
    skipped = 0
    for t, cols in TABLES:
        if t == "matchups":
            rows = _matchup_rows()
        else:
            rows = [[r[c] for c in cols]
                    for r in con.execute(f"SELECT {','.join(cols)} FROM {t}")]
        if remote:
            before = len(rows)
            if t == "agents":
                have = remote["agents"]
                rows = [r for r in rows if have.get(r[0]) != r[4]]
            elif t == "runs":
                rows = [r for r in rows if r[0] not in remote["runs"]]
            else:
                rows = [r for r in rows if r[0] not in remote[t]]
            skipped += before - len(rows)
        if not rows:
            continue
        per = max(1, MAX_PARAMS // len(cols))
        marks = "(" + ",".join("?" * len(cols)) + ")"
        for i in range(0, len(rows), per):
            chunk = rows[i:i + per]
            out.append((f"INSERT OR REPLACE INTO {t}({','.join(cols)}) VALUES "
                        + ",".join([marks] * len(chunk)),
                        [v for row in chunk for v in row], len(chunk)))
    con.close()
    if skipped:
        print(f"  skipping {skipped:,} rows already in D1 "
              f"(pass --force to rewrite them)")
    return out


# --------------------------------------------------------------------------
# episodes, over the bulk import endpoint
# --------------------------------------------------------------------------

def _lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def _dump_episodes(run_ids, path):
    """Write INSERT statements for these runs, each under MAX_STMT_BYTES."""
    con = DB.connect()
    head = f"INSERT INTO episodes({','.join(EPISODE_COLS)}) VALUES "
    n = stmts = 0
    with open(path, "w") as f:
        buf, size = [], len(head)
        ids = ",".join(str(int(r)) for r in run_ids)
        for r in con.execute(f"SELECT {','.join(EPISODE_COLS)} FROM episodes "
                             f"WHERE run_id IN ({ids})"):
            tup = "(" + ",".join(_lit(v) for v in r) + ")"
            if buf and size + len(tup) + 1 > MAX_STMT_BYTES:
                f.write(head + ",".join(buf) + ";\n")
                stmts += 1
                buf, size = [], len(head)
            buf.append(tup)
            size += len(tup) + 1
            n += 1
        if buf:
            f.write(head + ",".join(buf) + ";\n")
            stmts += 1
    con.close()
    return n, stmts


def _bulk_import(path, log=print):
    """init -> PUT to R2 -> ingest -> poll."""
    import requests
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    etag = h.hexdigest()
    log(f"  {os.path.getsize(path)/1e6:.1f} MB, md5 {etag[:12]}")

    b = requests.post(f"{_base()}/import", headers=_headers(),
                      json={"action": "init", "etag": etag}, timeout=120).json()
    if not b.get("success"):
        raise SystemExit(f"  init failed: {json.dumps(b.get('errors'))[:400]}")
    res = b["result"]
    filename = res.get("filename")
    if res.get("upload_url"):
        log("  uploading to R2 ...")
        t0 = time.time()
        with open(path, "rb") as f:
            ru = requests.put(res["upload_url"], data=f, timeout=3600)
        if ru.status_code not in (200, 201):
            raise SystemExit(f"  upload failed HTTP {ru.status_code}: {ru.text[:200]}")
        log(f"  uploaded in {time.time()-t0:.0f}s")
    else:
        # Same etag already on the server -- skip straight to ingest. Note the
        # init response then carries the *previous* attempt's status, including
        # its error, which is how a SQLITE_TOOBIG failure first surfaced.
        log("  file already uploaded (etag matched)")
        if res.get("error"):
            raise SystemExit(f"  previous ingest of this file failed: {res['error']}")

    log("  ingesting ...")
    t0 = time.time()
    b = requests.post(f"{_base()}/import", headers=_headers(),
                      json={"action": "ingest", "etag": etag, "filename": filename},
                      timeout=900).json()
    if not b.get("success"):
        raise SystemExit(f"  ingest failed: {json.dumps(b.get('errors'))[:600]}")
    res = b["result"]
    bookmark = res.get("at_bookmark")
    for _ in range(720):
        if res.get("error"):
            raise SystemExit(f"  ingest error: {res['error']}")
        if res.get("success") or res.get("status") == "complete":
            log(f"  ingest complete in {time.time()-t0:.0f}s")
            return
        time.sleep(3)
        b = requests.post(f"{_base()}/import", headers=_headers(),
                          json={"action": "poll", "current_bookmark": bookmark},
                          timeout=300).json()
        if not b.get("success"):
            raise SystemExit(f"  poll failed: {json.dumps(b.get('errors'))[:400]}")
        res = b["result"]
    raise SystemExit("  timed out waiting for ingest")


def _episode_counts_remote():
    return {r["run_id"]: r["n"] for r in
            _q("SELECT run_id, COUNT(*) AS n FROM episodes GROUP BY run_id")}


def _episode_counts_local():
    con = DB.connect()
    out = {r[0]: r[1] for r in
           con.execute("SELECT run_id, COUNT(*) FROM episodes GROUP BY run_id")}
    con.close()
    return out


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_check(args):
    import requests
    _, _, token = _cfg()
    meta = (requests.get(_base(), headers={"Authorization": f"Bearer {token}"},
                         timeout=60).json().get("result") or {})
    if meta:
        print(f"database {meta.get('name')!r}  {meta.get('file_size', 0)/1e6:.1f} MB  "
              f"region {meta.get('running_in_region')}")
    tables = [r["name"] for r in
              _q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print(f"tables: {tables or '(none -- run `schema`)'}")
    for t in ("agents", "runs", "ratings", "matchups", "episodes"):
        if t in tables:
            print(f"  {t:9s} {_q(f'SELECT COUNT(*) AS n FROM {t}')[0]['n']:>8,} rows")
    return 0


def cmd_schema(args):
    for stmt in SCHEMA:
        _post(stmt)
    print(f"applied {len(SCHEMA)} schema statements")
    return cmd_check(args)


def cmd_push(args):
    batches = _batches(force=args.force)
    n_rows = sum(n for _, _, n in batches)
    print(f"meta + matchups: {n_rows:,} rows to write in {len(batches)} requests")
    if not args.dry_run:
        sent = 0
        for sql, params, n in batches:
            _post(sql, params)
            sent += n
            print(f"  {sent:,}/{n_rows:,}", end="\r", flush=True)
        print(f"  {sent:,}/{n_rows:,} uploaded")

    if args.episodes:
        local = _episode_counts_local()
        remote = _episode_counts_remote()
        missing = sorted(r for r, n in local.items() if remote.get(r, 0) != n)
        if not missing:
            print(f"episodes: in sync ({sum(local.values()):,} rows, "
                  f"{len(local)} runs)")
        else:
            total = sum(local[r] for r in missing)
            print(f"episodes: runs {missing} out of sync -> {total:,} rows")
            for r in missing:
                if remote.get(r):
                    print(f"  clearing partial run #{r} on the remote "
                          f"({remote[r]:,} rows)")
                    if not args.dry_run:
                        _post(f"DELETE FROM episodes WHERE run_id={int(r)}")
            os.makedirs("dist", exist_ok=True)
            path = "dist/episodes-push.sql"
            n, stmts = _dump_episodes(missing, path)
            print(f"  {n:,} rows as {stmts:,} statements "
                  f"(<= {MAX_STMT_BYTES // 1000} KB each)")
            if not args.dry_run:
                _bulk_import(path, log=print)
                os.remove(path)
    return 0 if args.dry_run else cmd_check(args)


def cmd_mirror(args):
    """Materialise D1 back into a local SQLite file, for offline querying."""
    target = args.path
    if os.path.exists(target) and not args.force:
        raise SystemExit(f"{target} exists; pass --force to overwrite")
    if os.path.exists(target):
        os.remove(target)
    out = sqlite3.connect(target)
    out.executescript(DB.SCHEMA)
    out.execute(MATCHUP_DDL)
    for t, cols in list(TABLES) + [("episodes", EPISODE_COLS)]:
        n = _q(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"]
        if not n:
            continue
        got = 0
        marks = ",".join("?" * len(cols))
        while got < n:
            rows = _q(f"SELECT {','.join(cols)} FROM {t} LIMIT {PAGE} OFFSET {got}")
            if not rows:
                break
            out.executemany(
                f"INSERT OR REPLACE INTO {t}({','.join(cols)}) VALUES({marks})",
                [[r[c] for c in cols] for r in rows])
            got += len(rows)
            print(f"  {t:9s} {got:,}/{n:,}", end="\r", flush=True)
        out.commit()
        print(f"  {t:9s} {got:,}/{n:,}")
    out.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    out.close()
    print(f"wrote {target} ({os.path.getsize(target)/1e6:.1f} MB)")
    return 0


def cmd_query(args):
    rows = _q(args.sql)
    if not rows:
        print("(no rows)")
        return 0
    cols = list(rows[0].keys())
    print(" | ".join(cols))
    for r in rows[:args.limit]:
        print(" | ".join(str(r.get(c)) for c in cols))
    if len(rows) > args.limit:
        print(f"... {len(rows) - args.limit} more")
    return 0


def cmd_top(args):
    run = args.run
    if run == "latest":
        rows = _q("SELECT MAX(id) AS id FROM runs")
        run = rows[0]["id"] if rows else None
        if run is None:
            raise SystemExit("no runs in D1 -- push first")
    rows = _q("SELECT agent, bt_elo, winrate, median_money FROM ratings "
              f"WHERE run_id={int(run)} ORDER BY bt_elo DESC LIMIT {int(args.n)}")
    print(f"run #{run}")
    for i, r in enumerate(rows, 1):
        print(f"{i:>3}  {r['bt_elo']:>+8.0f} {r['winrate']*100:>6.1f}% "
              f"{r['median_money']:>10,.0f}  {r['agent']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)
    p = sub.add_parser("push")
    p.add_argument("--episodes", action="store_true",
                   help="also bulk-import episodes for runs D1 does not have")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true",
                   help="rewrite rows D1 already has (costs write quota)")
    p.set_defaults(fn=cmd_push)
    m = sub.add_parser("mirror")
    m.add_argument("path")
    m.add_argument("--force", action="store_true")
    m.set_defaults(fn=cmd_mirror)
    q = sub.add_parser("query")
    q.add_argument("sql")
    q.add_argument("--limit", type=int, default=50)
    q.set_defaults(fn=cmd_query)
    t = sub.add_parser("top")
    t.add_argument("--run", default="latest")
    t.add_argument("-n", type=int, default=25)
    t.set_defaults(fn=cmd_top)
    args = ap.parse_args()
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
