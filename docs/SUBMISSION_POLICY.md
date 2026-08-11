# When to submit, and what

Five submissions a day, **only the latest two active**, and the ladder plays
roughly ten episodes an hour per active agent. Those three numbers together mean
a submission is not free and a *burst* of submissions is actively destructive.

This file exists because that was learned the expensive way: six submissions in
one afternoon left every one of them with 4–12 games. `55385995` read 837 at five
games and 647 at ten, and neither number meant anything.

---

## The rules

**1. One submission per half-day. Two absolute maximum.**
An agent needs **40+ episodes** before its score means anything, and that is four
hours of ladder time. Submitting again inside that window throws away the
measurement you were waiting for.

**2. Never submit without a completed local A/B.**
The bar is a win rate against `agents/bench3` — which now contains the public
meta agents — over **≥2,000 episodes an arm**, plus the ghost field. A four-seed
smoke test has pointed the wrong way four separate times; it is a syntax check,
not evidence.

**3. Never submit two changes at once.**
Two changes that are each correct can cancel: alternate-day watering and
fertilizing were both right and together were worth nothing until the phase
interaction was found. If two are ready, submit the larger and hold the other.

**4. The two active slots are an experiment, not a shop window.**
Keep the incumbent in one slot and the challenger in the other, so they play the
same field at the same time. Replacing both at once means the next comparison has
no control.

**5. Snapshot before submitting, always.**
`submissions/<date>-<name>/main.py`, byte-identical to what was uploaded, and a
row in `docs/RUNS.md` with the local evidence that motivated it. A ladder entry
has to stay traceable months later.

**6. Stress before submitting, always.**
`python tools/stress.py <file> -j 14` must be 28/28. A crash forfeits an entire
episode, and the ladder does not tell you it happened.

---

## The checklist

```
[ ] beats the incumbent over ≥2,000 episodes an arm against agents/bench3
[ ] measured against the ghost field too (tools/tournament.py ghosts)
[ ] exactly one substantive change since the incumbent
[ ] 28/28 on tools/stress.py, worst turn well under 1,000 ms
[ ] get_last_callable resolves to `agent`
[ ] snapshotted under submissions/<date>-<name>/
[ ] the incumbent has ≥40 ladder episodes, so its score is real
[ ] a row written in docs/RUNS.md
```

If the last box cannot be ticked, **wait**. The information you are about to
overwrite is worth more than the hours you save.

---

## What to do with the waiting time

The wait is not idle time — it is when the local loop earns its keep:

* `tools/ladder.py pull` on the incumbent, then read the **action histogram**,
  not just the digest. That is where the two largest improvements came from.
* Re-measure against `agents/bench3` and the ghosts. Both saturate; regenerate
  them when a candidate beats them above ~90%.
* Re-run previously **rejected** changes. The field has changed three times, and
  a rejection made against a weak field is not a fact about the game — the wheat
  filler failed three times and then won.

---

## Quota mechanics

Resets at **UTC midnight**. `kaggle competitions submission-limits kaggriculture`
reports what is left. Watch for the reset rather than polling by hand:

```bash
until [ "$(kaggle competitions submission-limits kaggriculture 2>/dev/null \
    | grep -oP 'Remaining today: \K\d+')" != "0" ]; do sleep 600; done
```

Deactivation is by recency, not by score: submitting a third agent drops the
oldest of the two active ones **even if it is the best**. Check which two are
active before submitting, and be deliberate about which one you are retiring.
