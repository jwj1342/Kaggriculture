# Ghosts: measuring against the top of the ladder, locally

Every agent in `agents/lib` shares one execution path. A tournament between them
measures which *configuration* of that path is best and **can never measure the
path itself** — which is why this project spent a week believing melon was the
best crop and 28 strawberry tiles the right number, and why our own field says
96% about an agent the ladder says 50% about.

A **ghost** is not a strategy and nothing about it is fitted. It is the recorded
action sequence of a player rated ~3,100, replayed turn by turn.

```bash
python tools/topeps.py index                       # which days Kaggle published
python tools/ghost.py  make --date 2026-08-09 --limit 48
python tools/ghost.py  verify --limit 12           # do they still score?
python tools/tournament.py ghosts --agents <candidate.py> --label <name>
```

---

## Where they come from

Kaggle publishes a dataset per day containing that day's highest-scoring
episodes, and an index of the days:

| dataset | contents |
|---|---|
| `kaggle/kaggriculture-episodes-index` | 625 bytes, one row per day, with the top and median participant rating |
| `kaggle/kaggriculture-episodes-<date>` | ~690 full replays, one JSON each, ~32 MB apiece |

The 2026-08-09 dump averages **3,068 to 3,218** across its participants. We were
at 790. **These are games we will never be matched into** — the ladder pairs on
rating — and until now there was no way to learn from them.

Individual files can be fetched with `kaggle datasets download <slug> -f <name>`,
so nothing is stored: download one 32 MB replay, keep 11 KB, delete.

## What a ghost is made of

The action sequence for the **stronger** side of the episode, gzipped and
base64'd into a standalone agent module. 720 turns of two players is 0.24 MB of
JSON; one player compresses to **11 KB**.

`configuration.seed` is scrubbed from the replay so agents cannot read it, but
`info.seed` survives. Replaying on that seed gives the ghost the same starting
board it actually played, and `agents/ghosts/manifest.json` carries the seed, the
seat, the team name and the original score.

## Do they still play well? Measured, yes

A ghost is **open-loop** — it cannot react to us — and the weed RNG is shared
between both farms and scales with each one's empty tiles, so our different play
perturbs its board too. Neither of those is a small objection, so it was
measured rather than assumed:

| ghost | original | replayed against us | kept |
|---|---|---|---|
| Patrick Chan | 120,199 | 108,355 | 90% |
| Aaweg Bhaladhare | 135,839 | 100,815 | 74% |
| Rikito Kanda | 130,149 | 81,795 | 63% |
| Kenjo1209 | 92,684 | 83,611 | 90% |
| Apollo's cattles | 52,901 | 114,658 | 217% |
| … 12 ghosts | | | **median 114%** |

They keep a median of **114%** of their original score. Several score *higher*
than they did, because we leave them more market room than their original
opponent did — which is itself an honest measurement of how much weaker we are.

**Use `verify` before trusting a new batch.** A ghost that collapses is noise
wearing a good player's name.

## What they say about us

| field | our win rate |
|---|---|
| `agents/lib`, our own strategies | **96%** |
| `agents/bench2`, our strongest shapes | 84–96% |
| **12 ghosts** | **42%** |
| the real ladder | 50–58% |

The ghost number is the one that tracks reality. Everything else is the echo
chamber, and the size of the gap is the size of the problem.

## How to use them

`tournament.py ghosts` plays every roster agent against every ghost **on the
ghost's recorded seed, in the ghost's recorded seat**. Two consequences:

* **Seats are not swapped and seeds are not shared**, so this is a field
  measurement, not a duel, and it is not seat-balanced. Compare candidates by
  win rate against the ghost set, not by Bradley-Terry — with one game per
  (roster, ghost) pair the BT graph is far too sparse and produces nonsense.
* **A ghost cannot be over-fitted to in the usual way**, because it does not
  adapt — but it *can* be over-fitted to as a fixed sequence. Rotate the set as
  new days are published rather than tuning against the same twelve forever.

## What the ghosts said about the engine decisions

Every engine change was re-measured against the ghost field. The headline is not
that anything reversed — it is **how badly the echo chamber compressed the
magnitudes**:

| change | against our own field | against 60–96 ghosts |
|---|---|---|
| the here-pass | +4 points (96.0% → 96.6% with the tile hold) | **36.7% → 1.7% without it** |
| the hiring ramp | +18, later +33 | **36.7% → 6.7% without it** |
| unit-picks-task scheduler | 77% → 54% | 36.7% → 3.3% |
| daily watering | 87.8% → 53.1% | 36.7% → 26.7% |

Removing the hiring ramp costs **$1,117 of median money and 30 points of win
rate**. On a weak field that change looks negligible; on a strong one it decides
the game. The echo chamber did not point the wrong way — it flattened the
differences until they were indistinguishable from noise.

The seven rejected changes were re-run too, and none of them reverses:

| rejected change | vs ghosts | paired against current |
|---|---|---|
| current | **39.6%** | — |
| `CARE` at priority 3 | 41.7% | 50–46 — a coin flip |
| carrying threshold 12 | 32.3% | 47–49 |
| fertilizer reserve 2× tiles | 12.5% | 41–55 |
| static zones | 5.2% | 35–61 |
| harvest every other tick | 25.0% | 24–72 |

`CARE` moves from clearly wrong to neutral; everything else stays rejected. The
engine decisions were right, and now they are right for a measured reason.

## What this does not give us

A ghost shows what a strong player *did*, never what they would have done. It
cannot punish a new exploit, and against a genuinely novel strategy its replies
are meaningless. It complements the ladder, which is closed-loop and slow, and
`agents/bench2`, which is fast and adaptive but shares our blind spots.

The three fields answer different questions:

| field | closed-loop | strong | fast | shares our blind spots |
|---|---|---|---|---|
| `agents/bench2` | yes | no | yes | **yes** |
| ghosts | **no** | **yes** | **yes** | no |
| the ladder | yes | yes | **no** | no |
