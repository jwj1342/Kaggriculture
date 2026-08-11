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
**The most likely-to-work version of C.** The meta's rigidity is real: it cannot
respond to the shop draw, and the shop draw swings demand for a single product
**49x**. A trace for the opening, where the board is deterministic and the meta
is strongest, handing over to the adaptive engine from about day 15, when the
town has revealed itself and a fixed plan is bleeding.

---

## 4. What tomorrow's numbers decide

Two measurements are in flight. They select the road:

**If `mgtightgrain` beats the meta agents in ≥35% of games** — the base is close
enough that road B pays. Counter-play on top of a competitive base is the
cheapest route to ~1,100.

**If it is under 20%** — the base is not competitive and countering will not
save it. Go to C or D; anything else is decoration.

**If the ladder score of `mgtightgrain` lands above 900** — the local-to-ladder
transfer is holding and the engine work is still paying. Below 850, it is not,
and the local field has drifted from reality again.

## 5. The order I would take them in

1. **Submit `mgtightgrain`** when the quota resets, and let it run 40+ episodes.
   It is measured, snapshotted and stress-clean; there is nothing to gain by
   holding it. (`docs/SUBMISSION_POLICY.md`)
2. **Road B, immediately**, while that accumulates — clone detection is a day's
   work and it is measurable against `agents/ref/` locally within minutes.
3. **Decide on C/D with the numbers from §4**, not before. A week-long search
   started on a hunch is the most expensive mistake available here.

The competition runs to 2026-09-30, so there is time for exactly one project of
C's size. Spending it on the right one matters more than starting it early.
