# Run log

Provenance for every experiment that produced a number cited anywhere in this
repo. Append a row when you run something; the point is that a claim can always
be traced back to the episodes behind it.

Everything from run #1 onward lives in `data/arena.sqlite` and can be re-queried:

```bash
python tools/db.py stats
python tools/db.py top --run 2 -n 40
sqlite3 data/arena.sqlite "SELECT * FROM runs"
```

---

## Tournaments in the database

| Run | Label | Shape | Agents | Episodes | Headline |
|---|---|---|---|---|---|
| **#1** | `library-screen-594` | panel, 8 seeds | 594 | 56,944 | `orchardherd` sweeps the top — later shown to be an artefact of two engine bugs |
| **#2** | `confirm-38-representative` | roundrobin, 20 seeds | 38 | 28,120 | `barnyard` 14th; first sign that rank and money had decoupled |
| **#5** | `enhanced-vs-field` | roundrobin, 20 seeds | 36 | 25,200 | first enhanced cut ranks 8th; herd deadlocked at nine |
| **#6** | `enhanced-fixed-vs-field` | roundrobin, 20 seeds | 36 | 25,200 | after the deadlock and land fixes: 75.8% against the field leader |
| **#7** | `ladder-field-spar` | roundrobin, 24 seeds | 34 | 26,928 | first field with opponents we did not write; `enhanced` ranks **27th of 34** |
| **#8** | `factorial-screen-960` | panel, 12 seeds | 960 | 184,224 | balanced produce×land×muck×market; the three reconstructed ladder shapes take the top three |
| **#9** | `factorial-confirm-40` | roundrobin, 48 seeds | 40 | 74,880 | `enhanced` **39th of 40**; `compost` good for strawberry, bad for melon |
| **#11** | `refine-labour-intel` | panel, 12 seeds | 640 | 122,856 | `crew` beats every labour option by 39+ points; **`intel` is worth nothing** |
| **#12** | `crop-ladder` | panel, 24 seeds | 72 | 27,552 | the strawberry ladder peaks at 28 tiles — on the pre-`compost` engine |
| **#13** | `crop-confirm` | roundrobin, 64 seeds | 24 | 35,328 | `bigberry` 1st at 86.1% |
| **#14** | `labour-recross` | panel, 24 seeds | 112 | 42,912 | `crew` (11 hands, 6%) still optimal on the fixed engine |
| **#15** | `crop-ladder-2` | panel, 24 seeds | 72 | 27,552 | 28 tiles still the peak after watering got cheaper |
| **#16** | `melon-recross` | panel, 32 seeds | 48 | 24,448 | more melon does not help locally, though ladder winners out-sell us on it |
| **#17** | `berryflood-confirm` | roundrobin, 64 seeds | 27 | 44,928 | `berryflood` (50 strawberry, copied from the 113k opponent) does not reach the top 11 |
| **#18** | `late-filler` | panel, 32 seeds | 32 | 16,256 | late-season carrot/wheat fillers rank 10-12; filling idle tiles is worse than leaving them |
| **#19** | `final-confirm` | roundrobin, 96 seeds | 14 | 17,472 | `marketgarden` 1st at 78.3% — fertilizing makes 18 strawberry tiles beat 28 |
| **#20** | `wheat-filler` | panel, 32 seeds | 24 | 12,160 | wheat on `smallhold` loses; the ladder winners' wheat is not what makes them win |
| **#21** | `wheat-after-ramp` | roundrobin, 64 seeds | 20 | 24,320 | wheat retried after the hiring ramp, still loses |
| **#22** | `bench-baseline` | roundrobin, 96 seeds | 12 | 12,672 | **the old reference field had saturated**: everything beat the anchors 97-100% |
| **#23** | `cand-vs-bench` | panel, 96 seeds | 6 | 11,520 | hiring ramp worth **+33 points** against a field that can rank; two identical builds score identically, validating the measurement |
| **#24** | `mg-sweep` | panel, 96 seeds | 9 | 17,088 | smaller and denser wins: `mgtight` 90.2% against `marketgarden` 59.1% |
| **#25** | `mg-sweep-2` | panel, 96 seeds | 8 | 15,360 | the shape brackets — 16 strawberry beats 14 and 18 |
| **#26** | `mgtight-confirm` | roundrobin, 96 seeds | 14 | 17,472 | `mgtight` / `mgtightwide` tied at the top, 14 points clear of the submitted shape |
| **#27** | `axis-recheck` | panel, 32 seeds | 144 | 92,160 | every axis re-measured on a field with spread; all previous choices confirmed |
| **#28** | `liquidate-day` | panel, 96 seeds | 5 | 9,600 | liquidate on day **29**, monotone: 92.9 / 90.2 / 85.9 / 76.0 |
| **#29** | `mgtight-fillers` | panel, 96 seeds | 7 | 13,440 | fillers on the tight base lose three ways — the idle time is not convertible |
| **#30** | `final3-confirm` | roundrobin, 96 seeds | 17 | 26,112 | with the here-pass, the wheat filler **flips** and `mgtightgrain` reaches the top |
| **#31** | `duel-final` | roundrobin, 256 seeds | 14 | 46,592 | `mgtightgrain` 86.7% and $75,727 over 46,592 episodes; beats `mgtightwide` 58.8% head to head |
| **#32** | `resweep-new-engine` | panel, 64 seeds | 24 | 30,208 | invalidated by the filename collision — `bench2` shares names with the roster |
| **#33** | `resweep-clean` | panel, 96 seeds | 7 | 13,440 | redone with unique names |
| **#34** | `herd-resweep` | panel, 96 seeds | 7 | 13,440 | herd size re-measured on the new scheduler: 7+3 still optimal, monotone both ways |
| **#36** | `axis-recheck-2` | panel, 32 seeds | 144 | 92,160 | every axis re-measured **again** after the here-pass; nothing flips |

Runs #10 and #35 were duplicate ingests of #11 and #36 and were deleted; `PRAGMA integrity_check`
is clean and the totals below exclude it.

**Twelve further A/B ablations were analysed straight from their shard JSONL and
deliberately not ingested**, because each is one change against one control
rather than a ranking: sticky assignment, idle pre-positioning, alternate-day
watering, CARE priority, `paced` selling, `shopwise`, the fertilizer reserve, the
carrying threshold, the ramp shape, the inverted scheduler, two-pass and zone
scheduling, the here-pass and the tile hold. Every one is written up with its arm
size in `docs/ENGINE_CHANGES.md` — **eleven landed, seventeen were rejected**.

