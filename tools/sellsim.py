#!/usr/bin/env python
"""卖出侧的前向模型：回合内的逐单位价格行走、小镇消耗、对手卖出推断。

**搜索建在错的市场模型上就是第五次重复，所以这个文件的每一条都必须能逐美元复现
引擎**，`verify()` 就是那道门（对真实对局的每一个卖出回合断言逐美元相等）。

三件事，都直接读自 `reference/engine/kaggriculture.py`：

1. **回合内是逐单位锁步，而且双方按同一 pre-commit 库存报价**（`_process_market`
   的 `quoted` 循环在任何 `_commit_unit` 之前填满）。所以**同一回合内没有先手价格
   优势** —— 两人拿同一个价。抢跑因此只能跨回合生效：先卖的那一方把账本抬高，
   后卖的那一方吃低价。这一条是整条线的基础，写错了搜索就在优化一个不存在的杠杆。
2. **卖出把库存 +1，除非成交价已经是 $1**（`_commit_unit`：`if price > 1`）。
3. **消耗是确定的且可观测**：商店在 `step % 4 == 0` 触发，每个已解锁实例对它卖的
   每个产品消耗 1（单品商店 ×2）；镇中心在 `step % 24 == 0` 对除 FERTILIZER 外的
   八个产品各消耗 1。`obs["town"]["unlocked_shops"]` 在观测里，所以推理时可以精确算。
"""
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _engine():
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    return K


def consumption_at(K, shops, step, cfg_shop=4, cfg_centre=24):
    """这一步末尾小镇会吃掉多少（返回 {product: units}）。确定的，可观测。"""
    out = {}
    if step % cfg_shop == 0:
        for s in shops:
            prods = K.SHOPS.get(s) or []
            mult = 2 if len(prods) == 1 else 1
            for p in prods:
                out[p] = out.get(p, 0) + mult
    if step % cfg_centre == 0:
        for p in K.TOWN_CENTER_PRODUCTS:
            out[p] = out.get(p, 0) + 1
    return out


def market_phase(K, inv, orders, sheds, moneys, cap=100,
                 hires=(0, 0), quads=(1, 1)):
    """**完整**复现 `_process_market`：给两边的订单列表，算出各自的收入/支出与终局账本。

    第一版只写了「同回合逐单位交错」，548 个卖出回合里错了 16 个（全差 1 美元）。
    原因是**外层循环是槽位 `i`，只有同一槽位的两张单才交错**
    （`kaggriculture.py:562` 的 `for i in range(max_len)`）。
    所以"争夺"的正确定义是**同槽位**，不是同回合 —— 这同时是一个可用的杠杆：
    把卖单放在对手买单的槽位上，两边就不互相走价。

    返回 (per-seat 现金变动, 终局库存, per-seat 成交明细)。
    **HIRE / BUY_LAND 不动市场账本，但是花钱的** —— 第一版把它们当成"不计价"，
    154/948 个回合因此对不上：它们改变的钱会决定后面的买单成不成功。
    所以它们在这里按引擎的顺序、按引擎的成本（`_fib(hires_today)` / `LAND_PRICES`）
    结算。`hires` 与 `quads` 是两边当回合开始时的 `hires_today` 与已解锁象限数。
    """
    inv = dict(inv)
    sheds = [dict(x) for x in sheds]
    moneys = list(moneys)
    cash = [0, 0]
    fills = [[], []]
    hires = list(hires)
    quads = list(quads)
    LP = getattr(K, "LAND_PRICES", [1000, 2000, 4000])
    HM = getattr(K, "FARM_HAND_COST_MULT", 1)
    qs = [list(o)[:getattr(K, "MAX_ORDERS", 10)] for o in orders]
    for i in range(max(len(qs[0]), len(qs[1]))):
        st = []
        for p in (0, 1):
            o = qs[p][i] if i < len(qs[p]) else None
            if not o or not isinstance(o, (list, tuple)) or not o:
                st.append(None); continue
            op = o[0]
            if op == "HIRE":
                c = HM * K._fib(hires[p])
                if moneys[p] >= c:
                    moneys[p] -= c; cash[p] -= c; hires[p] += 1
                st.append(None); continue
            if op == "BUY_LAND":
                extra = quads[p] - 1
                if extra < len(LP):
                    c = LP[extra]
                    if moneys[p] >= c:
                        moneys[p] -= c; cash[p] -= c; quads[p] += 1
                st.append(None); continue
            if op in ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(o) >= 3:
                try: n = int(o[2])
                except (TypeError, ValueError): st.append(None); continue
                st.append({"t": op, "i": o[1], "n": n} if n > 0 else None)
            else:
                st.append(None)
        for _ in range(100_000):
            quoted = [None, None]
            for p in (0, 1):
                s_ = st[p]
                if s_ is None or s_["n"] <= 0: continue
                t, it = s_["t"], s_["i"]
                if t == "SELL" and it in K.PRODUCTS:
                    quoted[p] = (t, it, K.market_price(it, inv.get(it, K.MARKET_I0)))
                elif t == "BUY_PRODUCT" and it in ("WHEAT", "FERTILIZER"):
                    quoted[p] = (t, it, K.market_price(it, inv.get(it, K.MARKET_I0) - 1))
                elif t == "BUY_SEED" and it in K.CROPS:
                    quoted[p] = (t, it, K.CROPS[it]["seed"])
                elif t == "BUY_ANIMAL" and it in K.ANIMALS:
                    quoted[p] = (t, it, K.ANIMALS[it]["cost"])
                else:
                    st[p] = None
            if quoted[0] is None and quoted[1] is None: break
            committed = False
            for p in (0, 1):
                q = quoted[p]
                if q is None: continue
                t, it, price = q
                ok = False
                if t == "SELL":
                    if sheds[p].get(it, 0) > 0:
                        sheds[p][it] -= 1; moneys[p] += price; cash[p] += price
                        if price > 1: inv[it] = inv.get(it, K.MARKET_I0) + 1
                        fills[p].append((it, price)); ok = True
                elif t == "BUY_PRODUCT":
                    if moneys[p] >= price and sum(sheds[p].values()) < cap:
                        moneys[p] -= price; cash[p] -= price
                        sheds[p][it] = sheds[p].get(it, 0) + 1
                        inv[it] = inv.get(it, K.MARKET_I0) - 1
                        fills[p].append((it, -price)); ok = True
                elif t == "BUY_SEED":
                    if moneys[p] >= price:
                        moneys[p] -= price; cash[p] -= price; ok = True
                elif t == "BUY_ANIMAL":
                    if moneys[p] >= price and sum(sheds[p].values()) < cap:
                        moneys[p] -= price; cash[p] -= price
                        sheds[p][it] = sheds[p].get(it, 0) + 1; ok = True
                if ok:
                    st[p]["n"] -= 1; committed = True
                else:
                    st[p] = None
            if not committed: break
    return cash, inv, fills


