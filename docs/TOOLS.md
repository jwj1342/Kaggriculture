# Tool reference

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
python tools/registry.py gen --plan all --out agents/lib  # 594 strategies
python tools/registry.py gen --plan main                  # 26, one axis varied
```

| reads | writes |
|---|---|
| `agents/_engine.py` (template with a `CONFIG` marker block) | `agents/lib/*.py`, `agents/lib/manifest.json` |

Plans: `main` (26), `edge` (8 corners), `produce` (72), `muck` (30),
`grid` (512), `all` (594, deduplicated union). Full cross product is 9,216.

### `agents/_engine.py`
Not an agent — the single execution path every generated strategy shares. Its
`CONFIG` block is replaced by the generator. Editing it changes all 594
strategies, so regenerate afterwards.

### `agents/barnyard.py`
The hand-written original, and the agent currently on the ladder (submission
`55332339`). Kept because it is the only strategy not expressible as an atom
composition, and because the ladder entry must stay traceable.

---

## Running episodes

### `tools/tournament.py`
The main harness. Two shapes, because a full round robin over 594 strategies
would be 176,121 pairings.

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
not written by us; `docs/LADDER_FIELD.md` is what it found.

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
are transcribed into `docs/EVALUATION.md` §7, which is where published numbers
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
python tools/sync.py export --full       # dist/arena-full.sqlite.xz   4.6 MB
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
nested directory breaks the imports. Verifies by unpacking, checking
`get_last_callable` resolves to `agent`, and running a full episode. Single-file
agents do not need it; submit the `.py` directly.

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

Thin scripts that source the environment, set `OMP_NUM_THREADS=1`, and call the
corresponding tool with `-j $SLURM_CPUS_PER_TASK`. All CPU-only — never request
a GPU.

| script | wraps | default resources |
|---|---|---|
| `slurm/tournament.sh` | `tools/tournament.py` | 32 cpus, 48 G, 6 h |
| `slurm/eval.sh` | `tools/eval.py` | 32 cpus, 32 G, 2 h |

```bash
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8
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
