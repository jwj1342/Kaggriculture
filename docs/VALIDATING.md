# Is my agent actually better? — the short version

Written because this project has now made the same mistake at both ends: a
reference field that **everything beats**, and a reference field that
**everything beats by the same amount**. Both produce confident numbers that mean
nothing, and neither announces itself.

If you read one thing here, read §1.

---

## 1. Pick the field that matches your agent's level

There are two, and using the wrong one wastes the run.

| your agent wins… | use | why |
|---|---|---|
| **50–70%** of `agents/bench3` | `agents/bench3/*.py` | engine level: shapes near yours, both ends open |
| **95%+** of `agents/bench3` | `closer_cleo`, `slotter_silas`, `ledger_lena`, `broker_bea` | wrapped level: the only field that still separates |

The second row is not a refinement, it is a different measurement. On
2026-08-11, eight variants of a `closer_cleo`-class agent scored **99.4% on the
ghost field and could not be told apart**; `bench3` put the same eight at 92–98%.
Against each other the same four agents space out cleanly — 92.7 / 73.8 / 54.1 /
29.3 over 3,072 episodes — because none of them is saturated against the others.

Rebuild both with:

```bash
bash tools/fetch_fields.sh          # ref agents, ghosts, lines, bench3
```

**Run it before your first measurement.** `agents/` is git-ignored in full, so a
fresh clone has no opponents at all — and a bench without the reference agents
measures our own family against itself, which is the mistake that cost this
project a week (`docs/LADDER_FIELD.md`).

## 2. How many episodes

| you are trying to resolve | episodes per arm |
|---|---|
| 10 points | 96 |
| 5 points | 384 |
| 3 points | ~2,000 |
| an engine change you intend to submit | **≥2,000**, plus the ghost field |

**Four seeds resolve nothing.** Three separate changes read positive over four
seeds and were 21 to 44 points *behind* over 2,304 episodes an arm. A smoke test
is a syntax check.

Sizing on the cluster — 0.375 episodes per core-second with `KG_FAST_ENV=1`:

```bash
sbatch --array=0-15 --cpus-per-task=32 --mem=40G --time=00:30:00 \
    slurm/tournament_array.sh panel \
    --agents agents/mine/*.py --panel agents/bench3/*.py \
    --seeds 96 --jobs 32 --label mylabel
python tools/tournament.py ingest --shards data/shards/mylabel
```

Short jobs start, long ones queue: the same work at `--time=03:00:00` with 64
cores waited 78 minutes; at `--time=00:30:00` with 32 it started immediately
across sixteen nodes.

## 3. Reading the result

**Report two numbers, not one.** The wrapped reference agents are unbeatable for
an engine-level agent (we win 0.2%). Averaging them into one headline adds a
constant: three unbeatable opponents in fifteen depress every score by about 25
points, which is how "43%" turned out to mean "73.5% against opponents we can
contest, and 0% against three we cannot".

**When win rate saturates, read median money.** In the terminal-window sweep the
ghost win rates were identical across eight arms and the money ordered them
correctly, agreeing with the un-saturated field.

**A non-monotone curve is not a result.** It means the variable you swept is not
the variable that matters. The first terminal-window sweep gave 95.6 / 98.6 /
89.8 / 94.1 / 85.1 — the dip in the middle was the signal to sweep finer, and the
finer sweep found a clean plateau.

**Check the mirror.** Run the candidate against itself. Scores roughly halve; if
they more than halve, the agent depends on a passive opponent.

## 4. Two ways to get a confident wrong answer

**The harness silently ran different code.** `get_last_callable` returns
`[v for v in env.values() if callable(v)][-1]` — the last *callable value* in the
module dict. Wrapping an agent (`_INNER = agent`, then a new `def agent`) leaves
`_INNER` last, so the framework loads the **unwrapped** agent; every arm then
scores identically and the tidy conclusion is "the change is worth nothing". A
helper `def` placed after `agent` does the same. Park callables in lists, `del`
helper names, and **verify by asking the loaded function for a known answer** —
compiling is not enough. `tools/hybrid.py:_verify` is the pattern.

**The engine was right and you read it backwards.** A probe showed the farm
buying no seed for ten days on $109–$435 and it looked like a deadlock.
"Fixing" it lost 8–14 points over 137,644 episodes: the cash was going to
livestock, which is worth more. Nothing in the code said so — it fell out of a
cash floor meeting a purchase-rate limit. **Before concluding an engine is
broken, find out what it spent the resource on.**

## 5. Same-named builds

`short(path)` is the **basename**, so two builds called
`smallhold-crew-mgtight-…` from different directories merge into one ratings row
in the database. Two runs were corrupted this way.

For an A/B where the arms share names — every engine ablation — read the shard
JSONL directly and key on the full path. Do not ingest:

```python
import glob, json, collections, os
w = collections.Counter(); g = collections.Counter()
for s in glob.glob("data/shards/<label>/shard-*.jsonl"):
    for line in open(s):
        r = json.loads(line)
        for i, side in enumerate(("left", "right")):
            a = r[side]
            if "/bench3/" in a or "/ref/" in a:      # panel, not candidate
                continue
            g[a] += 1                                 # full path, not basename
            w[a] += (r["money"][i] > r["money"][1-i]) or \
                    0.5 * (r["money"][i] == r["money"][1-i])
for a in sorted(g, key=lambda k: -w[k]/g[k]):
    print(f"{100*w[a]/g[a]:5.1f}%  {a}")
```

## 6. Before you submit

`docs/SUBMISSION_POLICY.md` is the full checklist. The three that get skipped:

* **`python tools/stress.py <file> -j 14` must be 28/28.** A crash forfeits the
  whole episode and the ladder does not tell you it happened.
* **Exactly one substantive change.** Two correct changes can cancel — alternate
  day watering and fertilising were both right and together worth nothing until
  the phase interaction was found.
* **Deactivation is by recency, not score.** Submitting a third agent drops the
  *older* of the two active ones even if it is your best. This has already cost
  a 1363.7 and a 1287.2 in one night.
