#!/bin/bash
# Sharded tournament across a Slurm job array. CPU-only -- never request a GPU.
#
# Each array task runs a stride-slice of the job list on a whole node and writes
# an append-only JSONL shard. Nothing but the final `ingest` touches the
# database: two of the three data-integrity incidents in docs/RUNS.md came from
# concurrent or unclosed SQLite writers, so array tasks are kept away from it.
#
#   sbatch --array=0-15 slurm/tournament_array.sh roundrobin \
#       --agents agents/spar/*.py agents/enhanced/main.py --seeds 24 \
#       --label big-field
#   # when the array finishes:
#   python tools/tournament.py ingest --shards data/shards/big-field
#
# Sizing: one episode is ~2.6 s on one core with KG_FAST_ENV=1, so a 64-core
# task clears roughly 20 episodes a second. Pick the array width so each task
# gets 10-30 minutes of work -- short tasks backfill into idle time far more
# easily than one long job, which is the whole point of sharding here.
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-tourney-array
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=64
#SBATCH --mem=96G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/tourney-%A_%a.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/tourney-%A_%a.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS=1

# Verified byte-identical to the unpatched framework, 17% faster. See
# tools/tournament.py:_fast_env.
export KG_FAST_ENV=1

N=${SLURM_ARRAY_TASK_COUNT:-1}
K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK} shard=${K}/${N} job=${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}"

python tools/tournament.py "$@" --shard "${K}/${N}" -j "${SLURM_CPUS_PER_TASK}"
