#!/usr/bin/env python
"""Summarise Slurm accounting, trainer phase timing, and GPU telemetry.

Examples:
    python tools/slurm_audit.py --job 20360593
    python tools/slurm_audit.py --timing rl/runs/foo/timing.csv
    python tools/slurm_audit.py --gpu logs/profiles/foo/20360593-gpu.csv
"""

import argparse
import csv
import json
import os
import statistics
import subprocess
from datetime import datetime


def duration_seconds(value):
    """Parse Slurm's [days-]HH:MM:SS[.sss] duration format."""
    if not value or value in {"Unknown", "None", "N/A"}:
        return None
    days = 0
    if "-" in value:
        day, value = value.split("-", 1)
        days = int(day)
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes, seconds = 0, parts[0], parts[1]
    else:
        return float(value)
    return days * 86400 + int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _timestamp(value):
    if not value or value in {"Unknown", "None", "N/A"}:
        return None
    return datetime.fromisoformat(value)


def memory_mib(value):
    if not value:
        return None
    units = {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}
    suffix = value[-1].upper()
    if suffix in units:
        return float(value[:-1]) * units[suffix]
    return float(value) / 1024 / 1024


def audit_job(job_id):
    fields = ["JobIDRaw", "JobName", "State", "ExitCode", "Submit", "Eligible",
              "Start", "End", "Elapsed", "Timelimit", "AllocCPUS", "ReqMem",
              "TotalCPU", "MaxRSS", "AllocTRES"]
    proc = subprocess.run(
        ["sacct", "-j", str(job_id), "-n", "-P", "--format=" + ",".join(fields)],
        check=True, text=True, capture_output=True)
    rows = [dict(zip(fields, line.split("|"))) for line in proc.stdout.splitlines()
            if line.strip()]
    row = next((r for r in rows if r["JobIDRaw"] == str(job_id)), None)
    if row is None:
        raise ValueError(f"job {job_id} not found in sacct")
    elapsed = duration_seconds(row["Elapsed"])
    total_cpu = duration_seconds(row["TotalCPU"])
    cpus = int(row["AllocCPUS"] or 0)
    submit = _timestamp(row["Submit"])
    eligible, start = _timestamp(row["Eligible"]), _timestamp(row["Start"])
    row["dependency_s"] = ((eligible - submit).total_seconds()
                           if submit is not None and eligible is not None else None)
    row["queue_s"] = ((start - eligible).total_seconds()
                      if eligible is not None and start is not None else None)
    row["turnaround_wait_s"] = ((start - submit).total_seconds()
                                if submit is not None and start is not None else None)
    row["elapsed_s"] = elapsed
    row["total_cpu_s"] = total_cpu
    row["cpu_efficiency"] = (total_cpu / (elapsed * cpus)
                             if elapsed and total_cpu is not None and cpus else None)
    batch = next((r for r in rows if r["JobIDRaw"] == f"{job_id}.batch"), None)
    max_rss = row["MaxRSS"] or (batch["MaxRSS"] if batch else "")
    row["max_rss_mib"] = memory_mib(max_rss)
    row["req_mem_mib"] = memory_mib(row["ReqMem"])
    row["memory_efficiency"] = (
        row["max_rss_mib"] / row["req_mem_mib"]
        if row["max_rss_mib"] is not None and row["req_mem_mib"] else None)
    return row


def _number(value):
    value = value.strip().replace("%", "").replace("MiB", "").replace("W", "")
    try:
        return float(value)
    except ValueError:
        return None


