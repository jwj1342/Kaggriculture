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
size in `docs/ROADMAP.md §11` — **eleven landed, seventeen were rejected**.

**Three more on 2026-08-11**, also read from shard JSONL rather than ingested,
and for a second reason: all three carry builds that share basenames across
directories, and `short(path)` is the basename, so ingesting would merge them
into one ratings row — the defect that corrupted runs #22 and #32.

| label | arms | episodes | outcome |
|---|---|---|---|
| `bootlock` | 3 engines × 6 produce × 2 land | **137,664** | the opening seed freeze is a trade, not a deadlock — rejected, `ROADMAP.md` §11 |
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

**3,397,241 episodes total** across 87 runs, plus 737 real ladder episodes. Regenerate these three numbers with `python tools/db.py stats` -- they are the only figures here that drift, and they drift every time anyone runs anything.

The `文档` table in the top-level `README.md` indexes every document by question.

Runs #1–#6 ran on an engine with two defects that hurt crop plans much more than
herd plans, and on a library that could not issue `FERTILIZE`. **Do not compare
their numbers with #7's.** `docs/ROADMAP.md §11` §4 has the controlled A/B and
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
differences as hypotheses; `docs/VALIDATING.md` §6 has the arm sizes that settle
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
384/384 apart locally. `docs/ROADMAP.md §11` is the diagnosis: the field we were
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
  (`docs/ANALYSIS.md`).
- **Main effects in `docs/LEADERBOARD.md` are unbalanced** by construction, because
  the composition plans do not sample the axes evenly. The balanced versions are
  in `docs/ROADMAP.md §11` and they reverse some orderings.
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

## Wave 5: correcting the demand model does not rescue the shop-aware dial

`_remaining_drain` is the only code in the agent that reads
`town.unlocked_shops`, and it does not match this engine -- it fires the town
centre every 12 steps with a 1/2/4 multiplier stepping up on days 10 and 20,
where the engine fires it every 24 with multiplier 1. Against 200 real ladder
shop draws it overestimates by 1.3-1.8x on most products and 4.7-6.7x on melon,
whose entire estimate is the wrong term because no shop consumes melon.

It feeds `_race_factor` alone. 20 cells, 56,320 episodes, controls 50.0%/50.0%,
and the design's own pre-registered self-check passed: at `r0` the donor and
fixed cells are identical to the decimal, confirming the model is unreachable
when the weight is zero.

```
pooled over every race > 0 cell, field, 16,384 episodes each
  donor model   86.27%  [85.73, 86.79]
  fixed model   86.62%  [86.09, 87.13]     +0.35, intervals overlap

pooled over both models, field, 8,192 each
  r0 (off)      87.67%  [86.94, 88.37]     <- donor's value, and the best
  r05           87.21%
  r1            86.63%
  r2            86.24%
  r4            85.69%  [84.92, 86.43]     disjoint from r0
```

Racing is monotonically harmful under both models. Fixing the model does not
rescue it.

**A pre-registered prediction, refuted.** The design file said a truer model
reports less remaining demand, so `_race_factor` fires harder, so the corrected
version should be *worse*. It is marginally better instead, and inside noise. The
mechanism offered for wave 1's result was therefore wrong in direction; the
honest reading is that correcting the model barely changes which products get
raced, because the mechanism is worthless either way.

Production cannot respond either: PLANT names its crop in the action and the
engine drops every plant request for a crop when seeds are short, so editing
BUY_SEED redirects nothing and can destroy a turn's planting.

That closes shop-response through the market layer. The 34-point spread the shop
draw controls is reachable only on the production side, and the production side
is the tape.

## The prospective test of the panel, resolved (2026-08-14)

Written before the result, in `RUNS.md` and `docs/TODO.md`: two agents from the
same source team, the same market layer, the same packaging, differing only in
which recorded episode they replay. `k01` scored 92.4% on the fixed ten-opponent
panel and `k06` 98.5%. Three outcomes were declared in advance -- clearly above,
level, or clearly below.

```
submission          eps   W-L    cum loss  trail-18  trail-30  2nd half   score
55489160  k06        94  74-20     21.3%     27.8%     26.7%    25.5%   2612.3
55484175  k01        59  46-13     22.0%     27.8%     40.0%    40.0%   2391.6
```

**Clearly above, by 220.7 points.**

Rule 7 is satisfied in the way that matters, though not in the way it is written.
`k01` has converged: its trailing-30 loss rate is 40.0%, past the one-third line,
and its score has turned over (2413.9 -> 2418.2 -> 2421.9 -> 2391.6). `k06` has
*not* -- 26.7% trailing-30, still winning three in four, still climbing. But it
has 1.6x the episodes of the converged incumbent and sits 220.7 points above it.
The rule exists because a climbing agent's score is a floor; a floor that is
already 220 points clear of a settled comparison can only move away from it.

