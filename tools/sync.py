#!/usr/bin/env python
"""Share the episode database without needing cluster access.

The database is 7.6 GB across 3.4M episodes as of 2026-08-14, and `--full` is no
longer something you hand around: it is hundreds of MB and git will not take it.
The part most people actually want -- agents, runs and ratings -- is 0.42 MB and
is committed as `dist/arena-meta.sqlite.xz`. So this is a publishing
problem, not a hosted-database problem: snapshots are exported, compressed, and
handed around; nobody needs an account on the machine that ran the tournament.

    python tools/sync.py export                 # meta snapshot, ~0.3 MB
    python tools/sync.py export --full          # everything; local transfer only, not for git
    python tools/sync.py import dist/arena-meta.sqlite.xz
    python tools/sync.py merge other.sqlite     # fold someone else's runs in
    python tools/sync.py push                   # upload to the shared remote
    python tools/sync.py pull                   # download and install

Two snapshot shapes:

  meta   agents + runs + ratings. Every ranking, every atom effect, no episodes.
         Small enough to commit if you ever wanted to. This is what a
         collaborator needs to read `tools/leaderboard.py` output or check a
         claim in docs/.
  full   the above plus every episode row and its digest. Needed to mine for
         defects or re-derive an aggregate that was never tabulated.

`merge` exists because run ids are per-database AUTOINCREMENT. Folding a
laptop-run tournament into the shared history means remapping them, which is why
you cannot just concatenate two files.
"""

import argparse
import json
import lzma
import os
import shutil
import sqlite3
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB  # noqa: E402

DIST = "dist"
META_TABLES = ["agents", "runs", "ratings"]
# Where `push` / `pull` go. A Kaggle dataset needs no new infrastructure and no
# new credentials -- everyone on the team already has a Kaggle account, because
# that is the competition. Override with KG_REMOTE=<owner>/<slug>.
REMOTE = os.environ.get("KG_REMOTE", "")


def _copy_schema_and(con_src, path_out, tables, where_episodes=None):
    if os.path.exists(path_out):
        os.remove(path_out)
    out = sqlite3.connect(path_out)
    out.executescript(DB.SCHEMA)
    for t in tables:
        cols = [r[1] for r in con_src.execute(f"PRAGMA table_info({t})")]
        collist = ",".join(cols)
        q = f"SELECT {collist} FROM {t}"
        if t == "episodes" and where_episodes:
            q += f" WHERE {where_episodes}"
        rows = con_src.execute(q).fetchall()
        if rows:
            marks = ",".join("?" * len(cols))
            out.executemany(f"INSERT INTO {t}({collist}) VALUES({marks})", rows)
    out.commit()
    out.execute("VACUUM")
    out.close()


def cmd_export(args):
    con = DB.connect()
    os.makedirs(DIST, exist_ok=True)
    tables = META_TABLES + (["episodes"] if args.full else [])
    name = "arena-full" if args.full else "arena-meta"
    raw = os.path.join(DIST, f"{name}.sqlite")

    _copy_schema_and(con, raw, tables)
    size_raw = os.path.getsize(raw)

    packed = raw + ".xz"
    with open(raw, "rb") as fi, lzma.open(packed, "wb", preset=6) as fo:
        shutil.copyfileobj(fi, fo, 1 << 20)
    size_packed = os.path.getsize(packed)
    if not args.keep_raw:
        os.remove(raw)

    n_runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    n_eps = con.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    print(f"exported {name}: {n_runs} runs, "
          f"{n_eps if args.full else 0:,} episodes")
    print(f"  {size_raw/1e6:>7.1f} MB uncompressed")
    print(f"  {size_packed/1e6:>7.1f} MB -> {packed}")
    return 0


def cmd_import(args):
    src = args.path
    target = DB.DB_PATH
    if os.path.exists(target) and not args.force:
        raise SystemExit(f"{target} exists; use --force to replace, or `merge` to combine")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    if src.endswith(".xz"):
        with lzma.open(src, "rb") as fi, open(target, "wb") as fo:
            shutil.copyfileobj(fi, fo, 1 << 20)
    else:
        shutil.copyfile(src, target)
    con = DB.connect(target)
    r = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    e = con.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    print(f"installed {target}: {r} runs, {e:,} episodes")
    return 0


