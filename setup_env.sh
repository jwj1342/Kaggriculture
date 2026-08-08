# Kaggriculture environment. Source it, do not execute it:
#
#     source setup_env.sh          # from the project root
#     source /path/to/Kaggriculture/setup_env.sh    # from anywhere
#
# Works on the Vulcan cluster and on an ordinary laptop; the module load is
# skipped where Lmod does not exist.
#
# Every credential and cache path is redirected into the project directory, so
# nothing this project does touches your home directory:
#
#   .kaggle/   Kaggle credentials  (KAGGLE_CONFIG_DIR)
#   data/      dataset downloads, kagglehub cache, arena.sqlite
#   .cache/    pip / HuggingFace / generic XDG caches
#
# Run tools/bootstrap.sh first if venv/ does not exist yet.

# Resolve the project root from this file's own location so the script works
# for any user, from any working directory, in bash or zsh.
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    _KG_SELF="${BASH_SOURCE[0]}"
elif [ -n "${(%):-%N}" ] 2>/dev/null; then
    _KG_SELF="${(%):-%N}"
else
    _KG_SELF="$0"
fi
PROJECT_ROOT="$(cd "$(dirname "${_KG_SELF}")" && pwd)"
unset _KG_SELF
export KG_ROOT="${PROJECT_ROOT}"

# Lmod exports these; neither exists on a personal machine, where the venv's
# own interpreter is used as-is.
if [ -n "${LMOD_CMD:-}${MODULESHOME:-}" ]; then
    module purge
    module load python/3.11.5
fi

if [ ! -f "${PROJECT_ROOT}/venv/bin/activate" ]; then
    echo "[Kaggriculture] venv/ is missing -- run: bash ${PROJECT_ROOT}/tools/bootstrap.sh"
    return 1 2>/dev/null || exit 1
fi

source "${PROJECT_ROOT}/venv/bin/activate"
unset PIP_PREFIX          # the cluster presets PIP_PREFIX, which fights venvs

# --- Kaggle credentials: this directory only; copies under $HOME never apply ---
export KAGGLE_CONFIG_DIR="${PROJECT_ROOT}/.kaggle"

# --- Data and caches: keep them beside the project, not in $HOME ---
export KAGGLEHUB_CACHE="${PROJECT_ROOT}/data/kagglehub"
export KAGGLE_DATA_DIR="${PROJECT_ROOT}/data"
export XDG_CACHE_HOME="${PROJECT_ROOT}/.cache"
export PIP_CACHE_DIR="${PROJECT_ROOT}/.cache/pip"
export HF_HOME="${PROJECT_ROOT}/.cache/huggingface"

mkdir -p "${KAGGLEHUB_CACHE}" "${PIP_CACHE_DIR}" "${HF_HOME}"

# --- Parallelism -------------------------------------------------------------
# Episodes are single-threaded and we parallelise across episodes, so BLAS
# threads only cause contention. Inside Slurm, follow the allocation.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"

echo "[Kaggriculture] root       = ${PROJECT_ROOT}"
echo "[Kaggriculture] python     = $(python -V 2>&1)"
echo "[Kaggriculture] kaggle CLI = $(kaggle --version 2>/dev/null | tail -1)"
echo "[Kaggriculture] credentials= ${KAGGLE_CONFIG_DIR}"
