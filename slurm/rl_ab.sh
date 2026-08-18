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
#SBATCH --time=02:30:00
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-ab-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-ab-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

B=${B:-1024}
ITERS=${ITERS:-60}
SEED=${SEED:-0}
OUT=rl/runs/trl-ab
mkdir -p "$OUT"

echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader) job=${SLURM_JOB_ID} B=$B iters=$ITERS seed=$SEED"

echo "=== arm A: hand-written PPO (train_t.py) ==="
python rl/tensor_env/train_t.py --device cuda --B "$B" --iters "$ITERS" \
    --seed "$SEED" --obs-half \
    --log "$OUT/hand.csv" --save "$OUT/hand.pt"

echo "=== arm B: TorchRL trainer (rl/train.py) ==="
python rl/train.py --device cuda --B "$B" --iters "$ITERS" \
    --seed "$SEED" \
    --log "$OUT/trl.csv" --save "$OUT/trl.pt"

echo "=== curves (iter, win, money) ==="
for arm in hand trl; do
    echo "--- $arm"
    awk -F, 'NR==1 || NR%6==2 {print $1", win="$4", money="$5}' "$OUT/$arm.csv"
done
echo "AB-DONE"
