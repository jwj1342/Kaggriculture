# Improvement backlog

Ranked work not yet applied. Measured results live in `docs/ATOM_EFFECTS.md`;
this file is what to do about them.

Everything identified but **not yet applied** to `agents/barnyard.py`, ranked
by expected value. Each entry states the evidence, because several "obvious"
improvements measured *negative* when tested.

Status of `barnyard` as of 2026-08-07: submitted (`55332339`), ~67k median
against `starter`, ~30k in a mirror match, 0 crashes across 28 pathological
configurations, worst turn 145 ms against a 1,000 ms budget.

---

## Tier 0 — found on the ladder, not yet in the submitted agent

These come from 94 real episodes (`docs/LADDER_FIELD.md`). They are ahead of
everything below because they are the difference between 49% and the field, and
because they are already implemented in the *library* engine — the submitted
`agents/enhanced/` still has none of them.

### 0a. Spend the fertilizer on the crops instead of selling it

**Evidence.** Each production tick of an `ongoing` crop adds `2 if (watered and
fertilized) else 1`, so a fertilized strawberry yields **8 units per planting
instead of 4**. Nothing consumes fertilizer, so selling it is a race to a floor:
ours closes the season at **$8 against a $100 base** after we dump 330 units.
The strongest ladder opponent bought 42 strawberry seeds and sold 320 units —
7.6 per planting, against our library's 3.9.

**What to do.** Port the `compost` behaviour from `agents/_engine.py` into
`agents/enhanced/farm.py` and `market.py`: a `FERTILIZE` task on ongoing crops
whose cover has lapsed, a `PICKUP` of fertilizer from the shed, and a sale
reserve sized off the standing ongoing tiles.

### 0b. Stop building the plan around melon

**Evidence.** No shop buys melon; the town centre takes one a day. Its entire
season is worth **$7,500** sustainable plus a 158-unit one-off, against
strawberry's $90,000 and milk's $91,200. Measured on the ladder, both players
together sell a median of 184 melon into a pool of 188 — it is drained to the
floor every episode, and we take 45%. Melon closes at **8% of base**;
strawberry closes at **225%**.

**What to do.** Re-weight the crop plan toward strawberry and keep melon as the
early cash bridge it is good at. Run #7 measures which mix.

### 0c. Back-port the two engine fixes

`agents/_engine.py` now buys feed before livestock, gates purchases on feed
actually being in hand, and computes the feed reserve once for buyer, gate and
seller. `agents/enhanced/` already had the first and third; it does **not** have
the seed-budget floor, which is what bankrupted the reconstruction's opening.

---

## Tier 1 — large, and we have evidence

### 1. React to which shops actually unlocked

> Update from the ladder pull: **all eight shop slots unlocked in 35 of 35
> episodes.** The risk this item hedges against — a season with no buyer for
> your product — did not occur once. What varies is the *mix* (each individual
> shop appears in 57–74% of episodes), so the item stands, but "melon is safe
> because no shop is needed for it" was never a real hedge.

**Evidence.** The 1.32.6 rebalance made shops sample **with replacement**, capped
at 8 instances. One episode can spawn four Yarn Stores and no Bakery. Since town
demand is what the market absorbs (`docs/GAME_ECONOMICS.md` §3.2), the shop draw decides which
products are worth producing, and it changes every game.

Measured spread from the stress run, holding the agent fixed:

| Environment | Final money |
|---|---|
| `town buys every turn` | 110,481 |
| defaults | 66,409 |
| `shops never unlock` | 46,423 |
| `town never buys` | 30,918 |

A 3.5x swing driven purely by town demand, and in a real episode the composition
of that demand is random.

**What to do.** Read `obs["town"]["unlocked_shops"]` and recompute a target mix
each time a shop unlocks. The mapping is fixed and small:

```
BAKERY         EGG, WHEAT              PET_CAFE       CARROT (x2)
PIZZA_SHOP     MILK, TOMATO, WHEAT     SMOOTHIE_SHOP  STRAWBERRY, MILK
BRUNCH_SPOT    EGG, WHEAT, STRAWBERRY  FARMERS_MARKET WHEAT, CARROT, TOMATO, STRAWBERRY
YARN_STORE     WOOL (x2)               ICE_CREAM_SHOP STRAWBERRY, MILK, WHEAT
```

Per-day demand for product *p* = `6 x (instances demanding p, doubled for
single-product shops)` plus 1 from the town centre. Size the herd and crop plan
to that number instead of to constants.

**Risk.** Shops unlock late (day 3, 6, 9 …). Early decisions must be made blind,
so this is a mid-game correction, not an opening plan.

### 2. Stop over-committing to melon