**Panel win rate predicts the ladder when the source team is held constant.**
That is the first local measurement in this repo with any validated relation to
real strength, and it is a pre-registered prediction rather than a correlation
found afterwards -- `docs/ROADMAP.md` §10.5 is what happens when you look for the
correlation first.

**It is n=2.** One comparison, in the predicted direction, with the confound that
killed §10.5 (different source teams) deliberately removed. It does not license
ranking across teams, and it does not license using the panel as a search
objective without a second confirmation.

### Two numbers that change with it

**The replay penalty is 630.8 points, not 877.** `カワシギ` is still #1 at 3235.7
and our copy of their recording now scores 2604.9 on the leaderboard: **80.5%
retained**, against 73% when measured with `k01`. Picking a better episode from
the same team recovered about 246 points of the penalty, which is most of what
plan selection can be worth.

**"Copying recordings cannot reach the prize zone" was too strong.** The top-ten
threshold is 3061.4 and a perfect copy of the #1 team would be 3235.7 -- the
ceiling is inside the prize zone. The barrier is retention: reaching tenth from a
#1 recording needs 94.6% where we get 80.5%. Whether a recording can ever retain
94.6% of an adaptive agent is a different question, and the honest answer is
probably not, but the arithmetic no longer rules it out on ceiling alone.

### Where the team stands

```
4,356 teams.   RL is all you need: #348, 2604.9, top 8.0%

  rank    1  3235.7        1 -> 10    19.37 points per rank
  rank   10  3061.4       10 -> 20     3.95
  rank   50  2916.2       50 -> 100    1.20
  rank  100  2856.3      100 -> 200    1.22
  rank  348  2604.9  <-  200 -> 348    0.88
  rank 2000   817.8      348 -> 500    1.16
```

At our position one point is roughly one rank -- #344 to #352 spans 4.4 points
across nine teams. +130 reaches #200 and +251 reaches #100. The top ten is a
different regime: 174 points across nine ranks.

## The TorchRL unification A/B (2026-08-18, one H100, 2 × 44.2M lane-steps)

The `rl-baseline` and `tensorize` branches merged to main today, with TorchRL
as the training framework gluing them: `EpisodeT` wrapped as a batched
`EnvBase` (`rl/tensor_env/trl_env.py`), the masked two-head policy as a custom
distribution (bit-exact against the hand-written math, `test_trl.py` gate i),
and the update loop as swappable loss modules (`rl/train.py --algo ppo|a2c`).
Per the repo rule -- an engine-adjacent change gets an A/B, not an argument --
both trainers ran the same budget on the same GPU before the hand-written
loops were declared superseded.

Setup: B=1024 episodes per iteration, 60 iterations, seed 0, learner vs the
tensor starter, identical coefficients (GAE 0.999/0.95, clip 0.2, entropy
0.003, Adam 1e-4). `slurm/rl_ab.sh`, job 20053670 (arm A) / 20057312 (arm B).

```
arm  trainer                 steps        win@36  final win  final money  mean sps
A    train_t.py (hand)       44,175,360    1.000     1.000       14,859     49,177
B    rl/train.py (torchrl)   44,175,360    1.000     1.000       24,966     46,440
```

Arm B's curve: 0.014 (it 12) -> 0.47 (it 18) -> 0.92 (it 30) -> 1.000 (it 36
on), against arm A's 1.000 from it 30. Same milestone, one-arm-later; the
TorchRL arm then keeps improving the margin (24,966 vs 14,859 final money)
where the hand arm plateaus at ~14k. Framework tax on throughput: -5.6%.

Caveats, so this table is not over-read: money-vs-starter is the shaped
training objective, not a ladder statement; the two arms share coefficients
but not sampling RNG paths, so curves are not lane-comparable -- equality of
the mathematics is established by the bit-exact gates in
`rl/tensor_env/test_trl.py`, and this A/B only had to show the framework does
not *lose* anything at equal budget. It gained instead.

Two failures on the way, both now in the code as comments: the first arm-B
attempt OOMed inside torchrl's GAE (`torch.stack` of obs + next.obs wanted
26.7 GiB on top of the collector's two 29 GiB copies; fixed with
`shifted=True` + buffer-reuse collection), and the first eval-chain attempt
died printing checkpoint metadata (`global_step` is the rl-baseline key,
torchrl checkpoints carry `iter`). The dependency-chained eval job followed a
failed parent and had to be cancelled -- `afterok` on an OOM-bound job wastes
a queue slot, nothing more.

The acceptance chain then ran end to end on the arm-B checkpoint: export as
`pitchfork` (numpy agent + weights.npz) -> ten-opponent roster, 48 seeds a
side, 96 episodes per pair (`slurm/rl_eval.sh` with RUN/CKPT/NAME env vars,
job 20059228, 2.5 minutes at -j 32):

