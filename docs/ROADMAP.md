# Where this went, and where it can go

**Read this first if you have been away.** On 2026-08-11 the ladder score went
from 838 to 1364, and it was not a tuning result. The shape of the problem
turned out to be different from what the first ten days assumed, and most of
what was believed on 2026-08-10 is now known to be wrong. This file is the
correction, in the order the evidence arrived.

---

## 1. What we believed on 2026-08-10

* Our engine was a competitive agent that needed better parameters.
* The top of the ladder played one shared plan, and `agents/ref/closer_cleo.py`
  contained it.
* The gap was concentrated in the opening, so a recorded opening spliced onto
  our engine would close most of it.

All three were wrong. The measurements that killed them are below, each with its
arm size, because the pattern in this project is that plausible reasoning loses
to 100,000 episodes about four times out of five.

## 2. The gap is not in the opening — it is in every phase

`tools/hybrid.py` splices a recorded 720-turn opening onto our engine at a
chosen day, so "how much of the season does the opening decide" is measurable
rather than arguable. Sweeping the handover day, 96 seeds, 3,648 episodes an arm:

| handover | win rate | median $ |
|---|---|---|
| our engine alone | 54.0% | 69,804 |
| day 2 | 63.3% | 77,321 |
| day 6 | 69.7% | 78,591 |
| day 12 | 67.7% | 83,047 |
| day 20 | 71.1% | 90,003 |
| day 28 | 77.9% | 89,272 |
| the recording alone | **98.6%** | **99,168** |

**The curve never turns over.** There is no day at which our engine starts
adding value; more recording is better all the way to 100% of it. Two days of it
are worth +9.3 points. A hybrid has nothing to be a hybrid *of*.

Raising the engine's crop, herd and hand targets at handover to the board it
inherits (`--adopt`, without which its absolute targets make it refuse to replant
a farm larger than its plan, and it decays 55 → 12 plants) moves this ±4 points
and does not change the shape.

## 3. The top does not play the plan in `agents/ref/`

This is the correction that mattered most, and it was hidden by a one-line bug in
how similarity was measured.

Two farms running the same plan **one turn apart** agree on nothing when compared
index to index. Comparing the 156 recorded top trajectories to `closer_cleo`'s
embedded `_TRACE` that way gives 0% and looks like "they all play something
different". Sweeping shifts of ±8 turns first (`tools/lines.py`):

* only **8 of 156** overlap `closer_cleo`'s plan above 30%
* the recordings match **each other** at a median of **75.4%**, half of all pairs
  above 90%
* they collapse to **25 lines**, the largest holding **97 of 156 across 38 teams**

So the monoculture is real, and **the line this repo measured against all week is
played by about 5% of the top**.

## 4. The value is the wrapper, not the plan

Replayed on seeds they never saw, against `bench3` plus two references:

| agent | win rate | median $ |
|---|---|---|
| `closer_cleo` — plan **+ adaptive layer** | **99.2%** | 102,667 |
| cluster 1 representative — raw recording | 66.6% | 85,057 |
| our best engine | 60.9% | 71,557 |
| cluster 4 — raw recording | 29.1% | 45,715 |
| cluster 2 — raw, **best original score** | 11.8% | 14,984 |
| cluster 3 — raw recording | 0.9% | 1,217 |

