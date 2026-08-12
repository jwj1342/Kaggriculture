# Onboarding — your first hour

For someone joining this repo cold. Follow it top to bottom; it takes about an
hour and ends with you having run a real tournament and read a real result.

---

## 0. What this project is, in five sentences

Kaggriculture is a Kaggle **simulation** competition: you submit a *program*, not
predictions, and it plays 720-turn farming seasons head-to-head against other
people's programs. The prize is ten equal $5,000 places, so the target is **top
10**, not first. Ranking is win/loss only — the coin margin never enters — and
the final leaderboard is a single Bradley-Terry fit over the last two weeks of
episodes.

This repo holds a **composable strategy library** (594 generated agents from six
orthogonal atoms), a **local tournament system** that has run 85,064 episodes into
SQLite, and the analysis derived from it. One agent is live on the ladder.

---

## 1. Set up (10 minutes)

**This project runs on the Vulcan cluster and on an ordinary laptop.** Everything
except Slurm works identically; `bootstrap.sh` and `setup_env.sh` detect which
one they are on.

You need Python 3.9+ (3.11 matches the cluster and Kaggle's own runtime) and
your own Kaggle API credentials.

```bash
git clone <repo> Kaggriculture      # on the cluster, put it under $SCRATCH
cd Kaggriculture

bash tools/bootstrap.sh             # builds venv/, verifies with a real episode
```

On the cluster this loads `module python/3.11.5` and takes `numpy`/`pandas` from
the Compute Canada wheelhouse. On a laptop it uses whatever `python3` is on
`PATH` (override with `PYTHON=/path/to/python3.11`) and installs everything from
PyPI. Same environment either way.

Then put **your own** Kaggle credentials in `.kaggle/`:

```bash
# either of these works; get them from https://www.kaggle.com/settings/api
printf '{"username":"YOU","key":"..."}' > .kaggle/kaggle.json
echo 'KGAT_...'                             > .kaggle/access_token
chmod 600 .kaggle/*
```

They stay in this directory — `setup_env.sh` points `KAGGLE_CONFIG_DIR` here, so
copies under `$HOME` are never used, deliberately.

```bash
source setup_env.sh                         # every session, from anywhere
kaggle competitions list -s kaggriculture   # confirms auth works

python tools/registry.py gen --plan all --out agents/lib   # 594 strategies
```

`agents/lib/` is **generated and git-ignored** — 594 files derived from
`agents/_engine.py` plus `tools/registry.py`. Regenerate it rather than editing
it, and regenerate after touching either source.

`data/arena.sqlite` (136 MB, 85,064 episodes) is also git-ignored, because it is
too large for git and is regenerable. Copy it rather than re-earning it — it
represents about three hours of 32-core compute:

```bash
# whoever has it exports a snapshot -- 4.6 MB, not 136 MB
python tools/sync.py export --full        # -> dist/arena-full.sqlite.xz

# you install it
python tools/sync.py import dist/arena-full.sqlite.xz

# or just the rankings, 36 KB, if you only want to read results
python tools/sync.py export               # -> dist/arena-meta.sqlite.xz
```

Without it every tool still works; `tools/db.py` creates an empty database and
you start accumulating your own runs.

**Or skip the file entirely.** Every tier is mirrored to Cloudflare D1, so with
the `*.secret` credentials you can query all 85,064 episodes directly:

```bash
python tools/d1.py check
python tools/d1.py top -n 20
python tools/d1.py query "SELECT json_extract(a.atoms,'\$.labour') labour,
    COUNT(*) n, ROUND(AVG(r.winrate)*100,1) winpct
  FROM ratings r JOIN agents a ON a.name=r.agent
  WHERE r.run_id=1 GROUP BY labour ORDER BY winpct DESC"
python tools/d1.py mirror local.sqlite    # or pull it down as a file
```

**Why bootstrap exists rather than a plain `pip install -r`:** `kaggle-environments`
declares `open_spiel`, which builds from source and fails on this cluster. It is
installed `--no-deps` on purpose, with `numpy`/`pandas` taken from the Compute
Canada wheelhouse. Import errors for *other* environments (`lux_ai_s3`, `halite`,
`open_spiel_env`) print to stderr and are expected.

---

## 2. Run one episode and look at it (10 minutes)

```bash
python tools/trace.py agents/barnyard.py starter
```

You get a day-by-day table: money, hands, land, tile composition, shed contents,
market prices. **This is the most important tool in the repo.** Illegal actions
in this engine are *silent no-ops* — no error, no cost — so bugs look exactly
like bad strategy. Every five-figure bug found here was found by reading a trace,
never by staring at a final score.

Then check the agent survives abuse:

```bash
python tools/stress.py agents/barnyard.py -j 8
```

28 pathological configurations (zero money, a 4×4 board, a shed that holds one
item, one turn per day, free hands). A crash forfeits an entire episode, so this
runs before anything else.

---

## 3. Understand the naming (5 minutes)

A strategy's name **is** its definition — six atoms, always in the same order:

```
land - labour - produce - market - intel - muck

estate-crew-mixedfarm-metered-blind-muck
  │      │        │        │       │     └ collect the free daily fertilizer
  │      │        │        │       └ ignore the opponent
  │      │        │        └ hold sales below a price floor
  │      │        └ melon + strawberry + wheat + cows + sheep + geese
  │      └ up to 11 hands/day, ≤6% of cash on payroll
  └ three of the four 5×5 quadrants
```

**No version numbers, ever.** Two identical configurations cannot end up with
different names, and a name tells you what the agent does without opening it.

```bash
python tools/registry.py list          # the whole atom space
ls agents/lib | head                   # the generated library
```

`agents/barnyard.py` is the one hand-written exception: the original agent, still
the one on the ladder. `agents/legacy/` holds superseded ad-hoc agents, kept
because published results cite them; its README maps old names onto atoms.

---

## 4. Run a tournament (20 minutes)

**On the cluster** — never on the login node. One episode (~2.7 s) is fine; a
tournament is not.

```bash
sbatch slurm/tournament.sh roundrobin \
    --agents agents/barnyard.py agents/lib/homestead-crew-orchardherd-flood-blind-muck.py starter \
    --seeds 24 --label "my-first-run"

squeue -u $USER                    # wait for it
tail -f logs/tourney-<jobid>.out
```

**On a laptop** — the same runner, called directly, sized to your cores:

```bash
python tools/tournament.py roundrobin \
    --agents agents/barnyard.py agents/lib/homestead-crew-orchardherd-flood-blind-muck.py starter \
    --seeds 8 --label "my-first-run" -j $(python -c 'import os;print(os.cpu_count())')
```

Budget realistically: one episode is ~2.7 s of one core. Eight cores give ~3
episodes/s, so the three-agent run above (48 episodes) takes under a minute, but
the full 594-strategy screen (57,000 episodes) would take about five hours.
Screening the whole library is a cluster job; everything else is comfortable
locally.

Every episode lands in `data/arena.sqlite`. Then:

```bash
python tools/db.py stats                    # what has been run, ever
python tools/db.py top --run latest         # the ranking
python tools/leaderboard.py --run latest    # regenerates docs/LEADERBOARD.md + site/
```

Throughput reference: ~9.8 episodes/s on 32 cores, so **~35,000 episodes/hour**.
A properly powered A/B (384 episodes) costs about 40 seconds of a compute node.

---

## 5. Read the knowledge, in this order (25 minutes)

If you have been away for more than a few days, **start with `docs/ROADMAP.md`**
— it is written for exactly that case and opens with what turned out to be wrong.

1. `docs/ROADMAP.md` — where this went and why, with the arm size on every claim
2. `docs/VALIDATING.md` — how to tell whether your change is real. Two fields for
   two levels; using the wrong one wastes the run
3. `docs/GAME_ECONOMICS.md` — what the game actually rewards
4. `docs/ENGINE_CHANGES.md` — seven landed, five rejected, all with arm sizes
5. `docs/LADDER_FIELD.md` — why a field we wrote ourselves misled us for a week
6. `docs/SUBMISSION_POLICY.md` — before you touch the ladder
7. `docs/EVALUATION.md` — the long form of §2 above

`docs/MAP.md` routes any other question to the document that answers it.

## 6. Five things that will bite you

These are not hypotheticals; each one has already cost real work here.

**Illegal actions fail silently.** No exception, no log, no cost. Wrong tile,
empty inventory, full shed — all just no-ops. Always trace.

**`FEED` takes wheat from the acting unit's inventory, not the shed.** And
`PICKUP` only works on the four tiles beside the shed. Without explicitly routing
hands back for feed, every unit stays busy watering and the entire herd starves.
That single bug cost ~45k.

**Seed-to-seed spread exceeds most tuning effects.** Early 3–4 seed sweeps in
this repo produced *contradictory orderings on repeat runs*. The floor for a
believable result is a few hundred episodes; see EVALUATION §5 for the table.

**Common random numbers do not control this environment.** `_end_of_day` draws
weeds and the shop unlock from one shared RNG, and weed draws scale with how many
empty tiles *both* farms have — so changing your agent changes which shops
unlock. Pairing on seed helps but cancels nothing.

**The strategy space is non-transitive.** A measured rock-paper-scissors cycle
exists: flood beats metered beats spite beats flood. Any ranking is a ranking
*against its field*, and swapping the field reorders it. Two honest tournaments
in this repo disagree for exactly this reason.

---

## 7. Where things stand

- `agents/barnyard.py` is live on the ladder (submission `55332339`), currently
  ~623 rating. It ranks **14th of 38** in the local confirm tournament — beaten
  by every `orchardherd` composition by ~21,000 median money.
- 5 submissions per day; only the latest 2 stay active.
- The highest-value open work is in `docs/IMPROVEMENTS.md`, and the single
  clearest defect is the opening starvation described in `docs/ATOM_EFFECTS.md`.
- **Nothing measured locally has been validated against the real ladder yet.**
  Every local opponent is one we wrote, so a systematic bias is entirely
  possible. Spending one submission to test whether local rank predicts ladder
  rank is probably the best next experiment.

---

## 8. Cluster etiquette

Vulcan's login node is shared. One episode is fine; anything larger goes through
Slurm. This workload is CPU-only — **never request a GPU**.

```bash
sbatch slurm/tournament.sh ...     # 32 cores, the default for real runs
salloc --account=aip-zhouyang --time=02:00:00 --cpus-per-task=16 --mem=32G
```

`$SCRATCH` is 5 TB, **not backed up**, and purged after 60 days of inactivity
(age = `min(atime, ctime)`). `data/arena.sqlite` is the one irreplaceable file
here — copy it to `~/projects/` if it matters to you.
