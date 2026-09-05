#!/usr/bin/env python
"""**+20k 住在哪里**：把配对差额的方差拆到棋盘 / 商店抽取 / 对手三个因子上。

这局游戏的需求侧是**唯一的真随机**：商店有放回地抽、最多八家，所以有些局里
**根本没有商店吃 melon 或 wool** —— 那两个产品的库存永远不回来，而 cleo 的静态层
照旧把它们砸进一个塌掉的价格里，因为它不知道这局没人买。这比"对手在市场上压你"
更像 `56013382` 那 18 场败局里 27k 摆动的来源。

三个因子可以**独立操纵**，尽管商店与杂草共用一条 RNG：
  * 棋盘/天气：换 episode seed，**商店组合强制固定**；
  * 商店抽取：**seed 固定**，强制不同的商店组合（解锁的**时刻与数量不变**，
    只换是哪几家 —— 所以杂草的 RNG 抽取完全不受影响）；
  * 对手：seed 与商店都固定，换对手。

报每个因子内的 sd（配对差额与我方钱各一份）。
"""
import argparse
import collections
import itertools
import os
import random
import statistics as st
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _engine():
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    return K


def run(K, a, b, seed, forced=None, steps=720):
    """一局。`forced` 非空时，每一步把 `unlocked_shops` 覆写成 forced 的前 n 家
    （n = 引擎自己已解锁的数量），**解锁时刻与数量保持引擎原样**。"""
    from kaggle_environments import make
    real = K._town_consume

    def town(env, state, step):
        if forced is not None:
            t = state[0].observation.town
            n = len(t.get("unlocked_shops") or [])
            t["unlocked_shops"] = list(forced[:n])
        return real(env, state, step)

    K._town_consume = town
    try:
        env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
        env.run([a, b])
        o = env.steps[-1][0].observation
        return (int(o["farms"][0]["money"]), int(o["farms"][1]["money"]),
                list(o["town"].get("unlocked_shops") or []))
    finally:
        K._town_consume = real


def sd_report(name, rows, extra=""):
    m = [x[0] - x[1] for x in rows]
    mine = [x[0] for x in rows]
    print(f"{name:34} n={len(rows):3d}  "
          f"margin 中位 {st.median(m):>+9,.0f}  **sd {st.pstdev(m):>9,.0f}**  "
          f"极差 {max(m)-min(m):>9,.0f}   我方钱 sd {st.pstdev(mine):>9,.0f}  {extra}")
    return st.pstdev(m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default="submissions/2026-09-04-sharedmeta-cleo/main.py")
    ap.add_argument("--opp", default="agents/champ/k01.py")
    ap.add_argument("--opps", default="agents/champ/k01.py,agents/champ/k06.py,"
                                      "agents/champ/k12.py,agents/newlines/n01.py,"
                                      "agents/newlines/n07.py,agents/newlines/n10.py,"
                                      "agents/ref/closer_cleo.py,"
                                      "submissions/2026-08-07-barnyard/main.py")
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    os.environ.setdefault("KG_FAST_ENV", "1")
    K = _engine()
    types = sorted(K.SHOPS)
    rng = random.Random(11)
    BASE_SEED = 123
    BASE_SHOPS = [types[i % len(types)] for i in range(K.MAX_SHOP_INSTANCES)]

    print(f"我方 {a.me}\n商店类型 {types}\n"
          f"固定组合（因子 A/C 用）{collections.Counter(BASE_SHOPS).most_common()}\n")

    print("=== 因子 A：只变棋盘/天气 seed（商店组合强制固定，对手固定）===")
    rows = [run(K, a.me, a.opp, BASE_SEED + 977 * i, BASE_SHOPS)[:2]
            for i in range(a.n)]
    sd_a = sd_report("A 棋盘 seed", rows)

    print("\n=== 因子 B：只变商店抽取（seed 固定，对手固定）===")
    rows_b = []
    draws = []
    for i in range(a.n):
        d = [rng.choice(types) for _ in range(K.MAX_SHOP_INSTANCES)]
        draws.append(d)
        rows_b.append(run(K, a.me, a.opp, BASE_SEED, d)[:2])
    sd_b = sd_report("B 商店抽取（随机 8 家）", rows_b)
    for d, r in sorted(zip(draws, rows_b), key=lambda t: t[1][0] - t[1][1])[:2] + \
                sorted(zip(draws, rows_b), key=lambda t: t[1][0] - t[1][1])[-2:]:
        milk = sum(1 for s in d if "MILK" in K.SHOPS[s])
        wool = sum(1 for s in d if "WOOL" in K.SHOPS[s])
        mel = sum(1 for s in d if "MELON" in K.SHOPS[s])
        print(f"      margin {r[0]-r[1]:>+9,.0f}  卖奶 {milk} 卖毛 {wool} 卖瓜 {mel}"
              f"  {collections.Counter(d).most_common(3)}")

    print("\n=== 因子 C：只变对手（seed 与商店都固定）===")
    opps = [o for o in a.opps.split(",") if os.path.exists(os.path.join(_REPO, o))]
    rows_c = [run(K, a.me, o, BASE_SEED, BASE_SHOPS)[:2] for o in opps]
    sd_c = sd_report(f"C 对手（{len(opps)} 个）", rows_c)

    tot = sd_a**2 + sd_b**2 + sd_c**2
    print(f"\n方差份额（sd² 归一）：棋盘 {100*sd_a**2/tot:.0f}%  "
          f"**商店抽取 {100*sd_b**2/tot:.0f}%**  对手 {100*sd_c**2/tot:.0f}%")
    print("读法：大头在商店抽取 ⇒ 条件化配置残差；大头在棋盘 ⇒ 农场程序鲁棒性，"
          "与卖出层无关；三者都小 ⇒ cleo 在静态配置下已接近天花板，"
          "剩下的价值只在农场与卖出的耦合里。")


if __name__ == "__main__":
    main()
