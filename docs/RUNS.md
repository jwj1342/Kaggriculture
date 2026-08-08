# Run log

Provenance for every experiment that produced a number cited anywhere in this
repo. Append a row when you run something; the point is that a claim can always
be traced back to the episodes behind it.

Everything from run #1 onward lives in `data/arena.sqlite` and can be re-queried:

```bash
python tools/db.py stats
python tools/db.py top --run 2 -n 40
sqlite3 data/arena.sqlite "SELECT * FROM runs"
```

---

## Tournaments in the database

| Run | Label | Shape | Agents | Episodes | Slurm | Finished | Headline |
|---|---|---|---|---|---|---|---|
| **#1** | `library-screen-594` | panel, 6 anchors, 8 seeds, both seats | 594 | 56,944 | 409573 | 2026-08-07 22:29 | `orchardherd` compositions sweep the top; `swarm` and `nomuck` are catastrophic |
| **#2** | `confirm-38-representative` | round robin, 20 seeds, both seats | 38 | 28,120 | 410822 | 2026-08-07 23:21 | `homestead-crew-orchardherd-flood-*` ranks 1–4; `barnyard` ranks 14th |
| **#5** | `enhanced-vs-field` | round robin, 20 seeds, both seats | 36 | 25,200 | 420380 | 2026-08-08 | first cut of the enhanced baseline ranks **8th**; diagnosis below |
| **#6** | `enhanced-fixed-vs-field` | round robin, 20 seeds, both seats | 32 | ~19,800 | 421206 | 2026-08-08 | after the herd-deadlock and land fixes |

**85,064 episodes total.** Database is 136 MB.

Run #1's roster is the whole `all` plan from `tools/registry.py`. Run #2's roster
is run #1's top 8, the best carrier of every atom option, all eight boundary
corners, plus `barnyard` and `starter`.

---

## Earlier experiments (JSON in `logs/`, pre-database)

These predate the SQLite store. Kept because published conclusions cite them.

| What | Scale | Output | Headline |
|---|---|---|---|
| Tunable league | 8 agents × 24 seeds × 2 seats = 1,344 eps | `logs/league_v1.json` | `HAND_CAP=11` beats the then-default 14; `TARGET_COWS=10` confirmed |
| Probe league | 21 agents × 16 seeds × 2 seats = 6,720 eps | `logs/league_probes.json` | `one_quadrant` 1st, `dump_all` 2nd *above* `barnyard`, `product_only` last on $78 |
| Adversary league | 8 agents × 24 seeds × 2 seats = 1,344 eps | `logs/league_adv.json` | pure denial (`parasite`) went 0/168 and made opponents *richer* |
| A/B: `dump_all` vs `barnyard` | 192 seeds × 2 seats = 384 eps | `logs/eval_dump.json` | 71.4% win, CI [66.6%, 75.6%], while earning ~25% less |
| A/B: `one_quadrant` vs `barnyard` | 192 seeds × 2 seats = 384 eps | `logs/eval_1q.json` | 93.2% win, CI [90.3%, 95.3%], earning *more* |
| A/B: `enhanced` vs field leader | 384 eps | `logs/eval_enh_vs_top.json` | **75.8% win**, CI [71.3%, 79.8%], margin +3,016 |
| A/B: `enhanced` vs `barnyard` | 384 eps | `logs/eval_enh_vs_barn.json` | **100% win** (384/384), margin +25,753 |
| Quadrant sweep | 4 configs × 8 seeds | — | 1→49,078 · 2→68,738 · 3→68,892 · 4→68,892 |
| Crop-scale sweep | 6 configs × 8 seeds | — | scaling the crop plan up is monotonically worse |
| Stress suite | 28 pathological configs | — | `barnyard` 28/28 clean, worst turn 145 ms |

Grand total including these: **~95,000 episodes**.

---

## Submissions

| Date | Submission | Agent | Snapshot | Local evidence | Ladder |
|---|---|---|---|---|---|
| 2026-08-07 | `55332339` | `barnyard` | `submissions/2026-08-07-barnyard/` | ~67k median vs `starter`; 28/28 stress | validation passed; 600 → 634.7 |
| 2026-08-08 | `55358912` | `enhanced` (tar.gz, 5 modules) | `submissions/2026-08-08-enhanced/` | 100% vs `barnyard` and 75.8% vs the field leader, both over 384 episodes; 28/28 stress | pending at time of writing |

