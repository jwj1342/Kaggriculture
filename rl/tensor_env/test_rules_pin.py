#!/usr/bin/env python
"""Pin every price-model mirror against the INSTALLED engine.

The 1.32.7 rebalance (hinge scarcity pricing on CARROT/TOMATO/EGG) sat
undetected from the 08-18 venv rebuild until a tape reconstruction
failed: every byte-exact gate in this repo compared the tensor line to
OUR OWN mirrors, and nothing compared the mirrors to the package that
`tools/eval.py` actually runs. This gate closes that hole: it imports
the installed `kaggle_environments` engine and requires

  * agents/kg_rules.market_price   == installed market_price
  * rl/tensor_env/engine_np.market_price == installed market_price

for every product over an inventory sweep that crosses both sides of
I0, the hinge knee at I0 - T, and the $1 floor. Run it after every
package upgrade -- it is the executable form of CLAUDE.md's "re-diff
the reference copy after every upgrade".

Ends PIN-PASS / PIN-FAIL.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_HERE, _RL, os.path.join(_REPO, "agents")):
    if p not in sys.path:
        sys.path.insert(0, p)


def main():
    from kaggle_environments.envs.kaggriculture import kaggriculture as REAL
    import kg_rules as KR
    import engine_np as E

    # parameter tables must match row for row
    for item, p in REAL.MARKET_PARAMS.items():
        for mirror, name in ((KR.MARKET_PARAMS, "kg_rules"),
                             (E.MARKET_PARAMS, "engine_np")):
            if mirror[item] != p:
                print(f"PIN-FAIL {name}.MARKET_PARAMS[{item}]:\n"
                      f"  mirror   {mirror[item]}\n  installed {p}")
                return 1

    bad = 0
    checked = 0
    for item, p in REAL.MARKET_PARAMS.items():
        i0, t = p["I0"], p["T"]
        # dense around the knee and I0, sparse over the long tails
        invs = set(range(i0 - 3 * t - 10, i0 + 3 * t + 10, max(1, t // 25)))
        invs |= set(range(i0 - 20_000, i0 + 40_000, 997))
        invs |= {i0 - 1, i0, i0 + 1, i0 - t, i0 - t - 1, i0 - t + 1}
        for inv in sorted(invs):
            want = REAL.market_price(item, inv)
            got_k = KR.market_price(item, inv)
            got_e = E.market_price(item, inv)
            checked += 1
            if got_k != want or got_e != want:
                bad += 1
                if bad <= 5:
                    print(f"PIN mismatch {item}@{inv}: installed {want} "
                          f"kg_rules {got_k} engine_np {got_e}")
    if bad:
        print(f"PIN-FAIL ({bad}/{checked} points differ)")
        return 1
    print(f"PIN-PASS: {checked:,} (item, inventory) points, "
          f"both mirrors == installed engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
