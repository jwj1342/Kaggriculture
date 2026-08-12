# What is written where

Which file to open for a given question, and which document explains it. Every
claim in the docs traces to a run in `data/arena.sqlite`; every behaviour in the
docs traces to a line in `agents/_engine.py`.

Start at `README.md`, then `docs/ONBOARDING.md`. This page is the index for
everything after that.

---

## By question

| If you want to know… | Read | Which is produced by |
|---|---|---|
| what the game actually rewards | `docs/GAME_ECONOMICS.md` | `reference/engine/kaggriculture.py` |
| what real opponents do, and why our own field misled us | `docs/LADDER_FIELD.md` | `tools/ladder.py` → `ladder_episodes` |
| how to measure against the **top** of the ladder locally | `docs/GHOSTS.md` | `tools/topeps.py`, `tools/ghost.py` |
| **how much of the season the opening decides** | `docs/ROADMAP.md` §3 D | `tools/hybrid.py` → `data/shards/handover*` |
| every change made to the agent and what it measured | `docs/ENGINE_CHANGES.md` | shard JSONL under `data/shards/` |
| **is my agent actually better** | `docs/VALIDATING.md` | `tools/fetch_fields.sh`, `slurm/tournament_array.sh` |
| how to produce a number that survives scrutiny | `docs/EVALUATION.md` | — |
| **why the score jumped from 838 to 1364** | `docs/ROADMAP.md` §5 | `tools/hybrid.py`, `tools/lines.py` |
| which distinct plans the ladder actually plays | `docs/ROADMAP.md` §3 | `tools/lines.py` |
| what each atom option is worth | `docs/ATOM_EFFECTS.md` *(superseded in part)* | runs #1–#2 |
| the atom taxonomy and boundary cases | `docs/STRATEGY_LIBRARY.md` | `tools/registry.py` |
| provenance for any single number | `docs/RUNS.md` | `runs` table |
| what every script does | `docs/TOOLS.md` | — |
| conventions, and how to submit | `docs/CONTRIBUTING.md` | — |
| **running on the Vulcan cluster** *(optional -- skip if you have no account)* | `docs/CLUSTER.md` | `slurm/*.sh` |
| the current ranking | `docs/LEADERBOARD.md` *(generated)* | `tools/leaderboard.py` |

---

## By source file

### `agents/_engine.py` — the single execution path

Every generated strategy is this file with a different `CONFIG` block, so a
change here moves the whole library. The behaviours worth knowing, and where
each is justified:

| Region | Behaviour | Justified in |
|---|---|---|
| `CONFIG` block | replaced by the generator; never hand-edit | `docs/STRATEGY_LIBRARY.md` |
| `_TO_FLOOR` | units to drive each product to the $1 floor, computed once | `docs/GAME_ECONOMICS.md` §market |
| `_town_drain` | what the town removes per step, given the shop draw | `docs/LADDER_FIELD.md` §2 |
| `shopwise` herd re-weighting | herd follows the shop draw, not the plan | `docs/ENGINE_CHANGES.md` §6 |
| `feed_reserve` / `feed_solvent` | one number for buyer, gate and seller | `docs/ENGINE_CHANGES.md` §1 |
| hiring `want_hands` | hire to the work, not to the plan | `docs/ENGINE_CHANGES.md` §5 |
| the *here-pass* | work the tile you are standing on | `docs/ENGINE_CHANGES.md` §3 |
| `held_tiles` | reserve a tile's remaining work for that unit | `docs/ENGINE_CHANGES.md` §4 |
| ongoing-crop watering | alternate days, except on production ticks | `docs/ENGINE_CHANGES.md` §2 |
| `FERTILIZE` scheduling | only on watered tiles, within a tick's reach | `docs/ENGINE_CHANGES.md` §2–3 |
| fertilizer price gate | stop collecting below $30 | `docs/ENGINE_CHANGES.md` §4 |
| `LIQUIDATE_DAY = 29` | the last day of the season | `docs/ENGINE_CHANGES.md` |
| the assignment loop | greedy, task-picks-unit — **eleven alternatives lost** | `docs/ENGINE_CHANGES.md` §rejections |

### `tools/registry.py` — what a strategy *is*

Seven orthogonal axes; the name is the definition. Composition plans:

| Plan | Materialises | Used for |
|---|---|---|
| `all` | the deduplicated union | the standing library |
| `bench` | the **standard reference field** | `--panel` in screens, fixed opponents in ablations |
| `ladder` | opponents reconstructed from real replays | keeping the field honest |
| `factorial` | produce × land × muck × market, balanced | main effects that are not confounded |
| `crop`, `refine`, `labour`, `recheck` | one-axis sweeps around the incumbent | re-measuring after an engine change |

