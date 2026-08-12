#!/usr/bin/env python
"""Reading a farm out of an observation, once.

Counting what is on the tiles is the first thing every analysis tool does, and
four of them had grown their own copy of the same nested loop -- `trace.py`,
`topeps.py`, `tournament.py` and `ladder.py`. They differed only in whether they
truncated names to two characters for display, which is a formatting decision
that does not belong inside a survey.

The tile shapes come from `reference/engine/kaggriculture.py`: a tile is `None`
when empty, or a dict whose `kind` is `PLANT`, `WEED`, or a structure, with
animals carrying an `animal` key rather than a distinguishing `kind`.
"""

from collections import Counter


def survey(farm):
    """What is standing on this farm's tiles.

    Returns crops, animals and structures as Counters keyed by full name, plus
    plain counts of weeds and empty tiles. Callers that want short display names
    truncate afterwards -- that is presentation, not measurement.
    """
    crops, animals, structs = Counter(), Counter(), Counter()
    weeds = empty = 0
    for row in farm.get("tiles") or []:
        for tile in row:
            if tile is None:
                empty += 1
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "PLANT":
                    crops[tile["crop"]] += 1
                elif kind == "WEED":
                    weeds += 1
                elif "animal" in tile:
                    animals[tile["animal"]] += 1
                else:
                    structs[kind] += 1
    return {"crops": crops, "animals": animals, "structs": structs,
            "weeds": weeds, "empty": empty}


def ready(farm):
    """Units of produce standing unharvested on the board.

    The season-end version of this number is how the endgame defect was found:
    our engine left 84 units in the field against the meta's 13, because it had
    dismissed its whole workforce on the liquidation day.
    """
    return sum(int(t.get("yield_units", 0) or 0)
               for row in farm.get("tiles") or [] for t in row
               if isinstance(t, dict) and t.get("yield_units"))
