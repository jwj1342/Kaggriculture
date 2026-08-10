# What was changed in the engine, and what it was worth

`agents/_engine.py` is the single execution path behind every generated
strategy, so a change here moves the whole library at once. That is exactly why
each one below is an A/B against a fixed set of opponents on the same seeds,
with the arm size stated. **Five landed and four were rejected**, and one of the
rejections turned out to be a bug in the change rather than a fact about the
game — `compost` lost twice on good evidence before an interaction was found and
it became the largest single win here.

The rule this file exists to enforce: **an engine change is a claim about the
game's rules, and it gets measured before it is believed.** Every entry cites the
rule in `reference/engine/kaggriculture.py` it depends on.

---

## Landed

### 1. Feed before livestock, and one feed reserve

`market.py` in `agents/enhanced/` had already fixed this; the library engine had
not, so all 594 strategies were quietly starving their herds whenever the
opening cash went elsewhere.

* An animal escapes after **two unfed days** (`consecutive_unfed >= 2`), and
  returns nothing for four to eight days. The purchase gate asked whether the
  feed was *affordable*, not whether it was *in the shed*.
* The buyer sized the wheat reserve against the intended herd and the seller
  against placed animals only, so wheat bought for the herd was sold straight
  back. One reconstructed episode churned **944 wheat** through the market with
  the herd stuck at six of a planned fourteen.

Both now come from one `feed_reserve` computed once per turn, and `feed_solvent`
counts wheat in transit as well as in the shed — hands carry eight at a time, so
a farm that is actively feeding can look insolvent while it is not.

A third defect in the same area: the seed budget kept a flat `$100` cash floor,
fine for a `$10` wheat seed and ruinous for a `$100` strawberry seed. The
reconstruction of the ladder's strongest shape spent `$4,000` on 44 seeds in two
days and then sat on **$72 with three hands and no animals until day 10**. The
floor now reserves the next few animals and their first feed.

**Worth**, same 12 seeds, same pairings, old engine against new:

| strategy | old | new | win rate vs `barnyard` |
|---|---|---|---|
| `homestead-crew-orchardherd-flood-blind-muck` | 42,911 | **66,158** | 100% → 100% |
| `estate-crew-berryherd-flood-blind-muck` | 39,934 | **64,924** | **8% → 100%** |
| `estate-crew-mixedfarm-metered-blind-muck` | 32,936 | **49,448** | 0% → 92% |

The strawberry plans gained most, because crops and animals compete for the same
opening cash. Everything `docs/ATOM_EFFECTS.md` says about `produce` was measured
before this fix and is superseded.

### 2. Alternate-day watering for `ongoing` crops

The end-of-day rule is:

```python
if tile["consecutive_unwatered"] >= 2:
    farm["tiles"][y][x] = {"kind": "WEED"}; continue
...
fertilized = was_watered and tile.get("fertilized_until_day", -1) >= current_day
tile["yield_units"] = min(cd["max_yield"], tile["yield_units"] + (2 if fertilized else 1))
```

**An ongoing crop's production tick does not depend on being watered that day.**
Watering only stops the tile turning into a weed after two dry days, and — when
fertilising — doubles the tick. So a strawberry tile can be watered every other
day at no cost in yield. On 28 tiles that removes about 160 watering actions an
episode, and actions are the binding constraint: only ~15% of them do any work,
44% is walking and 17% is `PASS`.

**Worth: 71.1% → 82.2%** over 3,072 episodes an arm against four fixed
opponents, +$2,300 median. Improved three of four shapes strongly, one neutral.

### 3. Water the tick days, so fertilizer actually lands

This one is a **correction to two earlier conclusions**, and the most valuable
change of the session.

`compost` -- spending the fertilizer on the crops instead of selling it -- was
rejected twice. It lost 15 pairings out of 15 in run #7, and still lost 38% to
62% after the priority was fixed. The arithmetic said it should win easily: with
realized ladder prices, a fertilized strawberry tile earns **$89 a day against an
unfertilized $44**, the best rate of anything in the game.

