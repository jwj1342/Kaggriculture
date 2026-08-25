#!/usr/bin/env python
"""Verify that a queued job still sees its registered source and input files."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
        proc = subprocess.run(["git", "diff", "--quiet", expected_commit, "--"],
                              cwd=ROOT)
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
