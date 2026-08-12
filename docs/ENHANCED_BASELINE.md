# The enhanced baseline *(historical)*

> **`agents/enhanced/` is no longer the best agent and has not been submitted
> since 2026-08-08.** It was superseded by the generated `mgtight` family
> (857.6 on the ladder) and then by a wrapped-plan agent (1363.7). This file is
> kept because the directory is still tracked, because it is the project's only
> worked example of a **multi-file** agent, and because its reasoning is sound
> even where its conclusions were overtaken.
>
> Read it for: how `tools/package.sh` builds a multi-file submission, and how an
> opponent-aware market layer is put together. Do **not** read it for what to
> build -- that is `docs/ROADMAP.md`.

`agents/enhanced/` — an opponent-aware farm assembled from what 95,000 locally
measured episodes actually showed. Every structural choice below traces to a
number in `docs/ATOM_EFFECTS.md`; nothing here is a guess dressed as a decision.

It is the first multi-file agent in the project, packaged with
`tools/package.sh` into the tar.gz Kaggle accepts, so the logic can be split
across modules instead of crammed into one `main.py`.

```
agents/enhanced/
  main.py       glue, per-episode memory, the plan constants, agent() last
  engine.py     engine constants and the exact price model
  opponent.py   forecasting their board, inferring their sells, sizing ours
  farm.py       board survey and the action scheduler
  market.py     hiring, land, livestock, feed, seeds, sales
```

---

## 1. What it inherits from the measurements

| Choice | Value | Why |
|---|---|---|
| labour | 11 hands, ≤6% of cash/day | `crew` won 55%, `swarm` (30 hands, uncapped) won **10%** — worse than never hiring, because the n-th hire costs `fib(n)` |
| land | **one quadrant, filled** | 1–2 beat 3–4 by ~10 points in the library; head-to-head, a two-quadrant version of *this* agent left 32 of 50 tiles idle against the leader's 18 of 25 |
| production | melon ×7, 10 cows, 8 sheep | `orchardherd` won **96.5%** in a balanced slice; adding strawberry and wheat (`mixedfarm`) lost 26 points. 18 pens + 7 melon is exactly one quadrant |
| fertilizer | always collected, sold on sight | a herd that never collects it ends on **$79** — bankrupt buying feed before day-8 milk. It is bridge financing, not a bonus |
| geese | none | `henhouse` measured 28.8%; the tiles are worth more as melon |
| feed | bought, never grown | growing 4 wheat costs ~6 actions; buying it costs ~$30 and zero actions, and actions are the binding constraint |

Melon is capped rather than filling the board because its pool is finite: **no shop demands melon**, only the town centre's 1/day, so roughly 158
units take the price from $250 to the $1 floor and both players draw from the
same pool.

---

## 2. The bugs, and one retraction

### Fixed: the opening starved the herd

The previous agent bought animals it could not feed. Day-by-day on seed 30001:
four animals bought by day 0, two dead by day 2, one alive from day 3 to day 10,
and the farm idle with three empty pens until the melon harvest funded a restart.
Roughly $1,200 of livestock and ten days of production, in every episode.

The first attempted fix made it **worse** — five lost instead of three — and the
reason is worth recording, because it is the same class of defect twice:

```
step 1:  BUY_WHEAT x6                  shed: 6
step 2:  BUY_COW x1 + SELL_WHEAT x6    shed: 0   <-- selling the feed we just bought
step 3:  BUY_WHEAT x6                  shed: 6
step 4:  BUY_COW x1 + SELL_WHEAT x6    shed: 0
```

The buyer sized the wheat reserve against the *intended* herd; the seller sized
it against *placed* animals only. Cows sitting in the shed counted for neither,
so freshly bought feed looked like surplus and went straight back to the market.
Eight turns took $3,000 down to $299 while stockpiling four unplaced cows, which
then starved.

**The fix is structural, not a patch:** one function, `market.feed_reserve()`,
computes the reserve once, counting every mouth committed to — placed, in the
shed, being carried, and the next two intended. Both call sites use it, so they
cannot disagree. Livestock purchases additionally require the feed to be
**present in the shed**, not merely affordable; affordability is not possession.

Measured after: **0 animals lost in the first 16 days**, and the same seed goes
from 25,102 to 63,225.

### Fixed: melon oversold

21% of episodes kept selling melon after the price had bottomed. Sale sizing now
comes from `opponent.sell_plan`, which never sells below a floor derived from the
post-dump price. Measured on seed 30001: 138 units sold against a 158-unit floor,
where the old agent's distribution had a 90th percentile of 168 and a max of 376.

### Retracted: "HIRE floods the market queue"

An earlier note in `docs/ATOM_EFFECTS.md` claimed the agent issued ~241 HIRE
orders per episode, most unaffordable, each wasting one of the ten market slots.
**Measured, that is false.** Both this agent and its predecessor hire at a
**100% success rate**:

| agent | HIRE orders | hands actually hired | success |
|---|---|---|---|
| `enhanced` | 266 | 266 | 100% |
| `barnyard` | 279 | 279 | 100% |

The claim came from a public meta write-up describing *other players* and was
never checked against ours. Hiring is still budget-capped — `fib(n)` explodes —
but not for queue-pressure reasons. Recorded here so nobody "fixes" it again.

