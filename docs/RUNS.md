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

## Why the 35 tiles stay empty: the planting chain is reachable, not reinforced (2026-08-21)

Action census of cropper-peek (sampled export, 3 reference-engine
episodes vs barnyard, 2,157 farmer turns): BUY_SEED 12, PLANT 5,
HARVEST 20 -- the chain works end to end (wheat is ongoing; 5 plants
yielded 20 harvests), it is just never scaled: ~1.7 plants a game
against the anatomy's ~60. Where the capacity actually goes: FEED 635
+ PICKUP 169 + 1,146 movement turns (53% of the farmer's life is
walking the dairy loop), and the market head -- one action a turn --
spends 18% of them on DEAD HIRE (397 orders with hands already at 12:
silent no-ops, zero cost, zero gradient, so the habit never prunes,
yet each one displaces a possible BUY_SEED). Verdict: not a mask bug,
not an exploration hole -- a credit/scale problem. The marginal crop
has tiny ROI while the farmer is saturated and AUTO hands won't orbit
1-2 plants; there is no smooth gradient from 1.7 to 30 crops.
Side-notes: seed 2000 produced this line's first 70k game (70,762 vs
61,317); seed 3000 lost 42.6k vs 64k -- variance is huge. gen-7
candidates that follow: mask HIRE at the hand cap (kill the dead 18%),
and whatever cropper's 30/crop curve verdict says about the credit
side. (Probe: $CLAUDE_JOB_DIR/tmp/probe_plant.py pattern, worth
promoting to tools/ if reused.)

## The w49 anatomy: planting is hand labour, and our hands cannot plant (2026-08-21)

