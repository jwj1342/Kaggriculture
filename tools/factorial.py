#!/usr/bin/env python
"""Read a perturbation run and separate what an arm did to us from what it did to them.

    python tools/factorial.py --shards data/shards/mkt-wave1 --manifest agents/mkt/manifest.json

Every arm here is the same agent with one market constant changed, played
against a byte-identical copy of itself. That makes the causal question sharp --
the field plan does not vary, so nothing but market behaviour can move the
result -- but a raw win rate still cannot say *why* an arm moved, and in this
environment the two candidate reasons pull in opposite directions.

THE CONFOUND THIS EXISTS TO REMOVE

Market slot position does two unrelated things at once. It decides whether our
sell is priced before the opponent's matching order (the front-run), and it
decides whether the cash from that sell has landed before the buy orders behind
it in the same queue (our own funding chain). The donor's file warns about the
second in its own docstring, and moving one sell to the last slot cost $19,000 in
a single measured episode with the market barely moving: wool inventory differed
by 47 units between the two arms, so almost none of it was competition.

So each arm is played in two conditions:

  mirror   vs an identical copy of itself -- the real question, and the only
           condition where interference is possible at all
  starter  vs the built-in baseline, which barely trades -- close to playing
           alone, so a change here is our own farm getting better or worse

and reported as four numbers rather than one:

  win%     mirror win rate, seat-balanced. The competition scores wins only.
  d_ours   our money in the mirror, minus the control's
  d_opp    THEIR money in the mirror, minus the control's. This is the attack
           measure. An arm that does not move d_opp did not interfere with the
           opponent, whatever it did to the win rate.
  d_solo   our money against starter, minus the control's. The part of d_ours
           that owes nothing to the opponent.

  margin   mean of (ours - theirs) *within each episode* in the mirror. The two
           players in one episode earn almost the same amount -- pearson +0.950,
           measured over the trace library -- because most of the money is a
           property of the board, not the player. Subtracting inside the episode
           removes that shared term, so the margin resolves an effect several
           times smaller than either mean alone can.

`d_ours - d_solo` is what the arm gained *because there was an opponent*. An arm
whose whole effect is in d_solo rearranged its own cash flow and never touched
the market; an arm with a negative d_opp is interference, and is worth having
only when d_ours - d_opp beats the control's zero.

WHAT THE SOLO CONDITION IS NOT

`starter` barely trades, so prices in that condition stay near base and our sales
face a market that is far richer than a mirror's. d_solo therefore is not a clean
"own farm" measure -- it is our farm in easy market conditions. It separates
own-cash-flow effects from opponent effects well enough to rank arms, and badly
enough that a small d_solo should not be quoted as a quantity on its own.

CONTROLS ARE CHECKED FIRST AND THE RUN IS REFUSED IF THEY FAIL

`mctl` is a byte-identical copy of the base and `mnul` carries the interference
overlay with every dial empty. Both must sit at 50% against the base and agree
with each other. If they do not, the harness is biased -- seat assignment, seed
handling or the overlay itself -- and no arm in the run can be read.
"""

import argparse
import glob
import json
import math
import os
from collections import defaultdict


def wilson(w, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(shard_dir, base_stem, opponents):
    """-> {arm: {opp: {"w": wins, "n": games, "mine": [...], "theirs": [...]}}}"""
    rec = defaultdict(lambda: defaultdict(
        lambda: {"w": 0.0, "n": 0, "mine": [], "theirs": []}))
    files = sorted(glob.glob(os.path.join(shard_dir, "shard-*.jsonl")))
    if not files:
        raise SystemExit(f"{shard_dir}: no complete shards "
                         "(a shard file is renamed into place only when finished)")
    for path in files:
        with open(path) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if any(s != "DONE" for s in r["status"]):
                    continue
                left = os.path.basename(r["left"])[:-3] if r["left"].endswith(".py") else r["left"]
                right = os.path.basename(r["right"])[:-3] if r["right"].endswith(".py") else r["right"]
                ml, mr = r["money"]
                for me, opp, mine, theirs in ((left, right, ml, mr), (right, left, mr, ml)):
                    if opp not in opponents or me in opponents:
                        continue
                    cell = rec[me][opp]
                    cell["w"] += 1.0 if mine > theirs else 0.0 if mine < theirs else 0.5
                    cell["n"] += 1
                    cell["mine"].append(mine)
                    cell["theirs"].append(theirs)
                    cell.setdefault("margin", []).append(mine - theirs)
    return rec


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def sem(xs):
    """Standard error of the mean; the margin is paired, so this is a paired SE."""
    n = len(xs)
    if n < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)


