"""Spatial farm encoding for CNN / Transformer trunks.

Per farm, 22 channels on a 10×10 grid, channel-major (C, y, x). Packed
observation is  [global 75 | own 2200 | opp 2200]  so SpatialActor can
split without a second array.

Channel layout (must match rl.gpu.obs.encode_board):

    0 empty   1 locked   2 weed   3 plant (any crop)
    4..8 crop one-hot (WHEAT..MELON)
    9 yield_units/6   10 watered   11 consecutive_unwatered/2
    12 pasture   13 coop
    14..16 animal one-hot (COW, SHEEP, GOOSE)
    17 fed   18 cared   19 fertilizer_available
    20 farmer here   21 hands here / 4
"""

from .features import ANIMALS, CROPS, FEATURE_DIM, _get

BOARD = 10
CH_PER_FARM = 22
N_FARM = 2
BOARD_FLAT = CH_PER_FARM * N_FARM * BOARD * BOARD  # 4400
PACKED_DIM = FEATURE_DIM + BOARD_FLAT


def _as_xy(pos, default=(4, 4)):
    if pos is None:
        return default
    try:
        x, y = int(pos[0]), int(pos[1])
    except (TypeError, ValueError, IndexError):
        return default
    if x < 0 or y < 0 or x >= BOARD or y >= BOARD:
        return default
    return x, y


def encode_farm(farm):
    """Return (CH, 10, 10) float32 for one farm."""
    out = [[[0.0] * BOARD for _ in range(BOARD)] for _ in range(CH_PER_FARM)]
    tiles = _get(farm, "tiles") or []
    for y in range(BOARD):
        row = tiles[y] if y < len(tiles) else []
        for x in range(BOARD):
            t = row[x] if x < len(row) else "LOCKED"
            if t is None:
                out[0][y][x] = 1.0
                continue
            if t == "LOCKED" or not isinstance(t, dict):
                out[1][y][x] = 1.0
                continue
            kind = t.get("kind")
            if kind == "WEED":
                out[2][y][x] = 1.0
            elif kind == "PLANT":
                out[3][y][x] = 1.0
                crop = t.get("crop")
                if crop in CROPS:
                    out[4 + CROPS.index(crop)][y][x] = 1.0
            elif kind == "PASTURE":
                out[12][y][x] = 1.0
            elif kind == "COOP":
                out[13][y][x] = 1.0
            try:
                yu = float(t.get("yield_units") or 0.0)
            except (TypeError, ValueError):
                yu = 0.0
            out[9][y][x] = max(0.0, min(1.0, yu / 6.0))
            if t.get("watered_today"):
                out[10][y][x] = 1.0
            try:
                uw = float(t.get("consecutive_unwatered") or 0.0)
            except (TypeError, ValueError):
                uw = 0.0
            out[11][y][x] = max(0.0, min(1.0, uw / 2.0))
            animal = t.get("animal")
            if animal in ANIMALS:
                out[14 + ANIMALS.index(animal)][y][x] = 1.0
            if t.get("fed_today"):
                out[17][y][x] = 1.0
            if t.get("cared_today"):
                out[18][y][x] = 1.0
            if t.get("fertilizer_available"):
                out[19][y][x] = 1.0

    fx, fy = _as_xy(_get(farm, "farmer"))
    out[20][fy][fx] = 1.0
    for pos in (_get(farm, "hands") or []):
        xy = _as_xy(pos, default=None)
        if xy is None:
            continue
        hx, hy = xy
        out[21][hy][hx] = min(1.0, out[21][hy][hx] + 0.25)
    return out


def _flatten_farm(ch):
    flat = []
    for c in range(CH_PER_FARM):
        for y in range(BOARD):
            flat.extend(ch[c][y])
    return flat


def encode_board(obs):
    """Own then opponent, each CH*10*10, length BOARD_FLAT."""
    player = int(_get(obs, "player") or 0)
    farms = _get(obs, "farms") or []
    mine = farms[player] if player < len(farms) else {}
    opp = farms[1 - player] if (1 - player) < len(farms) else {}
    return _flatten_farm(encode_farm(mine)) + _flatten_farm(encode_farm(opp))


def pack_obs(obs, global_feats=None):
    """Packed vector: global features then board. Length PACKED_DIM."""
    from .features import encode as encode_global
    g = list(global_feats) if global_feats is not None else encode_global(obs)
    b = encode_board(obs)
    if len(g) != FEATURE_DIM:
        raise ValueError(f"global feats {len(g)} != {FEATURE_DIM}")
    if len(b) != BOARD_FLAT:
        raise ValueError(f"board feats {len(b)} != {BOARD_FLAT}")
    return [float(v) for v in g] + [float(v) for v in b]
