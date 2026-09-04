#!/usr/bin/env python
"""Clone-invariant rankings over arena.sqlite: Nash averaging, alpha-Rank, IQM.

    python tools/nashrank.py --label toprr-v1 --external data/plan_ladder.json

WHY THIS EXISTS. Every local ruler this project has built gets the top tier
BACKWARDS. The known answer is k01 (ladder 2302.2) > k06 (2035.9), and seven
rulers in a row have ranked k06 first: five on 2026-09-02 (win rate, median
money, margin, hands@20, Bradley-Terry) and two on 2026-09-04 (`newplan-v1`
95.31% vs 92.71%, `toprr-v1` 41.87% vs 38.94%). `toprr-v1` closed the "make
the field stronger" remedy, because its saturation gate PASSED (97.36%-15.14%)
and it still inverted.

Balduzzi et al. 2018 (NeurIPS, "Re-evaluating Evaluation") names the defect
that all seven share: a round-robin AVERAGE is not invariant to the field's
composition. Adding a clone of an agent adds a column that every other agent
scores the same against, so the average silently reweights toward whatever
the field happens to contain many copies of. Our field is exactly that case:
the mined plans are near-duplicates of each other -- 14 candidates, 7 at
>=99.77% agreement on farm actions and 3 at exactly 100.00% -- and
`{n02, n04, n06, n09}` are one meta plan's variants. So "average win rate
against this field" is partly a measure of how many n04-like agents are in it.

Nash averaging is invariant to that: a clone gets mass split with its twin
and the ranking does not move. alpha-Rank (Omidshafiei et al. 2019) is the
evolutionary answer to the same problem and handles the non-transitivity
Czarnecki et al. 2020 predicts near the top of a spinning top. IQM (Agarwal
et al. 2021) is not a ranking at all -- it is the honest error bar to put on
whatever number we do report, at a +-145 noise floor.

THIS TOOL IS NOT ITSELF EVIDENCE. It has to pass the same pre-registered
gates the seven failures were judged by, printed at the end:

  (1) known answer   k01 > k06                     -- five+two rulers failed
  (2) saturation     nobody at 100.00% / 0.00%
  (3) bottom control n11/n12 stay in the bottom half
  (4) reported       Spearman against the external ladder-cohort scores

Reading discipline: `docs/RUNS.md` says team-median ladder score is an UPPER
ENVELOPE, not the plan's strength, and money is not score (rho=+0.73). This
tool ranks agents on our own episodes; the external column is a check on the
ranking, not a target to fit.
"""

import argparse
import json
import math
import os
import sqlite3
import sys

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- data ------