**Three more on 2026-08-11**, also read from shard JSONL rather than ingested,
and for a second reason: all three carry builds that share basenames across
directories, and `short(path)` is the basename, so ingesting would merge them
into one ratings row — the defect that corrupted runs #22 and #32.

| label | arms | episodes | outcome |
|---|---|---|---|
| `bootlock` | 3 engines × 6 produce × 2 land | **137,664** | the opening seed freeze is a trade, not a deadlock — rejected, `ENGINE_CHANGES.md` |
| `handover` | 17 handover days + anchors | 62,016 | no handover day helps; the curve runs to 100% recording — `ROADMAP.md` §3 D |
| `handover-adopt` | same, targets adopted at handover | 39,936 | ±4 points, no change in shape |
| `endgame` | 3 endgame variants × 10 shapes | 109,440 | keeping the task list alive on the liquidation day loses; so does never liquidating |
| `endhire` | hire on the liquidation day, ± the task list | 109,440 | **landed**, +1.66 points — the workforce was being dismissed on the most valuable day |
| `endhire-ghosts` | the same two engines vs 156 ladder trajectories | 3,120 | independent confirmation, +4.55 points |
| `endD-shape` | 10 shapes under the new engine, 192 seeds | 72,960 | disagrees with the ghost field on the produce axis — tiebreaker `endD-ref` in flight |
| `tracelib` | 959 post-rebalance top episodes mined for distinct plans | 1,894 traj | **201 distinct plans**, 9:1 duplication — `ROADMAP.md` §10 |
| ~~`metaduel`~~ | 12 mined plans + champion | 28,080 | **void** — the replays were one turn late; see `ROADMAP.md` §10 |
| `duel101` | 101 mined plans, one shared wrapper, 48 seeds | **477,225** | champion 64th at 36.5%; 3.3% of triples are cycles but none inside the top 12 — `ROADMAP.md` §10 |

Reproduce any of them without the database:

```bash
python - <<'PY'
import glob, json, collections, os
w = collections.Counter(); g = collections.Counter()
for s in glob.glob("data/shards/bootlock/shard-*.jsonl"):
    for line in open(s):
        r = json.loads(line)
        for i, side in enumerate(("left", "right")):
            a = r[side]
            if "/bench3/" in a or "/ref/" in a: continue    # panel, not candidate
            g[a] += 1                                       # key on the full path
            w[a] += (r["money"][i] > r["money"][1-i]) or 0.5*(r["money"][i] == r["money"][1-i])
for a in sorted(g, key=lambda k: -w[k]/g[k])[:5]:
    print(f"{100*w[a]/g[a]:5.1f}%  {a}")
PY
```

Runs #8 and #9 were the first sharded runs: 48 array tasks × 32 cores = 1,536
cores, `KG_FAST_ENV=1`. Run #8's 184,224 episodes took about six minutes of wall
clock against the ~9 hours the same work would have taken on one 32-core job.

**1,297,916 episodes total** across 43 runs, plus 396 real ladder episodes. Regenerate these three numbers with `python tools/db.py stats` -- they are the only figures here that drift, and they drift every time anyone runs anything.

`docs/MAP.md` says which document explains which run.

Runs #1–#6 ran on an engine with two defects that hurt crop plans much more than
herd plans, and on a library that could not issue `FERTILIZE`. **Do not compare
their numbers with #7's.** `docs/LADDER_FIELD.md` §4 has the controlled A/B and
what each fix was worth.

## Ladder episodes (real opponents)

| Pulled | Submissions | Episodes | Kept | Headline |
|---|---|---|---|---|
| 2026-08-09 | `55332339`, `55358912` | 94 | 125 KB of digests, 1.9 GB of replays discarded | 48% overall; `enhanced` 49%, `barnyard` 47% — a 384/384 local gap is worth two points here |

`ladder_episodes` in `data/arena.sqlite`. Re-query with
`python tools/ladder.py stats`.

Run #1's roster is the whole `all` plan from `tools/registry.py`. Run #2's roster
is run #1's top 8, the best carrier of every atom option, all eight boundary
corners, plus `barnyard` and `starter`.

---

## Earlier experiments (JSON in `logs/`, pre-database)

These predate the SQLite store. Kept because published conclusions cite them.

| What | Scale | Output | Headline |
|---|---|---|---|
| Tunable league | 8 agents × 24 seeds × 2 seats = 1,344 eps | `logs/league_v1.json` | `HAND_CAP=11` beats the then-default 14; `TARGET_COWS=10` confirmed |
| Probe league | 21 agents × 16 seeds × 2 seats = 6,720 eps | `logs/league_probes.json` | `one_quadrant` 1st, `dump_all` 2nd *above* `barnyard`, `product_only` last on $78 |
| Adversary league | 8 agents × 24 seeds × 2 seats = 1,344 eps | `logs/league_adv.json` | pure denial (`parasite`) went 0/168 and made opponents *richer* |
| A/B: `dump_all` vs `barnyard` | 192 seeds × 2 seats = 384 eps | `logs/eval_dump.json` | 71.4% win, CI [66.6%, 75.6%], while earning ~25% less |
| A/B: `one_quadrant` vs `barnyard` | 192 seeds × 2 seats = 384 eps | `logs/eval_1q.json` | 93.2% win, CI [90.3%, 95.3%], earning *more* |
| A/B: `enhanced` vs field leader | 384 eps | `logs/eval_enh_vs_top.json` | **75.8% win**, CI [71.3%, 79.8%], margin +3,016 |
| A/B: `enhanced` vs `barnyard` | 384 eps | `logs/eval_enh_vs_barn.json` | **100% win** (384/384), margin +25,753 |
| Quadrant sweep | 4 configs × 8 seeds | — | 1→49,078 · 2→68,738 · 3→68,892 · 4→68,892 |
| Crop-scale sweep | 6 configs × 8 seeds | — | scaling the crop plan up is monotonically worse |
| Stress suite | 28 pathological configs | — | `barnyard` 28/28 clean, worst turn 145 ms |

Grand total including these and the ablations: **well over 1.3 million episodes**.

---

## Submissions

