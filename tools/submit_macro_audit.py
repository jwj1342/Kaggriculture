#!/usr/bin/env python
"""Register and submit a reproducible macro audit through Slurm."""

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
from pathlib import Path

import submit_rl


ROOT = Path(__file__).resolve().parents[1]
INPUT_FLAGS = {"--checkpoint", "--opponent"}


def _audit_inputs(argv):
    candidates = []
    for index, value in enumerate(argv[:-1]):
        if value in INPUT_FLAGS:
            candidates.extend(submit_rl._path_values(argv[index + 1]))
    for value in argv:
        for flag in INPUT_FLAGS:
            if value.startswith(flag + "="):
                candidates.extend(submit_rl._path_values(value.split("=", 1)[1]))

    result = {}
    for value in candidates:
        path = Path(value)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            continue
        resolved = path.resolve()
        key = (str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT)
               else str(resolved))
        result[key] = {
            "sha256": submit_rl._sha256(resolved),
            "bytes": resolved.stat().st_size,
        }
    return dict(sorted(result.items()))


def _validate_audit_args(values):
    values = list(values)
    if values and values[0] == "--":
        values = values[1:]
    if not values or values[0] not in {"baseline", "counterfactual"}:
        raise ValueError("audit arguments must start with baseline or counterfactual")
    if any(value == "--output" or value.startswith("--output=") for value in values):
        raise ValueError("submitter controls --output")
    return values


def build_command(args, audit_args, run_dir, manifest_path):
    return [
        "sbatch", "--parsable", f"--job-name=kg-{args.run[:20]}",
        f"--cpus-per-task={args.cpus}", f"--mem={args.mem_gb}G",
        f"--time=00:{args.minutes:02d}:00",
        "--export=ALL," + f"KG_RUN_MANIFEST={manifest_path}",
        str(ROOT / "slurm" / "rl_macro_audit.sh"),
        *audit_args, "--output", str(run_dir / "result.json"),
    ]


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="name below rl/runs/")
    ap.add_argument("--hypothesis", required=True)
    ap.add_argument("--acceptance", required=True)
    ap.add_argument("--minutes", type=int, default=30)
    ap.add_argument("--cpus", type=int, default=8)
    ap.add_argument("--mem-gb", type=int, default=24)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("audit_args", nargs=argparse.REMAINDER)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        audit_args = _validate_audit_args(args.audit_args)
    except ValueError as exc:
        ap.error(str(exc))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run):
        ap.error("--run must contain only letters, digits, '.', '_' and '-'")
    if not 1 <= args.minutes <= 60:
        ap.error("--minutes must be between 1 and 60")
    if not 1 <= args.cpus <= 16 or not 1 <= args.mem_gb <= 128:
        ap.error("--cpus must be 1..16 and --mem-gb must be 1..128")

    status = submit_rl._git("status", "--porcelain", "--untracked-files=all")
    changes = submit_rl._relevant_changes(status)
    if changes:
        paths = ", ".join(line[3:] for line in changes[:8])
        ap.error(f"source worktree is dirty ({paths}); commit first")
    commit = submit_rl._git("rev-parse", "HEAD")
    run_dir = ROOT / "rl" / "runs" / args.run
    if run_dir.exists() and any(run_dir.iterdir()):
        ap.error(f"run directory is not empty: {run_dir}; choose a new name")
    manifest_path = run_dir / "submission.json"
    command = build_command(args, audit_args, run_dir, manifest_path)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {
        "schema": 1,
        "kind": "macro_audit",
        "created_utc": now,
        "run": args.run,
        "commit": commit,
        "source_dirty": False,
        "hypothesis": args.hypothesis,
        "acceptance": args.acceptance,
        "audit_argv": audit_args,
        "input_files": _audit_inputs(audit_args),
        "resources": {
            "backend": "cpu", "cpus": args.cpus,
            "mem_gb": args.mem_gb, "minutes": args.minutes,
        },
        "jobs": [],
    }
    print(("DRY " if args.dry_run else "SUBMIT ") + shlex.join(command))
    if args.dry_run:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    submit_rl._write_json(manifest_path, manifest)
    proc = subprocess.run(command, cwd=ROOT, check=True, text=True,
                          capture_output=True)
    job_id = proc.stdout.strip().split(";")[0]
    manifest["jobs"].append({"job_id": job_id, "command": command})
    submit_rl._write_json(manifest_path, manifest)
    print(f"manifest: {manifest_path}")
    print(f"job: {job_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
