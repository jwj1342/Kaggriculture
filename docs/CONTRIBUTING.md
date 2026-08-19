# Contributing

Conventions and workflows. Read `docs/ONBOARDING.md` first if you have not set up
the environment yet.

---

## Naming

**A strategy's name is its definition.** Seven atoms, fixed order, hyphen-joined:

```
land-labour-produce-market-intel-muck-adapt
```

There are **no version numbers anywhere in this repo**. `v1`, `v2`, `final2` and
friends carry no information, drift out of sync with what they label, and make
two identical configurations look different. If you need to talk about a point on
the grid by a shorter name, add an alias in `ALIASES` in `tools/registry.py` —
aliases are decoration on top of the real name, never a replacement.

Other naming rules in force:

| Thing | Convention | Example |
|---|---|---|
| Generated strategy | atom composition | `estate-crew-mixedfarm-metered-blind-muck-shopwise` |
| Hand-written agent | what it does | `agents/barnyard.py` |
| Submission snapshot | date + agent | `submissions/2026-08-07-barnyard/` |
| Tournament run | purpose + scale | `library-screen-594`, `confirm-38-representative` |
| Slurm log | tool + job id | `logs/tourney-409573.out` |

---

## Adding a strategy

Do **not** hand-write a new agent file. Pick a point on the grid:

```bash
python tools/registry.py list                          # see the space
python tools/registry.py gen --plan all --out agents/lib
```

If the strategy you want is not expressible, that means an atom is missing —
which is a more interesting change than a new file. See below.

---

## Adding an atom option

1. Add the option to the relevant table in `tools/registry.py` (`LAND`, `LABOUR`,
   `PRODUCE`, `MARKET`, `INTEL`, `MUCK`, `ADAPT`). The value is a dict of `CONFIG` keys.
2. Teach `agents/_engine.py` to read any new `CONFIG` key it introduces.
3. Regenerate: `python tools/registry.py gen --plan all --out agents/lib`
4. Validate every file still loads and exposes `agent` last:
   ```bash
   python - <<'EOF'
   import os
   for f in sorted(os.listdir("agents/lib")):
       if not f.endswith(".py"): continue
       env = {}
       exec(compile(open("agents/lib/"+f).read(), f, "exec"), env)
       last = [v for v in env.values() if callable(v)][-1]
       assert last.__name__ == "agent", f
   print("all ok")
   EOF
   ```
5. `python tools/stress.py agents/lib/<a-new-strategy>.py -j 8`
6. Re-run the screen so the leaderboard includes it.

**Keep the axes orthogonal.** If two options interact so strongly that one is
meaningless without the other, they belong on one axis as a single combined
option, not on two. The whole value of the design is that any assignment is
valid.

---

## Adding a new axis

Same as above, plus: add it to `AXES` in `tools/registry.py`, to `AXIS_ORDER` and
`AXIS_CAPTION` in `tools/leaderboard.py`, and to `AXES` in the analysis queries.
Every existing strategy will change name, so regenerate the library and expect
the database's historical `agents` rows to refer to names that no longer exist —
that is fine, `episodes` rows are immutable history.

---

## Running a tournament

Never on the login node.

```bash
# screen the whole library -- O(n), the only affordable shape at 1,728 strategies
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8 --label "screen-<what>"

# confirm the survivors -- O(n^2), exact
sbatch slurm/tournament.sh roundrobin --from-run latest --top 24 --seeds 24

# or an explicit roster
sbatch slurm/tournament.sh roundrobin --agents a.py b.py starter --seeds 20
```

Then always:

```bash
python tools/leaderboard.py --run latest     # docs/LEADERBOARD.md + site/
```

and record the run in `docs/RUNS.md` with one line saying what it was for.

**Choosing a panel.** The default anchors span the space deliberately: a strong
metered farm, a land-light farm, a flooder, a hoarder, a pure herd, and `starter`
as a floor. If the top of your screen saturates at 100% — as run #1 did — the
panel is too weak for that tier and the ordering among the leaders is arbitrary.
Fix it by adding a stronger anchor, not by trusting the order.

---

## Measuring anything

`docs/VALIDATING.md` is the long version. The short version:

- **Report intervals, not points.** `tools/eval.py` gives a Wilson interval on
  the win rate and a paired bootstrap on the money margin.
- **Swap seats.** Every harness here plays both; do not remove that.
- **Budget the sample.** 96 episodes resolves a 10-point edge, 384 a 5-point
  edge, 1,068 a 3-point edge. Anything smaller resolves nothing.
- **Never repeat a seed with the same pair.** Episodes are deterministic given
  `(seed, both agents)`; a repeat adds zero information.
- **Compare on balanced subsets.** Main effects across an unbalanced design are
  confounded, and the confound here reverses conclusions — see
  `docs/ROADMAP.md §11`, the section on why `dairy` looked better than
  `orchardherd`.
- **Check the mirror.** Run a candidate against itself. Scores roughly halve
  against a real opponent; if they more than halve, the agent depends on a
  passive opponent.

---

## The agent contract

Whatever you build must satisfy all of this, or it forfeits episodes:

- `main.py` at the archive root; the **agent function must be the last callable
  bound at module level** (`get_last_callable` takes `[-1]`). No `def`, `class`
  or `from x import f` after it.
- Wrap the whole policy in `try/except` returning `{"farmer": ["PASS"], "hands":
  [], "market": []}`. A crash loses the episode; a passed turn loses one turn.
- **1 second per turn** (`actTimeout`), plus a 60 s bank that only the *excess*
  over one second draws from. Reference: the current agent uses 0.246 ms.
- `hands` actions are positional — entry `i` maps to `farms[me]["hands"][i]`.
- Max 10 market orders per turn; extras are dropped silently.
- Module-level state persists for a whole episode (verified), so caching across
  turns is legitimate. Reset it when you see `step == 0`.

---

## Submitting

```bash
mkdir -p submissions/$(date +%F)-<name>
cp agents/<agent>.py submissions/$(date +%F)-<name>/main.py
cd submissions/$(date +%F)-<name>
kaggle competitions submit kaggriculture -f main.py -m "<what changed and why>"
kaggle competitions submissions kaggriculture
```

**Always snapshot the exact file submitted.** The ladder entry has to be
traceable back to source months later; the working tree will have moved on.

5 submissions per day, only the latest 2 stay active. Check remaining quota with
`kaggle competitions submission-limits kaggriculture`.

Then log it in `docs/RUNS.md` alongside the local result that motivated it, so
the local-vs-ladder correlation can be checked later.

