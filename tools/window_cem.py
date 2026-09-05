#!/usr/bin/env python
"""回退课程的第一格：**冻结 cleo 前缀，只开最后 W 回合，直接优化终局配对差额。**

为什么这是最友好的学习问题（Salimans & Chen 2018 的回退课程 / Jump-Start RL，
方向反过来做）：

  * 前缀全部冻结为 cleo，所以**不需要任何中途的胜负代理** —— 奖励就是终局
    `我方钱 − 对手钱`。这个游戏在第 10 回合没有"打过"可言（前期全是负现金流），
    造中途 φ 正是这个项目已经吃过亏的地方。
  * 窗口之外全部冻结，终局差额几乎是**窗口内动作的确定函数**（我们的卖单不改变
    地块数，而杂草与商店抽签共用同一条 RNG 且随空地数变化，所以抽签也不变）。
    信用分配从 720 步塌缩到几十步，本质上是一个上下文 bandit。
  * **CEM 不从策略采样**，所以 P≈1e-7 的表示缺口在这一步不适用 —— 修头是 PPO 的
    前置条件，不是这一步的。这一步先量出"最后一个窗口里到底有多少 margin 可拿"。

参考实现用 `engine_np`（对官方引擎有逐字节门），因为它能 deepcopy 与逐动作驱动：
实测 deepcopy 0.1 ms、60 步 2 ms（空盘），所以一次窗口 rollout 是毫秒级。

**学习者只控制窗口内的 SELL 单**；farmer / hands / 非 SELL 市场单全部来自 cleo，
所以零计划逐位等于 cleo（这就是这一格的已知阳性）。
"""
import argparse
import collections
import copy
import os
import random
import statistics as st
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "rl", "tensor_env"))
import engine_np  # noqa: E402

PRODUCTS = list(engine_np.PRODUCTS)


def load_agent(path):
    """kaggle_environments.agent.get_last_callable 的忠实模拟。"""
    src = open(os.path.join(_REPO, path)).read()
    env = {}
    d = os.path.dirname(os.path.join(_REPO, path))
    sys.path.append(d)
    try:
        exec(src, env)
    finally:
        if d in sys.path:
            sys.path.remove(d)
    cs = [v for v in env.values() if callable(v)]
    return cs[-1]


def obs_for(ep, p):
    s = ep.snapshot()
    return {"step": ep._step, "player": p, "day": s["day"], "hour": s["hour"],
            "farms": s["farms"], "market": s["market"], "town": s["town"],
            "private": s["private"][p], "remainingOverageTime": 60}


def _safe(fn, ob):
    try:
        a = fn(ob)
        return a if isinstance(a, dict) else {"farmer": ["PASS"], "hands": [], "market": []}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}


def shed_of(ep, p):
    return {k: int(v) for k, v in ep.privates[p]["shed"].items() if v}


def cleo_schedule(base, me, opp, W, maxo=10):
    """一次基线 rollout，记下 (cleo 的完整市场订单列表, 对手每回合卖了什么)。

    保留**原始列表与槽位索引** —— 第一版聚合成 {产品: 量} 再重组，δ=0 就复现不了
    cleo（差 −162、no-op 35.2%），因为**争夺是按槽位的**（判词续二十四）。

    对手的卖出是**先知信息**：这里用它来量"若完全知道对手何时卖，抢跑值多少"的
    天花板。天花板小 ⇒ 任何对手模型都救不了，不必再等预测器。
    """
    ep = copy.deepcopy(base)
    sched, opp_sched = [], []
    for _ in range(W):
        if ep.done:
            sched.append([]); opp_sched.append({}); continue
        a0 = _safe(me, obs_for(ep, 0))
        a1 = _safe(opp, obs_for(ep, 1))
        sched.append([list(o) for o in (a0.get("market") or []) if o])
        opp_sched.append({o[1]: int(o[2]) for o in (a1.get("market") or [])
                          if o and o[0] == "SELL" and len(o) > 2})
        ep.step([a0, a1])
    return sched, opp_sched


ALL = 10 ** 6            # 「全卖」：引擎按棚里的量截断


