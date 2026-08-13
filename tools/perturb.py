#!/usr/bin/env python
"""Generate market-behaviour variants of one wrapped agent, by rewriting constants.

    python tools/perturb.py --base agents/champ/k01.py --design designs/mkt1.json \
        --out agents/mkt

A wrapped agent (`tools/wrap.py`) is two things glued together: a recorded
720-turn field plan in `_TRACE`, and the donor's market layer. The market layer
is *parameterised* -- roughly a dozen module-level constants decide when a
product is sold, which market slot it takes, and how long it is held. Its author
knew slot order is a front-run:

    "Market slots resolve index by index across both players, so an order in an
    earlier slot is priced before the opponent's matching order in a later slot."

Nobody has measured what happens at the extremes. This script builds the arms
that would.

WHY REWRITE CONSTANTS RATHER THAN WRITE VARIANTS

Because it makes the controlled variable exact. Two files produced here differ
only in the constant lines named by the design; `_TRACE` is byte-identical, so
what is planted, harvested, hired and bought is identical across every arm. Any
outcome difference is caused by market behaviour and nothing else. Hand-written
variants cannot promise that, and `CLAUDE.md` forbids them for the same reason.

THE FAILURE MODE THIS GUARDS AGAINST

Illegal actions in this environment are silent no-ops, and so is a constant that
was never actually replaced -- the arm runs, scores, and is indistinguishable
from a real result. So every rewrite is checked three ways:

1. the constant's assignment line must occur exactly once in the base file;
2. after writing, the file is loaded the way the framework loads it
   (`get_last_callable`) and must resolve to `agent`;
3. the loaded module's live value of each rewritten constant must equal what was
   asked for. Verification reads the *loaded* module, not the source text.

An arm that fails any of these raises rather than being quietly skipped.

THE INTERFERENCE OVERLAY, AND WHY THE DONOR'S OWN DIALS COULD NOT BE USED

The donor's market layer already has a reservation mechanism (`_RESERVE`), and
using it was the obvious way to build hold/dump arms. Measured on 2026-08-13, it
does the opposite of what it reads like. `agent()` strips the tape's SELL orders
for any reserved product and re-plans them from `obs["private"]["shed"]` -- but
that shed is the *opening* shed of the turn, and the tape sells goods on the same
turn they are dropped into it. The controller cannot see them, emits no order,
and the goods rot. One episode, seed 777, `_RESERVE={"WOOL": 0.0}` -- nominally
"dump all wool at once":

    wool SELL orders   29 -> 10        wool units listed   136 -> 63
    our bank      $63,550 -> $43,073   opponent      $63,457 -> $101,479

Less sold, not more. `_RESERVE` is empty in the donor too (`tools/wrap.py` says
so), so this path has never executed in any measurement in this repo.

So the overlay below places orders that need no shed observation at all. The
engine's per-unit market loop aborts an order the moment the shed runs out, so a
SELL of 9999 lists exactly what is present -- including goods dropped this very
turn. That is the only mechanism here that can dump reliably.

    _X_SELL_FROM   {item: step} -- before `step`, the tape's SELL orders for the
                   item are suppressed and the goods accumulate; from `step`, one
                   oversized SELL lists everything. step=0 is a pure front-run,
                   a large step is hoard-then-crash. One dict expresses both the
                   target and the timing, which are the two factors worth crossing.
    _X_SLOT        0 puts the order in the earliest slot, -1 in the latest. The
                   engine resolves market orders index by index across both
                   players, so this is the whole front-run.
    _X_BUY         {item: [max_price, until_step, qty]} -- BUY_PRODUCT drains
                   inventory and lifts the price. Only WHEAT and FERTILIZER can
                   be bought, and fertilizer has no other sink in the entire
                   engine: no shop and no town-centre consumes it, so a buyer is
                   the only thing that ever lowers its inventory.

Added orders never displace a tape order off the 10-slot queue -- they fill the
slots freed by suppression, and are dropped if there is no room. Truncating the
tape instead would break its funding chain (sells pay for the buys behind them
in the same queue), which is a different experiment from the one intended.

The overlay renames the base's `agent` to `_inner_agent` and defines a new
`agent` last. Binding `_INNER = agent` after the fact would load the *unwrapped*
function and score every arm identically with no error -- see the agent contract
in `CLAUDE.md`. Two controls guard this: `<prefix>ctl` is the untouched base, and
`<prefix>nul` carries the overlay with every dial empty. Both must return 50%.
If `nul` and `ctl` disagree, the overlay is not inert and no arm means anything.

DESIGN FILES

Two forms, both JSON. Explicit arms:

    {"arms": {"wool_dump": {"_RESERVE": {"WOOL": 0.0}}}}

or a full factorial, which is the point of the tool -- `factors` maps a factor
name to its levels, and the Cartesian product of levels becomes the arms:

    {"factors": {
        "target": {"none": {}, "wool": {"_RESERVE": {"WOOL": 0.5}}},
        "fuse":   {"d24": {"_RAMP_START": 576}, "d12": {"_RAMP_START": 288}}}}

    -> arms target=none.fuse=d24, target=none.fuse=d12, target=wool.fuse=d24, ...

Levels of different factors are merged left to right, so a later factor wins a
key collision; the merge order is the `factors` key order, which JSON preserves.
The manifest records each arm's factor levels, which is what
`tools/factorial.py` needs to separate main effects from interactions.

A CONTROL IS ALWAYS EMITTED

`<prefix>ctl.py` is a byte-identical copy of the base under a different name.
Played against the base it must score 50%, and it is the only arm whose expected
value is known in advance. If it comes back anything else, the harness is
biased and no other arm in the run means anything -- check it first.
"""

