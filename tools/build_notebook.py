#!/usr/bin/env python
"""Build notebooks/baseline.ipynb from an agent file.

Keeps a single source of truth: the notebook's `%%writefile main.py` cell is
generated from agents/<name>.py rather than maintained by hand.

    python tools/build_notebook.py agents/barnyard.py notebooks/baseline.ipynb
"""

import json
import os
import sys

INTRO = """# Kaggriculture — Baseline "Barnyard"

A first submission built directly off the engine source (`kaggle_environments/
envs/kaggriculture/kaggriculture.py`), not off the prose rules. Everything below
is derived from the code the episodes actually run.

## What the numbers say

**Farm hands are the cheapest lever in the game.** The n-th hire of a day costs
`fib(n)` (1, 1, 2, 3, 5, 8, 13, …) and buys 24 extra actions. The first eight
hands together cost less than one melon seed. But `fib` explodes — the 17th hand
alone costs more than the first fifteen combined — so this agent caps the day's
payroll at a fraction of cash rather than at a head count.

**Fertilizer is one-way.** Every surviving animal makes one unit per day, free.
No shop and not the town center consumes `FERTILIZER`, so its market inventory
only ever rises and its price only ever falls. Holding fertilizer is strictly a
loss; this agent sells every unit the turn it reaches the shed.

**The town, not the buffer, is the real customer.** Each product starts at 10,000
market inventory, and dumping into that buffer walks the price down a cliff
(~62 units flattens strawberry, ~59 wool, ~76 milk, ~158 melon). What refills the
buffer is town demand: up to 8 shop instances, each pulling its products every 4
turns, plus the town center. That is roughly 2,000 units of demand across a
season — far more than the static buffer. So herd size should track *town
demand*, and sales should be metered in small batches.

**Feed is a logistics problem, not an economics one.** `FEED` consumes wheat from
the *acting unit's* inventory, and `PICKUP` only works on the four tiles next to
the shed. Without explicitly routing hands back for feed, every unit stays busy
with watering and care and the whole herd starves. That single bug cost this
agent ~45k in testing.

## Strategy

1. Melon + strawberry opening for capital (melon is the best profit per tile-day).
2. Roll it into an animal engine; `FEED` + `CARE` daily, which triples yield.
3. Collect and immediately sell fertilizer.
4. Buy wheat for feed instead of growing it — actions are scarcer than coins.
5. Meter every sale against the exact price curve, copied from the engine.
6. Liquidate everything from day 28: unsold inventory scores nothing.
"""

TEST = """from kaggle_environments import make

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run(["main.py", "starter"])

final = env.steps[-1]
for i, s in enumerate(final):
    print(f"Player {i}: reward={s.reward:,.0f}  status={s.status}")
"""

OUTRO = """## Submitting

```bash
kaggle competitions submit kaggriculture -f main.py -m "barnyard opening"
kaggle competitions submissions kaggriculture
```

Or press **Submit to competition** on the right.

## Where this baseline is weak

- **Fixed crop and herd plan.** Which shops unlock is random and drives which
  products the town actually buys. The plan should react to `obs["town"]
  ["unlocked_shops"]` instead of being hard-coded.
- **No fertilizer used on plants.** Fertilizing an ongoing crop on a production
  day doubles that yield; strawberry output could go from 4 units to 8 for two
  actions. Right now every unit of fertilizer is sold instead.
- **Ignores the opponent.** Both players sell into one shared market, so whoever
  sells first gets the better price. This agent never looks at the opponent's
  board to anticipate their harvest.
- **Greedy nearest-unit assignment.** No routing: units criss-cross the board
  instead of working a tile cluster to completion.
"""


def cell(kind, text):
    if kind == "md":
        return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.splitlines(keepends=True)}


def main():
    agent_path = sys.argv[1] if len(sys.argv) > 1 else "agents/barnyard.py"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "notebooks/baseline.ipynb"
    with open(agent_path) as f:
        agent_src = f.read()

    nb = {
        "cells": [
            cell("md", INTRO),
            cell("md", "## The agent\n\nWritten straight to `main.py` so the notebook and the submission cannot drift."),
            cell("code", "%%writefile main.py\n" + agent_src),
            cell("md", "## Play a full season against the built-in `starter` agent"),
            cell("code", TEST),
            cell("md", OUTRO),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(nb, f, indent=1)
    print(f"wrote {out_path} ({os.path.getsize(out_path):,} bytes) from {agent_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
