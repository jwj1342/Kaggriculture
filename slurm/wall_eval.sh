#!/bin/bash
# Paired head-to-head against the four strong local recordings, and nothing else.
#
# Why this exists separately from slurm/rl_eval.sh: that script owns a ten-agent
# roster spanning every strength band and re-exports the checkpoint itself. The
# question here is narrower and is the one the G1/G3 gates actually turn on --
# "does this agent beat the strong tapes" -- and the four walls are cleo, lena,
# bea and w49. Two of them (cleo, bea) are not in rl_eval.sh's roster at all.
#
# Takes an ALREADY EXPORTED agent so the thing measured is the same file a
# submission would ship, not a fresh export that might differ.
#
#   AGENT=rl/out/anvil-fix/main.py SEEDS=192 sbatch slurm/wall_eval.sh
#
# Every seed is played twice with the seats swapped (tools/eval.py h2h), and the
# verdict is the Wilson interval against 50%, not the mean.
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-wall-eval
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/wall-eval-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/wall-eval-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
# Both measured: eval is single-threaded Python, and letting BLAS grab threads
# per worker oversubscribes the node and has silently halved throughput here.
export OMP_NUM_THREADS=1
export KG_FAST_ENV=1

AGENT=${AGENT:?set AGENT to an exported main.py}
SEEDS=${SEEDS:-192}
LABEL=${LABEL:-$(basename "$(dirname "$AGENT")")}
OUTDIR=${OUTDIR:-rl/out/${LABEL}/wall_eval}
mkdir -p "$OUTDIR"

WALLS=(
    agents/bench3/closer_cleo.py
    agents/bench3/ledger_lena.py
    agents/bench3/broker_bea.py
    agents/wrapped/w49.py
)

echo "WALL-EVAL agent=${AGENT} label=${LABEL} seeds=${SEEDS} cpus=${SLURM_CPUS_PER_TASK}"
for opp in "${WALLS[@]}"; do
    base=$(basename "$opp" .py)
    echo "=================================================================="
    echo "=== ${LABEL} vs ${base}"
    python tools/eval.py h2h "$AGENT" "$opp" --seeds "$SEEDS" \
        -j "${SLURM_CPUS_PER_TASK}" -o "${OUTDIR}/${base}.json"
done
echo "WALL-EVAL-DONE"
