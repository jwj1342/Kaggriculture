#!/bin/bash
# Strategy-library tournament. CPU-only -- do not request a GPU.
#
#   sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8
#   sbatch slurm/tournament.sh roundrobin --from-run latest --top 24 --seeds 24
#
#SBATCH --account=aip-zhouyang
#SBATCH --job-name=kg-tourney
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=48G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/tourney-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/tourney-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS=1

echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK} job=${SLURM_JOB_ID}"
python tools/tournament.py "$@" -j "${SLURM_CPUS_PER_TASK}"
