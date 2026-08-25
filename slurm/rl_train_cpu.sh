#!/bin/bash
# CPU-default training link. B=1024 peaks near 77 GiB RSS on current configs;
# 96G leaves headroom without the 35-CPU billing weight of the old 140G jobs.
# Submit through tools/submit_rl.py so the pilot, manifest and dependencies are
# recorded consistently.
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-cpu
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-cpu-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-cpu-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
MAX_MINUTES=${KG_MAX_MINUTES:-25}
MIN_SPS=${KG_MIN_SPS:-5000}

if [ -n "${KG_RUN_MANIFEST:-}" ]; then
    python tools/run_preflight.py --manifest "$KG_RUN_MANIFEST" || exit 42
elif [ -n "${KG_EXPECT_COMMIT:-}" ] && ! git diff --quiet "$KG_EXPECT_COMMIT" --; then
    echo "RUN-PREFLIGHT source changed since submission; expected=$KG_EXPECT_COMMIT current=$(git rev-parse HEAD)" >&2
    exit 42
fi

echo "RUN-META job=${SLURM_JOB_ID:-local} run=${KG_RUN_ID:-adhoc} host=$(hostname) backend=cpu cpus=${SLURM_CPUS_PER_TASK:-16} commit=$(git rev-parse HEAD)"
git status --short --untracked-files=no | sed 's/^/RUN-DIRTY /'

set +e
python rl/train.py --device cpu --threads "$OMP_NUM_THREADS" \
    --max-minutes "$MAX_MINUTES" --min-sps "$MIN_SPS" --rb-free \
    --profile-timing "$@"
rc=$?
set -e
echo "TRAIN-EXIT code=$rc"
exit "$rc"