```
opponent            games    win                 margin
random                96   100.0% [96.2,100.0]  +20,615   BEATEN
starter               96   100.0% [96.2,100.0]  +16,562   BEATEN
ghost-89825016-0      96    44.8% [35.2, 54.7]   -3,158   unresolved
ghost-89830307-0      96    40.6% [31.3, 50.6]   -3,492   unresolved
barnyard/enhanced/ledger_lena/spar x2/w49        0.0%     LOST
```

2/10 beaten. This checkpoint is the A/B artifact -- plain PPO against the
starter, no BC, no curriculum, no league -- so what this table certifies is
the pipeline, not the agent: a torchrl checkpoint now flows unmodified
through export -> roster -> scorecard (`rl/eval_summary.py --run trl-ab`).
The closed line needed BC + curriculum + league to reach its 4/10; those are
the hooks to wire into `rl/train.py` next (the league's opponents are already
representable on-device via `trl_env.FrozenPolicyOpponent`).

## foothold: the smoothing stack works; self-play still cannot leave its own basin (2026-08-19)

First combined run of the smoothed-gradient machinery (`rl/configs/foothold.yaml`):
residual policy over the pitchfork prior, curriculum starter -> pitchfork with
a handicap ladder (800 -> 400 -> 200 -> 0), league self-play snapshots, bounded
terminal margin 1.5 + win bonus 1.5, 5% opponent noise. Jobs 20078618/20078619
(chained via --resume), eval 20078620. 240 iterations, 176.7M lane-steps,
mean 35.5k sps (frozen-net opponents cost ~25% vs starter-only).

Mechanically, everything did its job: the curriculum climbed the entire ladder
inside the first 23 minutes, the resume chain restored pool state across jobs,
and by the end the policy beats its own prior 96% of the time at zero handicap
(money 26k vs 0.2k in those batches). Against its own league, this agent is a
monster.

The roster says none of it transferred:

```
opponent            foothold          pitchfork (prior)
ghost-89825016-0    42.7% [33.3,52.7]  44.8% [35.2,54.7]   level
ghost-89830307-0    38.5% [29.4,48.5]  40.6% [31.3,50.6]   level
barnyard margin     -48,013            -49,006             unchanged
w49 margin          -136,709           -136,480            unchanged
beaten              2/10               2/10
```

Reading: post-mortem §13-vi reproduced at higher fidelity. Crushing your prior
and your snapshots deepens the basin; it does not leave it. The smoothing
tools (margin, handicap) ran correctly but had nothing strong to grade
against -- the strongest tensor-representable training opponent IS the prior.
The binding constraint is now unambiguous and it is not the optimizer:
it is training-opponent strength. TODO #1 (tensorise barnyard/ghost) and
TODO #0 (per-unit action heads, Kilo's structural idea) are the two levers;
the margin/handicap machinery is built and gated, waiting for exactly them.

## siege: a real wall as a training opponent -- the gradient arrives, the action space cannot spend it (2026-08-19)

First run with tensorised barnyard as a curriculum stage (`rl/configs/siege.yaml`:
starter -> pitchfork -> barnyard, handicap ladder, margin tanh at scale 50k,
league, residual over pitchfork). Jobs 20083634/20083635, eval 20083636.
240 iterations, 176.7M lane-steps; barnyard batches run at ~21-23k sps
(the serial task-assignment loop costs ~2x vs starter batches), mean 34k.

The curriculum climbed both early stages inside link 1 (starter, then the
full pitchfork handicap ladder 800->0) and spent ~110 iterations on barnyard
at handicap 800 without ever passing a gate: batch win 0.000 throughout,
learner money on barnyard batches 10.3k -> 11.6k (it ~105) -> back to
~9-10.5k, against barnyard's steady ~55k. The margin signal was present and
graded every one of those episodes; the policy could not convert it.

```
opponent            siege             foothold          pitchfork (prior)
barnyard margin     -48,444           -48,013           -49,006     unchanged
ghost-89825016-0    43.8% [34.3,53.7] 42.7%             44.8%       level
ghost-89830307-0    50.0% [40.2,59.8] 38.5%             40.6%       drifted up, CIs overlap
beaten              2/10              2/10              2/10
```

