#!/usr/bin/env python
"""Measure market *behaviour* in mined recordings, and test it against real ladder wins.

    python tools/tracefeat.py --min-plays 20

Every line in `data/tracelib/index.json` is a 720-turn action log played by a
real competitor, and each turn's `market` field is an **ordered queue**. The
engine resolves market orders index by index across both players, so slot 0 is
priced before the opponent's slot 0, slot 1 before their slot 1, and so on.
Slot order is therefore a strategic choice that survives into the recording --
unlike almost everything else about a team's agent, which does not.

WHY THIS IS A DIFFERENT KIND OF EVIDENCE

`tools/tournament.py` measures how a recording does on boards it never saw, and
`docs/ROADMAP.md` §10.5 shows that number has no relation to real strength
(spearman -0.05, n=100). This script never simulates anything. It reads what the
players actually did, and scores it against `wins/plays` -- their real outcomes
in real ladder episodes. The label is not something this repo computed about
itself.

WHAT IT CANNOT SETTLE

`wins/plays` is the record of the *line*, pooled over every team that played it
and every wrapper they put around it. A line shared by 38 teams carries 38
different market layers, so a behavioural feature measured on the recording is
only loosely attached to the outcome. This biases every correlation here
*towards zero*, so a correlation that survives is real and a null one is weak
evidence of absence. Lines played by a single team are the clean subset and are
reported separately for that reason.

Both players' scores are recorded, and they are nearly equal within an episode
(pearson +0.950 -- most of the money is a property of the board), so `wins` is
the useful outcome and `best_score` is not. `docs/VALIDATING.md` opens with why.
"""

import argparse
import base64
import collections
import gzip
import json
import math

PREMIUM = ("MELON", "WOOL", "MILK", "STRAWBERRY")
SELLABLE = ("STRAWBERRY", "MELON", "MILK", "WOOL", "EGG",
            "TOMATO", "CARROT", "WHEAT", "FERTILIZER")


def decode(blob):
    return json.loads(gzip.decompress(base64.b64decode(blob)))


