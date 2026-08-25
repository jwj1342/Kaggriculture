#!/bin/bash
# A/B: hand-written device PPO (rl/tensor_env/train_t.py) vs the TorchRL
# trainer (rl/train.py), same budget, same seed, same GPU, same job. The
# repo rule is "engine changes get an A/B, not an argument" -- this is the
# acceptance gate for retiring the hand-written update loops.
#
#   sbatch slurm/rl_ab.sh                       # B=1024, 60 iters, seed 0
#   B=512 ITERS=40 sbatch slurm/rl_ab.sh
#
# This is the ONE workload in this repo that runs on a GPU: EpisodeT is a
# batched tensor engine (rl/tensor_env/DESIGN.md §5); the "never request a
# GPU" rule targets the single-threaded deepcopy-bound kaggle-env path.
# Reference curve (L40S, tensorize line): win vs starter 0 -> 0.62 (it 18)
# -> 1.00 (it 30 on), ~18 min for 44M lane-steps at B=1024.
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-ab
# TODO (2026-08-23): 2.5 hours is a bad shape on this cluster -- 30-minute jobs
# started immediately where a 3-hour request queued 78 minutes. This script runs its
# two arms SEQUENTIALLY in one job; the measured alternative is to run them in
# PARALLEL on one card (the retained batch is 14.55 GB peaking ~22-29 GB, so two fit
# in 80 GB, and collection is launch-latency bound so the SMs have room). Left
# unrestructured because it is not the script currently in use -- see the resource
# sweep in logs/profsweep-* before changing it.
#SBATCH --time=02:30:00
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-ab-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-ab-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
# 1, not $SLURM_CPUS_PER_TASK: this script runs rl/train.py on the GPU, where
# collection is one python thread issuing CUDA launches. Measured 2026-08-23:
# TotalCPU ~= Elapsed on every training link, i.e. 0.99 of 8 cores used, and
# fairshare bills the reservation (see slurm/rl_train.sh for the full note).
export OMP_NUM_THREADS=1

export PYTORCH_ALLOC_CONF=expandable_segments:True

B=${B:-1024}
ITERS=${ITERS:-60}
SEED=${SEED:-0}
ARMS=${ARMS:-hand trl}          # ARMS=trl sbatch ... reruns one arm only
OUT=rl/runs/trl-ab
mkdir -p "$OUT"
source "$PROJECT/slurm/gpu_telemetry.sh"
start_gpu_telemetry "trl-ab"
trap finish_gpu_telemetry EXIT

echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader) job=${SLURM_JOB_ID} B=$B iters=$ITERS seed=$SEED arms=$ARMS"

for arm in $ARMS; do
    case $arm in
    hand)
        echo "=== arm A: hand-written PPO (train_t.py) ==="
        python rl/tensor_env/train_t.py --device cuda --B "$B" --iters "$ITERS" \
            --seed "$SEED" --obs-half \
            --log "$OUT/hand.csv" --save "$OUT/hand.pt"
        ;;
    trl)
        echo "=== arm B: TorchRL trainer (rl/train.py) ==="
        # --rb-free: peak 60.97 -> 47.34 GiB at B=1024, same throughput
        # (docs/RUNS.md 2026-08-23; see slurm/rl_train.sh for the full reading).
        python rl/train.py --device cuda --B "$B" --iters "$ITERS" \
            --seed "$SEED" --rb-free \
            --log "$OUT/trl.csv" --save "$OUT/trl.pt"
        ;;
    esac
done

echo "=== curves (iter, win, money) ==="
for arm in hand trl; do
    [ -f "$OUT/$arm.csv" ] || continue
    echo "--- $arm"
    awk -F, 'NR==1 || NR%6==2 {print $1", win="$4", money="$5}' "$OUT/$arm.csv"
done
echo "AB-DONE"