Reading: this is the cleanest evidence yet for the post-mortem's exit-② claim.
foothold showed self-play lacks the signal; siege supplied the signal --
a full-strength barnyard, margin-graded, 50% of batches for ~45M steps --
and the macro action space still could not shorten the loss by a dollar.
To out-earn barnyard you need its labour engine (a dozen hands cycling
harvest/feed/care at scale), and the macro space's hands run a fixed
priority cascade the policy cannot steer. The per-unit multi-head action
space (rl/TODO.md #0) is now the live hypothesis, with this run as its
baseline: the A/B question is precisely "does -48k move when the policy
can allocate labour".

## breach: labour control does not breach the wall either -- and the probes watched it drift (2026-08-19)

siege + --multi-head (`rl/configs/breach.yaml`): per-hand task heads,
AUTO-biased so iteration 0 plays exactly siege's scheduler. Jobs
20086618/20086619, evals 20086620 (best.pt) and 20093298 (latest.pt).
The early stopper ended the run at iteration 160 of 240 -- six stage-3
probes without improvement -- its first production firing, ~35 GPU-minutes
saved, chain and eval unharmed.

The deterministic probes tell the whole story vs barnyard (fixed seeds,
argmax, no handicap): -34,640 on arriving at stage 3, then -47.5k, -45.9k,
-46.5k, -48.5k, -42.3k, -67.9k -> stop. While the policy crushed the rest
of the pool (batch win ~1.0, money 20-23k vs snapshots/pitchfork), its
barnyard margin DRIFTED AWAY. The reference-engine eval agrees with the
last probe almost exactly (-67,270 vs -67,915 -- the probe machinery is
well calibrated): ghosts 39.6%/36.5%, still 2/10.

```
barnyard margin   pitchfork era  foothold  siege    breach(latest)
                  -49,006        -48,013   -48,444  -67,270
```

Two mechanism findings along the way: best.pt's probe ratchet compared
scores across frontiers (a 0.97-win stage-2 probe outranks every 0-win
stage-3 probe; best.pt froze at ~iter 80) -- fixed to final-stage probes
only; and probe-vs-eval agreement validates fixed-field probes as a cheap
stand-in for reference-engine evals during training.

Reading: exit ② alone is not the key. The gradient reaches the policy
(siege), the policy can allocate labour (breach), and it still walks
downhill toward the pool mix instead of the wall. The two live hypotheses:
(a) objective -- nothing prices the ANIMAL ENGINE that makes barnyard's
55k; Kilo's future-credit potential (--potential future, already ported
and gated) does exactly that, one flag away from an A/B; (b) pool
dynamics -- the beatable half of the pool owns the reward hill; a
barnyard-weighted or barnyard-only phase would isolate it. Both are
single-variable follow-ups on breach's config.

## The 2x2 on breach's config: solvency and sell timing learned; the wall is made of labour (2026-08-20)

The breach verdict pre-registered two hypotheses -- (a) the objective is
blind to the animal engine, (b) the beatable half of the pool owns the
reward hill -- and both are single flags on breach's config, so they ran
as a factorial with breach as (0,0): `foresight` (+ `--potential future`),
`grudge` (`opponents: barnyard` alone, league off), `vendetta` (both).
Jobs 20163860-71: three ~50-min links per arm, dependent roster eval on
best.pt. foresight completed 240 iterations (176.7M lane-steps); grudge
and vendetta early-stopped at 179 (stagnated, 132.5M).

Probe shape, identical in all three arms: pinned at -66..-68k (the breach
endpoint band) for the first ~70 barnyard iterations, then a ~20k jump
once each arm had ~50M lane-steps of margin-graded barnyard batches, a
peak near -41..-43k, and then degradation -- vendetta's last probe fell
all the way back to -68.5k. Peak-then-collapse is the regime's normal
behaviour, not an accident of breach; the final-stage-only best.pt
ratchet is why the artifacts keep the peak (vendetta eval -40,990 vs its
best probe -40,800 -- calibrated again). Win stayed 0.000 against
barnyard everywhere: no arm took a single game off the wall.

Roster (96 games per pair, best.pt), breach alongside:

| arm | barnyard | ghost-25016 | ghost-30307 | spar-grazier | beaten |
|---|---|---|---|---|---|
| breach (0,0) | -67,270 | 39.6% | 36.5% | -- | 2/10 |
| foresight (a) | **-36,607** | 0.0% (-21.7k) | 0.0% (-21.2k) | -67.8k | 2/10 |
| grudge (b) | -42,801 | 39.6% (-4.3k) | **45.8% (-2.6k)** | **-46.7k** | 2/10 |
| vendetta (ab) | -40,990 | 12.5% | 10.4% | -68.9k | 2/10 |

Three findings:

1. **What the recovered ~25-30k is made of.** Seed-1000 traces of the
   peak policies against barnyard: both potentials fixed the bankruptcy
   (cash buffer held, hands paid and retained, weeds ~zero -- breach's
   farm lost its whole crew to unpaid wages by day 9) and both learned
   first-harvest timing (sell day 11 at ME 136-152 for +10-13k; breach
   held until the price hit $1). Solvency plus sell timing, nothing else.
