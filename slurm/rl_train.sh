#!/bin/bash
# Training shard for the unified TorchRL trainer. Long runs are chains of
# ~30-minute GPU jobs (short jobs start fast on this cluster; docs: 30-min
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
#SBATCH --time=00:30:00
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-train-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-train-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
# 1, NOT $SLURM_CPUS_PER_TASK. Measured 2026-08-23 (docs/RUNS.md):
#   * sacct on every training link of that night: TotalCPU ~= Elapsed, i.e. 0.99
#     of 6-8 allocated cores actually used. Collection is ONE python thread
#     issuing CUDA launches and the tensors live on the card, so the torch CPU
#     thread pool has nothing to parallelise.
#   * CPU-side thread scaling is NEGATIVE past 4 anyway: at B=512, 1 thread
#     18,957 lane-steps/s, 4 threads 29,833, 8 threads 18,492, 16 threads 8,473.
#     The engine is thousands of tiny ops and pool overhead dominates.
# Over-requesting is not free: fairshare bills the RESERVATION, not the usage,
# and sprio shows AGE contributing 0 with FAIRSHARE at 1,572,636 of 1,574,890 --
# so idle-reserved cores directly lengthen our own queue waits. That night
# reserved ~40 core-hours and used ~7.
export OMP_NUM_THREADS=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

echo "host=$(hostname) job=${SLURM_JOB_ID}"
# 25, so the link exits on its own inside a 30-minute walltime rather
# than being killed mid-iteration.
python rl/train.py --device cuda --max-minutes 25 "$@"
