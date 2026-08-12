# Kaggriculture

Working codebase for the Kaggle **Kaggriculture** simulation competition
(<https://www.kaggle.com/competitions/kaggriculture>), running on the Vulcan HPC
cluster.

You submit a **program**, not predictions. It plays 720-turn farming seasons
head-to-head against other people's programs on a live ladder. Ranking is
win/loss only — the coin margin never counts.

- **Prizes** $50,000 as ten equal $5,000 places, so the target is **top 10**.
- **Timeline** started 2026-07-29 · entry and merger deadline 2026-09-23 · final
  submission 2026-09-30 · leaderboard converges ~2026-10-15.
- **Field** 2,903 teams, 5,376 submissions as of 2026-08-07.
- **Status** `mgtight` live at ~790 (from 623 at the first submission).
  **1,228,544 local episodes** across 32 runs, plus 184 real ladder replays digested.

### → New here? Read [`docs/ONBOARDING.md`](docs/ONBOARDING.md). It takes an hour and ends with you having run a real tournament.

---

## Setup

Runs on the Vulcan cluster **and on an ordinary laptop** — Python 3.9+ is the
only hard requirement. Both scripts detect the platform themselves.

```bash
bash tools/bootstrap.sh          # builds venv/, verifies with a real episode
# put your own Kaggle credentials in .kaggle/  (see ONBOARDING §1)
source setup_env.sh              # every session, works from any directory
```

`setup_env.sh` activates `venv/` and redirects **every** credential and cache
path into this directory, so nothing here touches your home directory. On the
cluster it also loads `module python/3.11.5`; elsewhere that step is skipped.

Dependencies live in `requirements/`, split by **installation semantics** rather
than by purpose, because a flat file cannot express them:

| File | Installed with | Why |
|---|---|---|
| `base.txt` | plain `pip install -r` | numpy, pandas, kaggle, kagglehub, jupytext |
| `nodeps.txt` | `pip install --no-deps -r` | `kaggle-environments` declares 19 dependencies including `open_spiel`, which fails to build; Kaggriculture needs three of them |
| `lock.txt` | nothing — generated | audit snapshot of a known-good cluster environment |

Regenerate the lock with `bash tools/bootstrap.sh --freeze`.

> On the cluster, `$SCRATCH` is **not backed up** and is purged after 60 days of
> inactivity. `data/arena.sqlite` is the one irreplaceable file — copy it to
> `~/projects/` if you care about it.

## Daily commands

```bash
python tools/trace.py agents/barnyard.py starter        # day-by-day, one episode
python tools/stress.py agents/barnyard.py -j 8          # 28 pathological configs
python tools/registry.py list                           # the atom space
python tools/registry.py gen --plan all --out agents/lib
python tools/db.py stats                                # what has ever been run
python tools/sync.py export --full                      # shareable 4.6 MB snapshot

# tournaments: Slurm on the cluster, or the runner directly with -j elsewhere
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8
sbatch slurm/tournament.sh roundrobin --from-run latest --top 24 --seeds 24
python tools/tournament.py roundrobin --agents a.py b.py --seeds 8 -j 8

python tools/leaderboard.py --run latest                # regenerates the leaderboard
```

`slurm/` is cluster-only; every script there is a thin wrapper that calls the
same tool with `-j $SLURM_CPUS_PER_TASK`.

---

## The idea

Every strategy is one option from each of **seven orthogonal atoms**, so its name
*is* its definition and the library is a cross product rather than a pile of
files:

```
land - labour - produce - market - intel - muck - adapt

smallhold-crew-mgtightgrain-flood-blind-compost-shopwise
```

The seventh axis, `adapt`, is the only one about the *town* rather than the farm
or the opponent: shops are drawn with replacement, so demand for one product
swings 49x between episodes.
There are **no version numbers anywhere in this repo**.

Everything is measured locally before it goes near the ladder. `tools/tournament.py`
runs panel screens (`O(n)`) and round robins (`O(n²)`), persists every episode to
SQLite, and fits **Bradley-Terry** strengths — the same estimator Kaggle uses for
the final leaderboard.

Every episode lands in `data/arena.sqlite` on the cluster and is mirrored to a
**Cloudflare D1** database, so collaborators query the measured episodes without
a cluster account or a downloaded file. Sync is one-way, local to remote;
see `docs/CONTRIBUTING.md` "The sync contract".

**Live leaderboard:** <https://claude.ai/code/artifact/c576b6af-80f5-4240-9f97-40e294ee47fa>
· regenerate with `tools/leaderboard.py`, same URL every time.

---

## How it fits together

Four layers. Each one only depends on the layer above it, and everything below
`tools/` is regenerated rather than edited.

```
  DEFINITION      tools/registry.py          seven atom tables + composition plans
                  agents/_engine.py          one execution path, generated CONFIG block
                          │
                          │  registry.py gen --plan all
                          ▼
  STRATEGIES      agents/lib/*.py            standalone, submittable agents
                  agents/spar/*.py           opponents reconstructed from real
                                             ladder replays -- keep in every field
                  agents/lib/manifest.json   name, atoms, source hash
                          │
                          │  sbatch slurm/tournament.sh
                          ▼
  EVIDENCE        data/arena.sqlite          every episode ever run
                    agents    name, atoms, source hash
                    runs      one row per tournament
                    episodes  result, shop draw, final prices, ~1.6 KB digest x2
                    ratings   Bradley-Terry snapshot per run
                          │
              ┌───────────┼────────────────────┐
              │           │                    │
              ▼           ▼                    ▼
  OUTPUT   db.py      leaderboard.py      hand analysis -> docs/
           queries    docs/LEADERBOARD.md
                      site/leaderboard.html -> published artifact
```

**Why this shape.** A strategy is never written by hand, so two people cannot
produce the same policy under different names, and a name always describes the
agent. Every number ever cited traces back to rows in one database, so a claim
can be re-checked with a query instead of a re-run. The published page is a pure
function of that database, so refreshing it is one command and the URL never
changes.

Sideways from that pipeline sit the harnesses that answer narrower questions:
`tools/trace.py` (why did this episode go like that), `tools/stress.py` (does it
survive abuse), `tools/eval.py` (is A better than B, with an interval).

## Layout

```
agents/
  _engine.py       the single execution path; its CONFIG block is generated
  lib/             generated strategies + manifest.json  (git-ignored)
  spar/            sparring field rebuilt from ladder replays  (git-ignored)
  barnyard.py      hand-tuned original; the first agent submitted
  legacy/          superseded ad-hoc agents, kept because docs cite them
tools/
  bootstrap.sh     build venv/ from scratch
  registry.py      atom definitions, composition plans, code generation
  tournament.py    panel / round-robin runs, persisted to SQLite
  leaderboard.py   renders docs/LEADERBOARD.md + site/leaderboard.html from the DB
  db.py            schema and queries over every episode ever run
  eval.py          A/B with Wilson intervals and a paired bootstrap
  stress.py        28 pathological environment configurations
  trace.py         day-by-day trace of one episode
  build_notebook.py  regenerates notebooks/baseline.ipynb from an agent
  arena.py sweep.py league.py   older single-purpose harnesses
docs/              all knowledge and results -- see the table below
data/arena.sqlite  the evidence layer (136 MB, git-ignored; share via tools/sync.py)
dist/              exported snapshots -- 4.6 MB full, 36 KB rankings-only
reference/
  engine/          copy of kaggriculture.py -- the rules that actually run
  docs/            official README.md and AGENTS.md from the competition dataset
  notebooks/       public notebooks pulled from Kaggle (+ .py conversions)
requirements/      base.txt, nodeps.txt, lock.txt -- split by install semantics
submissions/       exact snapshot of every file sent to Kaggle
slurm/             cluster-only wrappers: tournament.sh, eval.sh, league.sh, sweep.sh
site/              generated leaderboard page
logs/              Slurm output and pre-database league JSON
```

**Generated, never hand-edited:** `agents/lib/`, `agents/spar/`, `docs/LEADERBOARD.md`,
`site/leaderboard.html`, `notebooks/baseline.ipynb`. **Git-ignored:** those plus
`venv/`, `.cache/`, `.kaggle/`, `data/`. A fresh checkout is ~6 MB; see
`docs/ONBOARDING.md` §1 for restoring the library and the database.

## FAQ

Three questions everyone asks in their first week. Longer answers behind each
link; these are enough to get moving.

### 1. How do I actually submit to Kaggle?

**Credentials first.** `setup_env.sh` points `KAGGLE_CONFIG_DIR` at the
project's own `.kaggle/`, so nothing here touches `~/.kaggle` and you can hold
several accounts on one machine:

```bash
mkdir -p .kaggle && chmod 700 .kaggle
printf '{"username":"YOU","key":"..."}' > .kaggle/kaggle.json   # kaggle.com/settings/api
chmod 600 .kaggle/*
source setup_env.sh
kaggle competitions submission-limits kaggriculture     # proves it works
```

**Then submit.** A single-file agent goes up as `main.py`; a multi-file one has
to be a tar.gz with every module at the **archive root**, because Kaggle unpacks
into `/kaggle_simulations/agent/` and a nested directory breaks the imports.

```bash
python tools/stress.py agents/mine/main.py -j 14        # must be 28/28
mkdir -p submissions/$(date +%F)-mine && cp agents/mine/main.py submissions/$(date +%F)-mine/
kaggle competitions submit -c kaggriculture \
    -f submissions/$(date +%F)-mine/main.py -m "one sentence + the local evidence"

# multi-file: builds, unpacks, checks get_last_callable, runs a full episode
bash tools/package.sh agents/mine mine
```

**Three rules that have each already cost us a slot** — the full list is
[`docs/SUBMISSION_POLICY.md`](docs/SUBMISSION_POLICY.md):

* **Five a day, only the latest two active, and deactivation is by *recency*, not
  score.** A third submission drops the older active one even if it is your best.
* **An agent needs 40+ ladder episodes before its score means anything** — about
  four hours. Submitting again inside that window throws away the measurement you
  were waiting for.
* **Always snapshot** under `submissions/<date>-<name>/` and log the local
  evidence in [`docs/RUNS.md`](docs/RUNS.md). A ladder entry has to stay
  traceable months later.

### 2. How do I run my strategy locally first?

```bash
source setup_env.sh                  # any directory, any machine
bash tools/bootstrap.sh              # only if venv/ is missing
bash tools/fetch_fields.sh           # opponents -- a fresh clone has none
```

Then, cheapest first:

| what you want | command |
|---|---|
| does it crash? | `python tools/stress.py <agent>.py -j 8` |
| one episode, day by day | `python tools/trace.py <agent>.py starter` |
| is A better than B? | `python tools/eval.py h2h a.py b.py --seeds 96 -j 32` |
| against the whole field | `sbatch --array=0-15 --cpus-per-task=32 --mem=40G --time=00:30:00 slurm/tournament_array.sh panel --agents <agent>.py --panel agents/bench3/*.py --seeds 96 --jobs 32 --label mine` |
| fold the shards in | `python tools/tournament.py ingest --shards data/shards/mine` |

**Do not hand-write a strategy file.** Add an atom option in
`tools/registry.py` and regenerate — the name is the definition, and every
generated strategy shares one execution path so the comparison stays fair.

**Then read [`docs/VALIDATING.md`](docs/VALIDATING.md) before believing the
number.** It is short and it exists because this project has produced confident
nonsense at both ends of the scale: a reference field everything beat, and a
reference field everything beat by the same amount. Four seeds resolve nothing —
three changes read positive over four seeds and were 21 to 44 points *behind*
over 2,304 episodes an arm.

### 3. How do I analyse a game?

**Your own ladder games.** Kaggle keeps the replays; `ladder.py` pulls them,
keeps a ~1.4 KB digest and deletes the 19 MB original:

```bash
python tools/ladder.py pull --limit 40      # your recent ladder episodes
python tools/ladder.py stats                # win rate, opponent shapes, what sold
```

**The top of the ladder**, which you will never be matched into:

```bash
python tools/topeps.py index                # list Kaggle's daily top-episode dumps
python tools/topeps.py pull                 # digest them into the database
python tools/ghost.py make --limit 60 --per-team 2 --bands
python tools/lines.py                       # which distinct plans they actually play
```

A *ghost* is one of those trajectories turned into a local opponent — 11 KB, the
recorded action sequence replayed turn by turn. Nothing is fitted.
[`docs/GHOSTS.md`](docs/GHOSTS.md) has the sampling design and its limits.

**One episode, in detail.** `tools/trace.py` prints the farm day by day — tiles,
shed, prices, money. **Illegal actions are silent no-ops in this engine**, so a
bug looks exactly like bad strategy and a final score will never tell you which
you have. Every five-figure defect in this repo was found by reading a trace,
not by staring at a score.

---

## Documentation

Everything the project knows lives in `docs/`. Nothing is only in someone's head
or only in a chat log.

| Document | What it holds |
|---|---|
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md) | **start here** — setup, first tournament, the five things that will bite you |
| [`docs/GAME_ECONOMICS.md`](docs/GAME_ECONOMICS.md) | what the engine actually rewards; the three places the official page is wrong |
| [`docs/VALIDATING.md`](docs/VALIDATING.md) | **is my change real?** two fields for two levels, and the two ways to get a confident wrong answer |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | **where this went and why** — read first if you have been away |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | the long form: how many episodes, and what the randomness does |
| [`docs/MAP.md`](docs/MAP.md) | **which document answers which question, and where each behaviour lives in the code** |
| [`docs/LADDER_FIELD.md`](docs/LADDER_FIELD.md) | what real opponents do, and why local rank did not predict it |
| [`docs/ENGINE_CHANGES.md`](docs/ENGINE_CHANGES.md) | every change to the agent, what it measured, and the seventeen that were rejected |
| [`docs/ATOM_EFFECTS.md`](docs/ATOM_EFFECTS.md) | what each atom measured to be worth — superseded in part, see the notice at the top |
| [`docs/STRATEGY_LIBRARY.md`](docs/STRATEGY_LIBRARY.md) | the atom taxonomy and the boundary cases |
| [`docs/ADVERSARIAL.md`](docs/ADVERSARIAL.md) | can you win by suppressing the opponent? (partly, and not how you'd think) |
| [`docs/IMPROVEMENTS.md`](docs/IMPROVEMENTS.md) | backlog, with a measured-and-rejected list |
| [`docs/ENHANCED_BASELINE.md`](docs/ENHANCED_BASELINE.md) | the current best agent: every choice traced to a measurement, plus one retraction |
| [`docs/TOOLS.md`](docs/TOOLS.md) | every script: what it does, what it reads and writes, known limitations |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | conventions, the sync contract, adding atoms, submitting |
| [`docs/RUNS.md`](docs/RUNS.md) | provenance: every experiment and the claim it supports |
| [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md) | generated from the database — do not hand-edit |

---

## What we know so far

Short version; the evidence is in `docs/ATOM_EFFECTS.md` and, for anything about
the real field, `docs/LADDER_FIELD.md`.

**The loop that produces the gains.** Local measurement kept converging on the
wrong answer until the ladder corrected it, three times. The sequence that works:
submit → pull our own replays with `tools/ladder.py` → read what the opponent
*did*, not what their farm looked like → change one thing → A/B it at 2,000+
episodes an arm → resubmit. `docs/MAP.md` is the index; `docs/ENGINE_CHANGES.md`
records all twenty-eight attempts, eleven of which landed.

The single most valuable measurement in the project came from one replay's
**action histogram**: the leader spends 1.02 movement actions per action that
does work and we spent 2.4, because 50% of their work is done without moving —
an animal takes FEED, CARE, COLLECT_FERTILIZER and HARVEST on one tile. Three
*shape* ideas taken from the same replay all measured negative first.

**Local rank did not predict ladder rank, and we know why.** `enhanced` beats
`barnyard` 384 out of 384 locally and is level with it against real opponents
(49% and 47% over 94 pulled ladder episodes). Three causes, all now fixed:
melon is the *smallest* market in the game — no shop buys it, so its whole
season is worth $7,500 against strawberry's $90,000; the library could not issue
`FERTILIZE`, which doubles every `ongoing` crop; and the engine bought livestock
it could not feed, which penalised crop plans hardest because crops and animals
compete for the same opening cash. `agents/spar/` now puts real opponent shapes
in the field.

**The engine was rebalanced on 2026-08-06/07** (`kaggle-environments` 1.32.6):
town-centre demand halved and shops now draw **with replacement**. Every public
meta analysis dated 08-06 or earlier describes a game that no longer exists.

**Labour dominates every other axis, and its failure mode is inverted.**
`crew` (11 hands, ≤6% of cash) wins 55%; `swarm` (30 hands, no payroll cap) wins
**10%** — worse than never hiring at all. The n-th hire costs `fib(n)`.

**Fertilizer is bridge financing, not a bonus.** An animal-only farm that never
collects it ends the season on **$79**: it goes bankrupt buying feed before the
first milk arrives on day 8. A farm with crop income survives the same ablation
at $44k.

**Land matters an order of magnitude less than labour.** One or two quadrants
beat three or four by ~10 points with hands to work them, and by nothing without.

**Dumping beats metering, conditionally.** `flood` wins 83% against `metered`'s
77% while *earning less* — it wins by denying the shared market. Three of four
paired configurations favour it; the fourth reverses.

**The strategy space is non-transitive.** flood > metered > spite > flood, all
measured. Any ranking is a ranking against its field.

**Our own agent is not our best.** `barnyard` ranks 14th of 38 locally, behind
every `orchardherd` composition by ~21,000 median money — and it is what is on
the ladder.

**Nothing local has been validated against the real ladder.** Every local
opponent is one we wrote. That is the biggest open question in the project.
