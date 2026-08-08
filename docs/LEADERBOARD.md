# Strategy leaderboard

Run **#2** · `confirm-38-representative` · roundrobin · 38 strategies · 28,120 episodes · 20 seeds/pair · finished 2026-08-07 23:21:38

Ranked by **Bradley-Terry** strength — the same estimator Kaggle uses for the final leaderboard. BT-Elo is relative to the median strategy in the field; +400 means 10:1 odds.

> A high win rate with a low median $ means the strategy wins by denying the shared market rather than by earning. That does score on the ladder, but it is fragile against opponents who do not feed it.

## Top 40

| # | BT-Elo | win% | median $ | sd $ | strategy | alias |
|--:|-------:|-----:|---------:|-----:|----------|-------|
| 1 | +1961 | 99 | 65,167 | 15,038 | `homestead-crew-orchardherd-flood-evade-muck` |  |
| 2 | +1566 | 94 | 63,108 | 15,553 | `homestead-crew-orchardherd-flood-blind-muck` |  |
| 3 | +1566 | 94 | 63,108 | 15,553 | `homestead-crew-orchardherd-flood-frontrun-muck` |  |
| 4 | +1566 | 94 | 63,108 | 15,553 | `homestead-crew-orchardherd-flood-spite-muck` |  |
| 5 | +1169 | 88 | 62,753 | 15,972 | `homestead-crew-orchardherd-adaptive-evade-muck` |  |
| 6 | +1029 | 85 | 62,642 | 16,203 | `homestead-crew-orchardherd-metered-evade-muck` |  |
| 7 | +922 | 83 | 59,773 | 16,620 | `homestead-crew-orchardherd-adaptive-spite-muck` |  |
| 8 | +748 | 78 | 58,716 | 16,134 | `estate-crew-orchardherd-adaptive-blind-muck` |  |
| 9 | +748 | 78 | 58,716 | 16,134 | `latifundium-crew-orchardherd-adaptive-blind-muck` |  |
| 10 | +748 | 78 | 58,716 | 16,134 | `smallhold-crew-orchardherd-adaptive-blind-muck` |  |
| 11 | +479 | 70 | 48,094 | 12,180 | `smallhold-crew-mixedfarm-flood-blind-muck` |  |
| 12 | +445 | 69 | 52,572 | 13,558 | `homestead-crew-orchardherd-vault-spite-muck` |  |
| 13 | +385 | 67 | 46,129 | 13,692 | `homestead-crew-ranchmix-flood-blind-muck` |  |
| 14 | +288 | 63 | 44,242 | 16,894 | `barnyard` |  |
| 15 | +184 | 59 | 36,304 | 23,978 | `estate-crew-dairy-adaptive-blind-muck` |  |
| 16 | +164 | 58 | 51,654 | 14,613 | `estate-crew-berryherd-flood-blind-muck` |  |
| 17 | +104 | 56 | 39,352 | 13,794 | `estate-crew-mixedfarm-metered-blind-muck` | manor |
| 18 | +101 | 56 | 35,046 | 8,855 | `estate-lean-orchardherd-flood-evade-muck` |  |
| 19 | +61 | 54 | 41,446 | 16,490 | `homestead-crew-mixedfarm-metered-blind-nomuck` |  |
| 20 | -94 | 47 | 27,014 | 12,236 | `homestead-crew-mixedfarm-metered-blind-dung` |  |
| 21 | -128 | 46 | 29,680 | 12,053 | `estate-crew-mixedfarm-vault-blind-muck` |  |
| 22 | -176 | 44 | 22,622 | 22,066 | `homestead-crew-woolworks-flood-blind-muck` |  |
| 23 | -223 | 42 | 19,692 | 3,192 | `estate-crew-henhouse-adaptive-blind-muck` |  |
| 24 | -292 | 39 | 18,288 | 6,433 | `estate-crew-melonrush-flood-blind-muck` |  |
| 25 | -435 | 34 | 16,156 | 4,661 | `estate-swarm-mixedfarm-adaptive-blind-muck` |  |
| 26 | -457 | 33 | 20,846 | 5,710 | `estate-crew-berrypatch-adaptive-blind-muck` |  |
| 27 | -486 | 32 | 16,566 | 5,219 | `latifundium-swarm-mixedfarm-flood-spite-muck` |  |
| 28 | -508 | 31 | 15,734 | 6,953 | `homestead-swarm-mixedfarm-metered-blind-muck` |  |
| 29 | -759 | 22 | 9,418 | 2,924 | `estate-solo-mixedfarm-adaptive-blind-muck` |  |
| 30 | -759 | 22 | 9,418 | 2,923 | `latifundium-solo-mixedfarm-metered-blind-muck` |  |
| 31 | -783 | 22 | 3,810 | 6,569 | `estate-crew-ranchmix-metered-blind-dung` |  |
| 32 | -926 | 17 | 10,090 | 2,498 | `estate-crew-graingrind-adaptive-blind-muck` |  |
| 33 | -1087 | 13 | 7,228 | 2,122 | `homestead-lean-rootcellar-flood-spite-muck` |  |
| 34 | -1143 | 12 | 7,393 | 2,470 | `estate-crew-vinehouse-adaptive-blind-muck` |  |
| 35 | -1163 | 11 | 7,206 | 617 | `homestead-solo-graingrind-vault-blind-nomuck` |  |
| 36 | -1361 | 7 | 4,547 | 1,886 | `homestead-crew-rootcellar-adaptive-blind-muck` |  |
| 37 | -1676 | 4 | 3,494 | 60 | `starter` |  |
| 38 | -3421 | 0 | 79 | 1 | `estate-crew-ranchmix-metered-blind-nomuck` |  |