**That correlation has since been measured, and it is weak.** `enhanced` beat
`barnyard` 384 out of 384 locally and drew level with it on the ladder (49% vs
47%); the whole `mgtight` family moved 623 → 857 while a third-party wrapped-plan
agent scored 1364 out of the box. Local rank is worth something *within* a level
and worth very little *across* levels -- which is what `docs/VALIDATING.md` §1
is about. Log the local number anyway; it is how that was found out.

**And before you submit, check what is currently active.** Deactivation is by
recency, not score, so in a shared repo a submission from someone who does not
know the current state drops the best agent. That has already cost a 1363.7 and
a 1287.2 in one night: `kaggle competitions submissions kaggriculture | head -5`.

---

## A generated agent is a pair of files, not one

`registry.py gen` writes `<strategy>.py` **and** `kg_rules.py` into the output
directory. The strategy holds the policy and its stamped `CONFIG`; `kg_rules.py`
is the game's rules mirrored from `reference/engine/kaggriculture.py` -- crop and
animal tables, the price model, the shop map -- and it holds no strategy and
reads no `CONFIG`.

That boundary is the one that pays. The engine has been rebalanced once
mid-competition and will be again, and when it is, `kg_rules.py` is the only
file that changes.

The pair travels together. `get_last_callable` puts the agent file's own
directory on `sys.path` before exec'ing it, so a flat sibling import resolves
both locally and inside Kaggle's `/kaggle_simulations/agent/`. To submit one:

```bash
bash tools/package.sh agents/lib/<strategy>.py mine
```

which stages the pair as `main.py` + `kg_rules.py` at the **archive root** -- a
nested directory would not import -- then unpacks its own archive, resolves
`get_last_callable`, and plays a full episode before handing you the tar.gz.

**Import explicitly, never `import *`.** Star-import skips underscore names. The
first attempt at this split used it, `_TO_FLOOR` and the private helpers went
missing, every agent raised inside its own `try/except` and returned `PASS`, and
nine strategies banked exactly the $3,000 they started with while the generator
reported success. `gen` now smoke-tests its first output -- resolves it the way
the framework will, calls it on a synthetic opening board, and refuses to finish
if it passes on turn 0 -- but the rule is cheaper than the check.

**Every plan may omit any axis it does not vary**; `complete()` fills the rest
from `REFERENCE`. Nine of the fourteen plans were silently dead for exactly this
reason -- they predated the seventh axis and raised `KeyError: 'adapt'`.

---

## Tests

There is one test file and it covers `tools/stats.py`:

```bash
python tests/test_stats.py
```

That is not an oversight waiting to be fixed everywhere. Most of this codebase
is I/O against Kaggle, SQLite and a 720-turn simulator, and it is checked by
harnesses that run the real thing -- `tools/stress.py` (28 pathological
configurations), `ghost.py verify`, `package.sh` (unpacks the archive, resolves
`get_last_callable`, plays a full episode), and `hybrid.py`'s `_verify`, which
exists because a spliced agent can compile, load, and silently run the *wrong*
function.

`stats.py` is different: it is pure, it has no dependencies, and a drift in it
would be invisible -- a wrong ranking looks exactly like a right one. **That is
the test to write for: something whose failure mode is a plausible number.**
If you add another pure module, give it a test file. If you add another Kaggle
or simulator wrapper, give it a verification step that runs the real thing
instead.

---

## What goes in the database, and what does not

`data/arena.sqlite` holds every episode ever run: result, status, shop draw,
final prices, and a ~1.6 KB **digest** per player.

It does **not** hold full replays — those are ~27 MB each and 3.4 million of them is
not a thing. If you need something that is not in the digest, extend `_digest()`
in `tools/tournament.py` and note that older rows will not have the new field.
The digest already carries final composition, per-product buy/sell totals, hire
order counts, and money/herd/hand curves at days 5/10/15/20/25/29.

Never edit `episodes` rows. They are history; a wrong number there poisons every
later analysis silently.

### The sync contract

`data/arena.sqlite` on the cluster is the **source of truth**. Cloudflare D1 is
the **published mirror**. Sync is **one-way, local to remote**, and it is a
separate step from running a tournament.

```
COMPUTE NODE                      LOGIN NODE                    ANYWHERE
(no outbound internet)            (has internet)

tournament.py                     tools/publish.sh --push       tools/d1.py query
    │  writes                         │  pushes                 tools/d1.py top
    ▼                                 ▼                         tools/d1.py mirror
data/arena.sqlite  ──────────────▶  D1 'kaggriculture'  ───────▶  a collaborator
  source of truth                    published mirror              needs no cluster
                                                                   account and no
                                     5 tables (size as of the       downloaded file
                                     last publish; `d1.py check`)
```

**Why the split is not negotiable.** Compute nodes have no outbound internet —
measured from inside a Slurm allocation, `curl https://api.cloudflare.com`
returns HTTP 000, while the login node connects fine. A tournament therefore
*cannot* write to D1 even if we wanted it to. `tools/publish.sh` warns if you run
it inside a job.

**Direction is one-way on purpose.** D1 is never authoritative: if the two
diverge, local wins and a re-push fixes it. `tools/d1.py mirror` reads D1 back
into a file, but that file is for querying, not for merging upward.

#### The four tiers, and how each moves

| tier | rows | transport | time |
|---|---|---|---|
| `agents`, `runs` | ~600 | query API, `INSERT OR REPLACE` | seconds |
| `ratings` | ~600 | same | seconds |
| `matchups` | thousands | same | ~2 min |
| `episodes` | millions (3.4M local) | **bulk import** (SQL → R2 → ingest) | seconds of ingest, upload dominates |

Row counts above are shapes, not facts — the local database is the source of
truth (`tools/datalake.py status`), and `tools/d1.py check` reports what the
mirror actually holds.

`matchups` is the pairwise aggregate — games, wins, median money per unordered
pair. It exists so a win matrix or a Bradley-Terry refit reads thousands of rows
instead of millions. Keep using it for anything that does not need per-episode detail.

Episodes must go through the bulk import endpoint. The same rows over the query
API are ~14,000 requests and about 50 minutes; the import endpoint ingests them
in 4 seconds.

#### Two D1 limits that will bite you

Both produced real failures here, and both are handled in `tools/d1.py`:

| limit | symptom | handling |
|---|---|---|
| bound parameters, capped well below SQLite | `too many SQL variables` at 900 params | `MAX_PARAMS = 90` |
| statement length | `statement too long: SQLITE_TOOBIG` on 200-row inserts (~280 KB) | dump caps statements at `MAX_STMT_BYTES = 60_000` |

A third trap: after a failed ingest, `init` with the **same etag** returns the
*previous* attempt's status rather than a fresh upload URL — so a retry appears
to succeed while reporting the old error. `_bulk_import` checks for that and
raises.

#### Commands

