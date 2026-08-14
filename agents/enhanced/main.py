"""Kaggriculture enhanced baseline.

An opponent-aware farm built from what 95,000 locally measured episodes actually
showed, rather than from the competition's prose. The reasoning behind each
choice is in docs/ROADMAP.md §11; the short version:

  * **Labour is the dominant axis.** 11 hands capped at 6% of cash per day
    measured 55% win rate; 30 hands with no payroll cap measured 10% -- worse
    than never hiring, because the n-th hire costs fib(n).
  * **Less land, not more.** One or two quadrants beat three or four by ~10
    points. Extra tiles dilute a fixed labour pool across cheap work.
  * **Melon opening, cow-and-sheep engine.** That shape (`orchardherd`) won
    96.5% in a balanced slice; adding strawberry and wheat to it lost 26 points.
  * **Fertilizer is bridge financing, not a bonus.** A herd that never collects
    it ends the season on $79 -- bankrupt buying feed before the first milk
    arrives on day 8.
  * **Selling is a race only when the pool does not regenerate.** Front-running
    everything measured *worse* than ignoring the opponent. See opponent.py.

The agent function must be the last callable bound at module level -- the
framework loads a file with `get_last_callable`, which takes `[-1]`. Nothing may
be defined or imported after it.
"""

from engine import ANIMALS, LAST_PLANT_DAY, PRODUCTS, SEASON_DAYS
from farm import assign, build_tasks, survey
from market import build_orders
from opponent import SellTracker, forecast

LIQUIDATE_DAY = 28          # unsold inventory scores nothing

# The measured-best structural shape. Melon is capped near the point where the
# market stops absorbing it: its pool is ~158 units and no shop demands it, so
# production past that is worth $1 a unit.
# One quadrant, filled. Measured head-to-head, a two-quadrant version of this
# same agent left 32 of 50 tiles idle while the one-quadrant field leader used 18
# of 25 -- the extra land does not add production, it spreads the same hands over
# more walking. 18 animal pens plus 7 melon tiles is exactly one quadrant.
PLAN = {
    "land": 1,
    "hands": 11,
    "hire_frac": 0.06,
    "animals": {"COW": 10, "SHEEP": 8, "GOOSE": 0},
    "crops": [("MELON", 7)],
    "last_plant": LAST_PLANT_DAY,
}

_STATE = [None, None]


def _memory(seat, step):
    """Per-seat episode memory. The module is exec'd once and called 720 times,
    so this persists; reset when a new episode starts at step 0."""
    mem = _STATE[seat]
    if mem is None or step < mem.get("last_step", -1):
        mem = {"tracker": SellTracker(), "last_step": step}
        _STATE[seat] = mem
    mem["last_step"] = step
    return mem


def _plan(obs):
    player = int(obs.get("player", 0) or 0)
    farms = obs.get("farms") or []
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    opp = farms[1 - player] if len(farms) >= 2 else {}
    priv = obs.get("private") or {}
    shed = dict(priv.get("shed") or {})
    seeds = dict(priv.get("seeds") or {})
    invs = [dict(d or {}) for d in (priv.get("inventories") or [{}])]
    board = len(farm["tiles"])
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    step = int(obs.get("step", day * 24 + hour) or 0)
    money = float(farm.get("money", 0) or 0)
    market = obs.get("market") or {}
    m_inv = dict(market.get("inventory") or {})
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    endgame = day >= LIQUIDATE_DAY

    seat = 1 if player == 1 else 0
    mem = _memory(seat, step)
    tracker = mem["tracker"]
    tracker.update(m_inv, shops, step)

    opp_ready, opp_imminent, _cap = forecast(opp, day)

    units = [(0, farm["farmer"][0], farm["farmer"][1])]
    for i, pos in enumerate(farm.get("hands") or []):
        units.append((i + 1, pos[0], pos[1]))
    while len(invs) < len(units):
        invs.append({})

    view = survey(farm, board)
    shed_total = sum(shed.values())

    tasks = build_tasks(view, PLAN, day, shed, seeds, endgame,
                        len(units), invs, money)
    actions = assign(tasks, units, invs, shed, view, board, endgame, shed_total)

    orders, submitted = build_orders({
        "farm": farm, "priv": priv, "plan": PLAN, "view": view, "day": day,
        "hour": hour, "money": money, "m_inv": m_inv, "shops": shops,
        "endgame": endgame, "tracker": tracker, "opp_ready": opp_ready,
        "opp_imminent": opp_imminent, "shed": shed, "seeds": seeds,
        "invs": invs,
    })
    # Record what we asked for, so next turn's inventory delta can be attributed
    # to the opponent rather than to ourselves.
    tracker.pending = submitted

    return {
        "farmer": actions[0] if actions and actions[0] else ["PASS"],
        "hands": [a if a else ["PASS"] for a in actions[1:]],
        "market": orders,
    }


def agent(obs):
    try:
        return _plan(obs)
    except Exception:
        # A crash forfeits the whole episode; a passed turn costs one turn.
        return {"farmer": ["PASS"], "hands": [], "market": []}
