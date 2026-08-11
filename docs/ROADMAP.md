# Where this can go, and what it would take

Written after the discovery that changes the shape of the problem: **the top of
the ladder is a monoculture.** 79% of 96 sampled top farms play one identical
action sequence, and an independent analysis of 530 replays found 104 distinct
teams sharing plans, one group of 29 teams alone.

That is not a field of strong opponents. It is one strong opponent with a
hundred names.

---

## 1. Where we actually stand

| | |
|---|---|
| our ladder rating | **~790** |
| top 10 cutoff | **~3,050** |
| leader | 3,215 |
| our best local agent, head to head against the meta | $80,473 vs $107,829 |

The 790 → 3,050 gap is not a tuning gap. Twenty-eight engine changes, eleven
landed, moved us from 623 to 790.

## 2. Why the meta wins, mechanically

The meta is **not a scheduler**. It is a pre-computed 720-turn action sequence,
base85-encoded into the agent, replayed regardless of what happens.

| | the meta trace | our engine |
|---|---|---|
| actions that do work | **43.0%** | 27% |
| `PASS` | **6.8%** | ~25% |
| steps per action that works | **1.17** | 1.85 |

**An online scheduler cannot match a pre-computed plan in a near-deterministic
game.** The board starts empty and identical, tiles never move, crops grow on a
fixed clock. Only weeds and the shop draw vary — which is why the meta leaves 19
weeds standing and never adapts to the town. It does not need to.

Our scheduler re-derives every decision each turn from local heuristics and pays
for it in walking and idling. Eleven different scheduling rules were tried; the
greedy one we have is the best of them. **That line of work is finished.**

## 3. The four roads from here

### A. Keep tuning the online scheduler
**Ceiling: ~850.** Eleven scheduler variants and seventeen rejected changes say
this is done. Worth maybe one more pass over the crop shape now that `bench3`
contains the meta, and nothing more.

### B. Counter the monoculture
**Ceiling: ~1,100. Effort: days.** 79% of top opponents run a *known, open-loop*
script. Its board signature is detectable by day 4 (`closer_cleo` does exactly
this), and once detected, everything it will do is known in advance.

Two levers, neither of which needs its code:

* **Front-run the shared sell schedule.** Both players glut the same product on
  the same turn. Selling one turn earlier takes the better half of the price
  curve. `closer_cleo` is a worked example of this idea.
* **Take what it cannot.** It ignores the shop draw entirely. We have
  `shopwise`. In a season where wool demand is 49/day instead of 1, a fixed plan
  cannot pivot and we can.

This is real but bounded: it makes a weaker base agent punch above itself. It
does not close a 2,300-point gap on its own.

### C. Build our own trace
**Ceiling: top 10. Effort: a week, and it may fail.** The top is a trace, so
matching the top means having a trace. Not *the* trace — ours.

The search is tractable because the environment nearly is: fix a canonical seed,
optimise a 720-turn action sequence against it, verify it transfers across
seeds. We have 1,536 cores and an episode costs 2.6 s, so ~35,000 evaluations an
hour. Seed a search from our current engine's own output — which already plays a
coherent farm — and improve it with local moves rather than starting from noise.

Risks, stated plainly: a trace overfitted to one seed may not transfer; the
search space is 720 turns × 12 units and most of it is nonsense; and we would be
spending a week on something that may end up worse than what we have.

**Why not just use the public trace.** It is unlicensed and reconstructible, and
104 teams already run it — the NOTICE in `agents/ref/` declines to claim a
licence over it. Copying it would make us the 105th identical agent, and the
final ranking is a Bradley-Terry tournament among submissions: a clone gains
nothing from being a clone. The interesting question is whether an
independently-optimised trace beats the community-evolved one, and that question
is only answerable by doing C.

