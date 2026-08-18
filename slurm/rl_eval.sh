#!/bin/bash
# Export the latest RL checkpoint and evaluate it against the local roster.
# CPU-only -- never request a GPU.
#
#   sbatch slurm/rl_eval.sh                   # default run m1, 48 seeds
#   RUN=m1 SEEDS=96 sbatch slurm/rl_eval.sh   # heavier pass
#
# Results land in rl/runs/<run>/eval/<opponent-basename>.json plus the stdout
# tables in the job log. The verdict lines from tools/eval.py (Wilson interval
# vs 50%) are what counts -- README §9.
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-eval
#SBATCH --time=00:55:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=48G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-eval-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-eval-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS=1
export KG_FAST_ENV=1

RUN=${RUN:-m1}
SEEDS=${SEEDS:-48}
CKPT=${CKPT:-latest.pt}
AGENT="rl/out/groundhog/main.py"

python rl/export_agent.py --ckpt "rl/runs/${RUN}/${CKPT}" --name groundhog
mkdir -p "rl/runs/${RUN}/eval"

# Ten local opponents spanning every strength band this repo fields:
# baselines, our hand-written agents, a strong reference, recording-lineage
# agents at all three fidelities (bare ghost replays, spar reconstructions,
# a wrapped recording). Ghosts chosen by name order, not by weakness.
ROSTER=(
    random
    starter
    agents/barnyard.py
    agents/enhanced/main.py
    agents/bench3/ledger_lena.py
    agents/spar/estate-crew-grazier-flood-blind-muck.py
    agents/spar/estate-crew-berrybaron-metered-blind-muck.py
    agents/ghosts/ghost-89825016-0.py
    agents/ghosts/ghost-89830307-0.py
    agents/wrapped/w49.py
)

for opp in "${ROSTER[@]}"; do
    base=$(basename "$opp" .py)
    echo "=================================================================="
    echo "=== groundhog vs ${opp}"
    python tools/eval.py h2h "$AGENT" "$opp" --seeds "$SEEDS" -j "${SLURM_CPUS_PER_TASK}" \
        -o "rl/runs/${RUN}/eval/${base}.json"
done
echo "EVAL-DONE"