Census of the w49 tape itself (2 reference episodes vs barnyard,
163k/98k finals): revenue is six lines -- STRAWBERRY 30.4%, MILK 22.3%,
WOOL 20.8%, MELON 11.4%, WHEAT 7.7%, FERTILIZER 7.3% -- on ~177 seeds
a game (we plant ~1.7). The structural fact: **hands do the crops**
(hand ops: WATER 1,744, HARVEST 680, PLANT 352, FERTILIZE 168; the
farmer planted ZERO times), while the farmer specialises in animals
(CARE 150, COLLECT_FERT 146, FEED 134) and walks only 32% of turns to
our 53%. Meanwhile our HAND_TASKS vocabulary is AUTO/IDLE/HARVEST/
WATER/CARE/COLLECT_FERTILIZER/DIG/FEED -- **no PLANT**: the planting
chain we measured this morning is farmer-only by construction, which
is why no credit scheme can scale it -- the farmer has no spare turns.
This is FEED all over again (83% of barnyard's feeding was hand
labour; adding the task moved the wall -48k -> -36k), except bigger:
crops are ~50% of w49's revenue. gen-7 headline: the PLANT hand task
(one new index; crop choice stays in the market head via BUY_SEED --
plant the most-held seed; empty-tile claims serialised like FEED's
wheat reservations). Also noted: w49 spams HIRE too (520 orders, cap
12) -- dead-HIRE masking (TODO #11) loses nothing against the meta.

## sower: the PLANT arm launches on a widened head (2026-08-21, jobs 20220387-90)

The handplant branch (worktree Kaggriculture-gen7, commit ba99608)
gives HAND_TASKS its ninth word: PLANT -- task-only like FEED, empty
tiles as targets, crop = most-held viable seed (deadline-aware; the
market head owns the mix via BUY_SEED), seed-budgeted serial claims.
Full battery green including a new M6 (hands-only planting: 138 PLANTs
across two crops, peak 22 in the ground, farmer never planted, device
== CPU byte-exact) and both tapes still dollar-exact. The era cross:
rl/widen_hands.py Net2Net surgery -- draught trunk (~420 iters), old
head rows copied hand-major, PLANT column zero-weight at bias -4,
self-check proves the policy identical on old columns. sower runs
--init-from that surgery ckpt (fresh optimizer, kickstart re-anneals
from 0.5 -- deliberately: barnyard's hand-PLANT intents now label the
new column, they were AUTO-lossy before). Single variable vs
draught-ext: the vocabulary. Opponents barnyard-only, 200 iters, 4
links. The gen-7 question in one line: with the word available, the
observation channels already present (seeds at g[38:43]), the teacher
labelling it, and the build curve paying for crops (cropper's arm),
does the crop economy finally scale past 1.7 plants a game?

## The k06 anatomy: industrial fertilizer, and the third-tier vocabulary gaps (2026-08-21)

Census of the k06 tape (2 reference episodes vs barnyard, 167k/92k):
revenue FERTILIZER 31.8% (qty 3,342 -- eight times w49's volume),
WHEAT 17.8% (qty 2,132; 276 wheat seeds a pair -- feed AND commodity),
WOOL 14.9%, MILK 14.4%, STRAWBERRY 13.5%, MELON 7.3%. The k-line's
structural step over w49 is fertilizer-led volume production: hand
COLLECT_FERTILIZER 600, hand FERTILIZE 118 (crop yield boost), hand
PLACE 100 (the shed-deposit metering the tape gate needed). Our
infrastructure already covers the big pieces (COLLECT task, SELL
vocabulary, cropper's fert-credit potential term, and now PLANT);
the remaining vocabulary gaps are third-tier: hand FERTILIZE and hand
PLACE, an order of magnitude smaller than PLANT was (118/100 ops vs
352). Herd size is the fertilizer feedstock -- k06 buys ~14
animals/game, our build curve's plateau. Seed variance is huge even at
the top (k06: 167k on seed 1000, 92k on seed 2000).

## draught-ext: the plateau is real -- the recipe has converged (2026-08-21, job 20220502)

The 140-iteration extension (280 -> 420) of the accepted draught trunk,
sampled roster at 96 games/opponent: barnyard 47.9% [38.2, 57.8]
margin -2,217 (the accepted draught-samp resolved 56.8% at 384 games --
not dethroned, not improved), ghosts 75.0%/76.0% (same band),
enhanced/main 0% at -33.6k (was -36.8k), spar/lena/w49 walls unmoved.
Training money sat at 41-43k the whole extension. Verdict: **the
draught recipe is done** -- more compute on the same recipe buys
nothing; the 42k dairy plateau is structural (the anatomies say the
next income lines are crops and fertilizer volume, which this
vocabulary cannot express). The deliverable remains draught-samp@280.
The three levers already in flight are exactly the diagnosis: sower
(PLANT vocabulary), wrangler (tape market pressure), cropper (crop
credit + fert-credit).

## sower-v1 KILLED at iter 3: a fresh kickstart anneal is a wrecking ball on a mature trunk (2026-08-21)

Three iterations: win 0.436 -> 0.000, money 42,948 -> 21,520, entropy
6.84 -> 4.64, while barnyard fattened to 56.8k on our collapsed market
presence. The mechanism: --init-from resets the step counter, so ks
re-annealed from coef 0.5 -- a CE loss of ~1.2 against a policy-gradient
term of ~0.03. Forty-to-one. When granger ran that ratio the policy was
RANDOM and the teacher was pure gain; on a trained 42k dairy machine the
same pull scrambles a coherent strategy into half-barnyard incoherence
within minutes. Chain scancelled (20220387-90), 3 GPU-links saved.
Rule for every future warm restart: **teacher coefficient scales down
with trunk maturity** -- a mature trunk gets a whisper (<=0.05), not
the cold-start dose. sower-v2 relaunches from the same surgery init
with ks 0.05/40M, plus the gen-5 credit terms (aa38644 merged into
handplant cleanly): the crop credit, not the teacher, should carry the
planting gradient.

## Hands are DAY LABOUR, and the 4-hand plateau was our own decode (2026-08-21)

Chasing TODO #11's "dead HIRE" hypothesis with a per-day probe
overturned it completely. The engine's _end_of_day does
`farm["hands"] = []` -- **the whole crew is fired every night**. Hands
are day labour: a full 12-hand day costs fib(0..11) = $376, re-bought
every morning; the tops' HIRE spam (k06: 554 orders in 2 episodes) is
simply the daily payroll, and so were our census's "397 dead HIREs".
Nothing was dead. What WAS broken: our HIRE decode bursts at most 4
hires per action, so a 12-hand morning needs the policy to press HIRE
three times before the day's work -- a habit no arm learned in 400+
iterations. The probe showed it plainly: day 21 hired to 8, day 22
back to 4; a permanent 4-hand farm run by an action cap we wrote
ourselves. Fix (handfert branch, with the FERTILIZE task): burst cap
4 -> 10 (the order-slot bound), budget cap unchanged -- one HIRE
action now buys the working day. Effect available to every future arm:
3x labour for pennies, which is exactly the workforce the crop economy
(PLANT/WATER/HARVEST/FERTILIZE at scale) was missing. TODO #11's
masking premise is retired; measured before masked, and a good thing.

## sower pivots to the gen-8 basket; the whisper dose is validated (2026-08-21)

sower-v2's 43 iterations answered the dose question: at ks 0.05
(annealed to 0.01) the trunk did NOT collapse -- money held 41-42k
throughout, entropy climbed 6.5 -> 8.0 as the policy paid an
exploration tax (win 0.44 -> 0.27-0.32) hunting new behaviour. The
maturity rule holds. But v2 was hunting under-equipped: the gen7 tree
still had the 4-hire burst (a 4-hand farm cannot run a crop economy)
and the first-come-first-served PLANT semantics gate_m2 later proved
wrong. Killed at it 43 (checkpoint preserved in the gen7 worktree) and
relaunched as sower-v3 (20223777-81, roster 20223782) from the gen8
tree: PLANT + FERTILIZE + 10-hire day-labour burst + atomic-PLANT
physics + crop/fert credits + whisper ks. One arm, the full basket.

Interpretive note for every verdict now in flight: draught, carter,
cropper and wrangler all trained under the 4-hire burst -- their
shared 42k plateau has a concrete mechanical reading (a 4-hand farm
against the meta's 12), which the anatomies' labour numbers said all
along. The plateau was never about training method; it was about the
size of the workforce the action space could buy.

## cropper takes the wall at 69.8%; carter trades it for generalisation (2026-08-21, jobs 20220646 / 20213998)

Two verdicts, one morning. **cropper-samp (the credit arm: crop curve
+ fert-credit 0.3 over the draught recipe): barnyard 69.8%
[60.0, 78.1], margin +1,875 -- the interval clears 50% whole, at 96
games; ghosts 96.9% / 91.7%; random/starter 100/99.** The previous
best was draught-samp's 56.8% at 384 games. Single-variable answer:
the gen-5 credit terms work, +13pp on the wall -- and this under the
4-hire day-labour cap, with the planting we know it still doesn't do.
Roster stands 5/10 with fatter margins everywhere; main 0% (-38.7k),
spar/lena/w49 walls unmoved. cropper-samp is the acceptance
front-runner now.

**carter-samp (league/pfsp): the yeoman pattern** -- the wall slips to
8.3% (-33.6k) while ghosts hit the line's best-ever 93.8% / 94.8%, and
**main 10.4% (-10.1k): the first nonzero win rate any arm has taken
off enhanced/main**, at a third of draught's margin deficit. Mixed
self-play pools trade the anchored wall for breadth; as a deliverable
it loses, as evidence it says the pool composition steers exactly
what the theory said it would.

Both arms trained at 4 hands. The gen-8 basket (sower-v3) holds the
credit terms cropper just validated, plus the workforce to use them.

## reeve opens gen-9: the strongest trunk takes the tape ladder with a full crew (2026-08-21, jobs 20224217-20)

The behavioural census of final cropper (3/3 wins over barnyard)
attributed its 69.8% to a tighter dairy loop and doubled fertilizer
collection (COLLECT 15 vs 7) -- PLANT stayed at 5; the crop economy is
still locked behind hand labour, as diagnosed. So gen-9 stacks
everything at once: **reeve** = cropper trunk (surgery 8 -> 10,
verified) x the gen-8 basket (PLANT + FERTILIZE + the 10-hire
day-labour burst + atomic physics + the very credits cropper just
validated) x wrangler's tape ladder (barnyard -> w49 -> k06 at the
reachable 0.45 gate), whisper teacher 0.05. Three arms now in flight:
wrangler (tapes, 4-hand era, control), sower-v3 (basket vs barnyard,
attribution), reeve (the confluence bet). Rosters queued at every
tail. If reeve's hands plant under tape pressure, the w49 margin is
the number to watch.

## First light: the crop-and-fertilizer economy assembles (sower-v3, iter ~28/200)

Mid-link census (3 episodes, sampled export): **hand PLANT 87** (~29
plants a game, from 1.7), hand WATER 180, hand HARVEST 265, **hand
COLLECT_FERTILIZER 567 + farmer 62 = 629 -- k06-tape volume (600)**,
BUY_SEED 143 orders (96 wheat + 46 melon, from 24), HIRE 663 orders =
the daily payroll flowing. The pieces the whole night was built for --
day-labour burst, PLANT/FERTILIZE vocabulary, credit terms -- are
running simultaneously for the first time. Not yet monetised: hand
PASS is 41% of hand-turns (idle workforce), score 1W-2L in close games
(52.6/62.4/20.7k vs 60.4/61.4/22.1k), entropy 12.2 still climbing --
the exploration tax is buying structure. 170 iterations of the chain
remain; the number to watch is win rate converting as crops and
fertilizer reach the market.

## wrangler verdict: pressure without means moves nothing (2026-08-21, job 20220535)

The tape-mixture arm (4-hand era, 50% w49 tape / 50% barnyard after its
reachable gate): barnyard 59.4% [49.4, 68.7] (above draught-ext's
47.9%, below cropper's 69.8%), ghosts 80.2/79.2%, and the number the
arm existed for -- **w49 margin -98,844, statistically where draught
left it (-99,970)**. lena -111.6k, main 0%/-43.0k. Verdict: market
pressure alone cannot conjure an economy the action space cannot
produce; training against a 126k-income open-loop opponent taught
price-crash survival, not production. The attribution matrix closes:
credits +13pp on the wall (cropper), league/pfsp trades the wall for
breadth and the first nonzero on main (carter), tapes alone ~nothing
on the target tier (wrangler). What remains in flight is the only
combination the matrix leaves standing: vocabulary + workforce +
credits (sower-v3, recovered to trunk level at it 55 with the crop
economy inside), plus the same under tape pressure (reeve).

## The night's lineage merges to main, battery-sealed (2026-08-21, job 20227171)

main <- handfert: the deposit-PLACE (k06 tape), hand PLANT, hand
FERTILIZE, the 10-hire day-labour burst, the atomic-PLANT physics fix,
the gen-5 credit terms, and the generalised head surgery
(rl/widen_hands.py) -- 7 files, one clean merge, and the full battery
green on main afterwards (MULTI M1-M7 / B3 / B3B / BARN / KICK / TRL /
PIN / both tapes dollar-exact). Worktrees k6tape, gen5, gen7 are
superseded; gen8 keeps running the two live chains on the identical
code. Anything launched from main is now gen-8-native.

## tiller: the trunk-comparison cell (2026-08-21, jobs 20227799-804)

Third live arm, filling the matrix cell the night still lacked:
**tiller** = the CROPPER trunk (reeve's own widened init, reused) x the
gen-8 basket x plain barnyard, seed 1. Against sower-v3 it isolates
the trunk (draught vs cropper at a fixed recipe); against reeve it
isolates the tapes (same trunk, same basket); and it doubles the
night's chance that one basket arm monetises by morning -- the
checkpoint-tree parallelism the project was asked for. Six links
queued (~260 iters), tail roster 20227805.

## The plateau breaks in training: sower-v3 crosses 0.52 (2026-08-21, iter 74-77)

Twenty iterations after recovering the trunk's level with the crop
economy inside (it 55: 0.429), sower-v3 reads **win 0.513-0.542** --
through the 0.42-0.48 batch-win ceiling that defined every 42k-era arm
of this project, with the teacher at zero and the slope intact
(+0.10 win in 20 iters). The assembled economy is monetising. Money
still ~42k vs 43k (win rate is moving first -- more games tipped, not
yet more income; the income lift is what w49 needs). ~320 iterations
of runway remain; tiller (cropper trunk, same basket) just started
L1 and reeve climbs toward its tape gate behind them.

## Census at iter 100: the economy deepens, the mix shifts to melon (sower-v3)

L2 closed at **win 0.574** (0.43 -> 0.52 -> 0.574 across 33 iters).
Census, 3/3 wins (+14.5k/+6.3k/+2.7k): hand WATER doubled to 363 (the
crops are being maintained, not just planted), hand PLANT holds at
82, COLLECT_FERTILIZER 628, idle hand-turns down (5,594 from 6,027) --
and the seed mix flipped on its own: **MELON 56 > WHEAT 35** (was
96 wheat / 46 melon at iter 28). The policy is discovering melon
pricing under the hinge without any anchor pointing at it -- the
credit terms are crop-agnostic. Money at parity-plus (43.6k vs 43.6k
batch means, wins by margin); the income lift phase is next. L3
runs; ~300 iterations of runway remain.

## reeve crosses the gate: the tape stage begins, this time with means (2026-08-21)

reeve's barnyard EMA touched 0.45 around iter 90 and the pool advanced
to stage 2/3 -- half its batches now face the w49 tape's 84-126k
economy. Tape-batch money starts at ~27k, exactly where wrangler's
sat for its whole run; the difference is that reeve carries the
vocabulary, the day-labour burst and the credit terms. Whether
tape-batch money CLIMBS from here is the entire question wrangler's
verdict posed ("pressure without means moves nothing" -- now the
means are aboard). Runway ~300 iterations.

## Another first: the learner out-earns the wall (sower-v3, iter 102-105)

win 0.60-0.65 and **money 43.6k vs barnyard's 41.6k -- the first
positive batch-mean income margin in the project's history** (every
prior era sat 2-3k under). The curve: 0.43 (it 55) -> 0.52 (77) ->
0.574 (88) -> 0.64 (105), slope intact. The win-rate phase is rolling
into the income phase on schedule; what the w49 wall needs is for
this margin to keep widening as the crop economy scales.

## Deploy check at iter ~110: the curve is real (sower-v3)

Reference-engine validation of the mid-chain checkpoint: **67.7%
[57.8, 76.2] vs barnyard, margin +1,659, median money 45,878** -- the
training climb transfers to deployment intact, and at a third of its
runway sower-v3 already matches cropper-samp's tail (69.8%). Median
income 45.9k is the highest this line has recorded (the 42k era is
over). The tail roster (12 opponents, tier-2 anchors included) will
say what the income curve bought against the walls.

## The counterfactual answers: tape-batch income moves (reeve, iter 96-133)

Under the w49 tape's crashed market, reeve's income climbs 27.0k ->
30.5k across 37 iterations -- the exact number wrangler sat on for its
entire run without means (26-27k, flat). Pressure with vocabulary,
workforce and credits aboard IS trainable signal. Slow (+~1k/10 iters)
but structural; ~270 iterations of runway remain, and every 1k here is
1k off the -98k w49 margin at the tail. tiller tracks sower-v3's
recovery arc on schedule (0.361 at it 46).

## Census at iter ~160: the economy is land-gated now (sower-v3)

3/3 wins (+12.0k/+3.7k/+6.2k, margins growing), but the structure
says the next wall is LAND: BUY_LAND stuck at 1/game (2 quadrants)
while the 60-crop economy needs 3-4. The policy has adapted around
the constraint rather than through it -- seed buying tightened from
143 to 77 orders (it buys what it can plant), idle hand-turns ticked
back up (no land -> no crop chores). Diagnosis: land is underpriced
in the potential (LAND_VALUE = 300 flat, vs the ~5k of downstream
crop credit a quadrant actually unlocks), and the BUY_LAND gradient
arrives only through a two-step chain. First concrete gen-10 design
input from tonight's data: **value land by what it unlocks** (raise
the build-curve land term or make LAND_VALUE scale with seed/crop
flow) -- recorded in rl/TODO.md #13.

## Census at iter 228: the top meta's anatomy, reproduced from scratch (sower-v3)

**win 0.909-0.927, money 52.1k vs barnyard's 42.7k (+9.5k batch
margin).** The census explains it: hand WATER 1,205 (was 405; w49's
tape does 1,744), hand PLANT 126 = 42 crops a game (was 82), HARVEST
441 (was 264), FERTILIZE 30 (was 1), idle hand-turns HALVED to 3,351
(was 6,463) -- and the seed mix moved again, on its own:
**STRAWBERRY 144 > MELON 31 > WHEAT 9**. Strawberry is the top meta's
LARGEST revenue line (30.4% of w49's season, RUNS.md 2026-08-21) and
nothing in the reward names it: the crop-agnostic credit terms plus a
workforce that can water 1,200 times found it. 3/3 census wins by
+13.9k / +18.8k / +13.9k. A 12-opponent roster on this exact
checkpoint is running (job 20233430) rather than waiting for the chain
tail -- if it clears 70% on barnyard this is the new deliverable.
Two arms confirm the arc: tiller 0.761 / 49.5k at it 143, reeve 0.838
/ 52.5k at it 259 (its barnyard batches, while half its diet is the
w49 tape).

## BREAKTHROUGH: sower-it228 rewrites every number (2026-08-21, job 20233430)

Twelve opponents, 96 games each, sampled export of the it-228
checkpoint -- and it is a different agent from anything this project
has produced:

| opponent | sower-it228 | previous best | delta |
|---|---|---|---|
| barnyard | **92.7% [85.7, 96.4]** +11,336 | cropper 69.8% +1,875 | **+23pp** |
| ghost-89825016 | **100%** +34,494 | cropper 96.9% | +3pp |
| ghost-89830307 | **100%** +36,017 | cropper 91.7% | +8pp |
| enhanced/main | **19.8%** -9,753 | carter 10.4% -10,106 | **+9pp** |
| spar grazier | **6.2%** -11,096 | 0% -13,255 | **first nonzero vs spar** |
| spar berrybaron | 0% -18,564 | 0% -28,058 | margin -9.5k |
| **closer_cleo** | 0% **-82,184** | 0% -102,609 | **+20,425** |
| broker_bea | 0% -89,552 | 0% -104,832 | +15,280 |
| ledger_lena | 0% **-91,168** | 0% -105,129 | +13,961 |
| w49 | 0% **-84,468** | 0% -95,976 | +11,508 |

Roster 5/12 with both recordings at 100%, and -- the number that
matters for the ladder -- **every tier-2/3 wall closed by 11-20k in a
single generation**. The 1364-tier deficit went from 2.5x income to
~2.0x. Nothing here is a tuning artefact: the same checkpoint's census
shows 42 crops a game, 1,205 hand waters, strawberry as the lead crop,
idle labour halved. The breakthrough protocol is firing: mirror +
packaging (job 20233780). The chain has ~170 iterations left and the
slope has not bent -- this is a mid-chain checkpoint, not a tail.

## plowman: the land A/B, forked off the breakthrough (2026-08-21, jobs 20234101-04)

The iter-160 census named the next wall (land: BUY_LAND stuck at 1/game
while a 60-crop economy needs 3-4 quadrants) and diagnosed why -- the
potential prices a quadrant at Kilo's flat $300 while it unlocks ~5k of
downstream crop credit. `--land-value` (main tree, default off,
test_trl green) is the lever; **plowman** is the A/B: the sower trunk
forked at iter 251 with ONE change, land 300 -> 1500. The control is
the sower chain itself, still running the same recipe at 300, which
makes this the cleanest single-variable test the project has run --
same trunk, same recipe, same seeds stream, one constant. Four links
(~170 iters), roster 20234105. Watch BUY_LAND per game (1 -> 3?) and
whether crops move past 42.

## The income curve keeps going: 56.9k, and reeve's tape batches hit 38.7k (2026-08-21)

sower-v3 at iter 258-259: **win 0.945, money 56.9k vs the wall's
45.6k** -- +11.3k batch margin, and the income is now 35% above the
42k plateau that stood for the project's whole history. plowman forked
from this trunk reads the same on its first iterations (0.945 / 57.7k
at land 1500, too early to attribute).

reeve, meanwhile, answers wrangler's question completely: its
**tape-batch income is 38.7k, up from 27.0k when the stage opened**
(iter 96 -> 301). wrangler, without the means, sat at 26-27k for its
entire chain. +11.7k of income earned inside a market the w49 tape has
crashed -- that is the mechanism that closes the -84k margin, measured
directly.

## harrow: a pure top-economy diet (2026-08-21, jobs 20234367-69)

Fifth arm, fifth GPU. reeve proved income is trainable under tape
pressure (27.0k -> 38.7k); harrow asks how far that goes when the diet
is ONLY the target economies: the breakthrough trunk (sower @ 251) vs
tape:w49 -> tape:k06, gate 0.30, no barnyard mass, no teacher (ks 0 --
barnyard's intents are the wrong teacher for a 100k economy). reeve is
the mixed control. The known risk is the documented one: open-loop
tapes are exploitable, so the roster (barnyard / main / spar / ghosts
/ tier-2 anchors) is the judge, not the training win rate -- which
will read ~0 by construction. The number that matters: tape-batch
income, and whether the tail roster's w49/lena/cleo margins fall
below -80k.

## SUBMITTED: sower-it228, the RL line's first ladder read (2026-08-21)

User authorised one submission. Pre-flight per SUBMISSION_POLICY: stress
**28/28 clean, worst turn 238ms** (limit 1000), mirror margin +0, package
unpacked-and-played ($60,365), snapshot in
`submissions/2026-08-21-sower-it228/`. Uploaded 19.8 MB; 4 submissions
left today. Side effect noted at submit time: only the latest two are
active, so this retires 55489160 (2035.9 -- a mined top-of-ladder plan
replayed open-loop, not ours and not RL) and leaves the RL v2 baseline
(55542013, 506.9) plus this one. That is the point of the read: RL v2
scored 506.9 while losing 0/96 to barnyard; this agent beats barnyard
92.7% and takes 19.8% off enhanced/main, so the gap between those two
numbers calibrates the whole local->ladder mapping for this line.
Expect a floor, not a level, for the first hours (rule 7: a score does
not count until the agent has lost a third of its games).

## Two tails, two firsts, and a clean complementarity (2026-08-21)

**sower-samp (tail, it 286; basket vs barnyard):** barnyard 96.9%
+15,437, **enhanced/main 55.2% [45.3, 64.8] margin +2,020 -- the first
time this project's RL line has WON against main**, spar grazier 28.1%
(was 6.2% at it 228), w49 -78.1k. Interval spans 50 so main is
"unresolved" pending a 384-game run, but the point estimate and the
margin are both positive for the first time.

**reeve-samp (gen-9 confluence; 50/50 barnyard + w49 tape):** barnyard
94.8%, **spar grazier 61.5% [51.5, 70.6] -- interval entirely above 50,
the first outright win over an `agents/spar/` agent (the field
reconstructed from real ladder replays)**, and the best wall margins
this project has recorded: **cleo -79.1k, lena -78.7k, bea -79.7k,
w49 -70.4k**. Its weakness is exactly where sower is strong: main 8.3%.

The complementarity is the finding: **tape pressure buys wall margin,
barnyard/self-play buys reactive skill against reactive opponents.**
sower is +47pp on main; reeve is 6-22k better on every tier-2/3 wall.
Neither dominates. The next arm has to be the mixture, and that is
what sheaf (below) is.

For the record, the arc of the wall margins in one night:
draught -100.0k -> cropper -96.0k -> sower-it228 -84.5k ->
sower-tail -78.1k -> reeve -70.4k (w49); and cleo -102.6k -> -79.1k.

## sheaf and granary: the mixture and the leak (2026-08-21, jobs 20237088-91 / 20237170-73)

**sheaf** (gen-11 mixture): reeve's trunk -- the best wall margins on
record -- on barnyard + w49 tape + k06 tape **with league snapshots and
pfsp**, plus land 1500. The two tails proved tape pressure and reactive
self-play buy different things and trade off; sheaf trains both at once,
which is the only combination the verdict matrix leaves untried.

**granary** (gen-11 A/B): sower's tail continued with exactly one
change, `--wheat-feed-cap 2.0`. It runs from the gen11 worktree
(c401c8c, WHEAT-PASS: cap-off twins byte-equal, cap-on twins agree and
differ, the promise verified pointwise on a synthetic grid). The
control is sower's own tail roster, already archived. Expected value if
the measurement holds: +21k a game, a third of current income, and the
same again off every wall margin.

Five arms now: tiller and plowman (land A/B) finishing, harrow (pure
tape diet), sheaf, granary. Rosters queued at every tail.

## bourse: the missing term gets an A/B (2026-08-21, jobs 20238051-54)

The gap analysis traced hoarding, the wheat churn and the absent
sell-timing skill to ONE missing term -- the potential believed a sale
does not move the price. `--potential future-exec` (gen12, 37e8623,
EXEC-PASS) values shed stock at what the engine would actually pay for
it, unit by unit down its own price curve. The gate quantified the old
distortion: **a 300-unit milk hoard was overvalued by 37,436** -- more
than a whole game's income. bourse forks sower's tail with that single
change; granary forks the same trunk with the wheat cap; sower's own
tail roster is the shared control. Queued behind tiller's last link to
hold GPU concurrency at five.

## tiller verdict: the arc reproduces, the trunk does not decide it (2026-08-21, job 20227805)

tiller = the cropper trunk on the same gen-8 basket that sower ran on
the draught trunk. Roster: barnyard 94.8% +17,325 (the largest wall
margin any arm has posted), main 37.5% -3,502, spar grazier 19.8%,
ghosts 100/100, w49 -83.9k, cleo -86.5k, income distribution median
40.9k with 16% of games under 20k.

Against sower's tail (barnyard 96.9%, main 55.2%, w49 -78.1k, 10%
under 20k) it is a shade weaker everywhere except the barnyard margin.
Verdict: **the basket, not the trunk, is what carries this generation**
-- two different trunks converge to the same behaviour within noise,
which is the cleanest evidence yet that the vocabulary/workforce/credit
package is the causal ingredient. Trunk choice for future forks can
therefore be made on income-distribution floor rather than lineage.

## The frozen farm, explained: the shaping term punished growth (2026-08-21)

A per-day trace of the submitted agent (sower-it228 vs barnyard, seed
1000) shows the shape of every arm's ceiling: **8 cows and 8 structures
by day 6, then twenty-three days without buying a single animal,
structure or quadrant, while cash climbed from $0 to $46,230 and sat
idle.** No animals died (8 stayed 8). Feeding was 220 farmer actions and
**zero hand actions**. The farm did not fail to grow; it stopped
choosing to.

The cause is in the potential, stacked from two Kilo constants:

1. `ANIMAL_CREDIT 0.4` / `PLANT_CREDIT 0.5` price future production at
   40-50%, so a cow that really returns +720 (7 milk x 160, cost 400)
   reads +48;
2. `UNFED_RISK 0.8` + `UNCARED_RISK 0.3` are charged off the DAILY
   fed/cared flags, so a newly placed animal is charged **1.1x its own
   cost the moment it lands** -- and "not fed yet today" is every
   animal's normal morning state.

Measured deltas for one more cow, net of its price: **day 10 -392,
day 16 -584** -- the dominant reward term was telling the policy that
growth is a mistake, all season, in every arm. That single fact explains
the frozen herd, the 2-quadrant board, the idle cash, and a good part of
the income gap to the 1364 tier (their farms are 3 land / 13 animals).

Fix (gen13, d896f4a, CAPITAL-PASS): `--capital-credit` replaces both
haircuts; `--risk-mechanic` charges neglect the way the engine does
(escape at 2 unfed days, costing that animal's own credited production).
The pair moves day 10 to **+600** and day 16 to **+120** while keeping a
genuinely bad day-22 purchase negative. **byre** (jobs above) is the
A/B: sower's tail trunk, that pair, sower's own tail roster as control.

## harrow rewrites the field: 7/12, the best floor, and wrangler's verdict inverted (2026-08-21, job 20234370)

The pure top-economy diet -- gen-8 basket, w49 then k06 tape, no
barnyard mass, no teacher -- is the strongest product this project has
produced, on every axis at once:

| opponent | harrow | previous best |
|---|---|---|
| barnyard | **100%** +11,804 | sower-tail 96.9% |
| **enhanced/main** | **64.6% [54.6, 73.4]** +3,893 | sower-tail 55.2% (CI spanned 50) |
| **spar grazier** | **84.4% [75.8, 90.3]** +7,037 | reeve 61.5% |
| spar berrybaron | 36.5% -1,879 | reeve 1.0% |
| ghosts | 100% / 100% | 100% / 100% |
| closer_cleo | 0% **-70,040** | reeve -79,128 |
| ledger_lena | 0% **-70,661** | reeve -78,703 |
| broker_bea | 0% **-70,036** | reeve -79,656 |
| w49 | 0% **-68,661** | reeve -70,354 |

**7/12 beaten** (random, starter, both ghosts, barnyard, main, grazier),
income median **47,218** and -- the number the ladder losses pointed at --
**only 4% of games under 20k** (sower-it228, the submitted one: 20%).

And it inverts wrangler's verdict. wrangler concluded "pressure without
means moves nothing": tapes alone, in the 4-hire era, left w49 at
-98.8k. With the means aboard (vocabulary, day-labour crew, credits),
**tape pressure is the best diet we have** -- better than barnyard
self-play (sower) and better than the 50/50 mixture (reeve). The tapes
are not opponents to beat; they are a 100k economy to imitate under
market pressure, and the policy learns the production side from them.

Acceptance chain running (job 20240482: mirror, stress, packaging).
This is the submission candidate whenever the next slot is authorised.

## The library has a 186k tape (2026-08-21) -- threshing takes the pool

harrow reached 7/12 on ONE tape that replays at 83.8k, and its pool
never even advanced past stage 1. Checking what else the mined library
holds, all four gate-verified byte-exact on the current engine:

| tape | replayed money (this engine) | recorded (manifest) |
|---|---|---|
| **w03** | **186,101** | 155,241 |
| k06 | 100,032 | -- |
| w10 | 96,168 | -- |
| w01 | 86,215 | 157,577 |
| w49 | 83,778 | -- |
| w02 | 80,265 | 155,280 |

w03 replays at over twice w49 and above k06 -- the richest economy
available to train against, and it was sitting unused all along.
**threshing** (jobs 20243698-704, roster 20243705) is harrow's recipe on
the pool {w49, w10, k06, w03} with pfsp weighting toward whichever the
policy loses to hardest, forked from harrow's own trunk. If tape
imitation is what carried harrow to 7/12, a library twice as rich is the
cheapest multiplier on the board.

## The walls were always trainable: cleo, lena and bea are wrapper-plus-tape (2026-08-21)

`agents/bench3/closer_cleo.py` and `agents/wrapped/w49.py` are the same
637-line file with a different `_TRACE`: the tier-2 anchors ARE the same
wrapper-plus-plan construction as the mined tapes. So their plans load
straight into `tape_t` -- and they gate byte-exact on the current engine:

| anchor | tape replay (this engine) | ladder rating |
|---|---|---|
| closer_cleo | **155,344** | 1363.7 |
| ledger_lena | **150,635** | 1364 tier |
| broker_bea | **150,150** | 1364 tier |

**The tier this project has never taken a single game from -- 0/96 on
every roster it has ever appeared in -- has been available as a training
opponent all along.** docs/GAP-2000.md called this the hardest wall on
the way to 2000 ("no reactive 1364-tier opponent can be trained
against") and estimated real work to fix; the actual fix was one command,
because cleo shares w49's wrapper.

Caveat, stated plainly: the tape is the PLAN, not the agent. The wrapper
(terminal liquidation from step 680, sell reordering, front-run) is worth
about 26k -- `tape:w49` replays at 83.8k while the wrapped w49 earns
~110k against us -- so these are open-loop 150k economies, not reactive
1364-tier play. Open-loop tapes are exploitable, which is why the roster
judges and the pool keeps five of them with pfsp.

**anvil** (jobs 20244318-21, roster 20244322): harrow's trunk on the pool
{k06, bea, lena, cleo, w03} -- the actual walls plus the two richest
tapes -- gate 0.25, pfsp hardest-first. threshing (generic strong tapes)
is the control: does training on the EXACT walls beat training on
comparable strangers?

## plowman verdict: land pricing is real but the barnyard-only diet caps it (2026-08-21, job 20234105)

Land at 1500 instead of 300, single variable off sower's trunk:
barnyard **100% +27,642** (the largest margin any arm has posted against
the wall), grazier 63.5% (beaten), main 34.4%, ghosts 100/100,
cleo -76.6k, w49 -76.6k, lena/bea -84.3/-84.6k. **6/12**, income median
45.7k, 12% of games under 20k.

Read against its control (sower's tail: barnyard 96.9%, main 55.2%,
cleo -85.4k, 10% under 20k) and against harrow (100%, main 64.6%,
cleo -70.0k, 4% under 20k): **the land term clearly works on the
production side** -- +8k of self-play income, +10k of wall margin
against cleo/w49 -- but on a barnyard-only diet it does not touch the
reactive matchups the way tape pressure does, and its floor is worse
than harrow's by 8 points. The lesson matches sheaf's premise: the
potential fixes and the opponent diet are orthogonal, and the diet is
what moves the tier-2 walls. The four potential arms (land, wheat,
market impact, capital credit) are therefore best judged as ingredients
to fold into a TAPE arm, not as products on their own.

## harvest: both halves multiplied (2026-08-21, gen15 b728e61)

plowman's verdict separated the two things this project has been fixing:
the **reward's truthfulness** (four measured falsehoods, each now a
gated flag) and the **opponent diet** (tape pressure, which is what moves
the tier-2 walls). Each was tested alone. **harvest** multiplies them:

  diet   tape:{cleo 155k, lena 151k, bea 150k, w03 186k, k06 100k}, pfsp
  reward land 1500 + future-exec + wheat-feed-cap 2.0
         + capital-credit 1.0 + risk-mechanic
  trunk  harrow's tail (the 7/12 product)

gen15 merges all four flag sets into one tree (wheatgate into capcredit)
and passes the whole battery -- WHEAT-PASS, CAPITAL-PASS, EXEC-PASS,
test_trl, MULTI-PASS -- plus an all-flags-on training smoke. Five links,
roster at the tail. This is the arm the last twelve hours of measurement
were aiming at.

## sheaf verdict: the mixture buys the best floor (2026-08-21, job 20237092)

barnyard + w49/k06 tapes + league snapshots + pfsp, land 1500, from
reeve's trunk: barnyard 100% +15,303, grazier 83.3%, main 58.3%
[48.3, 67.7] +3,006 (interval spans 50), berrybaron 42.7%, ghosts
100/100, walls cleo -71.7k / lena -71.0k / bea -70.0k / w49 -73.3k.
**6/12**, and the distribution is the best on record: **income median
51,933, only 3% of games under 20k** (harrow 47.2k / 4%; the submitted
it228 35.7k / 20%).

Head to head with harrow (pure tape diet): harrow wins main outright
(64.6% with the interval clear of 50) and takes 7/12; sheaf has the
better income distribution and matching walls. Since the ladder's losses
are floor events, both are live candidates -- a 384-game resolution of
sheaf's main matchup (queued) decides whether the mixture matches
harrow's roster too.

## SUBMITTED: harrow-samp, the second RL read (2026-08-21)

User authorised this one plus one more overnight if a stronger arm lands.
Uploaded 19.8 MB, 3 submissions left today. Active pair is now
harrow-samp + sower-it228 (544.0 and climbing, 21 games 10W-11L), so the
first read stays live as the control -- the displaced slot was the old
2026-08-16 RL v2 baseline (507.9).

Pre-flight, all archived above: 7/12 roster, mirror margin +0, stress
28/28 with a 66.7ms worst turn, package unpacked and played ($73,703),
income median 47.2k with 4% of games under 20k against the submitted
predecessor's 20%. Honest expectation stated to the user before
submitting: **900-1300, not 1500** -- a ladder rating is where you stop
winning, and the cleo/lena/bea tier (1287-1364) is still 0/96 locally.

## granary verdict + sheaf resolved (2026-08-21, jobs 20237174 / 20247922)

**granary** (the wheat feed cap, single variable off sower's trunk):
barnyard **100% +28,243** (largest wall margin on record, edging
plowman's +27.6k), grazier 72.9% beaten, main 43.8% +413, ghosts
100/100, walls cleo -78.6k / lena -80.5k / bea -79.8k / w49 -72.1k.
**6/12**, income median 46.3k, 13% under 20k. The cap does what the
measurement promised on the production side (+8k of self-play income,
the wall margin up 12k over its control) but, like plowman's land term,
a barnyard-only diet leaves the reactive matchups and the floor behind
harrow's. Third confirmation that reward truth and opponent diet are
orthogonal.

**sheaf's main matchup resolved**: 384 games, **58.6% [53.6, 63.4],
margin +2,851** -- interval entirely above 50, so sheaf beats
enhanced/main outright and its roster is **7/12**, matching harrow with
a better floor (3% vs 4%) and a better median (51.9k vs 47.2k). Two
7/12 products now, both tape-fed; the difference between them is the
mixture (sheaf keeps barnyard mass + league snapshots).

## bourse verdict: the truest reward term, and it made the agent worse (2026-08-21, job 20238055)

The market-impact potential (`future-exec`, stock valued at execution
revenue) is the most defensible term in the whole potential -- X2 of its
gate proves the valuation equals the engine's payment to the dollar --
and as a single variable off sower's trunk it produced the **largest
self-play income of any arm (70.4k) and the biggest barnyard margin
(+31,133)**, while the roster went the other way:

    BEATEN 5/12 (was 5/12 for the control, but the shape is worse)
    grazier   0.0% (control 28.1%, harrow 84.4%)
    main     15.6% (control 55.2%)
    lena  -90.5k, bea -89.3k (control -100.2k / -102.1k)
    income median 41.2k, **20% of games under 20k** (control 10%)

Read plainly: pricing market impact taught the policy to hoard less and
sell into thin markets, which maximises money against a passive
opponent and **collapses against anyone who competes for the same
demand** -- exactly the matchups (grazier, main) where it fell. The
honest lesson is the one this repo already has in ROADMAP §11: a term
being TRUE is not the same as a term being USEFUL, and only the A/B
tells you which. `future-exec` stays in the tree, off by default, and it
does NOT go into the harvest package.

Correction filed for harvest: it currently runs with `--potential
future-exec`. The three fixes that measured well (land, wheat cap,
capital credit + risk mechanic) stay; the market-impact term should be
dropped from the combination. Rebuilding the arm with
`--potential future-mkt` and keeping the rest.

## Both reads climbing; harrow's floor shows up on the ladder (2026-08-21 evening)

| submission | score | games | our income (ladder) |
|---|---|---|---|
| sower-it228 (55668491) | 498.4 -> 544.0 -> **558.2** | 21 (10W-11L) | median ~52k, four games at 14-36k |
| **harrow-samp (55673426)** | **593.3** (entering) | 11 (5W-6L) | **median 61.8k, minimum 27.8k** |

harrow's first eleven ladder games confirm what the local distribution
predicted: **its worst game is 27.8k where it228's worst four were
14-36k**, and its median income is 61.8k against it228's 52k. Every loss
so far is to an opponent earning 33-84k -- it is losing to production,
not collapsing. The 4%-floor property is the one that transfers.

## byre verdict: the biggest wall margin ever recorded, and still 5/12 (2026-08-21, job 20239591)

The investment-truth pair (capital-credit 1.0 + risk-mechanic) off
sower's trunk: **barnyard 100% with margin +40,459** -- half again the
next best (granary +28.2k) and nearly four times the control's +15.4k --
plus the highest self-play income any arm reached (72.0k). Walls
cleo -73.4k / w49 -76.3k (control -85.4k / -78.1k), lena/bea -83.5k.
And yet: grazier 40.6%, main 30.2%, **5/12**, median 44.6k, 13% under
20k.

Same shape as plowman, granary and bourse: **a reward fix that is
mechanically right buys production and buys nothing against reactive
opponents.** Four independent confirmations now. The wall margin ranking
is almost the inverse of the roster ranking:

| arm | barnyard margin | BEATEN | main |
|---|---|---|---|
| byre | **+40,459** | 5/12 | 30.2% |
| bourse | +31,133 | 5/12 | 15.6% |
| granary | +28,243 | 6/12 | 43.8% |
| plowman | +27,642 | 6/12 | 34.4% |
| harrow (tape diet) | +11,804 | **7/12** | **64.6%** |
| sheaf (tape+mix) | +15,303 | **7/12** | **58.6%** |

Beating barnyard harder is not progress; it is overfitting to barnyard.
The tape arms win less crushingly against the wall and far more against
everything that fights back. Every future product line goes through a
tape diet -- that is now settled by six arms, not an argument.

## harvest killed at iter 50, and why: base-priced credit lies under tape pressure (2026-08-21)

harvest (three reward fixes on the wall-tape pool) degraded instead of
adapting: tape-batch income 39.6k -> 37.3k -> 34.0k -> 32.6k across 50
iterations, against anvil's 44.5k and threshing's 44.2k on the same diet
with no reward changes. Killed; four GPU-links saved.

The mechanism is bourse's lesson in a second costume. `capital-credit
1.0` credits future production at **base** price. That is exactly right
when you can sell at base -- which is the barnyard world, where byre
posted a +40k wall margin -- and it is a lie when a 150k tape is dumping
into the same market and realised prices sit far below base. The
potential then over-values production, so the policy over-invests into a
crashed market and its income falls. Both of the two reward terms that
looked most principled (execution pricing, base-priced capital credit)
fail specifically under the diet that matters.

**harvest3** (jobs above) keeps only the diet-agnostic fixes: land 1500
(a quadrant unlocks 25 tiles regardless of price), wheat-feed-cap 2.0
(pure churn prevention, no price assumption) and risk-mechanic (removes
a spurious placement penalty). capital-credit stays in the tree, off,
with this verdict attached: **it belongs to barnyard-diet runs only.**

## threshing verdict: the richer library buys the best main and w49 numbers (2026-08-21, job 20245143)

harrow's recipe on the pool {w49 84k, w10 96k, k06 100k, w03 186k} with
pfsp, 300 iterations: **main 68.8% [58.9, 77.1] +5,991** (harrow 64.6%,
the best reactive-matchup number this line has posted), **w49 -66,334**
(harrow -68.7k, the smallest tier-3 deficit on record), cleo -68.9k,
lena -74.1k, bea -77.7k, grazier 63.5%, ghosts 100/100, barnyard 89.6%
+9,003. **7/12**, income median 48.6k, 5% under 20k.

Against harrow (single w49 tape): main +4.2pp, w49 margin +2.3k, cleo
-1.1k, barnyard -10.4pp, floor +1pp. So the richer library helps exactly
where it should -- the matchups that require production and adaptation --
and costs a little of the barnyard saturation nobody needs. Three tape
arms now sit at 7/12 (harrow, sheaf, threshing), each with a different
mixture, and all three beat main; the four barnyard-diet reward arms sit
at 5-6/12 with none beating main. The diet finding is now overdetermined.

Still 0% on cleo/lena/bea/w49. The margins have come from -103k (cropper,
this morning) to -66k, i.e. 36% of the gap closed in one day, but no arm
has taken a single game off that tier yet.

## anvil verdict AND submitted: training on the walls themselves (2026-08-21 night, jobs 20244322 / 20258070)

The arm that trains on the tier it has never beaten -- pool {cleo 155k,
lena 151k, bea 150k, w03 186k, k06 100k}, pfsp, no barnyard, no teacher:

| axis | anvil | harrow (previous best) |
|---|---|---|
| enhanced/main | **72.9% [63.3, 80.8]** +6,262 | 64.6% |
| spar grazier | **72.9%** +1,878 | 84.4% |
| ghosts | 100/100, **+45.1k / +46.1k** | 100/100, +41k |
| ledger_lena | **-67,688** | -70,661 |
| closer_cleo | **-68,087** | -70,040 |
| broker_bea | **-69,281** | -70,036 |
| w49 | -74,491 | **-68,661** |
| income median | **52,998** | 47,218 |
| **games under 20k** | **2%** | 4% |
| BEATEN | 7/12 | 7/12 |

Training against a tier moves that tier: the three anchors it trained on
all improved, and w49 -- the one strong tape NOT in its pool -- got
worse. That is the cleanest causal statement about opponent diet this
project has produced, and it is a recipe, not a coincidence: to close a
wall, put that wall in the pool.

Also the best deliverable on both ladder-relevant axes: median income
53.0k and a 2% catastrophic tail (the submitted first read had 20%).
Acceptance: mirror margin +0 [-800, +766], stress 28/28 worst turn
68.2ms, package unpacked and played $74,983. **Submitted** under the
user's overnight authorisation (2 submissions left today); active pair is
now anvil + harrow (632.9), with sower-it228 (568.3) retired to make
room -- harrow stays as the control.

## forge: every tape-able wall in one pool (2026-08-21 night, jobs 20258762-66)

anvil established the rule and its own gap proved it: the three anchors
in its pool improved (cleo -70.0k -> -68.1k, lena -70.7k -> -67.7k,
bea -70.0k -> -69.3k) while w49, the one strong tape left out, regressed
(-68.7k -> -74.5k). forge applies the rule completely -- **seven tapes,
every wall this project can compile**: cleo 155k, lena 151k, bea 150k,
w03 186k, k06 100k, w10 96k, w49 84k, pfsp hardest-first, from anvil's
own trunk.

Checked and excluded: `agents/spar/*` (0 of 30 files carry a `_TRACE` --
they are generated atom agents, not wrapper-plus-plan) and
`agents/enhanced` (hand-written). Those stay eval-only, which keeps three
genuinely held-out opponents on the roster -- spar grazier, spar
berrybaron and enhanced/main -- so forge cannot be scored against a field
it trained on.

## The margin has two terms, and we had only ever measured one (2026-08-22)

Measuring the OPPONENT's income on the roster's own 48 seeds, for the
first time:

| opponent | alone (vs passive starter) | with harrow present | with anvil present |
|---|---|---|---|
| w49 | **159,195** | 101,952 (**-57,244**) | 118,491 (-40,704) |
| closer_cleo | **148,150** | 106,204 (-41,946) | 112,769 (-35,382) |

Three things follow, one of them a correction of my own claim.

**(1) Correction: the "tape replay value" numbers were single-seed
noise.** The tape gate replays on seed 424242, where w49's plan earns
83,778 -- but on the roster's 48 seeds the same plan averages 159,195
against a passive opponent. So "the library has a 186k tape" (w03)
overstated w03's specialness: every one of these plans is a 150k+
economy, and the ordering I read off single-seed replays was mostly
seed luck. The pool choices survive (they were all strong), the ranking
does not.

**(2) The wrapper is worth ~nothing on the same board.** Wrapped w49 vs
starter 83,684 against the pure tape's 83,778; wrapped cleo 154,165
against 155,344 -- both slightly LOWER. So `GAP-2000.md`'s "the wrapper
is worth about 26k" was a confounded comparison (tape-vs-starter against
wrapped-vs-us) and is withdrawn. The terminal-liquidation port
(gen16 tapewrap, TAPEWRAP-PASS) adds +109 for cleo and +0 for w49
because **the recorded plans already liquidate**. It stays in the tree,
default on, as a correctness nicety, not a lever.

**(3) The real decomposition, and where the next gain is.** margin =
our income - theirs, and both halves are ours to move:

    harrow:  we 33.6k, w49 102.0k  ->  margin -68.4k   (suppresses -57.2k)
    anvil:   we 43.0k, w49 118.5k  ->  margin -75.5k   (suppresses -40.7k)

**anvil earns 9.4k more than harrow and lets w49 earn 16.5k more, so its
margin is worse.** Every arm so far has been optimised for the first term
only. Beating the 1364 tier needs both: earn ~100k AND hold them near
100k. That reframes the "0% on four walls" number -- we are not one
production doubling away, we are one production doubling plus a
suppression policy away.

## vise: the suppression term was saturated all along (2026-08-22, jobs 20260935-38)

The terminal margin reward is `margin_bonus * tanh((mine - theirs) /
margin_scale)` with scale 50,000. Against the tier we care about our
margin sits at -70k, i.e. **tanh(-1.4) = -0.89 -- saturated, slope
~0.06.** Every arm has therefore trained with the second half of the
objective effectively switched off: crushing the opponent's income by
20k and losing by 50k instead of 70k earned it almost nothing.

vise unsaturates it -- scale 150,000 (slope ~0.8 in the operating range)
and weight 3.0 -- with everything else identical to anvil: same trunk,
same five-tape pool, same potential. If the suppression half of the
margin is trainable at all, this arm is where it shows, and the number
to read is not our income but **the opponent's** in the tail roster
(w49 101.9k under harrow, 118.5k under anvil, 159.2k alone).

## harvest3 verdict: three fixes that each worked, broken by their combination (2026-08-22, job 20252023)

The three "diet-agnostic" reward fixes together (land 1500 + wheat cap
2.0 + risk-mechanic) on the wall-tape pool, and the roster says
**bankruptcy**:

    starter        38.5%   (it LOSES to the scripted starter 61% of the time)
    random         86.5%   (100% for every other arm)
    p05 income     0       (at least 5% of games end at zero money)
    under 20k      21%     (anvil 2%, harrow 4%)
    w49            -138,796  (w49 earns 148,180 -- unsuppressed)
    BEATEN         5/12

Losing to `starter` and a p05 of exactly zero is a collapse signature,
not a weak strategy. The mechanism fits an interaction nobody tested:
**wheat-feed-cap limits the feed stock while risk-mechanic removes the
daily unfed penalty**, so the policy is free to under-feed, the herd
escapes (the engine takes an animal at two unfed days), and on the seeds
where that starts early the farm never recovers. land-value 1500 then
compounds it by pulling cash into quadrants.

Each of the three measured *well* on its own (plowman 6/12, granary
6/12, byre 5/12 with the biggest wall margin on record). **Their
combination is worse than any of them and worse than doing nothing.**
That is the third distinct way this project has now seen reward terms
fail -- untrue (land at 300), true-but-useless (execution pricing,
base-priced capital credit), and individually-fine-but-jointly-toxic.
Recorded rule: **potential terms compose non-linearly; a package needs
its own A/B, never inheritance from its parts.**

Product line unchanged: the tape-diet arms (harrow, anvil, threshing,
forge, vise) carry the line; the reward fixes stay off by default.

## chisel: the single-point attack on the 1364 tier (2026-08-22, jobs 20264844-47)

Four walls at 0/96 is the most stubborn number on the board, and anvil
proved the rule that moves walls (put the wall in the pool). chisel puts
exactly ONE wall in the pool -- closer_cleo, the 1364-tier anchor -- with
vise's unsaturated margin reward, and asks a diagnostic question instead
of a product one: **can this line take a single game off that tier, and
what does the board look like when it does?**

The cost is known and accepted: one open-loop tape is exploitable, so the
tail roster (12 opponents, three of which -- spar x2 and enhanced/main --
are never trained against) prices the overfit. What we want out of it is
not a deliverable but an answer: if chisel beats cleo even 5% of the time,
the deficit is a production gap that scale can close; if it stays at 0%
with the margin term unsaturated and the opponent in the pool, then
something structural is missing and the next generation needs a different
idea, not more of this one.

## Suppression is not a separate lever: production is upstream of both terms (2026-08-22)

vise (margin term unsaturated: weight 3.0, scale 150k) and chisel (one
wall in the pool, same margin term) both ran ~40 iterations past their
forks, and the opponent's income did not budge:

    vise    it 81 -> 117:  ours 48.2k -> 47.6k,  opponent 118.9k -> 117.6k
    chisel  it  0 ->  36:  ours 42.2k -> 46.0k,  opponent 107.5k -> 107.3k

Our own income rose (chisel +3.8k in 36 iterations); **theirs is flat.**
So the premise behind vise -- that the second half of the margin is an
untapped lever -- is wrong in an instructive way. You suppress a market
opponent by OUT-SELLING them: pushing inventory into the products they
sell so their prices collapse. That requires production. The policy is
already selling everything it grows, so re-weighting the reward toward
margin cannot buy more suppression; it just buys more production, which
is what the numbers show.

**Corrected model: production is upstream of both terms.** The -62k
deficit against cleo (we 44k, they 106k, and they earn 148k when left
alone) decomposes as "we suppress 42k already, and we need ~60k more of
our own output". There is no cheap second axis. What remains is the
anatomy gap itself -- 3-4 quadrants, 13-14 animals, ~60 crops, 5-6
revenue lines -- and the open question is how to grow production under
tape pressure, given that the two reward terms which grew it on the
barnyard diet (land value, base-priced capital credit) both fail when a
150k opponent crashes the prices those terms assume.

## The -62k is a PRICE gap, not a production gap (2026-08-22, anvil-samp probe)

Same policy (anvil-samp), same three seeds, weak opponent vs the 1364
tier, counting physical units sold and the price each fetched:

| | vs barnyard | vs closer_cleo |
|---|---|---|
| units sold | 3,324 | **4,407 (+33%)** |
| sale revenue | 299,703 | 276,757 (-8%) |
| **average unit price** | **90.2** | **62.8 (-30%)** |
| our final money | 37-59k | 19-37k |

**We produce MORE against the strong opponent and earn less.** The deficit
is price, not output. Per line:

| product | vs barnyard | vs cleo | price change |
|---|---|---|---|
| MILK | 552 u @ **141.3** | 578 u @ **49.5** | **-65%** |
| STRAWBERRY | 357 u @ 228.2 | 270 u @ 177.4 | -22% |
| WHEAT | 1,742 u @ 43.8 | 2,862 u @ 46.0 | **+5% (held)** |
| MELON | 159 u @ 178.9 | 143 u @ **225.6** | **+26%** |
| FERTILIZER | 514 u @ 69.2 | 554 u @ 65.4 | -5% |

cleo dumps milk and our **second-biggest line loses two thirds of its
price**, while wheat holds (the town's steady demand) and melon actually
pays MORE (cleo barely sells it). Our economy is dairy-heavy; that is
precisely the economy this tier destroys.

Two consequences, both testable:

1. **Product-mix adaptation is the missing behaviour.** The prices are in
   the observation, so the policy CAN see the crash -- but its production
   is committed days earlier (a cow bought on day 6 makes milk on day 20
   whatever the price), so the reallocation has to happen at BUILD time,
   not sale time. Against a fixed tape that is learnable.
2. **And the potential blocks it**: future animal/crop output is credited
   at BASE price, so under a milk crash the potential still says a cow's
   milk is worth 160 when the market pays 49. That is the third
   appearance of the base-price assumption, and this time it has a
   specific cost: the policy cannot see that dairy is the wrong economy
   against this tier. A mark-to-market production credit is the obvious
   A/B -- with the caveat that two previous repricing terms
   (execution-priced inventory, base-priced capital credit) both failed,
   so it gets its own arm and its own roster, inheriting nothing.

For the record, the top meta is diversified exactly where we are not:
w49 is strawberry 30% / milk 22% / wool 21%, k06 is fertilizer 32% /
wheat 18%. Ours is wheat 49% / milk 19% / fertilizer 16%.

## Ladder calibration: the three reads are indistinguishable (2026-08-22)

| submission | local roster | ladder trajectory |
|---|---|---|
| sower-it228 | 5/12, floor 20%, median 35.7k | 498 -> 544 -> 558 -> 568 -> **555** |
| harrow-samp | 7/12, floor 4%, median 47.2k | 593 -> 633 -> 607 -> **616** |
| anvil-samp | 7/12, floor 2%, median 53.0k | 627 -> **572** |

harrow and anvil are locally two tiers apart from the first submission
(7/12 against 5/12, a floor of 2-4% against 20%, +12-17k of median
income) and **on the ladder all three sit in one 550-620 band**, with
anvil currently BELOW harrow despite the better roster.

Two honest readings, and the repo already warned about the first:
CLAUDE.md's "a ranking against a field we wrote is not evidence about the
ladder" applies exactly here. The second is sample size -- 12 to 25 games
each, where a 50-game swing is ordinary noise (the project's own rule 7
was written for this). Neither read is usable for choosing between harrow
and anvil yet; what IS usable is that the first submission's 20% floor
did show up as the lowest of the three trajectories.

Consequence for the next choice: **stop treating small local roster gains
as ladder gains.** The next submission should wait for either a
qualitative change (a nonzero win rate against the 1364 tier) or a much
larger local gap than 7/12-vs-7/12.

## Observability is not the problem (2026-08-22, ruling out a class)

Before attributing the missing product-mix adaptation to the reward, the
cheaper explanation had to be ruled out: maybe the policy simply cannot
SEE the dumping. It can. `features_t._globals` already carries

    g[8:17]   the nine current market prices, normalised by base
    g[17:26]  market inventory deviation, (I0 - inv) / T

so both the price collapse and its cause (inventory piling above target)
are in every observation, every step. The 4,867-dim observation was never
the constraint.

That leaves the reward, which is exactly what ledger tests: the policy
sees milk trading at 49 and the potential tells it a cow's milk is worth
160. One class of explanation eliminated for the cost of one grep.

## What 2000 actually looks like on our own scale (2026-08-22, job 20274290)

Running the two tape-replay submissions that scored **2035.9** and
**2302.2** through the exact 12-opponent roster our arms are judged on:

| agent | ladder | BEATEN | income median | p05 | under 20k |
|---|---|---|---|---|---|
| **topline** | **2035.9** | **12/12** | **118,374** | **63,999** | **0%** |
| kawashigi-k06 | 2302.2 | 12/12 | 124,373 | 68,971 | 0% |
| anvil-samp (our best) | ~572-627 | 7/12 | 53,0 | ~23,2 | 2% |
| harrow-samp | ~607-616 | 7/12 | 47,2 | ~21,3 | 4% |

**A 2035-scoring agent beats every one of our twelve opponents --
including cleo, lena, bea and w49 -- and its FIFTH PERCENTILE income
(64.0k) is higher than our MEDIAN (53.0k).**

This replaces every estimate I have made about the distance to 2000, and
it is much larger than the one I gave last night:

    BEATEN          7/12  ->  12/12
    median income   53k   ->  118k   (2.2x)
    p05 income      23k   ->  64k    (2.8x)

My earlier "+18% of income" figure came from comparing LADDER-game
incomes (61k ours against a weak ladder field, 72k for the 2035 agent) --
same-field arithmetic on a field that is far softer than our roster. The
roster comparison is the honest one because it holds the opponents fixed,
and it says the gap is a **doubling**, not a nudge.

Two consolations, both real. First, the target is now a measurable
local number instead of a ladder guess: 12/12 and a 118k median, on a
roster we run in 45 minutes. Second, the 2035 agent is an open-loop
replay of a human team's plan -- it proves the ECONOMY is reachable on
this engine (118k median against our whole field), not that a policy
must be superhuman to get there.

## vise verdict: best cleo margin on record, worst generality (2026-08-22, job 20260939)

Unsaturating the margin term (weight 3.0, scale 150k) off anvil's trunk:
**closer_cleo -66,320 -- the smallest deficit against the 1364 tier this
project has recorded** (anvil -68.1k, harrow -70.0k), and lena -69.9k.
But main 44.8% (anvil 72.9%), grazier 55.2% (anvil 72.9%), w49 -78.6k,
**5/12**, income median 48.9k, floor 4%.

So the margin re-weighting does exactly what the trajectory suggested: it
buys production and pressure against the tapes it trains on, and pays for
it in the matchups that need adaptation. Same trade as byre and bourse
made on the barnyard diet, one tier up. The suppression half of the
objective remains, as recorded earlier today, not a separate lever.

## forge verdict: the best main number yet, and the seven-tape pool plateaus (2026-08-22, job 20258767)

Every tape-able wall in one pool (cleo, lena, bea, w03, k06, w10, w49),
376 iterations: **enhanced/main 75.0% [65.5, 82.6] +9,826 -- the best
reactive-matchup number this project has recorded** (anvil 72.9%,
threshing 68.8%, harrow 64.6%), grazier 84.4% (ties harrow's best),
barnyard 99.0% +23,456, ghosts 100/100. **7/12**, income median 51.0k,
floor 5%.

But the walls did not move further: cleo -70.6k (anvil -68.1k),
lena -77.2k (anvil -67.7k), bea -80.7k (anvil -69.3k), w49 -69.7k
(anvil -74.5k, threshing -66.3k). **Seven tapes is not better than five
on the walls -- it is better on the held-out reactive opponents.** With
pfsp spreading the sampling mass across seven 100-186k economies, each
individual wall gets less attention than it did in anvil's five-tape pool
(and anvil's own gap already showed the mechanism: the pool member gets
the gain).

So the tape-diet family has converged to a plateau: **five arms
(harrow, sheaf, threshing, anvil, forge) all land at 7/12 with medians
47-53k and floors 2-5%**, differing only in which axis they favour. The
calibration says 2000 needs 12/12 and 118k. More tapes, more pfsp and
more iterations at this scale are not going to close a 2.2x income gap --
the next generation needs a different lever, and the two candidates on
the board are the mark-to-market production credit (ledger, running) and
whatever chisel's single-wall attack reveals.

## chisel's answer: the deficit is proportional, not a missing behaviour (2026-08-22, job 20264848)

313 iterations against nothing but closer_cleo, with the unsaturated
margin term, and the diagnostic question -- can this line take a single
game off the 1364 tier? -- has an answer: **no. 0/96, still.** But the
numbers around that zero are the informative part:

    closer_cleo margin  -59,762   (best of any arm: anvil -68.1k, vise -66.3k)
    our income vs cleo  median 45,236, MAX 100,478
    cleo's income       median 111,791, MIN 51,107
    the closest game    we 18,211 vs cleo 51,107  (-32,896)

Three readings:

1. **The gap is proportional, not situational.** We earn ~40% of cleo's
   money on rich boards (100k against its ~140k) and ~35% on poor ones
   (18k against 51k). The closest game is not a near-miss on a board that
   suited us -- it is a poor board where both farms earned little and we
   still lost by 33k. There is no board type where we are close.
2. **Concentrating all training on one wall bought 8k of margin (-68k ->
   -60k) in 313 iterations and no wins.** The same recipe against five
   walls bought the same 7/12. So the ceiling is the recipe, not the
   attention allocation.
3. **And chisel is nonetheless the best all-round product we have**:
   7/12, main 71.9%, grazier 82.3%, income median **53,997**, floor
   **2%** -- the best median and floor of any arm, from a pool of exactly
   one opponent. Overfitting to one tape cost almost nothing measurable,
   which says the tapes are teaching a general economy rather than an
   exploit.

Taken with forge's plateau and the 2035-agent calibration (12/12, 118k
median), the conclusion is unavoidable and worth stating plainly: **this
generation's recipe tops out around 7/12 and a 50k median. Closing a
2.2x income gap needs a different idea, not more of this one.** The one
untested idea still on the board is ledger's mark-to-market production
credit; after that, the honest next moves are structural (a real
opponent model, or a search/planning layer at inference, or the CNN trunk
the capacity roadmap has been holding).

## ledger verdict, and the regularity behind four failures: a price-blind potential is a regulariser (2026-08-22, job 20269437)

Mark-to-market production credit (future crop/animal output at
min(market, base)) off anvil's trunk: **cleo -65,539** (second-best
recorded, behind chisel's -59.8k), and then the same collapse the other
repricing arms showed -- **main 36.5%** (anvil 72.9%, forge 75.0%),
**grazier 37.5%** (anvil 72.9%), w49 -86.7k (the worst on record),
**5/12**, median 48.8k.

That completes a set of four, and the pattern is now unmistakable:

| arm | change | trained-pool effect | held-out effect (main / grazier) |
|---|---|---|---|
| bourse | inventory at execution revenue | barnyard margin +31k | main 15.6%, grazier 0% |
| harvest | production at base x 1.0 credit | income fell 39.6k -> 32.6k | killed at iter 50 |
| vise | margin term unsaturated | **best cleo -66.3k** | main 44.8%, grazier 55.2% |
| ledger | production at min(market, base) | **cleo -65.5k** | main 36.5%, grazier 37.5% |

**Every attempt to make the potential more truthful about prices has cost
generality**, and always in the same place: the opponents we never train
against.

The explanation that fits all four: **the base-price valuation is a
regulariser.** It is a fixed yardstick that does not move when an
opponent dumps, so the economy the policy learns is invariant to who is
across the table. Feeding market prices into the potential injects the
opponent's behaviour into our own reward signal, and the policy duly
learns opponent-specific responses -- better against the pool it trains
on, worse against anything held out. Kilo's "deliberate simplification"
turns out to be load-bearing.

Practical rule, recorded: **price-dependent terms belong in the
OBSERVATION (where they already are -- g[8:17] prices, g[17:26] inventory)
and not in the potential.** The reward should describe what we want built;
the observation should describe what the market is doing. Four arms and
about twenty GPU-hours bought that sentence.

## longhaul: the control the plateau claim needs (2026-08-22, 12 links to ~1200 iterations)

Every "the tape-diet family plateaus at 7/12" verdict rests on chains of
300-400 iterations -- and chisel's own income slope had **not** flattened
when its chain ended at 313 (42k -> 51k, still climbing). So the claim is
underdetermined: it might be the recipe's ceiling, or it might be where we
happened to stop.

**longhaul** is that control: chisel's trunk, anvil's five-wall pool,
nothing else changed, **twelve links to ~1200 iterations** (roster
20284697). Two clean outcomes:

* still 7/12 and ~54k median at 3x the compute -> the plateau is a
  property of the recipe, and the remaining ideas (inference-time search,
  CNN trunk) are the only way forward;
* it moves -> every verdict in the last two days was measured too early,
  and the cheapest lever available was patience.

Running alongside the two action-layer arms (reaper: metered selling;
sweeper: metered selling plus the sell sweep), which share anvil's trunk
and pool and differ from it by one decode rule each. Three-point ladder
in flight: anvil (dump) -> reaper (meter) -> sweeper (meter + sweep).

## reaper verdict: metering wins the price and loses the matchups (2026-08-22, job 20289583)

Metered selling (floor 0.85 x base) as the single variable off anvil's
trunk: **6/12**, ghosts at record margins (+47.3k / +48.0k, the largest
this project has posted), grazier 81.2% +6,330, barnyard 96.9%, income
median 51.9k, floor 5%. Against anvil (7/12, main 72.9%, median 53.0k,
floor 2%): **main falls to 40.6%**, cleo -73.2k (anvil -68.1k), lena and
bea both worse, w49 -68.8k (better).

So the gate's finding was real but incomplete. Metering does raise the
realised price per unit -- that is arithmetic, and the training income
was consistently 1-2k above anvil's at equal iterations. What the roster
adds is the cost: **holding stock for a better price means holding stock,
and an opponent who competes for the same demand sells it out from under
you.** Against the tapes (open loop, never adapting) metering is free
money; against main and cleo it is inventory left on the shelf.

That is the same shape as every reward-side price experiment, arriving
from the action side: **price-aware behaviour helps against opponents who
do not react and hurts against opponents who do.** The regularity now
spans both halves of the design -- reward and action -- and the honest
summary is that our price sophistication is worth less than our
production. sweeper (metering plus the sell sweep) is still running and
its training income has been consistently BELOW reaper's, which fits:
sweeping sells the stock metering was holding.

## grange: the only production lever the regularity does not forbid (2026-08-22, jobs above)

Two things are now established by measurement. Production is what
separates us from the 1364 tier (they earn 2.5x on every board type, and
chisel's 313 focused iterations moved the margin 8k without a single
win). And price sophistication does not pay: four reward-side experiments
(bourse, harvest, vise, ledger) and now one action-side experiment
(reaper) all helped against open-loop tapes and hurt against reactive
opponents.

`--build-bonus` is the exception that fits both facts. It credits
structures, animals and crops **by count** against the 231k-season
anatomy curve, with no price anywhere in the term, so it cannot inject an
opponent's behaviour into our objective -- and the traced gap is exactly
count-shaped:

    animals   8   vs the ladder field's 13, k06's ~14
    quadrants 2   vs the field's 3 (50 tiles LOCKED all game)
    crops     42  vs the top meta's ~60 standing, ~177 seeds bought

granger.yaml has run this at 1.0 in every arm since gen-4. grange runs
**3.0**, single variable off anvil's trunk and pool. If the count credit
at triple weight does not move the build numbers, then the shaping term
is not what is holding production back and the remaining explanations are
structural (capacity, or search at inference).

## sweeper closes the three-point ladder: price sophistication is monotonically negative (2026-08-22, job 20284158)

The three-point ladder, same trunk (anvil), same five-wall pool, one
decode rule apart at each step:

| arm | selling rule | BEATEN | main | grazier | barnyard | median | floor |
|---|---|---|---|---|---|---|---|
| anvil | dump the holding | **7/12** | **72.9%** | 72.9% | 92.7% | **53.0k** | **2%** |
| reaper | meter to floor 0.85 | 6/12 | 40.6% | **81.2%** | 96.9% | 51.9k | 5% |
| sweeper | meter + sweep all lines | **5/12** | **27.1%** | 47.9% | 76.0% | 46.3k | 10% |

**Monotone, in the wrong direction, on every axis that involves a
reacting opponent.** Each increment of price sophistication cost roughly
13 points of main and 2-5 points of floor; sweeper even lost barnyard
down to 76%. Against the non-reacting opponents it is the reverse (ghost
margins peak at reaper/sweeper), which is exactly the signature of the
regularity now established six times over:

**price-aware machinery pays against opponents who do not adapt and costs
against opponents who do -- in the reward (bourse, harvest, vise, ledger)
and in the action space (reaper, sweeper) alike.**

The mechanism for the action side is concrete: metering means holding
stock for a better price, and a competitor sells the same product before
that price arrives. Holding is only free when nobody else is selling.

Practical consequence, recorded: **stop building price machinery.** The
remaining candidates are production (grange, running: count-based build
credit at 3x) and compute (longhaul, running: the same recipe at 1200
iterations). If both come back flat, the honest conclusion is that this
architecture tops out here and the next step is structural -- capacity or
inference-time search -- not another knob.

## THE OPENING WAS THE GAP: a 12-day scripted opening, zero training, +1 opponent and every wall 20-26k closer (2026-08-22)

The trajectory diff localised the deficit to the first twelve days (the
1364 tier reaches 3 quadrants / 14 animals / 37-61 crops by day 12; we
reach 1-2 / 8-9 / 16). Testing that needed no training at all: replay a
tier tape's first 288 steps, then hand the board to our own network.

| opponent | anvil | + cleo's 12-day opening | delta |
|---|---|---|---|
| barnyard | 92.7% +10,926 | **100% +37,244** | +3.4x margin |
| **spar berrybaron** | **10.4% -7,977** | **99.0% +15,443** | **the 8th opponent falls** |
| enhanced/main | 72.9% +6,262 | **99.0% +34,664** | +26pp |
| spar grazier | 72.9% +1,878 | 83.3% +18,483 | +10pp |
| ghosts | 100% +45k/+46k | 100% +54k/+55k | +9k each |
| closer_cleo | 0% **-68,087** | 0% **-42,248** | **+25,839** |
| ledger_lena | 0% -67,688 | 0% -43,999 | +23,689 |
| broker_bea | 0% -69,281 | 0% -43,335 | +25,946 |
| w49 | 0% -74,491 | 0% -52,299 | +22,192 |
| **BEATEN** | 7/12 | **8/12** | |
| income median | 53.0k | **64.4k** | +11.4k |
| p05 income | 23.2k | **39.6k** | +16.4k |
| games under 20k | 2% | **0%** | floor gone |

w49's opening gives nearly the same (8/12, median 64.0k, walls -45 to
-54k), so this is the tier's SCHEDULE paying off, not one tape's luck.

Three things follow.

1. **Our network is competent at the harvest and incompetent at the
   opening.** Given a farm it has never managed to build, it runs it well
   enough to add 11k of median income and erase the catastrophic tail
   entirely. Every arm since gen-4 has been spending its capacity
   re-deriving a capital-formation schedule that the library already
   contains.
2. **The remaining wall gap is the harvest, and it is smaller than we
   thought**: from the tier's own day-12 position they earn ~110k against
   us and we earn ~64k, so ~42k of the original 68k is post-opening play.
   That is now the well-posed target.
3. **This is the cheapest result of the entire project**: no GPU, no
   retraining, one export-time change. It also vindicates the 2035.9
   tape-replay submission from a new angle -- following a proven
   trajectory beats discovering one, and the correct use of RL here is to
   improve what happens AFTER the script, not to rediscover the script.

## The opening-length sweep, and what it says about our policy's value (2026-08-22)

Splicing cleo's first D days in front of anvil's network, D swept, four
opponents (one trained-against wall, two held-out reactive agents, and
the tier):

| D | barnyard | main (held out) | berrybaron (held out) | cleo | income median |
|---|---|---|---|---|---|
| 6 | 100% | 87.5% | 75.0% | -62,010 | 60.0k |
| 8 | 99.0% | 97.9% | 89.6% | -58,002 | 57.2k |
| 12 | 100% | 99.0% | 99.0% | -42,248 | 64.3k |
| 16 | 100% | 100% | 100% | -38,549 | 68.0k |
| **20** | **100%** | **100%** | **100%** | **-22,648** | **78.0k** |

**Monotone in D on every axis.** Every extra day of the recorded plan
replacing our policy makes us better. There is no phase of the game where
our trained policy is worth more than a replay of a human plan -- and the
sweep is, read literally, an interpolation between our agent and the tape
whose full replay scored 2035.9.

The useful reading is a decomposition. At D=20 the remaining deficit
against cleo is **-22,648 over the last ten days from cleo's own day-20
position** (banked: both seats at 35.7k, 3 quadrants, 14 animals). The
endgame arm trains exactly that and reproduced the number at iteration 1
(we earn 67.4k, they earn 91.1k). So:

    beat the 1364 tier over a season   = a 68k problem, 0/96 after five generations
    beat their last ten days from their own farm = a 23k problem, now being trained

Two supporting readings from the same day, both negative and both
consistent: **grange** (count-based build credit tripled to 3.0) sits at
44.5k at iter 132, no better than anvil's ~45k, so the shaping weight is
not what caps production; and **longhaul** (the same recipe at 1200
iterations) reads 49.6k at iter 312, so compute is not it either.
Neither shaping nor patience is the bottleneck -- **the trajectory is.**

## A calibrated answer to "what level is it": the spar field as an instrument (2026-08-22, job 20292544)

The 12-opponent roster cannot place an agent between 763 and 1287 because
our field has no rung there. The 30-agent `agents/spar/` field can, because
**we submitted nine members of that generator ourselves** and know their
ladder scores: 647, 700, 721, 729, 742, 749, 751, 759, 763 (mean 729).

Running two products across all 30, 24 seeds each (1,440 episodes each):

| | anvil-samp | hybrid-cleo12 |
|---|---|---|
| overall win rate | **33.0%** | **86.8%** |
| opponents beaten (CI > 50) | 10/30 | **28/30** |
| income median | 39,376 | **61,390** |
| p05 income | 24,137 | **44,471** |
| worst matchup | **0%** (three marketgarden lines) | **60%** |

**The instrument validates itself.** Elo from the field mean:
729 + 400·log10(0.330/0.670) = **606** for anvil, whose actual ladder read
is **572-627**. The same arithmetic gives hybrid-cleo12
729 + 400·log10(0.868/0.132) = **1056**.

So the estimate is **~1050 +- 150**, and the +-150 is not hand-waving:
the same submitted file scored 1363.7 and 1218.6 on two different runs.
Placed against everything this project has measured:

    2302 / 2035   full tape replays of other teams' plans
    1364 / 1287   closer_cleo (third-party) and our one-line change to it
    ~1050         hybrid-cleo12  <- scripted opening + our network
    763 ... 647   the best of our own generated agents (nine submissions)
    623 / 621     enhanced / barnyard
    627 ... 555   this RL line's three submissions

Caveats, all real: the spar field is our own reconstruction (though it
just predicted anvil's ladder score to within noise); the Elo step assumes
transitivity in a game this repo has documented as non-transitive; and the
first twelve days of the product are cleo's plan, not ours.

## SUBMITTED: hybrid-cleo12 (2026-08-22, user-authorised)

Uploaded 19.8 MB; **3 submissions remaining today** (the count includes a
collaborator's `Pure Python Agent v1`, 385.6, at 07:30 -- not ours and not
from this line). Active pair is now hybrid-cleo12 + that collaborator
submission, so anvil (592.3) rotates out.

What was submitted, stated plainly in the submission message itself: the
first twelve days (288 steps, 40% of the episode) replay closer_cleo's own
`_TRACE`; the remaining 60% is our trained multi-head policy at sampling
temperature 1.0. Pre-flight: mirror +0 [-764, +754], stress 28/28 with a
55.4ms worst turn, package unpacked and played $91,970 with
`get_last_callable` resolving to `agent`.

Calibrated expectation on record before the read arrives: **~1050 +- 150**,
from the spar-field instrument that predicted anvil's 572-627 as 606. If it
lands there it is the best result this project has produced outside of
whole-tape replays, and the first time the line clears 1000 -- with the
caveat, permanently attached, that the opening is not ours.

## grange verdict: tripling the count-based build credit changes nothing (2026-08-22, job 20289928)

`--build-bonus 3.0` (against granger.yaml's 1.0), single variable off
anvil's trunk, 309 iterations: **6/12**, barnyard 94.8%, grazier 82.3%,
main 46.9%, berrybaron 1.0%, walls cleo -68.2k / lena -68.6k / bea -68.8k
/ w49 -77.6k, income median 46.3k, floor 7%. Against its control (anvil:
7/12, main 72.9%, cleo -68.1k, median 53.0k, floor 2%) it is **slightly
worse on every axis**, and its training income never left the 44-46k band
that anvil occupied.

This was the last price-free production lever on the board -- the one
mechanism the "price machinery does not pay" regularity could not
forbid, aimed at a gap that is exactly count-shaped (8 animals vs 13,
2 quadrants vs 3, 42 crops vs ~60). Tripling its weight moved neither
the build numbers nor the roster.

Read together with longhaul (the same recipe at 1200 iterations, flat at
48-50k) and the opening sweep (monotone: every day of a recorded plan
substituted for our policy improves every axis), the conclusion is
narrow and well-supported: **the shaping term is not what caps our
production, and neither is compute. The policy's own trajectory is.**
The one arm still showing a slope is endgame, which works because the
problem was reframed rather than reweighted: given the tier's own day-20
farm, close their last ten days -- -23,784 at iteration 1, **-9,676 at
iteration 161, 59% of it gone.**

---

## 2026-08-22 · hybrid-cleo12 的天梯读数坐实了,并且换掉了"2000 = 118k"这把尺子

**读数**:705.9,12 局,4 胜 5 负(这批 9 局)——**输掉的比例已过三分之一,
按 `SUBMISSION_POLICY.md` 规则 7,这个分数是真实水平,不是还在爬的地板**。
它是 RL 线历史最高(此前 610.1 harrow),但仍在 700 档。

**首次把五发提交放在同一张天梯表上对齐(`ladder_episodes`,收入按胜/负分栏)**:

| 提交 | 局数 | 胜率 | 我方中位 | 对手中位 | 胜局:我/对手 | 负局:我/对手 |
|---|---|---|---|---|---|---|
| sower-it228 | 21 | 48% | 49,104 | 42,993 | 60,552 / 36,546 | 36,250 / 51,920 |
| harrow-samp | 11 | 45% | 61,828 | 49,278 | 62,774 / 20,256 | 57,948 / 70,076 |
| anvil-samp | 13 | 54% | 59,891 | 52,878 | 65,398 / 29,962 | 48,292 / 72,554 |
| **hybrid-cleo12** | 12 | 50% | **66,662** | **67,860** | 64,668 / **50,927** | 68,626 / 87,104 |
| **topline(2035.9)** | 94 | **79%** | **84,264** | 76,196 | 86,470 / **74,720** | 70,679 / 78,323 |

**三条读法,第二条是最有用的那条:**

1. **我方收入确实一路在涨**:49.1k → 61.8k → 59.9k → **66.7k**。脚本开局那
   一发是最高的,且它面对的场地也最硬(对手中位 67.9k,前三发只有 43–53k)
   ——**天梯按分数配对,分数越高对手越强,所以"胜率没涨"掩盖了实力在涨**。

2. **差距的最锐利表述在"胜局的对手收入"这一栏**:topline 赢的是**挣 74.7k
   的对手**;我们赢的是**挣 50.9k 的对手**。我们不是赢得少,是**只能赢穷板**。
   跨过 2000 需要的不是"多赢几局",而是**把能赢的对手收入线从 51k 抬到 75k**。

3. **修正我 08-22 上午的校准**:我当时说 2000 分 = 收入中位 118k。那是**本地
   12 对手花名册**的尺子(topline 在花名册上确实是 118,374)。**天梯场地远软
   于花名册**:同一个 topline 在真实天梯上只挣 84,264。天梯原生的表述是
   **在一个 76k 的场地里挣 84k(+8k 的相对优势)**,而我们现在是**在一个 68k
   的场地里挣 66.7k(−1.2k)**。两个数字都对,但**别再拿 118k 当天梯目标**
   ——它会让人以为要产能翻倍,实际需要的是 +26% 收入外加把对手压下去。

**连带确认了脚本开局的价值不是本地过拟合**:hybrid 在天梯上的收入比 anvil
高 6.8k,面对的场地却硬 15.0k。这是本地花名册结论(+11.4k 中位)在真实天梯上
的独立复现。


## 2026-08-22 · 把顶端磁带当**老师**而不是对手,量出了一条谁都没查过的缺口

五代以来我们只把 150k 的磁带当对手打,从没模仿过它们;而我们唯一的
kickstart 教师是 `barnyard`(约 40k)——对 2000 分的目标来说是错的教师。
AlphaStar / VPT / OpenAI Five 的共同起点都是**先监督模仿专家、再 RL**。
新工具两个:`rl/tensor_env/project_tape.py`(词表覆盖率)与
`rl/tensor_env/tape_labels.py`(把磁带编成逐步标签 + 四臂定位)。

**一、词表覆盖率(满 719 步,五条磁带)**

| 磁带 | 农夫 | 市场整单 | 市场首单 | 指令/回合 | 帮手 | 帮手/回合 |
|---|---|---|---|---|---|---|
| closer_cleo | 96.1% | 54.5% | 64.8% | 1.05 | 94.3% | 8.40 |
| ledger_lena | 75.8% | 35.2% | 38.9% | 1.64 | 95.8% | 9.17 |
| broker_bea | 75.8% | 36.2% | 43.7% | 1.58 | 95.9% | 9.23 |
| w49 | 86.5% | 64.8% | 69.7% | 0.86 | 96.8% | 8.17 |
| k06 | 95.7% | 56.6% | 66.6% | 1.25 | 97.2% | 8.62 |

帮手侧未覆盖的 op:**PICKUP 104–234、DROP 8–88、PLACE 13–50、
BUILD_PASTURE 9–13**(每局)。市场侧未覆盖的首单以 **SELL** 与
**BUY_PRODUCT** 为主,原因不是品类而是**数量**:顶端一次卖
**中位 4–7 个单位**(p90 10–19,最大 49–65),一局卖 159–523 次;
我们的词表只有"全卖"与"半卖"。他们一局买 **264–967 个单位的小麦**
(全是 `BUY_PRODUCT WHEAT`)——**这顺带推翻了我们"小麦周转是漏损"的诊断**
(granary 臂的前提):顶端买小麦的量是我们的四倍,漏的不是买,是买了不转化。

**二、决定性的定位:arm B(磁带自己的市场 + 标签驱动的农场)**

| 臂 | 第 6 天 | 第 12 天 | 第 18 天 | 第 24 天 | 第 29 天 | 终局 |
|---|---|---|---|---|---|---|
| A 全部我方 | 2 株 / 0 兽 | 3 / 0 | 6 / 0 | 4 / 0 | 2 / 0 | 1,122 |
| B +磁带市场 | 6 / 0 | 4 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 3,532 |
| D 全部磁带 | **18 / 6** | **38 / 14** | 58 / 14 | 48 / 14 | 37 / 14 | **155,344** |

**动物一只都没上场,尽管 arm B 里磁带自己的市场在第 0 步就买了 3 头牛。**
机制:**顶端是用帮手放置动物、用帮手建牧场的**(覆盖率表里 PLACE 13–50、
BUILD_PASTURE 9–13 全在帮手栏且全部未覆盖);我们的 `HAND_TASKS` 只有
8 项杂活,没有 BUILD、没有 PLACE。所以买回来的动物只能排队等**唯一的
农夫**去放——**农夫是我们建设产能的串行瓶颈,而顶端把它并行到 8–9 个帮手上**。

这条假设与本项目已知的两次最大跃升同型:帮手词表补 PLANT/FERTILIZE、
HIRE 连发帽 4→10,两者都是"顶端用帮手做的事,我们的帮手不会做"。

**三、必须自己纠正的一条:DRIVE 比值不是词表判词**

`tape_labels.py` 的 DRIVE 臂(用我们的选项执行磁带的意图)读数 0.0–8.5%,
初版输出把它解释成"词表是天花板"。**这个解释是错的,我撤回它。** 两个混淆:
(1) 我们的 `BUY_*` 选项**自带数量**(HIRE 一次雇 10、BUY_WHEAT 按畜群成批),
把磁带 275 条小额买单换成我们的大额选项会直接**把农场买破产**(w49 那臂剩 0 元);
(2) 队列化市场指令后更差(1,122 → 500),因为积压峰值 127 条、过期丢弃 338 条。
**我们自己训练的网络用同一套选项能挣 40–65k,所以词表显然不是 0.7% 的天花板。**
DRIVE 能支持的结论只有一条,而它已经写在第二节里:**磁带的分工方式在我们的
动作空间里无法表达**。

**记档规则**:一个仪器给出的读数低于**同一套代码里已知的下界**(我们自己的
策略),先怀疑仪器。今天这条差点被我写成"五代奖励工程都被动作空间锁死"的
大结论,而真相是我的标签坏了两处,真正的缺口只是帮手词表里的两项。

## 2026-08-22 · 实收单价:我们的卖法没问题,**卖的东西**不对(并撤回"数量表达不足")

`probe_price.py` 按引擎的定价方式精确计价每一笔卖单(卖 q 个从库存 I 起,
收入 = Σ price(i, I+k)),库存取自真实重放。对手统一为脚本 starter。

| 谁 | 单位 | 笔数 | 收入 | 实收/单位 | 单笔中位 |
|---|---|---|---|---|---|
| 磁带 cleo(155,344) | 1,223 | 231 | 189,572 | 155.0 | 4 |
| 磁带 k06(100,032) | 3,515 | 434 | 261,831 | 74.5 | 7 |
| anvil-samp(78,430) | 1,472 | 274 | 134,435 | 91.3 | 4 |
| chisel-samp(35,270) | 1,650 | 239 | 93,848 | 56.9 | 6 |

**撤回今天上午那条推断。** 我根据覆盖率表(市场整单只有 35–65% 可复现)推断
"我们只会全卖/半卖,顶端小批量卖,所以我们卖不出好价"。**实测两条都不成立**:
我们的单笔中位是 **4–6**,与顶端的 4–7 相同(反复半卖 + 已有的计量机制自然
composes 出小批量);我们的 MILK 实收 234/单位、STRAWBERRY 233/单位,与 cleo
的 244 / 241 持平。**卖法不是病灶。**

**病灶是产品组合。** 同板对比每品类的单位数:

| 品类 | cleo | anvil | 差额 × cleo 单价 |
|---|---|---|---|
| STRAWBERRY | 270 | 88 | **−182 × 241 = −43.9k** |
| MELON | 132 | 44 | **−88 × 249 = −21.9k** |
| WOOL | 164 | **0** | **−164 × 72 = −11.8k** |
| FERTILIZER | 236 | 236 | 0 |
| MILK | 230 | 213 | −4.0k |
| WHEAT | 191 | **891** | +700 × 38 = +26.6k(最便宜的品类) |

**收入差 189,572 − 134,435 = 55.1k,上表几乎逐项对上(−55k)。** 我们不是
少卖,是**多卖了全场最便宜的东西、少卖了最贵的三样,而且一根羊毛都没有**
(没有羊)。

**而那 891 单位小麦不是产出,是买进来又倒出去的。** 种子与饲料的采购账:

| 谁 | 买种子 | 买小麦(饲料) | 峰值作物 |
|---|---|---|---|
| cleo | WHEAT 68, STRAWBERRY 41, MELON 26 | 275 | — |
| k06 | WHEAT 138, STRAWBERRY 34, MELON 20, CARROT 15 | 495 | — |
| anvil | STRAWBERRY 41, MELON 10 | **1,126** | 草莓 31 + 甜瓜 9 = 40 |
| chisel | MELON 29, STRAWBERRY 2 | **1,298** | 甜瓜 15 + 草莓 2 = 17 |

引擎的 FEED **每只动物每天恰好吃 1 单位小麦**(参考引擎第 510 行),所以
8 只的畜群整季需要约 240 单位。**我们买了 1,126–1,298,再把 891–1,119 倒回
市场。** 原因是一行代码:`BUY_WHEAT` 的数量是 `max(5, 2 * herd)`,**从不减去
棚里已有的存货**,每按一次就再买 2×herd。granary 臂的 `WHEAT_FEED_CAP` 只
封了掩码(棚里超过 cap×herd 就不许买),**数量那一行没动**,所以周转被限幅
而没有消除。

**已开的实验**:`WHEAT_BUY_EXACT`(gen25 `feedcap`)把数量改成"补足两日目标
的差额",并在目标已满时把这个动作判为非法。这是**零训练 A/B**——权重、种子
全同,只有动作层这一个变量,所以它是纯 CPU 的(job 20295480,9 个对手 × 48 局
× 两臂)。

**记档规则(今天第二次用到)**:一个从覆盖率表推出来的机制假设,必须先在
真实重放上量一次才算数。我今天两次从"词表覆盖率低"推出错误结论——一次说
天花板在动作空间(实为标签坏),一次说卖不出价(实为组合不对)。**覆盖率
说的是"能不能说出这句话",不是"说出来值多少钱"。**

## 2026-08-22 · endgame 判词:换问题比换奖励有效(反向课程的立论依据)

**304 迭代,margin −23,784 → −7,697(收窄 68%),对 cleo 的胜率 0% → 14.1%。**

这是本项目**唯一一条有斜率的臂**。它和其他十几条臂的差别不在奖励、不在
算力、不在对手池,而在**问的问题**:它不从第 0 天开始,而是从 **cleo 自己
第 20 天的状态库**开始训练(`data/banks/cleo-0480.pt`)。

对照两条同期的阴性:
- **longhaul**(1200 迭代算力对照,同配方从第 0 天):it 572 仍然 50–52k、
  **胜率 0.000**、对手 119–121k。算力翻倍不动。
- **grange**(势函数权重 ×3):6/12,阴性。

**结论**:我们训练不出顶端经济,不是因为奖励说错了话或迭代不够,而是因为
**从第 0 天出发的策略永远走不到那个状态分布里去**,于是它在自己那 50k 的
盆地里被优化得很好。给它顶端的中局状态,同一套奖励、同一套算力立刻产生
斜率——这就是 backplay / 反向课程(Resnick et al.)的全部内容。

**已启动的主线**:`backplay-d16 → d12 → d8 → d4`,每段从上一段权重继续
(链 20294386..97,尾部花名册 20294398)。库已建好:第 4/8/12/16/20 天,
双方资金 405 → 683 → 10.2k → 21.7k → 35.7k。**最关键的性质**:如果走通,
最终产物**自己打完整局,不需要 hybrid 那段脚本开局**——那才是"用 RL 达到
2000",而不是"用别人的录音达到 700"。

## 2026-08-22 · 反向课程改成**累积**起始分布(以及第 0 天收尾段)

第一版课程是"平移"的:d16 段只从第 16 天开局。**这会逐段遗忘。** endgame 用了
304 迭代才把第 20 天从 −23,784 做到 −7,697;一个只有 255 迭代、又从不回访
第 20 天的 d16 段,会把迭代花在重新学回第 20 天上。

引擎的 step 计数器在整个批次里是**标量锁步**的,所以单个状态库不可能混不同
天数(库文件里 `step` 就是一个 int)。但 `--bank` **本来就接受逗号分隔的列表**,
环境每次 reset 随机抽一个库——所以抗遗忘不需要改代码,只需要传累积列表:

| 段 | 起始状态分布 | bank-frac |
|---|---|---|
| endgame(已完成) | 第 20 天 | 1.0 |
| d16 | 第 16、20 天 | 1.0 |
| d12 | 第 12、16、20 天 | 1.0 |
| d8 | 第 8、12、16、20 天 | 1.0 |
| d4 | 第 4、8、12、16、20 天 | 1.0 |
| **d0(新增 4 link)** | 第 4–20 天 **+ 一半真正的第 0 天开局** | **0.5** |

d0 段是整条链的目的:**产物必须自己打完整局**。hybrid 那条线(脚本开局 +
网络)本地已经很强——20 天开局对 starter 中位 118,460,比 12 天那发(已提交,
天梯 705.9)高 26k,其中 8.6k 是 endgame 训练带来的——但它有 **20/30 天是
第三方录音**,所以它回答的不是"用 RL 达到 2000"这个题。**两条线要分开记:
hybrid 是提交候选,课程是目标本身。**

诚实标注:d16 段的第 2、3 个 link 会在中途捡起这个改动(第 1 个 link 用的是
平移版)。它只增加状态覆盖、不改目标,而第 20 天的本事已由 endgame 段建立,
所以我没有重启它。

## 2026-08-22 · hybrid-endgame20:第一次在完整局里赢下那三堵墙

把 **endgame 训练过的网络**(304 迭代,从 cleo 自己第 20 天的状态库出发,
margin −23,784 → −7,697)接在 **cleo 自己 20 天的开局**后面。对照 `hyb-d20`
是**同一段开局 + 未训练的 anvil 网络**——开局相同、种子相同、对手相同,所以
差额恰好是 endgame 训练买到的东西。每臂 **1,152 局**(12 对手 × 48 种子 × 双席)。

| 对手 | hyb-d20 胜率 / margin | **hybrid-endgame20** |
|---|---|---|
| closer_cleo(池内) | 0.0% / −22,648 | **15.6% / −7,774** |
| ledger_lena | 1.0% / −21,849 | **15.6% / −6,150** |
| broker_bea | 1.0% / −22,261 | **16.7% / −6,377** |
| w49(未在任何池) | 0.0% / −33,576 | 0.0% / **−21,413** |
| enhanced/main | 100% / +54,112 | 100% / **+64,709** |
| barnyard | 100% / +56,553 | 100% / **+70,434** |
| **收入中位** | 80,934 | **94,835** |
| **p05** | 47,584 | **54,642** |
| 灾难局 <20k | 0% | 0% |

**这是本项目第一次在完整局里赢下 cleo / lena / bea**(此前每一条臂、每一次
花名册都是 0/96)。三堵墙的 margin 从 −22k 一齐收到 −6~−8k,而且 **w49 也
收窄了 12k,尽管它不在 endgame 的池里**——这是泛化,不是对池过拟合。

与校准锚点对比(topline,天梯 2035.9,同一套 12 对手花名册):

| | BEATEN | 中位 | p05 | 灾难局 |
|---|---|---|---|---|
| topline(2035.9) | 12/12 | 118,374 | 63,999 | 0% |
| **hybrid-endgame20** | **8/12** | **94,835** | **54,642** | **0%** |
| hybrid-cleo12(已提交,705.9) | 8/12 | 64,436 | 39,600 | 0% |
| chisel(此前最强纯网络) | 7/12 | 54,000 | ~23,000 | 2% |

**收入中位 64.4k → 94.8k(+47%),离锚点只差 23.5k。**

**必须挂在这条判词上的限制**:hybrid-endgame20 的**前 20 天(30 天里的 20 天)
是第三方录音**。它是提交候选,**但它回答的不是"用 RL 达到 2000"**。它证明的
是另一件更有用的事:**只要把顶端的中局状态交到网络手上,同一套奖励和算力就
能把那三堵墙打成 15% 胜率。**这正是反向课程赌的那件事,现在有了 1,152 局的
证据——所以课程那条链的先验从"值得一试"升级为"机制已验证,只剩能否把开局
也学会"。

## 2026-08-22 · 小麦 A/B 判词:小幅为正(+1,743),而且**否掉了我的"带宽"假设**

零训练 A/B,`WHEAT_BUY_EXACT`,权重/种子/对手全同,9 个对手 × 96 局 × 两臂:

| 对手 | 胜率 off → on | 收入中位 off → on |
|---|---|---|
| grazier(spar) | 72.9% → **88.5%**(+15.6) | 33,909 → 37,260 |
| barnyard | 92.7% → 95.8% | 57,030 → 62,154 |
| ledger_lena | 0% → 0% | 38,567 → **46,396**(+7,830) |
| closer_cleo | 0% → 0% | 43,028 → **49,551**(+6,523) |
| enhanced/main | 72.9% → 78.1% | 53,382 → 49,266(−4,116) |
| berrybaron(spar) | 10.4% → **5.2%**(−5.2) | 44,472 → 38,298(−6,174) |
| w49 | 0% → 0% | 43,010 → 40,284(−2,726) |
| **9 个对手均值** | **+2.1 点** | **+1,743** |

**结论:留着,但它不是杠杆。** 9 个对手里 6 个收入变好、3 个变差,均值 +1,743
——按本项目的分辨率(96 局分辨 10 点差距),这是"大概真实但很小"。

**它同时否掉了我提出的两个假设,两个都要撤回:**

1. **"周转在漏 27k"**——错。我按"891 单位 × 38/单位"算出的 27k 是**营收**,
   不是**损失**:买入推高价格、卖出压低价格,一次往返近似价格中性。真实价值
   就是这 +1,743。
2. **"市场头的槽位被小麦占满了,腾出来就能多买种子"**——错。小麦用量从 1,126
   降到 387(−65%)之后,`BUY_SEED` 的按压次数是 51 → 46(**下降**),草莓
   种子 41 → 35,作物峰值不变。**槽位不是稀缺资源,策略只是不想买种子。**

所以那 77.6k 的产品组合缺口(草莓 −43.9k、甜瓜 −21.9k、羊毛 −11.8k)必须
**正面攻**,不能靠腾带宽绕过去。

## 2026-08-22 · hybrid-endgame20 验收通过(提交与否归用户)

- **镜像**:胜率 44.8%,margin **+0**,CI [−574, +566] —— 席位公平。
- **压力**:**28/28 clean**,最坏回合 **77.1 ms**(预算 1000 ms)。
- **打包**:解包后 `get_last_callable` 解析到 `agent`,跑完整 720 步一局
  **$116,275**。快照在 `submissions/2026-08-22-hybrid-endgame20/`(20.3 MB)。
- 本地花名册见上一条判词:8/12,中位 94,835,p05 54,642,灾难局 0%。

**我不会自己提交。** 今天剩 3 个名额;如果要发,命令在
`submissions/2026-08-22-hybrid-endgame20/` 里。诚实标注要随附:**前 20 天
(30 天里的 20 天)是 closer_cleo 的录音**,MIT 覆盖其市场层,provenance 在包内。

## 2026-08-22 · 势函数按 base 计价是错的:794 局真实天梯价格给出的表

上一条判词说产品组合缺口必须正面攻。攻法找到了,而且它是**一个可以直接验证的
错误**,不是一个新启发式。

`ladder_episodes.prices` 里有本项目**所有 794 局真实天梯对局**的收盘市价。
和势函数用来给产量计价的 `kg_rules` base 价对比:

| 品类 | base | 天梯中位 | p25–p75 | 比值 | 势函数 |
|---|---|---|---|---|---|
| MELON | 250 | **22** | 4–43 | 0.09 | **高估 11.4 倍** |
| FERTILIZER | 100 | 16 | 8–30 | 0.16 | 高估 6.2 倍 |
| MILK | 160 | 66 | 1–229 | 0.41 | 高估 2.4 倍 |
| WHEAT | 25 | 52 | 46–55 | 2.06 | 低估 2.1 倍 |
| STRAWBERRY | 120 | 201 | 55–257 | 1.68 | 低估 1.7 倍 |
| TOMATO | 60 | 87 | 77–100 | 1.45 | 低估 1.4 倍 |
| EGG | 50 | 63 | 58–68 | 1.26 | 低估 1.3 倍 |
| CARROT | 35 | 42 | 41–42 | 1.20 | 低估 1.2 倍 |
| WOOL | 200 | 218 | 5–242 | 1.09 | 大致正确 |

**机制**:商店消耗作物的速度超过两个农场的供给(整局作物库存都在 I0 **以下**,
所以作物价高于 base),而动物产品与肥料堆在 I0 **以上**。这是 SHOPS 机制与
产出速率决定的,**与对手无关**——本地一局的实测(hybrid-endgame20 对 cleo)
给出同样的方向:草莓库存 9,915 / 实价 197,牛奶 10,044 / 实价 68。

**为什么这解释了我们的行为**:势函数给一块甜瓜地 **750**、一块草莓地 **240**,
所以策略去种甜瓜——`chisel` 买了 **29 颗甜瓜种子、2 颗草莓种子**。而甜瓜在
天梯上每个单位 **22 元**。换成实价表后两者变成 **66 与 402**,偏好翻转
(门 R3 就是钉这个)。动物侧:一头牛的信用 512 → **211**,一只羊 507 → **552**
——**羊变得比牛好**,而顶端每局卖 164 单位羊毛,我们卖 **0**。

**为什么这不是 bourse / ledger / mtm 那四条阴性的重复**(ROADMAP §11:四个
价格相关的势函数项,四次失败):**这张表是静态的**,不读任何实时市场状态,
所以不可能把对手行为注入我们的目标;唯一的输入是"这块地产出什么品类"。
诚实标注写在源码里:MELON 的四分位距是 4–43、MILK 是 1–229,中位数是一个
双峰分布的中心。

`--realised-price W`(0 = base,1 = 实测表),`REALISED-PASS`
(R1 逐元判等 / R2 五个品类的比值全对 / R3 偏好翻转 / R4 对 W 单调)。
**assay 臂**从 chisel 权重起训(iteration 0 = chisel),链 20296292-96,
第一个 link 以 `afterok` 挂在门电池 20296291 上——门不过就不烧 GPU。

## 2026-08-22 · 种子批量 A/B:收入 +2,238 而胜率 −2.1 点(方向相反,先不采纳)

`BUY_SEED_<c>` 每个市场订单只买 **1 颗种子**,而市场头每回合只发 1 条,
所以**种植吞吐被锁在每回合 1 块地**——而 8–12 个帮手每人一回合能种一块。
顶端每局在种子上花 62–112 个市场槽位。`SEED_BATCH=6` 改成"按能下地的空地
成批买"(减去棚里已有种子,再受现金约束)。零训练 A/B,权重/种子/对手全同:

| 对手 | 胜率 off → on | 收入中位 off → on |
|---|---|---|
| closer_cleo | 0% → 0% | 43,028 → **50,688**(+7,660) |
| ledger_lena | 0% → 0% | 38,567 → **44,697**(+6,130) |
| starter | 100% → 100% | 68,766 → 74,802(+6,036) |
| grazier(spar) | 72.9% → **60.4%**(−12.5) | 33,909 → 39,318(+5,408) |
| barnyard | 92.7% → **86.5%**(−6.2) | 57,030 → 56,207(−823) |
| **9 个对手均值** | **−2.1 点** | **+2,238** |

**收入涨、胜率跌——这是个警号,不是胜利。** 对固定策略而言对手是确定性的,
所以"我们更富但输更多"只能来自棋盘交互:多种的地要多浇水,帮手的工时被
挤占。按 `CLAUDE.md` 的"看排名对钱"那条规则,方向相反的改动不该默认采纳。
**`SEED_BATCH` 默认保持 1。**

小麦那条是 +2.1 胜率 / +1,743 收入,和这条方向恰好相反,所以起了第三臂
**两个一起开**(`both-on`,数组 20296587,报表 20296607),四臂同基线对比。
若两者相消,则这两个动作层修正都不值得带上。

**顺带量清一条结构性上限**:顶端在 **18–41% 的回合发 2–10 条市场指令**
(cleo 有 19 个回合发满 10 条,lena 有 41% 的回合 ≥2 条),而我们的市场头
每回合只有 **1 条**。但总量只差 4.6%(cleo 752 条 / 719 回合),**所以它不是
主要限制**;失去的是时机上的集中度,这一点还没测。

**手写日程(`probe_ceiling.py`)的诚实结论**:它建到了 3 块地、6 只动物,
但作物停在 10–14 且最终破产。**一个差的日程证明不了词表不行**——这正是
DRIVE 那一臂被撤回的原因,所以我不把它当证据。它确认的是:顶端建设的**每个
部件在我们的动作空间里都单独可表达**(3 块地 1000/2000/4000、14 只动物走帮手
PLACE、37–61 株在种子预算内),做不到的是**同时把三样都融资出来**——那是
策略的经济学问题,不是词表缺口。

## 2026-08-22 · stockman 的行为读数:**帮手拿到了新词却不用**(以及为什么)

it 57 的检查点,一整局的动作统计:

| | 帮手 BUILD_PASTURE | 帮手 PLACE | 农夫 BUILD/PLACE | 畜群峰值 |
|---|---|---|---|---|
| stockman it 57 | **4** | **0** | 3 / 4 | **4** |

**新词几乎没被用,农夫仍然包办建设。** 机制是我事先量到一半的:

- **空牧场在势函数里恰好值 +0**(一株草莓 +240,一个带牛的牧场 +640),
  所以 **BUILD 是零梯度动作**;
- **PLACE 在没有空栏时是被掩码的**,所以链条中**有奖励的那一半从没有信号的
  那一半出发不可达**。

单靠熵探索要在同一局里先偶然 BUILD、再偶然 PLACE、再喂活它,才能拿到一次
正反馈——57 个迭代里一次都没成。

**修法不动奖励,动动作的组合**:`PLACE_BUILDS`——一个抱着动物、没有空栏的
帮手,**自己在最近的空地上建牧场**,于是整条链作为**一个动作**拿到 +640 的
动物信用。这和 `_with_stock` 把"走到棚、PICKUP、再执行消耗动作"复合成一个
选项是同一个手法。

**门 H4 是关键的那个**:帮手**只给 PLACE**、全程不发 BUILD 任务、农夫 PASS,
畜群还必须立起来——它们自己建了 6 个牧场、立起 6 只,设备与 CPU 逐元一致。

`penner` 臂(gen27)从与 stockman **相同的拓宽后 chisel 权重**起训,配方相同,
**只差这一处复合**。stockman 剩下的 3 个 link 已取消(它的假设已在 it 57 被
按我预测的方式否掉),GPU 让给这条;它的花名册改挂在正在跑的那个 link 上,
读到的是 it ~150 的检查点,仍是一个有效数据点。

**记档规则**:一个新动作如果它自己没有奖励、而它解锁的那个动作又被掩码,
**词表加了等于没加**。加动作时要同时问"这个动作的第一次正反馈从哪来"。

## 2026-08-22 · 动作层经济学四臂对比:采纳小麦,拒绝种子,**两个一起开会抵消**

同一份 anvil 权重、同一批 48 种子 × 双席、9 个对手,只换动作层常量:

| 臂 | 平均胜率 | vs 基线 | 收入中位 | vs 基线 |
|---|---|---|---|---|
| legacy(现行) | 38.8% | +0.0 | 43,028 | +0 |
| **wheat**(`WHEAT_BUY_EXACT`) | **40.9%** | **+2.1** | **46,396** | **+3,368** |
| seed(`SEED_BATCH=6`) | 36.7% | −2.1 | 45,736 | +2,708 |
| **both** | 39.1% | **+0.3** | 42,630 | **−398** |

**两个一起开把彼此抵消掉了**(+0.3 胜率 / −398 收入),尽管单独一个 +2.1、
另一个 +2,708 收入。已归档的"势函数项非线性叠加,组合包必须自己做 A/B"
这条规则,**对动作层的修正同样成立**——现在有了直接证据。

**决定**:采纳 `WHEAT_BUY_EXACT`(下一次提交的导出里打开),拒绝 `SEED_BATCH`,
拒绝组合。注意非传递性一如往常:`both` 对 enhanced/main 是四臂最高的 91.7%,
对 w49 却是最低的 36,817。

**未办事项**:`WHEAT_BUY_EXACT` 目前只有 CPU 侧;如果要**带着它训练**,必须
补设备孪生(`mrem` LUT),否则训练与部署的动作层不一致。零训练使用(导出时
打开)不需要它。

## 2026-08-22 · 课程的难度剖面:**前四天的状态库几乎没有用**,而这重述了差距

`train.py` 的 it 0 就是未训练策略从某个状态库出发的表现(d16 的 −24,627 就是
这么读的)。用 chisel 的权重、对 cleo、CPU、64 车道,对六个起点各跑 1 迭代:

| 起点 | 我方收入 | 对手收入 | margin | 相对第 0 天 |
|---|---|---|---|---|
| 第 0 天(完整局) | 47,076 | 101,925 | −54,849 | — |
| **第 4 天** | 49,730 | 109,291 | **−59,561** | **更难** |
| 第 8 天 | 53,700 | 108,444 | −54,744 | +105 |
| 第 12 天 | 58,781 | 105,007 | −46,226 | +8,623 |
| 第 16 天 | 60,442 | 98,915 | −38,473 | +16,376 |
| 第 20 天 | 66,530 | 87,132 | −20,602 | +34,247 |

**状态库恢复的是双方的状态**,所以"第 4 天"这一行的意思是:**把 cleo 自己
第 4 天的农场(19 株作物)交到我们手上,我们用剩下 26 天挣 49,730,而 cleo
在同一个起点上挣 109,291。** 第 4 天的库不但没帮上,还比从零开始更差
——因为 cleo 第 4 天只有 405 元,资本还没形成,而它的**计划**已经领先。

**这要求重述"开局是差距"这句话。** hybrid 的结论(把前 12/20 天换成录音,
收入 +26k)是对的,但它对的原因不是"我们不会开局",而是**我们不会复利**:
给同样的农场,我们把它经营成 50k,顶端经营成 109k。开局录音之所以有效,是
因为它同时替我们完成了**前 20 天的每一个经营决定**,而不只是"开局摆位"。

**对课程的两条推论:**
1. **有用的梯段是第 12–20 天**(+8.6k / +16.4k / +34.2k),**第 4、8 天两段
   几乎等于从零开始**。所以链里 d8、d4 两段(6 个 link)的边际价值最低。
2. 但**逐段继承确实在起作用**:d16 从 chisel 起是 −38,473,而从 endgame 权重
   继承后 it 0 是 −24,627、26 迭代后 −7,694。**同一个起点,继承把它从 −38.5k
   打到 −7.7k(收窄 80%)。** 所以课程的机制成立,只是最后 12 天的复利技能
   要靠 d12/d8/d4/d0 四段自己长出来。

**两条在跑的臂正好都打在这一点上**:`assay`(势函数按天梯实价——前 12 天的
现金引擎是小麦,2 天一收、天梯 52 元/单位,而策略被 base 价骗去种甜瓜,
天梯 22 元)、`penner`(帮手复合建栏——建设产能)。它们改的都是**复利速度**,
不是开局摆位。

## 2026-08-22 · d16 段判词 + 按剖面重排课程的 GPU 预算

**d16 收在 margin −7,688、对 cleo 胜率 11.4%**,起点 −24,627。它在 **it 29 就
到 −7,694**,之后 30 个迭代一直平在那里——**一段收敛后再加迭代不再有用**。

对照 chisel 从同一个第 16 天状态出发是 **−38,473**(难度剖面)。所以
**逐段继承把同一个起点从 −38.5k 打到 −7.7k,收窄 80%**,而只用了 26 个迭代。

**按剖面重排预算**(判词见上一条):第 4、8 天两段的 margin 与从零开始几乎
相同(−59,561 / −54,744 对 −54,849),边际价值最低;而 **d0 段的累积库本来
就包含第 4、8 天的库**(`seq 0 4 20` → 4/8/12/16/20),所以砍掉这两段
**不丢任何状态覆盖**。改成:

    endgame(第 20 天, 已完成) → d16(已完成) → d12(3 link) → d0(6 link)

d0 的起始分布是**一半真正的第 0 天开局 + 一半第 4–20 天的库**,即完整梯段。
省下的 6 个 link 给了最终那一段——它才是"产物自己打完整局"的地方。

**penner 的 A/B 基线已核实**:it 0 money **51,249**,与 stockman 的 it 0
逐位相同(两者都从同一份拓宽后的 chisel 权重出发),所以之后每一分差异
都只来自 `PLACE_BUILDS` 这一处复合。

## 2026-08-22 · 复合还不够:**帮手的任务每回合重新采样,所以多回合的行程几乎从不完成**

`penner`(PLACE 复合建栏)在 step 11 的读数:

| | 帮手 PLACE | 帮手 BUILD_PASTURE | 帮手 PICKUP | 农夫 PLACE / BUILD | 峰值畜群 |
|---|---|---|---|---|---|
| stockman it 57 | 0 | 4 | — | 3 / 4 | 4 |
| penner step 11 | **0** | 2 | **5** | 20 / 18 | 6–7 |

**取货支腿动了(PICKUP 5 次),放置一次都没完成。** 病因是这个动作空间的一个
性质,我此前没有把它算进去:**每个帮手的任务每回合都重新采样**,所以一趟需要
多回合的行程,只有在策略**连续多回合选同一个任务**时才会走完——而一个新的
PLACE 头概率大约 **2%**。帮手抱起一头牛,下一回合被派去浇水,然后抱着它走完
整局。

**修法与已有的"载重 ≥8 就 DROP"支腿同型:让手里拿着什么来决定,而不是被派了
什么。** `CARRY_COMPLETES`——抱着牧场动物的帮手,走到最近的空栏放下,没有空栏
就在最近的空地上建一个。

只处理**牧场动物**(牛/羊):鹅要鸡舍而帮手建不了,而真实天梯场地的畜群几乎
全是牛羊;这个限制让**所有帮手共用一个目标平面**,于是设备孪生是一个静态平面
且不需要认领(CPU 侧这条支腿用 `_goto_do`,和 FEED/FERTILIZE 的取货支腿一样
不占用池条目)。

门 `test_herd` 加上这条支腿后:H2 峰值畜群 6 → **7**、放置 6 → **9**;
H3 从农夫速率的 3.8 倍到 **4.4 倍**;H4(帮手只给 PLACE、不发 BUILD)自建牧场
6 → **9**、放置 6 → **13**。四个门全程设备与 CPU 逐元一致。

`penner` 已从 `init.pt` 干净重启(正在跑的那个 link 用的是没修的代码,
PLACE 必为 0,那 50 GPU 分钟本来就是废的)。

**记档规则(今天第二条同类)**:加一个动作时要问两件事——"它的第一次正反馈
从哪来"(零梯度问题),以及"**它需要几个回合才能兑现,而策略会不会连续选它**"。
在这个动作空间里,**任何跨回合的动作都必须自己完成,不能依赖策略的持续性。**

## 2026-08-22 · 帮手动作分布:hyb-eg20 已经"像顶端在操作",而 26% 闲置是**症状不是原因**

同板(对 starter / 磁带自身重放)的帮手动作占比:

| 帮手动作 | cleo | k06 | anvil(已提交) | **hyb-endgame20** |
|---|---|---|---|---|
| 走路 | 50.3% | 51.8% | 54.6% | 53.4% |
| **PASS(闲置)** | **6.8%** | 9.5% | **26.0%** | **9.9%** |
| WATER | 13.8% | 14.8% | 8.9% | 14.6% |
| HARVEST | 5.0% | 5.8% | 2.8% | 4.4% |
| FEED | 4.5% | 3.3% | **0.0%** | 2.8% |
| PICKUP | 3.9% | 1.7% | 0.0% | 2.5% |
| PLANT | 2.0% | 2.8% | 0.9% | 1.6% |
| FERTILIZE | 1.6% | 1.0% | 0.1% | 0.8% |
| 每回合帮手数 | 8.39 | 8.62 | 7.88 | 7.94 |

**第一条读法**:`hybrid-endgame20` 的分布**几乎就是 cleo 的**(闲置 9.9% 对 6.8%、
浇水 14.6% 对 13.8%、收获 4.4% 对 5.0%),而 anvil 的完全不是。这是 endgame
训练价值的**独立佐证**——它不只是收入高,它的**操作节奏已经是顶端的节奏**。
顺带:anvil 的帮手**一次都不喂食**,喂食全压在农夫身上(农夫 152 个回合在喂),
而顶端把它分给帮手。

**第二条读法要撤回我自己的推断(今天第五次)。** 我看到 anvil 闲置 26%,推断
病因是**掩码逐帮手独立计算**:8 个帮手都能合法选 WATER 而只有 1 块地缺水,
7 个 PASS。于是做了 `BUSY_HANDS`(家族被抢空就退回 AUTO 而不是 PASS)并零训练
实测——**闲置率只从 26.0% 掉到 24.4%**。AUTO 回退**也找不到活干**,所以那
24% 是**棋盘上真的没有活**:地都浇了、没有可收的、没有草。

**所以 26% 闲置是"农场太小养不住 8 个帮手"的症状,不是原因。** cleo 的 6.8%
来自它有 37–61 株作物和 14 只动物要照料;我们有约 40 株和 4–9 只。
**`BUSY_HANDS` 放弃,不占一次数组。**

**这条阴性把今天所有测量收成了一个故事**:闲置、收获率低、没有羊毛、甜瓜过重、
畜群只有 4–9 只、不会复利——**全部是"农场的规模与构成"这一件事的下游**。
所以现在**不该再加调度类的杠杆**,而在跑的两条臂正好打在两个上游成因上:
`assay`(该种什么——势函数把甜瓜高估 11.4 倍)和 `penner`(建得多快——
帮手复合建栏 + 抱着就放)。

## 2026-08-22 · 两份花名册:stockman 阴性坐实,longhaul 证明**算力会把策略做坏**

**stockman(帮手 BUILD+PLACE 两个独立任务,it 119,1,248 局)**

| | BEATEN 留出 | 训练过 | 收入中位 | p05 | 灾难局 |
|---|---|---|---|---|---|
| chisel(基线) | 7/10 | 0/2 | 54,000 | ~23,000 | 2% |
| **stockman** | **7/10** | **0/3** | **51,344** | 23,705 | 2% |

与 it 57 的行为读数完全一致:**新词没被用,所以唯一的净效果是把手部头从 10 拓到
12、稀释了策略**——中位低了 2.7k。四堵墙全部 0%(cleo −58,611、lena −68,648、
bea −68,209、w49 −68,179、k06 −75,129)。**这条阴性的价值在于它把病因钉死在
"零梯度 + 掩码链",而不是"词表不够"**;修好之后的 penner 正在跑。

**longhaul(1200 迭代算力对照,读到 it 629,1,152 局)**

| | chisel(313 迭代) | **longhaul(629 迭代)** |
|---|---|---|
| BEATEN 留出 | 7/10 | **5/10** |
| 收入中位 | 54,000 | **43,355** |
| p05 | ~23,000 | **17,817** |
| 灾难局 <20k | 2% | **8%** |
| enhanced/main | 71.9% | **39.6%** |
| grazier(spar) | 82.3% | **7.3%** |

**两倍算力把每一个轴都做差了。** 此前归档的判词是"算力是空杠杆"(它在训练
日志里一直平在 50–52k、胜率 0.000);花名册说得更重:**它不是平,是退化**。

机制:训练日志里的 money 是**对训练池**的,而池里三条磁带的胜率始终是 0.000
——**目标函数在一个它赢不了的池子上被优化了 629 个迭代**,于是策略朝"在必输
局里少输一点"的方向漂,把对留出对手的通用性交出去了(grazier 82.3% → 7.3%
是最刺眼的一格)。

**记档规则**:**长链必须有留出集上的早停**,否则"训练指标不动"会掩盖"留出
指标在掉"。我们的 `--probe-every` 是确定性探针,不是留出花名册;这次是花名册
才看见退化。今天这条和"算力不是杠杆"合并成一条更强的:**在一个你赢不了的池子
上加算力,会主动损害泛化。**

## 2026-08-22 · penner 行为读数(step 102):链条通了,**没有第三个结构性障碍**

| | 帮手 PLACE | 帮手 BUILD_PASTURE | 帮手 PICKUP | 农夫 PLACE / BUILD | 峰值畜群 |
|---|---|---|---|---|---|
| stockman it 57(两个独立任务) | **0** | 4 | — | 3 / 4 | 4 |
| penner 未修 step 11(只复合建栏) | **0** | 2 | 5 | 20 / 18 | 6–7 |
| **penner + CARRY_COMPLETES step 102** | **4** | **25** | 12 | **13 / 10** | 5–6 |

(三局合计,17,696 个帮手动作;收入 57.3k–62.3k,基线 chisel 中位 54.0k。)

**帮手第一次真的在放动物和建牧场**,农夫的建设份额从 20 次降到 13 次。所以
"帮手 PLACE 恒为 0"不是第三个结构性障碍,就是前两条:零梯度 + 跨回合行程
不自完成。两条都修掉之后链条通了。

**新的瓶颈是发起频率**:carry 支腿只在帮手**手里有动物**时触发,而拿到动物要
先被派 PLACE 一次——`widen_hands` 的新任务偏置是 **−4.0**(为了让 it 0 与
stockman 逐位相同,A/B 才干净),所以取货每局只有 4 次。它在往上走(0 → 4),
链上还有 3 个 link;**先不动偏置,保住基线**。如果 roster 显示畜群仍停在 5–6,
下一臂的变量就是这个偏置(−4.0 → −2.0),而不是再加动作。

## 2026-08-22 · assay 行为读数(it 149):作物组合按预测翻转,动物侧还没动

| | 买种子 | 峰值作物 | 畜群 |
|---|---|---|---|
| chisel(基线) | MELON 29, **STRAWBERRY 2** | MELON 15, STRAWBERRY 2 | 牛 8 |
| **assay it 149** | MELON 21, **STRAWBERRY 14** | **STRAWBERRY 12**, MELON 9 | 牛 7 |

草莓种子 **2 → 14**(7 倍),草莓已取代甜瓜成为主力作物——正是门 R3 钉的那个
偏好翻转(base 价下甜瓜 750 对草莓 240;实价下 66 对 402)。**势函数说的是真话,
策略就跟着改种什么。**

**动物侧尚未动**:仍是 8 头牛、**0 只羊**,尽管实价表给一只羊 552、一头牛 211。
候选原因:市场头的 `BUY_SHEEP` 从未被按过,而畜群构成不像作物那样由种子采购
间接决定——它需要策略直接选那个市场选项。若 roster 出来后羊毛仍是 0,下一步
是查 `BUY_SHEEP` 的掩码与被按频率(纯观测/掩码问题),而不是再改势函数。

训练日志的 money 仍平在 51.6k,但那是**对训练池**(三条不可战胜的磁带)的读数
——longhaul 的判词刚说明这个指标会掩盖留出集上的变化。**判词等花名册。**

## 2026-08-22 · 动物的价值次序在 base 与天梯之间**完全反转**,以及第六次撤回

**一、为什么我们的畜群是 8 头牛、0 只羊、0 只鹅**

| 动物 | 成本 | 产品 | base 价/天 | **天梯价/天** | 天梯回本 |
|---|---|---|---|---|---|
| SHEEP | 500 | WOOL 200 → **218** | 66.7 | **72.7** | 6.9 天 |
| GOOSE | 300 | EGG 50 → **63** | 50.0 | **63.0** | **4.8 天** |
| **COW** | 400 | MILK 160 → **66** | **80.0** | **33.0** | **12.1 天** |

**在 base 价下次序是 牛 > 羊 > 鹅;在真实天梯价下是 羊 > 鹅 > 牛。完全反转。**
一头牛在天梯上要 12 天回本,而动物通常在第 8–12 天才放下去——**它几乎不回本**。
我们的策略学的是 base 价的次序,所以买满一圈牛。这是 assay 那条判词的动物侧,
也解释了它为什么需要时间:要推翻三百多个迭代学来的"牛最好"。

**二、第六次撤回:`PLANT_BY_VALUE`——杠杆没有作用对象**

我看到帮手的 `PLANT` 选的是**持有最多**的种子(不是最值钱的),推断这是单一
栽培偏置:要种草莓,策略得先在仓里赢一场"数量竞赛",而市场头每回合只能买
一颗种子。于是做了按天梯价值选作物的规则(草莓 804、番茄 348、小麦 312、
胡萝卜 168、甜瓜 132),零训练 A/B。

**anvil 与 chisel 的四个种子上,两臂逐位相同。** 查清了原因:

- 作物**全是帮手种的**(农夫 PLANT 计数为 0;chisel 的帮手种了甜瓜 30、草莓 2),
  所以规则确实是决定性的;
- 但 **720 个回合里,仓库同时持有两种种子的只有 1 个回合**。规则最多能在一个
  回合上产生差异。

**所以真正的约束是市场头买什么种子,不是帮手怎么挑。** `BUY_SEED` 每个市场
槽位一颗,策略买了甜瓜 29 / 草莓 2,仓里就几乎从来没有可选项。**这反过来
加强了 assay 的地位:作物组合 100% 由 `BUY_SEED_<c>` 的按压决定,而按哪个由
势函数对该作物的估值决定** —— assay 改的正是这一处,它的草莓种子已 2 → 14。

`PLANT_BY_VALUE` 与 `BUSY_HANDS` 一样保留在默认关闭的标志后面,把测量写在
注释里,因为下一个看到"帮手按数量选种子"的人会有同样的想法。

**记档规则**:动作层的规则只在**有多个候选**时才有影响力。改规则前先量一次
"这条规则每局真正被调用、且候选多于一个的回合数"——今天这个数是 **1**。

## 2026-08-22 · 1,588 份真实天梯农场记录:分档的是**收获效率**,不是建设

`ladder_episodes.our_digest / their_digest` 里每一局都有逐日的资金/畜群/帮手
轨迹、土地数、首块地日期、买卖明细——**双方都有**,即 794 局对局共 **1,588 份
真实农场记录**。按终局收入分档:

| 档 | 收入中位 | 畜群@15 | 土地 | 首块地 | 资金@15 | 卖草莓 | 卖羊毛 | 卖甜瓜 |
|---|---|---|---|---|---|---|---|---|
| 前 10% | 120,772 | 14 | 3.0 | 7 | 21,360 | **270** | **164** | 120 |
| 中 40–60% | 68,975 | 12 | 3.0 | 7 | 14,284 | 138 | 120 | 114 |
| 后 10% | 29,940 | 12 | 3.0 | 9 | 8,664 | **35** | **39** | 114 |

**三条反直觉的读数:**
1. **畜群构成三档完全相同**(买牛 8、羊 6、鹅 0)。**没有人买鹅**,尽管鹅的
   天梯日产值(63/天)是牛(33/天)的近两倍、回本 4.8 天对 12.1 天——整个
   场地集体否决了鹅,这本身是信息。所以"牛是最差动物"的算术为真,但**畜群
   构成不是分档的原因**。
2. **土地三档都是 3.0 块**,首块地第 7–9 天。**建设也不是分档的原因。**
3. **甜瓜成交量与收入完全不相关**(120/114/114)。甜瓜不是有害,**只是不是杠杆**。

**分档的是草莓(270 → 35,7.7 倍)与羊毛(164 → 39,4.2 倍)。**

## 而我们的缺口在**收获**,不在种植

把我们自己的天梯农场对上场地前 10%:

| | 收入 | 土地 | 首块地 | 畜群@15 | 资金@15 | 草莓 | 羊毛 | 买羊 |
|---|---|---|---|---|---|---|---|---|
| 场地前 10% | 120,772 | 3.0 | 7 | 14 | 21,360 | 270 | 164 | 6 |
| anvil(纯 RL) | 59,891 | 2.0 | 10 | 6 | 14,405 | 98 | **0** | **0** |
| **hybrid-cleo12** | 66,662 | **3.0** | **7** | 11 | **24,594** | 96 | 114 | 6 |

hybrid-cleo12 靠脚本开局在**土地、首块地、资金@15、羊、羊毛**上都追平了前 10%
(资金@15 还更高),**只剩草莓 96 对 270**。

**每颗种子的产出**才是病灶:

| | 买草莓种子 | 卖草莓 | **单位/种子** |
|---|---|---|---|
| 场地前 10% | 37 | 270 | **7.3** |
| 场地后 10% | 14 | 35 | 2.6 |
| **anvil** | **54** | 98 | **2.0** |
| hybrid-cleo12 | 38 | 96 | 2.3 |

**anvil 买的草莓种子比前 10% 还多(54 对 37),每颗只榨出 2.0 个单位对他们的
7.3。** 种植时机也不是原因:hyb-eg20 的草莓种植日与 cleo 完全相同(41 株、
中位第 11 天、p90 13),浇水/收获频率也几乎相同(14.6%/4.4% 对 13.8%/5.0%)。

**同一批地的三方对照(同板,对 starter):**

| 谁在收这 41 株草莓 | 草莓单位 | 单位/种子 | 收入 |
|---|---|---|---|
| cleo 自己 | **270** | 6.6 | 155,344 |
| **endgame 训练过的网(hybrid-endgame20)** | **206** | **5.0** | 118,442 |
| 未训练的网(hyb-d20) | 138 | 3.4 | 103,955 |

**训练买到的正是收获效率:3.4 → 5.0 单位/种子,把与 cleo 的差距合了一半。**
而收获效率恰好就是天梯前 10% 与后 10% 的分界线(7.3 对 2.6)。

**这是反向课程最强的论据**:它改善的东西,正是真实天梯上区分 120k 与 30k 的
那一件事;而 hybrid 之所以有效,是因为它把**收获窗口**也交给了录音——草莓从
第 10 天起每两天出一次,12 天的开局把整个收获期留给我们的网,20 天的开局只
留最后十天。

**下一条要查的**:收获效率的物理原因。浇水频率与收获频率都已追平,所以
剩下的候选是(a)收获的**时点**——持续产出作物有 max_held 上限,不及时收就
浪费后续周期;(b)帮手的收获**目标选择**是最近优先,可能反复走向同一区域。
两者都能在本地一局里数出来。

## 2026-08-22 · 收获效率的物理原因:**施肥让每次产出翻倍,而我们几乎不施肥**

从参考引擎读出持续产出作物的确切机制(`_daily_refresh_plants`,第 787–803 行):

- 产出事件在 `days_since_first % interval == 0` 时发生,**总共 `max_yield` 次**
  (草莓:第 10、12、14、16 天,共 4 次);
- 每次加 **1 个单位**,**若当天浇过水且在施肥期内则加 2**;
- `yield_units` 的上限是 `max_yield`(4),所以**不及时收,后续事件就撞上限浪费**;
- 第 `max_yield` 次产出后 `max_lifespan_step` 被设定,之后 `_decay_plants`
  每 2 步扣 1 点,**到期未收的产量会烂掉**,归零后变杂草;
- 另一条通道:`consecutive_unwatered >= 2` → **整块地立刻变杂草**。

**所以一株草莓的产出区间是 4(不施肥)到 8(施肥且每次都及时收)个单位。**
非持续作物(小麦/甜瓜)更极端:它们的 `yield_units` **只在产量窗口内浇水时
累积**,施肥同样翻倍——小麦不施肥上限是 3,施肥才是 6。

**同板测量(对 starter,seed 424242):**

| | 施肥动作 | 收获动作 | 卖出草莓 | **单位/种子** |
|---|---|---|---|---|
| chisel | **0** | 90 | 6 | 3.0 |
| anvil | **5** | 171 | 88 | 2.3 |
| **hybrid-endgame20** | **46** | 283 | 206 | **5.2** |
| cleo(1.6% × 6,039) | **≈97** | — | 270 | 6.6 |
| 场地前 10%(天梯) | — | — | 270 | **7.3** |

**施肥次数的排序(0 → 5 → 46 → 97)与每颗种子产出的排序(3.0 → 2.3 → 5.2 →
6.6)几乎一一对应**,而引擎机制正好解释它:施肥把每次产出事件从 1 个单位变
2 个,上界从 4 抬到 8。**前 10% 的 7.3 就是"施肥 + 及时收"的理论上限 8 附近。**

**一条要撤回的小推断**:我先看到"39 株草莓有 26 株变成杂草(67%)"就报了警,
但读完 `_decay_plants` 才知道**每株作物寿终都会变杂草**,所以那个比例大部分
是正常的,不能当旱死的证据。(hybrid-endgame20 的比例是 82% 而它的产出最高,
本身就说明这个指标不可用。)

**下一条杠杆是现成的**:`--fert-credit` 已在每条臂的配方里(granger.yaml 用
0.3),也就是说**施肥已经被计入势函数,策略却仍然只做 5 次**。所以下一臂的
单变量应该是把它**调高**——机制上的预期效果是作物产出最多翻倍,而作物是
天梯前 10% 与后 10% 的分界线。这条比再加动作或再加算力都便宜。

## 2026-08-22 · `IDLE_FERTILIZES`:单一对手说 +6,548,九对手说 −438(不采纳)

施肥的**机制**是真的(见上一条判词:每次产出事件 1 → 2 个单位)。但"让闲置
的帮手去施肥"这个动作层补丁**没有兑现它**。

零训练 A/B,同权重同种子。先看**只对 starter、4 个种子**:

| 臂 | 施肥动作 | 卖草莓 | 单位/种子 | 收入中位 |
|---|---|---|---|---|
| legacy | 6 | 62 | 2.9 | 77,700 |
| fert-on | **38** | 77 | **4.2** | **84,248(+6,548,4 个种子全部改善)** |

再看**九个对手 × 96 局**:

| 对手 | 胜率 Δ | 收入中位 Δ |
|---|---|---|
| grazier(spar) | **+12.5** | +2,892 |
| barnyard | +5.2 | +2,145 |
| starter | +0.0 | +690 |
| w49 | +0.0 | +951 |
| ledger_lena | +0.0 | −518 |
| enhanced/main | −2.1 | −2,146 |
| berrybaron(spar) | −3.1 | −2,272 |
| k06 | +0.0 | −2,548 |
| closer_cleo | +0.0 | **−3,136** |
| **均值** | **+1.4 点** | **−438** |

**对被动对手全是正的,对会反应的对手全是负的**——这正是已归档六次的那条规律
(价格相关的机器对不反应的对手有用、对反应者有害)。机制上讲得通:施掉的肥料
就是卖不掉的肥料,而多出来的草莓要卖进一个对手也在卖的市场。

**+1.4 点在 96 局的分辨率下不可解(档案:96 局分辨 10 点差距),不采纳。**

**方法论判词,今天最该记住的一条**:**单一对手 4 个种子给 +6,548,九对手给
−438,相差 7k,而且四个种子全部同向**——种子内部一致性**完全没有**告诉我
它会在别的对手上成立。`docs/VALIDATING.md` 早就写了"要在平衡子集上比较",
今天这条是它的一个昂贵实例:**我差点把 +6,548 当成结论。** 今后任何动作层
标志,**没跑过九对手数组就不算测过**。

**施肥这件事的正确做法仍在奖励侧**:`--fert-credit` 已在配方里(0.3),把它
调高是让**策略自己**决定何时施肥比卖肥料更值——而不是用动作层强制。那是下一
臂的单变量。

## 2026-08-22 · 训练买到的不是"学会施肥",是**照料吞吐**——而这三件事是乘性互补

问题:endgame 训练把每颗种子的产出从 3.4 抬到 5.0,是因为学会了施肥吗?
同一段 20 天开局、同一批地、同一批种子,只换网络(三个种子的中位):

| | 施肥 | 浇水 | 收获 | 卖草莓 | 单位/种子 | 收入 |
|---|---|---|---|---|---|---|
| hyb-d20(未训练的 anvil 网) | 37 | 774 | 238 | 138 | 3.5 | 103,955 |
| hybrid-endgame20(训练过) | **45** | **913** | **283** | **200** | **5.0** | **118,442** |
| 增幅 | +22% | +18% | +19% | **+45%** | **+43%** | +14% |

**答案是不。它三件事各多做约 19%,产出多 43%。** 引擎的机制解释了这个超线性:

- 没浇水 → **当天没有产出事件**;连续两天不浇 → **整块地变杂草**;
- 浇了水但不在施肥期 → 每次事件只有 **1 个单位而不是 2**;
- 不及时收 → `yield_units` 撞上限(4),**后续事件白费**;过期后
  `_decay_plants` 每 2 步扣 1,**存着的产量会烂掉**。

**所以浇水、施肥、收获是乘性互补,漏掉任何一环整个事件就折损。** 吞吐提高
19% 之所以能换来 43%,是因为它同时抬高了三个乘数。

**这条一次解释了三件此前分散的事**:
1. **`IDLE_FERTILIZES` 为什么失败**(上一条判词,九对手 −438):它只填三个
   乘性槽位里的一个,还要付出"肥料卖不掉"的代价。**单动作补丁打不动乘积。**
2. **为什么反向课程会继续付钱**:它改善的是**每回合的照料吞吐**,而吞吐在这个
   乘积结构里有杠杆。endgame 已经把 3.4 → 5.0,顶端是 6.6、场地前 10% 是 7.3。
3. **为什么 anvil 的 26% 闲置既是症状又要紧**:在小农场上没活干(症状),但在
   一个建起来的农场上,闲置就是直接的产出损失——hyb-d20 的产出动作占比 18.4%,
   训练过的是 21.7%,差的这 3.3 个百分点换来 43% 的草莓。

**对下一臂的修正**:我上一条判词写的"下一臂调高 `--fert-credit`"**不够好**
——它只抬一个乘数。正确的单变量是**抬高整个照料三件套的吞吐**。势函数里
已有的 `WATER_STRESS`(未浇水扣分)是三者里唯一被点名的;`--fert-credit` 抬
第二个;而"及时收"目前**完全没有信号**(收获只在钱到账时才被间接奖励,而
`SHED_DISCOUNT 0.9` 反而让棚里的存货比现金便宜)。**最便宜的单变量是给
"撞上限的产量"一个惩罚项**:一块 `yield_units == max_yield` 的地,它下一次
产出事件必然浪费——这个量在观测里已经有,而它是纯物理的、与对手无关。

## 2026-08-22 · 第六条臂 `furrow`:同一个旋钮,从未测过的配方

**天梯上 100% 的场地都有 3 块地**——前 10%、中间、后 10% 三档全部是 3.0 块,
首块地第 7 天(前/中)或第 9 天(后)。**我们的纯 RL 产物只有 2.0 块,而且第 10
天才买第一块。** 势函数给一块地 `LAND_VALUE = 300`,而 iter-160 普查测出每块
地约 **5,000** 的下游作物信用;地价本身只有 1000 / 2000 / 4000。

`--land-value` 只测过一次(**plowman,1500,barnyard 食谱**,6/12),而那一代
**每一条 barnyard 食谱的臂都是 5–6/12,不论修的是什么**。档案里最强的规律是
**"食谱决定一切"**,所以同一个旋钮在**磁带食谱**下是一个未测的变量,不是重复。

`furrow` = chisel 权重 + 磁带池 + `--land-value 2500`,其余与 assay / gleaner
完全相同。**不需要新代码**——这个旗标从 plowman 起就在,而 `land_value=300`
就是门在钉的逐元默认值。

**为什么这条值一个 GPU 名额**(按今天的检查清单过一遍):
- (a) 它不是"新动作",不存在零梯度/掩码链的问题;
- (c) 它每回合都在势函数里生效,不需要"候选多于一个";
- (e) 它抬的不是乘性三件套里的一环,而是**乘积的定义域**——多一块地就是多
  25 格可种植、可放牧的面积,三个乘数同时有更多对象;
- 它是纯物理量(拥有的象限数),不读市价,所以不属于已归档的四条价格阴性。

判据同样是 HELDOUT 与"土地数是否到 3、首块地是否提前到第 7 天"。

## 2026-08-22 · 反向课程**不向前迁移**:它把开局做坏了(主线的中心假设被推翻)

反向课程的全部前提是"从富的中局状态学到的技能会向前迁移到早期"。**这可以直接
测**:`train.py --iters 1` 且**不挂状态库**,it 0 就是"这份权重从第 0 天打完整局"
——第 0 天基线 −54,849 就是这么读的。对 cleo、64 车道、CPU:

| 权重 | 我方收入 | 对手收入 | margin | 熵 |
|---|---|---|---|---|
| chisel(从没见过状态库) | **47,076** | 101,925 | **−54,849** | 13.25 |
| backplay-d16 | 33,298 | 119,068 | **−85,770** | 7.58 |
| **backplay-d12** | **29,398** | 119,892 | **−90,494** | 7.79 |

**它不但没有迁移,还把整局收入做低了 37%,margin 恶化 35.6k。** 熵从 13.25 塌到
7.79——策略在状态库的分布上变得非常确定,而那份确定性在第 0 天是错的。

**机制:灾难性遗忘,而且是我的设计缺陷。** 我把起始分布做成了**累积**的
(第 d..20 天,判词见 08-22 "反向课程改成累积起始分布"),这解决了段与段之间的
遗忘——d16 因此 26 个迭代就追上了 endgame 用 304 个迭代达到的水平。但**没有
任何一段包含真正的第 0 天开局**:库只有第 4/8/12/16/20 天,而第 4 天的库里
cleo 只有 405 元、什么都还没建,所以它**替代不了**第 0 天。于是四段训练下来,
开局这一段从未被采样过,直接漂掉了。

**这同时解释了另一个此前的读数**:难度剖面里"第 4 天的库比第 0 天还难"
(−59,561 对 −54,849)——不是库没用,是**第 0 天这件事本身没有任何一段在练**。

**已经做的调整**(d0 段还没开始,所以来得及):
- 原计划 6 link、`--bank-frac 0.5`(一半真第 0 天)→ 改为 **8 link、
  `--bank-frac 0.35`(65% 真第 0 天开局)**,因为它现在要从 −90.5k 把开局
  重新学回来,比原计划的工作量大;
- 初始权重仍取 **d12**(不是 chisel):d12 从第 12 天出发是 −8.2k 而 chisel 是
  −46.2k,**晚段的本事很值钱,要保住**。所以 d0 段的形状就是"学出来的 hybrid"
  ——用真第 0 天开局把前 12 天补回来,同时用库把后 18 天钉住。

**设计规则入档(下一次做课程必须遵守)**:**反向课程的每一段都必须保留一部分
真正的初始状态开局**(`bank_frac < 1` 全程),否则最终阶段要从一个比起点更差的
开局重新学。文献里这条是标准做法,我只做对了一半(把库做成累积的),漏掉了
"库里必须包含 day 0"——而 day 0 没有库,所以只能靠 `bank_frac`。

**判据也要改**:此前每段的判词看的是"该段起点的 margin"(d16 −7,688、
d12 −8,152),那个数**只说明它在库的分布上变好了**。真正要盯的是**第 0 天整局
的 margin**,而这条判词就是它第一次被测出来。d0 段的花名册是最终判据。

## 2026-08-22 · 课程的价值和它的失败要分开算:**晚段本事值 +11.8k**

上一条判词说课程不向前迁移(从第 0 天打整局比 chisel 差 35.6k)。但那不等于
课程没用——它学到的东西**localised 在第 12–30 天**,而这可以直接兑现:把
`backplay-d12` 的权重接在**同一段 12 天 cleo 开局**后面,与已提交的
`hybrid-cleo12`(天梯 705.9,同一段开局 + anvil 的网)逐对手对比。每臂 **864 局**:

| 对手 | hybrid-cleo12 | **hybrid-d12net** | Δ |
|---|---|---|---|
| closer_cleo | −42,248 | **−24,354** | **+17,894** |
| ledger_lena | −43,999 | **−24,682** | **+19,317** |
| broker_bea | −43,335 | **−25,409** | **+17,926** |
| w49(未在任何池) | −52,299 | **−37,259** | **+15,040** |
| enhanced/main | 99.0% / +34,664 | **100% / +45,479** | +10,815 |
| grazier(spar) | 83.3% / +18,483 | **91.7% / +33,899** | +15,416 |
| berrybaron(spar) | 99.0% / +15,443 | **100% / +28,949** | +13,506 |
| barnyard | +37,244 | **+50,410** | +13,166 |
| starter | +77,773 | +68,975 | **−8,798** |
| **收入中位** | 61,152 | **72,959** | **+11,807** |
| **p05** | 37,354 | **47,259** | **+9,905** |

**除 starter 外每个对手都变好,四堵墙各收窄 15–19k,而这只是 d12 段的第 66 个
迭代。** 唯一的退步(starter)正是可预期的**池专化**:d12 全程 `bank-frac 1.0`、
只对着 cleo/lena/k06 三条磁带从库里训练,**它从没见过弱对手**。

**所以当前的账是这样的:**
- 课程**确实**产出了更强的晚段网络(比已提交产物的网络多 11.8k 中位);
- 课程**没有**产出更好的开局(第 0 天整局 −90.5k 对 chisel 的 −54.8k);
- 两者合起来的形状,就是 d0 段要学的东西:**保住晚段、把前 12 天补回来**。
  d0 段已按此重建(8 link、`bank-frac 0.35` 即 65% 真第 0 天开局,初始权重取
  d12 而不是 chisel)。

**顺带一条方法论**:hybrid-d12net 对 **starter 单一对手**是 71,800 对 83,828
(更差),对九个对手是 **+11.8k 中位**(更好)。**又一个"单一对手会给出反向
结论"的实例**——今天第二次,前一次是 `IDLE_FERTILIZES`(+6,548 对 −438)。
检查清单第 (d) 条再确认一遍。

## 2026-08-22 · 四个 hybrid 对齐:**课程的晚段训练 ≈ 八天录音**

同一批 9 个对手(864–1,152 局/臂),把开局长度与网络质量交叉:

| 臂 | 开局 | 网络 | 收入中位 | p05 | cleo | lena | w49 |
|---|---|---|---|---|---|---|---|
| hybrid-cleo12(已提交 705.9) | 12 天 | anvil | 61,152 | 37,354 | −42,248 | −43,999 | −52,299 |
| **hybrid-d12net** | 12 天 | **课程 d12(66 迭代)** | **72,959** | 47,259 | −24,354 | −24,682 | −37,259 |
| hyb-d20 | **20 天** | anvil | 74,801 | 44,408 | −22,648 | −21,849 | −33,576 |
| **hybrid-endgame20** | **20 天** | **endgame(304 迭代)** | **88,810** | **50,512** | **−7,774** | **−6,150** | **−21,413** |

**两项贡献几乎等量,而且可加**:
- 12 天开局下把网络从 anvil 换成课程网:**+11,807**;
- anvil 网下把开局从 12 天延到 20 天:**+13,649**;
- 20 天开局下把网络换成训练更久的 endgame:**+14,009**。

**最有用的是这条等价关系:课程网 + 12 天开局(72,959)≈ 未训练网 + 20 天开局
(74,801)。也就是说,课程的晚段训练大约值"八天第三方录音"。**

这给纯 RL 线一个可计量的目标:**hybrid-endgame20 的 88,810 = 20 天录音 + 304
迭代的晚段训练。若 d0 段能把"八天录音"那一份换成自学的开局,我们就能在
不用任何录音的情况下站到 74k–89k 之间**——而 chisel 从第 0 天出发的整局中位
是 47k。要补的正好是这个差。

**提交候选确认**:`hybrid-endgame20` 在这张表上每一项都最好(中位 88,810、
p05 50,512、四堵墙 −6k~−21k),它仍是唯一通过全部验收的候选。诚实标注不变:
20/30 天是录音,所以它是提交候选而**不是**"用 RL 达到 2000"的答案。

## 2026-08-22 · 第七条臂 `seedling`:**正向课程(局长)**,反向课程的互补方向

反向课程教不了开局(判词:从第 0 天整局 −90,494 对 chisel 的 −54,849,因为没有
任何一段采样过第 0 天)。互补的方向是**把局缩短,让开局成为唯一的问题**。

**为什么取 15 天**:1,588 份真实天梯农场记录里,最强的单一分档量是**资金@15**
——前 10% 是 **21,360**,我们是 **14,405**(中间档 14,284,所以我们**就在中位**)。
15 天局的终局回报直接就是这个量。

**为什么它不会教出"清仓"**:Ng 型 shaping 逐步是 `γφ(s') − φ(s)`,望远镜求和到
**`γ^T φ(s_T) − φ(s_0)`**,所以**截断处的势能在回报里**。目标于是是"**建出最好的
第 15 天局面**",而不是"第 15 天前把东西卖光"。这一点是这条臂能不能成立的关键,
所以写在这里。

**为什么它不可能有遗忘问题**:后面没有东西可忘。这正是反向课程失败的那个机制的
反面。

**顺带的效率**:15 天局是 360 步而不是 719,所以同样算力下**每单位时间的对局数
翻倍**,而开局这一段被采样的次数是原来的 4 倍(2 倍对局 × 每局全部在开局)。

**形状**:A 段 3 link,`--steps 361`(15 天);B 段 3 link,`--steps 720`(整局),
从 A 段权重继续。这是标准的正向课程/局长退火。起点仍是 chisel 权重,所以 it 0
与其余六条臂可比。**不需要新代码**——`--steps` 从一开始就在。

**判据**:B 段尾部的 12 对手花名册(HELDOUT),外加**第 0 天整局的 margin**
(要好过 chisel 的 −54,849,那是反向课程做不到的那一格)。

### 补记(同日,烧掉 GPU 之前核实承重假设)

`seedling` 的整条臂压在一句话上:"截断处的势能在回报里,所以短局优化的是建设
不是清仓"。我是从 Ng 公式推的,在提交之后回去**读了代码核实**,结果对了一半:

**对的那一半**(`trl_env._finish_step`):`r = (γ·φ(s') − φ(s)) / shape_scale`
**每一步都算,包括最后一步**;`done` 时的 `win_bonus` / `margin_bonus` 是
**相加**(`r = r + ...`)而不是替换。所以第 15 天局面的势能确实进了回报。

**错的那一半**:`granger.yaml` 带 **`win_bonus: 1.5`**,而它比较的是
**终局谁的现金多**。**1364 档在早期故意持有更少现金、更多资产**——cleo 第 12 天
只有 **10,195** 元而它的农场值好几倍。所以在 15 天局里这一项**恰好在推向不投资**,
正是这条臂要避免的那个畸变。

**已改**:A 段(15 天)加 `--win-bonus 0 --margin-bonus 0`,**只留 shaping**,
目标就是纯粹的"最好的第 15 天局面";B 段(整局)恢复,因为第 30 天现金**就是**
比分。

**记档规则**:**一条臂如果压在某个奖励项的行为上,提交后要回去读那段代码。**
今天这一次核实同时确认了一半、推翻了一半,而被推翻的那一半会把 3 个 GPU link
花在优化"第 15 天现金比对手多"上——那与目标相反。

## 2026-08-22 · 累积状态库 ≈ **4.6 倍算力**(设计的第一份直接证据)

同一段 20 天 cleo 开局,只换后面的网络,同一批 9 个对手(432–1,152 局/臂):

| 网络 | 训练 | 中位 | p05 | cleo | lena | bea | w49 | main |
|---|---|---|---|---|---|---|---|---|
| anvil | 未见过状态库 | 74,801 | 44,408 | −22,648 | −21,849 | −22,261 | −33,576 | +54,112 |
| **d12** | **累积库(第 12/16/20 天),66 迭代** | **90,788** | 50,016 | **−7,273** | **−4,917** | **−5,252** | −21,963 | **+67,878** |
| endgame | 单点(只第 20 天),**304 迭代** | 88,810 | **50,512** | −7,774 | −6,150 | −6,377 | **−21,413** | +64,709 |

**66 个迭代的累积库训练与 304 个迭代的单点训练打平**:中位、cleo/lena/bea 三堵墙、
enhanced/main 上 d12 略优,p05 与 w49 上 endgame 略优——差距在 432 局的分辨率内
属于**持平**。**所以累积状态库大约值 4.6 倍算力。**

这是这个设计(今天引入,判词"反向课程改成累积起始分布")的**第一份直接证据**;
此前只有间接的一条(d16 用 26 个迭代追上 endgame 用 304 个迭代达到的 margin)。
**机制**:单点库只教"从第 20 天的那一种局面继续",累积库教"从第 12–20 天的
任意局面继续",后者的状态覆盖宽得多,而这个游戏的晚段本来就是同一套照料动作
在不同规模的农场上重复——覆盖宽度直接换成样本效率。

**对交付物的影响**:`hybrid-d12net20`(20 天开局 + d12 网)中位 **90,788**,是
本项目**目前最强的本地产物**,略高于已打包的 `hybrid-endgame20`(88,810)。而
**d12 段还有 2 个 link 没跑完**,所以链尾重建一次这个 hybrid 会更强。**若用户
批准提交,应该等 d12 链尾再打包一次**,而不是发现在这个 66 迭代的中间检查点。

**但它仍然不是"用 RL 达到 2000"的答案**:20/30 天是录音。这条判词量的是
**课程设计的效率**,不是纯 RL 的进度。
