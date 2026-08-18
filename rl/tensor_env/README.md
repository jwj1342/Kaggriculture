# tensor_env — 张量化对局引擎与 GPU 训练闭环（`tensorize` 分支）

> **一句话**：把 Kaggriculture 的整局对局（棋盘、农场动作、市场逐单位结算、
> 城镇、每日刷新）和策略网络全部搬成 `(B, …)` 张量运算，B 个对局并行推进；
> 与竞赛参考引擎**逐字节一致**（CPU 与 CUDA 双设备验证），单张 L40S 每秒推进
> **22.8 万对局步**，GPU 端 PPO **18 分钟**从零学会打赢基线。

**B0–B4 七个阶段全部完成并过门，2026-08-18 与 `rl-baseline` 一起并入
`main`**；其上是 TorchRL 统一层（本目录 `trl_env.py`/`trl_policy.py`，训练
入口 `rl/train.py`，见 `rl/README.md`「TorchRL 统一层」）。设计宪法与逐阶段
数字见 `DESIGN.md`；本文是给合作者的入口：架构、每个文件是什么、怎么用、
怎么验证。**没有任何 Slurm/集群假设**——笔记本 CPU 能跑全部功能与全部门。

---

## 1. 为什么做这个

`rl-baseline` 分支（见其 `rl/README.md` §13 复盘）证明：RL 线的瓶颈在结构与
探索，不在优化器；而任何下一步（更大网络、逐雇工控制、仓库路线 C 的计划空间
搜索、大规模自博弈）都需要**便宜几个数量级的对局吞吐**。旧管线单核 ~275
步/秒、32 核 9.2k 步/秒，其中 42% 是框架 deepcopy——算力堆不动。

出路是让环境本身变成张量：不是"加速 Python"，而是换一种计算形态。前提有一条
铁律：**训练引擎的任何偏差都会训出"错误世界的最优解"**（仓库 §11 有整节
血泪账），所以每一层张量化都必须对参考引擎逐字节验证，"近似正确"不存在。

## 2. 架构：三层验证链条

```
kaggle 参考引擎 (reference/engine/kaggriculture.py)      ← 竞赛真值，一行不改
        ⇑ verify.py：同 (seed, 动作流) 全状态逐步 diff
engine_np.py     单局 dict 引擎，参考的逐字节移植             ← 所有张量实现的预言机
        ⇑ verify_t.py：G1 逐字节 / G2 批一致 / G3 市场风暴
engine_t.py      批量张量引擎 EpisodeT (B 局 lockstep, CPU/CUDA 同一代码)
   ├─ engine_t_idx.py   step_idx：张量原生动作路径（策略出索引，设备上解码）
   │      ⇑ test_b3b.py：step_idx(f,m) ≡ step_raw(decode(f,m)) 逐字节
   ├─ features_t.py     encode_t / masks_t：设备上特征与掩码
   │      ⇑ test_b3.py：与 CPU 参照 obs.encode / actions.*_mask 逐位相等
   ├─ potential_t.py    net_worth_t：设备上塑形势函数
   │      ⇑ test_b4c.py (i)：与 CPU 参照 obs.net_worth 逐位相等
   ├─ opponents_t.py    张量态 starter 对手（(B,) gather 直取决策）
   │      ⇑ test_b4a.py：与参考 starter 逐动作一致
   ├─ policy_t.py + train_t.py   同驻 GPU 的手写 PPO 闭环（A/B 对照臂）
   │      ⇑ test_b4c.py (iii)：学习曲线门
   └─ trl_env.py + trl_policy.py   TorchRL 统一层：EnvBase 批量环境 + 双头掩码分布
          ⇑ test_trl.py：策略/环境/GAE 与手写路径逐位对齐 + 双算法训练冒烟
          （训练入口 rl/train.py，loss 可替换）
```

每个 `⇑` 都是全状态/全向量的**精确判等**（`verify.first_diff`、
`np.array_equal`、float64 `==`），不是容差比较。评测纪律不变：竞赛评测
（`tools/eval.py`）永远跑参考引擎，训练引擎的偏差只允许表现为 train/eval
失配，绝不污染测量。

