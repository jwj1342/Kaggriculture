# Public candidates for the final selection

Acquired 2026-09-29. This is a static artifact review, not a strength claim.
All original downloads are under `data/endgame-public/`; no existing opponent
directory or submission snapshot was changed. `manifest.json` and `SHA256SUMS`
record source URLs, versions, dates, complete hashes and package checks.

## Ready for Slurm evaluation

| Label | File relative to `data/endgame-public/` | Pinned notebook | Source page date | SHA-256 prefix |
|---|---|---|---|---|
| State router | `state-router/output/main.py` | V3, script 347936183 | 2026-09-07 | `b87a27ed614a3332` |
| Conditional memory | `conditional-memory/output/main.py` | V3, script 340501157 | 2026-08-06 | `d9dc24ce5429ec62` |
| Rayk low-pressure opening | `rank-your-agent/output/main.py` | V27, script 349567011 | 2026-09-13 | `8f03b16618586e1d` |
| Shop router, reserved opponent | `shop-router-0913/output/main.py` | V1, script 349474696 | 2026-09-13 | `77cf67723a753be9` |

All four `submission.tar.gz` files contain only root-level `main.py`, byte-for-byte
equal to their sibling Python file. All use only the Python standard library.
The API's `lastRunTime` fields report September 26 for these artifacts, while
the actual notebook content/page dates above are older. A rerun is not a new policy.

### State router

