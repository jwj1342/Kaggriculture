"""Build an ALL-RL two-stage agent: net A builds, net B inherits, switch on day.

Why (docs/RUNS.md 2026-08-23). Tonight's lineage verdict measured a straight
trade-off on the bank_frac knob: a net carrying the curriculum lineage keeps the
hybrid regime (87,723) and loses day 0 (-56,081), while a chisel-started net buys
day 0 (-46,730) and never acquires the hybrid regime (77,484). One net cannot
hold both.

But the hybrid already proves the shape works -- it just uses a TAPE for the
build half, which is why it is a candidate rather than an answer to "reach 2000
with RL". If the mechanism really is "two policies for two distributions", then
two NETS with a switch point should also work, and that version is all-RL.

This needs no training: both nets exist. So it is the cheapest possible test of
the one structural idea the lineage verdict actually points at.

    python tools/build_netnet.py <builder-export> <inheritor-export> <day> <out>

Both exports must come from trees with identical kg_rules.py (checked here --
a silent mismatch would decode the same logits against different prices). Their
private obs/actions modules must have DIFFERENT names, which they do whenever
export_agent.py was given different --name values; that is asserted rather than
assumed, because two exports sharing a module name would have net B silently
running net A's encoder.

Each net's weights are renamed (weights_a.npz / weights_b.npz) because both
exports call theirs weights.npz and resolve it off their obs module's directory
-- flat, as tools/package.sh requires, so the collision is real.
"""
import os
import re
import shutil
import sys

builder, inheritor, switch_day, out_dir = (
    sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
os.makedirs(out_dir, exist_ok=True)


def private_modules(d):
    return sorted(f for f in os.listdir(d)
                  if f.startswith(("kg_rl_obs_", "kg_rl_actions_")))


ma, mb = private_modules(builder), private_modules(inheritor)
if not ma or not mb:
    sys.exit(f"no private modules found ({ma} / {mb})")
if set(ma) & set(mb):
    sys.exit(f"the two exports share module names {sorted(set(ma) & set(mb))} -- "
             f"re-export with distinct --name, or net B will run net A's encoder")

ra = open(os.path.join(builder, "kg_rules.py")).read()
rb = open(os.path.join(inheritor, "kg_rules.py")).read()
if ra != rb:
    sys.exit("kg_rules.py differs between the two exports -- the same logits "
             "would decode against different prices")

import numpy as _np
for _side, _src in (("a", builder), ("b", inheritor)):
    if "cfw" in _np.load(os.path.join(_src, "weights.npz")):
        sys.exit(f"export {_side} is head-coupled (CoupledMultiHeadMasked, "
                 f"cfw present) and this tool's generated forward does not "
                 f"implement the market conditioning -- the hybrid would "
                 f"silently play the UNCOUPLED base policy. Extend the "
                 f"template first (see rl/export_agent.py's coupled branch).")

for side, src, wname, modname in (("a", builder, "weights_a.npz", "kg_net_a"),
                                  ("b", inheritor, "weights_b.npz", "kg_net_b")):
    for f in os.listdir(src):
        if f in ("__pycache__", "main.py", "weights.npz"):
            continue
        if f == "kg_rules.py" and side == "b":
            continue          # identical, already copied
        shutil.copy(os.path.join(src, f), os.path.join(out_dir, f))
    shutil.copy(os.path.join(src, "weights.npz"), os.path.join(out_dir, wname))

    # the export's main.py becomes an importable module whose entry point is
    # `act`, with its weights load pointed at the renamed file
    # Repoint the weights load, and resolve it off THIS module's own __file__
    # rather than the obs module's. The export resolves it off the obs module's
    # directory, which is fine when the export dir is the only copy on the path
    # -- but here two copies of that module name exist (source export and this
    # build), and the first draft silently loaded the SOURCE dir and died on the
    # missing renamed file. A dir that happened to contain a weights.npz of the
    # right shape would have loaded the WRONG NET with no error at all.
    s = open(os.path.join(src, "main.py")).read()
    s = s.replace(
        'os.path.join(\n    os.path.dirname(os.path.abspath(_O.__file__)), "weights.npz")',
        f'os.path.join(\n    os.path.dirname(os.path.abspath(__file__)), "{wname}")')
    if f'"{wname}"' not in s:
        # fall back to a looser rewrite, then re-check
        s = s.replace('os.path.abspath(_O.__file__)', 'os.path.abspath(__file__)')
        s = s.replace('"weights.npz"', f'"{wname}"')
    if f'"{wname}"' not in s or "_O.__file__" in s:
        sys.exit(f"could not repoint the weights load in {src}/main.py -- refusing "
                 f"to ship a module that may load another net's weights")
    s = re.sub(r"\ndef agent\(", "\ndef act(", s)
    if "\ndef act(" not in s:
        sys.exit(f"no module-level `def agent(` in {src}/main.py")
    open(os.path.join(out_dir, modname + ".py"), "w").write(s)

open(os.path.join(out_dir, "main.py"), "w").write(f'''"""All-RL two-stage agent: net A builds through day {switch_day}, net B inherits.

Built by tools/build_netnet.py. The switch is on the DAY, not the step, and it
reads the day off the observation rather than counting turns, so a resumed or
re-seeded episode cannot drift out of phase with it.
"""
import kg_net_a as _A
import kg_net_b as _B

_SWITCH_DAY = {switch_day}
_TPD = 24
_PASS = {{"farmer": ["PASS"], "hands": [], "market": []}}


def agent(obs, config=None):
    try:
        day = obs.get("day")
        if day is None:
            day = int(obs.get("step", 0) or 0) // _TPD
        net = _A if int(day) < _SWITCH_DAY else _B
        return net.act(obs, config)
    except Exception:
        return _PASS
''')
print(f"net-net written: {out_dir} (builder {os.path.basename(builder)} through "
      f"day {switch_day}, then {os.path.basename(inheritor)})")
