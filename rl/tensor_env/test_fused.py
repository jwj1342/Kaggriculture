#!/usr/bin/env python
"""Byte-exact gate for the fused single-pass board analysis (actions.analyze).

Plays 2 full episodes (seeds 3111, 3112) on KGEnvNP vs "starter" with a
random-legal policy (numpy default_rng(0)) and at EVERY step compares the
rewired obs.encode / actions.farmer_mask / actions.market_mask /
obs.net_worth / obs.opp_visible_worth / actions.decode against verbatim
copies of the pre-fusion implementations kept below as the reference.
Exact equality everywhere -- arrays with array_equal, floats with ==,
decode dicts with ==.

Also times both paths per step and prints the speedup. Ends with
FUSED-PASS / FUSED-FAIL.

    source setup_env.sh && python rl/tensor_env/test_fused.py
"""

import os
import sys
import time
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np

import actions as A
import obs as O
import kg_rules as R
from kg_rules import _fib
from adapter import KGEnvNP

# ==========================================================================
# REFERENCE: verbatim copies of the original (pre-fusion) implementations.
# Only renames: ref_ prefixes, _scan -> ref_scan. Static tables (action
# lists, index maps, PLANT_DEADLINE, _me, _farmer_action, _hands_actions)
# are untouched by the fusion and are shared from actions/obs directly.
# ==========================================================================

N = 10
C = 24
CROP_LIST = list(R.CROPS)
ANIMAL_LIST = list(R.ANIMALS)
PRODUCT_LIST = list(R.PRODUCTS)
SHOP_LIST = sorted(R.SHOPS)
_QUADS = ["NE", "SW", "SE"]
BASE_G = 8 + 9 * 4 + 3 + 5 + 3 + 3 + 8 + 1
HAND_FEATURES = 3 + len(PRODUCT_LIST) + len(ANIMAL_LIST)
G = BASE_G + A.MAX_HANDS * HAND_FEATURES
assert G == O.G and C == O.C, "layout constants drifted from obs.py"


def ref_encode_board(farm, out, day):
    """Fill one (C, N, N) block for one farm. Single pass."""
    for y in range(N):
        row = farm["tiles"][y]
        for x in range(N):
            t = row[x]
            if t is None:
                out[0, y, x] = 1.0
            elif t == "LOCKED":
                out[1, y, x] = 1.0
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    out[2, y, x] = 1.0
                elif kind == "PLANT":
                    out[5 + CROP_LIST.index(t["crop"]), y, x] = 1.0
                    out[10, y, x] = t.get("yield_units", 0) / 6.0
                    out[11, y, x] = 1.0 if t.get("watered_today") else 0.0
                    out[13, y, x] = min(t.get("consecutive_unwatered", 0), 2) / 2.0
                    fert_left = max(0, t.get("fertilized_until_day", -1) - day + 1)
                    out[12, y, x] = min(fert_left, 3) / 3.0
                    out[14, y, x] = min(day - t.get("planted_day", day), 12) / 12.0
                elif "animal" in t:
                    out[15 + ANIMAL_LIST.index(t["animal"]), y, x] = 1.0
                    out[10, y, x] = t.get("yield_units", 0) / 6.0
                    out[18, y, x] = 1.0 if t.get("fed_today") else 0.0
                    out[19, y, x] = 1.0 if t.get("cared_today") else 0.0
                    out[20, y, x] = 1.0 if t.get("fertilizer_available") else 0.0
                    out[21, y, x] = min(t.get("consecutive_unfed", 0), 2) / 2.0
                elif kind == "COOP":
                    out[3, y, x] = 1.0
                elif kind == "PASTURE":
                    out[4, y, x] = 1.0
    fx, fy = farm["farmer"]
    out[22, fy, fx] = 1.0
    for hpos in farm.get("hands", []):
        out[23, hpos[1], hpos[0]] += 0.25