```bash
python tools/d1.py check                 # connectivity, sizes, row counts
python tools/d1.py schema                # once, to create the tables
python tools/d1.py push                  # meta + matchups, idempotent
python tools/d1.py push --episodes       # also episodes for runs D1 lacks
python tools/d1.py push --episodes --dry-run
python tools/d1.py query "SELECT ..."    # analysis, straight against D1
python tools/d1.py top -n 20
python tools/d1.py mirror local.sqlite   # materialise D1 into a file
```

`push --episodes` is **incremental**: it compares per-run episode counts against
D1 and imports only runs that differ, clearing a partial run on the remote first.
Re-running it when nothing changed prints `episodes: in sync` and does nothing.

Credentials come from a git-ignored `*.secret` in the project root:

```
ID:  <cloudflare account id>
API: <api token with D1 edit permission>
```

`chmod 600` it. The database id is discovered by name. `CF_ACCOUNT_ID` /
`CF_D1_DATABASE_ID` / `CF_API_TOKEN` override the file.

**Access control is on you.** This database is the entire measurement programme —
85,000 measured episodes and the evidence behind every claim in `docs/`. Anything
put in front of it (a Worker, a dashboard) must be authenticated. Kaggle's rules
also prohibit sharing outside your team.

### The file snapshot, as a fallback

D1 now carries every tier, so the compressed snapshots are a backup path rather
than the primary one. They remain the only offline-capable copy:

```bash
python tools/sync.py export            # dist/arena-meta.sqlite.xz    36 KB
python tools/sync.py export --full     # 本地传输用，不进 git（3.4M 局，几百 MB）
python tools/sync.py import <file>     # install as data/arena.sqlite
python tools/sync.py merge <file> --tag alice   # fold in someone else's runs
```

Neither snapshot belongs in git. xz-compressed SQLite cannot delta-compress: one
new row rewrites the whole stream, so git would store a full new blob each time.
Projected from the current growth rate (~316 rating rows per run):

| after | snapshot | git history if committed each run |
|---|---|---|
| 2 runs (now) | 36 KB | — |
| 50 runs | 547 KB | **27 MB** |
| 200 runs | 2.1 MB | **419 MB** |

**Git holds text; the mirror holds data.** `docs/LEADERBOARD.md` and
`docs/RUNS.md` are committed because they diff — `git log -p docs/LEADERBOARD.md`
reads as the history of what won.

#### Known limitations of the sync

Both are recorded rather than fixed; see the 《工具参考》 section of this file for the full list.

**Recomputed ratings for an existing run do not push.** The increment is decided
by whether D1 already holds a `run_id`. Recompute a run's ratings locally and the
new values are skipped, because the id has not changed. `push --force` is the
escape hatch, at the cost of rewriting all ~5,500 meta rows. A per-run content
checksum would be the proper fix.

**`--push` includes episodes, which is the expensive default.** The free tier
allows 100,000 row writes per day; a confirm run is ~28,900 and a library screen
~60,500. One screen fits in a day, two do not. If quota becomes the binding
constraint, drop to meta + `matchups` only:

| what | with episodes | matchups only |
|---|---|---|
| confirm run (38 strategies) | 28,862 rows | **703** |
| library screen (594) | 60,547 rows | **3,564** |

`matchups` already carries what a win matrix, a head-to-head record or a
Bradley-Terry refit needs. Only digest mining requires per-episode rows, and that
is occasional deep analysis rather than routine.

### The routine after a tournament

```bash
bash tools/publish.sh              # leaderboard + both snapshots
bash tools/publish.sh --push       # ... and upload (needs KG_REMOTE)

git add docs/LEADERBOARD.md docs/RUNS.md
git commit -m "tournament <label>: <one-line result>"
```

---

## Adding a dependency

`requirements/` is split by **how a package must be installed**, not by what it
is for — a flat `requirements.txt` cannot say "this one without its dependency
tree".

| File | Install command | Put a package here when |
|---|---|---|
| `base.txt` | `pip install -r requirements/base.txt` | it installs normally from PyPI |
| `nodeps.txt` | `pip install --no-deps -r requirements/nodeps.txt` | its declared dependencies are wrong, unbuildable, or enormous |
| `rl.txt` | cluster: `sbatch slurm/rl_setup.sh` (wheelhouse `--no-index`, inside a job); laptop: `pip install -r` | it belongs to the `rl/` training stack only |
| `lock.txt` | — generated | never edit; run `bash tools/bootstrap.sh --freeze` |

The RL stack deliberately stays out of `bootstrap.sh`: `torch~=2.10.0` is
pinned by the wheelhouse `tensordict`, weighs gigabytes, and nothing outside
`rl/` imports it. Install it with `sbatch slurm/rl_setup.sh` when you need it.

Then update `tools/bootstrap.sh` if the new package needs a platform-specific
path, and refresh the lock. Keep the comment in the requirements file explaining
*why* — `nodeps.txt` is 20 lines of comment for one package, and that is the
right ratio for a decision this surprising.

**Be conservative.** An agent has to run inside Kaggle's sandbox, where only what
the base image provides is available. Anything an agent imports at module level
must either be in that image or be vendored into the submission. Analysis-only
dependencies are unconstrained.

## Generated files — never hand-edit, never commit

| Path | Generated by | Regenerate with |
|---|---|---|
| `agents/lib/` | `agents/_engine.py` + `tools/registry.py` | `python tools/registry.py gen --plan all --out agents/lib` |
| `docs/LEADERBOARD.md`, `site/leaderboard.html` | `data/arena.sqlite` | `python tools/leaderboard.py --run latest` |
| `notebooks/baseline.ipynb` | an agent file | `python tools/build_notebook.py agents/<a>.py` |
| `agents/legacy/probes/`, `agents/legacy/adv/` | legacy generators | frozen; do not regenerate |
| `rl/runs/<run>/` (checkpoints, `plots/`), `rl/out/<name>/` | `rl/train.py`, `rl/export_agent.py`, `rl/plot_run.py` | re-run the training / export |

All of these are git-ignored or explicitly marked. If you find yourself editing
one, edit its source instead — otherwise the next regeneration silently reverts
your change.

`data/` and `.kaggle/` are git-ignored too: the database is ~7.5 GB — do NOT
casually copy it; share via `tools/sync.py` snapshots or query D1, and run
`tools/datalake.py status` before trusting `data/` is complete. Credentials
are per-person by design.

## Documentation

Keep results and their evidence together. When you measure something:

- Numbers that inform a decision go in `docs/ROADMAP.md §11` with the sample
  size and the slice they came from.
- **Negative results go in too.** `docs/ROADMAP.md §11.2` is the A/B ledger
  (landed and rejected both, with arm sizes): changes derived correctly from
  the rules still lost there, and a rejection made against a weak field is not
  a fact about the game. Check it before re-proposing an "obvious" improvement
  — several entries were exactly that, and measured worse.