## 3. 文件地图

| 文件 | 角色 | 关键实现要点 |
|---|---|---|
| `DESIGN.md` | 分支宪法：五个设计决策 D1–D5、七阶段验收门、GPU 申请理由、风险登记、状态布局（附录 A）、训练闭环设计（附录 B）、全部实测数字 | 改任何东西前先读 §3 决策 |
| `engine_np.py` | 参考引擎的逐字节移植（预言机） | 近乎逐行转写；`snapshot()` 是所有门的比较结构 |
| `verify.py` | 预言机 vs kaggle 引擎的门 | `first_diff` 是全项目共用的精确 diff |
| `engine_t.py` | **批量张量引擎** `EpisodeT(seeds, episode_steps, device)`；`step_raw(dicts)`（验证接口）、`snapshot(lane)`、`done`、`reward` | D1 全整型状态 + 价格查找表（对着 `engine_np.market_price` 制表，跨设备位精确）；D2 混合步进：每日 RNG 段用宿主一次 `getrandbits` 拉出 MT19937 原始字，设备上重建浮点、比较、scatter 杂草，商店抽取同一批（逐字节保真）；D3 市场逐单位循环串行于单位序、每次迭代 (B,2) 张量同时报价/提交双方；插入序敏感的库存用宿主侧序列元数据镜像 dict 语义 |
| `engine_t_idx.py` | **张量原生热路径** `step_idx(f_idx (B,2), m_idx (B,2))` | 宏意图设备上实现：最近目标 (dist,y,x) 字典序、贪心一步 `_step_toward`、取货腿、雇工调度器（LUT 驱动、无同步的 index_put 抢占）、复合市场指令；与 `step_raw∘decode` 逐字节等价 |
| `features_t.py` | `encode_t(ep,p)→(B,4867)f32`、`masks_t(ep,p)→((B,23),(B,22))bool` | 分数通道 float64 后降 f32（CUDA f32 除法差 1 ulp 的教训）；唯一宿主计算 = money 的 log1p 两槽（libm 不可跨设备复现） |
| `potential_t.py` | `net_worth_t(ep,p)→(B,)f64` | 与 `rl/obs.py::net_worth` 同语义：基准价、土地记账、终局衰减、流动性溢价 |
| `opponents_t.py` | `starter_actions` / `starter_indices` | 训练路径用索引形式；文档化的近似：market 头单选（参考 starter 偶发同回合买+卖） |
| `policy_t.py` | `PolicyT`：actor 4867→512→256→双头（掩码 −1e9），critic 独立 4867→256→256→1 | 与 rl-baseline `policy.py` 同构，可 `--hidden` |
| `train_t.py` | 同驻设备的采集 + 手写 PPO（GAE γ=0.999 λ=0.95、clip 0.2、独立 critic、熵 0.003） | 被 `rl/train.py`（TorchRL）取代，保留作 A/B 对照臂（`slurm/rl_ab.sh`） |
| `trl_env.py` | **TorchRL 统一层**：`KGTensorEnv(EnvBase)`，batch_size=[B] 的批量环境（VMAS/Brax 模式），对手内置（starter / 冻结权重 argmax） | 语义 = `train_t.collect` 逐位复刻；完整局 = `episode_steps - 1` 步、lockstep 终局、全局 reset；`money`/`opp_money` 随观测携带 |
| `trl_policy.py` | `ActorNet`/`CriticNet`（与 `PolicyT` 同名同序参数，checkpoint/导出契约不变）+ `TwoHeadMasked` 联合分布 | 掩码双头数学与手写逐位一致；A2C 的解析熵经 `HAS_ENTROPY` 注册 |
| `test_trl.py` | 统一层的四道门 | (i) 策略逐位 (ii) 环境逐位 (iii) GAE (iv) specs + ppo/a2c 冒烟 |
| `bench.py` / `profile_t.py` | 引擎对比基准（含双卡 map-reduce 原型）/ 逐阶段剖析器 | 数字见 §5 |
| `test_*.py`, `verify_t.py` | 验收门 | 见 §4 |
| `adapter.py`, `test_fused.py` | rl-baseline 继承的 engine_np gym 适配与融合特征门 | — |

