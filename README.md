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
- **Status** one agent live (`55332339`, ~623 rating). 95,000 local episodes run.

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

Every strategy is one option from each of **six orthogonal atoms**, so its name
*is* its definition and the library is a cross product rather than a pile of
files:

```
land - labour - produce - market - intel - muck

estate-crew-mixedfarm-metered-blind-muck
```

9,216 strategies are expressible; 594 are materialised and have been played.
There are **no version numbers anywhere in this repo**.

Everything is measured locally before it goes near the ladder. `tools/tournament.py`
runs panel screens (`O(n)`) and round robins (`O(n²)`), persists every episode to
SQLite, and fits **Bradley-Terry** strengths — the same estimator Kaggle uses for
the final leaderboard.

Every episode lands in `data/arena.sqlite` on the cluster and is mirrored to a
**Cloudflare D1** database, so collaborators query 85,000 measured episodes
without a cluster account or a downloaded file. Sync is one-way, local to remote;
see `docs/CONTRIBUTING.md` "The sync contract".

**Live leaderboard:** <https://claude.ai/code/artifact/c576b6af-80f5-4240-9f97-40e294ee47fa>
· regenerate with `tools/leaderboard.py`, same URL every time.

---

## How it fits together

Four layers. Each one only depends on the layer above it, and everything below
`tools/` is regenerated rather than edited.

```
  DEFINITION      tools/registry.py          six atom tables + composition plans
                  agents/_engine.py          one execution path, generated CONFIG block
                          │
                          │  registry.py gen --plan all
                          ▼
  STRATEGIES      agents/lib/*.py            594 standalone, submittable agents
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
  lib/             594 generated strategies + manifest.json  (git-ignored)
  barnyard.py      hand-tuned original; the agent on the ladder
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

**Generated, never hand-edited:** `agents/lib/`, `docs/LEADERBOARD.md`,
`site/leaderboard.html`, `notebooks/baseline.ipynb`. **Git-ignored:** those plus
`venv/`, `.cache/`, `.kaggle/`, `data/`. A fresh checkout is ~6 MB; see
`docs/ONBOARDING.md` §1 for restoring the library and the database.

## Documentation

Everything the project knows lives in `docs/`. Nothing is only in someone's head
or only in a chat log.

| Document | What it holds |
|---|---|
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md) | **start here** — setup, first tournament, the five things that will bite you |
| [`docs/GAME_ECONOMICS.md`](docs/GAME_ECONOMICS.md) | what the engine actually rewards; the three places the official page is wrong |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | **read before trusting any number you produce** |
| [`docs/ATOM_EFFECTS.md`](docs/ATOM_EFFECTS.md) | what each atom measured to be worth, over 85,064 episodes |
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

Short version; the evidence is in `docs/ATOM_EFFECTS.md`.

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
