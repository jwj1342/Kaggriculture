#!/bin/bash
#SBATCH --account=def-zhouyang
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=logs/rl-macro-audit-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?submit from the repository root}"
source setup_env.sh

: "${KG_RUN_MANIFEST:?submit macro audits through tools/submit_macro_audit.py}"
python tools/run_preflight.py --manifest "$KG_RUN_MANIFEST" || exit 42

echo "RUN-META commit=$(git rev-parse HEAD) host=$(hostname) cpus=${SLURM_CPUS_PER_TASK:-1}"
exec python rl/macro_audit.py "$@"