def infer_opponent_sales(prev_inv, inv, my_net, consumed):
    """从账本反推对手的净卖出：`inv - prev_inv = 我方净 + 对手净 - 消耗`。

    **这是观测里拿不到对手棚时唯一的对手信号**（`rl/obs.py` 写明对手的棚与种子是
    私有的）。它是净量而不是下单量，所以 $1 成交与失败的单看不见 —— 但那正是
    价格意义上重要的那部分。
    """
    return {it: (inv.get(it, 0) - prev_inv.get(it, 0)) - my_net.get(it, 0)
                + consumed.get(it, 0)
            for it in set(prev_inv) | set(inv)}


def verify(seeds=(123, 555), steps=720,
           a="submissions/2026-09-04-sharedmeta-cleo/main.py",
           b="agents/champ/k01.py"):
    """门：对真实对局的**每一个市场回合**，`market_phase()` 必须逐美元复现引擎的现金变动。

    喂进去的是双方**实际提交的订单列表**（含槽位顺序）与该回合开盘前的账本、棚、钱，
    所以这是端到端的复现，不是重构。带已知阳性：必须有争夺回合（**同槽位**双方都卖
    同一产品）参与，否则这道门在最重要的路径上是空过的。
    """
    os.environ.setdefault("KG_FAST_ENV", "1")
    K = _engine()
    from kaggle_environments import make

    snaps = []
    real_market = K._process_market

    def process_market(state, env):
        o = state[0].observation
        snaps.append(dict(
            step=int(o.step),
            inv=dict(o.market["inventory"]),
            money=[float(o.farms[p]["money"]) for p in (0, 1)],
            shed=[dict(state[p].observation.private.get("shed") or {})
                  for p in (0, 1)],
            hires=[int(o.farms[p].get("hires_today", 0)) for p in (0, 1)],
            quads=[len(o.farms[p].get("unlocked_quadrants") or ["NW"])
                   for p in (0, 1)],
            orders=[list((state[p].action or {}).get("market") or [])
                    if isinstance(state[p].action, dict) else []
                    for p in (0, 1)]))
        r = real_market(state, env)
        snaps[-1]["money_after"] = [float(o.farms[p]["money"]) for p in (0, 1)]
        snaps[-1]["inv_after"] = dict(o.market["inventory"])
        return r

    K._process_market = process_market
    checked = contested = bad = 0
    try:
        for seed in seeds:
            snaps.clear()
            env = make("kaggriculture",
                       configuration={"episodeSteps": steps, "seed": seed})
            env.run([a, b])
            for sn in snaps:
                if not any(sn["orders"]):
                    continue
                cash, inv, _f = market_phase(K, sn["inv"], sn["orders"],
                                             sn["shed"], sn["money"],
                                             hires=sn["hires"], quads=sn["quads"])
                want = [sn["money_after"][p] - sn["money"][p] for p in (0, 1)]
                checked += 1
                # 同槽位双方都卖同一产品 = 争夺
                for i in range(min(len(sn["orders"][0]), len(sn["orders"][1]))):
                    o0, o1 = sn["orders"][0][i], sn["orders"][1][i]
                    if (o0 and o1 and o0[0] == "SELL" and o1[0] == "SELL"
                            and o0[1] == o1[1]):
                        contested += 1
                        break
                if [round(c) for c in cash] != [round(w) for w in want] or \
                        inv != sn["inv_after"]:
                    bad += 1
                    if bad <= 3:
                        print(f"  ✗ seed {seed} step {sn['step']}: "
                              f"引擎现金 {[round(w) for w in want]} / "
                              f"模型 {[round(c) for c in cash]}"
                              + ("  账本也不符" if inv != sn["inv_after"] else ""))
    finally:
        K._process_market = real_market
    print(f"verify: {checked} 个市场回合，其中 **{contested} 个同槽位争夺回合**，"
          f"不一致 {bad}")
    if contested == 0:
        raise SystemExit("已知阳性为 0：没有争夺回合参与检验，这道门是空过的")
    if bad:
        raise SystemExit(f"{bad} 个回合模型与引擎不符 —— 搜索不能建在这上面")
    print("门通过：前向模型逐美元复现引擎（含同槽位争夺回合）")


if __name__ == "__main__":
    verify()
