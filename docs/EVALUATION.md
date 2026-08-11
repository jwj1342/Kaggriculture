# How to evaluate an agent

> **The reference field must be able to lose to the candidate and beat it.**
> Measured on 2026-08-10 (run #22): every strategy in the library beat the old
> anchors — `berrybaron-muck`, `orchardherd`, the submitted `enhanced` — between
> **97% and 100%** of the time, while `marketgarden` beat every other roster
> shape 53% to 90%. Both ends were saturated, so the ranking carried no
> information: a 99.2% and a 100.0% are the same measurement.
>
> `python tools/registry.py gen --plan bench --out agents/bench3` materialises
> the current standard field — the strongest shape of each production family
> plus one deliberate outlier. Copy in `agents/ref/*.py` and
> `agents/lines/line1.py` afterwards. Use it for `--panel` and as the fixed
> opponent set in ablations, and regenerate it whenever a candidate starts
> beating it above ~90%.
>
> **Saturation has two ends.** `dairy` was dropped from the field on
> 2026-08-11 for the opposite reason to the anchors above: every candidate beat
> it in **every single episode** over 7,296 of them. See §6.
>
> **Four seeds cannot resolve anything.** Three separate changes on 2026-08-10
> read positive over four seeds and were 21 to 44 points *behind* over 2,304
> episodes an arm: a larger fertilizer reserve (+$6,500 → −44 points), the
> inverted scheduler (+$15,000 → −23 points), and a raised carrying threshold.
> A smoke test is a syntax check, not evidence.

The hardest part of this competition is not writing a policy. It is knowing
whether the policy you just wrote is better than the one before it.

Early sweeps in this repo, at 3–4 seeds, produced **contradictory orderings on
repeat runs**. Every number they produced was noise. This document is the
correction: what the environment's randomness actually looks like, what the
tools measure, and how many games it takes to be allowed an opinion.

---

## 1. What the ladder actually scores

Only **win / loss / tie**. The coin margin never enters the rating. The final
leaderboard is a single **Bradley-Terry** fit over the last two weeks of
episodes ([host confirmation](https://www.kaggle.com/discussions/kaggriculture/731587)).

Three consequences for local evaluation:

1. **Mean money is the wrong headline metric.** An agent that reliably banks 80k
   beats one averaging 100k that occasionally collapses. Optimise win rate;
   report money only as a diagnostic.
2. **Variance is a cost, not just an error bar.** Consistency is what the rating
   rewards.
3. **Rank locally with the same estimator the prize uses.** `tools/league.py`
   fits Bradley-Terry by maximum likelihood over a local round robin, so local
   rankings are comparable in kind to the real leaderboard rather than to a
   sandbox mean.

---

## 2. Measured facts about this environment's randomness

All verified against the installed 1.32.6 engine.

### 2.1 Episodes are deterministic given `(seed, both agents)`

Re-running the same pair on the same seed reproduces the episode exactly. So
**repeat runs of an identical configuration add no information** — all variance
lives across seeds. A harness that runs the same config twice on the same seed is
burning CPU.

Useful corollary: the league correctly scored `barnyard`,
`barnyard__TARGET_COWS_10` and `barnyard__HAND_CAP_14` as *bit-identical*
(same BT strength, same median, same win rate) because those overrides happen to
equal the defaults. That is a free self-test of the whole pipeline.

### 2.2 Common random numbers do **not** control the environment

This one is easy to get wrong. In `_end_of_day` a single RNG, seeded from
`(seed, day)`, is used for **both** weed spawning and the shop unlock — and weed
spawning consumes one draw per empty tile, on **both** farms:

```python
rng = random.Random((seed * 1_000_003) ^ day)
for player_id, farm in enumerate(obs0.farms):
    ...
    _spawn_weeds(farm, board_size, weed_chance, rng)   # draws ∝ empty tiles
...
town["unlocked_shops"].append(rng.choice(sorted(SHOPS)))
```

So **how you play changes which shops unlock**, and so does how your *opponent*
plays. Measured on one fixed seed (42), four agent pairings produced four
completely different shop sequences:

| Pairing | Shops unlocked |
|---|---|
| `pass` vs `pass` | FARMERS_MARKET, PET_CAFE, YARN_STORE, YARN_STORE, … |
| `starter` vs `starter` | ICE_CREAM_SHOP ×3, YARN_STORE, BAKERY, … |
| `barnyard` vs `starter` | ICE_CREAM_SHOP, PET_CAFE, FARMERS_MARKET, BAKERY, … |
| `barnyard` vs itself | BRUNCH_SPOT ×3, BAKERY, SMOOTHIE_SHOP, … |

Implications:

- Pairing on seed reduces variance but **does not cancel it**. You cannot treat
  the shop draw as an exogenous control variable.
- A config change can win a seed for a reason unrelated to its merit — it nudged
  the weed count and drew a better shop.
- **Results against a weak opponent do not transfer.** Changing the opponent
  changes your own economy, not just the comparison.

### 2.3 Scores compress by roughly half against a real opponent

| Matchup | `barnyard` median |
|---|---|
| vs `starter` | ~67,000 |
| vs itself, and in a mixed league | ~30,000–40,000 |

Both players drain one shared market. Any number measured against a passive
opponent is inflated; always report the contested number too.

### 2.4 Seats are symmetric by construction — but verify anyway

All four quadrants are geometrically identical about the shed, each owning one
shed-access tile, and market orders quote both players against the same
pre-commit inventory. There is no structural seat advantage. Every harness here
still plays both seats and reports the split, because that assumption is cheap to
check and expensive to be wrong about.

---

## 3. The tools

| Tool | Question it answers |
|---|---|
| `tools/arena.py` | quick sanity: does A beat B at all? |
| `tools/trace.py` | *why* — day-by-day farm, shed, prices for one episode |
| `tools/eval.py` | is A better than B, with a confidence interval? |
| `tools/league.py` | how do N agents rank, by Bradley-Terry? |
| `tools/stress.py` | does the agent ever crash, stall, or time out? |
| `tools/sweep.py` | coordinate sweep over module-level tunables |
| `tools/make_probes.py` | regenerate the single-strategy probe agents |

### `eval.py` — A/B with an interval

```bash
python tools/eval.py h2h agents/v2.py agents/barnyard.py --seeds 96 -j 32
python tools/eval.py pool agents/v2.py agents/barnyard.py \
    --vs starter --vs agents/barnyard.py --seeds 48 -j 32
```

Plays both seats, reports a Wilson interval on the win rate and a paired
bootstrap on the money margin, and — when the result is not resolved — prints how
many episodes it would take. `pool` mode is closer to the ladder: both candidates
face the same opponents on the same seeds.

### `league.py` — round robin with Bradley-Terry

```bash
sbatch slurm/league.sh starter agents/barnyard.py \
    --variants agents/barnyard.py:HAND_CAP=8,11,14 --seeds 24
```

Emits a win matrix, BT strengths on an Elo-like scale, and per-agent money
distributions. `--variants` stamps out tunable variants automatically so a
parameter study is one command.

Reading the output: **a high win rate with a low median money is a red flag**.
It means the agent wins by denying the shared market rather than by earning —
which does score on the ladder, but is fragile against opponents who do not feed
it.

### `stress.py` — 28 pathological configurations

Zero money, a 4×4 board, a shed that holds one item, one turn per day, free farm
hands, a market where everything crashes. Real episodes always use the defaults,
so this is not about realism: it is about finding hardcoded assumptions before
the leaderboard does. A crash forfeits the whole episode.

`barnyard` currently passes 28/28 with a worst turn of 145 ms against a
1,000 ms budget.

---

## 4. The probe agents

`agents/probes/` holds 19 deliberately bad agents, each committing to a single
mechanic and abandoning everything else. They exist to price a lever in
isolation, and as fixed yardsticks that do not move when the baseline changes.

| Group | Probes | Question |
|---|---|---|
| Monoculture crops | `mono_wheat` `mono_carrot` `mono_tomato` `mono_strawberry` `mono_melon` | what is each crop worth alone? |
| Monoculture animals | `mono_cow` `mono_sheep` `mono_goose` | which animal carries the engine? |
| Animal decomposition | `fert_only` `product_only` | how much of animal income is the free fertilizer? |
| Land | `one_quadrant` `two_quadrant` `four_quadrant` | what is a quadrant worth? |
| Labour | `no_hire` `few_hands` `hire_max` | what is a farm hand worth, and where does `fib(n)` bite? |
| Market | `dump_all` `hoarder` | does metered selling actually pay? |
| Reference | `mixed_ref` | the probe's own balanced default |

All 19 are generated by `tools/make_probes.py` from the single parameterised
`agents/probe.py`, so there is exactly one source of truth. Regenerate after
editing:

```bash
python tools/make_probes.py
```

They double as a regression suite: if a refactor changes what `mono_melon`
scores on a fixed seed, something moved that should not have.

---

## 5. How many games do you actually need?

For a binary win/loss outcome, resolving a true win rate of `50% + d` at 95%
confidence needs roughly `n = (1.96² × 0.25) / d²` episodes:

| Effect you want to detect | Episodes | Seeds (both seats) | Wall time on 32 cores |
|---|---|---|---|
| 10 points (60% vs 50%) | 96 | 48 | ~8 s |
| 5 points | 384 | 192 | ~33 s |
| 3 points | 1,068 | 534 | ~90 s |
| 1 point | 9,604 | 4,802 | ~14 min |

Throughput: one episode is ~2.7 s on one core, so 32 cores run **~11.8
episodes/s ≈ 42,000 episodes/hour**.

**There is no excuse for an underpowered experiment here.** A properly powered
5-point test costs 33 seconds of a compute node. The 3–4 seed sweeps that started
this project were resolving nothing at all.

Two ways to do better than raw win counting:

- **Use the money margin as the statistic.** In a head-to-head the margin's sign
  *is* the win, so it carries the same information with far lower variance.
  `eval.py` bootstraps it alongside the win rate.
- **Pair on seed.** Both candidates play the same seeds against the same
  opponents. This helps even though §2.2 means it does not cancel everything.

---

## 6. Recommended workflow

1. **Change one thing.** Prefer a module-level tunable so `sweep.py` and
   `league.py --variants` can drive it without editing code.
2. **`stress.py` first.** 28 configurations, under a minute, catches crashes and
   slow turns before you spend a compute node.
3. **`league.py` on Slurm** with the change as a variant plus 2–3 probes for
   context. 24 seeds is enough for a first look; 96+ before believing anything
   under 10 points.
4. **Read the win matrix, not just the ranking.** An agent that beats everything
   except one probe is telling you something specific.
5. **Check the mirror.** Run the candidate against itself. Scores halve; if they
   more than halve, the agent depends on a passive opponent.
6. **`trace.py` any surprise.** Silent no-ops mean bugs look like bad strategy —
   every five-figure bug in this repo was found by reading a day-by-day trace,
   not by staring at a final score.
7. **Measure on two fields, and say so when they disagree.** `agents/bench3` is
   our own family; `agents/ghosts` is 156 replayed ladder trajectories. They
   have now disagreed on the produce axis by seven places — `mgtightgrain2`
   ranks first on the ghosts and seventh on `bench3` — and only one of them is
   evidence about the ladder. A number quoted from one field alone is a number
   about that field.
8. **Only then submit.** Five per day, latest two active.

### Which opponents are worth the compute

An opponent's value is its **variance across candidates**, not its strength.
Measured over 7,296 episodes with ten candidates on one engine:

| sparring partner | mean beaten | spread across candidates |
|---|---|---|
| `mgtightgrain2` | 64.6% | **29.7** |
| `orchardherd` | 73.4% | **26.1** |
| `rancher_rita` | 92.4% | 22.7 |
| `mgtight` | 39.8% | 20.8 |
| `melon_mateo` | 94.3% | 17.0 |
| `closer_cleo` | 0.3% | 0.7 |
| `ledger_lena` | 0.2% | 0.5 |
| `broker_bea` | 0.2% | 0.4 |
| `dairy` | **100.0%** | **0.0** |

`orchardherd` is weak — 36.5% as a candidate — and the third most informative
opponent in the panel. **Weak and useless are different things.** `dairy` is the
useless one: every candidate beat it in every single episode, mean 100.0% and
standard deviation exactly zero. It is removed.

Dropping `dairy` and the three meta agents leaves the candidate ranking
**completely unchanged** — all ten hold their position — for 37% less compute.

But keep the meta agents in the field and **report them separately**. They are
saturated the other way (we win 0.2%), so averaging them in only adds a
constant: three unbeatable opponents in fifteen depress every headline by about
25 points, which is how "43%" turned out to mean "73.5% against opponents we can
contest, and 0% against three we cannot". Two numbers, not one.

What the panel lacked was the middle, and `tools/lines.py --emit` supplies it:
`line1` is the ladder's most-played line and sits at 66.6% against this panel,
just above our best engine's 60.9%.

### Saturation has two ends, and we just hit the far one

`dairy` was cut because every candidate beat it every time. On 2026-08-11 the
opposite happened: measuring eight variants of a `closer_cleo`-class agent, the
**ghost field returned 99.4% for seven of them** and could not separate any.
`bench3` is close behind — the same arms sit at 92-98% there.

Both reference fields are built to rank *our* engine, which wins 54-61% of them.
They have no resolution at the level of an agent that wins 98%.

The only field that still discriminates at that level is **the wrapped agents
against each other**: `closer_cleo` 92.7%, `slotter_silas` 73.8%, `ledger_lena`
54.1%, `broker_bea` 29.3% over 3,072 episodes — clean spacing, no saturation at
either end. Use that panel for anything at this level, and read money as a
secondary signal when win rate saturates (it still ordered the terminal-window
sweep correctly when the ghost win rates were all identical).

### Two failure modes this repo keeps producing

**"It is doing nothing, so it must be stuck."** The seed-purchase probe showed
the farm buying nothing for ten days on $109-$435. It was not stuck; it was
spending the cash on livestock, which is worth more. Removing the "deadlock"
cost 8-14 points across 137,664 episodes. *Before concluding an engine is
broken, find out what it spent the resource on.* Nothing in the code says
"livestock outranks seed" — it falls out of a cash floor meeting a purchase
rate limit, and correct behaviour with no comment attached looks exactly like a
bug.

**A harness that silently runs the wrong code.** `get_last_callable` returns
`[v for v in env.values() if callable(v)][-1]` — the last *callable* in the
module dict. Wrapping an agent (`_INNER = agent`, then a new `def agent`) leaves
`_INNER` last, so the framework loads the **unwrapped** agent, every arm scores
identically, and the clean-looking conclusion is "the change is worth nothing".
A helper `def` placed after `agent` does the same. Park callables in lists,
`del` helper names, and *verify by asking the loaded function for a known
answer* — compiling is not enough. Two arms of this session's handover sweep
were lost to this before the check existed.

---

## 7. Results on record

### Tunable study — 8 agents, 24 seeds/pair, both seats (1,344 episodes)

```
 #  agent                        BT-Elo   winrate   median $
 1  barnyard  HAND_CAP=11       +142     79.5%     40,458
 2  barnyard (defaults)          +69     72.0%     39,247
 3  barnyard  TARGET_COWS=10     +69     72.0%     39,247   (== defaults)
 4  barnyard  HAND_CAP=14        +69     72.0%     39,247   (== defaults)
 5  barnyard  TARGET_COWS=14    -115     53.0%     36,525
 6  barnyard  TARGET_COWS=6     -392     30.1%     31,530
 7  barnyard  HAND_CAP=8        -534     21.4%     32,327
 8  starter                       -4814      0.0%      3,498
```

`HAND_CAP=11` beats the current default of 14 — the payroll curve bites earlier
than the coordinate sweep suggested. `TARGET_COWS=10` is confirmed correct.


### Probe league — 21 agents, 16 seeds/pair, both seats (6,720 episodes)

```
 #  agent              BT-Elo  winrate   median $      sd $
 1  one_quadrant         +952    97.2%     54,784    21,285
 2  dump_all             +727    90.8%     39,810    13,298
 3  barnyard          +619    86.6%     47,880    16,383
 4  few_hands            +535    82.8%     36,476     9,853
 5  two_quadrant         +471    79.7%     40,890    16,001
 6  mixed_ref            +304    70.8%     34,497    14,723
 7  four_quadrant        +284    69.7%     31,746    14,449
 8  mono_cow             +185    63.9%     25,098    26,032
 9  mono_sheep            +76    57.3%     14,138    22,206
10  mono_goose            +26    54.4%     16,858     3,566
11  hoarder                +0    52.8%     21,912    13,285
12  hire_max              -56    49.5%     13,160     6,613
13  no_hire              -160    43.8%     13,118     4,144
14  mono_strawberry      -302    36.7%     15,482     4,783
15  fert_only            -405    32.3%      8,409     5,854
16  mono_melon           -492    29.1%     10,667     5,111
17  mono_wheat           -748    21.9%      7,578     2,125
18  starter             -1269    11.9%      3,492        68
19  mono_carrot         -1359     9.8%      2,626     1,521
20  mono_tomato         -1394     9.1%      2,791     1,772
21  product_only        -4289     0.0%         78         2
```

Four results worth acting on:

**Land is actively harmful, monotonically.** Within the identical probe family:
`one_quadrant` +952 > `two_quadrant` +471 > `mixed_ref` (three) +304 >
`four_quadrant` +284. `one_quadrant` beats `barnyard` **32/32** while earning
*more* (46,163 vs 35,056). Extra tiles dilute a fixed labour pool across cheap
work. This contradicts the public meta's three-quadrant farm — but that meta was
measured before the 1.32.6 rebalance halved late-game town demand.

**Fertilizer is the animal economy, not a side effect.** `product_only` (animals
harvested for milk but fertilizer never collected) finishes dead last on **$78**,
having gone broke buying feed before the first milk arrives. `fert_only` at
$8,409 is far from great, but it survives. Fertilizer is the early cash flow that
funds the herd.

**Metering is not unconditionally correct.** `dump_all` ranks *above*
`barnyard` while earning 17% less. See `docs/ADVERSARIAL.md`.

**`mono_sheep` has sd $22,206 on a median of $14,138** — larger spread than
median. Wool's only demand is a single-product shop consuming at 2x, so the
result is dominated by whether a Yarn Store happens to spawn. Any strategy
resting on one product is a coin flip under with-replacement shop draws.

### Powered A/B tests — 192 seeds x 2 seats = 384 episodes each

```
dump_all      vs barnyard   71.4% win  CI [66.6%, 75.6%]  own median 35,776
one_quadrant  vs barnyard   93.2% win  CI [90.3%, 95.3%]  own median 47,655
```

Both seat splits are flat (72/70 and 93/93), so neither is a seat artefact.
`dump_all` wins 71% of the time while earning ~25% *less* than it would by
metering — see `docs/ADVERSARIAL.md`. `one_quadrant` wins 93% while earning
*more*, which makes the three-quadrant plan in `barnyard` the single largest
known defect.

### Quadrant study — 8 seeds

| Quadrants owned | Median money |
|---|---|
| 1 | 49,078 |
| 2 | 68,738 |
| 3 | 68,892 |
| 4 | 68,892 (never actually buys SE) |

### Robustness — 28 pathological configurations

28/28 finish `DONE`. Worst single turn 145 ms. Most fragile dimension: with
melon's base price set to $1 the agent falls from 66,409 to 18,060.

---

## 8. Throughput reference

| Setup | Episodes/hour | Notes |
|---|---|---|
| login node, 1 core | ~1,300 | fine for a smoke test; nothing more |
| login node, `-j 8` | ~10,600 | acceptable up to a few hundred episodes |
| `sbatch`, 32 cores | **~42,000** | the default for anything that will be believed |

A 21-agent probe round robin at 16 seeds per pair is 6,720 episodes — about
10 minutes on one 32-core node. A properly powered 5-point A/B is 33 seconds.
Use the cluster.

```bash
sbatch slurm/league.sh <agents...> --seeds 24 -o logs/run.json
sbatch slurm/eval.sh h2h agents/v2.py agents/barnyard.py --seeds 192
sbatch slurm/sweep.sh agents/barnyard.py --set HAND_CAP=8,10,12,14
```

All three are CPU-only. Do not request a GPU.
