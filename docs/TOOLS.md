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

Throughput ~9.8 episodes/s on 32 cores.

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
python tools/eval.py h2h agents/v2.py agents/barnyard.py --seeds 96 -j 32
python tools/eval.py pool agents/v2.py agents/barnyard.py --vs starter --seeds 48
```

### `tools/arena.py`, `tools/sweep.py`, `tools/league.py`
Earlier single-purpose harnesses, superseded by `tournament.py` and `eval.py` but
kept because published results cite them. `arena.py` is a quick head-to-head,
`sweep.py` a coordinate sweep over module-level tunables, `league.py` a
round robin with its own JSON output rather than the database.

---

## Evidence and publishing

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
| `slurm/league.sh` | `tools/league.py` | 32 cpus, 32 G, 3 h |
| `slurm/sweep.sh` | `tools/sweep.py` | 32 cpus, 48 G, 3 h |

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

**Legacy harnesses write JSON, not the database.** `league.py`, `sweep.py` and
`arena.py` predate `data/arena.sqlite`. Their results are transcribed into
`docs/RUNS.md` but the raw dumps are not queryable alongside everything else.
Prefer `tournament.py` for anything new.
