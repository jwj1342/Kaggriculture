# The real field, and why local rank did not predict it

Every opponent this project had measured itself against until now was one it had
written. This document is what happened when we finally looked at the other kind.

`tools/ladder.py` pulled **94 episodes we actually played on the ladder**,
reduced each 19 MB replay to a ~1.4 KB digest, and threw the raw file away. Those
digests carry both players' composition, per-product buy and sell totals, hiring,
and money/herd/hands curves at days 5, 10, 15, 20, 25 and 29.

The headline: locally, `enhanced` beats `barnyard` **384 out of 384**. On the
ladder they are indistinguishable — 49% and 47% over 35 and 59 episodes. A
100-point local gap is worth two points against real opponents.

---

## 1. What the real field builds

Median opponent, over the 35 episodes played by the current submission:

| | real opponents | what we built |
|---|---|---|
| quadrants owned | **3** | 1 |
| animals at the end | 10–11 | 13–14 |
| crops standing at the end | 5 | **0** |
| weeds left standing | 3–9 | **0** |
| idle tiles | 35–38 | **7** |
| HIRE orders | 233–263 | 277 |

We are tidier, denser and better staffed, and we lose. The two boards are not
competing on the same axis at all: ours is a maximally utilised single quadrant,
theirs is a sprawl that leaves half the land fallow and grows the right things
on the rest.

The single strongest discriminator in the whole dataset:

| | episodes | our win rate |
|---|---|---|
| opponent sold **≥ 50 strawberry** | 15 | **27%** |
| opponent sold < 50 strawberry | 20 | **65%** |

We sell zero strawberry. The strongest opponent observed sold **320** of it and
finished on $171,062 against our $65,056.

---

## 2. The economic root cause

Every product's market is a pool with a one-time depth and a daily refill. The
refill is town demand, which depends on which shops have unlocked; the depth is
how many units drive the price from base to the $1 floor.

| product | base | units to the floor | town demand/day | **sustainable/season** | **sustainable value** |
|---|---|---|---|---|---|
| MILK | $160 | 76 | 19 | 570 | **$91,200** |
| STRAWBERRY | $120 | 62 | 25 | 750 | **$90,000** |
| WOOL | $200 | 59 | 13 | 390 | $78,000 |
| TOMATO | $60 | 529 | 13 | 390 | $23,400 |
| WHEAT | $25 | 4000 | 31 | 930 | $23,250 |
| CARROT | $35 | 842 | 19 | 570 | $19,950 |
| **MELON** | **$250** | **158** | **1** | **30** | **$7,500** |
| FERTILIZER | $100 | 493 | **0** | 0 | **$0** |

**No shop anywhere buys melon.** Its only consumer is the town centre's flat
one unit a day. So melon is a 158-unit one-off worth about $19,750 in total,
split between two players who both want it — and it is the *smallest market in
the game*.

**Nothing at all consumes fertilizer.** Its inventory only ever rises.

Measured across the 35 episodes, both players together sold a median of **184
melon** against a pool of 158 plus 30 of refill. The melon market is drained to
the floor in every single episode. We take 45% of it.

That shows up directly in the closing prices:

| product | closing price | vs base |
|---|---|---|
| **STRAWBERRY** | **$270** | **225%** |
| **WHEAT** | **$54** | **216%** |
| TOMATO / EGG / WOOL / CARROT | $81 / $62 / $239 / $42 | 120–135% |
| MILK | $141 | 88% |
| **MELON** | **$19** | **8%** |
| **FERTILIZER** | **$8** | **8%** |

Strawberry closes *above melon's base price*. We spend the season dumping the
only two commodities that collapse, and touch none of the six trading at a
scarcity premium.

---

## 3. The crop mechanics that make it worse

`ongoing` is the most important flag in `CROPS` and the library ignored it.

| crop | ongoing | first yield | interval | max_yield | units per planting |
|---|---|---|---|---|---|
| WHEAT | no | d2 | — | 6 | 6, then the tile is empty |
| CARROT | no | d2 | — | 4 | 4, then empty |
| MELON | **no** | d10 | — | 6 | **6, then empty** |
| TOMATO | **yes** | d8 | 1 | 4 | 4 ticks then the plant dies |
| STRAWBERRY | **yes** | d10 | 2 | 4 | 4 ticks then the plant dies |

For a **non-ongoing** crop, `yield_units` starts at 1 and each WATER inside the
ripening window adds one, capped at `max_yield`. Harvest empties the tile.

For an **ongoing** crop, `max_yield` is the number of *production ticks over the
plant's life*, not the size of one. Each tick adds:

