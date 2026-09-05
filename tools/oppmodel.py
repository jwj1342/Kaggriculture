#!/usr/bin/env python
"""对手卖出时序**可不可预测** —— 决定搜索有没有东西可吃。

抢跑只能跨回合生效（同回合内双方按同一 pre-commit 库存报价，见 `tools/sellsim.py`），
所以搜索唯一要预测的是：**对手下一回合会不会卖这个产品**。

三个只用**可见状态**的预测器（对手的棚与种子是私有的，`rl/obs.py` 写明；
但对手的棋盘、市场账本、双方的钱都可见）：

  always-no   平凡基线；卖出是稀疏事件，所以它的准确率会很高而召回是 0
  persist     它上一回合卖了 X → 下一回合还卖 X
  shed-est    **从可见的棋盘重建对手的棚**：`yield_units` 下降 = 它收割了；
              再减去从账本反推的净卖出。估计棚 ≥ 阈值就预测它要卖。

报的是每个产品的 precision / recall / F1，以及 base rate。**F1 明显高于 base rate
才说明有东西可吃**；若 persist 或 shed-est 接近 1，搜索退化成一张表，连前瞻都不用。
"""
import argparse
import collections
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _engine():
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    return K


def trace(a, b, seed, steps=720):
    """一局的逐回合可见状态 + 对手（座位 1）的真实卖出（只用于打分）。"""
    os.environ.setdefault("KG_FAST_ENV", "1")
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    env.run([a, b])
    rows = []
    for st in env.steps[1:]:
        o = st[0].observation
        acts = [st[p].action if isinstance(st[p].action, dict) else {} for p in (0, 1)]
        opp_sell = collections.Counter()
        for ord_ in (acts[1].get("market") or []):
            if ord_ and ord_[0] == "SELL" and len(ord_) > 2:
                opp_sell[ord_[1]] += int(ord_[2])
        my_net = collections.Counter()
        for ord_ in (acts[0].get("market") or []):
            if not ord_ or len(ord_) < 3: continue
            if ord_[0] == "SELL": my_net[ord_[1]] += int(ord_[2])
            elif ord_[0] == "BUY_PRODUCT": my_net[ord_[1]] -= int(ord_[2])
        rows.append(dict(step=int(o["step"]), inv=dict(o["market"]["inventory"]),
                         opp_tiles=o["farms"][1].get("tiles"),
                         shops=list((o.get("town") or {}).get("unlocked_shops") or []),
                         opp_sell=opp_sell, my_net=my_net))
    return rows


def opp_yield_units(K, tiles):
    """对手棋盘上每个产品**已经长好、还没被收走**的单位数（可见）。"""
    out = collections.Counter()
    if not tiles:
        return out
    for row in tiles:
        for t in row or []:
            if not isinstance(t, dict):
                continue
            y = int(t.get("yield_units") or 0)
            if y <= 0:
                continue
            if t.get("crop"):
                out[t["crop"]] += y
            elif t.get("animal"):
                a = K.ANIMALS.get(t["animal"])
                if a: out[a["product"]] += y
    return out


def evaluate(rows, K, horizon=1, thr=6):
    """三个预测器，逐产品打分。目标：对手在未来 `horizon` 回合内卖 X。"""
    stats = collections.defaultdict(lambda: collections.Counter())
    est = collections.Counter()          # shed-est 的对手棚估计
    prev_units = None
    for i, r in enumerate(rows[:-horizon]):
        # ---- 更新棚估计：可见的收割增量 - 从账本反推的净卖出 ----
        units = opp_yield_units(K, r["opp_tiles"])
        if prev_units is not None:
            for it in set(prev_units) | set(units):
                drop = prev_units[it] - units[it]
                if drop > 0:
                    est[it] += drop                     # 收割进棚（可见）
        prev_units = units
        if i > 0:
            cons = {}
            if r["step"] % 4 == 0:
                for s in r["shops"]:
                    pr = K.SHOPS.get(s) or []
                    m = 2 if len(pr) == 1 else 1
                    for p in pr: cons[p] = cons.get(p, 0) + m
            if r["step"] % 24 == 0:
                for p in K.TOWN_CENTER_PRODUCTS: cons[p] = cons.get(p, 0) + 1
            d = {it: r["inv"].get(it, 0) - rows[i-1]["inv"].get(it, 0)
                 for it in r["inv"]}
            for it, dv in d.items():
                opp_net = dv - rows[i-1]["my_net"].get(it, 0) + cons.get(it, 0)
                if opp_net > 0:
                    est[it] = max(0, est[it] - opp_net)  # 它卖掉了
        # ---- 真值 ----
        for it in K.PRODUCTS:
            truth = any(rows[i + k + 1]["opp_sell"].get(it, 0) > 0
                        for k in range(horizon))
            preds = {"always-no": False,
                     "persist": r["opp_sell"].get(it, 0) > 0,
                     "shed-est": est[it] >= thr}
            for name, p in preds.items():
                key = (it, name)
                stats[key]["n"] += 1
                stats[key]["pos"] += int(truth)
                if p and truth: stats[key]["tp"] += 1
                elif p and not truth: stats[key]["fp"] += 1
                elif not p and truth: stats[key]["fn"] += 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default="submissions/2026-09-04-sharedmeta-cleo/main.py")
    ap.add_argument("--opps", default="agents/champ/k01.py,agents/newlines/n04.py,"
                                      "agents/ref/closer_cleo.py")
    ap.add_argument("--seeds", default="123,555")
    ap.add_argument("--horizon", type=int, default=1)
    ap.add_argument("--thr", type=int, default=6)
    args = ap.parse_args()
    K = _engine()
    for opp in args.opps.split(","):
        if not os.path.exists(os.path.join(_REPO, opp)):
            print(f"缺 {opp}"); continue
        agg = collections.defaultdict(lambda: collections.Counter())
        for s in args.seeds.split(","):
            for k, v in evaluate(trace(args.me, opp, int(s)), K,
                                 args.horizon, args.thr).items():
                agg[k].update(v)
        print(f"\n=== 对手 {os.path.basename(opp)}  "
              f"(horizon={args.horizon} 回合, shed-est 阈值 {args.thr}) ===")
        print(f"{'product':12}{'base rate':>11}" +
              "".join(f"{n:>26}" for n in ("persist P/R/F1", "shed-est P/R/F1")))
        for it in K.PRODUCTS:
            base = agg[(it, "always-no")]
            if base["pos"] == 0:
                continue
            line = f"{it:12}{100*base['pos']/base['n']:>10.1f}%"
            for name in ("persist", "shed-est"):
                c = agg[(it, name)]
                p = c["tp"] / max(1, c["tp"] + c["fp"])
                r = c["tp"] / max(1, c["tp"] + c["fn"])
                f1 = 2 * p * r / max(1e-9, p + r)
                line += f"{f'{100*p:.0f}/{100*r:.0f}/{100*f1:.0f}':>26}"
            print(line)


if __name__ == "__main__":
    main()