## Atom main effects

Mean BT-Elo of every strategy carrying each option. This is the marginal value of the choice, averaged over everything else.

**land**

| option | mean BT-Elo | strategies |
|--------|------------:|-----------:|
| `smallhold` | +613 | 2 |
| `homestead` | +392 | 16 |
| `latifundium` | -166 | 3 |
| `estate` | -484 | 15 |

**labour**

| option | mean BT-Elo | strategies |
|--------|------------:|-----------:|
| `crew` | +173 | 28 |
| `swarm` | -476 | 3 |
| `lean` | -493 | 2 |
| `solo` | -894 | 3 |

**produce**

| option | mean BT-Elo | strategies |
|--------|------------:|-----------:|
| `orchardherd` | +1047 | 12 |
| `dairy` | +184 | 1 |
| `berryherd` | +164 | 1 |
| `woolworks` | -176 | 1 |
| `henhouse` | -223 | 1 |
| `mixedfarm` | -253 | 10 |
| `melonrush` | -292 | 1 |
| `berrypatch` | -457 | 1 |
| `graingrind` | -1044 | 2 |
| `vinehouse` | -1143 | 1 |
| `rootcellar` | -1224 | 2 |
| `ranchmix` | -1273 | 3 |

**market**

| option | mean BT-Elo | strategies |
|--------|------------:|-----------:|
| `flood` | +479 | 12 |
| `adaptive` | -60 | 13 |
| `vault` | -282 | 3 |
| `metered` | -547 | 8 |

**intel**

| option | mean BT-Elo | strategies |
|--------|------------:|-----------:|
| `frontrun` | +1566 | 1 |
| `evade` | +1065 | 4 |
| `spite` | +272 | 5 |
| `blind` | -286 | 26 |

**muck**

| option | mean BT-Elo | strategies |
|--------|------------:|-----------:|
| `muck` | +166 | 31 |
| `dung` | -439 | 2 |
| `nomuck` | -1508 | 3 |

## Bottom 10

| BT-Elo | win% | median $ | strategy |
|-------:|-----:|---------:|----------|
| -759 | 22 | 9,418 | `estate-solo-mixedfarm-adaptive-blind-muck` |
| -759 | 22 | 9,418 | `latifundium-solo-mixedfarm-metered-blind-muck` |
| -783 | 22 | 3,810 | `estate-crew-ranchmix-metered-blind-dung` |
| -926 | 17 | 10,090 | `estate-crew-graingrind-adaptive-blind-muck` |
| -1087 | 13 | 7,228 | `homestead-lean-rootcellar-flood-spite-muck` |
| -1143 | 12 | 7,393 | `estate-crew-vinehouse-adaptive-blind-muck` |
| -1163 | 11 | 7,206 | `homestead-solo-graingrind-vault-blind-nomuck` |
| -1361 | 7 | 4,547 | `homestead-crew-rootcellar-adaptive-blind-muck` |
| -1676 | 4 | 3,494 | `starter` |
| -3421 | 0 | 79 | `estate-crew-ranchmix-metered-blind-nomuck` |

---
*Generated by `tools/leaderboard.py` from `data/arena.sqlite`.*