2. **The future potential buys wall margin with generality.** foresight
   is 6k better on barnyard and CATASTROPHIC everywhere else: ghosts
   40->0%, spar margins worse than breach. grudge (networth) kept the
   ghosts at 40-46% -- ghost-30307 at 45.8% is the multi-head line's best
   recording result -- and improved spar. The narrow specialist earns
   ~12k absolute; that loses to any opponent that simply farms well.
3. **Neither hypothesis was THE constraint.** All four factorial cells
   stall at 0 wins. The traces say why identically: NEITHER PEAK POLICY
   EVER BUYS AN ANIMAL. foresight goes dormant on day 22 with 100 melons
   rotting in the shed; grudge tiles the farm with 25 EMPTY pastures.
   The mechanical cause was measured while these arms ran: barnyard's
   hands do 83% of its feeding (181 hand-FEEDs/episode plus the wheat
   logistics), an animal escapes at two unfed days, and the hand
   vocabulary had no FEED task -- the 55k engine was unreachable in the
   action space no matter what the objective priced or the pool sampled.

The FEED hand task is now built and gated (M1-M5 incl. a behavioural
gate: hands alone sustain a herd, device == CPU bit-exact; BARN/B3B/TRL
suites green), alongside two tools from the literature review for the
rounds after: `--pfsp` (win-rate-weighted pool sampling, AlphaStar
f_hard) and `--kickstart barnyard` (annealed teacher CE on the learner's
own states, Schmitt et al. / the Lux-S1 recipe; gates K1-K3). Next:
`herdsman` = vendetta + FEED, the single-variable action-space test, and
`drover` = herdsman + kickstart on top.

## parrot: pure BC of the current-balance top ladder collapses on deployment (2026-08-20)