### D. Hybrid — trace opening, adaptive endgame
~~**The most likely-to-work version of C.**~~ **Measured and dead.** The idea was
that the meta's rigidity is real — it cannot respond to the shop draw, and the
shop draw swings demand for a single product **49x** — so a trace would carry
the deterministic opening and hand over to the adaptive engine around day 15.

`tools/hybrid.py` splices a recorded opening onto our engine at a chosen day and
the handover day is swept. Against `bench3` plus four reference agents, 96 seeds,
3,648 episodes an arm:

| handover | win rate | median $ |
|---|---|---|
| our engine alone | 54.0% | 69,804 |
| day 2 | 63.3% | 77,321 |
| day 6 | 69.7% | 78,591 |
| day 12 | 67.7% | 83,047 |
| day 16 | 64.7% | 86,879 |
| day 20 | 71.1% | 90,003 |
| day 24 | 72.3% | 89,017 |
| day 28 | 77.9% | 89,272 |
| the recording alone | **98.6%** | **99,168** |

**The curve never turns over.** There is no day at which our engine starts adding
value; more recording is better all the way to 100% of it. Two days of it are
worth +9.3 points. The premise of D — that the gap is concentrated in the opening
— is false: the gap is every phase.

Rerun with the engine's crop, herd and hand targets raised at handover to the
board it inherits (`--adopt`, without which the absolute targets make it refuse
to replant a farm larger than its plan, and it decays 55 -> 12 plants): ±4 points,
no change in shape. The handover shock is real and it is not the effect.

**What the curve does say** is where the cheapest remaining money is. Priced per
day, the steepest segment by a factor of four is the *last two*: day 28 to the
end is worth +20.7 points and $9,896, against 0-5 points for every other
segment. `endgame` switches the whole task list off on the liquidation day, so
WATER, FEED, CARE and COLLECT_FERTILIZER stop and an `ongoing` crop that is not
watered does not tick; the recording harvests 30 times, waters 19 and keeps
eleven hands on the payroll on day 29 while selling 133 wheat.

---

## 4. What the numbers decided

Both measurements are in. They ruled out more than they selected.

**`mgtightgrain` against the meta agents: 0 wins in 384.** Under 20% by the
widest possible margin, so **road B is dead** — countering an opponent we never
beat cannot be the lever. Its ladder score settled at 767, below the 850 line,
while the shape without the wheat filler reached 857.6 before falling back to
812 as its episode count grew.

**The handover sweep killed road D** (§3). The gap is not concentrated in the
opening, so there is no opening to graft.

That leaves **A** — worth one more pass and nothing more — and **C**, building a
full-season trace of our own. C is now the only road with a top-10 ceiling on it,
and the handover curve is the argument for it: a recording of *someone else's*
season, played by nothing but a lookup table, wins 98.6% of a field our best
engine wins 54% of.

## 5. The order I would take them in

1. **The endgame decoupling first.** It is the cheapest thing the handover curve
   found — 20 points priced in two days — and it is an engine change measurable
   in fifteen minutes, not a week. `endgame` fuses "start dumping inventory" with
   "stop farming"; the recording separates them.
2. **Then C, and only C.** A trace search seeded from our own engine's output,
   evaluated on many seeds against many opponents, because common random numbers
   do not control this environment — weeds and the shop unlock share one RNG and
   weed draws scale with *both* farms' empty tiles, so a sequence tuned on one
   seed sees a different board on the next. The recording's answer to that is to
   ignore weeds entirely, and it can afford to.
3. **Do not submit a copy of the public line.** 104 teams already run it. The
   final ranking is Bradley-Terry among submissions, so a clone of the modal
   agent draws 50% against the mode by construction — it inherits the cluster's
   rating and nothing above it, and `agents/ref/NOTICE` declines to claim a
   licence over the sequence. Use it as an instrument (`tools/hybrid.py`), never
   as a submission.

The competition runs to 2026-09-30, so there is time for exactly one project of
C's size. Spending it on the right one matters more than starting it early.
