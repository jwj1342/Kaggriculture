# The game, and what the engine actually rewards

Everything here is derived from `reference/engine/kaggriculture.py` — a copy of
the file the episodes import — not from the competition's prose, which is stale
in several places (§2). Re-diff that copy against the installed package after
every `kaggle-environments` upgrade; the balance has already changed once
mid-competition.

Companion documents: `docs/ATOM_EFFECTS.md` measures which of these levers
actually pays, and `docs/ADVERSARIAL.md` covers what you can do *to* the
opponent.

## 1. What the competition actually is

Two agents each run a farm for one 30-day season = **720 turns** (24 turns/day).
Whoever has more **coins in the bank** at the end wins. Unsold inventory scores
zero. Rating is Elo-style: only win/loss/tie matters, never the coin margin. A
final Bradley–Terry tournament decides the leaderboard.

Each turn an agent returns:

```python
{"farmer": [op, *args], "hands": [[op, *args], ...], "market": [[op, *args], ...]}
```

The main farmer plus every hired hand each get one action; up to
`maxMarketOrdersPerTurn` (10) market orders are processed per turn.

**This is a scheduling problem wearing a farming costume.** The scarce resource
is *actions*, the scarce asset is *tiles*, and the price of everything you
produce moves against you as you sell it.

### Hard constraints worth memorising

| Constraint | Value | Why it bites |
|---|---|---|
| `actTimeout` | **1 second per turn** | No search. Heuristics only. 60 s total overage bank. |
| `shedCapacity` | 100 items | Overflow at end-of-day is **discarded**, not queued. |
| `maxMarketOrdersPerTurn` | 10 | Hires, land, buys and sells all compete for these slots. |
| Submission size | 100 MiB | Runtime: 1.6 vCPU, 6.5 GiB RAM, 8 GiB disk. |
| Daily submissions | 5 | Only the latest **2** stay active. |

---

## 2. The 1.32.6 rebalance — and why old meta data is now suspect

`reference/engine/kaggriculture.py` is the ground truth: it is the file the
episodes import. It **disagrees with the overview page**, and the reason matters.

