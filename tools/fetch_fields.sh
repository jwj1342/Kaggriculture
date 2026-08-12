#!/bin/bash
# Rebuild the opponent fields a fresh clone does not have.
#
# `agents/ref/` and `agents/ghosts/` are deliberately git-ignored: one is
# third-party code, the other is 150+ generated files reconstructible from
# public data. Both are load-bearing -- a bench without them measures our own
# family against itself, which is the mistake that cost this project a week
# (docs/LADDER_FIELD.md).
#
#     bash tools/fetch_fields.sh            # both, default sizes
#     bash tools/fetch_fields.sh ref        # just the reference agents
#     bash tools/fetch_fields.sh ghosts 60  # just ghosts, 60 of them
#
# Needs Kaggle credentials in .kaggle/ (see docs/ONBOARDING.md §1).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source setup_env.sh

WHAT="${1:-all}"
N="${2:-60}"

if [ "$WHAT" = "all" ] || [ "$WHAT" = "ref" ]; then
  echo "==> reference agents (raykkretzschmar/kaggriculture-reference-agents, MIT)"
  # Ten agents in a documented teaching ladder, tiers 0-9. Tiers 6-9 replay the
  # shared meta line that 79% of the top of the ladder plays, which is why they
  # belong in every field. Licence and scope are in agents/ref/NOTICE -- read it
  # before reusing anything from tiers 6-9 in a submission.
  mkdir -p agents/ref
  kaggle datasets download raykkretzschmar/kaggriculture-reference-agents \
      --unzip -p agents/ref --force
  echo "    $(ls agents/ref/*.py | wc -l) agents"
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "ghosts" ]; then
  echo "==> ghosts (~90 s each: a 32 MB replay in, an 11 KB opponent out)"
  # Stratified on purpose: at most two per team, score bands filled evenly, and
  # sampled round-robin across days. A naive pull gave 12% of the field to one
  # team and drew every episode from the same hour. See docs/GHOSTS.md.
  python tools/ghost.py make \
      --dates 2026-08-09,2026-08-08,2026-08-07,2026-08-06 \
      --limit "$N" --per-team 2 --bands
  python tools/ghost.py balance
  echo
  echo "    verify before trusting them:"
  echo "      python tools/ghost.py verify --limit 12"
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "lines" ]; then
  echo "==> lines (the distinct plans the ladder actually plays)"
  # Needs agents/ghosts/ to exist. Aligns within +-8 turns before comparing:
  # two farms running the same plan one turn apart agree on *nothing* index to
  # index, which is why 156 recordings once looked like 156 strategies.
  python tools/lines.py --emit agents/lines
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "bench" ]; then
  echo "==> bench3 (the engine-level reference field)"
  python tools/registry.py gen --plan bench --out agents/bench3 >/dev/null
  # `gen` does not clean the directory, so an atom removed from the plan lingers
  # as a stale file. `dairy` was cut on 2026-08-11 and has to go by hand.
  rm -f agents/bench3/estate-crew-dairy-*.py
  for a in closer_cleo ledger_lena broker_bea rancher_rita melon_mateo; do
    [ -f "agents/ref/$a.py" ] && cp "agents/ref/$a.py" agents/bench3/
  done
  [ -f agents/lines/line1.py ] && cp agents/lines/line1.py agents/bench3/
  echo "    $(ls agents/bench3/*.py | wc -l) opponents"
fi

echo
echo "done. Two fields, for two different levels -- see docs/VALIDATING.md:"
echo "  agents/bench3/*.py     ENGINE level. Ranks agents that win 50-70% of it."
echo "  agents/ref/{closer_cleo,slotter_silas,ledger_lena,broker_bea}.py"
echo "                         WRAPPED level. The only field that still separates"
echo "                         agents winning 98%+ of bench3."
echo "  agents/ghosts/*.py     156 replayed ladder trajectories (saturating)"
echo "  agents/lines/line*.py  one representative per distinct ladder plan"
