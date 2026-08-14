#!/bin/bash
# Rebuild the opponent fields a fresh clone does not have.
#
# `agents/ref/` and `agents/ghosts/` are deliberately git-ignored: one is
# third-party code, the other is 150+ generated files reconstructible from
# public data. Both are load-bearing -- a bench without them measures our own
# family against itself, which is the mistake that cost this project a week
# (docs/ROADMAP.md §11).
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
  # team and drew every episode from the same hour. See docs/ROADMAP.md §11.
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

if [ "$WHAT" = "all" ] || [ "$WHAT" = "lines" ] || [ "$WHAT" = "wrapped" ]; then
  echo "==> wrapped (the real opposition: mined ladder plans, one shared layer)"
  # This is the field that matters now. `agents/bench3` ranks our own engine and
  # the agent we put on the ladder places 64th of 101 here, so a candidate that
  # only ever meets bench3 is being graded against the wrong thing entirely.
  #
  # Needs a trace library first; the pull is the slow part (~29 MB per episode,
  # deleted as soon as it is digested) and it is incremental, so an interrupted
  # run resumes.
  if [ ! -f data/tracelib/index.json ]; then
    if [ -f dist/tracelib.json.xz ]; then
      # The committed snapshot: 371 plans in 3 MB. Rebuilding it from Kaggle is
      # an hour of rate-limited pulling for the same result, so take the file.
      echo "    importing dist/tracelib.json.xz"
      python tools/tracelib.py import dist/tracelib.json.xz
    else
      echo "    no trace library -- pulling five post-rebalance days (needs a Kaggle key)"
      python tools/tracelib.py pull \
          --dates 2026-08-07,2026-08-08,2026-08-09,2026-08-10,2026-08-11 \
          --per-date "${N}" -j 8
    fi
  fi
  python tools/tracelib.py emit --out agents/lines --top 12 --min-score 50000 >/dev/null
  python tools/wrap.py --top 100 --out agents/wrapped
  echo "    $(ls agents/wrapped/*.py 2>/dev/null | wc -l) wrapped plans"
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "bench" ]; then
  echo "==> bench3 (the engine-level reference field)"
  python tools/registry.py gen --plan bench --out agents/bench3 >/dev/null
  # `gen` does not clean the directory, so an atom removed from the plan lingers
  # as a stale file. `dairy` was cut on 2026-08-11 and has to go by hand.
  rm -f agents/bench3/estate-crew-dairy-*.py
  # tier 6-9 only. `rancher_rita` and `melon_mateo` (tiers 5 and 4) are beaten
  # 100% of the time by *both* the champion and our own engine -- measured over
  # 192 seeds -- so they carry no information at either level any more.
  for a in closer_cleo ledger_lena broker_bea slotter_silas; do
    [ -f "agents/ref/$a.py" ] && cp "agents/ref/$a.py" agents/bench3/
  done
  [ -f agents/lines/line1.py ] && cp agents/lines/line1.py agents/bench3/
  # The current champion, so a candidate is measured against what it has to beat
  # rather than against whatever was best last week. `agents/CHAMPION` is tracked
  # in git; its last line is the path.
  CHAMP="$(grep -v '^#' "$ROOT/agents/CHAMPION" | grep -v '^$' | tail -1)"
  if [ -n "$CHAMP" ] && [ -f "$ROOT/$CHAMP" ]; then
    cp "$ROOT/$CHAMP" agents/bench3/champion.py
    [ -f "$ROOT/$(dirname "$CHAMP")/kg_rules.py" ] && \
      cp "$ROOT/$(dirname "$CHAMP")/kg_rules.py" agents/bench3/ 2>/dev/null
    echo "    champion: $CHAMP"
  else
    echo "    WARNING: agents/CHAMPION points at $CHAMP, which is missing" >&2
  fi
  echo "    $(ls agents/bench3/*.py | wc -l) opponents"
fi

echo
echo "done. Two fields, for two different levels -- see docs/VALIDATING.md:"
echo "  agents/wrapped/*.py    THE REAL FIELD. 100 mined ladder plans, one shared"
echo "                         adaptive layer. What we submitted places 64th here."
echo "  benchmarks/strongest.py  the bar to clear (source team #1), committed, = CHAMPION"
echo "  agents/bench3/*.py     ENGINE level. Ranks agents that win 50-70% of it."
echo "  agents/ref/{closer_cleo,slotter_silas,ledger_lena,broker_bea}.py"
echo "                         WRAPPED level. The only field that still separates"
echo "                         agents winning 98%+ of bench3."
echo "  agents/ghosts/*.py     156 replayed ladder trajectories (saturating)"
echo "  agents/lines/line*.py  one representative per distinct ladder plan"
