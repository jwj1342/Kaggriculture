#!/usr/bin/env python
"""Register and submit a reproducible option-lite RL chain through Slurm."""

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
from pathlib import Path

import submit_rl


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = {"--device", "--threads", "--save", "--resume", "--log",
              "--max-minutes"}
INPUT_FLAGS = {"--checkpoint", "--opponents", "--eval-opponents"}


def _validate_train_args(values):
    values = list(values)
    if values and values[0] == "--":
        values = values[1:]
    bad = sorted({flag for value in values for flag in CONTROLLED
                  if value == flag or value.startswith(flag + "=")})
    if bad:
        raise ValueError("submitter controls these flags: " + ", ".join(bad))
    return values


def _inputs(argv):
    candidates = []
    seen_flags = set()
    for index, value in enumerate(argv[:-1]):
        if value in INPUT_FLAGS:
            seen_flags.add(value)
            candidates.extend(submit_rl._path_values(argv[index + 1]))
    for value in argv:
        for flag in INPUT_FLAGS:
            if value.startswith(flag + "="):
                seen_flags.add(flag)
                candidates.extend(
                    submit_rl._path_values(value.split("=", 1)[1]))
    if "--checkpoint" not in seen_flags:
        candidates.append("rl/runs/anvil/latest.pt")
    if "--opponents" not in seen_flags:
        candidates.extend((
            "agents/bench3/closer_cleo.py",
            "agents/bench3/ledger_lena.py",
            "agents/bench3/broker_bea.py",
        ))
    if "--eval-opponents" not in seen_flags:
        candidates.extend((
            "agents/bench3/closer_cleo.py",
            "agents/wrapped/w49.py",
        ))
    result = {}
    for value in candidates:
        path = Path(value)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            continue
        resolved = path.resolve()
        key = (str(resolved.relative_to(ROOT))
               if resolved.is_relative_to(ROOT) else str(resolved))
        result[key] = {
            "sha256": submit_rl._sha256(resolved),
            "bytes": resolved.stat().st_size,
        }
    return dict(sorted(result.items()))


def build_jobs(args, train_args, run_dir, manifest_path, start_index=0):
    jobs = []
    dependency = None
    for offset in range(args.links):
        index = start_index + offset
        pilot = offset == 0 and args.pilot_minutes > 0
        minutes = args.pilot_minutes if pilot else args.full_minutes
        command = [
            "sbatch", "--parsable",
            f"--job-name=kg-{args.run[:20]}-{'p' if pilot else f'l{index + 1}'}",
            f"--cpus-per-task={args.cpus}", f"--mem={args.mem_gb}G",
            f"--time=00:{minutes + 5:02d}:00",
            "--export=ALL," + ",".join((
                f"KG_RUN_ID={args.run}", f"KG_MAX_MINUTES={minutes}",
                f"KG_RUN_MANIFEST={manifest_path}")),
        ]
        if dependency is not None:
            command.append(f"--dependency=afterok:{dependency}")
        command.extend([
            str(ROOT / "slurm" / "rl_macro_train.sh"),
            "--save", str(run_dir / "latest.pt"),
            "--log", str(run_dir / "train.jsonl"),
        ])
        if args.resume or index > 0:
            command.extend(["--resume", str(run_dir / "latest.pt")])
        command.extend(train_args)
        jobs.append({"index": index + 1, "pilot": pilot, "command": command})
        dependency = f"JOB_{index + 1}"
    return jobs


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--acceptance", required=True)
    parser.add_argument("--links", type=int, default=1)
    parser.add_argument("--pilot-minutes", type=int, default=8)
    parser.add_argument("--full-minutes", type=int, default=45)
    parser.add_argument("--cpus", type=int, default=8)
    parser.add_argument("--mem-gb", type=int, default=16)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("train_args", nargs=argparse.REMAINDER)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        train_args = _validate_train_args(args.train_args)
    except ValueError as error:
        parser.error(str(error))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run):
        parser.error("--run contains unsupported characters")
    if not 1 <= args.links <= 8:
        parser.error("--links must be between 1 and 8")
    if not 1 <= args.pilot_minutes <= 10 or not 1 <= args.full_minutes <= 50:
        parser.error("pilot/full minutes must be 1..10 and 1..50")
    if not 1 <= args.cpus <= 16 or not 1 <= args.mem_gb <= 128:
        parser.error("cpus and memory must be within cluster limits")

    status = submit_rl._git("status", "--porcelain", "--untracked-files=all")
    changes = submit_rl._relevant_changes(status)
    if changes:
        paths = ", ".join(line[3:] for line in changes[:8])
        parser.error(f"source worktree is dirty ({paths}); commit first")
    commit = submit_rl._git("rev-parse", "HEAD")
    run_dir = ROOT / "rl" / "runs" / args.run
    manifest_path = run_dir / "submission.json"
    if not args.resume and run_dir.exists() and any(run_dir.iterdir()):
        parser.error(f"run directory is not empty: {run_dir}")
    old = None
    if args.resume:
        if not (run_dir / "latest.pt").is_file():
            parser.error("--resume requires an existing latest.pt")
        if manifest_path.is_file():
            with open(manifest_path, encoding="utf-8") as handle:
                old = json.load(handle)

    jobs = build_jobs(
        args, train_args, run_dir, manifest_path,
        start_index=len(old.get("jobs", [])) if old else 0)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {
        "schema": 1,
        "kind": "option_lite_ppo",
        "created_utc": old.get("created_utc", now) if old else now,
        "updated_utc": now,
        "run": args.run,
        "commit": commit,
        "source_dirty": False,
        "hypothesis": args.hypothesis,
        "acceptance": args.acceptance,
        "train_argv": train_args,
        "input_files": _inputs(train_args),
        "resources": {
            "backend": "cpu", "cpus": args.cpus, "mem_gb": args.mem_gb,
            "pilot_minutes": args.pilot_minutes,
            "full_minutes": args.full_minutes,
        },
        "jobs": list(old.get("jobs", [])) if old else [],
    }
    if args.resume and old:
        fixed = ("commit", "hypothesis", "acceptance", "train_argv",
                 "input_files")
        changed = [key for key in fixed if manifest[key] != old.get(key)]
        if changed:
            parser.error("resume changed registered fields: " + ", ".join(changed))

    if not args.dry_run:
        submit_rl._write_json(manifest_path, manifest)
    dependency = None
    for job in jobs:
        command = [part.replace(
            f"afterok:JOB_{job['index'] - 1}", f"afterok:{dependency}")
                   for part in job["command"]]
        print(("DRY " if args.dry_run else "SUBMIT ") + shlex.join(command))
        if args.dry_run:
            job_id = f"JOB_{job['index']}"
        else:
            process = subprocess.run(
                command, cwd=ROOT, check=True, text=True,
                capture_output=True)
            job_id = process.stdout.strip().split(";")[0]
        dependency = job_id
        manifest["jobs"].append({
            "index": job["index"], "pilot": job["pilot"],
            "job_id": job_id, "command": command,
        })
        if not args.dry_run:
            submit_rl._write_json(manifest_path, manifest)
    if args.dry_run:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"manifest: {manifest_path}")
        print("new jobs: " + " -> ".join(
            row["job_id"] for row in manifest["jobs"][-args.links:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