- If a published claim turns out wrong, correct the document rather than adding
  a new one. There is one entry in `ROADMAP.md` §11 (`frontrun`) that exists
  purely to retract an earlier confounded result.

---

# 工具参考

> 原 `docs/CONTRIBUTING.md（工具参考）`，2026-08-14 并入这里。每个脚本做什么、以及它踩过的坑。

Every executable in this repo, what it does, and what it reads and writes.
`docs/ONBOARDING.md` is the narrative introduction; this is the inventory.

All of them resolve the project root themselves, so they run from any directory
once `setup_env.sh` has been sourced.

---

## Environment

### `tools/bootstrap.sh`
Builds `venv/` from scratch. Detects the platform via `$LMOD_CMD`/`$MODULESHOME`:
on the cluster it loads `module python/3.11.5` and takes numpy/pandas from the
Compute Canada wheelhouse; elsewhere it uses `python3` from `PATH` (override with
`PYTHON=`) and PyPI. Installs `kaggle-environments` with `--no-deps` on purpose
(see `requirements/nodeps.txt`), then verifies by running a real 48-step episode.

```bash
bash tools/bootstrap.sh            # create/recreate venv/
bash tools/bootstrap.sh --freeze   # only refresh requirements/lock.txt
```

### `setup_env.sh`
Sourced, never executed. Activates `venv/`, unsets the cluster's `PIP_PREFIX`,
and points `KAGGLE_CONFIG_DIR`, `KAGGLEHUB_CACHE`, `XDG_CACHE_HOME`,
`PIP_CACHE_DIR`, `HF_HOME` into the project directory so nothing touches `$HOME`.
Exports `KG_ROOT`. Skips the module load where Lmod is absent.

---

## Strategy definition

### `tools/registry.py`
The atom tables and the code generator. A strategy is one option from each of six
orthogonal axes; the name is the definition.

```bash
python tools/registry.py list                            # the whole space
python tools/registry.py gen --plan all --out agents/lib  # 1,728 strategies
python tools/registry.py gen --plan main                  # 26, one axis varied
```

| reads | writes |
|---|---|
| `agents/_engine.py` (template with a `CONFIG` marker block) | `agents/lib/*.py`, `agents/lib/manifest.json` |

Plans: `main`, `edge`, `produce`, `muck`, `grid`, `ladder`, `all` (1,728,
deduplicated union). The full seven-axis cross product is 241,920; counts
move with the option tables, so recheck with `registry.py list`.

### `agents/_engine.py`
Not an agent — the single execution path every generated strategy shares. Its
`CONFIG` block is replaced by the generator. Editing it changes every
generated strategy, so regenerate afterwards.

### `agents/barnyard.py`
The hand-written original (its 2026-08-07 ladder entry was `55332339`; the
ladder has long since moved on — see `docs/LADDER_STATE.md`). It now leads a
second life as the strongest tensor-native RL *training opponent*
(`rl/tensor_env/barnyard_t.py`, byte-exact against this file). Kept because it
is the only strategy not expressible as an atom composition, and because both
of those roles must stay traceable to this source.

---

## Running episodes

### `tools/tournament.py`
The main harness. Two shapes, because a full round robin over 1,728 strategies
would be ~1.5 million pairings.

```bash
# O(n): every strategy against a fixed six-anchor panel
python tools/tournament.py panel --lib agents/lib --seeds 8 -j 32

# O(n^2): every pair, for the survivors
python tools/tournament.py roundrobin --from-run latest --top 24 --seeds 24 -j 32
python tools/tournament.py roundrobin --agents a.py b.py starter --seeds 20 -j 8
```

| reads | writes |
|---|---|
| agent files, `agents/lib/manifest.json` | `data/arena.sqlite`: one `runs` row, one `episodes` row per game, one `ratings` row per agent |

Fits Bradley-Terry strengths at the end. Each episode stores a ~1.6 KB **digest**
per player: final composition, per-product buy/sell totals, hire order counts,
and money/herd/hand curves at days 5/10/15/20/25/29. Full replays (~27 MB each)
are deliberately not stored.

Throughput ~9.8 episodes/s on 32 cores, or ~12.3 with `KG_FAST_ENV=1`.

#### Where the time actually goes

An episode is ~3.2 s on one core, and **the strategy under test is only ~13% of
it**. Profiled: 42% is `deepcopy` of the whole game state (twice per step, once
per agent), ~12% is `jsonschema.validate` on every action, and the rest is
`structify`. It is the same thing that makes a stored replay 19 MB — the
framework re-materialises the entire board constantly.

`KG_FAST_ENV=1` drops the schema validation, which is the only part that is not
load-bearing: illegal actions are silent no-ops by design, so the interpreter
already ignores anything malformed. Measured over three seeds: **3.13 s → 2.61 s,
17% faster, byte-identical results.** The deepcopy is left alone — agents must
not share mutable state.

#### A trap: agents are keyed by filename

`short(path)` is the file's basename, so **two builds of the same strategy from
different directories collapse into one row** in `ratings` and in the
Bradley-Terry fit. `agents/lib/<strategy>.py` and `agents/lib/<strategy>.py` are one agent as
far as a run is concerned, and run #22 merged three of them without complaint.

Ablations therefore read their shard JSONL directly and key on the *directory*
(`"/final/" in path`), never on the ratings table. Only use `ingest` + `ratings`
when every roster entry has a distinct filename.

#### Sharding across a job array

```bash
sbatch --array=0-47 --cpus-per-task=32 --mem=40G --time=00:30:00 \
    slurm/tournament_array.sh panel --lib agents/factorial \
    --panel <anchors> --seeds 12 --label factorial-screen-960
python tools/tournament.py ingest --shards data/shards/factorial-screen-960
```

Each task runs `jobs[k::N]` — a **stride**, not a block, so no task collects all
the slow matchups — and writes one append-only JSONL file, renamed into place
only once complete. `ingest` is the single process that touches SQLite; it
deduplicates on `(left, right, seed)` so a requeued array task is harmless, and
warns loudly if the episode count is short.

**Array tasks must never open the database.** Forty-eight of them registering the
same manifest concurrently corrupted `data/arena.sqlite` on 2026-08-09 (recovered
in full; see `docs/RUNS.md`). `--shard` with `--from-run` is now a hard error for
that reason.

Scheduling, on this cluster: **short tasks start; long ones queue.** The same
work at `--time=03:00:00` and 64 cores per task sat behind a 78-minute priority
wait; at `--time=00:30:00` and 32 cores it started immediately across sixteen
nodes. 48 tasks × 32 cores = 1,536 cores turns a 47-minute tournament into
about 2 minutes.