def cross_report(rec, man, mirror, field):
    """Main effects and 2-way interactions, in both the mirror and the field.

    Reading only the mirror is the trap this exists to avoid. The donor's
    front-run fires on a mirror detector, so self-play is its best case by
    construction; a dial can own the mirror and be worth nothing against a real
    opponent. Every number is therefore printed twice, and the gap between the
    two columns is the finding, not either column alone.
    """
    cells = {}
    for stem, meta in man.items():
        levels = meta.get("levels") or {}
        if not levels or "__base__" in levels.values():
            continue
        c = rec.get(stem)
        if not c:
            continue
        m = c.get(mirror)
        fw = sum(c[o]["w"] for o in field if o in c)
        fn = sum(c[o]["n"] for o in field if o in c)
        if not m or not fn:
            continue
        cells[stem] = {"levels": levels, "arm": meta["arm"],
                       "mw": m["w"], "mn": m["n"], "fw": fw, "fn": fn}
    if not cells:
        print("\n(没有可用的交叉单元)")
        return

    factors = sorted({k for c in cells.values() for k in c["levels"]})

    def agg(sel):
        mw = sum(c["mw"] for c in sel); mn = sum(c["mn"] for c in sel)
        fw = sum(c["fw"] for c in sel); fn = sum(c["fn"] for c in sel)
        return (mw / mn if mn else 0, mn, fw / fn if fn else 0, fn)

    print(f"\n{'='*74}\n主效应 —— 每个因子的边际，镜像 vs 真实录音场\n{'='*74}")
    for f in factors:
        levels = sorted({c["levels"][f] for c in cells.values()})
        print(f"\n  因子 {f}")
        print(f"    {'level':<10}{'镜像胜率':>10}{'(n)':>9}{'录音场胜率':>12}{'(n)':>9}   差")
        for lv in levels:
            p_m, n_m, p_f, n_f = agg([c for c in cells.values() if c["levels"][f] == lv])
            lo, hi = wilson(p_f * n_f, n_f)
            flag = "  <<<" if lo > 0.5 else ("  xxx" if hi < 0.5 else "")
            print(f"    {lv:<10}{100*p_m:>9.1f}%{n_m:>9,}{100*p_f:>11.1f}%{n_f:>9,}"
                  f"{100*(p_m-p_f):>+7.1f}{flag}")

    for i, fa in enumerate(factors):
        for fb in factors[i + 1:]:
            la = sorted({c["levels"][fa] for c in cells.values()})
            lb = sorted({c["levels"][fb] for c in cells.values()})
            if len(la) * len(lb) > 40:
                continue
            for cond, lab in (("m", "镜像"), ("f", "真实录音场")):
                print(f"\n  交互 {fa} x {fb} —— {lab}胜率")
                print("    " + " " * 10 + "".join(f"{x:>10}" for x in lb))
                for a_lv in la:
                    row = []
                    for b_lv in lb:
                        sel = [c for c in cells.values()
                               if c["levels"][fa] == a_lv and c["levels"][fb] == b_lv]
                        p_m, n_m, p_f, n_f = agg(sel)
                        row.append(p_m if cond == "m" else p_f)
                    print(f"    {a_lv:<10}" + "".join(f"{100*v:>9.1f}%" for v in row))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", default="data/shards/mkt-wave1")
    ap.add_argument("--manifest", default="agents/mkt/manifest.json")
    ap.add_argument("--mirror", default="k01", help="the identical-opponent condition")
    ap.add_argument("--solo", default="starter", help="the barely-trading condition")
    ap.add_argument("--control", default="mctl")
    ap.add_argument("--field", default="",
                    help="comma-separated non-mirror opponents. Given these, "
                         "main effects and 2-way interactions are printed for "
                         "the mirror and the field side by side.")
    ap.add_argument("--force", action="store_true",
                    help="report even if the controls fail. The numbers are not "
                         "interpretable; this exists to debug the harness.")
    a = ap.parse_args()

    with open(a.manifest) as f:
        man = json.load(f)["arms"]
    field = [x.strip() for x in a.field.split(",") if x.strip()]
    rec = load(a.shards, a.control, {a.mirror, a.solo} | set(field))
    if not rec:
        raise SystemExit("no episodes matched -- check --mirror/--solo names")

    ctl = rec.get(a.control, {})
    if a.mirror not in ctl:
        raise SystemExit(f"control {a.control} never played {a.mirror}")
    c_mine = mean(ctl[a.mirror]["mine"])
    c_opp = mean(ctl[a.mirror]["theirs"])
    c_solo = mean(ctl.get(a.solo, {}).get("mine", []))

    # --- controls -----------------------------------------------------------
    print("控制组检查 —— 这两个必须在 50%，否则下面全部作废")
    ok = True
    for stem in (a.control, a.control[:-3] + "nul"):
        cell = rec.get(stem, {}).get(a.mirror)
        if not cell:
            print(f"  {stem}: 缺失"); ok = False; continue
        p = cell["w"] / cell["n"]
        lo, hi = wilson(cell["w"], cell["n"])
        good = lo <= 0.5 <= hi
        ok &= good
        print(f"  {stem:<6}{100*p:>7.1f}%  [{100*lo:.1f}, {100*hi:.1f}]  "
              f"n={cell['n']:,}  {'OK' if good else '<<< 偏了'}")
    if not ok and not a.force:
        raise SystemExit("\n控制组没落在 50% —— 先修仪器，不要读实验臂 (--force 可强制)")

    # --- arms ---------------------------------------------------------------
    rows = []
    ctl_stems = {a.control, a.control[:-3] + "nul", "mnul", "nnul"}
    for stem, cell in rec.items():
        m = cell.get(a.mirror)
        if not m or stem in ctl_stems:
            continue
        p = m["w"] / m["n"]
        lo, hi = wilson(m["w"], m["n"])
        rows.append({
            "arm": man.get(stem, {}).get("arm", stem), "stem": stem,
            "p": p, "lo": lo, "hi": hi, "n": m["n"],
            "d_ours": mean(m["mine"]) - c_mine,
            "d_opp": mean(m["theirs"]) - c_opp,
            "d_solo": mean(cell.get(a.solo, {}).get("mine", [])) - c_solo,
            "margin": mean(m["margin"]), "margin_se": sem(m["margin"]),
        })
    rows.sort(key=lambda r: -r["p"])
    c_margin = mean(ctl[a.mirror]["margin"])
    c_margin_se = sem(ctl[a.mirror]["margin"])

    print(f"\n对照基准: 我方 ${c_mine:,.0f} / 对手 ${c_opp:,.0f} (镜像), "
          f"单机 ${c_solo:,.0f} (对 {a.solo})")
    print(f"配对边际 (同局内 我方-对手): 对照 ${c_margin:+,.0f} ± {1.96*c_margin_se:,.0f}"
          "  —— 镜像对局理论上应为 0")
    print(f"\n{'':>3} {'臂':<18}{'胜率':>8}{'95%区间':>16}{'配对边际±95%':>20}"
          f"{'Δ我方':>10}{'Δ对手':>10}{'Δ单机':>10}   判读")
    for i, r in enumerate(rows, 1):
        beats = r["lo"] > 0.5
        loses = r["hi"] < 0.5
        # Order matters. The solo condition is checked first because a big
        # own-farm effect swamps everything and makes the mirror numbers
        # unreadable -- an arm that starves its own farm also stops competing,
        # which shows up as the opponent getting richer and looks like a failed
        # attack when no attack was ever attempted.
        #
        # The thresholds are deliberately low. The effects that decide mirror
        # matches here are worth a few hundred dollars and tens of points of win
        # rate, because two identical agents finish near a tie and a small
        # consistent edge flips a large share of them. A $1,000 threshold, tried
        # first, classified the run's two best arms as "did nothing".
        if abs(r["d_solo"]) > 2000:
            read = "自伤为主，与对手无关"
        elif r["d_opp"] > 200:
            read = "把钱送给了对手"
        elif r["d_opp"] < -100:
            read = "干扰对手且自己得利" if r["d_ours"] > 0 else "伤敌但自伤"
        else:
            read = "无可测效应" if abs(r["p"] - 0.5) < 0.03 else "微额，胜率驱动"
        mark = "  <<<" if beats else ("  xxx" if loses else "")
        mg = f"{r['margin']:>+11,.0f} ±{1.96*r['margin_se']:>6,.0f}"
        print(f"{i:>3} {r['arm']:<18}{100*r['p']:>7.1f}%  "
              f"[{100*r['lo']:>5.1f},{100*r['hi']:>5.1f}]{mg}"
              f"{r['d_ours']:>+10,.0f}{r['d_opp']:>+10,.0f}{r['d_solo']:>+10,.0f}   "
              f"{read}{mark}")

    print("\nΔ 是相对对照组的均值差。Δ对手 是攻击是否奏效的唯一证据："
          "\n对手没掉钱，就没有干扰到市场，无论胜率怎么动。")

    # --- factor grouping ----------------------------------------------------
    groups = defaultdict(list)
    for r in rows:
        groups[r["arm"].split(".", 1)[0]].append(r)
    print(f"\n按因子分组的主效应（组内最好的一条）")
    for g in sorted(groups):
        best = max(groups[g], key=lambda r: r["p"])
        span = max(r["p"] for r in groups[g]) - min(r["p"] for r in groups[g])
        print(f"  {g}: 最好 {best['arm']:<18}{100*best['p']:>6.1f}%   "
              f"组内跨度 {100*span:>5.1f} 点   ({len(groups[g])} 条)")

    if field:
        cross_report(rec, man, a.mirror, field)


if __name__ == "__main__":
    main()
