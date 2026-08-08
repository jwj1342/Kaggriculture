#!/bin/bash
# Large agent parameter sweep. CPU-only -- do not request a GPU.
#
#   sbatch slurm/sweep.sh agents/barnyard.py --set HAND_CAP=8,10,12,14
#
#SBATCH --account=aip-zhouyang
#SBATCH --job-name=kg-sweep
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=48G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/sweep-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/sweep-%j.err

set -euo pipefail

PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"

export OMP_NUM_THREADS=1          # each episode is single-threaded; parallelism is across episodes

echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK} job=${SLURM_JOB_ID}"
python tools/sweep.py "$@" -j "${SLURM_CPUS_PER_TASK}"
