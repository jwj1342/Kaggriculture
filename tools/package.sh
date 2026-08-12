#!/bin/bash
# Package an agent into the tar.gz Kaggle expects.
#
#     bash tools/package.sh agents/enhanced enhanced              # a directory
#     bash tools/package.sh agents/lib/<strategy>.py mine         # one generated strategy
#
# Produces submissions/<date>-<name>/submission.tar.gz with main.py and its
# modules at the archive ROOT -- Kaggle unpacks into /kaggle_simulations/agent/
# and loads main.py from there, so nested directories break the imports.
#
# Also snapshots the sources beside the archive, because a ladder entry has to
# stay traceable to the code that produced it months later.

set -euo pipefail
SRC="${1:?usage: package.sh <agent-dir> <name>}"
NAME="${2:?usage: package.sh <agent-dir> <name>}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="submissions/$(date +%F)-${NAME}"
mkdir -p "$OUT"

# A generated strategy is `<name>.py` beside a shared `kg_rules.py`. Accept the
# strategy file directly and assemble the pair, so submitting one is a single
# command and nobody has to remember that the rules travel with it.
if [ -f "$SRC" ] && [ "${SRC##*.}" = "py" ]; then
  STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
  cp "$SRC" "$STAGE/main.py"
  RULES="$(dirname "$SRC")/kg_rules.py"
  [ -f "$RULES" ] || RULES="$ROOT/agents/kg_rules.py"
  [ -f "$RULES" ] || { echo "error: kg_rules.py not found beside $SRC" >&2; exit 1; }
  cp "$RULES" "$STAGE/"
  SRC="$STAGE"
fi

[ -f "$SRC/main.py" ] || { echo "error: $SRC/main.py not found" >&2; exit 1; }

cp "$SRC"/*.py "$OUT"/
tar -czf "$OUT/submission.tar.gz" -C "$SRC" $(cd "$SRC" && ls *.py)

# --- verify the archive is loadable the way Kaggle will load it -------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
tar -xzf "$OUT/submission.tar.gz" -C "$TMP"
[ -f "$TMP/main.py" ] || { echo "error: main.py is not at the archive root" >&2; exit 1; }

# shellcheck disable=SC1091
source setup_env.sh >/dev/null
python - "$TMP" <<'PY'
import sys, os
d = sys.argv[1]
sys.path.insert(0, d)
src = open(os.path.join(d, "main.py")).read()
env = {}
exec(compile(src, "main.py", "exec"), env)
last = [v for v in env.values() if callable(v)][-1]
assert last.__name__ == "agent", (
    f"last callable is {last.__name__!r}, not 'agent' -- get_last_callable takes [-1], "
    "so nothing may be defined or imported after the agent function")
print(f"  last callable resolves to {last.__name__}()")

from kaggle_environments import make
env_ = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 7})
env_.run([os.path.join(d, "main.py"), "starter"])
fin = env_.steps[-1]
assert all(s.status == "DONE" for s in fin), [str(s.status) for s in fin]
# $3,000 is the starting money: the agent passed every turn, which is what a
# missing import looks like from the outside. It has happened.
assert float(fin[0].reward or 0) > 3000.0, (
    f"scored exactly the starting money ({fin[0].reward}) -- it did nothing all "
    "season, which usually means an import failed inside the try/except")
print(f"  full 720-step episode from the unpacked archive: "
      f"{[float(s.reward or 0) for s in fin]}")
PY

SIZE=$(stat -c%s "$OUT/submission.tar.gz")
echo
echo "$OUT/submission.tar.gz  ($((SIZE / 1024)) KB, limit 100 MiB)"
echo "files in archive:"
tar -tzf "$OUT/submission.tar.gz" | sed 's/^/  /'
cat <<EOF

Submit with:
  cd $OUT
  kaggle competitions submit kaggriculture -f submission.tar.gz -m "<what changed>"

Then log it in docs/RUNS.md with the local result that motivated it.
EOF