def ref_global_features(obs):
    me = obs["player"]
    farms = obs["farms"]
    mine, theirs = farms[me], farms[1 - me]
    priv = obs["private"]
    market = obs["market"]
    prices = market["prices"]
    inv = market["inventory"]
    shed = priv["shed"]
    seeds = priv["seeds"]
    carried = priv["inventories"][0] if priv["inventories"] else {}
    day, hour = obs.get("day", 0), obs.get("hour", 0)

    import math
    g = [
        day / 30.0,
        hour / 24.0,
        math.log1p(max(0.0, mine["money"])) / 12.0,
        math.log1p(max(0.0, theirs["money"])) / 12.0,
        len(mine.get("hands", [])) / 10.0,
        len(theirs.get("hands", [])) / 10.0,
        mine.get("hires_today", 0) / 8.0,
        sum(shed.values()) / R.SHED_CAPACITY,
    ]
    for p in PRODUCT_LIST:
        g.append(prices[p] / R.MARKET_PARAMS[p]["base"] / 2.0)
    for p in PRODUCT_LIST:
        off = (R.MARKET_PARAMS[p]["I0"] - inv[p]) / R.MARKET_PARAMS[p]["T"]
        g.append(max(-3.0, min(3.0, off)) / 3.0)
    for p in PRODUCT_LIST:
        g.append(min(shed.get(p, 0), 60) / 60.0)
    for a in ANIMAL_LIST:
        g.append(min(shed.get(a, 0), 4) / 4.0)
    for c in CROP_LIST:
        g.append(min(seeds.get(c, 0), 20) / 20.0)
    for p in PRODUCT_LIST:
        g.append(min(carried.get(p, 0), 20) / 20.0)
    for q in _QUADS:
        g.append(1.0 if q in mine["unlocked_quadrants"] else 0.0)
    for q in _QUADS:
        g.append(1.0 if q in theirs["unlocked_quadrants"] else 0.0)
    unlocked = obs["town"]["unlocked_shops"]
    for s in SHOP_LIST:
        g.append(unlocked.count(s) / 4.0)
    g.append(len(unlocked) / 8.0)
    hands = mine.get("hands", [])
    inventories = priv["inventories"]
    items = PRODUCT_LIST + ANIMAL_LIST
    for slot in range(A.MAX_HANDS):
        if slot < len(hands):
            x, y = hands[slot]
            hinv = inventories[slot + 1] if slot + 1 < len(inventories) else {}
            g += [1.0, x / (N - 1), y / (N - 1)]
            g += [min(hinv.get(item, 0), 8) / 8.0 for item in items]
        else:
            g += [0.0] * HAND_FEATURES
    return g


def ref_encode(obs):
    me = obs["player"]
    day = obs.get("day", 0)
    boards = np.zeros((2, C, N, N), dtype=np.float32)
    ref_encode_board(obs["farms"][me], boards[0], day)
    ref_encode_board(obs["farms"][1 - me], boards[1], day)
    g = np.asarray(ref_global_features(obs), dtype=np.float32)
    assert g.shape[0] == G, f"global feature drift: {g.shape[0]} != {G}"
    return np.concatenate([boards.reshape(-1), g])


def ref_net_worth(obs):
    me = obs["player"]
    farm = obs["farms"][me]
    priv = obs["private"]
    prices = {p: R.MARKET_PARAMS[p]["base"] for p in PRODUCT_LIST}

    t = obs.get("day", 0) * 24 + obs.get("hour", 0)
    decay = min(1.0, max(0.0, (720.0 - t) / 120.0))

    assets = 0.0
    assets += sum(R.LAND_PRICES[:len(farm["unlocked_quadrants"]) - 1])
    for item, n in priv["shed"].items():
        if n <= 0:
            continue
        if item in R.ANIMALS:
            assets += n * R.ANIMALS[item]["cost"]
        else:
            assets += n * prices[item]
    for c, n in priv["seeds"].items():
        assets += n * R.CROPS[c]["seed"]
    for invd in priv["inventories"]:
        for item, n in invd.items():
            if item in prices:
                assets += n * prices[item]
            elif item in R.ANIMALS:
                assets += n * R.ANIMALS[item]["cost"]
    for y in range(N):
        for x in range(N):
            t = farm["tiles"][y][x]
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "PLANT":
                assets += R.CROPS[t["crop"]]["seed"]
                assets += t.get("yield_units", 0) * prices[t["crop"]]
            elif "animal" in t:
                a = R.ANIMALS[t["animal"]]
                assets += a["cost"]
                assets += t.get("yield_units", 0) * prices[a["product"]]
    return (farm["money"] + 0.5 * min(farm["money"], 800.0)
            + decay * assets)