### `tools/trace.py`
Day-by-day table for one episode: money, hands, land, tile composition, shed,
prices. **The most useful debugging tool here**, because illegal actions in this
engine are silent no-ops — bugs look exactly like bad strategy.

```bash
python tools/trace.py agents/barnyard.py starter
python tools/trace.py agents/barnyard.py starter -p 1 --seed 42
```

### `tools/stress.py`
28 pathological environment configurations: zero starting money, a 4x4 board, a
shed that holds one item, one turn per day, free hands, a market where every
product crashes. Not about realism — about finding hardcoded assumptions before
the ladder does. A crash forfeits an entire episode.

```bash
python tools/stress.py agents/barnyard.py -j 8
```

Reports status and worst turn duration per case. `barnyard` passes 28/28 with a
worst turn of 145 ms against the 1,000 ms budget.

### `tools/eval.py`
Statistically honest A/B. Plays both seats, reports a Wilson interval on the win
rate and a paired bootstrap on the money margin, and prints the sample size
needed when a result is not resolved.

```bash
python tools/eval.py h2h agents/lib/<candidate>.py agents/barnyard.py --seeds 96 -j 32
python tools/eval.py pool agents/lib/<candidate>.py agents/barnyard.py --vs starter --seeds 48
```

### `tools/ladder.py`
Pulls the episodes we played **on the ladder**, against real opponents, and keeps
only the digest. This is the only measurement in the project whose opponents were
not written by us; `docs/ROADMAP.md §11` is what it found.

```bash
python tools/ladder.py pull                    # all submissions
python tools/ladder.py pull --submission 55358912 --limit 40
python tools/ladder.py stats                   # what the real field builds
```

Each replay is **19 MB** and all of it is `steps`: the complete 10×10 board is
re-serialised for both players in every one of the 720 steps, 5.7 MB of tiles
alone, while the actions — the only part carrying information — come to 0.3 MB.
So every replay is downloaded, reduced to ~1.4 KB, written to `ladder_episodes`
in `data/arena.sqlite`, and deleted in a `finally` block. Measured over 94
episodes: **1.9 GB down to 125 KB**, a factor of 14,530.

Which seat was ours is *determined, not guessed*: `kaggle competitions logs <ep>
0` returns 403 for the opponent's agent, so one extra call per episode settles
it. Guessing would mirror every opponent statistic in the dataset.

Known limit: the `episodes` listing is truncated at roughly 37 rows per
submission, so a pull reaches the most recent episodes, not the full history.

### Removed: `arena.py`, `sweep.py`, `league.py`
Deleted 2026-08-12. All three were superseded by `tournament.py` (panel and
round robin, persisted to SQLite) and `eval.py` (A/B with an interval), and they
were the main source of duplication in the repo -- five different `_play`
implementations lived across them. Their results predate `data/arena.sqlite` and
are transcribed into `docs/RUNS.md`, which is where published numbers
citing them should point. `slurm/league.sh` and `slurm/sweep.sh` went with them.

### `tools/db.py`
Schema and queries over `data/arena.sqlite`. Four tables: `agents`, `runs`,
`episodes`, `ratings`.

```bash
python tools/db.py init
python tools/db.py stats                 # what has ever been run
python tools/db.py top --run latest -n 40
python tools/db.py sql "SELECT ..."
```

`db.close(con)` checkpoints WAL and closes. Use it — a writer that exits without
a checkpoint once left a 0-byte database that had reported success
(`docs/RUNS.md`, data integrity incidents).

### `tools/leaderboard.py`
Renders the database into a leaderboard: a markdown table for git and a
self-contained HTML page for publishing. Also computes atom main effects.

```bash
python tools/leaderboard.py --run latest --top 40
```

| reads | writes |
|---|---|
| `data/arena.sqlite` | `docs/LEADERBOARD.md`, `site/leaderboard.html` |

The HTML renders each strategy name as six fixed-position cells so a reader can
scan a column and see what the leaders share.

### `tools/d1.py`
Syncs to the Cloudflare D1 mirror. One-way, local to remote. Full details in
`docs/CONTRIBUTING.md` "The sync contract".

```bash
python tools/d1.py check                 # connectivity, size, row counts
python tools/d1.py schema                # once
python tools/d1.py push                  # meta + matchups, incremental
python tools/d1.py push --episodes       # also episodes for runs D1 lacks
python tools/d1.py push --force          # rewrite rows D1 already has
python tools/d1.py query "SELECT ..."
python tools/d1.py top -n 20
python tools/d1.py mirror local.sqlite   # materialise D1 back into a file
```

Credentials from a git-ignored `*.secret`; the database id is discovered by name.
Episodes move through D1's bulk import endpoint, not the query API.

### `tools/sync.py`
Compressed file snapshots, as the offline fallback to D1.

```bash
python tools/sync.py export              # dist/arena-meta.sqlite.xz    36 KB
python tools/sync.py export --full       # 本地传输用，不进 git（3.4M 局，几百 MB）
python tools/sync.py import <file>       # install as data/arena.sqlite
python tools/sync.py merge <file> --tag alice --into other.sqlite
python tools/sync.py push / pull         # via a Kaggle dataset (KG_REMOTE)
```

`merge` remaps run ids, because they are per-database `AUTOINCREMENT`, and skips
runs already present by label and episode count.

### `tools/publish.sh`
The routine after a tournament. Regenerates the leaderboard, exports snapshots,
and optionally syncs.

```bash
bash tools/publish.sh                    # leaderboard + snapshots, no network
bash tools/publish.sh --push             # ... and sync to D1 (+ Kaggle if set)
```

Warns if run inside a Slurm job: compute nodes have no outbound internet, so any
push from one fails.

### `tools/build_notebook.py`
Generates `notebooks/baseline.ipynb` from an agent file, so the notebook and the
submitted code cannot drift.

```bash
python tools/build_notebook.py agents/barnyard.py notebooks/baseline.ipynb
```

### `tools/hybrid.py`
Splices a recorded 720-turn opening onto a generated agent at a chosen day, so
"how much of the season is decided in the opening" can be measured instead of
argued.

```bash
python tools/hybrid.py <agent>.py --open agents/ref/closer_cleo.py \
    --days 0,4,8,12,16,20,24,28 [--adopt] --out agents/hybrid
```

`--adopt` raises the engine's crop, herd and hand targets to the board it
inherits at handover. Without it the targets are absolute counts, so an engine
configured for 16 strawberry handed a board carrying 41 never replants one and
the farm decays 55 -> 12 plants — which measures our target ceiling, not the
opening.

