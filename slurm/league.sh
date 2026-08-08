#!/bin/bash
# Local round-robin league. CPU-only -- do not request a GPU.
#
#   sbatch slurm/league.sh starter agents/barnyard.py --seeds 32
#
#SBATCH --account=aip-zhouyang
#SBATCH --job-name=kg-league
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/league-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/league-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS=1

echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK} job=${SLURM_JOB_ID}"
python tools/league.py "$@" -j "${SLURM_CPUS_PER_TASK}"
