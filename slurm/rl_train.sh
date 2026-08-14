#!/bin/bash
# PPO training shard for the rl/ line. CPU-only -- never request a GPU.
# Short jobs start fast on this cluster (docs: 30-min jobs started immediately
# where 3-hour ones queued 78 minutes), so training runs as a chain of ~50 min
# jobs; the checkpoint in rl/runs/<run>/ makes resumption free.
#
#   sbatch slurm/rl_train.sh --run m1 --n-envs 28
#
#SBATCH --account=aip-zhouyang
#SBATCH --job-name=kg-rl-train
#SBATCH --time=00:55:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=48G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-train-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-train-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS=1
export KG_FAST_ENV=1

echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK} job=${SLURM_JOB_ID}"
python rl/train_ppo.py --max-minutes 50 "$@"