An open-loop recording cannot transfer: different weeds and a different opponent
turn its actions into silent no-ops. **The most-played line is the most robust
one, not the best one** — cluster 2 has the highest original scores ($132,032
median against cluster 1's $78,510) and collapses hardest.

And in a 3,072-episode round robin a raw recording scores **0.0%** against every
agent that wraps a plan in an adaptive layer:

| | win rate |
|---|---|
| `closer_cleo` | 92.7% |
| `slotter_silas` | 73.8% |
| `ledger_lena` | 54.1% |
| `broker_bea` | 29.3% |
| raw recording | **0.0%** |

**What the wrapper actually is.** `closer_cleo`'s `agent()` rewrites only
`action["market"]` — `farmer` and `hands` come straight from the plan, untouched,
except for a controller that takes over the last few turns. It is a market layer:
a supply table measured over self-play, front-running a detected clone's glut,
and terminal liquidation. It is *not* micro-optimised movement or exception
handling; there is nothing to handle, since seeds and animals are fixed-price and
unlimited (`BUY_SEED` never touches `market["inventory"]`) and a purchase that
fails aborts only that one order.

## 5. So why did the score jump

Two things, in this order.

**Submitting `closer_cleo` unmodified** as a baseline, on the owner's explicit
instruction to prioritise ladder position. 838 → 1287. Its `_TRACE` is not
licensed by the dataset author (`agents/ref/NOTICE`: "reconstructible from public
replay data by anyone who wants it, and it reaches you on whatever terms the
competition's own rules provide"), so the question it raises is a competition
rules question, not a code-licensing one. **The snapshot carries LICENSE and
NOTICE beside it** and `docs/RUNS.md` records why it was sent.

**One line on top of it.** `closer_cleo` overrides its plan for the last three
turns with `_terminal_action`, an observation-driven harvest/drop/sell
controller. Its plan spends 8.8% of the last twenty turns watering — a day-29
watering ticks after the final turn and can never be harvested — and leaves 13
units standing in the field at the close. Sweeping the threshold, 384 seeds,
10,800 episodes an arm:

| controller starts | turns covered | win rate |
|---|---|---|
| step 704 | 16 | 91.9% |
| step 708 | 12 | 97.7% |
| **step 710–714** | **6–10** | **98.1%** |
| step 716 | 4 | 94.7% |
| step 717 — unchanged | 3 | 95.2% |

`step 714` is the smallest change reaching the plateau. Local: **+2.9 points**.
Ladder: **1287.2 → 1363.7, +76.5**. First time a change has been same-signed on
both.

## 6. What our own engine was worth

Eleven landed engine changes moved it from 623 to 857 over ten days. Today's two
findings are worth listing because they are the shape of everything left:

* **The seed freeze is a trade, not a deadlock.** The engine buys one round of
  seed on day 0 and nothing until day 11, sitting on $109–$435. Removing the
  cash floor that causes it *loses*, monotonically: 47.57% → 39.27% → 33.24% over
  137,664 episodes. The cash was going to livestock, which is worth more.
* **We were dismissing the workforce on the most valuable day.** Hands are a
  daily rental and the hiring block sat inside `if not endgame:`, so on the
  liquidation day twelve units became one, and 84 units of produce were left
  standing in the field. +1.66 points on `bench3`, +4.55 on the ghosts. Landed.

Both were found by instrumenting a *losing* experiment, not by reasoning.

## 7. The roads, with what is known now

### A. Keep tuning our engine — **ceiling ~900**
Eleven landed changes and seventeen rejections say this is finished. Our engine
wins 54–61% of the reference fields; `closer_cleo` wins 99%. This is not a
tuning gap.

### B. Counter the monoculture — **dead**
0 wins in 384 against the meta agents. Countering an opponent we never beat is
not a lever.

### C. Build our own full-season plan — **the only road with a top-10 ceiling**
The top is a plan plus a wrapper, so matching it means having both. Compute is
not the constraint: 0.375 episodes per core-second, ~2M episodes an hour on 1,536
cores, so a candidate evaluated on 8 seeds × 3 opponents costs 24 episodes and
~86,000 candidates fit in an hour.

The constraints are elsewhere, and §4 names them: an open-loop plan tuned on one
seed sees different weeds on the next, because weeds and the shop unlock share
one RNG and weed draws scale with **both** farms' empty tiles. Cluster 2 is what
that failure looks like — best original scores, 11.8% on transfer. Any search has
to evaluate across many seeds *and* many opponents, and the deliverable is a plan
**plus a market wrapper**, because the wrapper is where the measured value is.

### D. Hybrid opening — **dead** (§2)

## 8. Where the measurement stack is now

Both reference fields have saturated at the top. Eight variants of a
`closer_cleo`-class agent score 99.4% on the ghosts and cannot be separated;
`bench3` puts the same arms at 92–98%. Those fields were built to rank our
engine, which wins 54–61% of them.

The field that still discriminates at this level is **the wrapped agents against
each other** — 92.7 / 73.8 / 54.1 / 29.3, clean spacing, neither end saturated.
Use it for anything at this level, and read median money as a secondary signal
when win rate saturates: it ordered the terminal-window sweep correctly while the
ghost win rates were all identical.

`docs/EVALUATION.md` §6 has the full rule, including the opposite failure —
`dairy` was cut from `bench3` after being beaten by every candidate in every one
of 7,296 episodes.

## 9. What to do next

1. **Refresh the ghost pool.** The current 156 were pulled when we were at 838
   and they no longer separate anything at 1364. `bash tools/fetch_fields.sh
   ghosts 120` and re-cluster with `tools/lines.py`.
2. **Road C, and only C.** Seed a search from a recorded line rather than from
   noise, evaluate across seeds and opponents, and budget as much effort for the
   market wrapper as for the plan.
3. **Do not submit a copy of a public line as the final answer.** It gets the
   cluster's rating and nothing above it — 104 teams already run one, and the
   prize is top 10 among them. It is a baseline and a measuring stick, which is
   what it is being used as here.

The competition runs to 2026-09-30. There is time for exactly one project of C's
size, and choosing the right one matters more than starting early.