def audit_gpu(path):
    utils, memory = [], []
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    for row in rows:
        if not row:
            continue
        # Current schema: timestamp,index,name,gpu_util_pct,memory_util_pct,
        # memory_used_mib,memory_total_mib,power_w. The old profiler had four
        # columns: timestamp,gpu util,memory util,memory used.
        if row[0].strip().lower() == "timestamp":
            continue
        util_idx = 3 if len(row) >= 8 else 1
        memory_idx = 5 if len(row) >= 8 else 3
        util = _number(row[util_idx])
        mem = _number(row[memory_idx])
        if util is not None:
            utils.append(util)
        if mem is not None:
            memory.append(mem)
    if not utils:
        raise ValueError(f"no GPU samples found in {path}")
    return {
        "path": path,
        "samples": len(utils),
        "util_mean_pct": statistics.fmean(utils),
        "util_median_pct": statistics.median(utils),
        "idle_samples_pct": 100.0 * sum(x < 10 for x in utils) / len(utils),
        "busy_samples_pct": 100.0 * sum(x >= 90 for x in utils) / len(utils),
        "memory_peak_mib": max(memory) if memory else None,
        "memory_mean_mib": statistics.fmean(memory) if memory else None,
    }


def audit_timing(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"no timing rows found in {path}")
    phases = ["collect_s", "gae_s", "prepare_s", "update_s", "metrics_s",
              "probe_s", "checkpoint_s"]
    means = {phase: statistics.fmean(float(r.get(phase) or 0.0) for r in rows)
             for phase in phases}
    total = statistics.fmean(float(r["total_s"]) for r in rows)
    return {
        "path": path,
        "iterations": len(rows),
        "mean_total_s": total,
        "mean_wall_sps": statistics.fmean(float(r["wall_sps"]) for r in rows),
        "phases": {phase: {"mean_s": value,
                           "pct": 100.0 * value / total if total else 0.0}
                   for phase, value in means.items()},
    }


def _human_seconds(value):
    if value is None:
        return "n/a"
    if value < 60:
        return f"{value:.1f}s"
    return f"{value / 60:.1f}m"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--job", action="append", default=[], help="Slurm job ID; repeatable")
    ap.add_argument("--timing", action="append", default=[], help="trainer timing.csv")
    ap.add_argument("--gpu", action="append", default=[], help="nvidia-smi telemetry CSV")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not (args.job or args.timing or args.gpu):
        ap.error("at least one of --job, --timing, or --gpu is required")

    result = {"jobs": [], "timings": [], "gpus": []}
    for value in args.job:
        for job_id in value.split(","):
            result["jobs"].append(audit_job(job_id.strip()))
    result["timings"] = [audit_timing(path) for path in args.timing]
    result["gpus"] = [audit_gpu(path) for path in args.gpu]
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    for row in result["jobs"]:
        eff = row["cpu_efficiency"]
        rss = row["max_rss_mib"]
        parts = [f"JOB {row['JobIDRaw']}", row["JobName"], row["State"],
                 f"dep={_human_seconds(row['dependency_s'])}",
                 f"queue={_human_seconds(row['queue_s'])}",
                 f"run={_human_seconds(row['elapsed_s'])}",
                 f"cpu_eff={100 * eff:.1f}%" if eff is not None else "cpu_eff=n/a"]
        if rss is not None:
            parts.append(f"max_rss={rss / 1024:.1f}GiB")
        if row["memory_efficiency"] is not None:
            parts.append(f"mem_eff={100 * row['memory_efficiency']:.1f}%")
        print(" ".join(parts))
    for report in result["timings"]:
        print(f"TIMING {report['path']} iterations={report['iterations']} "
              f"mean={report['mean_total_s']:.2f}s wall_sps={report['mean_wall_sps']:,.0f}")
        for phase, values in report["phases"].items():
            print(f"  {phase[:-2]:<10} {values['mean_s']:7.3f}s {values['pct']:5.1f}%")
    for report in result["gpus"]:
        print(f"GPU {report['path']} samples={report['samples']} "
              f"util mean/median={report['util_mean_pct']:.1f}/{report['util_median_pct']:.1f}% "
              f"idle(<10%)={report['idle_samples_pct']:.1f}% "
              f"busy(>=90%)={report['busy_samples_pct']:.1f}% "
              f"peak_mem={report['memory_peak_mib']:.0f}MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
