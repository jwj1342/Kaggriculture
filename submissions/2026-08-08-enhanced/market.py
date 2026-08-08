"""Market orders: hiring, land, livestock, seeds, feed, and sales.

Three of the four bugs this baseline was built to fix live here.

**Opening starvation.** The previous agent bought animals it could not feed:
three of the first five starved inside three days and the farm then idled for
eight more with empty pens, because cash was $211 on day 5. Livestock is now
gated on *feed solvency* -- an animal is only bought when the herd's feed is
already covered for FEED_DAYS_REQUIRED days and the purchase still leaves enough
to keep buying wheat.

**Melon oversold.** 21% of episodes kept selling melon after the price had
bottomed at $1. Sale sizing now comes from `opponent.sell_plan`, which never
sells below a floor derived from the post-dump price.

**Not a bug, recorded so it is not "fixed" again:** an earlier note claimed HIRE
orders flooded the market queue with unaffordable requests. Measured, both this
agent and its predecessor hire at a **100% success rate** -- 266 orders, 266
hands. The claim came from a public meta write-up describing *other* players and
was never checked against ours. Hiring is still budget-capped, because fib(n)
explodes, but not for queue-pressure reasons.
"""

from engine import (ANIMALS, CROPS, LAND_PRICES, MAX_ORDERS, PRODUCTS,
                    SHED_CAPACITY, fib, payroll, price)
from opponent import sell_plan

FEED_DAYS_REQUIRED = 3      # days of feed the herd must already have covered
WHEAT_PER_ANIMAL = 2        # target shed reserve per animal
WHEAT_RESERVE_CAP = 28      # more than this just clogs the 100-slot shed


def hire_orders(farm, money, spent, plan, hour):
    """How many hands to hire this turn, and what they cost.

    The n-th hire of a day costs fib(n): the first eight together are cheaper
    than one melon seed, but the 17th alone costs more than the first fifteen
    combined. Measured, `crew` (11 hands on 6% of cash) wins 55% of the time and
    `swarm` (30 hands, no cap) wins 10% -- worse than never hiring at all.

    Only orders we can actually pay for are issued, so the market queue is never
    filled with hires that will bounce.
    """
    if hour > 3 or plan["hands"] <= 0:
        return [], 0.0
    hires = int(farm.get("hires_today", 0) or 0)
    spent_so_far = payroll(hires)
    budget = max(4.0, money * plan["hire_frac"])
    orders, cost = [], 0.0
    while len(orders) < 7 and hires < plan["hands"]:
        c = fib(hires)
        if spent_so_far + c > budget:
            break
        if money - spent - cost - c < 40:
            break
        orders.append(["HIRE"])
        cost += c
        spent_so_far += c
        hires += 1
    return orders, cost


def feed_reserve(view, shed, invs, plan, day):
    """Wheat the herd needs kept back, counted once.

    Two call sites need this number -- the buyer, to decide whether to top up,
    and the seller, to decide what is surplus. An earlier version computed it
    differently in each place: the seller used only *placed* animals, so wheat
    bought for a herd still sitting in the shed looked like surplus and was sold
    straight back. The result was a buy/sell loop that burned $3,000 down to $299
    in eight turns while stockpiling four unplaced cows, which then starved.

    So it counts every mouth we have committed to: placed, in the shed, being
    carried, and the next couple we intend to buy.
    """
    placed = len(view["animals"])
    pending = sum(shed.get(a, 0) for a in ANIMALS)
    pending += sum(iv.get(a, 0) for iv in invs for a in ANIMALS)
    target = sum(plan["animals"].values())
    committed = placed + pending
    if day <= 23 and committed < target:
        committed = min(target, committed + 2)      # the next purchases
    return min(WHEAT_RESERVE_CAP, committed * WHEAT_PER_ANIMAL)


def feed_solvent(shed, n_animals):
    """Is the feed for the enlarged herd already **in the shed**?

    An animal eats one wheat a day and returns nothing until day 4 at the
    earliest (goose) or day 8 (cow), and it escapes after two unfed days. An
    earlier version asked whether the wheat was *affordable* rather than whether
    it was *present*, and bought four animals on day 0 against an empty shed:
    two had starved by day 2 and the farm then idled for eight days with empty
    pens. Affordability is not possession -- the wheat has to be there.
    """
    return shed.get("WHEAT", 0) >= (n_animals + 1) * FEED_DAYS_REQUIRED


