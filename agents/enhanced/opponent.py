"""Reading the opponent, and deciding what that means for selling.

The opponent's whole board is public: every plant's `planted_day`, every animal's
`placed_day`, `yield_units`, `fed_today` and `pending_care_bonus`. Their harvest
schedule is therefore *computable*, not guessable. What is hidden is their shed,
their carried inventory and their queued orders.

Market inventory is shared and visible, and town consumption is deterministic
given the unlocked shops, so subtracting our own fills from the inventory delta
recovers what the opponent actually sold each turn. That is a measurement, not
an inference.

The one thing an earlier version of this got wrong, and this one does not:
**front-running is only correct when the pool does not regenerate.** Selling into
a product the town consumes heavily is not a race -- the price recovers. Selling
into melon, which no shop demands, is a pure race. The rule below weighs the
opponent's imminent supply against the town's refill rate instead of reacting to
supply alone.
"""

from engine import (ANIMALS, CROPS, MARKET_PARAMS, PRODUCTS, SEASON_DAYS,
                    price, town_rate, units_to_floor)

BASE = {k: v["base"] for k, v in MARKET_PARAMS.items()}

HORIZON = 3          # days ahead counted as "imminent"


def forecast(opp_farm, day):
    """What the opponent can sell now, and what their board will produce soon.

    Returns (ready, imminent, capacity) keyed by product:
      ready     units already harvestable on their tiles
      imminent  units their board will produce within HORIZON days
      capacity  what their board is built to produce at all
    """
    ready = {p: 0.0 for p in PRODUCTS}
    imminent = {p: 0.0 for p in PRODUCTS}
    capacity = {p: 0.0 for p in PRODUCTS}

    for row in (opp_farm.get("tiles") or []):
        for t in row:
            if not isinstance(t, dict):
                continue

            if t.get("kind") == "PLANT":
                crop = t.get("crop")
                if crop not in CROPS:
                    continue
                cd = CROPS[crop]
                age = day - int(t.get("planted_day", day))
                units = int(t.get("yield_units", 0) or 0)
                capacity[crop] += cd["max_yield"]
                if age >= cd["first_yield_day"]:
                    ready[crop] += units
                elif age + HORIZON >= cd["first_yield_day"]:
                    # One-shot crops dump their whole yield at once; ongoing ones
                    # trickle. Weight accordingly.
                    imminent[crop] += cd["max_yield"] if not cd["ongoing"] else 1

            elif "animal" in t:
                a = t.get("animal")
                if a not in ANIMALS:
                    continue
                ad = ANIMALS[a]
                prod = ad["product"]
                capacity[prod] += ad["max_held"]
                ready[prod] += int(t.get("yield_units", 0) or 0)
                age = day - int(t.get("placed_day", day))
                if age + HORIZON >= ad["first_yield_day"]:
                    # Steady-state rate, tripled if they are running CARE.
                    per_day = 1.0 / max(1, ad["interval"])
                    if t.get("cared_today") or t.get("pending_care_bonus"):
                        per_day *= 2.0
                    imminent[prod] += per_day * HORIZON
                if t.get("fertilizer_available"):
                    ready["FERTILIZER"] += 1
                capacity["FERTILIZER"] += 1

    return ready, imminent, capacity


class SellTracker:
    """Infers the opponent's realised sell rate from shared market inventory.

    inventory delta = our sells + their sells - town drain - buys

    We know our own submitted orders and the town drain exactly, so the residual
    is theirs. Sales at the $1 floor do not raise inventory, so this
    under-counts a fully crashed product -- which is fine, since nothing more can
    be taken from it anyway.
    """

    def __init__(self):
        self.prev_inv = None
        self.pending = {}
        self.sold = {p: 0.0 for p in PRODUCTS}
        self.steps = 0

    def update(self, m_inv, shops, step):
        if self.prev_inv is not None:
            drain = town_rate(shops)
            per_step = {p: v / 24.0 for p, v in drain.items()}
            for p in PRODUCTS:
                delta = m_inv.get(p, 0) - self.prev_inv.get(p, 0)
                theirs = delta - self.pending.get(p, 0) + per_step[p]
                if theirs > 0:
                    self.sold[p] += theirs
        self.prev_inv = dict(m_inv)
        self.steps = max(1, step)

    def rate(self, product):
        """Their observed sells per day for this product."""
        return self.sold.get(product, 0.0) * 24.0 / max(1, self.steps)

    def total_rate(self):
        return sum(self.sold.values()) * 24.0 / max(1, self.steps)


def sell_plan(item, held, m_inv, day, shops, opp_ready, opp_imminent,
              tracker, endgame=False, batch=8):
    """How many units of `item` to sell this turn, and why.

    The decision is between taking price now and taking it later. Later is worse
    by exactly the amount the opponent sells in between, and better by the amount
    the town consumes in between. So compare those two.
    """
    if held <= 0:
        return 0, "none"
    inv = m_inv.get(item, 10000)
    now = price(item, inv)

    if endgame:
        return min(held, 40), "liquidate"

    # Fertilizer has no consumer at all: its inventory only rises and its price
    # only falls, so holding it is strictly a loss. Always sell.
    rate = town_rate(shops)[item]
    if rate <= 0:
        return min(held, batch * 2), "one-way"

    headroom = units_to_floor(item, inv)          # units left before the $1 floor
    days_left = max(1, SEASON_DAYS - day)
    refill = rate * days_left                     # units the town will absorb
    threat = opp_ready.get(item, 0) + opp_imminent.get(item, 0)
    threat += tracker.rate(item) * min(HORIZON, days_left)

    # If what they are about to push exceeds what the town will take back, the
    # remaining headroom is a race and the first seller wins it. Otherwise the
    # pool regenerates and patience costs nothing.
    contested = threat > refill * 0.5 and headroom < threat + held

    base = BASE[item]
    if contested:
        # Take our share before it evaporates, but never sell below what the
        # price would be after they dump -- that is giving it away.
        after = price(item, inv + int(min(threat, headroom)))
        floor = max(after, base * 0.30)
        size = batch * 2
        why = "contested"
    else:
        floor = base * 0.55
        size = batch
        why = "metered"

    if now < floor:
        return 0, why + "-hold"

    n = 0
    limit = min(size, held)
    while n < limit and price(item, inv + n) >= floor:
        n += 1
    return n, why
