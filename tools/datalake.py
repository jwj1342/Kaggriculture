#!/usr/bin/env python
"""Keep the database, the shard landing zone and the shareable snapshots in step.

    python tools/datalake.py status        # what is out of sync, and by how much
    python tools/datalake.py sync          # ingest every shard directory not yet in `runs`
    python tools/datalake.py sync --prune  # ...and delete the shard files afterwards
    python tools/datalake.py export        # refresh the snapshots collaborators pull

WHY THIS EXISTS

Ingest is not automatic and never can be. Array tasks write JSONL and are kept
away from the database on purpose -- two of the three data-integrity incidents in
`docs/RUNS.md` came from concurrent writers, and forty-eight tasks registering a
manifest at once corrupted it once already. So a tournament ends with its results
on disk and nothing in the database until somebody runs `ingest`.

Nobody did, for a month. Measured 2026-08-14: **2,099,325 episodes in 44 shard
directories had never been ingested**, against 1,297,916 in the database. Two
thirds of everything this project has ever computed was sitting in files that no
tool reads. `duel101` alone -- the 477,225-episode round robin that
`docs/ROADMAP.md` §10 is built on -- was one of them.

This tool makes the gap visible in one command, so it stops being invisible.

THE FOUR LAYERS, AND WHICH ONES ARE ALLOWED TO BE DELETED

1. **Source of truth, irreplaceable.** `data/arena.sqlite` (every episode ever
   run) and `data/tracelib/index.json` (the mined plans). **Never delete rows
   from `episodes`; they are history** -- `CLAUDE.md` says so and it is the one
   rule here with no exception. Old runs are not clutter: an engine rebalance
   makes them a record of a different game, which is worth keeping and worth
   *labelling*, not deleting. (Checked 2026-08-14: every run in the database is
   post-1.32.6, so nothing currently needs that label.)

2. **Landing zone, delete after ingest.** `data/shards/<label>/`. A shard file is
   renamed into place only when complete, so a directory either holds a whole
   slice or nothing. Once `runs` has its label the JSONL is redundant with the
   database and costs 1.4 GB. `sync --prune` is the only thing here that deletes,
   and it deletes only directories whose label is already in `runs`.

3. **Shareable snapshots.** `dist/`. This is what a collaborator with a fresh
   clone can actually get, so it must be current and it must be tracked. As of
   2026-08-14 only `tracelib.json.xz` was either: `arena-full.sqlite.xz` held
   85,064 episodes from 2026-08-07 against the live 1.6M, and was not in git.

4. **Derived, regenerate freely.** `agents/*/`, `docs/LEADERBOARD.md`, `site/`.
   All git-ignored, all rebuildable from layers 1-3. Deleting any of it costs
   only the time to regenerate. Never hand-edit these.

WHAT `export` WRITES, AND WHY IT IS NOT THE WHOLE DATABASE

`arena-meta.sqlite.xz` carries `runs`, `agents` and `ratings` -- the shape of
every experiment ever run, a few hundred KB, and enough to answer "has this been
measured before". The 1.6M-row `episodes` table is deliberately left out: it is
gigabytes, it compresses badly because digests are already compressed, and it is
reproducible by re-running the tournament. `tracelib.json.xz` is the exception
that must ship in full, because the mined plans cannot be reproduced -- Kaggle's
daily episode datasets expire.
"""

import argparse
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "arena.sqlite")
SHARDS = os.path.join(ROOT, "data", "shards")
DIST = os.path.join(ROOT, "dist")


def _runs():
    if not os.path.exists(DB):
        return set()
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return {r[0] for r in c.execute("select label from runs")}
    finally:
        c.close()


def _shard_dirs():
    """-> [(path, label, n_files, n_lines)] for every directory that has results."""
    out = []
    for d in sorted(glob.glob(os.path.join(SHARDS, "*"))):
        files = glob.glob(os.path.join(d, "shard-*.jsonl"))
        if not files:
            continue
        meta = os.path.join(d, "meta.json")
        label = os.path.basename(d)
        if os.path.exists(meta):
            try:
                label = json.load(open(meta))["label"]
            except (ValueError, KeyError):
                pass
        n = sum(1 for f in files for _ in open(f))
        out.append((d, label, len(files), n))
    return out


