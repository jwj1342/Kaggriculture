# Contributing

Conventions and workflows. Read `docs/ONBOARDING.md` first if you have not set up
the environment yet.

---

## Naming

**A strategy's name is its definition.** Six atoms, fixed order, hyphen-joined:

```
land-labour-produce-market-intel-muck
```

There are **no version numbers anywhere in this repo**. `v1`, `v2`, `final2` and
friends carry no information, drift out of sync with what they label, and make
two identical configurations look different. If you need to talk about a point on
the grid by a shorter name, add an alias in `ALIASES` in `tools/registry.py` —
aliases are decoration on top of the real name, never a replacement.

Other naming rules in force:

| Thing | Convention | Example |
|---|---|---|
| Generated strategy | atom composition | `estate-crew-mixedfarm-metered-blind-muck` |
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
   `PRODUCE`, `MARKET`, `INTEL`, `MUCK`). The value is a dict of `CONFIG` keys.
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
# screen the whole library -- O(n), the only affordable shape at 594 strategies
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

`docs/EVALUATION.md` is the long version. The short version:

- **Report intervals, not points.** `tools/eval.py` gives a Wilson interval on
  the win rate and a paired bootstrap on the money margin.
- **Swap seats.** Every harness here plays both; do not remove that.
- **Budget the sample.** 96 episodes resolves a 10-point edge, 384 a 5-point
  edge, 1,068 a 3-point edge. Anything smaller resolves nothing.
- **Never repeat a seed with the same pair.** Episodes are deterministic given
  `(seed, both agents)`; a repeat adds zero information.
- **Compare on balanced subsets.** Main effects across an unbalanced design are
  confounded, and the confound here reverses conclusions — see
  `docs/ATOM_EFFECTS.md`, the section on why `dairy` looked better than
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

It does **not** hold full replays — those are ~27 MB each and 85,000 of them is
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
                                     113 MB, 5 tables              downloaded file
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
| `matchups` | 4,252 | same | ~2 min |
| `episodes` | 85,064 | **bulk import** (SQL → R2 → ingest) | 4 s ingest, upload dominates |

`matchups` is the pairwise aggregate — games, wins, median money per unordered
pair. It exists so a win matrix or a Bradley-Terry refit reads 4,252 rows instead
of 85,064. Keep using it for anything that does not need per-episode detail.

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

Both are recorded rather than fixed; see `docs/TOOLS.md` for the full list.

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
| `lock.txt` | — generated | never edit; run `bash tools/bootstrap.sh --freeze` |

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

All of these are git-ignored or explicitly marked. If you find yourself editing
one, edit its source instead — otherwise the next regeneration silently reverts
your change.

`data/` and `.kaggle/` are git-ignored too: the database is 136 MB (copy it
between checkouts, see ONBOARDING §1) and credentials are per-person by design.

## Documentation

Keep results and their evidence together. When you measure something:

- Numbers that inform a decision go in `docs/ATOM_EFFECTS.md` with the sample
  size and the slice they came from.
- **Negative results go in too.** `docs/ENGINE_CHANGES.md` has a
  *Measured and rejected* section and a *Measured and confirmed* one, and both
  earn their place: seventeen changes derived correctly from the rules still
  lost, and a rejection made against a weak field is not a fact about the game.
  already been shown not to work. Two entries there were "obvious" improvements
  that measured worse.
- If a published claim turns out wrong, correct the document rather than adding
  a new one. There is one entry in `ATOM_EFFECTS.md` (`frontrun`) that exists
  purely to retract an earlier confounded result.
