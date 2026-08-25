#!/bin/bash
# CPU regression gates for changes to the RL trainer and its infrastructure.
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-rl-test
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=/scratch/jwj/Kaggriculture/logs/rl-test-%j.out
#SBATCH --error=/scratch/jwj/Kaggriculture/logs/rl-test-%j.err

set -euo pipefail
PROJECT=/scratch/jwj/Kaggriculture
cd "$PROJECT"
source "$PROJECT/setup_env.sh"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-2}"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"

echo "TEST-META job=${SLURM_JOB_ID:-local} host=$(hostname) commit=$(git rev-parse HEAD)"
python tests/test_infra.py
python tests/test_stats.py
python tests/test_macro_audit.py
python rl/tensor_env/test_trl.py
echo "RL-TESTS-PASS"
