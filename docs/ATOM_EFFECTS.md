# What each atom is worth

Measured on the 594-strategy library. Screening run **#1**: every strategy against
a six-anchor panel, 8 seeds per pairing, both seats — **56,944 episodes**. All
figures below are win rate against that panel unless stated; median $ is the
strategy's own end-of-season money.

Everything is stored in `data/arena.sqlite` and can be re-derived with a query.

---

## A methodological warning that changes the numbers

**Main effects across an unbalanced design are confounded, and the confound here
is large.** The composition plans do not sample the axes evenly: `orchardherd`
appears in 256 strategies because the 512-strategy `grid` crosses it with every
land, labour, market and intel option — including `solo`, `swarm` and `vault`,
which are terrible. `dairy` appears in only 10, all of them paired with `crew`
and a sane market.

Averaging naively makes `dairy` (51%) look better than `orchardherd` (36%). On a
**balanced** slice — same labour, same intel, same muck, evenly crossed over land
and market — the order reverses:

| produce | win rate | median $ |
|---|---|---|
| `orchardherd` | **96.5%** | 56,974 |
| `ranchmix` | 91.2% | 51,109 |
| `dairy` | 79.0% | **62,592** |
| `mixedfarm` | 70.1% | 43,418 |
| `berryherd` | 37.8% | 42,362 |
| `woolworks` | 35.2% | 13,784 |
| `henhouse` | 28.8% | 20,452 |
| `melonrush` | 17.0% | 12,987 |
| `berrypatch` | 16.7% | 17,855 |
| `graingrind` | 16.7% | 8,987 |
| `vinehouse` | 16.7% | 5,514 |
| `rootcellar` | 14.8% | 4,262 |

*(n = 6 per row: land ∈ {homestead, estate} × market ∈ {metered, flood, adaptive},
with labour=crew, intel=blind, muck=muck.)*

Every figure below is from a balanced slice or a strictly paired ablation.
The unbalanced numbers are in `docs/LEADERBOARD.md` and on the published page, which
is why that page labels the sample size beside each option.

---

## 1. `labour` dominates everything else

| labour | win rate |
|---|---|
| `crew` (11 hands, 6% of cash) | **55%** |
| `lean` (4 hands) | 33% |
| `solo` (0 hands) | 17% |
| `swarm` (30 hands, unlimited budget) | **10%** |

**`swarm` is worse than `solo`.** Hiring without a payroll cap is more damaging
than never hiring at all — the n-th hire costs `fib(n)`, so an unbounded hire
loop burns the bankroll faster than the extra actions can earn it back. This is
the single largest effect in the library, and it is a cliff rather than a slope.

## 2. `land` matters, but an order of magnitude less

Balanced within the `grid` slice, so land is evenly crossed with everything:

| labour | homestead (1) | smallhold (2) | estate (3) | latifundium (4) |
|---|---|---|---|---|
| `crew` | **75%** | **75%** | 66% | 64% |
| `lean` | 33% | 33% | 32% | 32% |
| `solo` | 17% | 17% | 17% | 17% |
| `swarm` | 11% | 10% | 10% | 10% |

One or two quadrants beat three or four by ~10 points *when there are hands to
work them*, and land makes no difference at all without them. Compare that to the
65-point spread on the labour axis. The public meta's three-quadrant farm is not
wrong so much as second-order.

## 3. `muck` — fertilizer is the animal economy's cash flow

Strictly paired: only the muck axis changes, everything else identical.

| produce | `muck` | `nomuck` | `dung` (fertilizer only) |
|---|---|---|---|
| `dairy` | 79% / $61,710 | **0% / $79** | 17% / $4,645 |
| `woolworks` | 40% / $15,460 | **0% / $75** | 17% / $8,302 |
| `henhouse` | 28% / $21,438 | **0% / $42** | 23% / $2,533 |
| `ranchmix` | 96% / $50,734 | **0% / $79** | 17% / $10,380 |
| `mixedfarm` | 81% / $47,123 | **41% / $44,082** | 31% / $25,458 |

An animal-only farm that never collects fertilizer ends the season on **$79** —
it goes bankrupt buying feed before the first milk arrives on day 8. But
`mixedfarm`, which has crop income, survives `nomuck` at $44k.

So the mechanism is specific: **fertilizer is not a bonus, it is the bridge
financing.** It is the only animal income available before day 8, and every
animal produces one unit a day for free whether fed or not. Remove it and a pure
herd cannot reach its own payback date.

