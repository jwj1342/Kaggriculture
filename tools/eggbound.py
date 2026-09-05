"""EGG 上界工具（判词续三十）。

含成本的鹅群上界：买鹅 300/只、隔日喂麦（按市价真金白银扣钱）、
   附带肥料产出（每只每天 1 个，随带子既有的 SELL FERTILIZER 一起卖）。
   蛋只在结算瞬间进棚，绝不占用棚容量；订单一律追加在末尾。"""
import sys, statistics as st
SHAM = "--sham" in sys.argv
from kaggle_environments import make
import kaggle_environments.envs.kaggriculture.kaggriculture as K

import os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(_ROOT, "agents/newlines/n04.py")

def run(seed, G, seat=0, fert=True, buyday=4, opp=None):
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    orig = K._process_market
    S = {"eggs": 0, "fert": 0, "feed_cost": 0, "buy_cost": 0, "last": -1, "pend_e": 0, "pend_f": 0}
    def patched(state, env_):
        if G <= 0:
            return orig(state, env_)
        obs0 = state[0].observation
        day = int(K.get(obs0, "day", 0) or 0)
        farm = obs0.farms[seat]; priv = state[seat].observation.private; shed = priv["shed"]
        if day != S["last"]:
            S["last"] = day
            if day == buyday:                               # 买鹅
                farm["money"] -= G * K.ANIMALS["GOOSE"]["cost"]; S["buy_cost"] += G * 300
            if day >= buyday:
                wp = K.market_price("WHEAT", obs0.market["inventory"]["WHEAT"], obs0.market.get("params"))
                c = (G // 2 + G % 2) * wp                   # 隔日喂 => 每天半数
                farm["money"] -= c; S["feed_cost"] += c
                if not SHAM: S["pend_e"] += G              # CARE 不做,保守取 1 蛋/只/天
                if fert and not SHAM: S["pend_f"] += G
        act = state[seat].action
        if isinstance(act, dict) and isinstance(act.get("market"), list):
            m = act["market"]; added = []
            b_e, b_f = shed.get("EGG", 0), shed.get("FERTILIZER", 0)
            if S["pend_e"] > 0 and len(m) < 10:
                shed["EGG"] = b_e + S["pend_e"]; m.append(["SELL", "EGG", S["pend_e"]]); added.append("E")
            if fert and S["pend_f"] > 0 and len(m) < 10:
                shed["FERTILIZER"] = b_f + S["pend_f"]; m.append(["SELL", "FERTILIZER", S["pend_f"]]); added.append("F")
            if added:
                r = orig(state, env_)
                if "E" in added:
                    sold = (b_e + S["pend_e"]) - shed.get("EGG", 0); S["eggs"] += sold
                    S["pend_e"] = max(0, S["pend_e"] - sold); shed["EGG"] = b_e
                    if shed.get("EGG", 0) <= 0: shed.pop("EGG", None)
                if "F" in added:
                    sold = (b_f + S["pend_f"]) - shed.get("FERTILIZER", 0); S["fert"] += sold
                    S["pend_f"] = max(0, S["pend_f"] - sold); shed["FERTILIZER"] = b_f
                    if shed.get("FERTILIZER", 0) <= 0: shed.pop("FERTILIZER", None)
                return r
        return orig(state, env_)
    K._process_market = patched
    try:
        env.run([AGENT, opp or AGENT])
    finally:
        K._process_market = orig
    mn = [f["money"] for f in env.state[0].observation.farms]
    return mn[seat] - mn[1 - seat], mn[seat], S

if __name__ == "__main__":
    seeds = [int(x) for x in sys.argv[1].split(",")]
    Gs = [int(x) for x in sys.argv[2].split(",")]
    fert = "--nofert" not in sys.argv
    bd = int([a.split("=")[1] for a in sys.argv if a.startswith("--buyday=")][0]) if any(a.startswith("--buyday=") for a in sys.argv) else 4
    OPP = ([a.split("=",1)[1] for a in sys.argv if a.startswith("--opp=")] or [None])[0]
    base = {s: run(s, 0, opp=OPP)[0] for s in seeds}
    print(f"对手 {OPP or '镜像 n04'}  买鹅日 {bd}  含成本（买鹅+喂麦{'+肥料收入' if fert else '，无肥料'}）  基线 margin {base}")
    print(f"{'鹅数':>5}{'seed':>7}{'Δmargin':>11}{'我方钱':>10}{'蛋':>7}{'肥':>7}{'买鹅':>9}{'喂麦':>9}")
    for G in Gs:
        d = []
        for s in seeds:
            mg, mo, S = run(s, G, fert=fert, buyday=bd, opp=OPP)
            d.append(mg - base[s])
            print(f"{G:>5}{s:>7}{mg-base[s]:>+11,.0f}{mo:>10,.0f}{S['eggs']:>7}{S['fert']:>7}"
                  f"{-S['buy_cost']:>9,}{-S['feed_cost']:>9,}")
        print(f"  ==> {G} 只鹅  **配对 Δmargin 中位 {st.median(d):+,.0f}**\n")
