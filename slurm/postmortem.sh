#!/bin/bash
#SBATCH --account=def-zhouyang
#SBATCH --job-name=kg-postmortem
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --output=logs/postmortem-%j.out

set -euo pipefail
PROJECT="${KG_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT"
source setup_env.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg
python tools/build_postmortem.py
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import shutil
import nbformat
from nbclient import NotebookClient

root = Path.cwd()
path = root / 'notebooks/postmortem/kaggriculture-final-strategy-and-lessons.ipynb'
work = root / 'data/postmortem-notebook'
work.mkdir(parents=True, exist_ok=True)
nb = nbformat.read(path, as_version=4)
nbformat.validate(nb)
client = NotebookClient(nb, timeout=180, kernel_name='python3', resources={'metadata': {'path': str(work)}})
client.execute()
nbformat.validate(nb)
assert not any(o.output_type == 'error' for c in nb.cells if c.cell_type == 'code' for o in c.outputs)
nbformat.write(nb, path)
for suffix in ('svg', 'png'):
    shutil.copyfile(work / f'postmortem_artifacts/confirmation-effects.{suffix}', root / f'docs/assets/confirmation-effects.{suffix}')
svg = root / 'docs/assets/confirmation-effects.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
checks = {'slurm_job_id': os.environ.get('SLURM_JOB_ID'), 'nbformat_valid': True,
          'all_code_cells_executed': all(c.execution_count is not None for c in nb.cells if c.cell_type == 'code'),
          'cells': len(nb.cells), 'code_cells': sum(c.cell_type == 'code' for c in nb.cells),
          'notebook_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'artifact_checks': json.loads((work / 'postmortem_artifacts/artifact-checks.json').read_text())}
(root / 'notebooks/postmortem/EXECUTION.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks, indent=2))
PY
