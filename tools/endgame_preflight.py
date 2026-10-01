#!/usr/bin/env python
"""Verify and run an exact submission archive on a Slurm compute node."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("snapshot")
    ap.add_argument("--opponent", required=True)
    ap.add_argument("--seed", type=int, default=1140001)
    args = ap.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("Run through Slurm.")
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable
    snapshot = Path(args.snapshot).resolve()
    archive = snapshot / "submission.tar.gz"
    with tempfile.TemporaryDirectory(prefix="kg-endgame-preflight-") as d:
        dest = Path(d)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not member.isfile() or member.name not in ("main.py", "LICENSE.txt", "NOTICE.txt", "kaggle-environments-LICENSE.txt"):
                    raise RuntimeError(f"Unexpected archive entry: {member.name}")
                (dest / member.name).write_bytes(tar.extractfile(member).read())
        policy = dest / "main.py"
        assert policy.read_bytes() == (snapshot / "main.py").read_bytes()
        fn = get_last_callable(policy.read_text(), path=str(policy))
        assert fn is fn.__globals__.get("agent"), "Framework selected a helper instead of the exported agent"
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": args.seed})
        env.run([str(policy), str(Path(args.opponent).resolve())])
        final = env.steps[-1]
        assert [str(x.status) for x in final] == ["DONE", "DONE"]
        assert sum(bool((step[0].get("action") or {}).get("market")) for step in env.steps) > 0
        result = {"job": os.environ["SLURM_JOB_ID"], "archive": str(archive),
                  "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                  "main_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
                  "callable_is_exported_agent": True, "callable_name": fn.__name__,
                  "schema_validation": "enabled", "seed": args.seed,
                  "opponent": args.opponent, "status": [str(x.status) for x in final],
                  "money": [float(x.reward or 0) for x in final], "steps": len(env.steps)}
        (snapshot / "PREFLIGHT.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
