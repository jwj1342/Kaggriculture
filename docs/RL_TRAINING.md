# RL 训练方案 v2 —— 势函数整形 + 逐单位动作头

> 本文档描述 2026-08-15 重设计后的完整 RL 方案，替代 v1（factored 单任务 +
> 稀疏增量奖励）。v1 的失败分析见文末。
> 墙钟为什么慢、deepcopy / 向量化怎么加快：见 `docs/RL_SPEED.md`。

## 1. 核心思想

| 问题 | v1 方案 | v2 方案 |
|---|---|---|
| 信用分配断裂 | γ=0.99（有效视野 ~100 回合，看不见 240 回合后的 melon 收益） | γ=0.997 + 势函数整形（种下即得分） |
| 奖励稀疏 | Δmoney（>90% 步为 0） | 势函数 Φ 每步都在变（种植/浇水/除草/喂食全都即时反映） |
| 动作表达力 | 1 个 (task, mode) 控制全部单位 | 逐单位动作头：farmer + 每个 hand + market 独立决策 |
| 对手太强学不到 | 首轮就打 barnyard（全败，无正向信号） | 课程：starter → barnyard → strongest |
| 胜负对齐 | 绝对收益 | 相对势 Φ(mine) − Φ(opp) + 终局 ±15 |

## 2. 势函数设计（rl/potential.py）

势函数估算「从这个状态打到终局，预期净资产是多少」（单位：美元）：

```
Φ(s) = money
     + Σ shed[item] × base_price[item] × 0.9        # 库存（略低于基础价：卖出会压价）
     + Σ seeds[crop] × seed_cost × 0.5              # 种子残值
     + Σ_plant  预期剩余收获量 × base_price × 0.5    # 关键：种植即入账
     + Σ_animal 预期剩余产出 × base_price × 0.4      # 动物未来产出
     − Σ 未喂食/未照料动物 × 重置成本 × 0.8           # 逃跑风险
     − Σ_weeds 25                                    # 每棵杂草占一格的机会成本
     + len(hands) × 40                               # 雇工生产力资产
     + (已开地块数 − 1) × 300                         # 土地资产
```

其中「预期剩余收获量」：
- ongoing 作物（TOMATO/STRAWBERRY）：`days_left / interval × max_yield`
- 一次性作物（WHEAT/CARROT/MELON）：`1 × max_yield`（尚未收获时）

环境每步返回：

```
r' = (Φ_rel(s') − Φ_rel(s)) / 1000     # Φ_rel = Φ(mine) − Φ(opp)
done 时加 ±15                            # 胜 / 负
```

**性质**（Ng, Harada & Russell 1999）：势函数整形不改变最优策略，
只把长周期的因果链压缩成即时信号。种 melon（种子 $80）瞬间 Φ 上升约
`6 × 250 × 0.5 = $750`，浇水保住作物避免 Φ 下跌，除草 +25 —— 每个
中间行为都有了梯度。

## 3. 动作空间（multi-head）

策略网络 trunk：75 → 256 → 256（tanh）
输出头：

| 头 | 维度 | 说明 |
|---|---|---|
| farmer_task | 13 | farmer 本回合任务 |
| hand_task × 12 | 13 × 12 | 每个 hand 独立任务（按激活数量 mask） |
| market_mode | 4 | HOLD / METERED / DUMP / RESTOCK |
| value | 1 | Critic |

log π = Σ 各头 log-prob（multi-discrete 标准分解）。
IDLE 任务 → 该单位走默认调度器（保底行为）。
导出文件为单文件纯 Python agent，可直接提交 Kaggle。

## 4. 训练配置

```bash
python -m rl.train_ppo --arch multi \
    --iters 300 --episodes 8 --workers 12 \
    --opponents starter,agents/barnyard.py,benchmarks/strongest.py \
    --switch-after 100 --pga-frac 0.3 \
    --gamma 0.997 --entropy 0.003 --lr 3e-4 \
    --ckpt-dir rl/ckpt_official
```

- 课程：iter 1–100 vs starter（弱敌 → 能赢 → 正向终局信号），
  101–200 vs barnyard，201–300 vs strongest
