# Can you win by suppressing the opponent?

> **Provenance.** The agents named below (`agents/adversary.py`, `agents/adv/*`,
> `agents/probes/*`) were hand-written for this study, were never committed —
> `agents/` is git-ignored — and no longer exist on disk. The conclusion is the
> artefact; the episodes behind it are in `data/arena.sqlite`. Nothing here needs
> rerunning, because the answer is **no** and the reason is structural (§1). If
> you want to reproduce it, the agents are three dozen lines each and §5
> describes what each one does.

The idea: since the ladder scores **win/loss only** and never the margin, an
agent does not need to be rich — it only needs to be richer. So could an agent
default to doing nothing and act purely to hold the opponent down?

This document works out which channels the engine actually provides, then
measures whether they win.

---

## 1. There is exactly one channel

The two farms are fully separate. You cannot reach their tiles, animals, shed,
seeds or hands. There is no attack action, no sabotage, no stealing. The only
shared object in the entire environment is **the market** — one inventory and one
price vector for both players.

So "suppression" can only mean moving a price against them. Three ways to try:

### 1.1 Corner the feed market — blocked by the shed cap

`WHEAT` and `FERTILIZER` are the only products a player can *buy*. Buying drains
market inventory, which drives the price **up** — and wheat is what every animal
eats. Cost to push wheat up, computed from the engine's curve:

| Target price | Units you must buy | Cost |
|---|---|---|
| $35 | 90 | $2,820 |
| $50 | 600 | $24,800 |
| $80 | 2,970 | $182,160 |
| $150 | 15,500 | $1,674,000 |

But **`shedCapacity` is 100 items**, and bought goods land in the shed. You
cannot hold more than 100 wheat, so you cannot hold the price above roughly $35.
To buy more you must first sell some back — which returns the price to where it
started. The attack is capped at a ~$10/unit tax on their feed, for ~$3,000 of
tied-up capital and your entire shed.

### 1.2 Free price manipulation — the engine explicitly prevents it

Verified against the engine: a buy immediately followed by a sell of the same
item nets **exactly $0** and leaves inventory unchanged. This is deliberate —
`_commit_unit` quotes buys at *post*-buy inventory and sells at *pre*-sell
inventory. There is no costless way to move a price.

### 1.3 Crash the pools — this one works, but it is not free

Every product's price collapses to the $1 floor after a finite number of units:

| Product | Units to floor | Total revenue on the way down |
|---|---|---|
| Strawberry | 62 | $3,809 |
| Wool | 59 | $7,928 |
| Milk | 76 | $6,181 |
| Melon | 158 | $26,485 |
| Tomato | 529 | $11,128 |
| Carrot | 842 | $10,680 |

Selling into a pool requires **producing the goods**, which costs exactly what it
costs the opponent. But note the third column: you are *paid* on the way down.

**This is the key structural fact of the game.** The pools are finite and shared,
so selling into one first is simultaneously earning it and denying it. Denial and
profit are not a trade-off — they are the same action. "Take the melon pool early"
and "deny the opponent $26k of melon" describe one move.

---

## 2. Pure denial is mechanically impossible

An agent that does not produce has nothing to sell, and therefore cannot move any
price. `agents/adv/parasite.py` is the control: minimal self-investment (one
quadrant, four hands, fastest-cycle crop), never meters, exists only to dump.

Over an 8-agent league — 1,344 episodes, 24 seeds per pair, both seats — it
finished **0 wins from 168 games**, last of eight, at −4,552 BT-Elo.

It is worse than that. Look at what its opponents scored:

| Opponent | Score **against `parasite`** | Their normal median |
|---|---|---|
| `barnyard` | **67,312** | 40,800 |
| `dump_all` | **53,182** | 33,150 |
| `mixed_ref` | **45,703** | 21,809 |

**The pure suppressor did not merely fail to suppress — it made every opponent
richer than they are against a normal opponent, by 30–110%.** By declining to
produce, it left every pool uncontested and handed the whole market over.

That is the cleanest possible refutation. In a shared finite market, *not
competing for a pool is the opposite of denying it*. Denial is not a separate
activity you can specialise in; it is a by-product of taking the goods yourself.

Also worth stating plainly: doing nothing ends the season on the $3,000 you
started with, and even the built-in `starter` finishes above that. Passivity
loses unaided.

---

## 3. Partial denial does work — and it beats metering

The interesting case is not "produce nothing", it is "produce normally but stop
protecting your own price". That is the `dump_all` probe: identical to the
metered reference in every way except that it sells everything on sight.

From the 21-agent probe league (6,720 episodes, 16 seeds per pair, both seats):

```
 #  agent          BT-Elo  winrate   median $
 2  dump_all         +727    90.8%     39,810
 3  barnyard      +619    86.6%     47,880
```

**`dump_all` ranks above `barnyard` while earning 17% less money.**

Confirmed at full statistical power — 192 seeds x 2 seats = **384 episodes**:

```
A = agents/probes/dump_all.py      B = agents/barnyard.py
  games      384   (274W 110L 0T)
  win rate    71.4%   95% CI [66.6%, 75.6%]
  margin           +4,444   95% CI [+3,770, +5,146]
  own money  median 35,776    (baseline's usual median is 47,880)
  as player 0: 72%   as player 1: 70%
```

**A 71% win rate while earning roughly 25% less than it would by metering.** The
seat split is flat, so this is not a seat artefact. `dump_all` drags both scores
down and drags the opponent's down further.

### But the strategy space is non-transitive

The same league produced a clean rock-paper-scissors cycle (48 episodes per
pairing, both seats):

```
dump_all     beats  barnyard   67%     (33,979 vs 29,634)
spite        beats  dump_all      56%     (20,038 vs 20,518)
barnyard  beats  spite        100%     (37,092 vs 24,002)
```

So `barnyard` still tops that league's Bradley-Terry table at +491 despite
losing its head-to-head with `dump_all` — it beats everything else by more. BT is
a global fit, and with a non-transitive field the ranking depends on who else is
in the pool.

Two consequences:

* **A local league rank is only meaningful relative to its roster.** Beating your
  own previous agent proves little if the ladder is full of a third type.
* **The ladder rating you get depends on the field composition**, which drifts.
  An agent that adapts its selling policy to the opponent in front of it is
  strictly better positioned than one that commits to a point on the cycle.

### Why the dumping asymmetry exists

A metering agent holds inventory waiting for a price that a dumper never lets
recover. Two things then punish the meterer:

1. The dumper was **paid** on the way down — it captured the pool's revenue.
2. The meterer's held stock is worth $1 when it finally sells, and the 100-slot
   shed forces it out eventually anyway.

So metering is only correct if the opponent also meters. Against a dumper it is
strictly worse. This has the shape of a prisoner's dilemma: mutual patience is
jointly best, but "sell now" dominates whenever the opponent might sell now.

**The public advice to "sell in small metered batches" is conditional, and nobody
says so.** It is correct in a field of meterers and wrong in a field of dumpers.

---

### Opponent-awareness measures well; avoidance does not

Against `mixed_ref` — the same skeleton with no opponent model — over 48 episodes:

| Variant | vs `mixed_ref` |
|---|---|
| `frontrun` (sell into their imminent harvests) | **96%** |
| `spite` (frontrun while ahead, parasite while behind) | **96%** |
| `avoid` (produce what they are not producing) | **0%** |

Reading the model is worth a great deal; *avoiding* them is worth nothing.
`avoid` steers into whichever pool is uncontested, which is uncontested precisely
because it is low-value. Contesting a rich pool beats owning a poor one outright.

(Caveat: `frontrun`/`spite` also run `HAND_CAP=11` against `mixed_ref`'s 12, so a
small part of that 96% is the tunable, not the opponent model. The direction is
not in doubt at that margin, but a clean single-variable test is still owed.)

---

## 4. What to actually build

Not a pure suppressor. The measurements point at four things, roughly in order of
value:

1. **Take contested pools first.** Melon (~158 units, no shop demand, shared) and
   the premium goods (~60-76 units) are races, not harvests. Earliness is the
   whole game there.
2. **Meter conditionally.** Track the opponent's realised sell rate from market
   inventory deltas — inventory is shared and visible, town consumption is
   deterministic, so subtracting our own fills recovers *exactly what they sold
   each turn*. Meter against a meterer, dump against a dumper.
3. **Front-run their harvests.** Their board is fully public, including every
   animal's `yield_units`, `fed_today` and `pending_care_bonus`, and every
   plant's `planted_day`. Their harvest schedule is computable several days out.
4. **Trade the uncontested pool.** If they have committed to wool, take milk. A
   pool you have to yourself pays base price; a contested one pays the floor.

And one genuinely spite-shaped policy, which is correct *because* margin does not
score:

5. **Switch on the scoreboard.** While ahead, protect prices and bank the lead.
   While clearly behind late, there is nothing left to protect — maximise denial
   and variance, because losing by $1 and losing by $100k score the same.
   Implemented as `MODE="spite"` in `agents/adversary.py`.

---

## 5. Files

| File | What it is |
|---|---|
| `agents/adversary.py` | opponent-conditioned agent; `MODE` selects the strategy |
| `agents/adv/frontrun.py` | sells hard into products the opponent is about to harvest |
| `agents/adv/avoid.py` | steers production away from what the opponent produces |
| `agents/adv/parasite.py` | the pure-denial control; expected to lose |
| `agents/adv/spite.py` | plays normally while ahead, parasite while behind |
| `agents/probes/dump_all.py` | never meters — the partial-denial probe |
| `agents/probes/hoarder.py` | the opposite extreme; finishes 0/32 against baseline |

`_opponent_model()` in `agents/adversary.py` is the reusable piece: it turns the
opponent's public board into `ready` / `imminent` / `capacity` per product.
