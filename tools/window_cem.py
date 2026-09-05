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
    """一次基线 rollout，记下 cleo 在窗口内的**完整市场订单列表**（保槽位）。

    第一版只记聚合后的 {产品: 量} 再用 `keep + sorted(sells)` 重组，
    δ=0 就复现不了 cleo（差 −162、no-op 35.2%）—— 因为**争夺是按槽位的**
    （`tools/sellsim.py` 判词），重排订单列表就换了结算。所以这里记原始列表，
    时移时只把 SELL 条目**搬到另一个回合的同一索引**，其余原位不动。
    """
    ep = copy.deepcopy(base)
    sched = []
    for _ in range(W):
        if ep.done:
            sched.append([]); continue
        a0 = _safe(me, obs_for(ep, 0))
        a1 = _safe(opp, obs_for(ep, 1))
        sched.append([list(o) for o in (a0.get("market") or []) if o])
        ep.step([a0, a1])
    return sched


def build_plan(sched, delta, W):
    """把每个 SELL 条目搬到 t+δ 的**同一索引**；δ=0 时逐位等于原列表。"""
    slots = [dict() for _ in range(W)]      # turn -> {index: order}
    for t, orders in enumerate(sched):
        for i, o in enumerate(orders):
            if o and o[0] == "SELL":
                tt = min(W - 1, max(0, t + int(delta.get(o[1], 0))))
                slots[tt].setdefault(i, []).append(o)
            else:
                slots[t].setdefault(i, []).append(o)
    plan = []
    for u in range(W):
        row = []
        for i in sorted(slots[u]):
            row.extend(slots[u][i])
        plan.append(row)
    return plan


def rollout_shift(base, me, opp, W, sched, delta, maxo=10):
    """**cleo 的订单列表 + 每产品一个时移**（订单空间的残差，9 个整数）。

    farmer / hands 仍逐回合来自 cleo（闭环）；市场列表按 `build_plan` 重放。
    **δ=0 必须逐位复现 cleo 的差额，且 no-op 率 ≈0** —— 这一格的已知阳性。
    no-op 用 patch `engine_np._commit_unit` 直接数成交，不用棚差分
    （棚同一步还会被收割与买入改动，差分会污染读数）。
    """
    plan = build_plan(sched, delta, W)
    ep = copy.deepcopy(base)
    filled = [0]
    real = engine_np._commit_unit

    def commit(op, item, price, farm, private, market, shed_capacity=100):
        ok = real(op, item, price, farm, private, market, shed_capacity)
        if ok and op == "SELL" and farm is ep.farms[0]:
            filled[0] += 1
        return ok

    engine_np._commit_unit = commit
    want = 0
    try:
        for w in range(W):
            if ep.done:
                break
            a0 = _safe(me, obs_for(ep, 0))
            a1 = _safe(opp, obs_for(ep, 1))
            row = plan[w][:maxo]
            want += sum(int(o[2]) for o in row
                        if o and o[0] == "SELL" and len(o) > 2)
            a0 = {"farmer": a0.get("farmer") or ["PASS"],
                  "hands": a0.get("hands") or [], "market": row}
            ep.step([a0, a1])
    finally:
        engine_np._commit_unit = real
    margin = float(ep.farms[0]["money"]) - float(ep.farms[1]["money"])
    noop = 1.0 - (filled[0] / want) if want else 0.0
    return margin, noop, want


