#!/bin/bash
# Behaviour cloning: collect scripted-expert episodes, clone into the policy
# net, leave a checkpoint under rl/runs/<run>/ that the unified trainer
# consumes via `rl/train.py --init-from rl/runs/<run>/bc_init.pt`
# (pair with --freeze-policy-until for the value warm-up). CPU-only.
#
#   RUN=m2 sbatch slurm/rl_bc.sh
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-bc
#SBATCH --time=00:40:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=48G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-bc-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-bc-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS=1
export KG_FAST_ENV=1

RUN=${RUN:-m2}
if [ "${SKIP_COLLECT:-0}" != "1" ]; then
    python rl/bc/collect_bc.py --episodes 224 --jobs 28
fi
python rl/bc/train_bc.py --run "$RUN" --epochs 6 --threads "${SLURM_CPUS_PER_TASK}"

# Sanity-read on the *pristine* clone before any PPO touches it: export it and
# play a handful of real episodes. A healthy clone should be near the teacher
# (>20k money, beats starter); a collapsed one means BC itself is the problem.
python rl/export_agent.py --ckpt "rl/runs/${RUN}/bc_init.pt" --name groundhog-bc
python tools/eval.py h2h rl/out/groundhog-bc/main.py starter --seeds 4 -j 8
echo "BC-VERIFY-DONE"
