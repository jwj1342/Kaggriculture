#!/usr/bin/env python
"""Append completed endgame runs to the arena, from one Slurm writer only."""
import argparse
import fcntl
import json
import os
from pathlib import Path

import db as DB
from endgame_eval import read_manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifests", nargs="+")
    ap.add_argument("--label", help="Unique run label for one nested manifest")
    args = ap.parse_args()
    if args.label and len(args.manifests) != 1:
        ap.error("--label requires exactly one manifest")
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("Run through a single Slurm job.")
    # All endgame finish jobs share this lock, including the schema setup and
    # final WAL checkpoint. Evaluation shards never open the database.
    lock_path = Path(str(Path(DB.DB_PATH).resolve()) + '.endgame-ingest.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path.open('a')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    con = None
    try:
        con = DB.connect()
        for filename in args.manifests:
            path = Path(filename)
            m = read_manifest(path)
            summary = json.loads((path.parent / "summary.json").read_text())
            expected = len(m["matches"])
            assert summary["matches"] == expected
            label = args.label or path.parent.name
            old = con.execute("SELECT id,n_episodes FROM runs WHERE label=?", (label,)).fetchall()
            if old:
                if len(old) != 1:
                    raise RuntimeError(f"Ambiguous existing run {label}")
                actual = con.execute("SELECT count(*) FROM episodes WHERE run_id=?", (old[0]["id"],)).fetchone()[0]
                if old[0]["n_episodes"] != expected or actual != expected:
                    raise RuntimeError(f"Partial previous ingest for {label}; inspect before retrying")
                print(f"Already complete: {label}, {expected} episodes")
                continue
            records = {}
            for shard in sorted((path.parent / "results").glob("*.jsonl")):
                for line in shard.read_text().splitlines():
                    row = json.loads(line)
                    index = row["index"]
                    if index in records or not 0 <= index < expected:
                        raise RuntimeError(f"Invalid or duplicate index {index}")
                    a, b, seed = m["matches"][index]
                    assert (row["left"], row["right"], row["seed"]) == (m["agents"][a], m["agents"][b], seed)
                    assert row["status"] == ["DONE", "DONE"]
                    records[index] = row
            assert len(records) == expected
            names = {name: f"endgame:{name}:{m['sha256'][src][:12]}" for name, src in m["agents"].items()}
            agents = [{"name": names[name], "alias": name, "path": src,
                       "sha": m["sha256"][src], "atoms": {"source": m.get("original_sources", {}).get(name)}}
                      for name, src in m["agents"].items()]
            DB.register_agents(con, agents)
            run_id = DB.start_run(con, label, "endgame", m["seeds"], 720, len(agents),
                                  slurm_job=os.environ["SLURM_JOB_ID"],
                                  notes=json.dumps({"manifest": str(path.resolve()), "phase": m["phase"],
                                                    "summary": str((path.parent/"summary.json").resolve())}))
            rows = []
            for index, row in sorted(records.items()):
                a, b, _ = m["matches"][index]
                rows.append(dict(row, left=names[a], right=names[b], prices={}))
            DB.add_episodes(con, run_id, rows)
            DB.finish_run(con, run_id, expected)
            print(f"Ingested run {run_id}: {label}, {expected} episodes", flush=True)
    finally:
        try:
            if con is not None:
                DB.close(con)
        finally:
            lock.close()


if __name__ == "__main__":
    main()
