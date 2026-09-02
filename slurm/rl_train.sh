#!/bin/bash
# Training shard for the unified TorchRL trainer. Long runs are chains of
# ~30-minute GPU jobs (short jobs start fast on this cluster; docs: 30-min
# jobs started immediately where 3-hour ones queued 78 minutes) --
# `rl/train.py --resume` restores model + optimizer + seed stream +
# curriculum/pool state, so chaining is free:
#
#   python tools/submit_rl.py --run <run> --backend gpu --links 2 \
#       --hypothesis "..." --acceptance "..." --gpu-justification "..." -- \
#       --config rl/configs/league.yaml
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

MAX_MINUTES=${KG_MAX_MINUTES:-25}
MIN_SPS=${KG_MIN_SPS:-8000}
RUN_ID=${KG_RUN_ID:-adhoc}
source "$PROJECT/slurm/gpu_telemetry.sh"
start_gpu_telemetry "$RUN_ID"
trap finish_gpu_telemetry EXIT

if [ -n "${KG_RUN_MANIFEST:-}" ]; then
    python tools/run_preflight.py --manifest "$KG_RUN_MANIFEST" || exit 42
elif [ -n "${KG_EXPECT_COMMIT:-}" ] && ! git diff --quiet "$KG_EXPECT_COMMIT" -- . ":(exclude)docs" ":(exclude)site" ":(exclude)notebooks"; then
    echo "RUN-PREFLIGHT source changed since submission; expected=$KG_EXPECT_COMMIT current=$(git rev-parse HEAD)" >&2
    exit 42
fi

echo "RUN-META job=${SLURM_JOB_ID:-local} run=$RUN_ID host=$(hostname) backend=gpu cpus=${SLURM_CPUS_PER_TASK:-2} commit=$(git rev-parse HEAD)"
git status --short --untracked-files=no | sed 's/^/RUN-DIRTY /'
# --rb-free: measured 2026-08-23 with --mem-report at B=1024 (docs/RUNS.md).
# The PPO update round-tripped the batch through a ReplayBuffer whose
# LazyTensorStorage is a third full copy of the observation, refilled once per
# epoch. Peak fell 60.97 -> 47.34 GiB and live-across-the-collect-boundary
# 43.37 -> 29.74, at identical throughput (10,593 vs 10,592 sps) -- the
# without-replacement partition is reproduced by a randperm.
#
# B stays at the config's 1024 and that is a MEASURED ceiling, not a default:
# B=1536 raises throughput to 15,166 sps (1.43x for 1.5x the lanes, iteration
# wall 69.5 -> 72 s, so collection is launch-latency bound and B is the real
# throughput lever) but peaks at 68.17 GiB and OOMs; 2048 and 3072 die outright.
# The blocker is ("next", "observation") at 13.35 GiB of the 27.68 GiB batch.
# It contributes nothing to the loss -- trl_env.py sets terminated = done and
# never sets truncated, so the bootstrap is multiplied by zero -- but it cannot
# simply be dropped, because in TorchRL it IS the next state (step_mdp promotes
# it to `observation`). The route to B=2048 is therefore float16 observation
# storage, as rl/tensor_env/train_t.py --obs-half already does; every feature is
# normalised into about [-1, 1], so the range is safe. That changes what the
# update sees and needs an A/B before it goes in.
set +e
python rl/train.py --device cuda --max-minutes "$MAX_MINUTES" \
    --min-sps "$MIN_SPS" --rb-free --profile-timing "$@"
rc=$?
set -e
echo "TRAIN-EXIT code=$rc telemetry=$GPU_CSV"
exit "$rc"
