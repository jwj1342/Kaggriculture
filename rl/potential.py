"""Potential function for reward shaping.

Φ(s) estimates the expected end-of-game net worth from state s.
The env uses r' = (Φ_rel(s') − Φ_rel(s)) / 1000, plus ±15 at episode end.
Φ already estimates undiscounted terminal wealth, so the shaping term is
undiscounted (Ng et al. 1999 with γ_Φ=1). The RL discount γ=0.997 applies
to these shaped rewards.

Plant credits used to dominate (melon plant ~$750 vs a placed cow ~$700),
so PPO learned to spam PLANT_TOMATO / HARVEST and skip the herd. Animals
are now priced above plants: a day-0 cow is ~$1.9k, a melon plant ~$375,
a tomato plant ~$60. Shed livestock count at 85% of purchase cost so
BUY_ANIMAL is no longer a −$400 hole that the market head learns to HOLD
through.

Pure stdlib so it can be embedded verbatim in the exported single-file agent.
Keep gpu/obs.py farm_phi and tensor_env/potential_future.py on these same
named credits.
"""

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["COW", "SHEEP", "GOOSE"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

BASE_PRICE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
              "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}

CROP_DATA = {
    "WHEAT":      {"seed": 10,  "first_yield_day": 2,  "max_yield": 6,  "ongoing": False, "interval": 0},
    "CARROT":     {"seed": 20,  "first_yield_day": 2,  "max_yield": 4,  "ongoing": False, "interval": 0},
    "TOMATO":     {"seed": 50,  "first_yield_day": 8,  "max_yield": 4,  "ongoing": True,  "interval": 1},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield": 4,  "ongoing": True,  "interval": 2},
    "MELON":      {"seed": 80,  "first_yield_day": 10, "max_yield": 6,  "ongoing": False, "interval": 0},
}
ANIMAL_DATA = {
    "GOOSE": {"cost": 300, "product": "EGG",  "max_held": 4, "first_yield_day": 4, "interval": 1},
    "COW":   {"cost": 400, "product": "MILK", "max_held": 6, "first_yield_day": 8, "interval": 2},
    "SHEEP": {"cost": 500, "product": "WOOL", "max_held": 6, "first_yield_day": 6, "interval": 3},
}
SEED_COST = {c: d["seed"] for c, d in CROP_DATA.items()}

# Named credits: gpu/obs.py and tensor_env/potential_future.py import these.
SHED_DISCOUNT = 0.9
SEED_RESIDUAL = 0.5
PLANT_CREDIT = 0.25
ANIMAL_CREDIT = 0.9
SHED_ANIMAL_CREDIT = 0.85
HERD_ASSET = 200.0
HOUSING_VALUE = 80.0
UNFED_RISK = 0.8
UNCARED_RISK = 0.3
WATER_STRESS = 0.15
WEED_COST = 25.0
HAND_VALUE = 40.0
LAND_VALUE = 300.0
SEASON_DAYS = 30
PHI_SCALE = 1000.0
TERMINAL_BONUS = 15.0


def _get(d, k, default=None):
    if isinstance(d, dict):
        return d.get(k, default)
    return getattr(d, k, default)


def _safe(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)


def _remaining_expected_yield(tile, crop, day=0):
    """Expected remaining harvest units for a planted tile.

    Ongoing (TOMATO/STRAWBERRY): remaining production events that still fit
    in the season, capped at max_yield (doc: days_left / interval, then cap).
    One-shot (WHEAT/CARROT/MELON): full max_yield while the plant still exists.
    """
    data = CROP_DATA[crop]
    sitting = _safe(tile.get("yield_units"))
    if data["ongoing"]:
        interval = max(1, int(data.get("interval") or 1))
        planted = int(tile.get("planted_day") or 0)
        first = int(data.get("first_yield_day") or 0)
        start = max(int(day), planted + first)
        if start > SEASON_DAYS:
            return sitting
        remaining_events = 1.0 + (SEASON_DAYS - start) / float(interval)
        days_since_first = int(day) - planted - first
        produced = 0.0
        if days_since_first >= 0:
            produced = float(min(data["max_yield"], days_since_first // interval + 1))
        remaining_cap = max(0.0, float(data["max_yield"]) - produced)
        return sitting + min(remaining_cap, remaining_events)
    return float(data["max_yield"])


def _remaining_animal_yield(tile, animal, day=0):
    """Held units plus expected remaining production events this season."""
    d = ANIMAL_DATA[animal]
    held = _safe(tile.get("yield_units"))
    interval = max(1, int(d.get("interval") or 1))
    placed = int(tile.get("placed_day") or 0)
    first = int(d.get("first_yield_day") or 0)
    start = max(int(day), placed + first)
    if start > SEASON_DAYS:
        return held
    remaining_events = 1.0 + (SEASON_DAYS - start) / float(interval)
    return held + remaining_events


def farm_potential(farm, priv, day=0):
    """Φ for one farm (mine or opponent's). Unit: dollars."""
    phi = _safe(_get(farm, "money"))

    shed = _get(priv, "shed") or {}
    for item in PRODUCTS:
        phi += _safe(shed.get(item)) * BASE_PRICE[item] * SHED_DISCOUNT
    for animal in ANIMALS:
        phi += _safe(shed.get(animal)) * ANIMAL_DATA[animal]["cost"] * SHED_ANIMAL_CREDIT

    seeds = _get(priv, "seeds") or {}
    for crop in CROPS:
        phi += _safe(seeds.get(crop)) * SEED_COST[crop] * SEED_RESIDUAL

    tiles = _get(farm, "tiles") or []
    for row in tiles:
        for t in (row or []):
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                crop = t.get("crop")
                if crop in CROPS:
                    stress = 0.0
                    if not t.get("watered_today") and _safe(t.get("consecutive_unwatered")) >= 1:
                        stress = WATER_STRESS
                    phi += (
                        _remaining_expected_yield(t, crop, day)
                        * BASE_PRICE[crop] * PLANT_CREDIT * (1.0 - stress)
                    )
            elif kind in ("PASTURE", "COOP"):
                animal = t.get("animal")
                if animal in ANIMALS:
                    d = ANIMAL_DATA[animal]
                    phi += (
                        _remaining_animal_yield(t, animal, day)
                        * BASE_PRICE[d["product"]] * ANIMAL_CREDIT
                    )
                    phi += HERD_ASSET
                    if not t.get("fed_today"):
                        phi -= d["cost"] * UNFED_RISK
                    if not t.get("cared_today"):
                        phi -= d["cost"] * UNCARED_RISK
                else:
                    phi += HOUSING_VALUE
            elif kind == "WEED":
                phi -= WEED_COST

    phi += len(_get(farm, "hands") or []) * HAND_VALUE
    phi += (len(_get(farm, "unlocked_quadrants") or ["NW"]) - 1) * LAND_VALUE
    return phi


def relative_potential(obs):
    """Φ(mine) − Φ(opp). Positive means we are ahead."""
    player = int(_get(obs, "player") or 0)
    farms = _get(obs, "farms") or []
    day = int(_get(obs, "day") or 0)
    mine = farm_potential(farms[player], _get(obs, "private") or {}, day)
    if len(farms) > 1:
        # opponent's shed is hidden; approximate from public info only
        opp_priv = {"shed": {}, "seeds": {}}
        theirs = farm_potential(farms[1 - player], opp_priv, day)
    else:
        theirs = 0.0
    return mine - theirs


def shaped_reward(obs_prev, obs_curr, done=False, phi_prev=None):
    """Potential-based shaping used by the env.

    r' = (Φ_rel(s') − Φ_rel(s)) / 1000, plus ±15 at episode end.
    Φ already estimates undiscounted terminal net worth, so the shaping
    term is undiscounted (using γ here would add a (γ−1)Φ penalty that
    punishes being rich). The RL discount γ=0.997 applies to these r'.
    """
    if phi_prev is None:
        phi_prev = relative_potential(obs_prev) if obs_prev is not None else 0.0
    phi_curr = relative_potential(obs_curr)
    r = (phi_curr - phi_prev) / PHI_SCALE
    if done:
        player = int(_get(obs_curr, "player") or 0)
        farms = _get(obs_curr, "farms") or []
        mine = farms[player] if player < len(farms) else {}
        opp = farms[1 - player] if len(farms) > 1 else {}
        my_m = _safe(_get(mine, "money"))
        opp_m = _safe(_get(opp, "money"))
        if my_m > opp_m:
            r += TERMINAL_BONUS
        elif my_m < opp_m:
            r -= TERMINAL_BONUS
    return float(r), float(phi_curr)