The gap was an interaction with change #2 above. The bonus is evaluated as

```python
fertilized = was_watered and tile["fertilized_until_day"] >= current_day
```

against **today's** watering, for a tick that resolves tomorrow. Strawberry ticks
every two days; alternate-day watering also has period two. In anti-phase, every
single tick lands on a dry day and the fertilizer buys nothing. Measured: 5.1
units a planting against a fertilized ceiling of 8.

So `ongoing` crops are now watered when thirsty **or** when tomorrow is a
production tick, and `FERTILIZE` only targets tiles that are already watered and
within the three-day cover of a tick.

| | strawberry per planting | strawberry sold |
|---|---|---|
| `muck` (sell it) | 3.3 | ~110 |
| `compost`, before this fix | 5.1 | ~140 |
| `compost`, after | **4.9-5.3** | **~180** |

**Worth: `compost` goes from losing to winning.** 66.3% against `muck`'s 54.8%
over 6,144 episodes an arm, all eight shapes improved, median money +$7,931.
Head to head on the same shape, 77.1% [72.9%, 81.3%] over 384 episodes.

The lesson is not about fertilizer. **Two changes that are each correct can
cancel**, and an atom rejected on measurement can be wrong-because-of-a-bug
rather than wrong. `compost` was rejected twice on good evidence and was right
both times.

### 4. Fertilizer price gate

Nothing consumes fertilizer, so its price only falls — ours closes the season at
**$8 against a $100 base**. Collecting it costs one action per animal per day
(227 an episode, measured). Below `$30` the action is worth more elsewhere.
Skipped entirely when the fertilizer is being *spent* on crops, where price is
irrelevant.

**Worth: 83.3% → 85.0%** over 3,072 episodes an arm; positive on all four shapes,
so the sign is solid even though the intervals just touch.

### 5. `shopwise` — a seventh axis, and the first about the town

Shops are drawn **with replacement**, eight instances, and unlock on a fixed
schedule of one every three days from day 3. A shop that sells a single product
counts double. Measured across 101 real ladder episodes, town demand per day:

| product | min | median | max | spread |
|---|---|---|---|---|
| WOOL | 1 | 13 | 49 | **49x** |
| CARROT | 1 | 19 | 55 | 55x |
| MILK | 1 | 19 | 37 | 37x |
| STRAWBERRY | 7 | 25 | 49 | 7x |

A fixed herd is a bet that the draw comes out average. The same four sheep are
worth `49 x 30 x $200` of season capacity in one town and almost nothing in the
next. `shopwise` re-weights the herd by `day_drain x base_price`, holding the
head count — and therefore the tile budget — exactly as planned.

**Worth: 68.4% → 71.9%** over 6,144 episodes an arm, six of eight shapes
improved. The gain is largest where the herd is most lopsided
(`berrydairy` 51.3% → 64.5%, `berrywool` 57.9% → 64.5%) and smallest on an
already-balanced one (`bigberry` 77.9% → 79.2%) — which is what a hedge should
look like.

It cannot do more than it does: the herd is bought by about day 15 and only
three of eight shops have unlocked by day 10, so most of the bet is placed
before the town has revealed itself.

---

## Measured and rejected

### Sticky task targets, and idle units pre-positioning

44% of actions are movement and 17% are `PASS`, and "nearest free unit" is
recomputed every turn — so a unit three steps into a five-step walk can be
pulled onto a nearer task and those steps wasted. Both fixes were tried:

| arm | win rate | median $ |
|---|---|---|
| as-is | **63.1%** | **53,825** |
| + sticky targets | 44.4% | 48,700 |
| + sticky and pre-positioning | 45.0% | 47,731 |

2,048 episodes an arm, four shapes, every cell moved the same way. The greedy
recomputation is not thrashing, it is **adapting**: which unit is best for a task
changes as the board changes, and holding a unit to a target it chose several
turns ago sends it to work that is already done. The walking is the cost of a
50-tile board worked by 12 units, not a scheduling defect.

### Promoting `CARE` from priority 7 to 3