def cem_shift(base, me, opp, W, sched, iters, pop, elite, rng, lo=-4, hi=4,
              verbose=True):
    """CEM over 每产品一个整数时移。9 维、每维 9 个取值 —— 便宜且对准机制。"""
    dims = PRODUCTS
    probs = {p: [1.0 / (hi - lo + 1)] * (hi - lo + 1) for p in dims}
    best = (-1e18, None, 1.0)
    for it in range(iters):
        cands = []
        for _ in range(pop):
            d = {p: lo + rng.choices(range(hi - lo + 1), probs[p])[0] for p in dims}
            m, noop, _w = rollout_shift(base, me, opp, W, sched, d)
            cands.append((m, d, noop))
        cands.sort(key=lambda t: -t[0])
        if cands[0][0] > best[0]:
            best = cands[0]
        top = cands[:elite]
        for p in dims:
            cnt = [0.0] * (hi - lo + 1)
            for _m, d, _n in top:
                cnt[d[p] - lo] += 1
            tot = sum(cnt) or 1
            probs[p] = [0.7 * probs[p][k] + 0.3 * cnt[k] / tot
                        for k in range(hi - lo + 1)]
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
    ap.add_argument("--shift", type=int, default=4, help="时移范围 +-N 回合")
    a = ap.parse_args()

    me, opp = load_agent(a.me), load_agent(a.opp)
    rng = random.Random(7)
    gains = []
    for s in [int(x) for x in a.seeds.split(",")]:
        ep = engine_np.Episode(seed=s, episode_steps=a.steps)
        T = a.steps - 1
        for _ in range(T - a.window):
            if ep.done:
                break
            ep.step([_safe(me, obs_for(ep, 0)), _safe(opp, obs_for(ep, 1))])
        base = ep
        cleo_margin = float("nan")
        ep2 = copy.deepcopy(base)
        for _ in range(a.window):
            if ep2.done: break
            ep2.step([_safe(me, obs_for(ep2, 0)), _safe(opp, obs_for(ep2, 1))])
        cleo_margin = float(ep2.farms[0]["money"]) - float(ep2.farms[1]["money"])

        sched = cleo_schedule(base, me, opp, a.window)
        vol = sum(int(o[2]) for r in sched for o in r
                  if o and o[0] == "SELL" and len(o) > 2)
        m0, noop0, want0 = rollout_shift(base, me, opp, a.window, sched,
                                         {p: 0 for p in PRODUCTS})
        print(f"\nseed {s}: 冻结点 step {base._step}  窗口内 cleo 计划卖 {vol} 单位  "
              f"棚 {shed_of(base, 0)}")
        print(f"  **cleo 闭环基线 {cleo_margin:+,.0f}** | δ=0 开环重放 {m0:+,.0f} "
              f"(差 {m0-cleo_margin:+,.0f}, no-op {noop0*100:.1f}%)", flush=True)
        # 已知阳性只该卡「δ=0 逐位复现 cleo」。no-op 的绝对值是 **cleo 自己的**
        # （它有时下单多于棚里的货），不是重放的产物 —— 第一版把 2% 当阈值是错的。
        # 要看的是 δ≠0 的 no-op 相对 δ=0 有没有变坏。
        if abs(m0 - cleo_margin) > 1:
            print("  ⚠️ 已知阳性不成立：δ=0 没有复现 cleo —— 开环重放已经在新状态上"
                  "卖不存在的货（非法动作静默 no-op，不会报错），这一格的读数不可信")
        else:
            print(f"  已知阳性通过：δ=0 逐位复现 cleo（cleo 自身 no-op {noop0*100:.1f}%，"
                  f"δ≠0 的 no-op 要和它比，不是和 0 比）")
        val, d, noop = cem_shift(base, me, opp, a.window, sched, a.iters, a.pop,
                                 a.elite, rng, -a.shift, a.shift)
        gains.append(val - cleo_margin)
        shifts = {k: v for k, v in sorted(d.items()) if v}
        print(f"  CEM 最好 {val:+,.0f}  **增益 {val - cleo_margin:+,.0f}**  "
              f"no-op {noop*100:.0f}%  时移 {shifts or '全 0'}")
    if gains:
        print(f"\n窗口 {a.window} 回合、每产品 ±{a.shift} 时移可拿到的增益："
              f"中位 {st.median(gains):+,.0f}   逐 seed {[f'{g:+,.0f}' for g in gains]}")


if __name__ == "__main__":
    main()