def build_plan(sched, opp_sched, knobs, W):
    """订单空间的残差，四个维度，每产品一组。δ 全 0 / 其余全关时逐位等于 cleo。

      shift_p    推迟/提前该产品的每一张卖单（搬到另一回合的**同一索引**）
      halve_p    减半（`ceil(q/2)`）
      avoid_p    **同槽位规避**：对手同一回合也卖 p 时，跳过我这张单。
                 这一条直接对准"争夺是按槽位的"那个发现 —— 不在对手身上走价。
      frac_p     **配置类**：把该产品的每张卖单按比例缩放，`0` = 整局不卖（持有）。
                 方差分解说可操纵的因子是**商店抽取**（我方钱 sd 17,914，而棋盘只有 499），
                 而商店组合决定哪些产品有需求 —— 所以「这局别卖 melon」这种配置决策
                 才是那 18k 所在的维度，时序类的四个维度从设计上就动不到它。
      preempt_p  **主动抢跑**：对手将在 t 卖 p，就在 t−1 追加一张全卖 p。
                 同回合内双方按同一 pre-commit 库存报价，所以抢跑只能跨回合。
    """
    slots = [dict() for _ in range(W)]
    for t, orders in enumerate(sched):
        for i, o in enumerate(orders):
            if o and o[0] == "SELL" and len(o) > 2:
                p = o[1]
                if knobs["avoid"].get(p) and opp_sched[t].get(p):
                    continue                       # 删除：不与对手同槽位相撞
                q = int(o[2])
                f = knobs.get("frac", {}).get(p, 1.0)
                if f <= 0.0:
                    continue                       # 完全不卖这个产品（持有）
                if f < 1.0:
                    q = max(1, int(q * f + 0.5))
                if knobs["halve"].get(p):
                    q = (q + 1) // 2
                if q <= 0:
                    continue
                tt = min(W - 1, max(0, t + int(knobs["shift"].get(p, 0))))
                slots[tt].setdefault(i, []).append(["SELL", p, q])
            else:
                slots[t].setdefault(i, []).append(o)
    for p, on in knobs["preempt"].items():
        if not on:
            continue
        for t, sells in enumerate(opp_sched):
            if sells.get(p) and t > 0:
                slots[t - 1].setdefault(10 ** 9, []).append(["SELL", p, ALL])
    return [[o for i in sorted(slots[u]) for o in slots[u][i]] for u in range(W)]


ZERO = None


def zero_knobs():
    return {"shift": {p: 0 for p in PRODUCTS},
            "halve": {p: 0 for p in PRODUCTS},
            "avoid": {p: 0 for p in PRODUCTS},
            "preempt": {p: 0 for p in PRODUCTS},
            "frac": {p: 1.0 for p in PRODUCTS}}


def rollout_shift(base, me, opp, W, sched, opp_sched, knobs, maxo=10):
    """**cleo 的订单列表 + 每产品一个时移**（订单空间的残差，9 个整数）。

    farmer / hands 仍逐回合来自 cleo（闭环）；市场列表按 `build_plan` 重放。
    **全零 knobs 必须逐位复现 cleo 的差额** —— 这一格的已知阳性。
    no-op 用 patch `engine_np._commit_unit` 直接数成交，不用棚差分
    （棚同一步还会被收割与买入改动，差分会污染读数）。
    """
    plan = build_plan(sched, opp_sched, knobs, W)
    ep = copy.deepcopy(base)
    # no-op 按**成交为 0 的订单数**算，不按单位比 —— `preempt` 追加的是「全卖」
    # （量 10^6），按单位比会把分母撑爆，第一版因此读出 100%，那是坏指标。
    per_item = [collections.Counter()]
    real = engine_np._commit_unit

    def commit(op, item, price, farm, private, market, shed_capacity=100):
        ok = real(op, item, price, farm, private, market, shed_capacity)
        if ok and op == "SELL" and farm is ep.farms[0]:
            per_item[0][item] += 1
        return ok

    engine_np._commit_unit = commit
    orders = dead = 0
    try:
        for w in range(W):
            if ep.done:
                break
            a0 = _safe(me, obs_for(ep, 0))
            a1 = _safe(opp, obs_for(ep, 1))
            row = plan[w][:maxo]
            sells = [o for o in row if o and o[0] == "SELL" and len(o) > 2]
            per_item[0].clear()
            a0 = {"farmer": a0.get("farmer") or ["PASS"],
                  "hands": a0.get("hands") or [], "market": row}
            ep.step([a0, a1])
            for o in sells:
                orders += 1
                if per_item[0].get(o[1], 0) <= 0:
                    dead += 1
    finally:
        engine_np._commit_unit = real
    margin = float(ep.farms[0]["money"]) - float(ep.farms[1]["money"])
    noop = (dead / orders) if orders else 0.0
    return margin, noop, orders