def _du(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def cmd_status(a):
    runs = _runs()
    dirs = _shard_dirs()
    done = [x for x in dirs if x[1] in runs]
    todo = [x for x in dirs if x[1] not in runs]

    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    n_ep = c.execute("select count(*) from episodes").fetchone()[0]
    n_run = c.execute("select count(*) from runs").fetchone()[0]
    span = c.execute("select min(date(started_at)), max(date(started_at)) from runs").fetchone()
    c.close()

    print(f"数据库  {DB}")
    print(f"  {n_ep:,} 局 / {n_run} 个 run / {span[0]} .. {span[1]} / "
          f"{os.path.getsize(DB)/1e9:.2f} GB")

    print(f"\n分片落地区  {SHARDS}")
    print(f"  已入库  {len(done):>3} 个目录 {sum(x[3] for x in done):>10,} 局   "
          f"可以 prune")
    print(f"  未入库  {len(todo):>3} 个目录 {sum(x[3] for x in todo):>10,} 局   "
          f"{'需要 sync' if todo else 'OK'}")
    if todo:
        for d, label, nf, n in sorted(todo, key=lambda x: -x[3])[:10]:
            print(f"      {label:<26}{n:>9,} 局  {nf} 个分片")
        if len(todo) > 10:
            print(f"      ... 另有 {len(todo)-10} 个")
    print(f"  占用    {_du(SHARDS)/1e9:.2f} GB")

    print(f"\n可分享快照  {DIST}")
    tracked = set()
    try:
        tracked = set(subprocess.run(["git", "-C", ROOT, "ls-files", "dist"],
                                     capture_output=True, text=True,
                                     check=True).stdout.split())
    except Exception:
        pass
    for f in sorted(glob.glob(os.path.join(DIST, "*"))):
        rel = os.path.relpath(f, ROOT)
        import datetime
        age = (datetime.datetime.now()
               - datetime.datetime.fromtimestamp(os.path.getmtime(f))).days
        mark = "tracked" if rel in tracked else "**未 tracked，队友拿不到**"
        stale = "  **过期**" if age >= 2 else ""
        print(f"  {os.path.basename(f):<26}{os.path.getsize(f)/1e6:>8.1f} MB  "
              f"{age} 天前  {mark}{stale}")

    if todo:
        print(f"\n-> python tools/datalake.py sync")


def cmd_sync(a):
    runs = _runs()
    todo = [x for x in _shard_dirs() if x[1] not in runs]
    if not todo:
        print("没有待入库的分片。")
    else:
        print(f"{len(todo)} 个目录 / {sum(x[3] for x in todo):,} 局待入库。"
              "严格串行 —— 这个库被并发写者损坏过一次。\n")
        for i, (d, label, _, n) in enumerate(todo, 1):
            print(f"[{i}/{len(todo)}] {label}  {n:,} 局")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "tournament.py"),
                                "ingest", "--shards", d],
                               capture_output=True, text=True, cwd=ROOT)
            if r.returncode != 0:
                print(f"  ** 失败，停止。后续目录未处理。**\n{r.stdout[-800:]}{r.stderr[-800:]}")
                return 1
    if not a.prune:
        return 0

    # Prune only what the database demonstrably holds. A label being present in
    # `runs` is not enough -- a half-ingested run would have the label and a
    # fraction of the rows, and deleting its shards would destroy the remainder
    # for good. So every directory is checked against the episode count actually
    # stored under that run, and a mismatch keeps the files.
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    stored = {r[0]: r[1] for r in c.execute(
        "select r.label, count(e.id) from runs r left join episodes e "
        "on e.run_id = r.id group by r.label")}
    c.close()
    gone, kept = [], []
    for d, label, nf, n in _shard_dirs():
        (gone if stored.get(label, -1) == n else kept).append((d, label, nf, n))
    for d, label, _, n in kept:
        have = stored.get(label)
        why = "未入库" if have is None else f"库里只有 {have:,} 局，分片有 {n:,}"
        print(f"  保留 {label:<26}{why}")
    if not gone:
        print("\nprune: 没有可安全删除的目录。")
        return 0
    freed = sum(_du(d) for d, *_ in gone)
    print(f"\nprune: {len(gone)} 个目录局数与数据库完全一致，删除释放 {freed/1e9:.2f} GB")
    for d, label, _, n in gone:
        shutil.rmtree(d)
    print("已删除。数据在数据库里，分片只是落地区。")
    return 0


def cmd_export(a):
    os.makedirs(DIST, exist_ok=True)
    import lzma
    meta = os.path.join(DIST, "arena-meta.sqlite")
    if os.path.exists(meta):
        os.unlink(meta)
    src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    dst = sqlite3.connect(meta)
    src.backup(dst)
    dst.execute("delete from episodes")
    dst.commit()
    dst.execute("vacuum")
    n = dst.execute("select count(*) from runs").fetchone()[0]
    dst.close()
    src.close()
    with open(meta, "rb") as f, lzma.open(meta + ".xz", "wb", preset=6) as g:
        shutil.copyfileobj(f, g)
    os.unlink(meta)
    print(f"dist/arena-meta.sqlite.xz  {n} 个 run 的元数据  "
          f"{os.path.getsize(meta + '.xz')/1e6:.2f} MB")
    print("episodes 表故意不导出：几个 GB，压不动（摘要本身已压缩），而且可以重跑复现。")
    print("\n剧本库要单独导出（它不可复现，Kaggle 的每日数据集会过期）:")
    print("  python tools/tracelib.py export")
    print("\n导出后记得 git add dist/*.xz —— 不 tracked 的快照队友拿不到。")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="磁盘、数据库、快照三者是否同步")
    p = sub.add_parser("sync", help="把所有未入库的分片入库")
    p.add_argument("--prune", action="store_true",
                   help="入库后删除已入库目录的分片文件。只删 runs 里已有 label 的。")
    sub.add_parser("export", help="刷新可分享快照")
    a = ap.parse_args()
    return {"status": cmd_status, "sync": cmd_sync, "export": cmd_export}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