def cmd_merge(args):
    """Fold another database's runs into ours, remapping run ids."""
    src_path = args.path
    tmp = None
    if src_path.endswith(".xz"):
        tmp = os.path.join(DIST, "_merge_tmp.sqlite")
        os.makedirs(DIST, exist_ok=True)
        with lzma.open(src_path, "rb") as fi, open(tmp, "wb") as fo:
            shutil.copyfileobj(fi, fo, 1 << 20)
        src_path = tmp

    dst = DB.connect(getattr(args, "into", None) or DB.DB_PATH)
    src = sqlite3.connect(src_path)
    src.row_factory = sqlite3.Row

    # Agents are keyed by name and are pure metadata -- upsert is safe.
    # `atoms` is stored as a JSON string; register_agents json.dumps() whatever
    # it is given, so pass the parsed dict or it gets double-encoded and every
    # downstream `a[axis]` lookup fails on a string.
    agents = [dict(r) for r in src.execute("SELECT * FROM agents")]
    if agents:
        DB.register_agents(dst, [
            {"name": a["name"], "alias": a["alias"], "path": a["path"],
             "atoms": json.loads(a["atoms"] or "{}"), "sha": a["sha"]}
            for a in agents])

    added_runs = added_eps = 0
    for run in src.execute("SELECT * FROM runs ORDER BY id"):
        label = run["label"]
        if args.tag:
            label = f"{label} [{args.tag}]"
        # Skip a run we already hold, identified by label + episode count.
        dup = dst.execute(
            "SELECT id FROM runs WHERE label=? AND n_episodes IS ? ",
            (label, run["n_episodes"])).fetchone()
        if dup and not args.allow_duplicates:
            print(f"  skip (already present): {label}")
            continue
        cur = dst.execute(
            "INSERT INTO runs(label, kind, seeds, steps, n_agents, n_episodes, "
            "slurm_job, started_at, finished_at, notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (label, run["kind"], run["seeds"], run["steps"], run["n_agents"],
             run["n_episodes"], run["slurm_job"], run["started_at"],
             run["finished_at"], run["notes"]))
        new_id = cur.lastrowid
        added_runs += 1

        eps = src.execute(
            "SELECT seed,left_agent,right_agent,left_money,right_money,left_status,"
            "right_status,shops,prices,left_digest,right_digest,wall "
            "FROM episodes WHERE run_id=?", (run["id"],)).fetchall()
        if eps:
            dst.executemany(
                "INSERT INTO episodes(run_id,seed,left_agent,right_agent,left_money,"
                "right_money,left_status,right_status,shops,prices,left_digest,"
                "right_digest,wall) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [(new_id, *tuple(e)) for e in eps])
            added_eps += len(eps)

        rts = src.execute(
            "SELECT agent,bt_strength,bt_elo,games,wins,winrate,median_money,sd_money "
            "FROM ratings WHERE run_id=?", (run["id"],)).fetchall()
        if rts:
            dst.executemany(
                "INSERT INTO ratings(run_id,agent,bt_strength,bt_elo,games,wins,"
                "winrate,median_money,sd_money) VALUES(?,?,?,?,?,?,?,?,?)",
                [(new_id, *tuple(r)) for r in rts])
        print(f"  merged run '{label}' -> #{new_id} ({len(eps):,} episodes)")

    dst.commit()
    # The database is in WAL mode, so committed rows sit in the -wal file until
    # a checkpoint. Leaving the connection open here once produced a 0-byte
    # database that had reported a successful merge -- close explicitly.
    dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    dst.close()
    src.close()
    if tmp and os.path.exists(tmp):
        os.remove(tmp)
    print(f"merged {added_runs} runs, {added_eps:,} episodes into "
          f"{getattr(args, 'into', None) or DB.DB_PATH}")
    return 0


def _require_remote():
    if not REMOTE:
        raise SystemExit(
            "no remote configured.\n"
            "  Set KG_REMOTE=<kaggle-owner>/<dataset-slug>, e.g.\n"
            "    export KG_REMOTE=yourname/kaggriculture-arena\n"
            "  Create it once with:\n"
            "    python tools/sync.py export --full\n"
            "    kaggle datasets init -p dist && $EDITOR dist/dataset-metadata.json\n"
            "    kaggle datasets create -p dist --dir-mode zip\n"
            "  Keep it PRIVATE: it is our measurements, not competition data.")
    return REMOTE


def cmd_push(args):
    remote = _require_remote()
    cmd_export(argparse.Namespace(full=True, keep_raw=False))
    cmd_export(argparse.Namespace(full=False, keep_raw=False))
    msg = args.message or "arena snapshot"
    print(f"pushing {DIST}/ to kaggle dataset {remote}")
    subprocess.run(["kaggle", "datasets", "version", "-p", DIST,
                    "-m", msg, "--dir-mode", "zip"], check=True)
    return 0


def cmd_pull(args):
    remote = _require_remote()
    os.makedirs(DIST, exist_ok=True)
    subprocess.run(["kaggle", "datasets", "download", remote,
                    "-p", DIST, "--unzip"], check=True)
    want = "arena-full.sqlite.xz" if args.full else "arena-meta.sqlite.xz"
    path = os.path.join(DIST, want)
    if not os.path.exists(path):
        raise SystemExit(f"{want} not in the downloaded dataset; got: {os.listdir(DIST)}")
    return cmd_import(argparse.Namespace(path=path, force=args.force))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export", help="write a compressed snapshot into dist/")
    e.add_argument("--full", action="store_true", help="include every episode row")
    e.add_argument("--keep-raw", action="store_true")
    e.set_defaults(fn=cmd_export)

    i = sub.add_parser("import", help="replace the local database with a snapshot")
    i.add_argument("path")
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_import)

    m = sub.add_parser("merge", help="fold another database's runs into ours")
    m.add_argument("path")
    m.add_argument("--tag", help="label suffix, e.g. a collaborator's name")
    m.add_argument("--allow-duplicates", action="store_true")
    m.add_argument("--into", default=None,
                   help="target database (default: data/arena.sqlite)")
    m.set_defaults(fn=cmd_merge)

    p = sub.add_parser("push", help="upload snapshots to the shared remote")
    p.add_argument("-m", "--message", default=None)
    p.set_defaults(fn=cmd_push)

    q = sub.add_parser("pull", help="download snapshots from the shared remote")
    q.add_argument("--full", action="store_true")
    q.add_argument("--force", action="store_true")
    q.set_defaults(fn=cmd_pull)

    args = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
