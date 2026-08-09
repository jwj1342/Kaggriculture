# The strategy library

Every strategy in this project is an assignment of one option to each of six
**orthogonal atoms**. There are no hand-written one-off agents and no version
numbers — a strategy's name *is* its definition.

```
land - labour - produce - market - intel - muck

estate-crew-mixedfarm-metered-blind-muck
```

Because the axes are independent, the library is a cross product rather than a
pile of files: **9,216 strategies** are expressible, of which the standing plan
materialises 594.

- `agents/_engine.py` — the single execution path, with a generated `CONFIG` block
- `tools/registry.py` — atom definitions, composition plans, code generation
- `agents/lib/` — generated strategies plus `manifest.json`

Regenerate the whole library after editing the engine or the atoms:

```bash
python tools/registry.py list          # inspect the space
python tools/registry.py gen --plan all --out agents/lib
```

Every generated file is standalone and submittable as-is: the `agent` function is
the last callable at module level, as `get_last_callable` requires.

---

## The six atoms

### `land` — how much of the board to own

| Option | Quadrants | Cost | Note |
|---|---|---|---|
| `homestead` | 1 (NW) | $0 | never buys |
| `smallhold` | 2 (+NE) | $1,000 | |
| `estate` | 3 (+SW) | $3,000 | the public meta's footprint |
| `latifundium` | 4 (+SE) | $7,000 | nobody on the ladder does this |

Purchase order is fixed by the engine (NE → SW → SE) and SE alone is 57% of the
total. Measured: melon saturates its market at ~14 tiles and animals at ~23, so
the high-value work fits inside two quadrants; beyond that, extra tiles add cheap
tasks that starve expensive ones.

### `labour` — how many hands per day

| Option | Cap | Payroll budget | Note |
|---|---|---|---|
| `solo` | 0 | — | the main farmer alone, 24 actions/day |
| `lean` | 4 | 6% of cash | |
| `crew` | 11 | 6% of cash | |
| `swarm` | 30 | 100% of cash | hires until broke |

The n-th hire of a day costs `fib(n)`: 1, 1, 2, 3, 5, 8, 13, 21… Eight hands cost
less than one melon seed; the 17th alone costs more than the first fifteen
combined. `swarm` exists to locate that cliff empirically, not because it is
sensible.

### `produce` — what the farm makes

Five monocultures (isolate one crop), three single-species herds (isolate one
animal), and four blends.

| Option | Crops | Animals |
|---|---|---|
| `melonrush` | melon ×40 | — |
| `berrypatch` | strawberry ×40 | — |
| `graingrind` | wheat ×40 | — |
| `rootcellar` | carrot ×40 | — |
| `vinehouse` | tomato ×40 | — |
| `dairy` | — | 24 cows |
| `woolworks` | — | 24 sheep |
| `henhouse` | — | 24 geese |
| `ranchmix` | — | 10 cow + 8 sheep + 6 goose |
| `mixedfarm` | melon 14 + strawberry 14 + wheat 20 | 10 + 8 + 6 |
| `orchardherd` | melon 14 | 10 cow + 8 sheep |
| `berryherd` | strawberry 16 | 10 cow + 8 sheep |

Three more are not designed but **reconstructed from real ladder opponents**
(`docs/LADDER_FIELD.md`), so the field contains the shapes that actually beat us
rather than only the shapes we thought of:

| Option | Crops | Animals | Read off |
|---|---|---|---|
| `berrybaron` | strawberry 24 + melon 10 | 8 cow + 6 sheep | the opponent that finished on $171,062 |
| `grazier` | wheat 8 + melon 4 | 14 cow | the cow-heavy archetype |
| `marketgarden` | strawberry 18 + melon 10 | 8 cow + 3 sheep | the balanced one |

Each crop entry also carries the last day it can still be planted and finish —
melon needs 10 days to ripen, strawberry 16 to fire all four yields — so a plan
stops planting rather than wasting tiles on crops that cannot mature. The
reconstructed atoms replant strawberry until **day 19**, not 13: a plant sown on
19 still catches one production tick on 29, and stopping at 13 leaves the tile
idle for the last twelve days.

### `market` — how sale sizing reacts to price

| Option | Behaviour |
|---|---|
| `metered` | hold below 55% of base price; sell ≤8/turn |
| `flood` | sell everything on sight, no floor |
| `vault` | hold everything until the day-28 liquidation |
| `adaptive` | infer the opponent's sell rate and mirror it |

`adaptive` is the only one that needs memory. Market inventory is shared and
visible, and town consumption is deterministic given `unlocked_shops`, so
subtracting our own fills from the inventory delta recovers **what the opponent
sold each turn**. Above ~0.9 units/turn they are dumping, and metering against a
dumper is strictly worse (see `docs/ADVERSARIAL.md`).

### `intel` — whether the opponent's board changes behaviour

| Option | Behaviour |
|---|---|
| `blind` | ignores the opponent entirely |
| `frontrun` | bigger batches and a lower floor on products they are about to harvest |
| `evade` | reorders the crop and herd plan away from what they are producing |
| `spite` | plays normally while ahead; floods once clearly behind after day 12 |

