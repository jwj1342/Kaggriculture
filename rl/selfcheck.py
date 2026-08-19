"""Smoke tests for the RL pipeline."""

import os

os.environ.setdefault("KG_FAST_ENV", "1")

import numpy as np  # noqa: E402

from . import features  # noqa: E402
from .action_space import (  # noqa: E402
    decode, decode_per_unit, FARM_TASKS, MARKET_MODES, TASK_IDX,
)
from .potential import farm_potential, shaped_reward  # noqa: E402
from .ppo import MLP, MultiHeadMLP, ppo_update_multihead  # noqa: E402


def _blank_obs(money=3000.0, extra_tile=None):
    tiles = [[None] * 10 for _ in range(10)]
    if extra_tile is not None:
        x, y, tile = extra_tile
        tiles[y][x] = tile
    return {
        "player": 0,
        "farms": [
            {"farmer": [4, 4], "hands": [[4, 3], [5, 5]],
             "tiles": tiles, "unlocked_quadrants": ["NW"], "money": money},
            {"farmer": [5, 5], "hands": [],
             "tiles": [[None] * 10 for _ in range(10)],
             "unlocked_quadrants": ["NW"], "money": 3000.0},
        ],
        "private": {"shed": {"WHEAT": 5, "EGG": 3}, "seeds": {"MELON": 2},
                    "inventories": [{"WHEAT": 1}, {}]},
        "market": {"inventory": {k: 10000 for k in features.PRODUCTS},
                   "prices": {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
                              "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}},
        "town": {"unlocked_shops": ["BAKERY"]},
        "day": 0, "hour": 0, "step": 0,
    }


def test_features():
    obs = _blank_obs()
    f = features.encode(obs)
    assert len(f) == features.FEATURE_DIM, f"feature dim mismatch: {len(f)} vs {features.FEATURE_DIM}"
    assert features.FEATURE_DIM == 75, f"doc expects 75 features, got {features.FEATURE_DIM}"
    assert all(isinstance(v, float) for v in f), "features not all float"
    print("features ok  dim=", len(f))


def test_decode():
    obs = _blank_obs(money=5000.0)
    for ti in range(len(FARM_TASKS)):
        for mi in range(len(MARKET_MODES)):
            action = decode(ti, mi, obs, step=120)
            assert "farmer" in action and "hands" in action and "market" in action
            assert isinstance(action["farmer"], list)
            assert isinstance(action["hands"], list)
            assert isinstance(action["market"], list)
            assert len(action["market"]) <= 10
    print("decode ok")


def test_decode_per_unit():
    obs = _blank_obs(money=5000.0)
    tasks = [TASK_IDX["HARVEST"]] + [TASK_IDX["WATER"]] * 12
    action = decode_per_unit(tasks, 1, obs, step=120)
    assert len(action["hands"]) == 2
    assert action["farmer"] is not None
    print("decode_per_unit ok")


def test_default_scheduler_and_restock():
    from .action_space import _default_task, MODE_IDX
    obs = _blank_obs()
    farm = obs["farms"][0]
    priv = obs["private"]
    priv["seeds"] = {c: 0 for c in features.CROPS}
    op = _default_task(farm["farmer"], farm, priv, 10)
    assert op != ["BUILD_PASTURE"], f"no-seed default should not pave farmland, got {op}"
    priv["seeds"]["WHEAT"] = 3
    op = _default_task(farm["farmer"], farm, priv, 10)
    assert op[0] in ("PLANT", "NORTH", "SOUTH", "EAST", "WEST"), f"with seeds should plant/walk, got {op}"
    obs["day"] = 0
    obs["hour"] = 0
    obs["private"] = priv
    act = decode_per_unit([0] * 13, MODE_IDX["RESTOCK"], obs, step=0)
    kinds = [o[0] for o in act["market"]]
    assert "BUY_LAND" not in kinds, f"RESTOCK must not buy land on an empty starting farm: {act['market']}"
    assert any(o[0] == "BUY_SEED" for o in act["market"]), act["market"]
    # Two idle units must not pile onto the same plant.
    tiles = [[None] * 10 for _ in range(10)]
    tiles[1][1] = {"kind": "PLANT", "crop": "MELON", "planted_day": 0,
                   "watered_today": False, "consecutive_unwatered": 1, "yield_units": 1}
    tiles[3][3] = {"kind": "PLANT", "crop": "MELON", "planted_day": 0,
                   "watered_today": False, "consecutive_unwatered": 1, "yield_units": 1}
    obs2 = _blank_obs()
    obs2["farms"][0]["tiles"] = tiles
    obs2["farms"][0]["farmer"] = [1, 1]
    obs2["farms"][0]["hands"] = [[3, 3]]
    obs2["day"] = 11
    split = decode_per_unit([0] * 13, MODE_IDX["HOLD"], obs2, step=264)
    assert split["farmer"][0] in ("WATER", "HARVEST")
    assert split["hands"][0][0] in ("WATER", "HARVEST")
    if split["farmer"][0] == split["hands"][0][0] == "WATER":
        pass
    # Walking must be a 1-token list, not a raw "EAST" string (engine reads action[0]).
    walk_obs = _blank_obs()
    tiles = [[None] * 10 for _ in range(10)]
    tiles[0][4] = {"kind": "PLANT", "crop": "MELON", "planted_day": 0,
                   "watered_today": False, "consecutive_unwatered": 1, "yield_units": 1}
    walk_obs["farms"][0]["tiles"] = tiles
    walk_obs["farms"][0]["farmer"] = [0, 0]
    walk_obs["farms"][0]["hands"] = []
    walk_obs["day"] = 11
    walked = decode_per_unit([0] * 13, MODE_IDX["HOLD"], walk_obs, step=264)
    assert isinstance(walked["farmer"], list) and walked["farmer"][0] in (
        "EAST", "WEST", "NORTH", "SOUTH", "WATER"), walked["farmer"]
    print("default scheduler + restock ok  farmer=", op, " market=", act["market"])


def test_potential_melon():
    empty = _blank_obs()
    melon = _blank_obs(extra_tile=(1, 1, {
        "kind": "PLANT", "crop": "MELON", "planted_day": 0,
        "watered_today": True, "consecutive_unwatered": 0, "yield_units": 1,
    }))
    phi_empty = farm_potential(empty["farms"][0], empty["private"], day=0)
    phi_melon = farm_potential(melon["farms"][0], melon["private"], day=0)
    delta = phi_melon - phi_empty
    # 6 × 250 × 0.5 = 750
    assert 600 < delta < 900, f"melon plant should lift Φ by ~750, got {delta}"
    r, _ = shaped_reward(empty, melon, done=False)
    assert r > 0.5, f"planting melon should give immediate shaped reward, got {r}"
    print("potential melon ok  dPhi=", round(delta, 1), " r=", round(r, 3))


def test_mlp_forward():
    mlp = MLP(seed=0)
    x = np.zeros(features.FEATURE_DIM, dtype=np.float64)
    act, logp, val, cache = mlp.act(x.tolist(), sample=False)
    assert 0 <= act[0] < len(FARM_TASKS)
    assert 0 <= act[1] < len(MARKET_MODES)
    assert -100 < logp < 100
    assert -1e6 < val < 1e6
    print("mlp forward ok")


def test_multihead_forward():
    mlp = MultiHeadMLP(seed=0)
    x = np.zeros(features.FEATURE_DIM, dtype=np.float64)
    act, logp, val, cache = mlp.act(x.tolist(), n_hands=2, sample=False)
    assert len(act) == 14, f"expected 14-way action, got {len(act)}"
    assert all(0 <= a < len(FARM_TASKS) for a in act[:13])
    assert 0 <= act[-1] < len(MARKET_MODES)
    assert act[3] == 0 and act[4] == 0  # inactive hands forced IDLE
    print("multihead forward ok  action=", act[:4], "...", act[-1])


def test_multihead_save_load():
    path = os.path.join(os.path.dirname(__file__), "_tmp_mh.npz")
    mlp = MultiHeadMLP(seed=1)
    mlp.save(path)
    mlp2 = MultiHeadMLP(seed=2)
    mlp2.load(path)
    os.remove(path)
    for k, v in mlp.params.items():
        assert np.allclose(v, mlp2.params[k]), k
    print("multihead save/load ok")


def test_ppo_multihead_update():
    mlp = MultiHeadMLP(seed=0)
    B = 32
    obs = [np.zeros(features.FEATURE_DIM) for _ in range(B)]
    act = [[0] * 14 for _ in range(B)]
    logp = [-2.0] * B
    rew = [0.1] * B
    val = [0.0] * (B + 1)
    done = [False] * (B - 1) + [True]
    nh = [2] * B
    stats = ppo_update_multihead(
        mlp, obs, act, logp, rew, val, done, n_hands_buf=nh,
        episode_lengths=[B], epochs=1, minibatch=16,
    )
    print("ppo multihead update ok  pol=", round(stats["policy_loss"], 4))


def test_env_episode():
    from .env import KaggEnv
    env = KaggEnv(opponent="starter", seed=1)
    obs = env.reset()
    rng = np.random.default_rng(1)
    total = 0.0
    for _ in range(20):
        act = [int(rng.integers(0, len(FARM_TASKS))), int(rng.integers(0, len(MARKET_MODES)))]
        obs, r, d, info = env.step(act)
        total += float(r)
        if d:
            break
    env.close()
    print("env episode ok  reward=", round(total, 3))


def test_env_multi_episode():
    from .env import KaggEnvMulti
    env = KaggEnvMulti(opponent="starter", seed=1)
    obs = env.reset()
    mlp = MultiHeadMLP(seed=0)
    total = 0.0
    rng = np.random.default_rng(1)
    n_hands = env.n_hands
    for _ in range(8):
        act, logp, val, _ = mlp.act(obs, n_hands=n_hands, sample=True, rng=rng)
        obs, r, d, info = env.step(act)
        n_hands = info.get("n_hands", n_hands)
        total += float(r)
        if d:
            break
    env.close()
    print("env multi ok  reward=", round(total, 3), " n_hands=", n_hands)


def main():
    test_features()
    test_decode()
    test_decode_per_unit()
    test_default_scheduler_and_restock()
    test_potential_melon()
    test_mlp_forward()
    test_multihead_forward()
    test_multihead_save_load()
    test_ppo_multihead_update()
    test_env_episode()
    test_env_multi_episode()
    print("selfcheck passed")


if __name__ == "__main__":
    main()
