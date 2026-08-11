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

echo
echo "done. The standard field is now:"
echo "  agents/ref/*.py        the public meta and the teaching ladder"
echo "  agents/ghosts/*.py     replayed top-player trajectories"
echo "  agents/bench3/*.py     regenerate with: python tools/registry.py gen --plan bench --out agents/bench3"
echo "                         then copy in the tier 4-9 agents from agents/ref/"