`CARE` accrues `pending_care_bonus`, spent on the next production tick, which
roughly triples steady-state animal output — so it looks underweighted at
priority 7, below fertilizer collection. **72.2% against 83.3%** over 3,072
episodes an arm, worse on all four shapes. It is not what the actions are short
of.

### Three attempts to raise FERTILIZE throughput

The top of the ladder is separated from the middle by one number. Across 184
real episodes, the median opponent gets **3.1 strawberry per planting** and so do
we (3.3, or 5.3 with `compost`). Four opponents get **7.6** — essentially the
fertilized ceiling of 8 — and they are the ones finishing on $139k-$171k while
everyone else is at $60k-$100k.

The gap is not fertilizer supply and not watering. It is the number of
`FERTILIZE` actions: ~110 are needed for 37 plants over four ticks each, and we
manage 52-62. Three ways to buy more were tried and all three lost:

| change | win rate | median $ |
|---|---|---|
| as-is (`fert_reserve = min(12, tiles)`) | **84.9%** | **70,206** |
| hold back `2 x tiles` of fertilizer instead of 12 | 41.0% | 58,772 |
| water every day when fertilising (instead of tick days) | ~neutral | ~equal |
| harvest ongoing crops every *other* tick | 82.6% | 69,382 |

The reserve change is the instructive one. A four-seed smoke test showed it
+$6,500 ahead; over 3,072 episodes an arm it is **44 points behind**. Fertilizer
held is fertilizer not sold, and the early price is real money. `docs/EVALUATION.md`
says four seeds cannot resolve anything and this is what that looks like.

The alternate-tick harvest is arithmetically free — `yield_units` caps at
`max_yield`, so banking two ticks of `+2` gives the same 8 units for half the
harvest actions — and it still lost overall, though it was the one change that
helped `marketgarden` specifically (89.7% against 86.1%, about two standard
errors). Not adopted on that evidence alone.

**What this means:** the action budget is the wall, and it is not obviously
movable by scheduling. 44% of actions are walking on a 50-tile board worked by
12 units. Whatever the top four are doing, it is not a priority tweak.

### `paced` — rate-matched selling

Depth and refill differ by sixty times across the nine products. Strawberry,
wool and milk reach the `$1` floor after 59–76 units while the town takes 13–25 a
day back out, so the market refills a quarter to a half of its entire depth
daily. Selling at the drain rate should hold the price near base all season,
where one dump crashes it and forfeits every later refill.

| market | win rate | median $ |
|---|---|---|
| `flood` | **68.3%** | **63,551** |
| `paced` | 63.9% | 63,043 |
| `metered` | 62.6% | 62,746 |

3,072 episodes an arm, worse on all four shapes. The reasoning is sound about a
*single* seller and wrong about this game: whatever you hold back, the opponent
sells instead. Dumping first takes the pool. The atom is kept in the registry so
the negative result stays reproducible.

---

### Four sweeps around the two biggest levers, all confirming what is there

Once the hiring ramp landed, the two settings it interacts with were swept
rather than assumed. All four arms were 2,304–3,072 episodes each against the
same fixed opponents.

**The ramp shape.** `min(plan, 2 + plants/3 + animals/2)` was a first guess and
turns out to sit on the optimum:

| ramp | win rate | median $ |
|---|---|---|
| `2 + p/3 + a/2` (kept) | **89.2%** | **71,176** |
| `2 + (p+a)/3` | 86.7% | 70,319 |
| `3 + p/2 + a/2` | 84.1% | 68,900 |
| `1 + p/4 + a/3` | 57.7% | 64,850 |

**Daily watering, retried.** It had been neutral before the ramp, and the ramp
frees actions, so it was worth re-running — changes interact, which is the whole
lesson of the fertilizer episode above. It is not neutral now, it is much worse:
**53.1% against 87.8%**. Watering only on tick days is right.

**The carrying threshold.** An idle unit walks to the shed once it holds six
units of produce, and the engine has *no carry limit at all* — `_inv_add` simply
adds — so raising the threshold looked like free movement savings, and shed
round trips are a large share of the 55% of actions spent walking.

