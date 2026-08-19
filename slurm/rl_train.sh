#!/bin/bash
# Training shard for the unified TorchRL trainer. Long runs are chains of
# ~50-minute GPU jobs (short jobs start fast on this cluster; docs: 30-min
# jobs started immediately where 3-hour ones queued 78 minutes) --
# `rl/train.py --resume` restores model + optimizer + seed stream +
# curriculum/pool state, so chaining is free:
#
#   sbatch slurm/rl_train.sh --config rl/configs/league.yaml \
#       --save rl/runs/<run>/latest.pt --resume rl/runs/<run>/latest.pt
#   sbatch --dependency=afterany:<jobid> slurm/rl_train.sh <same args>
#
# (--resume pointing at a not-yet-existing file is a fresh start, so the
# first link of the chain uses the same command line.)
# The first-generation CPU shard lives at rl/legacy/train_ppo.py.
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-train
#SBATCH --time=00:55:00
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-train-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-train-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTORCH_ALLOC_CONF=expandable_segments:True

echo "host=$(hostname) job=${SLURM_JOB_ID}"
python rl/train.py --device cuda --max-minutes 50 "$@"