The cold-start experiment the recordings invited: 55 post-rebalance
episodes (both seats, ~3.1k players, 100-146k games) -> 74,776
(obs, head-label) pairs by inverse decode (state-level fidelity: farmer
94.3%, hand work 85.1%, market 55.9% -- the metered-sell gap, TODO #8)
-> 12 epochs of class-weighted CE on MultiActorNet (val acc 0.61 / 0.90
/ 0.58, market argmax-NOOP held at 0.60 by the weights). Jobs 20172754
(train, CPU) / 20172755 (roster).

Roster: **1/10** -- loses even to starter (-564). The trace says why in
one line: it builds 4-6 pastures on day 0-1 and then freezes, money
pinned at $3,000 to day 27. Per-step accuracy is dominated by mid-game
states; the ~110 opening sequences that decide everything drown, argmax
locks onto the modal action, and one step off-distribution has no
recovery -- the same compounding drift that killed the old line's
barnyard clone at 79% per-step fidelity. Pure BC without on-policy
correction or search stays a dead artifact at this scale, exactly as
both the Kaggle-winners survey and our own §11 history said it would.

What survives: the dataset and its fidelity ledger (the market head's
55.9% is measured motivation for SELL_HALF), the sell-pattern
measurements, and the contrast experiment -- drover's kickstart puts
teacher labels on the LEARNER's own states, which is immune to this
exact failure by construction. mynah (BC-init + RL fine-tune) stays
staged but unlaunched: a frozen-pasture prior is a worse basin than
pitchfork.

## The anatomy of a 231k season (2026-08-20, 40 top-ladder seats, current balance)

Sell-revenue decomposition of the kept replays (price-at-sale, 20
episodes x both seats -- everyone here is a ~3.1k player):

| product | share | units |
|---|---|---|
| FERTILIZER | **29.7%** | 63,294 |
| WHEAT | 21.3% | 43,922 |
| STRAWBERRY | 16.6% | 10,815 |
| MILK | 13.4% | 10,398 |
| WOOL | 9.9% | 6,712 |
| MELON | **7.0%** | 3,996 |
| TOMATO+CARROT+EGG | 2.2% | -- |

The top of the ladder's #1 income line is SELLING FERTILIZER -- the
animal engine's real cash product, collected at herd scale -- with a
wheat-crop cash flow second and melons a 7% afterthought. Trajectory:
~4 animals by day 2 (animals FIRST, not after a melon harvest), 9 by
day 8, plateau 14.6 with ~12 hands, land 1->2->3 by day ~10, ~60 crop
tiles including ongoing strawberries. Mean sell revenue $231,656/seat.

Every arm this line has trained is anchored to the melon monoculture
the pitchfork prior discovered against the starter -- the top meta's
smallest revenue line. This table is the target program: fertilizer
and wheat throughput, early animals, strawberries, metered sells
(SELL_HALF just landed for exactly this).

## herdsman: expressiveness is ruled out -- FEED alone does not summon the herd (2026-08-20)

vendetta + the FEED hand task, single variable (rl/configs/herdsman.yaml,
jobs 20169415-18, eval 20169419). Ran the full 240 iterations, 176.7M
lane-steps; the probe ratchet walked -68k -> -38.8k (it 79, ahead of
vendetta's whole run at the matched checkpoint) -> -33.8k peak.

Roster (best.pt): barnyard **-33,965** -- the line's best wall margin
(vendetta -40,990, breach -67,270) -- with broad margin gains
(enhanced/main -59k -> -45k, ghosts -18k -> -12k) and still **2/10**,
win 0.000 on the wall.

The mechanism question is answered by the trace: **zero animals in
176.7M steps**. The whole gain is melon-economy polish (first wave sold
day 11 at 16.1k, second wave still rots). FEED made the animal engine
REACHABLE; nothing made it REACHED -- the BUY -> BUILD -> PLACE -> FEED
chain never assembles under on-policy exploration, whatever the
potential pays for it once assembled. After siege (signal), breach
(labour steering) and herdsman (task vocabulary), the wall's remaining
suspects are exploration and the objective's blindness to the
fertilizer stream -- which is what drover (teacher CE on own states,
running) and granger (kickstart + measured build-curve credit + no
melon anchor + an opponent-noise ladder, launched from the rebalance
worktree) are for.

## drover at 170 iterations: the kickstart trades the wall for the field (2026-08-20)

herdsman + --kickstart barnyard (rl/configs/drover.yaml, jobs
20169420-24, eval 20169425; the 5-link chain ran out at 170/240 -- 9.6k
sps under the double barnyard compute -- so an extension chain
20181559-61 continues it; this is the interim verdict).

The teacher CE annealed to zero by ~110M steps, batch money then climbed
to 18.5k -- the highest any wall arm has shown. The roster is the exact
MIRROR of herdsman's trade:

| | herdsman (FEED alone) | drover (+kickstart) |
|---|---|---|
| barnyard | **-33,965** | -40,824 |
| ghost-25016 | 0.0% (-12.2k) | **24.0% (-17.9k)** |
| ghost-30307 | 1.0% (-12.0k) | **38.5% [29,49] (-12.9k)** |
| spar grazier | -65,738 | **-45,079** |
| spar berrybaron | -80,832 | **-63,420** |
| beaten | 2/10 | 2/10 |

herdsman's pure-RL exploration polished one narrow melon line to a
better wall margin and total mode collapse everywhere else; the teacher
CE kept drover honest across the field -- ITS ARGMAX does not collapse
against the ghosts (the sampled-inference A/B on herdsman showed the
same 28-37% ghost strength hiding inside herdsman's weights: sampling
recovered it at the cost of ~10k wall margin; a T-sweep found no single
temperature that keeps both). ghost-30307 at 38.5% with the CI touching
48.5% is one nudge from this line's first recording win.

Alongside: granger (worktree stack: no melon anchor, kickstart,
build-curve credit, opponent-noise ladder now actually reaching
override opponents) posted the line's FIRST NONZERO WINS against
barnyard -- win 0.028 by the end of its noise-0.40 link, a live win
gradient at last. The ladder steps down 0.25 -> 0.10 -> 0 over its
remaining links.

### drover addendum: the stopper had already ruled, and sampling touches even (2026-08-20)

The 170-iteration state IS final -- the fifth link's early stopper fired
(stagnated: six flat probes at ~-50k) and wrote the chain-safe marker;
the extension links exited cleanly by design. And the sampled-inference
variant of the same weights closes the day's arc: **ghosts 40.6%
(margin -1,322, CI to +864) and 39.6% (-1,848, CI to +151)** -- both
recording matchups statistically indistinguishable from even, the
closest this line has come to its first recording win. Spar stays 0%
sampled. rebalance-1327 merged to main (d388291) now both chains are
concluded; granger continues from the worktree it was launched on.

### The ghost matchup is bimodal, not marginal (2026-08-20, 192 games x2)

Per-seed decomposition of drover-samp vs both ghosts (the "even-touching"
matchups): only 12/192 games land within +-3k. The shape is ~50 blowout
wins (+8k) against ~50 blowout losses (-8k): OUR income is tight (p10-p90
15.9k-24.9k) while the GHOST's is wide (12.9k-26.3k) -- we beat broken
tapes and lose to intact ones. No seat effect. The +1k the liquidation
mask recovered moved margins, not outcomes (41% before and after),
because mid-band losses sit at -4.4k median. Flipping the matchup needs
median income ~19.4k -> ~26k -- absolute economy, the animal/fertilizer
gap, not endgame crumbs. That is granger's lane (its noisy-wall batch
money passed 27.4k while this was measured).

## The animal engine turns over (2026-08-20, granger mid-run)

Seed-1000 trace of granger's link-4 checkpoint (zero-noise batches,
money 34.7k and climbing): wheat bought day 0, TWO COWS placed by day 5,
hands feeding on the wheat loop, MILK accumulating (12 -> 30 by day 15),
FERTILIZER stocking (22 units by day 28), liquidation-day sell to a
24,280 finish. Every link of BUY -> BUILD -> PLACE -> FEED -> PRODUCE ->
SELL is alive for the first time in this line's history -- the chain
that 176.7M steps of pure exploration (herdsman) never assembled, put
together by teacher labels + the measured build-curve credit + no melon
anchor. What remains is SCALE (2 cows vs barnyard's 21) and the crop
engine it cannibalised (4-7 melons; capital went to pastures) -- and
the checkpoint tree (steward/reveille/shepherd, forked from this trunk
with the hoarding-subsidy and gamma-annuity fixes) is already searching
the continuations.

## The recordings fall: steward-sampled takes both ghosts at 84-90% (2026-08-20 night)

First generation of the checkpoint tree, first verdicts. steward (the
granger trunk + the two reward-hacking fixes; chain 20189919-21, KILLED
EARLY at 150 iterations by the argmax-probe stopper -- this family's
strength lives in the sampled distribution and the argmax probe is a
lagging indicator, so the stopper and the plain roster BOTH mis-read it:
argmax roster 1/10, loses to starter). The sampled export of the same
checkpoint:

| opponent | win | margin |
|---|---|---|
| ghost-89825016 | **84.4% BEATEN** | +16,336 |
| ghost-89830307 | **89.6% BEATEN** | +18,131 |
| barnyard | 12.5% | **-7,814** |
| main | 0% | -23,465 |
| lena / w49 | 0% | -107,549 / -105,642 |

**4/10 beaten including both recordings** -- the acceptance line's
recording requirement is met; one more opponent (main at -23k or
barnyard itself at -7.8k) reaches >=5/10. This morning these ghosts
were coin flips and the wall was -34k. Alongside: granger's plain
ladder finished at ZERO-noise batch win 0.208 (0.010 -> 0.208 across
L4-L5), reveille (fixes+backplay) ended its L2 at 0.320 blended, and
the k-line stretch test measured the mountain above: k01/k06 out-earn
our best 20:1 (herdsman's argmax earns literally $0 under their market
pressure -- the starkest overfitting exhibit yet; drover-samp holds
6.5k). Discipline for this family from here: dual-mode rosters always,
stoppers off or batch-win-keyed, sampled exports as the deliverable.

### granger's own verdict: the wall at arm's length (2026-08-20 night)

The plain noise-ladder chain completed (L4-L5 at zero noise, batch win
0.010 -> 0.208), and its sampled roster is the line's new high-water
mark: **ghosts 92.7% / 92.7% (+20k), barnyard 27.1% at margin -3,285**,
lena/w49 margins up 55k from the morning (-94/-95k), 4/10 with both
recordings. The argmax roster of the same weights is 1/10 -- the
dual-mode discipline is now mandatory for this family. The trunk's
artifacts are preserved to the main tree and the rebalance worktree is
released; the second generation (steward revival at 300 iters with the
stopper off, reveille and shepherd finals) is on the cards to close the
last -3.3k.

### reveille's verdict and the third generation (2026-08-20 late night)

reveille (fixes + backplay bank) finished all 240: the bank taught even
the ARGMAX mode to fight the wall (barnyard 25.0% at -6,246 argmax --
every earlier argmax was 0%), and its sampled roster opened a fifth
front: **main 15.6% (-9,908, from 0%/-24.6k)**, ghosts 82.3%/82.3%,
barnyard 28.1% (-3,961). Still 4/10. Gen-3 forks from its endpoint:
yeoman = mixed pool (barnyard + the w49 tape via tape_t, pfsp 2.0,
league snapshots), the re-generalization + k-pressure arm.

## draught interim: capacity was binding -- the wide net eats the ladder (2026-08-21 early)

The 4x-wide probe (1024/512 trunk + 512 critic, ~12M params, identical
granger recipe, jobs 20197340-45) against granger's own rung finals:

| noise rung | granger final win | draught final win |
|---|---|---|
| 0.40 | 0.028 | ~0.47 EMA mid-rung |
| 0.25 | 0.396 | **0.918** |
| 0.10 | 0.485 | **0.736** (money 40.6k > wall 36.1k) |

Bigger-is-more-sample-efficient (Neumann & Gros) reproduced exactly: at
matched rungs and fewer steps the wide net dominates every reading. The
decisive zero-noise links are queued behind other users' GPU jobs. The
research verdict (TODO #9) stands confirmed at rungs 1-3: our 3M MLP --
93% of whose weights are the input projection -- was a binding
constraint all along. steward's line is pruned (revival to 300 iters
plateaued at win 0.13; its final sampled roster stays 4/10 with ghosts
at 90.6/96.9%); reveille's lineage continues through yeoman (mixed
pool, L2 final 0.249 blended).