import argparse
import itertools
import json
import os
import re
import shutil
import sys


OVERLAY = '''

# ===========================================================================
# Market-interference overlay -- generated by tools/perturb.py
# ===========================================================================
# Placed orders are derived from `step` alone, never from the observed shed:
# `obs["private"]["shed"]` is the turn's *opening* shed and cannot see goods
# dropped this turn, which is the whole reason the donor's `_RESERVE` path
# silently under-sells. An oversized SELL sidesteps it -- the engine's per-unit
# loop aborts the order when the shed empties, so 9999 lists exactly what is
# there.
_X_SELL_FROM = {}
_X_SLOT = 0
_X_BUY = {}


def _x_is_sell(o, items):
    return (isinstance(o, list) and len(o) >= 2 and o[0] == "SELL"
            and o[1] in items)


def _x_market(action, obs, step):
    if not _X_SELL_FROM and not _X_BUY:
        return
    orders = list(action.get("market") or [])
    fire = []
    if _X_SELL_FROM:
        hot = {i for i, t in _X_SELL_FROM.items() if step >= t}
        cold = {i for i, t in _X_SELL_FROM.items() if step < t}
        # Cold products are suppressed with no replacement -- that is the hoard,
        # and it is intended. Hot ones are *swapped*, one at a time, and only
        # when the replacement fits: dropping the tape's order and then losing
        # the replacement to the 10-slot cap would silently stop the arm selling
        # that product at all. Measured before this guard existed: D.late_wool
        # closed wool at $214 (never sold) and banked $42,829 against $101,655.
        orders = [o for o in orders if not _x_is_sell(o, cold)]
        for item in sorted(hot):
            trial = [o for o in orders if not _x_is_sell(o, {item})]
            if len(trial) < 10:
                orders = trial
                fire.append(["SELL", item, 9999])
    if _X_BUY:
        prices = ((obs.get("market") or {}).get("prices") or {})
        for item in sorted(_X_BUY):
            cap, until, qty = _X_BUY[item]
            if step <= until and float(prices.get(item, 1e9) or 1e9) <= cap:
                fire.append(["BUY_PRODUCT", item, qty])
    # Never push a tape order off the queue -- its sells fund the buys behind
    # them, and losing one is a different experiment from the one intended.
    fire = fire[:max(0, 10 - len(orders))]
    action["market"] = (fire + orders) if _X_SLOT >= 0 else (orders + fire)


def agent(obs, config=None):
    action = _inner_agent(obs, config)
    try:
        step = int(obs.get("step", 0) or 0)
        if step < 717:
            _x_market(action, obs, step)
    except Exception:
        pass
    return action
'''

AGENT_DEF = re.compile(r"^def agent\(", re.M)


def inject(src):
    """Rename the base's `agent` and define a new one last."""
    if len(AGENT_DEF.findall(src)) != 1:
        raise SystemExit("base must define `agent` exactly once at top level")
    src = AGENT_DEF.sub("def _inner_agent(", src)
    return src + OVERLAY


def _assignment(src, name):
    """The single top-level `name = ...` line, or raise saying why not."""
    pat = re.compile(rf"^{re.escape(name)} = .*$", re.M)
    hits = pat.findall(src)
    if len(hits) != 1:
        raise SystemExit(
            f"{name}: found {len(hits)} top-level assignments, need exactly 1. "
            "Only single-line module-level constants can be rewritten safely; "
            "a multi-line or conditional definition needs a different approach.")
    return pat


