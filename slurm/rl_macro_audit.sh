#!/bin/bash
#SBATCH --account=def-zhouyang
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=logs/rl-macro-audit-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?submit from the repository root}"
source setup_env.sh

if [[ -n "${KG_EXPECTED_COMMIT:-}" ]]; then
    python tools/run_preflight.py --commit "$KG_EXPECTED_COMMIT"
fi

echo "RUN-META commit=$(git rev-parse HEAD) host=$(hostname) cpus=${SLURM_CPUS_PER_TASK:-1}"
exec python rl/macro_audit.py "$@"