def ref_opp_visible_worth(obs):
    me = obs["player"]
    farm = obs["farms"][1 - me]
    t = obs.get("day", 0) * 24 + obs.get("hour", 0)
    decay = min(1.0, max(0.0, (720.0 - t) / 120.0))
    assets = float(sum(R.LAND_PRICES[:len(farm["unlocked_quadrants"]) - 1]))
    for y in range(N):
        for x in range(N):
            tile = farm["tiles"][y][x]
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                assets += R.CROPS[tile["crop"]]["seed"]
                assets += tile.get("yield_units", 0) * R.MARKET_PARAMS[tile["crop"]]["base"]
            elif "animal" in tile:
                a = R.ANIMALS[tile["animal"]]
                assets += a["cost"]
                assets += tile.get("yield_units", 0) * R.MARKET_PARAMS[a["product"]]["base"]
    return farm["money"] + decay * assets


_ref_memo_obs = None
_ref_memo_scan = None


def ref_scan(obs):
    global _ref_memo_obs, _ref_memo_scan
    if obs is _ref_memo_obs:
        return _ref_memo_scan
    farm, _priv, _inv, _pos = A._me(obs)
    day = obs.get("day", 0)
    s = {"empty": [], "weeds": [], "unwatered": [], "unfert": [], "harvest": [],
         "unfed": [], "uncared": [], "fert_ready": [],
         "coop_free": [], "pasture_free": []}
    tiles = farm["tiles"]
    for y in range(N):
        row = tiles[y]
        for x in range(N):
            t = row[x]
            if t is None:
                s["empty"].append((x, y))
            elif t == "LOCKED" or not isinstance(t, dict):
                continue
            elif "animal" in t:
                if not t["fed_today"]:
                    s["unfed"].append((x, y))
                if not t["cared_today"]:
                    s["uncared"].append((x, y))
                if t["fertilizer_available"]:
                    s["fert_ready"].append((x, y))
                if t.get("yield_units", 0) > 0:
                    s["harvest"].append((x, y))
            else:
                kind = t.get("kind")
                if kind == "PLANT":
                    if not t["watered_today"]:
                        s["unwatered"].append((x, y))
                    if t.get("fertilized_until_day", -1) < day:
                        s["unfert"].append((x, y))
                    if (t.get("yield_units", 0) > 0
                            and day - t["planted_day"]
                            >= R.CROPS[t["crop"]]["first_yield_day"]):
                        s["harvest"].append((x, y))
                elif kind == "WEED":
                    s["weeds"].append((x, y))
                elif kind == "COOP":
                    s["coop_free"].append((x, y))
                elif kind == "PASTURE":
                    s["pasture_free"].append((x, y))
    _ref_memo_obs, _ref_memo_scan = obs, s
    return s


