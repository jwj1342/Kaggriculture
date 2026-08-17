# tensor_env — 张量化对局引擎（无集群也能用）

批量张量版 Kaggriculture 引擎：B 个对局以 `(B, …)` 张量并行推进，与参考
引擎**逐字节一致**（验证矩阵见 `DESIGN.md` §4，CPU/CUDA 双设备全绿）。

**没有任何 Slurm / 集群假设**——依赖只有 torch（`requirements/rl.txt`）
加仓库自带文件；笔记本 CPU 可以跑全部功能和全部验收门，有 NVIDIA 卡时
`device="cuda"` 即可。

## 上手（任何机器）

```bash
source setup_env.sh                      # 或你自己的 venv
pip install -r requirements/rl.txt       # torch；集群上改用 --no-index

# 跑验收门（约 1–2 分钟，全绿应输出 VERIFY-T-PASS / B3-PASS / B3B-PASS）
python rl/tensor_env/verify_t.py --steps 240 --seeds 2
python rl/tensor_env/test_b3.py  --steps 120
python rl/tensor_env/test_b3b.py --steps 120
```

## API 速览

```python
import sys; sys.path[:0] = ["rl", "rl/tensor_env"]
import torch
from engine_t import EpisodeT          # + engine_t_idx 注入 step_idx
import engine_t_idx                    # noqa: F401  (mixin)
import features_t

B, dev = 256, "cpu"                    # 或 "cuda"
ep = EpisodeT(seeds=list(range(B)), episode_steps=720, device=dev)

while not ep.done:
    obs0 = features_t.encode_t(ep, player=0)      # (B, 4867) float32
    fm, mm = features_t.masks_t(ep, player=0)     # (B,23) / (B,22) bool
    # …策略前向、按掩码采样 f/m 索引（双方各一对）…
    ep.step_idx(f_idx, m_idx)          # (B,2) int 张量，张量原生热路径

snap = ep.snapshot(lane=0)             # 与参考引擎 snapshot 同构的 dict
```

字典路径 `ep.step_raw(...)` 仍在（验证门和录制流回放用），但热路径请用
`step_idx`——两者已被 `test_b3b.py` 证明逐字节等价，后者快 1.8–5.6×。

## 三条纪律

1. **正确性来自门，不来自信任**：改任何实现后先跑上面三个门；
2. 竞赛评测（`tools/eval.py`）永远走参考 kaggle 引擎，与本目录无关；
3. 升级 kaggle-environments 后先跑 `verify.py`（参考链条的第一环）。