| threshold | win rate | median $ |
|---|---|---|
| 6 (kept) | **89.2%** | **71,176** |
| 12 | 68.4% | 64,850 |
| 20 / 30 | 67.8% | 64,718 |

Produce in hand is produce not yet sellable. The delayed sales cost more than
the walking saves, and the effect saturates by 12 — above that the trigger
stops binding at all.

### Inverting the scheduler: let each unit pick its own task

The clearest single number separating us from the top of the ladder, measured
across three episodes: **they spend about one movement action per action that
does work; we spend 2.5.** Their split is 43% movement / 15% `PASS` / 42% work;
ours is 55% / 24% / 22%. Land does not explain it — two quadrants and three
produce byte-identical profiles — and neither does idle tile count.

The mechanism looked obvious. Assigning task-by-task in priority order hands
every task the globally nearest free unit, and the high-priority tasks go first,
so by the time a priority-8 watering is placed the only units left are the far
ones. Inverting it — each unit scores every unclaimed task as
`priority * W + distance` and takes its best — should cluster the work.

It does exactly what it was meant to do and still loses:

| scheduler | movement | `PASS` | work | win rate | median $ |
|---|---|---|---|---|---|
| task-picks-unit (kept) | 55% | 23% | 22% | **77.0%** | **70,301** |
| unit-picks-task, `W=1` | 46% | 33% | 21% | 54.3% | 62,398 |
| unit-picks-task, `W=2` | 48% | 32% | 20% | 42.8% | 60,016 |

Movement falls nine points, and it is `PASS` that absorbs the saving, not work.
Units that only take nearby tasks leave the distant urgent ones undone, and a
farm loses more to one unwatered plant than it gains from three saved steps.

Its four-seed smoke test showed **+$15,000**. Over 2,304 episodes an arm it is
23 points behind. That is the third time in one session that a four-seed check
pointed the wrong way; `docs/EVALUATION.md` is right and the smoke test is only
ever a syntax check.

**Six separate attempts have now failed to close the action-efficiency gap**:
sticky targets, idle pre-positioning, CARE priority, carrying threshold, daily
watering, and this. Whatever the top of the ladder is doing, it is not something
this scheduler can be tuned into.

### The idle time is not convertible

`mgtight` uses 34 of its 50 tiles and still spends 30% of its actions on `PASS`.
Sixteen spare tiles, idle hands, and a hiring ramp that would grow the crew to
match — so giving it more to do should be free. It is not. Every filler tried on
the tight base, against a field that can rank:

| shape | vs `bench` |
|---|---|
| `mgtight`, nothing added | **92.9%** |
| `mgtightherd` (+2 cow, +2 sheep) | 67.8% |
| `mgtightgrain` (+14 wheat) | 54.3% |
| `mgtightgrain2` (+24 wheat), `mgtightcarrot`, `mgtightboth` | below the top 9 |

This is the third independent test of the same idea — wheat on `smallhold`,
wheat after the hiring ramp, and now wheat, carrot and livestock on the tight
base — and all three say the same thing. **The `PASS` is not spare capacity.**
Work added at the edge of the farm costs more in walking than it returns, and the
21-22% ceiling on productive actions holds whatever is planted.

### Work the tile you are standing on

The one scheduler change that worked, and it came from looking at *when* the
opponent's units move rather than how far.

**50.1% of their actions that do work cost zero movement**, and 47% land on the
same tile as that unit's previous action. That is what a tile affords: an animal
takes FEED, then CARE, then COLLECT_FERTILIZER, then HARVEST — four turns
without a step — and a plant takes WATER then FERTILIZE.

Task-by-task assignment cannot see it. `claimed` is keyed on `(tile, op)`, so two
units are cheerfully sent to the same animal for two different jobs and both walk
there, while the unit already standing on it is sent somewhere else entirely.

A pass now runs before everything and gives each unit whatever work is under its
feet. It costs nothing, it is never wrong, and it is the first change to move the
metric:

| | steps per work action | movement | median $ |
|---|---|---|---|
| before | 2.36 | 50% | 66,722 |
| after | **1.87** | **39%** | **76,439** |