| Date | Submission | Agent | Snapshot | Local evidence | Ladder |
|---|---|---|---|---|---|
| 2026-08-13 | `55489160` | `kawashigi-k06` — the same team's strongest recorded line, chosen on the panel | `submissions/2026-08-13-kawashigi-k06/` | Panel win rate **98.5%** [97.8, 98.9] over 1,920 episodes against 92.4% [91.2, 93.5] for the incumbent, and **60.8%** [57.3, 64.2] head to head over 768. Beats all ten panel members; the incumbent's weakest matchup is 78.6%. 28/28 stress clean; 720/720 actions identical after packaging. | pending — **this is the prospective test of the panel, see below** |
| 2026-08-13 | `55484175` | `topline` — a recorded top-of-ladder plan under the `closer_cleo` market layer | `submissions/2026-08-13-topline/` | 92.4% over 1,920 episodes against the ten strongest plans previously mined (best incumbent 79.9%), **and** the highest-rated source team of the 371 in the library (カワシギ, #1 at 3,240). Two independent signals converge. Submitted as calibration, not as an answer — see the null result below. 28/28 stress clean; 720/720 actions identical after packaging. | **2144.1 and still climbing** — 21–1 over 22, so **not yet a score**: see the one-third rule below. Beats 1218.6 for the plan it replaced, on opponents of the same strength ($73,884 vs $77,991 mean opponent money, +$6,421 margin against +$1,135). |
| 2026-08-12 | `55458466` | `closer_cleo` + terminal at 714 (resubmit) | `submissions/2026-08-11-closercleo-term714/` | 91.7% [90.9, 92.5] over a 28,080-episode round robin against the twelve most-played plans mined from 959 post-rebalance ladder episodes, beating all twelve. The field is strictly transitive, so no ensemble has anything to exploit. 28/28 stress clean. | **1218.6** — the same file scored 1363.7 five days earlier, see below |
| 2026-08-11 | `55442784` | `closer_cleo` + terminal at 714 | `submissions/2026-08-11-closercleo-term714/` | Threshold sweep over 384 seeds against `bench3`, 10,800 episodes an arm: 714 reaches a 98.1% plateau against 95.2% unchanged. | **1363.7** — our best to date |
| 2026-08-11 | `55439740` | `closer_cleo` (third-party, unmodified) | `submissions/2026-08-11-closercleo/` | 99.2% of `bench3`+refs over 3,072 episodes and 99.4% of the 156 ghost trajectories, against 60.9% / 57.7% for our best engine. First of five in a 3,072-episode round robin among the trace agents at 92.7%, beating `slotter_silas` 88.0% and `ledger_lena` 91.9%. Raw replayed trajectories score **0.0%** against all four wrapped agents, so the value is the adaptive layer and not the trace. 28/28 stress clean. | **1287.2** — our own change is worth less than the gap between two runs of it |
| 2026-08-07 | `55332339` | `barnyard` | `submissions/2026-08-07-barnyard/` | ~67k median vs `starter`; 28/28 stress | 621.4; **47% over 59 real episodes** |
| 2026-08-08 | `55358912` | `enhanced` (tar.gz, 5 modules) | `submissions/2026-08-08-enhanced/` | 100% vs `barnyard` and 75.8% vs the field leader, both over 384 episodes | 623.6; **49% over 35 real episodes**, level with `barnyard` |
| 2026-08-09 | `55385371` | `marketgarden` | `submissions/2026-08-09-marketgarden/` | 34.9% vs `orchardherd` 16.1% over the balanced 960-cell factorial | 700.1 over 12 episodes |
| 2026-08-09 | `55385995` | `bigberry` | `submissions/2026-08-09-bigberry/` | 1st of 24, 86.1%, over a 35,328-episode round robin | 647–837 over 10 episodes; **71% win rate (5 of 7 pulled)** |
| 2026-08-09 | `55386385` | `bigberry` + alternate-day watering | `submissions/2026-08-09-bigberry-altwater/` | 82.2% against 71.1%, 3,072 episodes an arm | 780.4 over 10 episodes |
| 2026-08-09 | `55386857` | + fertilizer price gate | `submissions/2026-08-09-bigberry-fertgate/` | 85.0% against 83.3%, 3,072 an arm | 711.4 over 4 episodes |
| 2026-08-09 | `55386…` | + `shopwise` herd | `submissions/2026-08-09-bigberry-shopwise/` | 71.9% against 68.4%, 6,144 an arm | pending |

| 2026-08-10 | `55402695` | `mgtight` | `submissions/2026-08-10-mgtight/` | 1st of 24 over 35,328 episodes | **759.9** over 41 episodes |
| 2026-08-10 | `55404837` | + liquidate on day 29 | `submissions/2026-08-10-mgtight-liq29/` | monotone sweep, 92.9/90.2/85.9/76.0 | **838.4** over 47 — the liquidation day is worth +69 on the ladder |
| 2026-08-11 | `55418588` | `mgtightgrain` | `submissions/2026-08-11-mgtightgrain/` | 86.7% over 46,592 episodes | 781.1 over 38 — **bundled two changes, see below** |
| 2026-08-11 | `55424…` | `mgtight` + here-pass, no wheat | `submissions/2026-08-11-mgtight-here/` | 2×2 factorial: here-pass +42, wheat −31; agreed by three fields | pending |

### The wrapped field does not measure strategy strength (2026-08-13)

This is the largest measured null result in the repo and it invalidates the way
§10 of `docs/ROADMAP.md` was reading its own numbers.

Every plan in `agents/wrapped/` was recorded from a real team's episode, and that
team has a real ladder rating. So the local ranking can be checked against the
thing it is supposed to predict, without submitting anything. Over all 100 plans:

```
local win% vs the source team's ladder score   pearson -0.038   spearman -0.054   n=100
local win% vs the team's median rating         pearson -0.110   spearman -0.126
single-episode best $ vs ladder score          pearson -0.014   spearman +0.114
```

**Zero.** With n=100 this rules out any correlation above about 0.2. The 477,225
-episode round robin ranks 101 agents against each other very precisely and that
ranking carries no information about which agent is actually good.

The mechanism is visible without any statistics. Several teams appear in the
field more than once, because we mined several of their episodes:

| Team | Ladder | Plans mined | Local win% across them |
|---|---|---|---|
| THUNDER THUNDER | #364 @ 2,594 | 16 | **14% – 93%** |
| HealthStone | #234 @ 2,741 | 14 | **15% – 81%** |
| Seb (allegedly) | #801 @ 1,997 | 11 | 24% – 76% |
| カワシギ | **#1 @ 3,240** | 3 | **26% – 83%** |

Same team, same agent, same week. The median within-team spread is **52.6
points**, against a full-field spread of 81.1 — **65% of the entire field's
spread is reproduced inside one team's own episodes.** A wrapped plan's win rate
measures which episode it was recorded from, not who recorded it.

Two further facts fall out of the same check:

* **The "101-agent field" is 20 sources.** 63 of the 100 plans belong to a single
  team each, and those come from just 19 teams; two teams supply 30 of the seats.
* **The frequency filter in `tools/wrap.py` was mostly inoperative.** Only 57
  eligible lines have `count >= 2`, so 43 of the 100 seats were filled from 290
  tied single-sighting lines in dictionary order. `agents/darkhorse/` (40 lines
  picked by best single-episode money instead) put **18 of 40 above the old
  field's tenth-place threshold**, and its best, `d08`, scores 92.4% against the
  ten strongest incumbents where the best incumbent gets 79.9%.

The darkhorse result is real but it does not mean what the pre-registered
criterion in `docs/TODO.md` said it would. Selecting by single-episode money
selects for a *productive action sequence that transplants*, which is genuinely
what an open-loop replay needs. It does not select for strategy.

**What survives.** Nothing local predicts ladder strength today. The only
grounded signal left is external: the rating of the team a plan was recorded
from. `submissions/2026-08-13-topline/` was chosen where both signals happen to
agree, and exists to measure how much of a #1 team's plan survives open-loop
replay.

**What this does not say.** It does not say `term714` is strong. Its 64/101 and
36.5% are uninformative in both directions — but its ladder scores, 1363.7 and
1218.6 against a 3,240 top, are direct evidence and they stand.

### What an open-loop replay costs, in ladder points

`closer_cleo` submitted unmodified is an open-loop replay of the **shared public
meta line** wearing this exact market layer. It scored **1287.2**. The 93 teams
still on the board who play that same line score:

```
max 3,108   p75 2,848   median 2,588   p25 2,005   min 98
```

Same plan. **1,301 points below the median team that plays it, 1,820 below the
best.** That difference is everything the recording does not carry: reacting to
the shop draw, to weeds, to what the opponent is doing to prices.

Applied to `topline` (recorded from カワシギ, #1 at 3,240.2), the pre-registered
prediction for `55484175` was **1,400 – 1,950, point estimate ~1,650**, with a
stated implication that replaying recordings tops out near 1,900.

> ### ~~That prediction~~ — falsified the same day
>
> `55484175` reached **2144.1** within ninety minutes and was still climbing,
> at 21 wins in 22. Both the range and the ceiling are wrong.
>
> **The arithmetic double-counted.** `closer_cleo` scored 1287.2 while carrying
> the *shared public meta* plan -- a weak plan (47.4% locally, the most-copied
> line in the library). So
>
> ```
> 1287.2  =  a weak plan  +  the replay penalty
> ```
>
> Subtracting the whole 1,301–1,820 gap from 3,240 charged all of it to replay
> and implicitly priced plan quality at zero -- which is the quantity the
> submission exists to measure. Swapping the plan alone is worth **at least
> +857** (2144.1 − 1287.2) and had not finished.
>
> Keep the anchor, drop the conclusion: 1287.2 vs a 2,588 median for the teams
> playing that same plan is still a real measurement of *something*. It is just
> not a ceiling, because the plan and the replay penalty were never separated.

### The replay penalty, measured: 877 points

This is what `55484175` was submitted to find out, and it converged at 54
episodes (50.0% over the trailing 18, opponent strength flat).

```
カワシギ, the team whose episode we replay      3,236.5
topline, our open-loop replay of it            2,359.5
-----------------------------------------------------
open-loop replay penalty                         877
```

A recording under a market layer keeps **73%** of the rating of the adaptive
agent that produced it. The estimate this replaced was 1,301–1,820 -- **too
pessimistic by roughly a factor of two.**

Both numbers are from 2026-08-13 16:52 UTC, when the leaderboard as a whole was
flat over the preceding 3.5 hours (top 3,240.2 -> 3,236.5, tenth 3,094.4 ->
3,089.0, median 738.5 -> 739.4, 4,259 -> 4,288 teams), so the +1,145 from
`term714` to `topline` is movement and not inflation.

**What it costs the road.** A prize place needs 3,089.0 and we are at 2,359.5.
Cloning the single best recording available, with no loss at all, would reach
3,236.5 -- and 877 of that is not obtainable, because it is not in the plan.
Copying recordings cannot reach the prize zone; this measures by how much.

### The prospective test of the panel (written before the result)

Every claim about local measurement in this repo so far has been checked *after
the fact* -- correlate a local ranking against ladder scores that already exist.
That is how §10.5's null result was found, and it is also why it could not say
whether a *better* local measure would work. `55489160` is the first prospective
version: a prediction recorded before the number arrives.

**The design.** Two submissions, active at the same time, facing the same pool:

|  | incumbent `55484175` | challenger `55489160` |
|---|---|---|
| source team | カワシギ, #1 | **the same team** |
| market layer | `closer_cleo`, MIT | **the same file** |
| recorded episode | 92125421 | **92135733** |
| panel win rate | 92.4% [91.2, 93.5] | **98.5% [97.8, 98.9]** |
| head to head | — | **60.8% [57.3, 64.2]**, n=768 |
| ladder | **2359.5**, converged | *this is the prediction* |

Everything is held fixed except which episode was recorded, so the ladder is
being asked one question: **does a 6.1-point panel edge correspond to a real
ladder edge?**

**What each outcome means.** Read only after `55489160` has lost a third of its
trailing 18 (rule 7 in `SUBMISSION_POLICY.md`):

* **Clearly above 2359.5** -- the panel has predictive power with the source team
  held constant. The open item at the top of `docs/TODO.md` is half solved, and
  local optimisation becomes possible for the first time.
* **Level with it** -- the panel separates plans that the ladder does not. It
  stays useful as a filter and is worthless as an objective; do not search
  against it.
* **Clearly below** -- the panel is anti-predictive at the top, which would be
  the strongest result of the three and would mean the ten-agent panel is
  selecting for something the ladder punishes.

There is no outcome here that is not worth having, which is the point.

### A ladder score does not count until the agent loses a third of its games

A new submission enters low and climbs by beating weaker opponents. Until it has
climbed, the number on the leaderboard is a floor that is still moving.

```
losing < 1/3   still climbing. The score means "at least this much" and nothing else.
losing ~ 1/3   near its level. Start reading it.
losing ~ 1/2   converged. This is its score.
```

Measure it on a **trailing window of ~18 episodes**, never cumulatively --
cumulative lags forever, because the early wins against weaker opponents never
age out. At 54 episodes `55484175` was 22.2% cumulative and 50.0% over the last
18. Its three blocks ran 5.6% -> 11.1% -> 50.0% while mean opponent money went
$61,245 -> $82,795 -> $82,194: **opponent strength stopped rising and the loss
rate kept climbing, which is what convergence looks like.**

`55484175` read **1695.2** at 11 episodes (11–0) and **2144.1** at 22 (21–1) --
+449 points in forty minutes, same file, the only change being that it was still
ascending. The prediction above was made against the first reading and broke
against the second.

The converged counter-example is in the same table: `term714` over 130 pooled
episodes sits at exactly **50.0%**, and its 1363.7 / 1218.6 are real readings.

**Episode count is the wrong stopping rule.** `SUBMISSION_POLICY.md` rule 1 asks
for ≥40 episodes; that is necessary, not sufficient. `55484175` was at 95.5%
after 22 and would still have been climbing at 42. Episodes buy sample size,
**the loss fraction is what tells you it has found its level.** Recorded as rule
7 there.

### The same file, submitted twice, moved 145 points

`55442784` and `55458466` are the same agent. They scored **1363.7** and
**1218.6**. Nothing changed but the opponents the ladder happened to draw.

Every ladder comparison in this document smaller than ~145 points is inside that
band, including the +69 attributed to the liquidation day. Treat single-ladder-run
differences as hypotheses; `docs/EVALUATION.md` §6 has the arm sizes that settle
them locally.

### One submission, two changes, and why that was a mistake

`55418588` changed the production shape *and* added the here-pass. It landed at
781.1 against the incumbent's 838.4, and that number could not say which change
was responsible — exactly what `docs/SUBMISSION_POLICY.md` rule 3 forbids, and
the rule was written before the mistake was made.

A 2×2 factorial separated them, 512 episodes a cell:

| | no here-pass | here-pass |
|---|---|---|
| **no wheat** | 48.2% (the incumbent) | **90.6%** |
| **wheat** | 1.5% | 59.7% (what was submitted) |

The here-pass is worth **+42 points** and the wheat filler **−31**. Three
independent fields agree: direct head to head, the meta-inclusive `bench3`
(55.9% against 47.4%), and 156 replayed top-player trajectories (58.3% against
54.5%, with the incumbent at 33.3%).

**The best combination had never been submitted.** It is now.

### Submitting too often destroys the measurement

Only the **latest two** submissions stay active, and the ladder plays roughly ten
episodes an hour per active agent. Six submissions in one afternoon meant every
one of them was deactivated after 4–12 games:

| submission | episodes completed before deactivation |
|---|---|
| `55385371` | 12 |
| `55385995` | 10 |
| `55386385` | 10 |
| `55386857` | 4 |

Ten games cannot separate 700 from 900 — `55385995` read 837 at five games and
647 at ten, and neither number meant anything. It also starves
`tools/ladder.py`: the diagnosis that produced most of today's gain came from 94
replays, and no agent here collected more than twelve.

**Rule: submit at most once per half-day, and only when the local evidence is a
completed A/B.** The feedback loop here is measured in hours; the local one is
measured in minutes, and running the slow loop at the fast loop's cadence throws
the slow loop's data away.

*(A third row, `55348834 rl_models.zip`, appears on the submissions page with
status ERROR. It was not produced by this repo.)*

**The local-versus-ladder correlation is now measured, and it is weak.** Over 94
real episodes, `enhanced` wins 49% and `barnyard` 47% — the two agents that are
384/384 apart locally. `docs/LADDER_FIELD.md` is the diagnosis: the field we were
ranking against could not express the winning strategy, and the engine's bugs
penalised crop plans far more than herd plans. This is the single most useful
thing measured in the project so far, and it took 94 episodes.

---

## Reproducing a run

Tournaments are deterministic given `(seed, both agents)`, so a run reproduces
exactly if the agent files have not changed. `agents/lib/manifest.json` records a
source hash per strategy; the `agents` table stores it too.

```bash
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8 --label "screen-repro"
python tools/db.py top --run latest
```

If numbers differ from the table above with the same seeds, the engine version
changed — check `pip show kaggle-environments` against 1.32.6 and re-diff
`reference/engine/kaggriculture.py`.

---

## Data integrity incidents

**2026-08-09 — 48 concurrent array tasks corrupted the database; fully recovered.**
A sharded tournament was submitted as a 48-task Slurm array. The shard code path
was written specifically so that array tasks never touch SQLite — but the
roster/manifest step ran *before* the shard branch, so all 48 tasks opened
`data/arena.sqlite` and ran `register_agents` at the same instant. SQLite on a
shared Lustre filesystem does not survive that:

```
sqlite3.DatabaseError: database disk image is malformed
Tree 2 page 2 cell 0: 2nd reference to page 57875
```

Recovery, in order:

1. `cp -a` the damaged file to `data/arena.sqlite.corrupt-20260809` before
   anything else, so the recovery could be retried.
2. `sqlite3 <corrupt> .recover | grep -v sqlite_sequence | sqlite3 <new>`.
   (`.recover` emits a `sqlite_sequence` insert that the fresh database rejects;
   `.dump` is the wrong tool here because it stops at the first bad page.)
3. `PRAGMA integrity_check` → **ok**, and every run's row count matched the
   count logged in its `runs` row exactly: 56,944 / 28,120 / 25,200 / 25,200 /
   26,928 = **162,392, nothing lost**. `ladder_episodes` intact at 94.
4. `agents` came back with 603 of its rows; re-registered from the three
   manifests, which is where that table comes from anyway.
5. Run #7's `n_episodes` had been in a damaged page; recomputed from `episodes`.

The 160 duplicate `(run_id, seed, left, right)` keys found in run #1 during
verification are **not** recovery damage — they are byte-identical rows created
by `plan_panel` when an agent appears in both the roster and the panel, and they
predate this incident.

Fixes, both in `tools/tournament.py`:

* Shard mode now resolves `con = None` and never opens the database. `--shard`
  with `--from-run` is a hard error, because that is the one roster source that
  needs a read; resolve it on the submitting host and pass `--agents`.
* Verified rather than asserted: the shard path was re-run under a monkeypatched
  `sqlite3.connect` that raises on any path containing `arena.sqlite`, and the
  live database's md5 was compared before and after.

This is the third incident in this project caused by SQLite access patterns, and
the second where a tool reported success while doing the wrong thing. The rule
that would have prevented all three: **exactly one process writes the database,
and it is never a Slurm array task.**


**2026-08-08 — duplicate runs written by a test, removed.** A test of
`tools/sync.py merge` intended to write into a scratch database wrote into
`data/arena.sqlite` instead, adding runs #3 and #4 as exact copies of #1 and #2
(85,064 → 170,128 episodes). Both were deleted and the database vacuumed; runs
#1 and #2 were never modified and all counts are back to 85,064 / 633 / 594.

Two real bugs caused it, both now fixed:

* `db.connect(path=DB_PATH)` bound its default **at import time**, so reassigning
  `DB.DB_PATH` had no effect on where writes went — while log messages happily
  reported the new path. `connect()` now resolves `DB_PATH` at call time, and
  `sync.py merge` takes an explicit `--into`.
* `cmd_merge` never closed its connection. In WAL mode that left the committed
  rows in the `-wal` file, producing a **0-byte database that had just reported a
  successful merge**. Writers now checkpoint and close via `db.close()`.

A third bug surfaced during the cleanup: `cmd_merge` passed `atoms` to
`register_agents` as the JSON string it had read, and `register_agents`
`json.dumps()` whatever it is handed — so all 594 agent rows ended up
double-encoded, and `tools/leaderboard.py` crashed on the next run. Fixed at the
source and all 594 rows repaired.

The lesson worth keeping: a path reported in a log is not evidence of the path
written to. The round-trip test in the scratchpad exists because of this, and it
is what caught all three.

## Diagnosis: why the first enhanced cut ranked 8th

Run #5 put the first version of the enhanced baseline 8th of 36 — comfortably
ahead of `barnyard` (15th) but behind all seven `homestead-crew-orchardherd-*`
variants. Comparing digests across the same tournament made the cause obvious:

| | enhanced (first cut) | field leader |
|---|---|---|
| quadrants owned | 2 | **1** |
| animals at the end | **9** | 15 |
| idle tiles | **32** | 7 |
| wool sold | 30 | 48 |

Two independent defects:

**The herd deadlocked at nine.** `feed_solvent` required
`shed_wheat >= (n+1) * FEED_DAYS_REQUIRED`, but the reserve it was checking
against is capped at `WHEAT_RESERVE_CAP = 28`. At nine animals the requirement is
30 — unreachable — so no tenth animal could ever be bought. Two constants that
had to agree, and did not.

**Two quadrants were worse than one, for this agent.** With 18 pens and 12 melon
tiles planned against 50 tiles, 32 sat idle while the hands walked further. The
leader used 18 of 25. Land does not add production; it spreads the same labour.

Both fixed, and the result reverses: 75.8% against that same leader over 384
episodes, and 13–15 animals with 7 idle tiles instead of 9 and 32.

## Known caveats attached to these numbers

- **Run #1's top tier is saturated.** Eight strategies went undefeated against
  the panel, so Bradley-Terry diverges and their relative order is arbitrary.
  That is what run #2 exists to resolve.
- **Runs #1 and #2 disagree on atom effects** — `ranchmix` goes from second-best
  to worst, `frontrun` from marginal to top. Both are honest; they measure
  different fields. The strategy space is non-transitive
  (`docs/ADVERSARIAL.md`).
- **Main effects in `docs/LEADERBOARD.md` are unbalanced** by construction, because
  the composition plans do not sample the axes evenly. The balanced versions are
  in `docs/ATOM_EFFECTS.md` and they reverse some orderings.
- **The pre-database leagues used ad-hoc agent generators** (`agents/legacy/`)
  that had bugs the library engine later fixed. Treat their absolute numbers as
  indicative and their comparisons as valid only within a league.

## Can we interfere with the market? Two waves, 106,000 episodes (2026-08-13)

The question came from a specific model of the field: *if* every ladder opponent
is a recording plus a market wrapper, there must be some way to move prices
against them, because an open-loop agent cannot react. The engine says the
premise is half right. There are exactly two channels between the two farms --
the shared market inventory, and the end-of-day RNG, whose draw count depends on
each farm's empty-tile count and which therefore decides which shop unlocks and
so which market recovers. Only the first is usable on purpose.

Every arm is `agents/champ/k01.py` with market constants rewritten by
`tools/perturb.py` and played against a byte-identical copy of itself. `_TRACE`
never varies, so planting, harvesting, hiring and buying are identical in every
arm and nothing but market behaviour can move the result.

**Controls first.** `mctl` (byte-identical copy) and `mnul` (interference overlay
present, all dials empty) both returned 50.0% [45.7, 54.3] with a paired margin
of $+0 ± 429. The harness is unbiased and the overlay is inert.

### Every attempt to disrupt the market made the opponent richer

Nineteen arms dumped, hoarded or re-slotted supply. **Not one produced a negative
change in the opponent's bank.**

```
C.fr_straw   win 0.8%   us -$8,706   them +$9,608
C.fr_melon   win 1.0%   us -$8,132   them +$9,133
E.fuse_d20   win 0.0%   us -$82,229  them +$60,996
```

The reason is that we are already the disruption. The baseline lists 3,511 units
a season and closes fertilizer and milk at $1, and that sustained selling is what
holds the price down for the opponent. Anything that makes us sell less -- or
wrecks our own farm so we produce less -- *removes* pressure we were already
applying. In one traced episode the arm that hoarded wool left milk closing at
$183 against the baseline's $1.

Withdrawing as a seller is the largest gift available in this environment.

### The one dial that won is a self-play artefact

Extending the donor's clone-detection front-run from 1 turn to 3 scored **78.7%
[75.0, 82.0]** against a mirror; turning it off scored 22.9%. Money barely moved
-- Δus +$176, Δthem -$242, paired margin +$418 ± 431, which spans zero. A mirror
match finishes near a tie by construction, so a few hundred dollars of consistent
edge flips a quarter of the outcomes. The competition scores wins only, which is
exactly why `docs/VALIDATING.md` ranks on win rate and not on money.

Wave 2 crossed 7 horizons x 4 item sets x 2 slot policies and played all 56 cells
against the mirror **and** against four wrapped ladder recordings. Against the
recordings every one of the 58 agents returned **(901 wins / 992 games)** --
identical to the episode, not merely indistinguishable. `_front_run` needs
`_CLONE_CONFIDENCE >= 2`, which needs the opponent's public farm signature within
distance 1; self-play satisfies that by construction and no real recording ever
does. **None of the 78.7% transfers.**

### The interaction table, and why the main effect lies

```
mirror win rate            all9     melon     prem4      wool
h0 (off)                  21.8%     21.8%     21.8%     21.8%
h1                         4.8%     21.8%     59.9%     59.9%
h2                         4.8%     21.8%     78.8%     78.8%
h3                         4.8%     21.8%     80.2%     80.2%
h8                         4.8%     21.8%     79.0%     79.0%
```

The horizon effect exists only in one column. It is exactly zero for melon, and
*negative* for the widened item set. `prem4` and `wool` agree in every cell,
which means the mechanism only ever fires on wool and the four-product set is
decoration. The marginal main effect of h3 is 46.8% -- an average over cells
worth +58, 0 and -17 points, and a number that would have been read as a modest
win by anyone who did not print the interaction.

### Nobody on the ladder plays this dimension, and there is little room to

`tools/tracefeat.py` extracts fourteen behavioural features of the market queue
from all 371 mined lines and scores them against `wins/plays` -- real outcomes in
real ladder episodes, not anything this repo simulated. Null: best |spearman|
<= 0.28, the top-ranked feature changes with every play threshold, and
`prem_unit_share` reverses sign between subsets.

The structural measurement underneath it is the more useful one. Across 266,749
recorded turns:

```
53.61%  place no market order at all
29.87%  place exactly one
82.26%  contain no SELL order
```

Ten slots, and 83.5% of turns use none or one of them. Slot ordering has nothing
to order in most turns -- though 306 of 371 lines do fill all ten at some point,
so the capacity is used in bursts and not unknown to them.

### What this closes and what it leaves open

Closed: market interference as a route for a recording-plus-wrapper agent. The
channel exists, the baseline already sits at its aggressive end, and every
implementable move along it is self-harm.

Also closed: the fertilizer-subsidy hypothesis. Fertilizer has no sink anywhere
in the engine -- no shop and no town-centre line consumes it -- so a buyer is the
only thing that lowers its inventory, and we close it near $1 every season. The
arm that bought it cheap scored 15.1% at a $5 cap and 4.1% at $20, and made the
opponent richer. Buying lifts the price, which pays the seller.

Left open: the queue is 10 wide and 83.5% of turns use at most one slot. The
unused capacity is in *actions*, not in ordering -- HIRE and BUY_LAND are market
orders too. Nothing here tested that.

Caveat on all of it: the "field" condition is four wrapped recordings, not four
adaptive agents. The replay penalty is 877 points, so a recording is not the team
that produced it, and an adaptive opponent could react to a price move in ways no
recording can.

## Wave 3: what is the wrapper actually worth? (2026-08-13, 54,560 episodes)

Waves 1 and 2 closed market interference. Wave 3 turns the same instrument on the
agent's own structure, sweeping three thresholds that are literals in the donor
rather than named constants -- `tools/perturb.py` hoists them by regex and fails
loudly if a pattern does not match exactly once. Controls: `pctl` 49.6%
[43.4, 55.8], `pnul` 49.6%, paired margin $+34 ± 514.

### Buying land is not optional: 0.0% in both conditions

`_X_NO_LAND` suppresses the tape's BUY_LAND orders -- k01 buys two for $3,000,
and all 371 mined lines buy two or three. The arm won **zero of 5,208 mirror
episodes and zero of 20,832 field episodes**. It is the largest effect measured
in three waves.

This also fences off an earlier note. `RUNS.md` records that a second quadrant
made *our own engine* worse -- 32 of 50 tiles idle while hands walked further.
That was our engine. The ladder disagrees: across 643 real ladder episodes the
opponent's median holding is 3 quadrants with 40 idle tiles. Idle tiles are not
the cost they looked like.

### Starting liquidation at 600 instead of 680: +17 points, mirror only

```
mirror (vs an identical copy)          field (vs w39/w48/w16/w68)
          l600    l680    l720                  l600    l680    l720
t708     69.2%   46.4%   46.0%                 91.8%   91.2%   91.2%
t714     66.5%   49.6%   52.8%  <- donor       91.8%   91.4%   91.4%
t717     66.5%   49.6%   52.8%                 91.8%   91.4%   91.4%
t720     64.9%   50.4%   50.8%                 91.8%   91.4%   91.4%
```

`t714.l600` is 66.5% [60.4, 72.1] against the control's 49.6% -- clean and
significant. The same cell against the field is 91.8% [90.0, 93.4] against
91.4% [89.5, 93.0]. Intervals almost entirely overlap.

Third time in three waves that a large mirror effect is worth nothing against a
non-identical opponent. Selling earlier than your clone is front-running your
clone; a stranger is not on the same schedule.

### The only board-reading component in the agent is worth $4

`_terminal_action` reads tiles, assigns every hand a harvest/carry/drop task and
sells what it collected. It is the sole closed-loop part of the file, and it owns
six turns of seven hundred and twenty. `t720` disables it completely:

```
seed 777        t714 $83,465    t717 $83,465    t720 $83,461
step 717 farmer      NORTH           WEST            WEST
step 719 farmer    HARVEST         HARVEST         WATER
```

The actions genuinely differ; the money does not. Field win rate is 91.4% with it
and 91.8% without. Running it *longer* degrades monotonically -- 91.2% at t708,
88.0% at t696, 69.3% at t672, 31.5% at t624 -- because it harvests and carries but
never plants, waters or feeds. Disabling `_terminal_liquidation` (`l720`) costs
nothing either.

Note against a past decision: submission `55442784` was justified entirely by
moving this threshold from 717 to 714, measured at +2.9 points with disjoint
intervals against `bench3`. Here t717 and t714 return identical win rates in all
six cells and identical money on every seed tried. That does not refute the
bench3 measurement -- the field is different and the space is non-transitive --
but the effect does not reproduce.

### What this means for the route

The agent's strength is the recording. The wrapper's two terminal components are
worth nothing measurable, and the third (sell ordering) has only ever been
measured against a mirror -- wave 1's `A.sort_off` cost 37 points there while
moving nothing at all against `starter`. Nobody has run the sort dials against
the field; that is the cheapest open question left and it is one job.

If the wrapper is worth as little as this suggests, the 877-point replay penalty
is not a wrapper problem to be tuned away. It is the plan, and Road C is the only
lever.

## What actually couples the two players (2026-08-13)

Three questions, all answerable from data already on disk.

### In a mirror, weeds are the only tie-breaker

Two byte-identical agents on the same seed. Set `weedSpawnChance` to 0 and every
mirror episode ends in an **exact tie**, to the dollar, on every seed tried.
Restore it and the margins reappear.

The mechanism is in `_end_of_day`: one `random.Random((seed * 1_000_003) ^ day)`
serves both farms in player order, and `_spawn_weeds` draws only on empty tiles
(Python short-circuits `tiles[y][x] is None and rng.random() < chance`). Player 0
consumes the first N draws, player 1 the next M. Different draws, same stream.
Nothing else in the engine is asymmetric: market slots resolve index by index
against the same pre-commit inventory, and the town is shared.

Pooled over 2,048 control-vs-`k01` mirror episodes across three waves:

```
exact ties                     804 / 2,048  = 39.3%
non-tie margin, median         $717      (25th $180, 75th $1,857, 90th $7,448)
```

On the real ladder, 664 episodes, **zero exact ties**, median margin $10,392.
That is the useful contrast: a monoculture of one recording plus one wrapper
would tie 39% of the time. The ladder does not, so the field is not a
monoculture -- and it also explains why a few hundred dollars of consistent edge
flipped 28 points of mirror win rate in wave 1. The baseline margin is literally
zero.

### Where `topline` loses on the ladder: it peaks at day 15

59 ladder episodes, 46-13. Our own digest is identical in wins and losses --
open-loop replay -- so every difference is the opponent's.

```
our lead, median      d5      d10     d15      d20     d25     d29
wins                 -407   +1,490  +9,602  +8,994  +8,572 +11,284
losses                +80     +537  +7,200  +3,981    +837    -632

still ahead in losses:  d15 92%   d20 77%   d25 54%   d29 31%
```

We are ahead at day 15 in twelve of thirteen losses. The lead then decays
monotonically. In wins it grows. Day 15 is where we stop gaining, not where we
fall behind.

What the opponents who beat us do differently -- and it is not selling more of
what we sell:

```
                 us    opp (we win)   opp (we lose)
cows             10         8              8
milk sold       279       241            320
wool sold       120       138            154
strawberry      227       286            300
fertilizer    1,708       235            300
wheat         1,037       455            479
weeds left       13         5              5
```

**Ten cows produce 279 milk for us; eight cows produce 320 for the agents that
beat us.** 28 per cow against 40. We hire more (277 orders against 266), own more
animals, sell more than twice the total volume, and lose -- because 2,745 of our
3,511 units are fertilizer and wheat, one dumped at 3.5x its depth to a $1 close
and the other floored at $17.

### The shop draw is a coupling channel worth up to 20 points

Eight shop instances are drawn with replacement from eight shops, one every three
days, and each consumes fixed products every fourth step. That draw decides which
markets stay above the price floor. Measured over 4,096 episodes of an unmodified
`k01` against four mined ladder lines:

```
milk-consuming instances   n     win%          our $     their $   final milk price
0                        100    64.0%         58,964     61,066         $1
1                        392    88.8%         73,578     67,866         $1
2                      1,036    84.9%         76,804     71,487         $1
3                      1,024    92.6%         92,108     80,446         $1
4                      1,048    95.4%        105,930     94,344        $47
5                        420    98.1%        111,990     99,652       $197
```

The right-hand column is the mechanism. At three milk shops or fewer the milk
market is saturated and closes at the floor; at four the town drains enough to
keep it alive, and at five it closes near base price. Win rate spans 64% to 98%
and our bank spans $58,964 to $111,990 across a variable neither player controls.

Carrot shops run the other way (-6.4 points at three or more) because the eight
instance slots are zero-sum: a PET_CAFE is a slot that is not draining anything
we sell.

Two refinements that matter more than the headline:

**It is opponent-specific.** Against `w48` the effect is +20.0 points
(78.1% -> 98.0%, disjoint); against `w16` +10.5; against `w39` +2.0 and `w68`
+0.6, both nothing. The shop draw decides a matchup only when the two plans have
different product mixes. This is the coupling asked about, and it is not the
market inventory directly -- it is whose product mix the town happens to want.

**Earlier is better, monotonically.** Position of the first milk shop in the
unlock order: d3 96.4%, d6 90.4%, d9 89.6%, d12 83.0%, d15 79.2%, never 64.0%.
Cumulative drain explains this without needing an adaptation story.

### The opening this leaves

`obs["town"]["unlocked_shops"]` is public and fills up one entry every three
days, so by day 12 an agent has seen four of eight. Which markets will stay
liquid is therefore *knowable in-season*, and it is worth up to 20 points against
a given opponent. An adaptive agent can shift its product mix toward the draw. A
recording cannot -- it plants what it planted.

That is a concrete, measured mechanism for part of the 877-point replay penalty,
and unlike everything else in these four waves it is not a mirror artefact.

## Wave 4: the sell-ordering layer is the one part of the wrapper worth having

72 cells over `_SORT_KEY` x `_SELLS_FIRST` x `_RACE_WEIGHT` x promotion policy,
94,720 episodes, mirror and four mined ladder lines. Controls `qctl` and `qnul`
both 50.0% [43.9, 56.1], paired margin $+0 ± 503.

```
_SORT_KEY   field win%      interval        per opponent
impact        91.0%     [89.1, 92.6]    w39 93  w48 86  w16 87  w68 98   <- donor's
gross         87.5%     [85.3, 89.4]
off           86.9%     [84.7, 88.8]    <- reordering disabled
unit          81.2%     [78.6, 83.4]
```

`impact` against `off` is +4.1 points with disjoint intervals, and against the
worst key +9.8. **This is the first effect in four waves that survives a
non-identical opponent.** It is also the only dial in the file whose ranking rule
assumes the opponent is selling at all: `impact` ranks a sell by the revenue lost
to going second -- quantity times its own price impact -- rather than by revenue
at stake. Market competition is real, worth about four points, and the donor
already found the right rule for it.

Everything else in the layer is a mirror artefact or nothing. `_SELLS_FIRST`
scores 69.3% in the mirror and 91.0% in the field, identical to leaving it off.
`_RACE_WEIGHT` costs 5.7 points in the mirror and 0.4 in the field. Dropping
`_PROMOTE_IF_OPP_MONEY` -- the only rule in the whole agent that reads the
opponent's bank -- moves the field from 91.0% to 91.3%, well inside the interval.

### The wrapper, priced

```
sell ordering (_SORT_KEY='impact')      +4.1 points vs disabling
_terminal_action (board-reading)        $4 on $83,465; 91.0% with, 91.3% without
_terminal_liquidation                   0
_RACE_WEIGHT / _SELLS_FIRST / _PROMOTE  0 in the field
_RESERVE / _RAMP_* / _SHED_PRESSURE     dead code, and _RESERVE is broken
```

Four points. That is what the adaptive layer is worth against real recordings,
and it is already at its best setting. The 877-point replay penalty is not in
here.
