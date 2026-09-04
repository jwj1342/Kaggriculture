#!/usr/bin/env python
"""The sell side as a scheduling problem: economics, a fill trace, and the bound.

    python tools/liquidate.py econ
    python tools/liquidate.py trace A.py B.py --seed 123 --out fills.jsonl
    python tools/liquidate.py bound fills.jsonl --seat 0

WHY. The market is a single shared book per product. Selling raises that
product's inventory by one unit per unit sold (`_commit_unit`, and NOT when
the price has already floored at $1), and price falls in inventory. So a
sale is a permanent price concession -- against BOTH players, since the book
is shared.

But the book also RECOVERS, and that is the fact that makes timing worth
anything at all: `_town_consume` draws inventory DOWN every
`townShopSellInterval` (4) steps, once per unlocked shop instance per product
it sells (x2 for a single-product shop), plus 1 per day per product from the
town centre. So each product has a sustainable rate, and the sell problem is
"liquidate a known arrival stream into a book with finite resilience" --
optimal execution with transient impact, not a policy-learning problem.

The economics table (`econ`) is the whole reason this line exists: the four
high-base products collapse inside 59-158 units while the four cheap ones
barely move across 400. So the money is entirely in metering MELON, WOOL,
MILK and STRAWBERRY, and MELON has no shop at all -- its only demand is the
town centre's 1/day.

`bound` is deliberately an UPPER bound and not a strategy: it re-solves our
own fills with perfect foresight of the opponent's flow and of our own
arrivals. If the bound over a realised episode is small, this line is dead
without writing a controller; if it is large, the bound is what a controller
is chasing and the gap to it is the controller's error.
"""

import argparse
import collections
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def engine():
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    return K


# ------------------------------------------------------------------ econ ----

