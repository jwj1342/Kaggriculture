#!/usr/bin/env python
"""**条件化生产的先知上界**：知道商店抽签 / 对手之后换农场程序，能多拿多少 margin？

判词续二十七把卖出侧关闭了（生产固定时 cleo 离最优只差几百），并指出那 9,000 的
margin 住在生产里。专家的方案是把一条带子换成**一棵带子树**：在每个商店揭示点分支，
分支以"已见商店组合 + 识别出的对手"为条件。**先做上界，再做树。**

这里用一个不需要改带子的做法：**把 14 条挖来的农场程序当成分支**。
  * 条件化抽签的先知增益 = E_draw[ max_tape margin ] − max_tape E_draw[ margin ]
  * 条件化对手的先知增益 = E_opp [ max_tape margin ] − max_tape E_opp [ margin ]
两者都是**上界**（整条带子的粒度粗于每 3 天一次的分支，但带子之间的差异远大于
单个分支，所以作为"值不值得建树"的判据是合适的方向）。

商店组合的干预与 `tools/variance.py` 相同：**解锁的时刻与数量保持引擎原样，只换是
哪几家**，所以杂草的 RNG 抽取不受影响。
"""
import argparse
import collections
import itertools
import os
import random
import statistics as st

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _engine():
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    return K


def run(K, a, b, seed, forced, steps=720):
    from kaggle_environments import make
    real = K._town_consume

    def town(env, state, step):
        t = state[0].observation.town
        n = len(t.get("unlocked_shops") or [])
        if n:
            t["unlocked_shops"] = list(forced[:n])
        return real(env, state, step)

    K._town_consume = town
    try:
        env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
        env.run([a, b])
        o = env.steps[-1][0].observation
        return int(o["farms"][0]["money"]) - int(o["farms"][1]["money"])
    finally:
        K._town_consume = real


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", default="agents/newlines/n01.py,agents/newlines/n03.py,"
                                      "agents/newlines/n04.py,agents/newlines/n05.py,"
                                      "agents/newlines/n07.py,agents/newlines/n08.py,"
                                      "agents/newlines/n10.py,agents/newlines/n11.py,"
                                      "agents/champ/k01.py,agents/champ/k06.py")
    ap.add_argument("--opps", default="agents/champ/k01.py,agents/newlines/n04.py,"
                                      "agents/ref/closer_cleo.py")
    ap.add_argument("--seeds", default="123,555")
    ap.add_argument("--draws", type=int, default=5)
    a = ap.parse_args()
    os.environ.setdefault("KG_FAST_ENV", "1")
    K = _engine()
    types = sorted(K.SHOPS)
    rng = random.Random(11)
    mine = [m for m in a.mine.split(",") if os.path.exists(os.path.join(_REPO, m))]
    opps = [o for o in a.opps.split(",") if os.path.exists(os.path.join(_REPO, o))]
    seeds = [int(x) for x in a.seeds.split(",")]
    draws = [[rng.choice(types) for _ in range(K.MAX_SHOP_INSTANCES)]
             for _ in range(a.draws)]

    print(f"我方候选 {len(mine)} 条带子 × 抽签 {len(draws)} × 对手 {len(opps)} × "
          f"seed {len(seeds)} = {len(mine)*len(draws)*len(opps)*len(seeds)} 局\n")
    M = {}
    for i, d in enumerate(draws):
        for o in opps:
            for s in seeds:
                for m in mine:
                    M[(i, o, s, m)] = run(K, m, o, s, d)
        milk = sum(1 for x in d if "MILK" in K.SHOPS[x])
        wool = sum(1 for x in d if "WOOL" in K.SHOPS[x])
        best = max(mine, key=lambda m: st.median(M[(i, o, s, m)]
                                                 for o in opps for s in seeds))
        print(f"  抽签 {i}: 卖奶 {milk} 卖毛 {wool}  最佳带子 "
              f"{os.path.basename(best):10} "
              f"margin 中位 {st.median(M[(i,o,s,best)] for o in opps for s in seeds):>+9,.0f}",
              flush=True)

    def med(sel):
        return st.median(M[k] for k in M if sel(k))

    # 固定一条带子的最好期望
    fixed = {m: st.median(M[(i, o, s, m)] for i in range(len(draws))
                          for o in opps for s in seeds) for m in mine}
    best_fixed = max(fixed, key=fixed.get)
    print(f"\n最好的**固定**带子 {os.path.basename(best_fixed)}  "
          f"整体 margin 中位 {fixed[best_fixed]:>+9,.0f}")

    # 条件化抽签
    per_draw_best = [max(st.median(M[(i, o, s, m)] for o in opps for s in seeds)
                         for m in mine) for i in range(len(draws))]
    g_draw = st.median(per_draw_best) - fixed[best_fixed]
    # 条件化对手
    per_opp_best = [max(st.median(M[(i, o, s, m)] for i in range(len(draws))
                                  for s in seeds) for m in mine) for o in opps]
    g_opp = st.median(per_opp_best) - fixed[best_fixed]
    # 两者都条件化
    per_both = [max(st.median(M[(i, o, s, m)] for s in seeds) for m in mine)
                for i in range(len(draws)) for o in opps]
    g_both = st.median(per_both) - fixed[best_fixed]

    print(f"\n**先知增益（对最好的固定带子）**")
    print(f"  条件化【商店抽签】     {g_draw:>+9,.0f}")
    print(f"  条件化【对手】         {g_opp:>+9,.0f}")
    print(f"  两者都条件化           {g_both:>+9,.0f}")
    print(f"\n判据（专家预登记）：任一 ≥ +10,000 ⇒ 带子树是主线；"
          f"两者都 < +5,000 ⇒ 生产侧也接近天花板。")


if __name__ == "__main__":
    main()