*(A third row, `55348834 rl_models.zip`, appears on the submissions page with
status ERROR. It was not produced by this repo.)*

**The local-versus-ladder correlation is unmeasured.** Every local opponent is one
we wrote, so a systematic bias is possible. Adding a second submission chosen by
local rank — and seeing whether the ladder agrees — is the cheapest way to find
out whether any of this transfers.

---

## Reproducing a run

Tournaments are deterministic given `(seed, both agents)`, so a run reproduces
exactly if the agent files have not changed. `agents/lib/manifest.json` records a
source hash per strategy; the `agents` table stores it too.

```bash
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8 --label "screen-repro"
python tools/db.py top --run latest
```

If numbers differ from the table above with the same seeds, the engine version
changed — check `pip show kaggle-environments` against 1.32.6 and re-diff
`reference/engine/kaggriculture.py`.

---

## Data integrity incidents

**2026-08-08 — duplicate runs written by a test, removed.** A test of
`tools/sync.py merge` intended to write into a scratch database wrote into
`data/arena.sqlite` instead, adding runs #3 and #4 as exact copies of #1 and #2
(85,064 → 170,128 episodes). Both were deleted and the database vacuumed; runs
#1 and #2 were never modified and all counts are back to 85,064 / 633 / 594.

Two real bugs caused it, both now fixed:

* `db.connect(path=DB_PATH)` bound its default **at import time**, so reassigning
  `DB.DB_PATH` had no effect on where writes went — while log messages happily
  reported the new path. `connect()` now resolves `DB_PATH` at call time, and
  `sync.py merge` takes an explicit `--into`.
* `cmd_merge` never closed its connection. In WAL mode that left the committed
  rows in the `-wal` file, producing a **0-byte database that had just reported a
  successful merge**. Writers now checkpoint and close via `db.close()`.

A third bug surfaced during the cleanup: `cmd_merge` passed `atoms` to
`register_agents` as the JSON string it had read, and `register_agents`
`json.dumps()` whatever it is handed — so all 594 agent rows ended up
double-encoded, and `tools/leaderboard.py` crashed on the next run. Fixed at the
source and all 594 rows repaired.

The lesson worth keeping: a path reported in a log is not evidence of the path
written to. The round-trip test in the scratchpad exists because of this, and it
is what caught all three.

## Diagnosis: why the first enhanced cut ranked 8th

Run #5 put the first version of the enhanced baseline 8th of 36 — comfortably
ahead of `barnyard` (15th) but behind all seven `homestead-crew-orchardherd-*`
variants. Comparing digests across the same tournament made the cause obvious:

| | enhanced (first cut) | field leader |
|---|---|---|
| quadrants owned | 2 | **1** |
| animals at the end | **9** | 15 |
| idle tiles | **32** | 7 |
| wool sold | 30 | 48 |

Two independent defects:

**The herd deadlocked at nine.** `feed_solvent` required
`shed_wheat >= (n+1) * FEED_DAYS_REQUIRED`, but the reserve it was checking
against is capped at `WHEAT_RESERVE_CAP = 28`. At nine animals the requirement is
30 — unreachable — so no tenth animal could ever be bought. Two constants that
had to agree, and did not.

**Two quadrants were worse than one, for this agent.** With 18 pens and 12 melon
tiles planned against 50 tiles, 32 sat idle while the hands walked further. The
leader used 18 of 25. Land does not add production; it spreads the same labour.

Both fixed, and the result reverses: 75.8% against that same leader over 384
episodes, and 13–15 animals with 7 idle tiles instead of 9 and 32.

## Known caveats attached to these numbers

- **Run #1's top tier is saturated.** Eight strategies went undefeated against
  the panel, so Bradley-Terry diverges and their relative order is arbitrary.
  That is what run #2 exists to resolve.
- **Runs #1 and #2 disagree on atom effects** — `ranchmix` goes from second-best
  to worst, `frontrun` from marginal to top. Both are honest; they measure
  different fields. The strategy space is non-transitive
  (`docs/ADVERSARIAL.md`).
- **Main effects in `docs/LEADERBOARD.md` are unbalanced** by construction, because
  the composition plans do not sample the axes evenly. The balanced versions are
  in `docs/ATOM_EFFECTS.md` and they reverse some orderings.
- **The pre-database leagues used ad-hoc agent generators** (`agents/legacy/`)
  that had bugs the library engine later fixed. Treat their absolute numbers as
  indicative and their comparisons as valid only within a league.