def features(turns):
    """Behavioural features of one recording's market queue."""
    n_turns = len(turns)
    slot0_sell = slot0_prem = both = sell_first = 0
    sell_turns = n_orders = n_sell_orders = 0
    sell_idx_sum = sell_idx_n = 0
    early_sells = late_sells = 0
    units = collections.Counter()
    hires = buys = 0
    for step, t in enumerate(turns):
        market = t.get("market") or []
        n_orders += len(market)
        sells = [(i, o) for i, o in enumerate(market)
                 if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL"]
        purchases = [i for i, o in enumerate(market)
                     if isinstance(o, list) and o and o[0].startswith("BUY")]
        hires += sum(1 for o in market if isinstance(o, list) and o and o[0] == "HIRE")
        buys += len(purchases)
        if market and isinstance(market[0], list) and market[0]:
            if market[0][0] == "SELL":
                slot0_sell += 1
                if len(market[0]) >= 2 and market[0][1] in PREMIUM:
                    slot0_prem += 1
        if sells:
            sell_turns += 1
            n_sell_orders += len(sells)
            for i, o in sells:
                sell_idx_sum += i
                sell_idx_n += 1
                try:
                    q = int(o[2] or 0)
                except (TypeError, ValueError):
                    q = 0
                units[o[1]] += q
                if step < n_turns // 2:
                    early_sells += q
                else:
                    late_sells += q
        if sells and purchases:
            both += 1
            if min(i for i, _ in sells) < min(purchases):
                sell_first += 1
    total_units = sum(units.values()) or 1
    return {
        # Slot 0 is priced before the opponent's slot 0. This is the front-run.
        "slot0_sell": slot0_sell / max(1, n_turns),
        "slot0_prem": slot0_prem / max(1, n_turns),
        # Sells fund the buys behind them in the same queue; putting them first
        # was worth +20 points of win rate in the wave-1 perturbation run.
        "sell_first": sell_first / max(1, both),
        "mean_sell_idx": sell_idx_sum / max(1, sell_idx_n),
        "orders_per_turn": n_orders / max(1, n_turns),
        "sell_turn_frac": sell_turns / max(1, n_turns),
        "orders_per_sell_turn": n_sell_orders / max(1, sell_turns),
        "early_unit_share": early_sells / max(1, early_sells + late_sells),
        "prem_unit_share": sum(units[p] for p in PREMIUM) / total_units,
        "fert_unit_share": units["FERTILIZER"] / total_units,
        "wheat_unit_share": units["WHEAT"] / total_units,
        "units_per_turn": total_units / max(1, n_turns),
        "hires": hires,
        "buys_per_turn": buys / max(1, n_turns),
    }


def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def spearman(xs, ys):
    return pearson(rank(xs), rank(ys))


def report(rows, label):
    if len(rows) < 8:
        print(f"\n{label}: 只有 {len(rows)} 条，不够，跳过")
        return
    keys = sorted(rows[0]["f"])
    ys = [r["wr"] for r in rows]
    out = []
    for k in keys:
        xs = [r["f"][k] for r in rows]
        out.append((spearman(xs, ys), pearson(xs, ys), k,
                    min(xs), max(xs)))
    out.sort(key=lambda t: -abs(t[0]))
    print(f"\n{label}  (n={len(rows)} 条线, "
          f"天梯胜率 {100*min(ys):.0f}%–{100*max(ys):.0f}%)")
    print(f"  {'行为特征':<22}{'spearman':>10}{'pearson':>10}   取值范围")
    for s, p, k, lo, hi in out:
        star = "  <<<" if abs(s) >= 0.30 else ""
        print(f"  {k:<22}{s:>+10.3f}{p:>+10.3f}   {lo:.3f} – {hi:.3f}{star}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="data/tracelib/index.json")
    ap.add_argument("--min-plays", type=int, default=20,
                    help="a line's ladder win rate is only stable with enough "
                         "real episodes behind it")
    a = ap.parse_args()

    with open(a.index) as f:
        lines = json.load(f)["lines"]

    rows, solo = [], []
    for key, v in lines.items():
        plays = int(v.get("plays") or 0)
        wins = v.get("wins")
        if wins is None or plays < a.min_plays:
            continue
        turns = decode(v["turns"])
        row = {"key": key, "wr": float(wins) / plays, "plays": plays,
               "teams": v.get("teams") or [], "f": features(turns)}
        rows.append(row)
        if len(row["teams"]) == 1:
            solo.append(row)

    if not rows:
        raise SystemExit(f"no line has wins recorded with plays >= {a.min_plays}")

    print(f"读入 {len(lines)} 条线，其中 {len(rows)} 条有 >= {a.min_plays} 局真实天梯记录")
    tot_plays = sum(r["plays"] for r in rows)
    print(f"这些线合计 {tot_plays:,} 局真实对局")
    report(rows, "全部（每条线的天梯胜率 vs 该录音的市场行为）")
    report(solo, "只看单队伍独有的线（没有跨队包装层混淆）")

    print("\n最强与最弱的线，行为对照：")
    rows.sort(key=lambda r: -r["wr"])
    show = ("slot0_sell", "sell_first", "mean_sell_idx", "orders_per_turn",
            "prem_unit_share", "fert_unit_share", "units_per_turn")
    print(f"  {'线':<14}{'天梯胜率':>9}{'局数':>8}" + "".join(f"{k[:11]:>12}" for k in show))
    for r in rows[:5] + [None] + rows[-5:]:
        if r is None:
            print("  " + "-" * 100)
            continue
        print(f"  {r['key'][:12]:<14}{100*r['wr']:>8.1f}%{r['plays']:>8,}"
              + "".join(f"{r['f'][k]:>12.3f}" for k in show))


if __name__ == "__main__":
    main()