Two silent-failure traps are guarded, because both were hit while writing it and
neither raises: `get_last_callable` returns the **last callable value in the
module dict**, so `_INNER = agent` and a helper `def` after `agent` both make the
framework load the wrong function and every handover day then scores identically.
The generated file parks callables in lists and `del`s the helper name, and every
file is verified after writing — the framework must resolve `agent`, step 0 must
come from the recording, and the handover step must not.

Output goes to `agents/hybrid/` (git-ignored). **These are instruments, not
submissions** — see `docs/ROADMAP.md` §5.3 for why a copy of the public line
cannot rank above the crowd that already runs it.

### `tools/kaggle_cli.py` and `tools/board.py`
The two things every analysis tool here was reimplementing.

`kaggle_cli.py` -- `dataset_files(slug)` follows `Next Page Token` to the end
(the daily dumps run to hundreds of files and the CLI pages, so a single call
silently returns a prefix), and `dataset_file(slug, name, dest)` downloads one,
unpacking the `.zip` some CLI versions hand back instead. `ghost.py` and
`topeps.py` each had a byte-identical copy of the listing under a different name
(`_listing` and `_files`), so a fix to one would never have reached the other.

`board.py` -- `survey(farm)` counts crops, animals, structures, weeds and empty
tiles out of an observation; `ready(farm)` sums unharvested produce. Four tools
had their own copy of that nested loop, differing only in whether they truncated
names for display, which is presentation rather than measurement.

Both are deliberately thin. `kaggle_cli` shells out to the same commands a human
would type, because that is the only interface here with a stable contract and
because a failure then looks like something you can paste and rerun.

### `tools/stats.py`
The two estimators every ranking here depends on, and the only pure module in
the repo: `bradley_terry`, `wilson`, `resolved`, `elo`. No database, no
filesystem, no network.

It exists because `bradley_terry` lived in both `league.py` and
`tournament.py` and the copies had already drifted on their convergence settings
(1,000 iterations at 1e-10 against 2,000 at 1e-11). They agreed to 1.7e-10 on a
twelve-agent case so nothing published was wrong -- but the estimator behind
every number in `docs/` should not exist twice, because a fix to one would not
reach the other.

`tests/test_stats.py` covers it: transitivity, a tied field, fractional wins
from ties, the empty case, and a rock-paper-scissors cycle collapsing to equal
strengths -- which is the numerical form of "any ranking is a ranking against
its field".

```bash
python tests/test_stats.py
```

### `tools/topeps.py`
Digests Kaggle's daily dumps of the highest-scoring episodes -- games between
players rated ~3,100 that we are never matched into.

```bash
python tools/topeps.py index      # what dumps exist
python tools/topeps.py pull       # digest them into the database
python tools/topeps.py stats
```

The digest carries the **action histogram** -- `move_frac`, `pass_frac`,
`work_frac`, `steps_per_work`, `zero_move_frac` -- because that is where the
difference lives, not in the farm layout.

### `tools/ghost.py`
Turns those trajectories into local opponents.

```bash
python tools/ghost.py make --limit 60 --per-team 2 --bands
python tools/ghost.py balance
python tools/ghost.py verify --limit 12
```

A ghost is 11 KB: one player's recorded 720-turn action sequence, gzip+base85
encoded, replayed by step index. Nothing is fitted. Sampling is stratified on
purpose -- at most two per team, score bands filled evenly, round-robin across
days -- because a naive pull gave 12% of the field to one team and drew every
episode from the same hour. `verify` measures how much of its original score
each ghost still reaches before the set is trusted.

**They are open-loop and they degrade off their recorded seed**: different
weeds turn their actions into silent no-ops. That is a feature for an opponent
and a trap for anything else -- see `docs/ROADMAP.md` §4.

### `tools/fetch_fields.sh`
Rebuilds every opponent field a fresh clone does not have. **Run it before your
first measurement**; `agents/` is git-ignored in full.

```bash
bash tools/fetch_fields.sh            # ref agents, ghosts, lines, bench3
bash tools/fetch_fields.sh ghosts 60  # just ghosts
```

### `tools/package.sh`
Builds the tar.gz Kaggle expects, with every module at the **archive root**

```bash
bash tools/package.sh agents/lib/<strategy>.py mine    # a generated strategy
bash tools/package.sh agents/enhanced enhanced         # a directory
```

Given a single generated strategy it stages the pair (`main.py` + `kg_rules.py`)
itself, so submitting one is one command and nobody has to remember that the
rules travel with the policy. Everything ends up at the archive root -- Kaggle unpacks into `/kaggle_simulations/agent/`, so a
nested directory breaks the imports. It ships `*.py` **and `*.npz`** — an RL
export is `main.py + weights.npz + kg_rl_* modules` (`rl/export_agent.py`), and
a tar without the weights would PASS every turn. Verifies by unpacking, checking
`get_last_callable` resolves to `agent`, and running a full episode. Single-file
agents do not need it; submit the `.py` directly.

### `tools/fieldtable.py`
Reprints README's three opponent tables — the fields on disk, the standings in
`agents/wrapped/`, and every submission with its ladder score — in the README's
own markdown, so refreshing them is a paste rather than an edit.

```bash
python tools/fieldtable.py
```

It exists because those tables go stale silently: a field gets rebuilt, plans
get re-mined, submissions accumulate, and a table nobody can cheaply regenerate
becomes fiction that reads like fact.

### `tools/wrap.py`
Puts the same adaptive layer around each mined plan, so a round robin compares
plans instead of wrappers.

```bash
python tools/wrap.py --top 100 --out agents/wrapped
```

Without this, a field of bare recordings against one wrapped agent measures the
wrapper. That mistake produced a "92.4%, beats all twelve" reading for an agent
that sits 64th of 101 once every entrant carries the same layer.

The transplant is safe because the parts of the donor wrapper that depend on its
own plan are already dead: `_SUPPLY` is read only by `_reserve_price`, which is
only called for items in `_RESERVE`, and `_RESERVE` is empty. Each emitted file
is verified by loading it the way the framework will and checking that step 0
matches the plan.

### `tools/tracelib.py`
Mines the daily top-episode dumps into a library of the **distinct plans** the
ladder actually plays.

```bash
python tools/tracelib.py import dist/tracelib.json.xz   # 371 plans, no Kaggle key needed
python tools/tracelib.py stats
python tools/tracelib.py emit --out agents/lines --top 12 --min-score 50000
python tools/tracelib.py verify --dates 2026-08-11      # replays must be exact

python tools/tracelib.py pull --dates 2026-08-07,2026-08-08 --per-date 200 -j 8
python tools/tracelib.py export --out dist/tracelib.json.xz
```