## 4. 怎么用

```bash
source setup_env.sh                       # 或自己的 venv
pip install -r requirements/rl.txt        # torch；集群上 --no-index

# 全部验收门（笔记本 CPU 几分钟；有卡加 --device cuda）
python rl/tensor_env/verify_t.py                    # 引擎：G1/G2/G3
python rl/tensor_env/test_b3.py  --steps 240        # 特征+掩码逐位
python rl/tensor_env/test_b3b.py --steps 240        # step_idx 逐字节等价
python rl/tensor_env/test_b4a.py --steps 240        # 张量 starter
python rl/tensor_env/test_b4c.py --minutes 6        # 势函数逐位 + 学习曲线

# 训练（GPU 上 B=1024, 60 轮 ≈ 18 分钟即 100% 胜 starter）
python rl/tensor_env/train_t.py --device cuda --B 1024 --iters 60 --lr 3e-4

# 基准
python rl/tensor_env/bench.py --engines kaggle np t-cpu            # CPU
python rl/tensor_env/bench.py --engines t-gpu t-multi --devices 0 1
```

最小 API：

```python
import sys; sys.path[:0] = ["rl", "rl/tensor_env"]
import torch, engine_t, engine_t_idx, features_t   # engine_t_idx 注入 step_idx
ep = engine_t.EpisodeT(seeds=list(range(1024)), episode_steps=720, device="cuda")
while not ep.done:
    x = features_t.encode_t(ep, 0); fm, mm = features_t.masks_t(ep, 0)
    # ...策略前向、按掩码采样双方 (B,2) 索引...
    ep.step_idx(f_idx, m_idx)
snap = ep.snapshot(0)      # 与参考引擎 snapshot 同构的 dict
```

**热路径永远用 `step_idx`**；`step_raw` 只给验证门和录制流回放。

## 5. 数字（全部实测，详见 DESIGN.md §4/§4.5）

| 指标 | 数值 |
|---|---|
| kaggle 参考引擎 | ~800 lane-steps/s |
| engine_t **单卡 L40S，B=4096，真实策略负载** | **228.6k**（含掩码+采样 142.5k） |
| engine_t CPU B=4096 | 173.5k |
| 双卡 map-reduce 原型 | ~95% 线性效率 |
| GPU 端 PPO 学习曲线（B=1024） | 胜率 0→62%（it18）→100%（it30，18 min，44M 步） |
| 端到端训练吞吐 | ~40k lane-steps/s（采集占 95%，更新已不是瓶颈） |

## 6. 三条纪律（合作者必读）

1. **正确性来自门，不来自信任**：改 `engine_t*/features_t/potential_t` 后必跑
   对应门；CUDA 改动必须在 CUDA 上跑门（f32 除法在 CPU 位精确、CUDA 差 1 ulp
   是真实发生过的回归）。
2. **参考的算术是预言机，不是设备 libm**：任何浮点通道走"float64 计算再降
   f32"，与 `rl/obs.py` 同路径。
3. 升级 `kaggle-environments` 后先跑 `verify.py`（链条第一环），红了先修
   `engine_np.py`，再一路向上重验。

## 7. 剩余瓶颈与下一步（记录在 DESIGN.md B4b 行）

每步 ~6.9k 小算子的发射开销已成地板（CPU 上每个 ~2µs，GPU 上 launch-bound
同理）；每步残留的几处宿主同步（`hands_n.max()`、存在性表、市场循环终止
测试）在 GPU 上是显式 sync。下一档是 CUDA graphs / 槽位融合、设备侧 MT19937
（消掉每 lane-day ~8µs 的 `Random()` 构造），以及 B5：计划空间搜索原型
（仓库路线 C）——本引擎每小时可评估的候选数已足够支撑。