def load_pairs(db, label=None, run_id=None, min_games=1):
    """(names, W, N, per_seed) from one run.

    W[i, j] = win rate of i against j over every episode the two played,
    counting BOTH seats (a win is money_i > money_j; a tie is 0.5). N[i, j]
    is the episode count. per_seed maps (i, j, seed) -> list of margins, for
    the seed-cluster bootstrap.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    if run_id is None:
        rows = list(con.execute("SELECT id FROM runs WHERE label=?", (label,)))
        if not rows:
            raise SystemExit(f"no run labelled {label!r} in {db}")
        if len(rows) > 1:
            raise SystemExit(f"{label!r} matches run ids {[r[0] for r in rows]}"
                             f"; pass --run-id")
        run_id = rows[0][0]
    q = """SELECT seed, left_agent, right_agent, left_money, right_money,
                  left_status, right_status
           FROM episodes WHERE run_id=?"""
    names, idx = [], {}

    def ix(n):
        if n not in idx:
            idx[n] = len(names)
            names.append(n)
        return idx[n]

    raw = []
    dropped = 0
    for seed, la, ra, lm, rm, ls, rs in con.execute(q, (run_id,)):
        # A forfeit is not a game result -- docs/RUNS.md records money 0 as
        # the forfeit signature in the mined records, and the same applies
        # here: an ERROR/TIMEOUT seat says the harness failed, not that the
        # opponent outplayed it.
        if (ls and ls != "DONE") or (rs and rs != "DONE"):
            dropped += 1
            continue
        raw.append((seed, ix(la), ix(ra), float(lm), float(rm)))
    con.close()

    n = len(names)
    wins = np.zeros((n, n)); games = np.zeros((n, n))
    per_seed = {}
    seats = np.zeros((n, n, 2))
    for seed, i, j, mi, mj in raw:
        s = 1.0 if mi > mj else (0.5 if mi == mj else 0.0)
        wins[i, j] += s; wins[j, i] += 1.0 - s
        games[i, j] += 1; games[j, i] += 1
        seats[i, j, 0] += 1; seats[j, i, 1] += 1
        per_seed.setdefault((i, j, seed), []).append(mi - mj)
        per_seed.setdefault((j, i, seed), []).append(mj - mi)

    with np.errstate(invalid="ignore", divide="ignore"):
        W = np.where(games >= min_games, wins / np.maximum(games, 1), np.nan)
    np.fill_diagonal(W, 0.5)
    np.fill_diagonal(games, 0)
    return names, W, games, seats, per_seed, run_id, dropped


# ------------------------------------------------------- Nash averaging -----

def nash_average(W, iters=200_000, eta=None, seed=0):
    """Approximate maxent Nash of the symmetric zero-sum game A = 2W - 1.

    A is antisymmetric (A = -A.T) because W[i,j] + W[j,i] == 1 by
    construction, so the game is symmetric zero-sum and its Nash value is 0.
    Averaged multiplicative weights (Hedge) in self-play converges to a Nash
    of a zero-sum game in the time average; the duality gap max_i (A p)_i is
    returned so the caller can see whether it actually did. This is an
    APPROXIMATE maxent Nash: Hedge spreads mass over the support but does not
    solve the entropy program, and no claim beyond the reported gap is made.

    Returns (p, rating, gap) with rating = A @ p -- the payoff advantage of
    each agent against the equilibrium mixture, which is Balduzzi's Nash
    average.
    """
    A = 2.0 * np.nan_to_num(W, nan=0.5) - 1.0
    A = 0.5 * (A - A.T)                       # enforce exact antisymmetry
    n = A.shape[0]
    if eta is None:
        eta = math.sqrt(2.0 * math.log(n) / iters) * 4.0
    logw = np.zeros(n)
    acc = np.zeros(n)
    for _ in range(iters):
        w = np.exp(logw - logw.max())
        p = w / w.sum()
        acc += p
        logw += eta * (A @ p)
    p = acc / acc.sum()
    rating = A @ p
    return p, rating, float(rating.max())


def bipartition(G):
    """2-colour the "played" graph; returns (rows, cols) or None if not bipartite.

    A `panel` run is complete bipartite: candidates play the opponent roster
    and never each other. A connected bipartite graph has exactly one
    bipartition, so this recovers the panel's own two sides with no
    heuristics. A `roundrobin` is not bipartite and this returns None, which
    is the signal to use the symmetric (AvA) formulation instead.
    """
    n = G.shape[0]
    colour = [None] * n
    for s0 in range(n):
        if colour[s0] is not None:
            continue
        colour[s0] = 0
        stack = [s0]
        while stack:
            u = stack.pop()
            for v in np.nonzero(G[u])[0]:
                if colour[v] is None:
                    colour[v] = 1 - colour[u]
                    stack.append(int(v))
                elif colour[v] == colour[u]:
                    return None
    return ([i for i in range(n) if colour[i] == 0],
            [i for i in range(n) if colour[i] == 1])


def nash_average_avt(S, iters=200_000, eta=None):
    """Maxent-ish Nash of the two-population game (Balduzzi's AvT form).

    S[i, j] is the win rate of agent i against opponent j, so A = S - 0.5 is
    the advantage and the game is zero-sum between "pick an agent" and "pick
    an opponent". This is the formulation a PANEL needs, and it is the one
    that matters for our disease: the opponent roster is GENERATED (agents/spar,
    agents/wrapped are variants of one another), so an average over it weights
    agents by how many near-copies of each opponent the roster happens to
    hold. The equilibrium opponent mixture q* prices redundant opponents down
    to a shared mass and hard ones up.

    Returns (p, q, rating, gap) with rating = A @ q* -- each agent's advantage
    against the equilibrium opponent mixture.
    """
    A = np.nan_to_num(S, nan=0.5) - 0.5
    m, k = A.shape
    if eta is None:
        eta = math.sqrt(2.0 * math.log(max(m, k)) / iters) * 4.0
    lp, lq = np.zeros(m), np.zeros(k)
    ap, aq = np.zeros(m), np.zeros(k)
    for _ in range(iters):
        wp = np.exp(lp - lp.max()); p = wp / wp.sum()
        wq = np.exp(lq - lq.max()); q = wq / wq.sum()
        ap += p; aq += q
        lp += eta * (A @ q)
        lq -= eta * (A.T @ p)
    p, q = ap / ap.sum(), aq / aq.sum()
    rating = A @ q
    gap = float(rating.max() - (p @ A).min())
    return p, q, rating, gap


# ------------------------------------------------------------ alpha-Rank ----

def alpha_rank(W, alpha=None, m=50):
    """Single-population alpha-Rank stationary distribution.

    Payoff to i against j is W[i, j]. The chain is the Moran process of
    Omidshafiei et al. 2019: from incumbent i a single mutant j appears with
    probability 1/(n-1) and fixates with probability

        rho = (1 - e^{-a*d}) / (1 - e^{-a*m*d}),   d = W[j,i] - W[i,j]

    (rho = 1/m when d == 0). alpha is the selection strength; the default
    scales it to the observed payoff range so the chain is neither frozen nor
    uniform, and --alpha overrides it. Returns (pi, alpha).
    """
    M = np.nan_to_num(W, nan=0.5)
    n = M.shape[0]
    if alpha is None:
        d = np.abs(M - M.T)
        spread = float(np.nanmax(d)) or 1.0
        alpha = 10.0 / spread
    eta = 1.0 / (n - 1)
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = M[j, i] - M[i, j]
            if abs(alpha * m * d) < 1e-12:
                rho = 1.0 / m
            else:
                # exp-safe: factor out the larger exponent
                num = -np.expm1(-alpha * d)
                den = -np.expm1(-alpha * m * d)
                rho = num / den if den != 0 else 1.0 / m
            C[i, j] = eta * max(0.0, min(1.0, rho))
        C[i, i] = 1.0 - C[i].sum()
    # stationary distribution by power iteration on the row-stochastic chain
    pi = np.full(n, 1.0 / n)
    for _ in range(200_000):
        nxt = pi @ C
        if np.abs(nxt - pi).sum() < 1e-14:
            pi = nxt
            break
        pi = nxt
    return pi / pi.sum(), alpha


# ------------------------------------------------------------------ IQM -----

def iqm(x):
    x = np.sort(np.asarray(x, dtype=float))
    if x.size == 0:
        return float("nan")
    lo, hi = int(math.floor(0.25 * x.size)), int(math.ceil(0.75 * x.size))
    core = x[lo:hi] if hi > lo else x
    return float(core.mean())


def iqm_ci(per_seed, i, n_agents, boots=2000, rng=None):
    """IQM of agent i's per-episode margin, with a SEED-CLUSTER bootstrap.

    Resampling episodes independently would understate the interval: the
    seed is shared by every pair that played it, and this environment's
    seed-to-seed spread exceeds most tuning effects (docs/VALIDATING.md). So
    the resampling unit is the seed, not the episode.
    """
    rng = rng or np.random.default_rng(0)
    by_seed = {}
    for (a, b, s), v in per_seed.items():
        if a == i:
            by_seed.setdefault(s, []).extend(v)
    seeds = list(by_seed)
    if not seeds:
        return float("nan"), float("nan"), float("nan"), 0
    flat = [v for s in seeds for v in by_seed[s]]
    point = iqm(flat)
    draws = np.empty(boots)
    for b in range(boots):
        pick = rng.choice(len(seeds), size=len(seeds), replace=True)
        vals = [v for k in pick for v in by_seed[seeds[k]]]
        draws[b] = iqm(vals)
    return point, float(np.percentile(draws, 2.5)), \
        float(np.percentile(draws, 97.5)), len(flat)


# ----------------------------------------------------------------- gates ----

def spearman(a, b):
    """rho over the pairs where both are present; returns (rho, n)."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 3:
        return float("nan"), len(pairs)
    def rank(v):
        order = sorted(range(len(v)), key=lambda k: v[k])
        r = [0.0] * len(v)
        k = 0
        while k < len(order):
            j = k
            while j + 1 < len(order) and v[order[j + 1]] == v[order[k]]:
                j += 1
            avg = (k + j) / 2.0 + 1.0
            for t in range(k, j + 1):
                r[order[t]] = avg
            k = j + 1
        return r
    ra, rb = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    n = len(pairs)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra)
                    * sum((y - mb) ** 2 for y in rb))
    return (num / den if den else float("nan")), n