**The library is not in `data/arena.sqlite` and is not mirrored to D1.** The
database holds episodes and ratings; this is an index of *plans*, a different
kind of object, and it is the expensive part to rebuild -- about an hour of
rate-limited pulling. So it travels as a committed 3 MB file, the way the
database travels via `tools/sync.py`. `import` merges rather than replaces:
a plan already held keeps its best season and accumulates team sightings.

Deduplication is the whole job: 959 episodes gave 1,894 trajectories and 201
distinct plans, a ratio of 9:1. Every comparison sweeps shifts of +-8 turns
first, because two farms running the same plan one turn apart agree on nothing
index to index. The replay is deleted as soon as it is digested -- 29 MB in,
~11 KB out -- so disk never holds more than `-j` of them.

It refuses dates before the 1.32.6 rebalance (2026-08-06/07) on purpose: town
demand halved and shop draws became with-replacement, so a plan tuned before it
is playing a different game.

**Three things this cost, all worth knowing before touching the Kaggle API:**

* **`"429" in output` is not a rate-limit check.** Episode files are named after
  their ids, so `91804729.json` matches it and a healthy 11 KB listing gets
  discarded. Forty minutes of "backing off" here were a working API being
  thrown away once every two minutes. Match `429 Client Error` *and* require
  that the command produced nothing.
* **A retry storm keeps itself locked out.** 151 retries eight seconds apart
  never recovered; a single probe the moment they stopped succeeded instantly.
  Every retry refreshes the limit that is blocking it. `-j 8` and few requests
  beat `-j 64` and many, by a wide margin -- at 48 the download failure rate was
  80%, at 64 the account was 429'd for minutes.
* **`steps[i]["action"]` produced `steps[i]["observation"]`,** so a replay must
  return `_TURNS[i + 1]` at step i. Off by one, an open-loop plan makes every
  decision against the previous turn's board -- and it is invisible, because the
  shifted replay still produces a plausible season. `verify` used to report a
  ghost reaching 114% of its original score and that was read as success. The
  bar is now `tracelib verify`: both sides of a real episode reproduced **to the
  dollar**, plus an identical shop sequence.
* **The seed is in `info["seed"]`,** not in the first observation. Reading the
  wrong place gives `None` for every episode and an open-loop trace without its
  seed cannot be replayed on the board it was recorded on, which is most of its
  value. A whole 959-episode pull had to be redone.

### `tools/lines.py`
Clusters `agents/ghosts/` into the distinct *lines* the ladder actually plays,
and writes one representative per cluster.

```bash
python tools/lines.py                      # report
python tools/lines.py --emit agents/lines  # write line1.py ... line4.py
```

Alignment is the whole trick: two farms playing the same plan one turn apart
agree on **nothing** compared index to index, so the comparison sweeps shifts of
+-8 turns. Without it, 156 recordings look like 156 distinct strategies.

156 trajectories collapse to 25 lines at 85% agreement, the largest holding 97 of
them across 38 teams. Only 8 of the 156 match the plan embedded in `agents/ref/`,
so **the line this repo spent its measurements against is played by about 5% of
the top**. And the most-played line is not the strongest: cluster 1's median
original score is $78,510 against cluster 2's $132,032.

Replayed on seeds they never saw, cluster 1 holds 66.6% while cluster 2 collapses
to 11.8% and cluster 3 to 0.9% — these are open-loop recordings, and different
weeds turn their actions into silent no-ops. The most-played line is the most
*robust* one. `line1.py` is in `agents/bench3` for exactly that reason: it is the
only opponent we have between "we win 90%" and "we lose 99.8%".

### `tools/make_probes.py`
Regenerates the legacy single-strategy probes in `agents/legacy/probes/`.
Superseded by `registry.py`; kept because published results name them.

---

## Slurm wrappers

Thin scripts that source the environment and call the corresponding tool.
The tournament/eval path is CPU-only; the ONE exception to "never request a
GPU" is `rl/` training — the batched tensor engine is real GPU work
(rationale: `rl/tensor_env/DESIGN.md` §5). Evaluation always runs the CPU
reference engine.

| script | wraps | resources |
|---|---|---|
| `slurm/tournament.sh` | `tools/tournament.py` | 32 cpus, 48 G, 6 h |
| `slurm/tournament_array.sh` | sharded tournaments (JSONL out, ingest after) | array x 32 cpus, 30 min |
| `slurm/eval.sh` | `tools/eval.py` | 32 cpus, 32 G, 2 h |
| `slurm/rl_setup.sh` | install `requirements/rl.txt` into the venv | 4 cpus, 15 min |
| `slurm/rl_train.sh` | `rl/train.py` -- chainable ~50-min links via `--resume` | **GPU h100:1**, 8 cpus, 55 min |
| `slurm/rl_ab.sh` | hand-written vs TorchRL A/B arms | **GPU h100:1**, 8 cpus |
| `slurm/rl_bc.sh` | `rl/bc/` collect + clone + sanity | 32 cpus, CPU |
| `slurm/rl_eval.sh` | export + ten-opponent roster + plots | 32 cpus, CPU |

```bash
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8
sbatch slurm/rl_train.sh --config rl/configs/<preset>.yaml \
    --save rl/runs/<run>/latest.pt --resume rl/runs/<run>/latest.pt
```

---

## Data flow

```
tools/registry.py + agents/_engine.py
        │  gen
        ▼
agents/lib/*.py ──────┐
agents/barnyard.py ───┤
                      │  sbatch slurm/tournament.sh
                      ▼
              data/arena.sqlite  (source of truth, cluster only)
                      │
      ┌───────────────┼──────────────────┬─────────────────┐
      │ leaderboard.py│ d1.py push       │ sync.py export  │ db.py sql
      ▼               ▼                  ▼                 ▼
docs/LEADERBOARD.md   D1 'kaggriculture' dist/*.xz      ad-hoc analysis
site/leaderboard.html (published mirror) (offline copy)
      │                     │
      └─ git                └─ collaborators query directly
```

The RL line runs beside this, meeting it at eval/packaging:

```
reference/engine --byte-exact--> rl/tensor_env/ --> rl/train.py (TorchRL)
                                                        │
                                              rl/runs/<run>/ (ckpt + plots/)
                                                        │  rl/export_agent.py
                                                        ▼
                       tools/eval.py <-- main.py + weights.npz --> tools/package.sh
```

---

## Known limitations

Recorded rather than fixed, because each is a real edge case that has not yet
bitten and the fix would be speculative.

**Recomputed ratings for an existing run do not push.** `d1.py push` decides what
to send by asking whether D1 already holds a given `run_id`. If a run's `ratings`
are recomputed locally — a corrected Bradley-Terry fit, say — the new values are
skipped because the run id is unchanged. The escape hatch is `push --force`,
which rewrites all ~5,500 meta rows and costs that much write quota. A content
checksum per run would be the proper fix.