def build_orders(ctx):
    """Every market order for this turn, in priority order, capped at ten."""
    (farm, priv, plan, view, day, hour, money, m_inv, shops,
     endgame, tracker, opp_ready, opp_imminent) = (
        ctx["farm"], ctx["priv"], ctx["plan"], ctx["view"], ctx["day"],
        ctx["hour"], ctx["money"], ctx["m_inv"], ctx["shops"],
        ctx["endgame"], ctx["tracker"], ctx["opp_ready"], ctx["opp_imminent"])

    shed = ctx["shed"]
    seeds = ctx["seeds"]
    invs = ctx["invs"]
    shed_total = sum(shed.values())
    n_animals = len(view["animals"])
    reserve = feed_reserve(view, shed, invs, plan, day)
    orders, spent = [], 0.0
    submitted = {p: 0 for p in PRODUCTS}

    def afford(c):
        return money - spent >= c

    if not endgame:
        h, cost = hire_orders(farm, money, spent, plan, hour)
        orders += h
        spent += cost

        wheat_price = price("WHEAT", m_inv.get("WHEAT", 10000) - 1)

        # --- land: only when there is nothing left to plant and cash is easy ---
        unlocked = farm.get("unlocked_quadrants", ["NW"]) or ["NW"]
        n_extra = len(unlocked) - 1
        crop_room = sum(1 for p in view["free"])
        if (n_extra < min(len(LAND_PRICES), plan["land"] - 1)
                and len(orders) < MAX_ORDERS and crop_room <= 4):
            cost = LAND_PRICES[n_extra]
            if afford(cost + [1200, 2500, 4000][n_extra]):
                orders.append(["BUY_LAND"])
                spent += cost

        # --- feed first, always. The herd cannot be bought before the wheat
        #     exists, so the wheat has to be bought before the herd. ---
        need_w = reserve
        if n_animals == 0 and day <= 23 and sum(plan["animals"].values()):
            need_w = max(need_w, FEED_DAYS_REQUIRED * 2)
        if (len(orders) < MAX_ORDERS and need_w
                and shed.get("WHEAT", 0) < need_w
                and shed_total < SHED_CAPACITY - 10):
            k = min(10, need_w - shed.get("WHEAT", 0))
            if k > 0 and afford(wheat_price * k + 150):
                orders.append(["BUY_PRODUCT", "WHEAT", k])
                spent += wheat_price * k

        # --- livestock: gated on housing AND on feed already in the shed ---
        waiting = sum(shed.get(a, 0) for a in ANIMALS)
        target = sum(plan["animals"].values())
        housed = n_animals + len(view["empty_structs"])
        if (len(orders) < MAX_ORDERS and day <= 23 and waiting < 2
                and n_animals + waiting < target
                and housed <= target
                and shed_total < SHED_CAPACITY - 8):
            owned_of = {a: view["counts"][a] + shed.get(a, 0) for a in ANIMALS}
            want = next((a for a in ("COW", "SHEEP", "GOOSE")
                         if owned_of[a] < plan["animals"].get(a, 0)), None)
            if want:
                cost = ANIMALS[want]["cost"]
                # Keep enough to buy feed for the enlarged herd, not a flat
                # constant -- that constant is what starved the opening.
                keep = (n_animals + 1) * FEED_DAYS_REQUIRED * wheat_price
                if afford(cost + keep) and feed_solvent(shed, n_animals):
                    orders.append(["BUY_ANIMAL", want, 1])
                    spent += cost

        # --- seeds: only what there is a free tile for, and only what the
        #     market can still absorb ---
        for crop, target_tiles in plan["crops"]:
            if len(orders) >= MAX_ORDERS or crop_room <= 0:
                continue
            if day > plan["last_plant"][crop]:
                continue
            have = view["crops"].get(crop, 0) + seeds.get(crop, 0)
            if have >= target_tiles:
                continue
            cost1 = CROPS[crop]["seed"]
            k = min(4, target_tiles - have, crop_room)
            if k > 0 and afford(cost1 * k + 200):
                orders.append(["BUY_SEED", crop, k])
                spent += cost1 * k
                crop_room -= k

    # --- sales -------------------------------------------------------------
    sellable = []
    for item in PRODUCTS:
        held = shed.get(item, 0)
        if held <= 0:
            continue
        if item == "WHEAT" and not endgame:
            held = max(0, held - reserve)
            if held <= 0:
                continue
        inv0 = m_inv.get(item, 10000)
        threat = opp_ready.get(item, 0) + opp_imminent.get(item, 0)
        sellable.append((price(item, inv0) * min(held, 8) + threat * 40,
                         item, held))
    sellable.sort(reverse=True)

    pressure = shed_total >= 74
    for (_, item, held) in sellable:
        if len(orders) >= MAX_ORDERS:
            break
        qty, _why = sell_plan(item, held, m_inv, day, shops, opp_ready,
                              opp_imminent, tracker, endgame=endgame)
        if qty == 0 and pressure:
            # The shed discards overflow at end of day, so a full shed forces a
            # sale regardless of price.
            qty = min(held, 8)
        if qty > 0:
            orders.append(["SELL", item, qty])
            submitted[item] += qty

    return orders[:MAX_ORDERS], submitted