`dung` — collect the fertilizer, never harvest a product — is bad but survives,
which brackets the other half of the split.

## 4. `market` — dumping beats metering, conditionally

Balanced, labour=crew:

| market | win rate | median $ |
|---|---|---|
| `flood` (sell everything on sight) | **83.4%** | 54,133 |
| `adaptive` (mirror the opponent) | 77.4% | 55,620 |
| `metered` (hold below a price floor) | 77.0% | 55,598 |
| `vault` (hold to the buzzer) | 42.0% | 37,062 |

`flood` **earns slightly less** than `metered` ($54,133 vs $55,598) and **wins
more often** — the denial signature. Strictly paired, it is config-dependent:

| configuration | metered | flood | vault | adaptive |
|---|---|---|---|---|
| `homestead-crew-orchardherd-blind` | 92% | **100%** | 75% | 96% |
| `estate-crew-orchardherd-blind` | 94% | **99%** | 34% | 99% |
| `smallhold-crew-mixedfarm-blind` | 84% | **90%** | 26% | 86% |
| `estate-crew-mixedfarm-blind` | **82%** | 67% | 60% | 48% |

Three of four favour flooding; the fourth reverses it. That is the
non-transitivity documented in `docs/ADVERSARIAL.md` showing up as an
interaction, not noise. `vault` is the only unambiguous verdict: never hoard.

## 5. `intel` — a negative result

Balanced, labour=crew:

| intel | win rate | median $ |
|---|---|---|
| `spite` (flood once clearly behind) | **78.2%** | 48,966 |
| `blind` (ignore the opponent) | 72.8% | 48,561 |
| `frontrun` (sell into their imminent harvests) | 69.4% | 47,352 |
| `evade` (produce what they do not) | 59.5% | 43,968 |

**`frontrun` as implemented is worse than ignoring the opponent.** Strictly
paired on the one configuration with room to move
(`estate-crew-mixedfarm-metered`): blind 82%, spite 59%, frontrun 38%, evade 31%.

An earlier legacy comparison had `frontrun` beating its own skeleton 96% — that
result was confounded by a differing hand cap and does not survive a clean test.
Recorded here so it is not re-litigated.

`evade` is consistently bad, which reinforces the pool argument: the uncontested
pool is uncontested because it is worth less. Contest the rich one.

`spite` is the only opponent-aware atom that pays, and it pays for a scoring
reason rather than an economic one — margin never enters the rating, so a
trailing agent has nothing left to protect.

---

## What this says to build

1. **Get the payroll right first.** It is worth more than every other axis
   combined, and the failure mode (`swarm`) is worse than not hiring.
2. **One or two quadrants**, not three or four.
3. **Never skip the fertilizer.** For a herd it is not optimisation, it is
   solvency.
4. **`orchardherd` is the production shape to beat** — melon for the opening,
   cows and sheep for the engine, no strawberry and no wheat.
5. **Do not hoard.** Beyond that, sale sizing should be conditional rather than
   fixed, because flood-vs-meter flips with configuration.
6. **Drop `frontrun` and `evade`** in their current form, or rewrite them. Keep
   `spite`.

---

*Regenerate any of this from the database:*

```bash
python tools/db.py top --run 1 -n 40
python tools/leaderboard.py --run latest
sqlite3 data/arena.sqlite "SELECT ..."
```

---

## Confirm run #2 — 38 representative strategies, full round robin

20 seeds per pairing, both seats, **28,120 episodes**. The roster is the panel's
top 8, the best carrier of every atom option, all eight boundary corners, plus
`barnyard` (the agent on the ladder) and `starter`.