[Source](https://www.kaggle.com/code/thomastschinkel/kaggriculture-93-8-win-rate-public-state-router).
Five embedded 719-action tapes; decisions at six-day boundaries use public town
shops and carrot price. The code builds a larger feature vector including its own
private inventory, which is part of its legal observation. It does not read rival
private inventory or hidden current actions. Returning action lists makes fresh
copies. There is no environment import, filesystem access or network use; the
`__main__` block implements stdin/stdout only.

The advertised 93.8% describes frozen replay opponents: 689 tapes, 32 seeds and
both seats, plus a smaller independent panel according to the notebook. Fixed
opponents cannot respond to counterfactual market changes. These figures are
author-reported and have not been reproduced here. Route alignment and robustness
must be established by current-engine, reacting-opponent matches.

### Conditional memory

[Source](https://www.kaggle.com/code/kaitofukami/177-180-fresh-top-30-v21-1-conditional-memory).
One embedded route and 30 public-farm signature memories; nearest-neighbor matching
reorders existing sale orders. It also aligns workers, clamps sales to available
stock, repairs some weed-blocked actions and liquidates at the end.

The word “Fresh” is misleading for today's decision: the data cutoff is August 6,
and the notebook explicitly says it used engine 1.32.4. The 177/180 result contains
only 134 unique episodes, against fixed replay trajectories. Its later holdout
fell to 46/51. The notebook still contains unresolved `{base[...]}` placeholders
in its detailed route-provenance paragraph; do not claim that donor provenance was
fully reconstructed. This is an older control worth measuring, not evidence of
current gold strength.

### Rayk low-pressure opening

[Source](https://www.kaggle.com/code/raykkretzschmar/kaggriculture-rank-your-agent).
Use the output `main.py`, not the notebook's weak `my_agent.py` template. The output
is `v38_low_pressure_opening_20260913`: shop-dependent routes, market reactions,
labor and animal/crop extensions, storage and feed guards, and terminal planning.
Its opening buys 5 wheat, buys another 10, then sells up to 60.

The file contains two `exec` calls whose arguments are literal source strings.
Both were recursively parsed and inspected: deterministic official-engine unit
semantics and a bounded terminal physical planner. Their only additional imports
are `copy.deepcopy` and `time.perf_counter`. No unchecked dynamic code, subprocess,
network access, filesystem access, hidden-state access or external attachment was
found. Runtime latency and silent fallback counters still require Slurm checks.

The notebook reports 630/640 on a held-out local panel. This has not been reproduced
here. The webpage's historical “Best Score 2990.4 V11” belongs to an older version;
the downloaded V27 bytes must not inherit that score.

### Reserved external opponent: Shop Router 0913

[Source](https://www.kaggle.com/code/yhay81/shop-router-0913).
This is a distinct simple policy: compressed fixed tapes, a public first-two-shops
lookup at step 144, and a terminal route switch at step 648. No action repair or
dynamic economics layer. There is only one function, `agent`, with no I/O or
dynamic source execution. It returns the stored action object directly, so the
evaluation harness must not mutate returned actions in place.

Keep its outcomes out of candidate tuning and use fresh paired-seat seeds after
selecting finalists. It is a distinct artifact, but **not a fully independent
strategy lineage**: Rayk credits earlier yhay81 routes from September 8–11.
A separate reacting family or newly collected opponent sample would strengthen
the final check further.

## Attribution and license evidence

- Conditional memory: the [original notebook page](https://www.kaggle.com/code/kaitofukami/177-180-fresh-top-30-v21-1-conditional-memory/notebook)
  explicitly states Apache 2.0. Preserve the original notebook's mechanism credits
  and route-provenance statement alongside any derived artifact.
- Rayk: complete Apache 2.0 text and named upstream credits are embedded in the
  downloaded `main.py`. Preserve them, retain relevant notices, and identify any
  local changes. Its embedded engine-derived code references `NOTICE.txt`, but the
  original output archive includes only `main.py`; include accurate provenance
  documentation when building a derivative package.
- State router and Shop Router 0913: their downloaded source files and API metadata
  do not establish the license. Public accessibility is not enough to infer one.
  They are ready for local evaluation; confirm the original page's license before
  republishing or submitting a derived artifact. Do not silently label them MIT
  or Apache based on another notebook by the same author.

All four runtime policies use their supplied observation and embedded historical
data. Static review found no attempts to identify hidden seeds, inspect the runner,
obtain opponent private state, or communicate externally. This review does not
replace the competition rules or runtime tests.

## September 29 evening: two contemporary additions

Acquired after the original four were frozen. These are current competing
implementations, not independent strategy families. Do not pool their results as
if they were two unrelated samples of the population.

| Source | Current artifact | File relative to `data/endgame-public/` | SHA-256 prefix |
|---|---|---|---|
| [flexonafft](https://www.kaggle.com/code/flexonafft/kaggriculture-multi-route-farming-agent) | Step1010, fixed-point market closure | `multi-route/output/main.py` | `03165654e70bd044` |
| [tetsutani](https://www.kaggle.com/code/tetsutani/demand-preserving-turn-sale-timing) | Step1009, forty-one market closure passes | `demand-preserving/output/main.py` | `55be5d5f124c8daa` |

Both inherit the V39/Metav4/HybridOpening/Rescue production and market lineage.
Their inherited notices are identical. Step1010 replaces the repeated closure
stack with a bounded fixed-point loop, at most 48 applications, with stable/cycle
termination handling. This can affect both latency and final actions; the fresh
reacting-opponent evaluation must determine its value. Notebook “promoted” and
“strongest” language is the author's local claim. The source itself retains some
older HOLD comments; neither those comments nor a successful self-play notebook
establish current ladder strength.

### Static checks and package contents

- Original archives include `main.py`, `LICENSE.txt` and `NOTICE.txt`. Extracted
  `main.py` matches the archive bytes. The flexonafft original archive is named
  `submission_step1010_idle_seller.tar.gz`.
- Imports are standard-library only. Two literal `exec` strings were parsed
  recursively: the same deterministic engine fragment and terminal planner
  reviewed for Rayk. No unchecked dynamic payload was found.
- There is a dormant `open(path)` in an inherited optional replay-library loader;
  its local `path` is unconditionally `None`, so no external file is read.
  The imported `os` alias has no calls. There is no network or subprocess code.
- An inherited mixed-opening experiment contains a configuration-seed RNG branch.
  The shipped policy fixes `_ALT_MODE = 'HybridOpening'`; the `Mixed` branch is
  unreachable in these exact bytes. Keep that fact tied to the artifact hashes.
- The final module binding is `kaggle_submission_agent = agent`, pointing at
  Step1010 / Step1009 respectively. Runtime latency, fallback counters, and
  robustness are left to the parent agent's Slurm jobs.

### License and attribution handoff

Both original archives explicitly supply Apache 2.0 license text and a 5,043-byte
`NOTICE.txt`; preserve these files and their inherited source notices in any
package. This evidence is stronger than inferring a license from a page title.

Rayk's missing historical engine/planner notice can now be documented from the
public descendant's retained E182/E180 notice. Materials and provenance are in
`data/endgame-public/rank-your-agent/licensing/PACKAGING.md`. They include the
unchanged public Apache text, the directly downloaded Kaggle engine license, and
an explicitly labeled historical notice excerpt. The original Rayk source and
archive were not edited or repackaged by this task.

The inherited E180 notice also states that the exact Thomas state-router V3
hash `b87a27ed614a3332...` was published under Apache 2.0. This is useful upstream
attribution evidence; direct source-page license verification was still unavailable
in this acquisition session. No newly invented episode donor identities are added.
