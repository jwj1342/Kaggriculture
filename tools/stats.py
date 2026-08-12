#!/usr/bin/env python
"""The two estimators every ranking in this repo depends on.

They lived in two files each -- `bradley_terry` in `league.py` and
`tournament.py`, a Wilson interval open-coded wherever one was needed -- and the
copies had already drifted on their convergence settings (1,000 iterations at
1e-10 against 2,000 at 1e-11). They agreed to 1.7e-10 on a twelve-agent case, so
nothing published was wrong, but **the estimator that produces every number in
`docs/` should not exist twice.** A fix to one would not have reached the other.

Nothing here touches the database, the filesystem or the network: pure
functions, which is what makes them the one part of this codebase that is
straightforward to test.
"""

import math


def bradley_terry(wins, games, names, iters=2000, tol=1e-11):
    """Zermelo / MM iteration for Bradley-Terry strengths.

    `wins[(i, j)]` is how often `i` beat `j` and may be fractional, because a tie
    counts a half to each side. `games[(i, j)]` is how often they met. Strengths
    are normalised to mean 1.0, so they are comparable within one call and
    meaningless across calls -- a Bradley-Terry fit has no absolute scale.

    Kaggle fits the final leaderboard the same way, which is the reason to rank
    locally with this rather than with a mean of anything.
    """
    p = {n: 1.0 for n in names}
    for _ in range(iters):
        new = {}
        for i in names:
            num = sum(wins.get((i, j), 0.0) for j in names if j != i)
            den = sum(games.get((i, j), 0) / (p[i] + p[j]) for j in names
                      if j != i and games.get((i, j), 0))
            new[i] = num / den if den > 0 else p[i]
        tot = sum(new.values()) or 1.0
        new = {k: max(v, 1e-12) / tot * len(names) for k, v in new.items()}
        if max(abs(new[k] - p[k]) for k in names) < tol:
            return new
        p = new
    return p


def elo(strengths, scale=400.0):
    """Bradley-Terry strengths on an Elo-like scale, centred on the field."""
    import statistics
    if not strengths:
        return {}
    mid = statistics.median(math.log10(max(v, 1e-12)) for v in strengths.values())
    return {k: scale * (math.log10(max(v, 1e-12)) - mid) for k, v in strengths.items()}


def wilson(k, n, z=1.96):
    """Wilson score interval for `k` successes in `n`, as percentages.

    Used instead of the normal approximation because win rates here routinely
    sit near 0% or 100% -- a saturated reference field is the normal case, not
    the exception (`docs/VALIDATING.md` §1) -- and the normal interval runs off
    the end of the scale there.
    """
    if not n:
        return (0.0, 100.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (centre - half), 100 * (centre + half))


def resolved(k, n, z=1.96):
    """Does this interval exclude 50%? If not, how many episodes would?"""
    lo, hi = wilson(k, n, z)
    if lo > 50.0 or hi < 50.0:
        return True, n
    p = k / n if n else 0.5
    d = abs(p - 0.5)
    if d < 1e-6:
        return False, None                      # a true coin flip never resolves
    return False, int(math.ceil((z * z * 0.25) / (d * d)))
