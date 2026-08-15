"""Single-pass board analysis: analyze(obs) -> Analysis.

One walk per farm produces everything the per-step feature code used to
re-derive in four separate walks: the (2, C, 10, 10) float32 encode block
(obs.encode), the scan dict (actions masks/decode), the standing-asset sums
(obs.net_worth / obs.opp_visible_worth) and the herd size (BUY_WHEAT decode).

The implementation lives in actions.py, not here: exported agent directories
copy exactly obs.py / actions.py / kg_rules.py (renamed kg_rl_*) and must stay
self-contained, so this module only re-exports for engine-side callers.
`analysis(obs)` is the memoised entry point (keyed on observation object
identity, one obs dict per worker step).
"""

import os
import sys

_RL = os.path.dirname(os.path.abspath(__file__))
if _RL not in sys.path:
    sys.path.insert(0, _RL)

from actions import Analysis, analyze, _analysis as analysis  # noqa: E402,F401