### yeoman (gen-3, mixed pool with the w49 tape): the tape teaches the argmax (2026-08-21)

480 iterations from reveille's endpoint with barnyard + tape:w49 +
league snapshots under pfsp 2.0. The headline: **its ARGMAX beats both
ghosts (93.8% / 86.5%)** -- training against a recorded line fixed the
mode collapse against recordings without inference-time sampling; the
sampled roster pushes them to 99.0% / 96.9%, the line's best. The cost:
the wall slipped (sampled barnyard 11.5% at -36k) as PFSP moved mass to
the beatable tape and snapshots. 4/10 either mode. Lesson for gen-4
pool design: keep the wall's mass floored (f_var-style or a fixed
anchor share) when adding tapes.

## draught: capacity confirmed, and the wall shows a positive margin (2026-08-21 morning)

The 4x-wide probe finished all 280 iterations (12M params, granger
recipe, jobs 20197340-45). Rung-by-rung it dominated the 3M control at
every noise level (0.918 vs 0.396 at 0.25; 0.736 vs 0.485 at 0.10) and
at ZERO noise ended at batch win 0.449 vs the full-strength wall --
granger's control finished 0.208. Capacity was a binding constraint;
TODO #9's roadmap (bigger critic, LayerNorm prerequisites, CNN trunk as
the structural line) is now evidence-backed, not speculative.