**`publish.sh --push` includes episodes by default.** That is 28,000–57,000 row
writes per tournament, against a free-tier budget of 100,000 per day. One full
library screen fits; two do not. If quota becomes the constraint, the cheap mode
is meta + `matchups` only — 703 rows for a confirm run, 3,564 for a screen, a
17–41x reduction — because `matchups` already carries everything a win matrix or
a BT refit needs. Only digest mining requires per-episode rows.

**Panel screens can saturate.** When the top of a panel run all go undefeated,
Bradley-Terry strength diverges and their relative order is arbitrary. Run #1 did
this with eight strategies tied. The fix is a stronger anchor in the panel, not
trusting the order; the confirm round robin exists for exactly this.

**The legacy harnesses wrote JSON, not the database.** `league.py`, `sweep.py`
and `arena.py` predated `data/arena.sqlite` and are now deleted. Their results
are transcribed into
`docs/RUNS.md` but the raw dumps are not queryable alongside everything else.
Prefer `tournament.py` for anything new.

---

## 分支与协作

- **main 是唯一的集成分支。** RL 线的两条实验分支（`rl-baseline`、`tensorize`）
  已于 2026-08-18 合并进 main 并继续在 main 上演进；不要基于它们开新工作。
- **想法要署名。** 采纳协作者的设计时，移植提交带
  `Co-authored-by: <名字> <邮箱>`（先例：Kilo 的前瞻记账势函数与逐单位多头，
  两者的移植提交都带署名进了 main）。
- **长期分叉的个人分支自己负责 rebase。** `new-branch` 与 main 已大幅分叉
  （main 上的 `rl/` 统一层覆盖了它重复实现的引擎）；往 main 送东西请以
  main 的 `rl/` 结构为准。
- **提交信息讲"为什么"**，度量类改动附样本量；引擎/训练语义的改动必须先过
  对应的验收门（`rl/tensor_env/test_*.py`）再合。

---

# 在 Vulcan 集群上跑（可选）

> 原 `docs/CONTRIBUTING.md（集群）`，2026-08-14 并入这里。**这一节只对能访问 Vulcan 的人有用；
> 其余所有内容都不假设你有集群。**

**这份文档只对能访问 Vulcan 的人有用。其他所有文档都不假设你有集群。**

这个项目在普通笔记本上功能完整 —— 同样的工具、同样的数据库、同样的结论。集群唯一
带来的是**吞吐量**：一次全库筛选在笔记本上要几小时，在这里是几分钟。如果你没有集群
账号，跳过这份文档，按 `docs/VALIDATING.md` 里给出的局数在本地跑，只是慢一些。

一个换算，方便你判断需不需要：**每核每秒约 0.375 局**（带 `KG_FAST_ENV=1`）。

| 你想跑 | 8 核笔记本 | 512 核集群 |
|---|---|---|
| 一次 A/B（每臂 384 局） | 约 4 分钟 | 4 秒 |
| 一次形状扫描（约 7 万局） | 约 6.5 小时 | 3 分钟 |
| 一次引擎消融（约 14 万局） | 约 13 小时 | 6 分钟 |

**前两行在笔记本上是完全可行的。** 只有第三行真正需要集群。

---

## 基本规则

- **永远不要在登录节点跑重活。** 一局（约 2.7 秒）可以，锦标赛不行。
- **锦标赛/评估负载是纯 CPU 的 —— 不要为它申请 GPU**：单线程 Python，42% 的时间
  花在框架内部的 `deepcopy` 上。**唯一的例外是 `rl/` 训练**（批量张量引擎，
  `slurm/rl_train.sh` / `rl_ab.sh`，h100:1）；评估永远跑 CPU 参考引擎。
- **短任务立刻开跑，长任务排队。** 同样的工作量在 `--time=03:00:00` 加每任务 64 核下
  排了 78 分钟；在 `--time=00:30:00` 加 32 核下，十六个节点上立即开始。
- **`$SCRATCH` 不备份**，60 天不活动会被清理（年龄取 `min(atime, ctime)`）。
  仓库放在 `$SCRATCH` 下，但把 `data/arena.sqlite` 拷一份到 `~/projects/`。

## 分片跑大规模锦标赛

```bash
sbatch --array=0-15 --cpus-per-task=32 --mem=40G --time=00:30:00 \
    slurm/tournament_array.sh panel \
    --agents agents/mine/*.py --panel agents/bench3/*.py \
    --seeds 96 --jobs 32 --label mylabel

squeue -u $USER
python tools/tournament.py ingest --shards data/shards/mylabel
```

每个 array 任务跑作业列表的一个**跨步切片**（`jobs[k::N]`，不是分块 —— 相邻的作业是
同一对手在相邻种子上，分块会把所有慢的对局塞给同一个任务），并写一个只追加的 JSONL
分片。

**array 任务绝对不能打开 `data/arena.sqlite`。** 48 个任务并发注册 manifest 曾经把它
写坏过一次（全量恢复了，见 `docs/RUNS.md` 的数据完整性事故）。分片写 JSONL，由**一个**
`ingest` 进程做全部写入。`--shard` 和 `--from-run` 同时出现是硬错误。

`KG_FAST_ENV=1` 跳过 jsonschema 校验，实测结果逐字节相同，快 17%。`slurm/` 下的脚本
已经帮你设好了。

## 交互式调试

```bash
salloc --account=aip-zhouyang --time=02:00:00 --cpus-per-task=16 --mem=32G
```

拿到节点后可以直接跑代码。长时间的交互式会话建议配合 `tmux`，SSH 断线会杀掉 `salloc`。

## 环境

`bash tools/bootstrap.sh` 会自己检测集群并 `module load python/3.11.5`，`numpy`/`pandas`
从 Compute Canada 的 wheelhouse 取。在笔记本上同一个脚本走 PyPI。**两边环境等价**，
所以在笔记本上验证过的东西在集群上跑出来是一样的。

## 给没有集群的协作者

你缺的只是速度，不是能力。三条实用建议：

1. **用 `tools/eval.py h2h` 而不是全场地面板。** 96 个种子的两两对比在 8 核上约一分钟，
   足以分辨 10 分的差距。
2. **拿别人跑好的数据库，不要自己重挣。**
   `python tools/sync.py import dist/arena-meta.sqlite.xz` —— 那是几小时的算力压成
   几 MB。或者用 `tools/d1.py` 直接查远端镜像，连文件都不用下。
3. **分片格式是通用的。** 如果有人在集群上帮你跑了一批，你拿到 `data/shards/<label>/`
   下的 JSONL 就能自己分析，`docs/VALIDATING.md` §5 有现成的代码。
