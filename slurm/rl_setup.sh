#!/bin/bash
# One-shot: install the rl/ training stack (torch + torchrl + tensordict,
# Compute Canada wheelhouse, --no-index) into the project venv. Idempotent;
# agents never import any of it. Versions are pinned in requirements/rl.txt
# -- the wheelhouse tensordict requires torch ~= 2.10.0.
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

pip install --no-index -r requirements/rl.txt
python - <<'EOF'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
import torchrl, tensordict
print("torchrl", torchrl.__version__, "| tensordict", tensordict.__version__)
from torchrl.envs import EnvBase
from torchrl.objectives import ClipPPOLoss, A2CLoss
from torchrl.objectives.value import GAE
from torchrl.collectors import SyncDataCollector
import numpy
print("numpy", numpy.__version__)
EOF
echo OK