The roster: **draught-sampled vs barnyard 55.2% [45.3, 64.8], margin
+504 -- the line's first positive margin against the wall.** Ghosts
75.0% / 82.3%. The eval marks barnyard "unresolved" (CI spans 50%), so
a 384-game resolution run (job 20213873) decides whether the fifth
roster slot -- and with it the acceptance line -- has fallen. Its argmax
mode stays broken (0% wall, 34-41% ghosts): the sampled export IS this
family's deliverable.

## THE ACCEPTANCE LINE FALLS: draught-samp resolves barnyard at 56.8% (2026-08-21 morning)

The 384-game resolution run (job 20213873): **218W-166L, 56.8%
[51.8, 61.6], interval entirely above 50% -- the eval's own verdict:
"A is better."** With random, starter and both ghosts already beaten,
the roster stands at **5/10 including two recordings**: the acceptance
bar this line has chased since its first eval is met. Mirror match is
seat-fair (margin +0 +-1.7k). Full evidence pack with the honest ladder
estimate (~800-950 if submitted; 2000 needs the lena/w49 mountain) and
the user's decision options: docs/ACCEPTANCE-2026-08-21.md. Nothing has
been submitted -- that call is the user's, per standing instruction.

The arc, for the record: 26 hours ago this line had never taken a game
off barnyard (-67,270) and its best roster was 2/10. The pieces, in
landing order: FEED (the vocabulary), the 2x2 (solvency + sell timing),
the anatomy (the target economy), kickstart (drift-immune imitation),
the noise ladder (the first win gradient), the reward-hacking fixes
(the hoarding subsidy), sampled inference (the mode-collapse unlock),
the checkpoint tree (parallel search), and capacity (the 4x net that
carried it over). Every one measured, gated, and archived.

## wrangler: the tape ladder opens (2026-08-21 pre-dawn, jobs 20218380-83)

carter's audit found its curriculum gate unreachable: `advance-at 0.85`
vs barnyard when this line's best-ever EMA is ~0.50 means carter spends
all 480 iterations on stage 0 -- in practice it is a league/pfsp A/B of
draught (50% barnyard / 50% self-snapshots), and the w49 tape it was
named for never enters the mix. Kept running as that A/B; the real
mixed-pool arm is **wrangler**, launched from the k6tape worktree
(91e36bb, deposit-PLACE fix): draught trunk (~350 iters) + granger
recipe, opponents `barnyard -> tape:w49 (84k) -> tape:k06 (100k)` with
**advance-at 0.45** -- a gate the trunk's carried-over EMA (~0.47)
steps through immediately, putting the mix at 50% w49 tape / 50%
barnyard from the first links (the yeoman floor arrives free as the
pool's "earlier" mass). This is the user's requested mixture -- higher
tiers blended in by ratio -- rather than a wall we never summit.
Single variable vs draught-ext: the opponent mixture. Smoke on CPU
verified 3-anchor pool construction and trunk resume under the k6tape
tree; the k06 tape itself is gate-proven dollar-exact (100,032).
Watch: batch win vs w49 tape will read ~0 at first (an 84k open-loop
economy) -- the signal to track is MONEY under tape pressure, not win.