```python
fertilized = was_watered and tile["fertilized_until_day"] >= current_day
tile["yield_units"] = min(max_yield, yield_units + (2 if fertilized else 1))
```

**A fertilized strawberry yields 8 units per planting; an unfertilized one
yields 4.** One `FERTILIZE` sets `fertilized_until_day = day + 2`, covering three
days — more than one strawberry tick. On a non-ongoing crop fertilizer adds no
units at all, but each watering counts double, so a fertilized melon needs three
waterings instead of five.

Not one of the 594 strategies in the library ever issued a `FERTILIZE`. The
`muck` axis only ever decided whether to *collect* the fertilizer and whether to
sell it. So every strawberry plan we measured ran at exactly half its ceiling:
`berrypatch` sold a median of 138 strawberry from about 35 plantings — 3.9 per
planting, against an unfertilized maximum of 4.

The real opponent bought **42 strawberry seeds and sold 320 units** — 7.6 per
planting. They fertilize. We sold 330 fertilizer per episode into a market with
no consumer, closing at $8.

---

## 4. Why the local ranking pointed the wrong way

Four things compounded, each individually small:

**The library could not express the winning strategy.** No `FERTILIZE`, so
`ongoing` crops were capped at half. `LAST_PLANT_DAY["STRAWBERRY"] = 13` also
stopped replanting twelve days before a planting stops paying — a strawberry
sown on day 19 still catches a tick on day 29.

**Melon looks best in a field of melon farmers.** Melon's revenue is the one
thing in the game that does not depend on which shops unlocked, because no shop
ever buys it. In a field where every strong agent grows melon, the contest
reduces to who drains the fixed pool faster, and our agent is good at that. It
is a stable local optimum and a poor global one. Measured across all 35 ladder
episodes, all eight shop slots always unlock — the shop risk that makes melon
look safe does not exist.

**The engine had bugs that hurt crops more than herds.** See below.

**Rank stopped tracking money.** In run #2, `estate-crew-berryherd-flood-blind-muck`
ranked 16th of 38 with a median of **$51,654** — more than `barnyard` at 14th
($44,242) and `dairy` at 15th ($36,304). The ordering was already disagreeing
with the thing the ladder actually scores.

### The engine bugs, and what fixing them was worth

Two defects in `agents/_engine.py`, both the same shape as ones already fixed in
`agents/enhanced/` and never back-ported:

* **Livestock bought against an empty shed.** The purchase gate asked whether
  the feed was *affordable*, not whether it was *present*. An animal escapes
  after two unfed days. Any strategy whose opening cash went elsewhere — buying
  $100 strawberry seeds, for instance — lost its herd.
* **Buyer and seller disagreed on the feed reserve.** The buyer sized it against
  the intended herd, the seller against placed animals only, so wheat bought for
  the herd was sold straight back. Measured on one reconstructed episode: **944
  wheat churned through the market**, herd stuck at six of a planned fourteen.

A third: the seed budget kept a flat $100 floor, fine for a $10 wheat seed and
ruinous for a $100 strawberry seed. The reconstruction spent $4,000 on 44 seeds
in its first two days and then sat on **$72 with three hands and no animals
until day 10**.

Controlled A/B, same pairings, same 12 seeds, old engine versus new:

| strategy | old | new | win rate vs `barnyard` |
|---|---|---|---|
| `homestead-crew-orchardherd-flood-blind-muck` | 42,911 | **66,158** | 100% → 100% |
| `estate-crew-berryherd-flood-blind-muck` | 39,934 | **64,924** | **8% → 100%** |
| `estate-crew-mixedfarm-metered-blind-muck` | 32,936 | **49,448** | 0% → 92% |
| `estate-crew-dairy-adaptive-blind-muck` | 36,664 | 38,658 | 50% → 67% |
| `homestead-crew-ranchmix-flood-blind-muck` | 46,092 | 51,992 | 58% → 67% |

Every strategy improved, and the strawberry plan improved most: from losing 11
of 12 to winning 12 of 12. **The old rankings were substantially a ranking of
how badly each strategy was hurt by the engine's bugs**, and they hurt the crop
plans hardest because crops compete with the herd for the same opening cash.

---

## 5. The sparring field

`tools/registry.py`'s `ladder` plan materialises the shapes that actually beat
us, read off the digests rather than designed:

| atom | reconstructed from |
|---|---|
| `berrybaron` | 24 strawberry + 10 melon, 8 cow + 6 sheep — the $171k opponent |
| `grazier` | 8 wheat + 4 melon, 14 cow — the cow-heavy archetype |
| `marketgarden` | 18 strawberry + 10 melon, 8 cow + 3 sheep — the balanced one |

