#!/bin/bash
# Statistically meaningful agent evaluation. CPU-only -- do not request a GPU.
#
#   sbatch slurm/eval.sh h2h agents/v2.py agents/barnyard.py --seeds 192
#   sbatch slurm/eval.sh pool agents/v2.py agents/barnyard.py --vs starter --seeds 96
#
#SBATCH --account=aip-zhouyang
#SBATCH --job-name=kg-eval
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/eval-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/eval-%j.err

set -euo pipefail

PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"

export OMP_NUM_THREADS=1     # episodes are single-threaded; parallelism is across episodes

echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK} job=${SLURM_JOB_ID}"
python tools/eval.py "$@" -j "${SLURM_CPUS_PER_TASK}"