---

## 3. The opponent model

Their whole board is public: every plant's `planted_day`, every animal's
`placed_day`, `yield_units`, `fed_today` and `pending_care_bonus`. Their harvest
schedule is *computable*. What is hidden is their shed, their carried inventory,
and their queued orders.

Two channels, both measurements rather than guesses:

**`forecast()` — what their board will produce.** One pass over their tiles gives
`ready` (harvestable now), `imminent` (within three days) and `capacity` per
product. Animal rates account for `CARE`, which triples steady-state output.

**`SellTracker` — what they have actually sold.** Market inventory is shared and
visible, and town consumption is deterministic given `unlocked_shops`, so

```
their sells  =  inventory delta  −  our fills  +  town drain
```

Our own submitted orders are recorded each turn precisely so the next turn's
residual can be attributed to them.

### Why the previous front-runner failed, and what changed

`docs/ATOM_EFFECTS.md` records a clean negative result: the `frontrun` atom
measured **69.4%** against `blind`'s **72.8%**. Selling into the opponent's
imminent harvest was worse than ignoring them entirely.

The flaw was that it reacted to their supply without asking whether the pool
recovers. Selling early into wheat or milk gains nothing — the town consumes
those steadily and the price comes back. Selling early into melon is everything —
nothing consumes melon, so it is a pure race.

So `sell_plan` compares the two forces directly:

```
threat  = their ready + imminent + their observed sell rate x horizon
refill  = town_rate(product) x days remaining
contested = threat > refill/2  and  headroom < threat + what we hold
```

When contested, it takes its share now but never below the price the market would
show *after* they dump — selling under that is giving the pool away rather than
racing for it. When not contested, it meters normally at 55% of base. Fertilizer
short-circuits both: nothing consumes it, its inventory only rises, so holding it
is strictly a loss and it always sells.

---

## 4. Measured results

Against the built-in `starter`, seed 5: **73,740** (barnyard ~67,000).

Robustness, `tools/stress.py`, 28 pathological configurations: **28/28 clean**,
worst turn 142 ms against the 1,000 ms budget. The most informative cell:

| case | `barnyard` | `enhanced` |
|---|---|---|
| melon base price set to $1 | 18,060 | **51,749** |

Barnyard lost 73% of its score when melon was worthless. The enhanced baseline
loses 30%, because the herd and the opponent-aware sell sizing carry it.

Head-to-head, 192 seeds x 2 seats = **384 episodes** each:

| opponent | win rate | 95% CI | margin |
|---|---|---|---|
| `barnyard` (the previous submission) | **100.0%** | [99.0%, 100%] | +25,753 |
| `homestead-crew-orchardherd-flood-blind-muck` (field leader) | **75.8%** | [71.3%, 79.8%] | +3,016 |

Getting there took one round of diagnosis. The first cut ranked **8th of 36** —
ahead of `barnyard` but behind every `orchardherd` variant — because of two
independent defects that only showed up in the digests:

* **The herd deadlocked at nine animals.** `feed_solvent` demanded
  `shed_wheat >= (n+1) * FEED_DAYS_REQUIRED`, but the reserve it checks is capped
  at `WHEAT_RESERVE_CAP = 28`. At nine animals that is 30 — unreachable. Two
  constants that had to agree, and did not. This is the third instance in this
  project of the same failure mode: one quantity, two formulas.
* **Two quadrants were worse than one.** 18 pens plus 12 melon tiles against 50
  tiles left **32 idle** while the hands walked further; the leader used 18 of
  25. Land does not add production, it spreads the same labour.

`docs/RUNS.md` has the full comparison.

---

## 5. Packaging

```bash
bash tools/package.sh agents/enhanced enhanced
```

Produces `submissions/<date>-enhanced/submission.tar.gz` with all five modules at
the **archive root** — Kaggle unpacks into `/kaggle_simulations/agent/` and loads
`main.py` from there, so a nested directory breaks the imports. The script
verifies the archive by unpacking it, checking that `get_last_callable` resolves
to `agent`, and running a full 720-step episode from the unpacked copy.

13 KB against a 100 MiB limit.

---

## 6. Known limitations

**The `SellTracker` cannot see sales at the $1 floor.** Those do not raise market
inventory, by design in the engine, so a fully crashed product looks like nobody
is selling it. Harmless — nothing more can be extracted from a floored product
anyway — but it means the inferred rate understates a dumping opponent late.

**`forecast` assumes they harvest promptly.** It counts `yield_units` on their
tiles as sellable now. An opponent that deliberately holds harvested stock in the
shed is invisible to it, because sheds are private.

**The plan is still fixed.** Shops unlock randomly and with replacement, and they
decide what the town actually buys — but the crop and herd targets are constants.
Reading `unlocked_shops` to re-weight production is the largest remaining gap,
and is item 1 in `docs/IMPROVEMENTS.md`.

**No fertilizer is ever spent on plants.** Fertilizing an ongoing crop on a
production day doubles that yield. All fertilizer is sold instead, which is right
for fertilizer as a commodity but leaves the strawberry/tomato multiplier unused.
Not applicable to the current plan, which grows only melon — melon reaches its
cap on water alone — but it constrains what the plan can become.

**Local rank still has not been validated against the ladder.** Every opponent in
the field is one we wrote.