**Regenerate `bench` whenever a candidate beats it above ~90%.** It has saturated
twice; a reference that loses to everything ranks nothing.

### `tools/tournament.py` — how a number is produced

`panel` is O(n) screening, `roundrobin` is O(n²) confirmation, `ingest` folds
shard JSONL into one run. Array tasks never touch SQLite.

**Ablations read shard JSONL directly and key on the directory**, because
`short(path)` is the basename and two builds of the same strategy from different
directories merge silently into one row.

### `tools/topeps.py` and `tools/ghost.py` — the top of the ladder, locally

`topeps.py` digests Kaggle's daily dumps of the highest-scoring episodes — games
between players rated ~3,100 that we will never be matched into. Its digest
carries the **action histogram**, because that is where the difference lives:
they work 40.6% of their actions and spend 1.09 movement actions per action that
works; we were at 21-27% and 1.85.

`ghost.py` turns those trajectories into opponents. A ghost is 11 KB — the
recorded action sequence of one player, replayed on the seed and seat it played.
Nothing is fitted. `verify` measures how much of its original score it still
reaches (median 114%) before the set is trusted.

Our win rate: **96% against our own field, 42% against ghosts, 50-58% on the
ladder.** The ghost number is the one that tracks reality.

### `tools/ladder.py` — the opponents matched to *our* rating

Pulls our own ladder episodes, keeps a ~1.4 KB digest, deletes the 19 MB replay.
The seat is *determined* by the 403 on the opponent's logs, never guessed.

Two things it found that nothing else could: the melon trap
(`docs/LADDER_FIELD.md` §2) and the action histogram that produced the largest
single change in the project (`docs/ENGINE_CHANGES.md` §3).

---

## What a fresh clone does not have

Two opponent fields are git-ignored — one is third-party code, the other is 150+
generated files — and **both are load-bearing**. A bench without them measures
our own family against itself, which is the mistake that cost this project a
week.

```bash
bash tools/fetch_fields.sh            # both
bash tools/fetch_fields.sh ghosts 60  # just ghosts, 60 of them
```

| directory | what | why it is not committed |
|---|---|---|
| `agents/ref/` | the public teaching ladder, tiers 0–9; tiers 6–9 replay the shared meta line | third-party (MIT + a NOTICE with a real scope carve-out); one command to fetch |
| `agents/ghosts/` | 11 KB opponents replaying top-player trajectories | reconstructible from public replay data; ~90 s each to build |
| `agents/bench3/` | the standard reference field | generated: `registry.py gen --plan bench`, plus the tier 4–9 agents |

## The measurement chain

```
reference/engine/kaggriculture.py     ground truth, re-diffed after upgrades
            │
            ▼
tools/registry.py  +  agents/_engine.py
            │  gen --plan <name> --out agents/<dir>
            ▼
agents/<dir>/*.py                     one file per strategy, submittable as-is
            │  sbatch slurm/tournament_array.sh   (48 x 32 cores)
            ▼
data/shards/<label>/shard-NNN.jsonl   append-only, one file per array task
            │  tournament.py ingest              (single writer)
            ▼
data/arena.sqlite                     32 runs, 1,228,544 episodes, 184 real
            │
            ├── tools/leaderboard.py  → docs/LEADERBOARD.md, site/
            └── ad-hoc queries        → docs/ENGINE_CHANGES.md, docs/RUNS.md
```

The ladder loop runs alongside it and is what corrects the local one:

```
kaggle submit  →  ~10 episodes/hour  →  tools/ladder.py pull
                                              │
                                              ▼
                                     ladder_episodes (digests)
                                              │
                     ┌────────────────────────┴─────────────────┐
                     ▼                                          ▼
        reconstruct opponents into                  read the action histogram
        tools/registry.py `ladder` plan             from one full replay
                     │                                          │
                     └──────────────► docs/LADDER_FIELD.md ◄────┘
```

---

## Three traps this repo has fallen into

Each is recorded where it bites, and each cost real work:

1. **A saturated reference field ranks nothing.** When every candidate beats the
   anchors 97-100%, 99.2% and 100.0% are the same measurement. Rebuild `bench`.
   → `docs/EVALUATION.md`
2. **Four seeds point the wrong way.** Four separate changes read positive over
   four seeds and were 21-44 points behind over 2,304 episodes an arm. A smoke
   test is a syntax check. → `docs/EVALUATION.md`
3. **Agents are keyed by filename.** Two builds of the same strategy from
   different directories merge into one row and one Bradley-Terry node.
   → `docs/TOOLS.md`

And the one that shaped everything else: **a ranking against a field we wrote is
not evidence about the ladder.** → `docs/LADDER_FIELD.md`
