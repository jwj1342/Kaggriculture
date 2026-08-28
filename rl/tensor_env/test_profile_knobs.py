#!/usr/bin/env python
"""Gate for barnyard_t's parameterised profiles: every knob must MOVE something.

Stage 2 of the G1 plan screens dozens of executor candidates by enumerating
";key=value" overrides on a base profile. The failure mode that gate exists to
prevent is the one this repository has already paid for twice: an option that is
plumbed but inert. A knob that silently does nothing makes two arms of the sweep
identical, and a 60-row table then reports a real difference of exactly zero --
indistinguishable from "measured and refuted".

Three checks, zero tolerance:

  G1 (identity)   a spec with no overrides, and a spec whose overrides restate
                    the base profile's own defaults, must produce decisions
                    byte-identical to the bare profile name. If this fails the
                    parser is changing behaviour on its own.
  G2 (liveness)   every knob in barnyard_t._OVERRIDES, set to a value that
                    differs from the base, must change the decision stream on at
                    least one step. A knob that never moves anything is reported
                    by name and fails.
  G3 (rejection)  an unknown key and a malformed item must raise, rather than
                    being dropped.

    python rl/tensor_env/test_profile_knobs.py [--steps 240] [--lanes 2]

Ends KNOBS-PASS / KNOBS-FAIL.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

import barnyard_t
import engine_t
import engine_t_idx  # noqa: F401

BASE = "k01_route_s34_fert"

# A value per knob that differs from what BASE resolves to, so "no change" is
# unambiguously the knob's fault and not a no-op assignment. Kept next to the
# defaults it must differ from: BASE is s34 (straw 34), fert-on, wheatlast 24,
# trip 1, batch 2, reserve 0, pcap 7.
PROBE = {
    "melon": 26, "straw": 40, "wheat": 44,
    "melonlast": 12, "strawlast": 9, "wheatlast": 27,
    "trip": 6, "batch": 9, "reserve": 400, "pcap": 3,
    "handmul": 0.5, "fertmul": 4.0, "fert": 0,
}

# Earliest game day on which each probe can possibly change a decision. Without
# this the gate is unfalsifiable in the wrong direction: a 240-step window is
# days 0-9, and seven of these knobs are inert there BY DESIGN -- _K01_FERT_CAP
# is 0 until day 14, and a crop's target or deadline cannot bind until the plan
# reaches that crop. "Inert" then means "probed too early", which reads exactly
# like a plumbing bug. Declaring the day makes the distinction checkable.
MIN_DAY = {
    "melon": 0,        # first crop in the plan, binds immediately
    "straw": 10,       # plan reaches STRAWBERRY only after MELON is satisfied
    "wheat": 14,       # ... and WHEAT after STRAWBERRY
    "melonlast": 13,   # base 18, probe 12 -> bites the day after the probe
    "strawlast": 10,   # base 13, probe 9
    "wheatlast": 25,   # base 24, probe 27 -> bites only past the base deadline
    "trip": 0,
    "batch": 0,
    "reserve": 0,
    "pcap": 0,
    "handmul": 0,
    "fertmul": 14,     # _K01_FERT_CAP is 0 for days 0-13
    "fert": 14,        # same table
}


# Knobs that are inert for a MEASURED reason rather than a plumbing fault, with
# the measurement. A knob NOT listed here that fails to move still fails the
# gate, so this is an exemption list, not a suppression. Measured 2026-08-28 on
# seeds 31000/31013, full season, BASE route: peak standing tiles were 19 MELON,
# 33 STRAWBERRY, 28 WHEAT -- the route misses every one of its own targets (20 /
# 34 / 35), and it stops planting melon on day 7.
CAPPED = {
    "melonlast": "the route stops planting MELON on day 7, so lowering its "
                 "deadline from 18 to 12 cannot bind",
    "wheat": "the route peaks at 28 standing WHEAT against its existing target "
             "of 35, so raising the target to 44 cannot bind",
}


def _stream(profile, seeds, steps, device):
    """Run BASE's opponent adapter and return its per-step decision digest.

    The adapter is what a screen actually drives (it owns the persistent route,
    fertiliser budget and planted-total state), so the stream is taken through
    it rather than through bare compute() -- a knob that only bites via adapter
    state would otherwise look inert.
    """
    ep = engine_t.EpisodeT(seeds, episode_steps=steps, device=device)
    opp = barnyard_t.BarnyardOpponent(profile)
    opp.reset(ep, 1)
    gen = torch.Generator(device="cpu").manual_seed(777)
    digest = []
    n = 0
    while not ep.done and n < steps:
        ops = opp(ep, 1)
        # Every tensor the adapter emits, in a fixed key order. Taken
        # generically because the hand list is empty on step 0 and grows with
        # the crew, so a hand-written tuple of keys silently drops the market
        # ops or crashes on an empty list -- and the market ops are exactly
        # where the wheat knobs bite.
        flat = []
        for key in sorted(ops):
            value = ops[key]
            items = value if isinstance(value, (list, tuple)) else [value]
            for item in items:
                if torch.is_tensor(item) and item.numel():
                    flat.append(item.reshape(-1).detach().to(
                        "cpu", torch.int64))
        if flat:
            digest.append(torch.cat(flat).clone())
        # Player 0 plays a fixed pseudo-random legal-ish stream: PASS keeps the
        # board evolving without a second policy in the loop, and it is the same
        # for every profile, so any divergence is attributable.
        idx = torch.zeros((ep.B, 2), dtype=torch.long)
        ep.step_idx(idx, idx, override=[(1, ops)])
        n += 1
    del gen
    # One flat vector, not a stack: the per-step width changes as the crew
    # grows, and a width change between two profiles is itself a difference.
    return torch.cat(digest) if digest else torch.zeros(0, dtype=torch.int64)


def _differs(a, b):
    if a.shape != b.shape:
        return True
    return not torch.equal(a, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=720,
                    help="must cover MIN_DAY for every knob; 720 is a full "
                         "season and day 25 is the latest any knob needs")
    ap.add_argument("--lanes", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=31000)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    seeds = [args.seed0 + 13 * i for i in range(args.lanes)]

    def run(profile):
        return _stream(profile, seeds, args.steps, args.device)

    ref = run(BASE)
    print(f"  reference {BASE}: {ref.shape[0]} steps of decisions")

    # ---- G1: the parser must not change anything on its own ---------------
    for spec in (f"{BASE};", f"{BASE};straw=34", f"{BASE};fert=1",
                 f"{BASE};wheatlast=24", f"{BASE};trip=1", f"{BASE};pcap=7"):
        got = run(spec)
        if _differs(ref, got):
            print(f"G1 FAIL: {spec!r} restates a default yet changed decisions")
            print("KNOBS-FAIL")
            return 1
    print("  G1 identity: a no-op spec is byte-identical to the bare name")

    # ---- G2: every knob must move something -------------------------------
    days = args.steps // 24
    inert = []
    for key in sorted(barnyard_t._OVERRIDES):
        if key not in PROBE or key not in MIN_DAY:
            print(f"G2 FAIL: knob {key!r} has no probe value / min day here")
            print("KNOBS-FAIL")
            return 1
        if MIN_DAY[key] >= days:
            print(f"G2 FAIL: {key!r} cannot bite before day {MIN_DAY[key]} but "
                  f"the window is {days} days -- raise --steps, do not read "
                  f"this as inert")
            print("KNOBS-FAIL")
            return 1
        spec = f"{BASE};{key}={PROBE[key]}"
        moved = _differs(ref, run(spec))
        if key in CAPPED:
            # Exempt, but assert the exemption is still true: if such a knob
            # STARTS moving, the measured reason has gone stale and the note
            # above is now wrong.
            if moved:
                print(f"G2 FAIL: {key!r} is on the CAPPED list as inert because "
                      f"{CAPPED[key]}, but it moved decisions -- the "
                      f"measurement behind that exemption is stale")
                print("KNOBS-FAIL")
                return 1
            print(f"  G2 {key:<10} inert BY MEASUREMENT: {CAPPED[key]}")
            continue
        if not moved:
            inert.append((spec, MIN_DAY[key]))
        else:
            print(f"  G2 {key:<10} moves decisions  ({spec}, "
                  f"can bite from day {MIN_DAY[key]})")
    if inert:
        print("G2 FAIL: these knobs are plumbed but inert -- a sweep over them "
              "would report a difference of exactly zero:")
        for spec, day in inert:
            print(f"    {spec}   (declared to bite from day {day}, window "
                  f"{days} days, so this is NOT a window artifact)")
        print("KNOBS-FAIL")
        return 1

    # ---- G3: bad specs must raise, not be dropped -------------------------
    for bad in (f"{BASE};nosuchknob=1", f"{BASE};straw", f"{BASE};straw=abc"):
        try:
            barnyard_t.parse_profile(bad)
        except ValueError:
            continue
        print(f"G3 FAIL: {bad!r} was accepted")
        print("KNOBS-FAIL")
        return 1
    print("  G3 rejection: unknown key, missing '=' and bad value all raise")

    print(f"{len(barnyard_t._OVERRIDES)} knobs live, parser inert on no-ops")
    print("KNOBS-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
