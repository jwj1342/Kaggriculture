#!/bin/bash
#SBATCH --account=def-zhouyang
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/rl-macro-train-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?submit from the repository root}"
source setup_env.sh

: "${KG_RUN_MANIFEST:?submit macro training through tools/submit_macro_rl.py}"
python tools/run_preflight.py --manifest "$KG_RUN_MANIFEST" || exit 42

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
echo "RUN-META job=${SLURM_JOB_ID:-local} run=${KG_RUN_ID:-adhoc} host=$(hostname) backend=cpu cpus=$OMP_NUM_THREADS commit=$(git rev-parse HEAD)"

exec python rl/train_macro.py \
    --device cpu \
    --threads "$OMP_NUM_THREADS" \
    --max-minutes "${KG_MAX_MINUTES:-25}" \
    "$@"

