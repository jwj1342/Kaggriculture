"""Export a CNN / Transformer SpatialActor to a local eval agent.

The generated file imports torch (needed for conv / attention). Kaggle
submissions still want the numpy MLP exporter; this is the local exam path.

    python -m rl.export_spatial --weights rl/ckpt_cnn/ppo_it0080.pt \\
        --out logs/labour-heads-cnn.py
"""

import argparse
import os
import textwrap

import torch

from .board_obs import pack_obs  # noqa: F401  (documents the contract)
from .spatial_policy import SpatialActor


def generate(weights_path, out_path, net=None):
    ck = torch.load(weights_path, map_location="cpu", weights_only=False)
    net = net or ck.get("net")
    if net not in ("cnn", "transformer"):
        raise SystemExit(f"checkpoint net={net!r}; pass --net cnn|transformer")
    sd = ck.get("model") or ck.get("state_dict") or ck
    model = SpatialActor(net=net)
    model.load_state_dict(sd, strict=False)
    model.eval()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ckpt_abs = os.path.abspath(weights_path)
    src = textwrap.dedent(f'''\
    # Auto-generated spatial RL agent (local exam). Last callable is agent.
    import os
    import sys

    _ROOT = {root!r}
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    os.environ.setdefault("KG_FAST_ENV", "1")

    import torch

    from rl.action_space import decode_per_unit
    from rl.board_obs import pack_obs
    from rl.features import _get
    from rl.spatial_policy import SpatialActor

    _NET = {net!r}
    _CKPT = {ckpt_abs!r}
    _NHAND = 12
    _MODEL = SpatialActor(net=_NET)
    _CK = torch.load(_CKPT, map_location="cpu", weights_only=False)
    _MODEL.load_state_dict(_CK.get("model") or _CK.get("state_dict") or _CK, strict=False)
    _MODEL.eval()


    def agent(obs):
        try:
            packed = pack_obs(obs)
            xt = torch.tensor(packed, dtype=torch.float32).unsqueeze(0)
            player = int(_get(obs, "player") or 0)
            farms = _get(obs, "farms") or []
            farm = farms[player] if player < len(farms) else {{}}
            n_hands = len(_get(farm, "hands") or [])
            nh = torch.tensor([n_hands], dtype=torch.int64)
            with torch.no_grad():
                tasks, _, _ = _MODEL.act(xt, nh, sample=False)
            act = [int(v) for v in tasks[0].tolist()]
            step = int(_get(obs, "step") or 0)
            return decode_per_unit(act[:1 + _NHAND], act[1 + _NHAND], obs,
                                   step=step, hand_cap=_NHAND)
        except Exception:
            return {{"farmer": ["PASS"], "hands": [], "market": []}}
    ''')
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"wrote {out_path}  net={net}  weights={weights_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out", default="logs/labour-heads-spatial.py")
    ap.add_argument("--net", choices=["cnn", "transformer"], default=None)
    args = ap.parse_args()
    generate(args.weights, args.out, net=args.net)


if __name__ == "__main__":
    main()
