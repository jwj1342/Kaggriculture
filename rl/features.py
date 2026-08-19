"""Observation encoder for Kaggriculture RL.

Converts a kaggle-environments observation Struct/dict into a flat list of
floats in [-1, 1] (roughly). This module must stay pure-stdlib so it can be
copied verbatim into the exported single-file submission agent.
"""

import math

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["COW", "SHEEP", "GOOSE"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def _get(d, k, default=None):
    if isinstance(d, dict):
        return d.get(k, default)
    return getattr(d, k, default)


def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)


def encode(obs):
    player = int(_get(obs, "player") or 0)
    farms = _get(obs, "farms") or []
    my = farms[player] if player < len(farms) else {}
    opp = farms[1 - player] if len(farms) > 1 - player else {}
    priv = _get(obs, "private") or {}
    market = _get(obs, "market") or {}
    town = _get(obs, "town") or {}

    day = int(_get(obs, "day") or 0)
    hour = int(_get(obs, "hour") or 0)
    step = int(_get(obs, "step") or 0)

    def nrm(x, scale):
        return _clamp(_safe_float(x) / _safe_float(scale))

    def logn(x, cap):
        return _clamp(math.log1p(max(0.0, _safe_float(x))) / math.log1p(float(cap)))

    def logdiff(a, b, cap):
        return _clamp(math.log1p(max(0.0, _safe_float(a) - _safe_float(b))) / math.log1p(float(cap)))

    def norm_angle(t, period):
        p = float(period) if period else 1.0
        a = 2.0 * math.pi * (float(t) / p)
        return math.sin(a), math.cos(a)

    # phase features
    f = list(norm_angle(day, 30))
    f += list(norm_angle(hour, 24))
    f.append(nrm(step, 720))

    # money + units
    f.append(logn(_get(my, "money", 0), 200000))
    f.append(nrm(len(_get(my, "hands") or []), 12))
    f.append(nrm(len(_get(my, "unlocked_quadrants") or []), 4))

    # per crop: planted, harvestable, needs water
    tiles = _get(my, "tiles") or []
    planted = {c: 0 for c in CROPS}
    harvestable = {c: 0 for c in CROPS}
    needs_water = {c: 0 for c in CROPS}
    for row in tiles:
        for t in (row or []):
            if not isinstance(t, dict):
                continue
            k = t.get("kind")
            if k == "PLANT":
                crop = t.get("crop")
                if crop in planted:
                    planted[crop] += 1
                    if t.get("yield_units", 0) > 0:
                        harvestable[crop] += 1
                    if not t.get("watered_today"):
                        needs_water[crop] += 1
    for c in CROPS:
        f.append(nrm(planted[c], 40))
        f.append(nrm(harvestable[c], 20))
        f.append(nrm(needs_water[c], 30))

    # per animal: placed, unfed, uncared, fert_available
    placed_a = {a: 0 for a in ANIMALS}
    unfed = {a: 0 for a in ANIMALS}
    uncared = {a: 0 for a in ANIMALS}
    fert_avail = {a: 0 for a in ANIMALS}
    for row in tiles:
        for t in (row or []):
            if not isinstance(t, dict) or "animal" not in t:
                continue
            animal = t.get("animal")
            if animal in placed_a:
                placed_a[animal] += 1
                if not t.get("fed_today"):
                    unfed[animal] += 1
                if not t.get("cared_today"):
                    uncared[animal] += 1
                if t.get("fertilizer_available"):
                    fert_avail[animal] += 1
    for a in ANIMALS:
        f.append(nrm(placed_a[a], 20))
        f.append(nrm(unfed[a], 10))
        f.append(nrm(uncared[a], 10))
        f.append(nrm(fert_avail[a], 10))

    # weeds + empty unlocked
    weeds = 0
    empty_unlocked = 0
    for row in tiles:
        for t in (row or []):
            if not isinstance(t, dict):
                if t is None:
                    empty_unlocked += 1
            elif t.get("kind") == "WEED":
                weeds += 1
    f.append(nrm(weeds, 50))
    f.append(nrm(empty_unlocked, 60))

    # shed + seeds
    shed = _get(priv, "shed") or {}
    seeds = _get(priv, "seeds") or {}
    for item in PRODUCTS:
        f.append(logn(shed.get(item, 0), 100))
    for crop in CROPS:
        f.append(logn(seeds.get(crop, 0), 20))

    # market
    prices = _get(market, "prices") or {}
    inv = _get(market, "inventory") or {}
    for item in PRODUCTS:
        base = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
                "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}.get(item, 100)
        f.append(nrm(_safe_float(prices.get(item, 0)) / _safe_float(base) - 1.0, 2.0))
    for item in PRODUCTS:
        f.append(logn(inv.get(item, 0), 20000))

    # town
    f.append(nrm(len(_get(town, "unlocked_shops") or []), 8))

    # opponent summary
    opp_money = _get(opp, "money") or 0
    f.append(logdiff(opp_money, _get(my, "money", 0), 200000))
    f.append(nrm(len(_get(opp, "hands") or []), 12))
    f.append(nrm(len(_get(opp, "unlocked_quadrants") or []), 4))
    opp_tiles = _get(opp, "tiles") or []
    opp_crops = 0
    opp_animals = 0
    for row in opp_tiles:
        for t in (row or []):
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    opp_crops += 1
                if "animal" in t:
                    opp_animals += 1
    f.append(nrm(opp_crops, 40))
    f.append(nrm(opp_animals, 20))

    return [float(v) for v in f]


FEATURE_DIM = len(encode({
    "player": 0,
    "farms": [{"farmer": [0, 0], "hands": [], "tiles": [[None] * 10 for _ in range(10)],
               "unlocked_quadrants": ["NW"], "money": 3000},
              {"farmer": [0, 0], "hands": [], "tiles": [[None] * 10 for _ in range(10)],
               "unlocked_quadrants": ["NW"], "money": 3000}],
    "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
    "market": {"inventory": {"WHEAT": 10000, "CARROT": 10000, "TOMATO": 10000,
                             "STRAWBERRY": 10000, "MELON": 10000,
                             "EGG": 10000, "MILK": 10000, "WOOL": 10000, "FERTILIZER": 10000},
               "prices": {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
                          "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}},
    "town": {"unlocked_shops": []},
    "day": 0, "hour": 0, "step": 0,
}))
