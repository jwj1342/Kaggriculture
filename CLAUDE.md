# Kaggriculture — project rules

Kaggle simulation competition on the Vulcan cluster. `README.md` orients,
`docs/ONBOARDING.md` is the full first hour. This file is the short list of
things that are easy to get wrong.

## Environment

`source setup_env.sh` before anything — it resolves its own location, so it works
from any directory and for any user. If `venv/` is missing, run
`bash tools/bootstrap.sh` first.

Both scripts work on the cluster **and on a personal machine** — they detect Lmod
and skip `module load` where it does not exist. Collaborators are not all on
Vulcan; do not add cluster-only assumptions to anything outside `slurm/`.

Dependencies are in `requirements/`, split by install semantics:
`base.txt` (normal), `nodeps.txt` (`--no-deps`), `lock.txt` (generated audit
snapshot, cluster-specific). `kaggle-environments` is `--no-deps` on purpose —
its 19 declared dependencies include `open_spiel`, which fails to build; only
three are actually needed. Import errors for *other* environments (`lux_ai_s3`,
`halite`, `open_spiel_env`) print to stderr and are expected.

## Ground truth

`reference/engine/kaggriculture.py` is a copy of the file the episodes import.
**Trust it over the competition overview page**, which describes pre-1.32.6
balance. Re-diff it against the installed package after every upgrade — the
balance has already changed once mid-competition.

## Naming

**No version numbers.** A strategy is `land-labour-produce-market-intel-muck`;
the name is the definition. Hand-written agents get a semantic name
(`barnyard.py`). Submission snapshots are `submissions/<date>-<agent>/`.

Do not hand-write strategy files — add an atom option in `tools/registry.py` and
regenerate. Keep the axes orthogonal.

## Agent contract

- `main.py` is loaded with `get_last_callable`: the agent function must be the
  **last callable bound at module level**. No `def`, `class` or
  `from x import f` after it.
- 1 second per turn (`actTimeout`); only the excess draws on the 60 s bank.
- Wrap the policy in `try/except` returning `PASS`. A crash forfeits the episode.
- `hands` actions are positional — entry `i` maps to `farms[me]["hands"][i]`.
- Max 10 market orders per turn; extras are dropped silently.
- **Illegal actions are silent no-ops** — no error, no cost. Bugs look exactly
  like bad strategy. Use `tools/trace.py`.

## Measurement

`docs/EVALUATION.md` is mandatory reading before producing a number.

- Seed-to-seed spread exceeds most tuning effects; 3–4 seed sweeps here produced
  contradictory orderings on repeat runs. 96 episodes resolves a 10-point edge,
  384 a 5-point edge.
- Episodes are deterministic given `(seed, both agents)` — repeating a pair on a
  seed adds nothing.
- Common random numbers do **not** control this environment: weeds and the shop
  unlock share one RNG, and weed draws scale with both farms' empty tiles.
- Compare on **balanced subsets**. Unbalanced main effects reversed conclusions
  here at least once.
- The strategy space is **non-transitive**. Any ranking is against its field.
- Always check the mirror match; scores roughly halve against a real opponent.
- **A ranking against a field we wrote is not evidence about the ladder.**
  `enhanced` beat `barnyard` 384/384 locally and is level with it on the ladder
  (49% vs 47%). Include `agents/spar/` and cross-check with
  `python tools/ladder.py stats`.
- **Watch rank against money.** When a strategy ranks below one it out-earns,
  the ranking has stopped tracking what the competition scores — that was the
  first visible symptom of the engine bugs run #7 fixed.
- **Submit at most once per half-day.** Only the latest two submissions are
  active and the ladder plays ~10 episodes/hour, so a burst of submissions
  leaves every agent with 4–12 games: too few to rank, and too few to diagnose.
  `docs/RUNS.md` has the numbers.
- **Engine changes get an A/B, not an argument.** Four of seven derived from the
  rules correctly and still lost. `docs/ENGINE_CHANGES.md` records all seven with
  arm sizes; three of the losers assumed the farm was alone on the board.

## Cluster

Never run heavy work on the login node. One episode (~2.7 s) is fine; tournaments
go through Slurm. CPU-only — **never request a GPU**; the workload is
single-threaded Python and 42% of it is `deepcopy` inside the framework.

Shard anything big: `sbatch --array=0-47 --cpus-per-task=32 --mem=40G
--time=00:30:00 slurm/tournament_array.sh ...` then
`python tools/tournament.py ingest --shards data/shards/<label>`. 1,536 cores
turns a 47-minute tournament into two minutes. Set `KG_FAST_ENV=1` — it skips
jsonschema validation for a verified-identical 17%.

**Short tasks start; long ones queue.** The same work at `--time=03:00:00` with
64 cores a task waited 78 minutes on priority; at `--time=00:30:00` with 32 it
started immediately across sixteen nodes.

**Array tasks must never open `data/arena.sqlite`.** Forty-eight of them
registering a manifest concurrently corrupted it (recovered in full — see
`docs/RUNS.md`). Shards write JSONL; one `ingest` process does all the writing.
`KG_DB` redirects every writer at once, for tests.

## Structure

`tools/registry.py` (atoms) + `agents/_engine.py` -> `agents/lib/` (generated)
-> `tools/tournament.py` -> `data/arena.sqlite` -> `tools/leaderboard.py` ->
`docs/LEADERBOARD.md` + `site/leaderboard.html`. README "How it fits together"
has the diagram.

`agents/spar/` is the same generator on the `ladder` plan: opponents
reconstructed from real ladder replays. Keep it in every field — before it
existed, every measurement here was against strategies we wrote ourselves, and
`docs/LADDER_FIELD.md` is what that cost.

Generated, never hand-edit: `agents/lib/`, `agents/spar/`, `docs/LEADERBOARD.md`,
`site/leaderboard.html`, `notebooks/baseline.ipynb`. All of these plus `venv/`,
`.cache/`, `.kaggle/` and `data/` are git-ignored.

## Data

`data/arena.sqlite` holds every episode ever run and is the one irreplaceable
file here. Never edit `episodes` rows; they are history. Digests are ~1.6 KB per
player — full replays (~27 MB each) are deliberately not stored.

## Multi-file agents

`tools/package.sh <dir> <name>` builds the tar.gz, with every module at the
**archive root** — Kaggle unpacks into `/kaggle_simulations/agent/`, so a nested
directory breaks the imports. It verifies by unpacking, checking
`get_last_callable` resolves to `agent`, and running a full episode.

## Submissions

5 per day, only the latest 2 active. Snapshot the exact submitted file under
`submissions/<date>-<name>/` and log it in `docs/RUNS.md` with the local result
that motivated it. `notebooks/baseline.ipynb` is **generated** by
`tools/build_notebook.py` — edit the agent, not the notebook.