- γ=0.997，λ=0.95，clip=0.2，3 epochs，minibatch 512
- entropy 0.003（14 个头求和，系数调低防过散）
- 断点续训：`--init-weights rl/ckpt_official/ppo_it0300.npz`

## 5. 导出提交

```bash
python -m rl.export_multihead --arch multi --weights rl/ckpt_official/ppo_it0300.npz --out agents/rl_agent.py
python tools/stress.py agents/rl_agent.py -j 8   # 28 项病态配置
python tools/eval.py h2h agents/rl_agent.py agents/barnyard.py --seeds 48 -j 8
```

## 6. 文件结构

```
rl/potential.py      # 势函数（纯 stdlib，可嵌入 agent）
rl/action_space.py   # decode_per_unit：逐单位解码
rl/env.py            # KaggEnvMulti：势函数奖励 + 逐单位 step
rl/ppo.py            # MultiHeadMLP + ppo_update_multihead
rl/rollout.py        # 并行 worker（按 arch 分发）
rl/train_ppo.py      # --arch single|multi
rl/export_multihead.py   # npz multi-head 单文件导出（torchrl 导出仍是 rl/export_agent.py）
rl/gpu/              # 张量化训练引擎（可选，需 torch）
```

## 7. v1 失败复盘（存档）

- v1 奖励 `Δmoney/500` + 终局 ±5：ep_reward 在 −11 / −5 间震荡，
  策略收敛到「少亏躺平」局部最优，vs barnyard 0/64，中位数 $0。
- BC 预训练标签噪声大（剧本重放棋盘 diverged），task_acc 74% 无实际增益。
- 单任务头控制全部单位，策略无表达力，行为由静态调度器决定。

## 8. GPU 批量训练（`rl.gpu`）

CPU 训练慢，**不是因为 75→256 的 MLP**，而是因为官方环境每步 `deepcopy`
（一局 ~2.7 s，42% 在拷贝）。把网络单独搬到 GPU 几乎不加速。

真正能吃到 GPU 的做法：状态做成固定形状张量，一次 `step` 推进 B 局。
这套引擎在 `rl/gpu/`。规则用官方录音重放对拍（`python -m rl.gpu.verify --suite`），
不要再用 selfcheck「starter 会种胡萝卜」当引擎回归。雇工张量上限 32、日结入库
按背包 dict 插入顺序。提交仍走 `export_agent` + 官方 Python interpreter；
GPU 日志里的胜率不是梯子分数。

```bash
pip install -r requirements/gpu.txt          # torch
python -m rl.gpu.selfcheck                   # CPU 冒烟
python -m rl.gpu.verify --seeds 7,13 --left starter --right starter
python -m rl.gpu.verify --seeds 7 --left agents/barnyard.py --right starter
python -m rl.gpu.train --device cpu --batch 256 --iters 200 \
    --opponent starter --switch-after 80 \
    --init-weights rl/ckpt_official/ppo_it0300.npz --ckpt-dir rl/ckpt_gpu
python -m rl.export_multihead --arch multi --weights rl/ckpt_gpu/ppo_it0200.npz \
    --out agents/rl_agent.py
```

- `--device cpu`：本机 RTX 4060 上测过，一轮 256×720 约 132s；同配置 CUDA
  约 246s（核启动绑定，卡没吃饱）。`--device auto` 有 CUDA 就会选中它，
  在这类笔记本上是更慢的路径。数据中心大卡另测。
  即便没有 GPU，向量化 CPU（B=256）也比 8 进程 × kaggle deepcopy 采得更多。
- 对手：`starter`（官方胡萝卜循环）→ `--switch-after` 之后换成 `scripted`
  （全部 IDLE + RESTOCK，即默认农场调度，近似 barnyard 的农活）。
  真正的 `barnyard.py` 仍只能在 CPU 官方引擎上打。
- 权重格式与 CPU PPO 相同，可直接 `export_agent`。
- 集群锦标赛**仍然不要申请 GPU**（那是 deepcopy 负载）；这套脚本是本机
  / 带卡机器上的训练路径。
