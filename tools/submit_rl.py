#!/usr/bin/env python
"""Submit a disciplined, resumable RL chain through Slurm.

The wrapper owns device, checkpoint, timing, dependency, and walltime flags.
Experiment-specific rl/train.py arguments follow ``--``.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_preflight   # noqa: E402  -- one definition of "the code changed"

ROOT = Path(__file__).resolve().parents[1]


def code_unchanged_since(old_commit, root=None):
    """Has anything EXECUTABLE changed since `old_commit`?

    A pre-registration binds the code, not the hash. Comparing bare hashes is
    the submit-time half of the defect e6ae614/1fd6b33 fixed at run time:
    CLAUDE.md requires a verdict appended to docs/RUNS.md per experiment, so
    writing up any arm advances HEAD and would make every other run
    permanently un-resumable. Asks exactly the question run_preflight asks, so
    there is one definition of "the code changed" rather than two.
    """
    return subprocess.run(
        ["git", "diff", "--quiet", old_commit, "--"]
        + run_preflight.PROSE_EXCLUDED,
        cwd=str(root or ROOT)).returncode == 0
CONTROLLED = {
    "--device", "--save", "--resume", "--log", "--timing-log",
    "--profile-timing", "--max-minutes", "--rb-free", "--threads",
    "--min-sps",
}
SOURCE_PREFIXES = ("rl/", "tools/", "slurm/", "tests/", "requirements/")
FILE_FLAGS = {"--config", "--init-from", "--residual-base", "--bank",
              "--opponent", "--opponents"}


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                          capture_output=True).stdout.rstrip("\n")


def _validate_train_args(values):
    values = list(values)
    if values and values[0] == "--":
        values = values[1:]
    bad = sorted({flag for value in values for flag in CONTROLLED
                  if value == flag or value.startswith(flag + "=")})
    if bad:
        raise ValueError("submitter controls these flags: " + ", ".join(bad))
    for index, value in enumerate(values):
        if value == "--config":
            if index + 1 >= len(values):
                raise ValueError("--config requires a path")
            path = ROOT / values[index + 1]
            if not path.is_file():
                raise ValueError(f"config does not exist: {values[index + 1]}")
        elif value.startswith("--config="):
            path_value = value.split("=", 1)[1]
            path = ROOT / path_value
            if not path.is_file():
                raise ValueError(f"config does not exist: {path_value}")
    return values


def _relevant_changes(status):
    """Tracked changes plus untracked code/config files; ignore loose artifacts."""
    result = []
    for line in status.splitlines():
        path = line[3:]
        if not line.startswith("?? ") or path.startswith(SOURCE_PREFIXES):
            result.append(line)
    return result


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path_values(value):
    for item in str(value).split(","):
        item = item.strip()
        if item.startswith("tape:"):
            item = item[5:]
        if item:
            yield item


def _input_manifest(train_args):
    """Hash explicit inputs and file-valued settings referenced by YAML."""
    candidates = []
    for index, value in enumerate(train_args[:-1]):
        if value in FILE_FLAGS:
            candidates.extend(_path_values(train_args[index + 1]))
    for value in train_args:
        for flag in FILE_FLAGS:
            if value.startswith(flag + "="):
                candidates.extend(_path_values(value.split("=", 1)[1]))
    configs = [train_args[i + 1] for i, value in enumerate(train_args[:-1])
               if value == "--config"]
    configs += [value.split("=", 1)[1] for value in train_args
                if value.startswith("--config=")]
    for config in configs:
        path = Path(config)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            continue
        import yaml
        with open(path) as fh:
            values = yaml.safe_load(fh) or {}
        for key in ("init_from", "residual_base", "bank", "opponent", "opponents"):
            if values.get(key):
                candidates.extend(_path_values(values[key]))

    result = {}
    for value in candidates:
        path = Path(value)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            continue
        resolved = path.resolve()
        key = (str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT)
               else str(resolved))
        result[key] = {"sha256": _sha256(resolved), "bytes": resolved.stat().st_size}
    return dict(sorted(result.items()))


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(value, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def build_jobs(args, train_args, run_dir, expected_commit="", start_index=0):
    script_name = "rl_train.sh" if args.backend == "gpu" else "rl_train_cpu.sh"
    script = ROOT / "slurm" / script_name
    latest = run_dir / "latest.pt"
    managed = [
        "--save", str(latest), "--log", str(run_dir / "train.csv"),
        "--timing-log", str(run_dir / "timing.csv"),
    ]
    jobs = []
    dependency = None
    for offset in range(args.links):
        index = start_index + offset
        pilot = offset == 0 and args.pilot_minutes > 0
        train_minutes = args.pilot_minutes if pilot else args.full_minutes
        # Headroom between the trainer's own budget (KG_MAX_MINUTES) and the
        # walltime. The trainer only checks the clock BETWEEN iterations, so
        # the overshoot is one whole iteration plus the checkpoint save --
        # and the tail is what matters, not the median. 2026-09-04:
        # predator-n07's link 4 hit TIMEOUT at 35:06 against a 35-minute wall
        # because one iteration took 681 s (its median was 99 s and the
        # lambda=0 control's worst was 191 s). A TIMEOUT exits non-zero, so
        # `afterok` never fires and the REST OF THE CHAIN sits in the queue
        # as DependencyNeverSatisfied forever -- silently, with an intact
        # checkpoint. Size this from the arm's p99 iteration, not its median.
        allocation_minutes = train_minutes + args.headroom_minutes
        name = f"kg-{args.run[:20]}-{'p' if pilot else f'l{index + 1}'}"
        exports = ["ALL", f"KG_RUN_ID={args.run}",
                   f"KG_MAX_MINUTES={train_minutes}", f"KG_MIN_SPS={args.min_sps}",
                   f"KG_RUN_MANIFEST={run_dir / 'submission.json'}"]
        if expected_commit:
            exports.append(f"KG_EXPECT_COMMIT={expected_commit}")
        command = [
            "sbatch", "--parsable", f"--job-name={name}",
            f"--time=00:{allocation_minutes:02d}:00",
            "--export=" + ",".join(exports),
        ]
        if dependency is not None:
            command += [f"--dependency=afterok:{dependency}"]
        command += [str(script), *managed]
        if args.resume or index > 0:
            command += ["--resume", str(latest)]
        command += train_args
        jobs.append({"index": index + 1, "pilot": pilot, "command": command})
        dependency = f"JOB_{index + 1}"
    return jobs


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True, help="name below rl/runs/")
    ap.add_argument("--backend", choices=("cpu", "gpu"), default="cpu")
    ap.add_argument("--links", type=int, default=1, help="total jobs, including pilot")
    ap.add_argument("--pilot-minutes", type=int, default=5,
                    help="short first link; 0 disables the pilot")
    ap.add_argument("--full-minutes", type=int, default=25)
    ap.add_argument("--headroom-minutes", type=int, default=5,
                    help="walltime minus the trainer budget. The trainer's "
                         "clock check is BETWEEN iterations, so this must "
                         "cover one p99 iteration plus the save; a TIMEOUT "
                         "breaks the afterok chain and every later link "
                         "sits as DependencyNeverSatisfied with no error")
    ap.add_argument("--min-sps", type=int, default=0,
                    help="pilot throughput floor; default: CPU 5000, GPU 8000")
    ap.add_argument("--hypothesis", required=True)
    ap.add_argument("--acceptance", required=True,
                    help="pre-registered metric and pass/fail threshold")
    ap.add_argument("--gpu-justification", default="",
                    help="required for --backend gpu")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("train_args", nargs=argparse.REMAINDER,
                    help="rl/train.py arguments after --")
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        train_args = _validate_train_args(args.train_args)
    except ValueError as exc:
        ap.error(str(exc))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run):
        ap.error("--run must contain only letters, digits, '.', '_' and '-'")
    if not 1 <= args.links <= 8:
        ap.error("--links must be between 1 and 8; submit a reviewed continuation later")
    if not 1 <= args.full_minutes <= 50 or not 0 <= args.pilot_minutes <= 10:
        ap.error("full minutes must be 1..50 and pilot minutes 0..10")
    if not 2 <= args.headroom_minutes <= 30:
        ap.error("headroom minutes must be 2..30")
    if args.backend == "gpu" and not args.gpu_justification.strip():
        ap.error("--backend gpu requires --gpu-justification")
    if args.min_sps < 0:
        ap.error("--min-sps must be non-negative")
    if args.min_sps == 0:
        args.min_sps = 8000 if args.backend == "gpu" else 5000

    status = _git("status", "--porcelain", "--untracked-files=all")
    changes = _relevant_changes(status)
    if changes and not args.allow_dirty:
        paths = ", ".join(line[3:] for line in changes[:8])
        ap.error(f"source worktree is dirty ({paths}); commit first or use --allow-dirty")
    commit = _git("rev-parse", "HEAD")
    input_files = _input_manifest(train_args)
    run_dir = ROOT / "rl" / "runs" / args.run
    latest = run_dir / "latest.pt"
    manifest_path = run_dir / "submission.json"
    if args.resume and not latest.is_file():
        ap.error(f"--resume requested but checkpoint is missing: {latest}")
    if not args.resume and run_dir.exists() and any(run_dir.iterdir()):
        ap.error(f"run directory is not empty: {run_dir}; choose a new name or --resume")

    old_manifest = None
    if args.resume and manifest_path.is_file():
        with open(manifest_path) as fh:
            old_manifest = json.load(fh)
        expected = {
            "backend": args.backend,
            "hypothesis": args.hypothesis,
            "acceptance": args.acceptance,
            "train_argv": train_args,
            "commit": commit,
            "input_files": input_files,
        }
        changed = [key for key, value in expected.items()
                   if old_manifest.get(key) != value]
        # A bare hash comparison on `commit` is the wrong test, and it is the
        # submit-time half of the defect e6ae614/1fd6b33 fixed at run time:
        # CLAUDE.md requires a verdict appended to docs/RUNS.md per experiment,
        # so writing up ANY arm advances HEAD and makes every other run
        # permanently un-resumable -- which on 2026-09-02 cost two full waves
        # of arms that had to be discarded and relaunched from scratch.
        # What a pre-registration actually binds is the CODE, so ask the same
        # question run_preflight asks: does the executable tree still match?
        if "commit" in changed and old_manifest.get("commit"):
            if code_unchanged_since(old_manifest["commit"]):
                changed.remove("commit")
                print(f"resume: HEAD moved to {commit[:12]} but the executable "
                      f"tree is unchanged since {old_manifest['commit'][:12]} "
                      f"(only docs/site/notebooks differ) -- continuing")
        if changed:
            ap.error("resume changed registered fields (" + ", ".join(changed)
                     + "); use a new run name")
    prior_jobs = list(old_manifest.get("jobs", [])) if old_manifest else []
    expected_commit = "" if args.allow_dirty else commit
    jobs = build_jobs(args, train_args, run_dir, expected_commit=expected_commit,
                      start_index=len(prior_jobs))
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {
        "schema": 1,
        "created_utc": old_manifest.get("created_utc", now) if old_manifest else now,
        "updated_utc": now,
        "run": args.run,
        "backend": args.backend,
        "commit": commit,
        "source_dirty": bool(changes),
        "dirty_paths": [line[3:] for line in changes],
        "hypothesis": args.hypothesis,
        "acceptance": args.acceptance,
        "gpu_justification": args.gpu_justification,
        "links": args.links,
        "pilot_minutes": args.pilot_minutes,
        "full_minutes": args.full_minutes,
        "headroom_minutes": args.headroom_minutes,
        "min_sps": args.min_sps,
        "train_argv": train_args,
        "input_files": input_files,
        "jobs": prior_jobs,
    }
    if not args.dry_run:
        _write_json(manifest_path, manifest)
    dependency = None
    for job in jobs:
        command = list(job["command"])
        if dependency is not None:
            command = [part.replace(f"afterok:JOB_{job['index'] - 1}",
                                    f"afterok:{dependency}") for part in command]
        print("DRY " if args.dry_run else "SUBMIT ", shlex.join(command))
        if args.dry_run:
            job_id = f"JOB_{job['index']}"
        else:
            proc = subprocess.run(command, cwd=ROOT, check=True, text=True,
                                  capture_output=True)
            job_id = proc.stdout.strip().split(";")[0]
        dependency = job_id
        manifest["jobs"].append({
            "index": job["index"], "pilot": job["pilot"], "job_id": job_id,
            "command": command,
        })
        if not args.dry_run:
            _write_json(manifest_path, manifest)
    if args.dry_run:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"manifest: {manifest_path}")
        print("new jobs: " + " -> ".join(j["job_id"] for j in manifest["jobs"][-args.links:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
