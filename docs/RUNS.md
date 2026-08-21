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