def ref_farmer_mask(obs):
    farm, priv, inv, (fx, fy) = A._me(obs)
    s = ref_scan(obs)
    day = obs.get("day", 0)
    shed = priv["shed"]
    empties = bool(s["empty"])
    m = np.zeros(A.N_FARMER, dtype=bool)

    def allow(name, ok):
        if ok:
            m[A._F_IDX[name]] = True

    allow("PASS", True)
    allow("MOVE_N", fy > 0)
    allow("MOVE_S", fy < N - 1)
    allow("MOVE_E", fx < N - 1)
    allow("MOVE_W", fx > 0)
    allow("WATER", bool(s["unwatered"]))
    allow("HARVEST", bool(s["harvest"]))
    allow("FEED", bool(s["unfed"])
          and (inv.get("WHEAT", 0) > 0 or shed.get("WHEAT", 0) > 0))
    allow("CARE", bool(s["uncared"]))
    allow("COLLECT_FERT", bool(s["fert_ready"]))
    allow("FERTILIZE", bool(s["unfert"])
          and (inv.get("FERTILIZER", 0) > 0 or shed.get("FERTILIZER", 0) > 0))
    allow("DIG_WEED", bool(s["weeds"]))
    allow("BUILD_COOP", empties)
    allow("BUILD_PASTURE", empties)
    allow("DROP", bool(inv))
    for c in CROP_LIST:
        allow(f"PLANT_{c}", empties and priv["seeds"].get(c, 0) > 0
              and day <= A.PLANT_DEADLINE[c])
    for a in ANIMAL_LIST:
        kind = R.ANIMALS[a]["structure"]
        has = inv.get(a, 0) > 0 or shed.get(a, 0) > 0
        spots = s["coop_free"] if kind == "COOP" else s["pasture_free"]
        allow(f"PLACE_{a}", has and bool(spots))
    return m


def ref_market_mask(obs):
    farm, priv, _inv, _pos = A._me(obs)
    money = farm["money"]
    day = obs.get("day", 0)
    shed = priv["shed"]
    prices = obs["market"]["prices"]
    m = np.zeros(A.N_MARKET, dtype=bool)

    def allow(name, ok):
        if ok:
            m[A._M_IDX[name]] = True

    allow("NOOP", True)
    for p in PRODUCT_LIST:
        allow(f"SELL_{p}", shed.get(p, 0) > 0)
    for c in CROP_LIST:
        allow(f"BUY_SEED_{c}", money >= R.CROPS[c]["seed"]
              and day <= A.PLANT_DEADLINE[c])
    room = sum(shed.values()) < R.SHED_CAPACITY
    allow("BUY_WHEAT", room and money >= prices["WHEAT"] * 5)
    allow("BUY_FERT", room and money >= prices["FERTILIZER"])
    for a in ANIMAL_LIST:
        allow(f"BUY_{a}", room and money >= R.ANIMALS[a]["cost"])
    n_extra = len(farm["unlocked_quadrants"]) - 1
    allow("BUY_LAND",
          n_extra < len(R.LAND_PRICES) and money >= R.LAND_PRICES[n_extra])
    allow("HIRE",
          len(farm.get("hands", [])) < A.MAX_HANDS
          and money >= _fib(farm.get("hires_today", 0)))
    for p in PRODUCT_LIST:
        allow(f"SELL_HALF_{p}", shed.get(p, 0) > 0)
    for c in CROP_LIST:
        allow(f"BUY_SEED_BULK_{c}",
              money >= R.CROPS[c]["seed"] * A.SEED_BULK
              and day <= A.PLANT_DEADLINE[c])
    if day >= R.LIQUIDATE_DAY:
        sellable = [shed.get(p, 0) > 0 for p in PRODUCT_LIST]
        if any(sellable):
            m[:] = False
            m[1:1 + len(PRODUCT_LIST)] = sellable
    return m