On **2026-08-06/07** the host shipped a balance change
([discussion 733431](https://www.kaggle.com/discussions/kaggriculture/733431),
[PR #1394](https://github.com/Kaggle/kaggle-environments/pull/1394)), announced as
*"rolling out and hitting the leaderboard — make sure to upgrade to >= 1.32.6"*:

| | Before (what the overview page still describes) | After (1.32.6, what runs now) |
|---|---|---|
| Town centre | buys **2×/day**, escalating to 2×/4× after days 10/20 | buys **1×/day**, flat all season |
| Shop unlocks | sampled **without** replacement | sampled **with** replacement, capped at 8 instances |

The host's stated reason: *"The large demand from the TC meant that markets were
too resistant to sell pressure later in the game."*

**Two consequences that drive everything below.**

1. **Markets are now much more fragile.** Town demand was cut by roughly half to
   three-quarters late-game. Overproducing and dumping is punished far harder
   than it was a week ago. Metered selling matters more, and large herds matter
   less.
2. **Every public meta analysis dated 2026-08-06 or earlier describes a game that
   no longer exists.** That includes the daily episode datasets and the modal
   "8 cows + 6 sheep" farm in §5 — that composition was calibrated against
   *double* the town-centre demand. Treat pre-08-07 strategy conclusions as
   historical, not as targets.

Shops drawn with replacement also means **each game is genuinely different** —
one episode may spawn four Yarn Stores and no Bakery. A fixed crop-and-herd plan
is now strictly worse than one that reads `obs["town"]["unlocked_shops"]`.

Also not on the overview page: **`actTimeout` is 1 second**. The framework
deducts only the *excess* over one second from the 60 s bank
(`overage_time_consumed = max(0, duration - actTimeout)` in `core.py`), so the
real budget is 1 s every turn *plus* 60 s of borrowing across the episode.

Re-diff `reference/engine/` against the installed package after every
`kaggle-environments` upgrade — this has already changed once mid-competition.

---

## 3. The economics

### 3.1 Price curves

```
price(inv) = base ± amp · f(|inv − I0|),     amp = target · base / f(T)
```

Every product starts at `I0 = 10,000`. Selling pushes inventory up and price
down; town consumption pulls it down and price up. Floored at $1.

The `above_func` is what decides how badly you can hurt yourself. Units you can
dump from equilibrium before hitting the $1 floor:

| Product | Base | `above_func` | Units to floor | Character |
|---|---|---|---|---|
| Wool | 200 | `sq` | **59** | Dumps instantly |
| Strawberry | 120 | `linear` | **62** | Dumps instantly |
| Milk | 160 | `linear` | **76** | Dumps instantly |
| Melon | 250 | `sq` | **158** | Cheap early, cliff later |
| Tomato | 60 | `sqrt` | ~555 | Gentle |
| Carrot | 35 | `sqrt` | ~918 | Gentle |
| Wheat | 25 | `log` | 3000+ | Effectively never crashes |
| Egg | 50 | `log` | 3000+ | Effectively never crashes |
| Fertilizer | 100 | `linear` | ~500 | Steady bleed |

Melon's quadratic curve is worth internalising: the first 10 melons cost you
$1 of price, the 158th costs you $250. Sell melon **early and wide**.

### 3.2 The town is the real customer

The 10,000-unit buffer is a one-off. What pays the bills all season is town
demand, and it is much larger than the buffer:

- Up to **8 shop instances**, unlocking one every 3 days from day 3.
- Each instance consumes one of each of its products every **4 turns** = 6×/day
  (single-product shops pull 2×).
- Plus the town centre: one of every non-fertilizer product per day.

That totals roughly **2,000 units of demand across a season**, weighted by which
shops happen to unlock. Wheat appears in 5 of the 8 shop types, strawberry in 4,
milk in 3, egg and tomato in 2, carrot and wool in 1 each (both at 2×), and
**melon in none**.

Two consequences:

- **Melon is a fixed pool, not a faucet.** Its only demand is the town centre's
  1/day. Total extractable value across the whole season is roughly **$26k**,
  and it is *shared with the opponent* — first seller wins.
- **Herd size should track town demand, not land.** ~3 shops wanting milk absorb
  ~18/day; 8 cows on daily `CARE` produce ~12/day. The public meta's "8 cows +
  6 sheep" is calibrated to exactly this, not chosen arbitrarily.

### 3.3 Fertilizer is one-way

Every surviving animal makes 1 fertilizer per day, free, fed or not
(`fertilizer_available = True` on every end-of-day refresh). It is worth ~$100
at base.

**No shop and not the town centre consumes `FERTILIZER`** — check
`TOWN_CENTER_PRODUCTS` and `SHOPS` in the engine. So its market inventory only
ever rises and its price only ever falls. Holding fertilizer for a better price
is *strictly* a losing move. Sell every unit the turn it reaches the shed.

### 3.4 Farm hands: the cheapest lever, up to a point

The n-th hire of a day costs `fib(n)` = 1, 1, 2, 3, 5, 8, 13, 21, … and each hand
buys 24 extra actions that day. Cumulative payroll:

| Hands | 5 | 8 | 10 | 12 | 14 | 16 | 17 | 18 | 20 |
|---|---|---|---|---|---|---|---|---|---|
| Cost/day | 12 | 54 | 143 | 376 | 1,596 | 2,583 | **4,180** | 6,764 | 17,710 |

The first eight hands cost less than one melon seed. The 17th hand alone costs
more than the first fifteen combined. Testing confirmed the curve: pushing
`HAND_CAP` from 14 to 16 *lost* ~10k because payroll outran the extra output.
Budget the day's payroll as a fraction of cash rather than chasing a head count.

### 3.5 `CARE` roughly triples animal output

`CARE` + `FEED` on the same day banks +1 on `pending_care_bonus`, paid out on the
animal's next scheduled production. A cow (interval 2) goes from 1 milk per
2 days to **3 milk per 2 days** — $160/day extra for one action. Note the code
checks `fed_today` *before* resetting it, and an unfed animal still produces its
base 1 unit but forfeits the whole banked bonus.

### 3.6 Yield rules worth getting exactly right

- A fresh seed starts at `consecutive_unwatered = 1`. **Plant and water the same
  day or it is a weed by nightfall.** No grace period.
- One-shot crops gain +1 unit per watered day inside `[⌈max_yield_day/2⌉,
  max_yield_day]`; fertilizer makes it +2. Watering outside the window only
  keeps the plant alive, so the cheap pattern is *alternate days, then daily
  through the window*.
- Wheat and carrot **cannot** reach their listed max yield on water alone (4 and
  3, not 6 and 4). Melon reaches its cap of 6 on water alone by day 10 —
  fertilizing melon is wasted.
- Animals survive on **alternate-day feeding** (`consecutive_unfed >= 2`
  escapes), but the `CARE` bonus needs them fed *daily*.

### 3.7 Why nobody buys the fourth quadrant

The land is bought in a fixed order — NE $1,000, SW $2,000, SE $4,000 — and the
public meta's modal farm owns exactly `NE + NW + SW`. SE is never bought. The
reason is not geometry: all four quadrants are perfectly symmetric about the
shed, each owning one of the four shed-access tiles.

It is that **the market saturates long before the land does**, and the work that
does pay saturates even sooner. Expected town demand over a season plus the
initial 10,000-unit buffer, against what a single 25-tile quadrant produces:

| Product | Season absorption | One quadrant produces | Tiles that saturate it |
|---|---|---|---|
| Melon | 188 | 346 | **14** |
| Strawberry | 488 | 167 | 73 |
| Carrot | 1,169 | 562 | 52 |
| Wheat | 4,525 | 600 | 188 |
| Milk | 403 | — | ~13 cows |
| Wool | 287 | — | ~10 sheep |

Melon — by far the best crop per action — is fully saturated by **14 tiles**.
Animals saturate at roughly 13 cows + 10 sheep. That is ~37 tiles of genuinely
high-value work, which fits inside two quadrants.

Everything past that is low-value work competing for the same hands:

| Work | Coins per action |
|---|---|
| Animal HARVEST (6 units at once) | ~$960 |
| Melon bonus-window WATER | ~$250 |
| Sheep / cow daily cycle | ~$80 |
| Strawberry | ~$30 |
| Carrot / wheat / tomato | ~$16-21 |

So extra tiles do not add income, they add *cheap* tasks that starve the
expensive ones. Measured over 8 seeds, forcing the crop plan to fill more land
makes things monotonically worse:

| Config | Median money |
|---|---|
| 3 quadrants, crop plan ×1.0 | **68,892** |
| 4 quadrants, crop plan ×1.0 | 68,892 (never actually buys SE) |
| 3 quadrants, crop plan ×1.6 | 63,724 |
| 4 quadrants, crop plan ×2.2 | 55,766 |

And on quadrant count alone: 1 → 49,078 · 2 → 68,738 · 3 → 68,892 · 4 → 68,892.
**The second quadrant is worth ~20k; the third is noise; the fourth is worth
nothing and costs $4,000** — which instead buys 10 cows.


---

## 4. The three public notebooks

Pulled into `reference/notebooks/` (`.ipynb` plus a `.py` conversion for
grepping).

### `bovard/kaggriculture-getting-started` — the official tutorial (342 votes)

Walks the observation format and ships **"Melon Maxxer"**: buy a melon seed when
out, walk to the nearest tile needing work (harvest > water > plant), sell the
whole shed when melon price ≥ $200. The notebook then lists its own flaws — never
hires, never buys land, monocrops, and dumps its entire inventory in one order,
crashing the price mid-sale. Useful as a floor and as a correct reading of the
observation schema; not competitive.

### `cjlcjlcjl/kaggriculture-what-the-top-farms-do-a-live-meta` — the meta tracker

The most valuable of the three. It re-derives the engine's economics
(profit per tile-day, yield curves, the price-cliff table) and then **streams the
official daily top-episodes dataset** to tally what high-Elo players actually
built. Its 2026-08-06 snapshot (Elo band 2700+, 683 episodes):

- **Modal farm: 8 cows + 6 sheep, 5 hands, land NE+NW+SW — 44% of players.**
  Notably *no crops* at the top.
- Ending money: **median 115,664, max 168,527**.
- Build order (median first-order day): first hire **day 0**, first cow **day 0**,
  first sheep **day 0**, first land **day 7**.
- Early seeds, days 0–4: wheat 14.0, melon 11.6 per player.
- Cash curve: d5 = 299, d10 = 2,212, d15 = 21,272, d20 = 45,689.
- Sell rhythm (first day / avg batch): fertilizer d3/4.5, wheat d2/5.6,
  wool d9/5.3, melon d10/12.8, milk d10/4.8, strawberry d18/12.2.
- Ladder Elo moved from median 670 (07-30) to 2,973 (08-06) — the bar rises
  ~100 points a day, so a fixed strategy goes stale in about a week.

Its headline advice: sell in small metered batches, and since everyone runs the
same farm, **differentiate on timing** — sell into the shared market before the
opponent's harvest lands.

> **Caveat:** every number above predates the 1.32.6 rebalance (§3). The modal
> farm was tuned against a town centre buying twice as much, and against shops
> drawn without replacement. Its *method* — stream the daily dataset, tally what
> wins — stays valid; its *conclusions* need re-deriving on post-08-07 episodes.

### `flexonafft/kaggriculture-adaptive-replay-agent` — trajectory replay

A different school entirely. It embeds **two complete pre-optimised action
sequences** (zlib + base85 blobs) and picks one at episode start based on melon
and strawberry prices, then replays it verbatim. It never mixes routes mid-game.
Runtime adaptation is deliberately minimal:

- weed recovery when the board drifts from the recording,
- `_front_run_market`, which re-ranks existing SELL orders by opponent exposure ×
  glut weight × price × `log1p(qty)` — reading the opponent's tiles to sell ahead
  of their harvest,
- `_terminal_overlay`, an endgame liquidation that `PLACE`s every unit's
  inventory into the shed and dumps it,
- a divergence counter that falls back if the board stops matching.

Worth stealing: the endgame liquidation and the front-running sell ranking. The
approach itself — offline-optimise a trajectory, replay it — is a credible route
to the top given the environment is near-deterministic apart from weed RNG, shop
draws, and the opponent.

---


---

## 5. How the leaderboard score is produced

There is no metric computed from a file. Your rating is an **outcome of playing
games**, and it moves entirely on win/loss/tie — the coin margin never enters.

### Live ladder (now until 2026-09-30)

1. **Validation episode.** Every submission first plays one game against a copy
   of itself. Crash or timeout → `Error`, and `kaggle competitions logs` gives
   you the traceback. Ours (`90791512`) passed.
2. **Join the pool at the default rating.** Observed: **600.0**. This is a
   starting placeholder, not a measurement.
3. **Continuous matchmaking.** The server pairs active submissions — the latest
   **2 per team** — against opponents of *similar* rating, forever. New
   submissions play far more often, which pulls their rating to its true level
   quickly.
4. **Update after each episode.** Win → up, loss → down, tie → the two ratings
   converge. The size of the move scales with the rating *gap*: beating someone
   far above you moves you a lot, beating someone far below barely registers.
   Kaggle does not publish the exact update rule; treat the displayed number as
   a conservative estimate of skill that rises as uncertainty shrinks.
5. **The leaderboard shows only your best active submission.** Track the others
   on the Submissions page.

Practical implication: **variance is punished**. Since only win/loss counts, an
agent that reliably banks 80k beats one that averages 100k but occasionally
collapses. Optimise the win rate against a real opponent, not the mean score in
a mirror-free sandbox.

### Final evaluation — the Bradley-Terry tournament

Confirmed by the host in [discussion
731587](https://www.kaggle.com/discussions/kaggriculture/731587): submissions
lock at the deadline, episodes keep running for ~2 weeks, and then a **single
Bradley-Terry tournament** over that match record produces the final leaderboard.

Bradley-Terry is a model for pairwise comparisons. Each agent gets one strength
parameter `p_i`, and

```
P(i beats j) = p_i / (p_i + p_j)
```

All strengths are fit **at once**, by maximum likelihood, over the entire set of
observed episodes. The contrast with the live ladder is the whole point:

| | Live ladder (Elo-style) | Bradley-Terry |
|---|---|---|
| Updates | sequential, one game at a time | one batch fit over all games |
| Order of games | changes the result | irrelevant |
| Hot streaks | inflate the rating | averaged away |

The host's stated reason is exactly this: *"this change reduces any 'hot streaks'
that may otherwise influence the final results."*

So the ladder rating you watch day to day is a **noisy progress indicator**. What
decides the prize is your aggregate head-to-head record over the final two weeks.
Consistency compounds; a lucky run does not.