Measured over 1,920 episodes an arm on two shapes: `mgtight` 92.9% → **95.8%**,
`mgtightwide` 91.8% → **97.2%**.

**And it flipped a shape result that had failed three times.** Wheat as a filler
crop lost on `smallhold`, lost again after the hiring ramp, and lost a third time
on the tight base. With units able to chain work on a tile, `mgtightgrain`
(16 strawberry, 8 melon, **14 wheat**) is now the best shape measured: 86.7%
against the bench field and $75,727 median over 46,592 episodes, beating
`mgtightwide` **58.8% [54.5%, 63.1%]** head to head.

Four failures and then a win, because the thing that made it fail was somewhere
else entirely.

### Reserve the rest of a tile's work for the unit standing on it

A refinement of the one above, found by breaking our own zero-movement rate down
by action type:

| action | zero-movement | note |
|---|---|---|
| `CARE` | 54% | needs nothing carried |
| `FERTILIZE` | 42% | |
| `PLANT` / `HARVEST` | 35% / 29% | |
| `WATER` | 18% | one per plant per day — inherently a step apart |
| `COLLECT_FERTILIZER` | 16% | |
| `FEED` | **11%** | |

`CARE` chains and `FEED` does not, on the same animals. `claimed` is keyed on
`(tile, op)`, so the global pass was sending other units across the farm for the
*other* jobs on an animal a unit was already standing on — and by the next turn
that unit had nothing left and walked away.

Tiles worked in the here-pass are now held back from the global pass.
**96.0% → 96.6%** over 7,680 episodes an arm — 2.7 standard errors, small but
real, and free.

The zero-movement rate is 27.5% against the opponent's 50.1%, so most of that gap
is still open. `WATER` is the reason it cannot close much further with this
approach: it is the largest single category and one watering per plant per day
means consecutive waterings are always a step apart.

### Eleven schedulers, and the greedy one wins

`steps per action that does work` is the cleanest statement of the gap: the
ladder's best opponent runs at **1.02**, we run at **2.36**. At 1.02 a unit is
walking *through* its work — step, water, step, water — and no assignment rule
tried here produces that.

| scheduler | steps per work action | work % |
|---|---|---|
| **greedy: each task takes the globally nearest free unit** (kept) | **2.36** | **21%** |
| sticky targets | — | — (63% → 44% win rate) |
| each unit picks its own task, `prio*W + dist` | 2.4-ish | 21% (77% → 54%) |
| two passes: urgent global, the rest nearest-first | 2.89 | 18% |
| the same with the urgency cut at priority 4 | 2.99 | 18% |
| static zones: each unit owns a band of tiles | 2.86 | 20% |

Every alternative makes the ratio **worse**. Per-unit greedy in index order lets
neighbouring units take each other's nearby work; static zones make a unit walk
to its band and then idle in it while another band has three tasks waiting.

Two hypotheses were checked and are not the answer: the geometry is symmetric
(average distance to the shed is 4.00 whatever you own), and the engine
deliberately allows movement onto `LOCKED` tiles with shed operations resolving
before the lock guard, so routing across a locked quadrant is not a hidden cost.

**The greedy scheduler is at a local optimum in scheduler-space as well as in
parameter-space.** Whatever produces 1.02 is not a variation on assigning tasks
to units one turn at a time — it is more likely a different action model
entirely, such as planning a unit's route several turns ahead so that each step
lands on the next piece of work.

## The pattern in the rejections

Three of the four rejected changes were derived correctly from the rules and
still lost, and they lost for the same reason: **they optimise the farm as if it
were alone on the board.** Sticky assignment assumes the work list is static;
`paced` assumes the pool is yours to meter; promoting `CARE` assumes output is
the constraint. Two players draw from one market and one clock, and every one of
those assumptions is false in a way the arithmetic does not show.

The two that landed are both of the opposite kind: they remove work that the
*engine's own rules* say is unnecessary — a watering that does not affect yield,
an action spent collecting something with no buyer.