def rewrite(src, knobs):
    for name, value in knobs.items():
        src = _assignment(src, name).sub(f"{name} = {value!r}", src)
    return src


def _load(path):
    """Load it exactly as the competition framework will."""
    from kaggle_environments.agent import get_last_callable
    with open(path) as f:
        src = f.read()
    fn = get_last_callable(src, path=path)
    if fn.__name__ != "agent":
        raise SystemExit(f"{path}: framework would load {fn.__name__}, not agent. "
                         "Nothing callable may be bound after `agent` "
                         "(CLAUDE.md, agent contract).")
    return fn


def verify(path, knobs):
    """Check the *loaded* module's values, not the source text."""
    fn = _load(path)
    mod = fn.__globals__
    for name, want in knobs.items():
        if name not in mod:
            raise SystemExit(f"{path}: {name} is not defined after loading")
        if mod[name] != want:
            raise SystemExit(f"{path}: {name} loaded as {mod[name]!r}, asked {want!r}")
    # The field plan must survive untouched: only market behaviour is under test.
    got = fn({"step": 0})
    want = mod["_TRACE"][0]
    if got.get("farmer") != want.get("farmer"):
        raise SystemExit(f"{path}: step 0 farmer is {got.get('farmer')}, the "
                         f"plan says {want.get('farmer')} -- the arm is not a "
                         "market-only perturbation")
    return fn


def expand(design):
    """Design -> {arm_name: (knobs, {factor: level})}."""
    if "arms" in design:
        return {k: (v, {"arm": k}) for k, v in design["arms"].items()}
    factors = design["factors"]
    names = list(factors)
    out = {}
    for combo in itertools.product(*(list(factors[n]) for n in names)):
        knobs = {}
        for fname, level in zip(names, combo):
            knobs.update(factors[fname][level])
        arm = ".".join(f"{n}={lv}" for n, lv in zip(names, combo))
        out[arm] = (knobs, dict(zip(names, combo)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="agents/champ/k01.py")
    ap.add_argument("--design", required=True)
    ap.add_argument("--out", default="agents/mkt")
    ap.add_argument("--prefix", default="m")
    ap.add_argument("--clean", action="store_true",
                    help="empty --out first; stale arms from an earlier design "
                         "would otherwise be picked up by a glob and scored")
    a = ap.parse_args()

    with open(a.design) as f:
        design = json.load(f)
    with open(a.base) as f:
        base_src = f.read()

    arms = expand(design)
    if not arms:
        raise SystemExit(f"{a.design}: no arms")

    if a.clean and os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out, exist_ok=True)

    # Names go through a hash-free slug so a filename stays readable in shard
    # JSONL, where `short(path)` is all that survives.
    injected = inject(base_src)
    manifest = {}
    width = len(str(len(arms)))
    for i, (arm, (knobs, levels)) in enumerate(sorted(arms.items())):
        stem = f"{a.prefix}{i:0{width}d}"
        path = os.path.join(a.out, stem + ".py")
        with open(path, "w") as f:
            f.write(rewrite(injected, knobs))
        verify(path, knobs)
        manifest[stem] = {"arm": arm, "knobs": knobs, "levels": levels,
                          "base": a.base}
        print(f"  {stem}  {arm}")

    # Two controls. `ctl` is the base untouched; `nul` carries the overlay with
    # every dial empty. They must agree, and both must be 50% -- that is what
    # separates "the dial did something" from "the overlay did something".
    for stem, src, note in (
            (a.prefix + "ctl", base_src, f"control -- byte-identical to {a.base}"),
            (a.prefix + "nul", injected, "control -- overlay present, all dials empty")):
        path = os.path.join(a.out, stem + ".py")
        with open(path, "w") as f:
            f.write(src)
        verify(path, {})
        manifest[stem] = {"arm": "control", "knobs": {},
                          "levels": {k: "__base__" for k in
                                     (design.get("factors") or {})},
                          "base": a.base}
        print(f"  {stem}  {note}")

    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump({"base": a.base, "design": a.design, "arms": manifest}, f,
                  indent=1, ensure_ascii=False)
    print(f"\n{len(arms)} arms + 2 controls -> {a.out}")
    print(f"both controls must come back at 50% against {a.base}, and at 50% "
          "against each other; if not, stop -- no arm in the run means anything")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
