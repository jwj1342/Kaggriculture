#!/usr/bin/env python
"""Verify that a queued job still sees its registered source and input files."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# The commit check protects the COMPUTATION, so it must ignore trees that
# cannot change a result. It used to be an unrestricted `git diff <commit> --`
# over every tracked file, which put it in direct conflict with the project's
# own discipline: CLAUDE.md requires every verdict to be appended to
# docs/RUNS.md, so writing up one arm invalidated every arm still queued.
# Measured 2026-09-02: the mkt-w2/mkt-w4/fut-w4 batch (9 links) was already
# doomed to exit 42 with `docs/RUNS.md | 26 ++++` as the ONLY difference, and
# kg-g1-wheat-240/408 and kg-warmstart-neg-* died the same way earlier.
# Everything executable stays protected -- rl/, agents/, tools/, slurm/,
# requirements/, setup_env.sh and the configs are all still covered by ".".
# `*.md` is here because the first version of this list was incomplete and
# the sentinel caught it within the hour: rl/TODO.md is the project's LIVE
# QUEUE and it lives inside the code tree, so excluding only docs/ still
# voided 12 pending links when the standing table was updated. Four more
# markdown files sit under rl/ and rl/tensor_env/ for the same reason.
# No .md file is read by any computation.
PROSE_EXCLUDED = [".", ":(exclude)*.md", ":(exclude)docs",
                  ":(exclude)site", ":(exclude)notebooks"]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(manifest_path):
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    failures = []
    expected_commit = manifest.get("commit")
    if expected_commit and not manifest.get("source_dirty"):
        proc = subprocess.run(["git", "diff", "--quiet", expected_commit, "--"]
                              + PROSE_EXCLUDED, cwd=ROOT)
        if proc.returncode:
            failures.append(f"tracked files differ from {expected_commit}")
    for name, registered in manifest.get("input_files", {}).items():
        path = Path(name)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            failures.append(f"input missing: {name}")
            continue
        actual = sha256(path)
        if actual != registered["sha256"]:
            failures.append(f"input changed: {name}")
    if failures:
        raise RuntimeError("; ".join(failures))
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args(argv)
    manifest = verify(args.manifest)
    print(f"RUN-PREFLIGHT ok commit={manifest.get('commit')} "
          f"inputs={len(manifest.get('input_files', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
