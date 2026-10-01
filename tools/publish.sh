#!/bin/bash
# Refresh everything a collaborator reads, after a tournament.
#
#     bash tools/publish.sh                 # regenerate + export
#     bash tools/publish.sh --push          # ... and upload the snapshots
#
# The split it enforces:
#
#   git  gets text -- docs/LEADERBOARD.md and docs/RUNS.md. These diff, so
#        `git log -p docs/LEADERBOARD.md` reads as the history of what won.
#
#   dist/ gets binaries -- arena-{meta,full}.sqlite.xz. These do NOT go in git:
#        xz-compressed SQLite cannot delta-compress, so every version is a whole
#        new blob. Measured projection: 27 MB of git history after 50 runs,
#        419 MB after 200, none of it prunable.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f venv/bin/activate ]; then
    echo "error: run tools/bootstrap.sh first" >&2
    exit 1
fi
# shellcheck disable=SC1091
source setup_env.sh >/dev/null

echo "== regenerating the leaderboard =="
python tools/leaderboard.py --run latest

echo
echo "== exporting snapshots =="
python tools/sync.py export
python tools/sync.py export --full

# Anything that reaches the internet must run here, on the login node.
# Compute nodes have NO outbound access -- measured: curl to api.cloudflare.com
# from inside a Slurm allocation returns HTTP 000. That is why a tournament
# writes to local SQLite and publishing is a separate, later step.
if [ -n "${SLURM_JOB_ID:-}" ]; then
    echo
    echo "warning: running inside a Slurm job. Compute nodes have no outbound" >&2
    echo "internet, so --push and D1 upload will fail. Publish from the login node." >&2
fi

if [ "${1:-}" = "--push" ]; then
    echo
    echo "Cloudflare D1 archival replaces automatic sync; see docs/ARCHIVE.md."

    echo
    # Optional historical Kaggle file remote. The postmortem archive lives in
    # GitHub Release; do not recreate or repopulate the retired D1 database.
    if [ -n "${KG_REMOTE:-}" ]; then
        echo
        echo "== pushing the file snapshot =="
        python tools/sync.py push -m "snapshot $(date +%F)"
    fi
fi

cat <<'EOF'

done. Now commit the text:

    git add docs/LEADERBOARD.md docs/RUNS.md
    git commit -m "tournament <label>: <one-line result>"

and add a row to docs/RUNS.md if you have not already. dist/ is git-ignored on
purpose -- hand the .xz files around, or push them to the shared remote.
EOF