`spite` is justified by the scoring rule rather than by economics: margin never
enters the rating, so a trailing agent has nothing left to protect.

### `muck` — the free daily fertilizer

| Option | Collect fertilizer | Harvest animal products | Spend it on crops |
|---|---|---|---|
| `muck` | yes | yes | no — sell it |
| `nomuck` | no | yes | — |
| `dung` | yes | **no** | no — sell it |
| `compost` | yes | yes | **yes** |

Every surviving animal produces one fertilizer per day whether fed or not, and
no shop or the town centre ever consumes fertilizer — its price only falls, so
*selling* it is a race to the floor. Measured on the ladder, ours closes the
season at **$8 against a $100 base**. `nomuck` and `dung` split the animal
economy in half to price each side.

`compost` spends it instead, and on an `ongoing` crop that is the largest
multiplier in the game. Each production tick adds `2 if (watered and fertilized)
else 1`, so a fertilized strawberry yields **8 units per planting instead of 4**;
one `FERTILIZE` covers three days, more than one strawberry tick. On a
non-ongoing crop it adds no units — the cap is the cap — but each watering counts
double, so a fertilized melon needs three waterings instead of five.

No strategy in this library issued a `FERTILIZE` before run #7, which is why
every strawberry and tomato plan here had been measured at exactly half its
ceiling. See `docs/LADDER_FIELD.md`.

---

## Boundary cases

`plan_edge` materialises the corners deliberately. These are not meant to be
good; they are meant to bracket the space so every other result has a scale.

| Corner | Strategy | What it tests |
|---|---|---|
| do nothing well | `homestead-solo-graingrind-vault-blind-nomuck` | the floor: minimal everything |
| do everything | `latifundium-swarm-mixedfarm-flood-spite-muck` | whether maximalism ever pays |
| land without labour | `latifundium-solo-mixedfarm-metered-blind-muck` | 100 tiles, 24 actions/day |
| labour without land | `homestead-swarm-mixedfarm-metered-blind-muck` | 25 tiles, ~700 actions/day |
| pure denial | `homestead-lean-rootcellar-flood-spite-muck` | can suppression win alone? |
| pure patience | `estate-crew-mixedfarm-vault-blind-muck` | hold everything to the buzzer |
| herd, no fertilizer | `estate-crew-ranchmix-metered-blind-nomuck` | how much of animals is muck |
| fertilizer only | `estate-crew-ranchmix-metered-blind-dung` | the other half of the split |

Separately, `tools/stress.py` covers **environment** boundaries rather than
strategy ones — 28 pathological configurations (zero starting money, a 4×4 board,
a shed that holds one item, one turn per day, free hands, a market where every
product crashes) to catch hardcoded assumptions. A crash forfeits an episode, so
this runs before any tournament.

---

## Composition plans

Materialising all 9,216 is possible but wasteful. `tools/registry.py` defines
slices that answer specific questions:

| Plan | Size | Question |
|---|---|---|
| `main` | 26 | main effect of each atom, one axis varied at a time |
| `edge` | 8 | the corners |
| `produce` | 72 | every production atom × 2 land × 3 market |
| `muck` | 30 | fertilizer ablation across animal-bearing plans |
| `grid` | 512 | full cross of land × labour × market × intel, on 2 produce atoms |
| **`all`** | **594** | the union, deduplicated |

---

## Evaluating the library

A full round robin is O(n²) — 594 strategies would be 176,121 pairings. The
tournament runner therefore has two shapes:

**Screen (`panel`, O(n)).** Every strategy plays a fixed six-anchor panel
spanning the space: a strong metered farm, a land-light farm, a flooder, a
hoarder, a pure herd, and `starter` as a floor. 594 strategies × 6 anchors ×
8 seeds × 2 seats ≈ 57,000 episodes, about 80 minutes on 32 cores.

**Confirm (`roundrobin`, O(n²)).** The survivors play everyone. 24 strategies ×
24 seeds × 2 seats ≈ 13,000 episodes, about 20 minutes.

```bash
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8
sbatch slurm/tournament.sh roundrobin --from-run latest --top 24 --seeds 24
python tools/leaderboard.py --run latest
```

Both fit Bradley-Terry strengths — the same estimator Kaggle uses for the final
leaderboard — and persist every episode to `data/arena.sqlite`.

**A caveat that applies to any panel screen:** the strategy space is
non-transitive (a measured rock-paper-scissors cycle exists between metered,
flood and spite strategies — see `docs/ADVERSARIAL.md`). A panel score is
therefore a score *against that panel*, and the ranking will shift with the
anchors. That is a property of the game, not a defect of the method; it is also
why the confirm stage exists.

---

## Adding an atom

1. Add the option to the relevant table in `tools/registry.py`.
2. Teach `agents/_engine.py` to read whatever new `CONFIG` key it introduces.
3. `python tools/registry.py gen --plan all --out agents/lib`
4. `python tools/stress.py agents/lib/<any-new-strategy>.py`
5. Re-run the screen.

Keep the axes orthogonal. If two options interact so strongly that one is
meaningless without the other, they belong on the same axis as a single combined
option, not on two.