def cem_knobs(base, me, opp, W, sched, opp_sched, iters, pop, elite, rng,
              lo=-4, hi=4, dims=("shift", "halve", "avoid", "preempt"),
              verbose=True):
    """CEM over 每产品的四个旋钮。因子化分布：9 个 categorical + 27 个 Bernoulli。"""
    # **Local search out of cleo**, not a 50% random restart. The residual's whole
    # point is "zero deviation == cleo", so the distribution starts near the zero
    # solution and the zero solution stays resident in the population -- which
    # makes `best` incapable of being worse than cleo. Initialising at 0.5 on the
    # full-game window read -11,532 / -50,949; that is an under-powered optimiser,
    # not a finding (the known positive still passed, so the harness was fine).
    nsh = hi - lo + 1
    pr_shift = {p: [(0.6 if j == -lo else 0.4 / (nsh - 1)) for j in range(nsh)]
                for p in PRODUCTS}
    pr_bin = {d: {p: 0.12 for p in PRODUCTS} for d in ("halve", "avoid", "preempt")}
    FRACS = [1.0, 0.75, 0.5, 0.25, 0.0]
    pr_frac = {p: [0.6, 0.1, 0.1, 0.1, 0.1] for p in PRODUCTS}
    m_z, n_z, _oz = rollout_shift(base, me, opp, W, sched, opp_sched, zero_knobs())
    best = (m_z, zero_knobs(), n_z)
    for it in range(iters):
        cands = [(m_z, zero_knobs(), n_z)]
        for _ in range(pop - 1):
            k = zero_knobs()
            if "shift" in dims:
                for p in PRODUCTS:
                    k["shift"][p] = lo + rng.choices(range(nsh), pr_shift[p])[0]
            for d in ("halve", "avoid", "preempt"):
                if d in dims:
                    for p in PRODUCTS:
                        k[d][p] = 1 if rng.random() < pr_bin[d][p] else 0
            if "frac" in dims:
                for p in PRODUCTS:
                    k["frac"][p] = FRACS[rng.choices(range(len(FRACS)),
                                                     pr_frac[p])[0]]
            m, noop, _w = rollout_shift(base, me, opp, W, sched, opp_sched, k)
            cands.append((m, k, noop))
        cands.sort(key=lambda t: -t[0])
        if cands[0][0] > best[0]:
            best = cands[0]
        top = cands[:elite]
        if "shift" in dims:
            for p in PRODUCTS:
                cnt = [0.0] * nsh
                for _m, k, _n in top:
                    cnt[k["shift"][p] - lo] += 1
                tot = sum(cnt) or 1
                pr_shift[p] = [0.7 * pr_shift[p][j] + 0.3 * cnt[j] / tot
                               for j in range(nsh)]
        for d in ("halve", "avoid", "preempt"):
            if d not in dims:
                continue
            for p in PRODUCTS:
                m_ = sum(k[d][p] for _m, k, _n in top) / len(top)
                pr_bin[d][p] = 0.7 * pr_bin[d][p] + 0.3 * m_
        if "frac" in dims:
            for p in PRODUCTS:
                cnt = [0.0] * len(FRACS)
                for _m, k, _n in top:
                    cnt[FRACS.index(k["frac"][p])] += 1
                tot = sum(cnt) or 1
                pr_frac[p] = [0.7 * pr_frac[p][j] + 0.3 * cnt[j] / tot
                              for j in range(len(FRACS))]
        if verbose:
            print(f"    iter {it:2d}  best {cands[0][0]:>+10,.0f}  "
                  f"elite 均 {st.mean(c for c, _, _ in top):>+10,.0f}  "
                  f"no-op {cands[0][2]*100:.0f}%", flush=True)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default="submissions/2026-09-04-sharedmeta-cleo/main.py")
    ap.add_argument("--opp", default="agents/champ/k01.py")
    ap.add_argument("--seeds", default="123,555")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--window", type=int, default=240)
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--pop", type=int, default=30)
    ap.add_argument("--elite", type=int, default=6)
    ap.add_argument("--shift", type=int, default=4)
    ap.add_argument("--dims", default="shift,halve,avoid,preempt",
                    help="打开哪几个残差维度；用来做逐维消融")
    ap.add_argument("--shops", default="",
                    help="逗号分隔，强制商店组合。解锁的**时刻与数量**仍由引擎决定，"
                         "只换是哪几家 —— 杂草与商店共用一条 RNG，所以这样干预"
                         "不会改变杂草抽取。与 tools/variance.py 同一种手法。")
    a = ap.parse_args()
    if a.shops:
        forced = [x for x in a.shops.split(",") if x]
        _real_step = engine_np.Episode.step

        def _step(self, actions):
            k = len(self.town.get("unlocked_shops") or [])
            if k:
                self.town["unlocked_shops"] = list(forced[:k])
            return _real_step(self, actions)

        engine_np.Episode.step = _step
        print(f"强制商店组合: {forced}")

    me, opp = load_agent(a.me), load_agent(a.opp)
    dims = tuple(x for x in a.dims.split(",") if x)
    rng = random.Random(7)
    gains = []
    for s in [int(x) for x in a.seeds.split(",")]:
        ep = engine_np.Episode(seed=s, episode_steps=a.steps)
        for _ in range((a.steps - 1) - a.window):
            if ep.done:
                break
            ep.step([_safe(me, obs_for(ep, 0)), _safe(opp, obs_for(ep, 1))])
        base = ep
        ep2 = copy.deepcopy(base)
        for _ in range(a.window):
            if ep2.done:
                break
            ep2.step([_safe(me, obs_for(ep2, 0)), _safe(opp, obs_for(ep2, 1))])
        cleo_margin = float(ep2.farms[0]["money"]) - float(ep2.farms[1]["money"])

        sched, opp_sched = cleo_schedule(base, me, opp, a.window)
        vol = sum(int(o[2]) for r in sched for o in r
                  if o and o[0] == "SELL" and len(o) > 2)
        contest = sum(1 for t, r in enumerate(sched)
                      if any(o and o[0] == "SELL" and opp_sched[t].get(o[1])
                             for o in r))
        m0, noop0, _w = rollout_shift(base, me, opp, a.window, sched, opp_sched,
                                      zero_knobs())
        print(f"\nseed {s}: 冻结点 step {base._step}  cleo 计划卖 {vol} 单位  "
              f"**同槽位争夺回合 {contest}/{a.window}**  棚 {shed_of(base, 0)}")
        print(f"  cleo 闭环基线 {cleo_margin:+,.0f} | 全零 knobs {m0:+,.0f} "
              f"(差 {m0-cleo_margin:+,.0f})", flush=True)
        if abs(m0 - cleo_margin) > 1:
            print("  ⚠️ 已知阳性不成立：全零 knobs 没有逐位复现 cleo，读数不可信")
        else:
            print(f"  已知阳性通过（cleo 自身 no-op {noop0*100:.1f}%，"
                  f"非零 knobs 的 no-op 要和它比）")
        val, k, noop = cem_knobs(base, me, opp, a.window, sched, opp_sched,
                                 a.iters, a.pop, a.elite, rng,
                                 -a.shift, a.shift, dims)
        gains.append(val - cleo_margin)
        on = {d: [p for p in PRODUCTS if k[d][p]] for d in
              ("halve", "avoid", "preempt")}
        sh = {p: v for p, v in sorted(k["shift"].items()) if v}
        print(f"  CEM 最好 {val:+,.0f}  **增益 {val-cleo_margin:+,.0f}**  "
              f"no-op {noop*100:.0f}%")
        fr = {p: v for p, v in sorted(k.get("frac", {}).items()) if v != 1.0}
        print(f"    shift {sh or '全 0'}")
        print(f"    frac  {fr or '全 1.0'}")
        for d in ("halve", "avoid", "preempt"):
            if d in dims:
                print(f"    {d:8} {on[d] or '全关'}")
    if gains:
        print(f"\n窗口 {a.window}、维度 [{a.dims}] 的增益："
              f"中位 {st.median(gains):+,.0f}   逐 seed {[f'{g:+,.0f}' for g in gains]}")
        print("（对手卖出用的是**先知**信息，所以这是抢跑/规避的**天花板**；"
              "天花板小 ⇒ 任何对手模型都救不了）")


if __name__ == "__main__":
    main()
