#!/bin/bash
# One-shot: install torch (Compute Canada wheelhouse, --no-index) into the
# project venv for the rl/ training line. Idempotent; agents never import it.
#
#   sbatch slurm/rl_setup.sh
#
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-setup
#SBATCH --time=00:15:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-setup-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-setup-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"

pip install --no-index torch
python - <<'EOF'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
import numpy
print("numpy", numpy.__version__)
EOF
echo OK
