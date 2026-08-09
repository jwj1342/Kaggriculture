# What was changed in the engine, and what it was worth

`agents/_engine.py` is the single execution path behind every generated
strategy, so a change here moves the whole library at once. That is exactly why
each one below is an A/B against a fixed set of opponents on the same seeds,
with the arm size stated. Three landed and four were rejected; two of the
rejections were ideas that looked obviously right.

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

### 3. Fertilizer price gate

Nothing consumes fertilizer, so its price only falls — ours closes the season at
**$8 against a $100 base**. Collecting it costs one action per animal per day
(227 an episode, measured). Below `$30` the action is worth more elsewhere.
Skipped entirely when the fertilizer is being *spent* on crops, where price is
irrelevant.

**Worth: 83.3% → 85.0%** over 3,072 episodes an arm; positive on all four shapes,
so the sign is solid even though the intervals just touch.

### 4. `shopwise` — a seventh axis, and the first about the town

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