def cmd_econ(args):
    K = engine()
    print("resilience -- how fast the book recovers (per DAY of 24 steps;\n"
          "shops fire every 4 steps = 6 times a day, single-product x2)")
    for shop, prods in sorted(K.SHOPS.items()):
        m = 2 if len(prods) == 1 else 1
        print(f"  {shop:16} " + ", ".join(f"{p} {6*m}" for p in prods))
    print(f"  TOWN_CENTRE      " + ", ".join(f"{p} 1" for p in K.TOWN_CENTER_PRODUCTS))
    print(f"  (up to {K.MAX_SHOP_INSTANCES} instances, drawn WITH replacement "
          f"from the same RNG stream as the weeds)")

    ks = (10, 25, 50, 100, 200, 400)
    print("\nprice after selling k units into a book that starts at I0 "
          f"({K.MARKET_I0})")
    hdr = (f"{'product':11}{'base':>6}{'shape':>8}{'T':>6}{'tgt':>6}  "
           + "".join(f"{k:>7}" for k in ks) + f"{'half at':>9}{'$1 at':>7}"
           + f"{'max/day':>9}")
    print(hdr); print("-" * len(hdr))
    for p in K.PRODUCTS:
        q = K.MARKET_PARAMS[p]
        half = next((k for k in range(1, 4001)
                     if K.market_price(p, K.MARKET_I0 + k) <= q["base"] // 2), None)
        dead = next((k for k in range(1, 4001)
                     if K.market_price(p, K.MARKET_I0 + k) <= 1), None)
        cons = max([6 * (2 if len(v) == 1 else 1) for v in K.SHOPS.values()
                    if p in v] + [0]) + (1 if p in K.TOWN_CENTER_PRODUCTS else 0)
        print(f"{p:11}{q['base']:6d}{q['above_func']:>8}{q['T']:6d}"
              f"{q['above_target']:6.2f}  "
              + "".join(f"{K.market_price(p, K.MARKET_I0 + k):7d}" for k in ks)
              + f"{str(half):>9}{str(dead):>7}{cons:>9}")
    print("\nrevenue for N units, dumped at once vs metered at the sustainable "
          "rate\n(metered assumes the book is held at I0, i.e. sales <= "
          "consumption; it is an ideal, not a plan)")
    print(f"{'product':11}{'N':>5}{'dumped':>10}{'metered':>10}{'swing':>10}"
          f"{'days needed':>13}")
    for p, N in (("MELON", 100), ("WOOL", 200), ("MILK", 150),
                 ("STRAWBERRY", 150), ("TOMATO", 300), ("WHEAT", 400)):
        base = K.MARKET_PARAMS[p]["base"]
        cons = max([6 * (2 if len(v) == 1 else 1) for v in K.SHOPS.values()
                    if p in v] + [0]) + (1 if p in K.TOWN_CENTER_PRODUCTS else 0)
        inv, dumped = K.MARKET_I0, 0
        for _ in range(N):
            pr = K.market_price(p, inv)
            dumped += pr
            if pr > 1:
                inv += 1
        print(f"{p:11}{N:5d}{dumped:10,d}{N*base:10,d}{N*base-dumped:10,d}"
              f"{N/max(cons,1):13.1f}")


# ----------------------------------------------------------------- trace ----

def cmd_trace(args):
    from kaggle_environments import make
    K = engine()
    fills = []
    turn = [0]
    real_commit, real_town = K._commit_unit, K._town_consume
    real_market = K._process_market

    def commit(op, item, price, farm, private, market, shed_capacity=100):
        pre = market["inventory"].get(item)
        ok = real_commit(op, item, price, farm, private, market, shed_capacity)
        if ok and op in ("SELL", "BUY_PRODUCT"):
            # The seat matters and the engine does not pass it: _commit_unit
            # takes the farm DICT. The engine mutates the same objects all
            # episode, so their identities, captured once per step from the
            # observation, resolve the seat. Without this the fills are both
            # players merged -- and "both seats combined" is not a reading
            # about our own layer at all.
            fills.append(dict(step=turn[0], seat=seat_of.get(id(farm), -1),
                              op=op, item=item, price=int(price),
                              inv=int(pre), money=int(farm["money"])))
        return ok

    def town(env, state, step):
        turn[0] = int(step)
        # snapshot the book once a step, BEFORE consumption, so the realised
        # resilience can be reconstructed instead of assumed. Also each seat's
        # shed: SHED_CAPACITY is 100 and _drop_inventories DISCARDS the
        # overflow, so "hold the unit and sell it later" is not free and the
        # shed path is the binding feasibility constraint on any slicing.
        snaps.append((int(step),
                      dict(state[0].observation.market["inventory"]),
                      [dict(s.observation.private.get("shed", {}))
                       for s in state]))
        return real_town(env, state, step)

    def process_market(state, env):
        # The seat map MUST be taken here, not in _town_consume: this is the
        # function that binds farms = state[0].observation.farms and hands
        # those very dicts to _commit_unit. Taking it from the observation in
        # another hook attributed 9 of 3,669 fills -- kaggle_environments
        # re-wraps the observation between calls, so the identities differ.
        seat_of.clear()
        for i, f in enumerate(state[0].observation.farms):
            seat_of[id(f)] = i
        return real_market(state, env)

    snaps, seat_of = [], {}
    K._commit_unit, K._town_consume = commit, town
    K._process_market = process_market
    try:
        env = make("kaggriculture",
                   configuration={"episodeSteps": args.steps, "seed": args.seed})
        env.run([args.left, args.right])
    finally:
        K._commit_unit, K._town_consume = real_commit, real_town
        K._process_market = real_market

    fin = env.steps[-1][0].observation["farms"]
    out = dict(left=args.left, right=args.right, seed=args.seed,
               steps=args.steps,
               final_money=[int(fin[i]["money"]) for i in range(2)],
               shops=list(env.steps[-1][0].observation["town"]
                          .get("unlocked_shops", [])),
               fills=fills, snaps=snaps)
    with open(args.out, "w") as f:
        json.dump(out, f)
    bad = sum(1 for x in fills if x["seat"] < 0)
    if bad:
        raise SystemExit(
            f"{bad} of {len(fills)} fills could not be attributed to a seat -- "
            f"the seat map is broken and a merged reading is not a reading "
            f"about our own layer. Refusing to write {args.out}.")
    report(K, out)
    print(f"\nwrote {args.out}")


def report(K, out):
    fills = out["fills"]
    print(f"{out['left']} vs {out['right']} seed {out['seed']}: "
          f"money {out['final_money']}")
    print(f"shops unlocked: {collections.Counter(out['shops']).most_common()}")
    cons = {}
    for p in K.PRODUCTS:
        c = sum(6 * (2 if len(v) == 1 else 1)
                for name in out["shops"] for v in [K.SHOPS[name]] if p in v)
        cons[p] = c + (1 if p in K.TOWN_CENTER_PRODUCTS else 0)
    for seat in (0, 1):
        sold, rev = collections.Counter(), collections.Counter()
        for x in fills:
            if x["op"] == "SELL" and x["seat"] == seat:
                sold[x["item"]] += 1
                rev[x["item"]] += x["price"]
        who = out["left"] if seat == 0 else out["right"]
        print(f"\n  seat {seat} = {os.path.basename(os.path.dirname(who)) or who}"
              f"   {sum(sold.values()):,} units, {sum(rev.values()):,} revenue")
        print(f"  {'product':11}{'units':>7}{'revenue':>10}{'avg':>7}"
              f"{'base':>6}{'%base':>7}{'demand/season':>15}{'at base':>10}"
              f"{'headroom':>10}")
        for p in K.PRODUCTS:
            if not sold[p]:
                continue
            b = K.MARKET_PARAMS[p]["base"]
            # the sustainable ceiling is the REALISED shop draw's consumption,
            # and it is SHARED with the opponent -- so this column is the
            # whole book's quota, not ours
            dem = cons[p] * (out["steps"] // 24)
            at_base = sold[p] * b
            print(f"  {p:11}{sold[p]:7d}{rev[p]:10,d}{rev[p]/sold[p]:7.1f}"
                  f"{b:6d}{100*rev[p]/sold[p]/b:6.0f}%{dem:15,d}"
                  f"{at_base:10,d}{at_base - rev[p]:+10,d}")


# ----------------------------------------------------------------- bound ----

def cmd_bound(args):
    """Slice bound: what our own units would have fetched sold ONE PER TURN.

    The mechanism is not what a permanent-impact reading suggests, and the
    measured inventory path is what corrects it. Over a whole season the book
    barely leaves I0 -- on seed 555 MILK ranged 9,992..10,076 and WOOL
    9,993..10,059 -- because `_town_consume` draws it back down every four
    steps. What actually costs money is the INTRA-TURN excursion: the market
    phase quotes each unit at the live inventory and only calls
    `_refresh_prices` at the end, so an order for 60 milk walks its own price
    down 60 units deep and averages the bottom half of that walk. The book is
    back near I0 a few steps later.

    So the lever is slicing, not a schedule over days, and the bound is:
    price the same units one per turn against the inventory the book ACTUALLY
    showed. Two variants, both from measured data only:

      best-N      the N highest-priced turns at or after our first realised
                  sale of that product. Optimistic on arrival timing (a unit
                  cannot be sold before it exists) and conservative on impact
                  (our own slicing would leave the book higher than it was).
      in-order    one unit per turn, consecutively, from our first realised
                  sale. Arrival-feasible for anything the farm delivers at or
                  below one unit per turn, which every product here is.

    Neither is a strategy: both keep the opponent's flow and the shop draw
    exactly as they fell.
    """
    import numpy as np
    K = engine()
    out = json.load(open(args.fills))
    me, them = args.seat, 1 - args.seat
    snaps = out["snaps"]
    steps = [t for t, _ in snaps]

    ours = collections.defaultdict(list)
    for f in out["fills"]:
        if f["op"] == "SELL" and f["seat"] == me:
            ours[f["item"]].append((f["step"], f["price"]))

    print(f"slice bound, seat {me} -- our own units re-priced one per turn "
          f"against the MEASURED book")
    print(f"{'product':11}{'units':>7}{'realised':>10}{'in-order':>10}"
          f"{'best-N':>10}{'gain(io)':>10}{'%base':>7}{'->':>4}{'%base':>7}")
    tot = [0, 0, 0]
    for p in K.PRODUCTS:
        if p not in ours:
            continue
        lst = ours[p]
        N = len(lst)
        base = K.MARKET_PARAMS[p]["base"]
        realised = sum(x[1] for x in lst)
        first = min(x[0] for x in lst)
        # price a single slice would fetch on each turn from `first` onward
        series = [K.market_price(p, inv[p]) for t, inv, _sh in snaps if t >= first]
        if not series:
            continue
        in_order = sum(series[:N]) if len(series) >= N else \
            sum(series) + (N - len(series)) * series[-1]
        best_n = sum(sorted(series, reverse=True)[:N])
        tot[0] += realised; tot[1] += in_order; tot[2] += best_n
        print(f"{p:11}{N:7d}{realised:10,d}{in_order:10,d}{best_n:10,d}"
              f"{in_order-realised:+10,d}{100*realised/N/base:6.0f}%"
              f"{'':4}{100*in_order/N/base:6.0f}%")
    print(f"{'TOTAL':11}{'':7}{tot[0]:10,d}{tot[1]:10,d}{tot[2]:10,d}"
          f"{tot[1]-tot[0]:+10,d}")
    print(f"\nfinal money: ours {out['final_money'][me]:,}, "
          f"theirs {out['final_money'][them]:,}. The gain is REVENUE, not a "
          f"score delta -- the tape spends money on buys, and a higher book "
          f"also raises what the opponent gets for the same units.")
    print("measured book range (why the day-scale schedule is the wrong "
          "model):")
    for p in K.PRODUCTS:
        if p not in ours:
            continue
        ser = [inv[p] for _, inv, _sh in snaps]
        print(f"  {p:11} I0{min(ser)-K.MARKET_I0:+6d} .. "
              f"{max(ser)-K.MARKET_I0:+5d}   end {ser[-1]-K.MARKET_I0:+6d}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("econ")
    t = sub.add_parser("trace")
    t.add_argument("left"); t.add_argument("right")
    t.add_argument("--seed", type=int, default=123)
    t.add_argument("--steps", type=int, default=720)
    t.add_argument("--out", default="fills.json")
    b = sub.add_parser("bound")
    b.add_argument("fills")
    b.add_argument("--seat", type=int, default=0)
    args = ap.parse_args()
    {"econ": cmd_econ, "trace": cmd_trace, "bound": cmd_bound}[args.cmd](args)


if __name__ == "__main__":
    main()