def ref_market_action(obs, name):
    farm, priv, _inv, _pos = A._me(obs)
    shed = priv["shed"]
    day = obs.get("day", 0)
    if name == "NOOP":
        return []
    if name.startswith("SELL_HALF_"):
        p = name[len("SELL_HALF_"):]
        if day >= R.LIQUIDATE_DAY:
            first = [["SELL", p, shed[p]]] if shed.get(p, 0) > 0 else []
            rest = [["SELL", q, shed[q]] for q in PRODUCT_LIST
                    if q != p and shed.get(q, 0) > 0]
            return (first + rest)[:R.MAX_ORDERS]
        n = shed.get(p, 0)
        return [["SELL", p, (n + 1) // 2]] if n > 0 else []
    if name.startswith("SELL_"):
        p = name[len("SELL_"):]
        if day >= R.LIQUIDATE_DAY:
            first = [["SELL", p, shed[p]]] if shed.get(p, 0) > 0 else []
            rest = [["SELL", q, shed[q]] for q in PRODUCT_LIST
                    if q != p and shed.get(q, 0) > 0]
            return (first + rest)[:R.MAX_ORDERS]
        n = shed.get(p, 0)
        return [["SELL", p, n]] if n > 0 else []
    if name.startswith("BUY_SEED_BULK_"):
        return [["BUY_SEED", name[len("BUY_SEED_BULK_"):], A.SEED_BULK]]
    if name.startswith("BUY_SEED_"):
        return [["BUY_SEED", name[len("BUY_SEED_"):], 1]]
    if name == "BUY_WHEAT":
        herd = sum(1 for row in farm["tiles"] for t in row
                   if isinstance(t, dict) and "animal" in t)
        return [["BUY_PRODUCT", "WHEAT", max(5, 2 * herd)]]
    if name == "BUY_FERT":
        return [["BUY_PRODUCT", "FERTILIZER", 1]]
    if name.startswith("BUY_") and name[len("BUY_"):] in R.ANIMALS:
        return [["BUY_ANIMAL", name[len("BUY_"):], 1]]
    if name == "BUY_LAND":
        return [["BUY_LAND"]]
    if name == "HIRE":
        n_hands = len(farm.get("hands", []))
        burst, cost_cap = [], 0.05 * farm["money"]
        hires = farm.get("hires_today", 0)
        while (len(burst) < 10 and n_hands + len(burst) < A.MAX_HANDS
               and _fib(hires + len(burst)) <= cost_cap):
            burst.append(["HIRE"])
        return burst or [["HIRE"]]
    return []


def ref_decode(obs, f_idx, m_idx):
    s = ref_scan(obs)
    farmer = A._farmer_action(obs, A.FARMER_ACTIONS[f_idx], s) or ["PASS"]
    return {"farmer": farmer,
            "hands": A._hands_actions(obs, s),
            "market": ref_market_action(obs, A.MARKET_ACTIONS[m_idx])}


# ==========================================================================
# the gate
# ==========================================================================

def new_bundle(raw, f_idx=None, m_idx=None):
    if f_idx is None:
        return (O.encode(raw), A.farmer_mask(raw), A.market_mask(raw),
                O.net_worth(raw), O.opp_visible_worth(raw))
    return A.decode(raw, f_idx, m_idx)


def ref_bundle(raw, f_idx=None, m_idx=None):
    if f_idx is None:
        return (ref_encode(raw), ref_farmer_mask(raw), ref_market_mask(raw),
                ref_net_worth(raw), ref_opp_visible_worth(raw))
    return ref_decode(raw, f_idx, m_idx)


def play_and_compare(seed, rng):
    env = KGEnvNP(opponent="starter")
    raw = env.reset(seed=seed)
    steps, t_new, t_ref = 0, 0.0, 0.0
    while True:
        # Alternate which path runs first so neither always pays the
        # cold-dict / cold-cache cost of touching a fresh obs.
        order = (("new", "ref") if steps % 2 else ("ref", "new"))
        got = {}
        for which in order:
            t0 = time.perf_counter()
            got[which] = new_bundle(raw) if which == "new" else ref_bundle(raw)
            dt = time.perf_counter() - t0
            if which == "new":
                t_new += dt
            else:
                t_ref += dt
        vec, fm, mm, nw, ow = got["new"]
        rvec, rfm, rmm, rnw, row_ = got["ref"]

        assert vec.dtype == rvec.dtype and vec.shape == rvec.shape, \
            f"step {steps}: encode dtype/shape {vec.dtype}{vec.shape} vs {rvec.dtype}{rvec.shape}"
        assert np.array_equal(vec, rvec), \
            f"step {steps}: encode mismatch at {np.flatnonzero(vec != rvec)[:8]}"
        assert np.array_equal(fm, rfm), f"step {steps}: farmer_mask mismatch"
        assert np.array_equal(mm, rmm), f"step {steps}: market_mask mismatch"
        assert nw == rnw, f"step {steps}: net_worth {nw!r} != {rnw!r}"
        assert ow == row_, f"step {steps}: opp_visible_worth {ow!r} != {row_!r}"

        f_idx = int(rng.choice(np.flatnonzero(fm)))
        m_idx = int(rng.choice(np.flatnonzero(mm)))
        got = {}
        for which in order:
            t0 = time.perf_counter()
            got[which] = (new_bundle(raw, f_idx, m_idx) if which == "new"
                          else ref_bundle(raw, f_idx, m_idx))
            dt = time.perf_counter() - t0
            if which == "new":
                t_new += dt
            else:
                t_ref += dt
        assert got["new"] == got["ref"], \
            f"step {steps}: decode({f_idx},{m_idx}) {got['new']} != {got['ref']}"

        raw, done = env.step(got["new"])
        steps += 1
        if done:
            break
    assert steps >= 719, f"episode ended early at step {steps}"
    mine, theirs = env.final_money()
    return steps, t_new, t_ref, mine, theirs


def land_transition_gate(seed=7):
    """channel 1 (locked) is block-written from unlocked_quadrants instead of
    tile by tile, resting on the engine invariant LOCKED <=> quadrant not
    unlocked. The random policy is not guaranteed to ever afford BUY_LAND, so
    this deterministic buyer pins the unlock transitions into the gate."""
    buy_land = A.MARKET_ACTIONS.index("BUY_LAND")
    noop = A.MARKET_ACTIONS.index("NOOP")
    env = KGEnvNP(opponent="starter")
    raw = env.reset(seed=seed)
    unlocks = 0
    for step in range(720):
        before = len(raw["farms"][raw["player"]]["unlocked_quadrants"])
        assert np.array_equal(O.encode(raw), ref_encode(raw)), \
            f"land gate: encode mismatch step {step}"
        assert np.array_equal(A.farmer_mask(raw), ref_farmer_mask(raw)), \
            f"land gate: farmer_mask mismatch step {step}"
        assert O.net_worth(raw) == ref_net_worth(raw), \
            f"land gate: net_worth mismatch step {step}"
        m_idx = buy_land if A.market_mask(raw)[buy_land] else noop
        raw, done = env.step(A.decode(raw, 0, m_idx))
        unlocks += len(raw["farms"][raw["player"]]["unlocked_quadrants"]) != before
        if done:
            break
    assert unlocks >= 1, "land gate never exercised a quadrant unlock"
    print(f"land-transition gate: {unlocks} quadrant unlocks, "
          f"every step byte-identical")


def main():
    rng = np.random.default_rng(0)
    tot_steps, tot_new, tot_ref = 0, 0.0, 0.0
    for seed in (3111, 3112):
        steps, t_new, t_ref, mine, theirs = play_and_compare(seed, rng)
        tot_steps += steps
        tot_new += t_new
        tot_ref += t_ref
        print(f"seed {seed}: {steps} steps, every step byte-identical | "
              f"final money me {mine:,.0f} opp {theirs:,.0f} | "
              f"per-step old {t_ref / steps * 1e3:.3f} ms  "
              f"new {t_new / steps * 1e3:.3f} ms  "
              f"speedup x{t_ref / t_new:.2f}")
    print(f"\nTOTAL {tot_steps} steps | old path {tot_ref:.2f} s "
          f"({tot_ref / tot_steps * 1e3:.3f} ms/step) | new path {tot_new:.2f} s "
          f"({tot_new / tot_steps * 1e3:.3f} ms/step) | "
          f"speedup x{tot_ref / tot_new:.2f}")
    land_transition_gate()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("FUSED-FAIL")
        sys.exit(1)
    print("FUSED-PASS")