```
 #   BT-Elo  win%   median $   strategy
 1    +1961  99.2%    65,167   homestead-crew-orchardherd-flood-evade-muck
 2    +1566  94.3%    63,108   homestead-crew-orchardherd-flood-blind-muck
 3    +1566  94.3%    63,108   homestead-crew-orchardherd-flood-frontrun-muck
 4    +1566  94.3%    63,108   homestead-crew-orchardherd-flood-spite-muck
 5    +1169  87.8%    62,753   homestead-crew-orchardherd-adaptive-evade-muck
 6    +1029  85.0%    62,642   homestead-crew-orchardherd-metered-evade-muck
 7     +922  82.6%    59,773   homestead-crew-orchardherd-adaptive-spite-muck
 8     +748  78.0%    58,716   estate-crew-orchardherd-adaptive-blind-muck
 9     +748  78.0%    58,716   latifundium-crew-orchardherd-adaptive-blind-muck
10     +748  78.0%    58,716   smallhold-crew-orchardherd-adaptive-blind-muck
11     +479  69.9%    48,094   smallhold-crew-mixedfarm-flood-blind-muck
12     +445  68.8%    52,572   homestead-crew-orchardherd-vault-spite-muck
13     +385  66.7%    46,129   homestead-crew-ranchmix-flood-blind-muck
14     +288  63.1%    44,242   barnyard                    <- the ladder agent
15     +184  59.0%    36,304   estate-crew-dairy-adaptive-blind-muck
16     +164  58.2%    51,654   estate-crew-berryherd-flood-blind-muck
17     +104  55.7%    39,352   estate-crew-mixedfarm-metered-blind-muck
...
25     -435  33.6%    16,156   estate-swarm-mixedfarm-adaptive-blind-muck
27     -486  31.7%    16,566   latifundium-swarm-mixedfarm-flood-spite-muck
29     -759  22.4%     9,418   estate-solo-mixedfarm-adaptive-blind-muck
```

**`barnyard`, our submitted agent, ranks 14th of 38** — beaten by every
`orchardherd` composition. The gap is ~21,000 in median money and 36 points of
win rate against the same field.

**Ranks 2–4 and 8–10 are exact ties.** In those groups the differing atom never
fires: `intel` only changes behaviour when the opponent's board crosses a
threshold, and `land` beyond the first quadrant is never bought when
`crop_room <= 8` never trips. Identical scores are a correctness signal, not a
tie-break failure — the pipeline is deterministic and those really are the same
policy.

### Ranking is field-dependent

Compare the two runs' atom effects, on the same strategies:

| axis | screen (panel, 594) | confirm (round robin, 38) |
|---|---|---|
| land | smallhold +707 / estate +630 | smallhold +613 / **estate −484** |
| labour | crew +1586 / swarm −840 | crew +173 / **solo −894** |
| produce | berryherd +1603 | **orchardherd +1047 / ranchmix −1273** |
| market | flood +812 / metered +567 | flood +479 / **metered −547** |
| intel | frontrun +736 | **frontrun +1566 / blind −286** |
| muck | muck +711 / nomuck −1217 | muck +166 / nomuck −1508 |

`ranchmix` goes from second-best to worst; `frontrun` from marginal to top. Both
rosters are honest measurements — they are measuring *different fields*. This is
the non-transitivity in `docs/ADVERSARIAL.md` at library scale, and it is the
main reason to treat any single ranking as provisional.

---

## Defects found by mining the stored episodes

The digest exists so questions like these can be asked after the fact.

**Livestock starve in the opening.** Across 104,384 player-episodes, 44–66% of
purchased animals were absent from the final board. Some of that is the
deliberate day-28 liquidation, so a day-by-day trace was needed to separate the
two. Tracing `estate-crew-orchardherd-adaptive-blind-muck` on seed 30001:

```
day  alive  empty pens  bought
  0      4           0       4
  2      2           2       5   <- two starved
  3      1           3       5   <- three starved
  ...    1           3       5   <- stalled for seven days
 11      4          14      10   <- melon harvest funds the recovery
 14     17           1      22
```

The opening buys animals it cannot feed — cash is $211 by day 5 — so they starve
before producing anything, and the farm then idles with empty pens until the
melon harvest lands on day 11. Roughly $1,200 of animals plus ten days of
production, in every episode.

**Melon is oversold 21% of the time.** Median melon sales are 126 units against a
158-unit price floor, but the 90th percentile is 168 and the maximum 368. One
episode in five keeps selling melon after the price has bottomed at $1.

**~~Hire orders swamp the market queue.~~ RETRACTED.** This claimed a `crew`
strategy issues ~241 `HIRE` orders it cannot pay for, each wasting one of the ten
market slots. Measured directly, both `barnyard` and the enhanced baseline hire
at a **100% success rate** (279/279 and 266/266). The claim was lifted from a
public meta write-up describing *other players* and never checked against ours.

*Digest schema has since been extended with per-day herd and hand counts so the
starvation question can be answered by query rather than by re-tracing.*
