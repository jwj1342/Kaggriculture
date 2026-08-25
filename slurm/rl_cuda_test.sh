#!/bin/bash
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-cuda-test
#SBATCH --time=00:10:00
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=logs/rl-cuda-test-%j.out
#SBATCH --error=logs/rl-cuda-test-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?submit from the repository root}"
source setup_env.sh

if [[ -n "${KG_EXPECT_COMMIT:-}" ]] && ! git diff --quiet "$KG_EXPECT_COMMIT" --; then
    echo "RUN-PREFLIGHT source changed; expected=$KG_EXPECT_COMMIT current=$(git rev-parse HEAD)" >&2
    exit 42
fi

echo "TEST-META job=${SLURM_JOB_ID:-local} host=$(hostname) backend=gpu commit=$(git rev-parse HEAD)"
python rl/tensor_env/bank_t.py --device cuda
echo "RL-CUDA-TESTS-PASS"