def short(name):
    """Readable label. `submissions/<date>-<agent>/main.py` MUST NOT collapse
    to "main": docs/RUNS.md records that exact mistake merging fourteen
    candidates into one row on 2026-09-04, so main.py takes its directory."""
    b = os.path.basename(name)
    if b == "main.py":
        return os.path.basename(os.path.dirname(name)) or name
    return b[:-3] if b.endswith(".py") else b


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=os.path.join(_REPO, "data", "arena.sqlite"))
    ap.add_argument("--label", default="toprr-v1")
    ap.add_argument("--run-id", type=int)
    ap.add_argument("--alpha", type=float, help="alpha-Rank selection strength")
    ap.add_argument("--pop", type=int, default=50, help="alpha-Rank population m")
    ap.add_argument("--hedge-iters", type=int, default=200_000)
    ap.add_argument("--boots", type=int, default=2000)
    ap.add_argument("--external", default="",
                    help="json {agent-or-plan: ladder score} for the reported "
                         "Spearman; keys are matched on the short name")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    names, W, G, seats, per_seed, run_id, dropped = load_pairs(
        args.db, args.label, args.run_id)
    n = len(names)
    sn = [short(x) for x in names]
    print(f"{args.label} (run {run_id}): {n} agents, "
          f"{int(G.sum() // 2):,} episodes"
          + (f", {dropped} forfeits dropped" if dropped else ""))

    # seat balance -- an unbalanced pair is a confound this repo has been
    # burnt by before ("Compare on balanced subsets", CLAUDE.md)
    off = [(sn[i], sn[j], int(seats[i, j, 0]), int(seats[i, j, 1]))
           for i in range(n) for j in range(i + 1, n)
           if G[i, j] and seats[i, j, 0] != seats[i, j, 1]]
    print(f"seat balance: {'OK' if not off else f'{len(off)} unbalanced pairs'}")
    for r in off[:5]:
        print(f"   {r[0]} vs {r[1]}: {r[2]} / {r[3]}")
    miss = [(sn[i], sn[j]) for i in range(n) for j in range(i + 1, n)
            if not G[i, j]]
    if miss:
        print(f"missing pairs: {len(miss)} (e.g. {miss[:3]}) -- W is filled "
              f"with 0.5 there, which biases both rankings toward the mean")

    bip = bipartition(G > 0)
    avg = np.nanmean(np.where(np.eye(n, dtype=bool), np.nan, W), axis=1)
    if bip is None:
        mode = "AvA (round robin: symmetric zero-sum)"
        p, nash, gap = nash_average(W, iters=args.hedge_iters)
        pi, alpha = alpha_rank(W, alpha=args.alpha, m=args.pop)
        oppmass = None
    else:
        # A panel is complete bipartite, so the symmetric formulation would be
        # reading a matrix that is 0.5 everywhere inside each side. Balduzzi's
        # AvT form is the one that applies, and it is the one that matters
        # here: the opponent roster is GENERATED, so its near-duplicates are
        # exactly the redundancy Nash averaging is invariant to.
        rows, cols = bip
        if any(sn[i] in ("k01", "k06") for i in cols):
            rows, cols = cols, rows          # rank the side the gates name
        S = W[np.ix_(rows, cols)]
        mode = (f"AvT (panel: {len(rows)} ranked x {len(cols)} opponents; "
                f"same-side pairs never played, so AvA is undefined here)")
        pr, q, rt, gap = nash_average_avt(S, iters=args.hedge_iters)
        p = np.zeros(n); nash = np.full(n, np.nan); pi = np.full(n, np.nan)
        for k_, i in enumerate(rows):
            p[i] = pr[k_]; nash[i] = rt[k_]
        alpha = float("nan")
        oppmass = sorted(((sn[cols[j]], float(q[j])) for j in range(len(cols))),
                         key=lambda t: -t[1])
        avg = np.where(np.isnan(nash), np.nan,
                       np.array([np.nanmean(W[i, cols]) if not np.isnan(nash[i])
                                 else np.nan for i in range(n)]))
    print(f"mode: {mode}")

    ext = {}
    if args.external:
        ext = {short(k): v for k, v in json.load(open(args.external)).items()}

    rng = np.random.default_rng(7)
    rows = []
    for i in range(n):
        if np.isnan(nash[i]):
            continue
        pt, lo, hi, k = iqm_ci(per_seed, i, n, boots=args.boots, rng=rng)
        rows.append(dict(agent=sn[i], nash=float(nash[i]), mass=float(p[i]),
                         arank=float(pi[i]), avg_win=float(avg[i]),
                         iqm=pt, iqm_lo=lo, iqm_hi=hi, games=k,
                         external=ext.get(sn[i])))
    rows.sort(key=lambda r: -r["nash"])

    print(f"\nNash averaging duality gap {gap:+.5f} "
          f"(near 0 = the averaged Hedge iterate is at equilibrium)")
    if not math.isnan(alpha):
        print(f"alpha-Rank: alpha={alpha:.2f}, m={args.pop}")
    else:
        print("alpha-Rank: n/a on a panel (it needs agent-vs-agent play)")
    if oppmass:
        keep = [t for t in oppmass if t[1] > 1e-4]
        print(f"equilibrium opponent mixture: {len(keep)}/{len(oppmass)} "
              f"opponents carry mass -- " +
              ", ".join(f"{a} {100*w:.1f}%" for a, w in keep[:8]))
    print()
    hdr = (f"{'agent':>10} {'nash':>8} {'mass':>7} {'a-rank':>8} "
           f"{'avg win':>8} {'IQM margin':>12} {'95% CI':>21} {'ladder':>8}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        e = f"{r['external']:8.1f}" if r["external"] is not None else " " * 8
        print(f"{r['agent']:>10} {r['nash']:+8.4f} {r['mass']:7.3f} "
              f"{r['arank']:8.4f} {100*r['avg_win']:7.2f}% "
              f"{r['iqm']:12,.0f} [{r['iqm_lo']:8,.0f},{r['iqm_hi']:8,.0f}] {e}")

    # ---- pre-registered gates -------------------------------------------
    print("\n=== 预登记门（与七次失败同一套判据）===")
    pos = {r["agent"]: k for k, r in enumerate(rows)}
    def verdict(ok):
        return "✅ 通过" if ok else "❌ 判负"

    if "k01" in pos and "k06" in pos:
        r1, r6 = rows[pos["k01"]], rows[pos["k06"]]
        for nm, key in (("Nash 平均", "nash"), ("alpha-Rank", "arank")):
            ok = r1[key] > r6[key]
            print(f"(1) 已知答案 k01 > k06 —— {nm}: {verdict(ok)}  "
                  f"k01 {r1[key]:+.4f} vs k06 {r6[key]:+.4f}")
        ok = r1["iqm"] > r6["iqm"]
        print(f"(1') IQM margin k01 > k06: {verdict(ok)}  "
              f"{r1['iqm']:,.0f} vs {r6['iqm']:,.0f}"
              + ("  (CI 重叠，不构成分辨)" if not (
                  r1["iqm_lo"] > r6["iqm_hi"] or r6["iqm_lo"] > r1["iqm_hi"])
                 else "  (CI 不重叠)"))
    else:
        print("(1) 已知答案不可判：k01/k06 不在这个 run 里")

    sat = [r["agent"] for r in rows
           if r["avg_win"] >= 0.9999 or r["avg_win"] <= 0.0001]
    print(f"(2) 饱和门（无人 100.00%/0.00%）: {verdict(not sat)}"
          + (f"  饱和: {sat}" if sat else ""))

    bot = [r["agent"] for r in rows[len(rows) // 2:]]
    ctrl = [a for a in ("n11", "n12") if a in pos]
    ok = all(a in bot for a in ctrl) if ctrl else None
    print(f"(3) 底端对照 n11/n12 留在下半区: "
          + (verdict(ok) if ctrl else "不可判（不在场内）")
          + (f"  位次 {[pos[a] + 1 for a in ctrl]}/{len(rows)}" if ctrl else ""))

    if ext:
        for nm, key in (("Nash", "nash"), ("alpha-Rank", "arank"),
                        ("avg win", "avg_win"), ("IQM", "iqm")):
            vals = [None if (r[key] is None or (isinstance(r[key], float)
                                                and math.isnan(r[key])))
                    else r[key] for r in rows]
            if all(v is None for v in vals):
                print(f"(4) Spearman({nm}, 队伍中位分) = 不可算（该列全为 n/a）")
                continue
            rho, k = spearman(vals, [r["external"] for r in rows])
            crit = "" if k < 3 else f"  (n={k}; p<0.05 需约 {0.6 if k <= 9 else 0.5:.2f})"
            print(f"(4) Spearman({nm}, 队伍中位分) = {rho:+.3f}{crit}")
    else:
        print("(4) Spearman 未算：--external 未给")

    if args.json:
        json.dump(dict(label=args.label, run_id=run_id, gap=gap, alpha=alpha,
                       rows=rows), open(args.json, "w"), indent=1)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