plus a new `muck` option:

| atom | meaning |
|---|---|
| `compost` | spend the fertilizer on the crops instead of selling it |

Each is materialised on one and three quadrants, with and without `compost`, and
with `metered` and `flood` sale sizing — so the fertilizer multiplier and the
land question are each measured rather than assumed.

```bash
python tools/registry.py gen --plan ladder --out agents/spar
sbatch slurm/tournament.sh roundrobin --agents agents/spar/*.py \
    agents/enhanced/main.py agents/barnyard.py --seeds 24 --label ladder-field-spar
```

---

## 6. What the rebuilt field then measured

Run #8 screened all 960 cells of `produce × land × muck × market` against eight
anchors — 184,224 episodes, every cell holding exactly one strategy, so each
marginal below is a like-for-like comparison rather than a mean over whatever
company an atom happens to keep:

| `produce` | win rate | median $ |
|---|---|---|
| **`marketgarden`** (reconstructed) | **34.9%** | 35,995 |
| **`berrybaron`** (reconstructed) | **31.0%** | **37,510** |
| **`grazier`** (reconstructed) | **25.8%** | 22,550 |
| `woolworks` | 18.2% | 17,494 |
| `orchardherd` — *what the submitted agent is built on* | 16.1% | 15,337 |
| … `rootcellar` | 10.4% | 3,894 |

The three shapes read off real opponents take the top three places, ahead of
every shape this project designed for itself.

| `muck` | win rate | median $ |
|---|---|---|
| `compost` | 15.6% | **19,725** |
| `muck` | 15.6% | 18,089 |
| `dung` / `nomuck` | 13.0% | ~10,000 |

`land`: `smallhold`, `estate` and `latifundium` score **identically**, because
the `BUY_LAND` gate stops at two quadrants whatever the target is; all three beat
`homestead` (14.1% vs 13.5%). So the finding is *two quadrants beat one* — the
opposite of what the old library measured, and in the direction the real field
already pointed.

### The interaction, and a non-transitivity worth keeping

Run #9 confirmed the top 40 in a round robin, 48 seeds, 74,880 episodes. It
does **not** agree with run #8, and both are honest:

| matchup | result |
|---|---|
| `marketgarden-compost` vs `orchardherd-muck`, head to head | **30.2%** — melon wins the duel |
| the same two, against eight diverse anchors (run #8) | **34.9% vs 16.1%** — strawberry wins the field |

Melon beats strawberry *in a duel* because the melon pool is finite and
`orchardherd` drains it faster. Strawberry beats melon *against a field* because
its market regenerates. The ladder is a field, not a duel — and the ladder
digests already say opponents selling ≥50 strawberry beat us 73% of the time.

`compost` splits cleanly along the mechanism, which is the strongest evidence
that the mechanism is understood:

| within | `compost` vs `muck`, head to head |
|---|---|
| `marketgarden` (has ongoing crops) | **66.7%** — and earns more |
| `orchardherd` (melon only, not ongoing) | **14.6%** — fertilizer adds no units to a capped crop, so spending it is pure loss |

One implementation detail had to be fixed before any of this was measurable.
The end-of-day rule is `fertilized = was_watered and fertilized_until_day >=
current_day`: **fertilizer on a tile that is not watered that day does nothing.**
The first version ranked `FERTILIZE` above `WATER`, so it competed with the
action it depends on, and `compost` lost 15 pairings out of 15 in run #7.
Fertilizing only already-watered tiles took strawberry from 3.0 to **5.1 units
per planting**.

### Where the submitted agent stands

| run | field | `enhanced` |
|---|---|---|
| #6 (old engine, our own strategies) | 32 | **1st**, 75.8% against the field leader |
| #7 (reconstructed ladder shapes) | 34 | **27th**, 31.2% |
| #9 (top 40 of the balanced factorial) | 40 | **39th**, 2.9% |

`enhanced` still beats `barnyard` 96 games out of 96, so the ordering between our
own two agents was never wrong — they are both simply far below what the field
looks like once it is measured properly.

---

## 7. What this does not settle

The reconstructions are fitted to end-state digests, not to observed action
sequences — a replay records what a farm looked like, not why. Two different
policies can produce the same digest. They are a harder and more *representative*
field than what we had, not a simulation of specific opponents.

94 episodes is enough to see a 38-point split (27% vs 65% on the strawberry
cut) and not enough to rank anything finely; `docs/EVALUATION.md` has the
sample-size arithmetic. The ladder sample also covers two submissions over about
two days, so it describes the field at that rating, not the field at the top.