**Evidence.** In the stress run, setting melon's base price to $1 collapsed the
agent from 66,409 to **18,060** — a 73% loss from one product. Melon is also the
only product with **no shop demand at all** (only the town centre's 1/day), so
its entire season pool is ~188 units (`docs/GAME_ECONOMICS.md` §3.7) and it is shared with the
opponent. Whoever sells first gets the price.

**What to do.** Treat melon as an opening burst, not an engine: plant it early,
sell it early and wide, and let the plan decay toward products with real town
demand. Cap total melon production near the absorption limit rather than at a
fixed tile count.

### 3. Fertilize the ongoing crops

**Evidence.** From the engine: an ongoing crop that is **fertilized and watered**
on a production day yields 2 instead of 1. Strawberry fires on days 10, 12, 14,
16 after planting; fertilizer covers `day, day+1, day+2`, so **two** `FERTILIZE`
actions (at ages 10 and 14) cover all four production days and take the tile from
4 units to 8. That is +$480 for 2 actions, minus the ~$150 of fertilizer sales
forgone — roughly **$165/action**, second only to harvesting a full animal.

**What to do.** Reserve a little fertilizer instead of selling every unit, and
add a `FERTILIZE` task keyed to each ongoing crop's production schedule.

**Risk.** Currently all fertilizer is sold on sight, which is correct *for
fertilizer as a commodity* (its price only falls). This trades a falling asset
for a rising one, so it should win, but it needs measuring.

---

## Tier 2 — plausible, unmeasured

### 4. Front-run the opponent

The market is shared and their board is fully visible, including every animal's
`yield_units`, `fed_today` and `pending_care_bonus` (see the observation dump in
the session notes). We can compute exactly when their milk or wool will land and
sell into the price first. `flexonafft`'s public replay agent already does a
version of this (`_front_run_market`).

Also free: **market inventory is shared and visible**, so tracking inventory
deltas and subtracting our own fills and the (deterministic) town consumption
recovers *exactly what the opponent sold each turn*. We use none of this.

### 5. Route units instead of assigning greedily

The scheduler assigns each task to the nearest idle unit, so hands criss-cross
the board and burn actions on movement. Clustering work per unit — finish a tile,
then the neighbouring tile — should recover a meaningful share of the action
budget. Actions are the binding constraint, so this is a real multiplier.

### 6. Size sales from marginal revenue

`SELL_FLOOR` and `SELL_BATCH` are hand-tuned constants. The price curve is known
exactly and already implemented in the agent; the correct batch is the one that
maximises revenue over the remaining season given expected town demand. Replace
the constants with the optimisation.

---

## Tier 3 — bigger bets

### 7. One-day lookahead search on market decisions

The per-turn budget is 1 s and the agent currently uses **0.246 ms** — 0.02%.
A full 720-step two-player episode simulates in 2.7 s, i.e. ~3.75 ms/step, so a
24-step (one in-game day) rollout costs ~90 ms. That is ~10 rollouts per turn
inside budget, enough to answer "sell now or in two days" against a simulated
market rather than a constant.

### 8. Imitation learning from the daily episode dataset

The official daily datasets hold 700–900 full replays each with complete action
sequences. Supervised imitation of strong play is far more tractable here than
RL from scratch — see the host-forum thread on
[RL vs deterministic baselines](https://www.kaggle.com/discussions/kaggriculture/733383),
where PPO/SAC reportedly collapsed into local optima ("extremely efficient melon
farmers") because of delayed rewards and zero-tolerance mechanics.

**Wait for post-08-07 data.** Everything dated 08-06 or earlier is pre-rebalance
(`docs/GAME_ECONOMICS.md` §2). Each daily dataset is ~450–570 MB compressed but **~21 GB
unpacked**, so pull one day at a time and delete after use.

If a model does ship, prefer **pure-numpy inference from an `.npz`** — measured
at 0.567 ms for a 4.2M-parameter MLP on one core, i.e. ~1,700 forward passes per
turn, with zero dependency risk.

---

## Measured and rejected

Things that looked like improvements and were not. Recorded so they are not
retried.

| Change | Result | Why |
|---|---|---|
| Buy the 4th quadrant (SE) | no change; agent never wants it | Melon saturates at ~14 tiles, animals at ~23. High-value work fits in two quadrants. `docs/GAME_ECONOMICS.md` §3.7 |
| Scale the crop plan up ×1.6 / ×2.2 | 68.9k → 63.7k → 55.9k | Extra tiles add cheap tasks (~$20/action) that starve expensive ones (~$960/action) |
| Raise `HAND_CAP` from 14 to 16 | −10k | `fib(16)`=1,597 and `fib(17)`=2,584; the 17th hand costs more than the first fifteen combined |
| Raise `TARGET_COWS` to 16 | 69.9k → 62.5k | Overshoots milk's ~403-unit season absorption and crashes the price |

---

## Open questions worth an experiment

- **Sheep vs cows.** In a single-seed probe smoke test `mono_sheep` scored 54,889
  and `mono_cow` 4,250. One seed proves nothing, but the gap is large enough to
  investigate — wool's demand comes from a single-product shop that consumes at
  2x, so a Yarn Store draw may dominate the result.
- **How much of animal income is fertilizer?** The `product_only` probe (animals
  kept but fertilizer never collected) scored **79** on its smoke seed. If that
  holds up, the animal engine is mostly a fertilizer engine and the herd should
  be sized for fertilizer, not milk.
- **Does metering actually pay?** `dump_all` vs the metered default is a direct
  test of the single most-repeated piece of public advice.

The probe league (`logs/league_probes.json`) answers all three with 16 seeds per
pair across both seats. See `docs/EVALUATION.md`.
