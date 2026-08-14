# rl/ — 强化学习基线

`rl-baseline` 分支的实验线：一个每回合读取棋盘状态、在 720 步时序上学习的
模型驱动 agent。本文件是初版方案的全部选择及其理由；代码是方案的落地。
**这条线是研究性质的，一切最终验收仍走 `docs/VALIDATING.md` 的规矩。**

## 0. 这条线在项目里的定位

先承认已知格局（`docs/ROADMAP.md` §7）：在线调度器封顶 ~857；天梯顶端是
「剧本 + 市场外包装」；路线 C 是唯一还有前 10 天花板的路。RL 有三种兑现方式，
按落地难度递增、按天梯相关性递减排列正好相反：

1. **RL 学市场外包装**：farm 动作来自现成剧本，RL 只重写 `action["market"]`。
   与路线 C 完全对齐——实测价值本来就在外包装上（裸剧本对包装 agent 0/3072）。
2. **RL 作为剧本生成器**：完整 policy 在固定 seed 上 rollout，录下动作序列，
   套现成外包装提交。RL 不需要在所有 seed 上强，只要在一次 rollout 里强。
3. **RL 直接当完整 policy 提交**：最难（720 步 credit assignment、部署约束），
   学术上最有意思。

**v0 脚手架同时服务三者**——环境包装、观测编码、reward 管道是公共的。先按
方式 3 的最简版把管道跑通（M0/M1），M3 时用测量决定往 1 还是 3 走。

## 1. 里程碑（每个都有过/不过判据）

| | 内容 | 过关判据 |
|---|---|---|
| **M0** | 脚手架：环境包装 + 观测编码 + 动作空间 + 随机合法策略 | 随机策略完整跑完 720 步不崩，观测/掩码/解码全程无异常（`rollout.py` 绿灯）✅ |
| **M1** | PPO 启动（MLP，双头 categorical，掩码） | 学习曲线可见地脱离随机基线；对 `starter` 胜率 > 90%（96 seeds × 双席位） |
| **M2** | 变强：HIRE + 雇工共享策略；课程 starter → barnyard → bench3 → spar；BC 预训练选项 | 对 `barnyard` 胜率 > 60%（96 seeds） |
| **M3** | 分叉决策：完整 policy vs 学习型市场外包装（路线 C） | 用 panel 1,920 局数字决定，不用直觉 |

## 2. 环境接口（M0，已实现）

```
rl/kg_env.py     KGEnv：gym 风格 reset/step，kaggle_environments train 接口，
                 对手可以是注册名（"starter"）或任意 agent 文件路径
rl/obs.py        obs dict → 定长 float32 向量（OBS_DIM），net_worth() 势函数
rl/actions.py    因子化动作空间：farmer 头 + market 头，合法性掩码，宏动作执行器
rl/rollout.py    M0 冒烟测试：随机合法策略跑完整局
```

冒烟测试（单局约 3 s，登录节点允许）：

```bash
source setup_env.sh
python rl/rollout.py --episodes 1 --opponent starter --seed 1000
```

速度账：`KG_FAST_ENV` 打开后单局 ~2.6 s，即单核 ~275 步/s。框架开销
（deepcopy 42%）动不了，所以吞吐靠进程并行：32 workers ≈ 8–9k 步/s，
一千万步 ≈ 20 分钟。**训练是 CPU 任务，环境是瓶颈，永远不要申请 GPU。**

## 3. 观测编码（`rl/obs.py`）

环境近乎全知：双方农场、市场库存、价格、商店全部可见；**对手的 shed/种子
不可见**（在 `private` 里），只能从市场库存变化反推（`kg_rules._town_drain`
已有确定性扣除，M2 再做）。

编码为一个扁平向量，三段：

- **两张 10×10×24 棋盘**（自己在前，对手在后）：格子类型、作物/动物 one-hot、
  yield_units、浇水/施肥/喂食/照料状态、连续失水/失喂计数、农夫与雇工位置。
- **全局向量**：钱（双方，log 尺度）、day/hour、九种产品的价格（除以 base）
  和库存偏移（(I0−inv)/T）、自己的 shed/种子/随身物品、土地解锁、商店计数。
- 布局由代码即文档；`OBS_DIM` 导入时计算，改编码不需要同步魔法数字。

MLP 直接吃扁平向量；棋盘段保留了 (通道, y, x) 结构，v1 想上 CNN 时零成本切换。

## 4. 动作空间（`rl/actions.py`）——最重要的设计决定

原始动作空间是结构化字典（farmer + 每个雇工 + 最多 10 条市场指令），且
**非法动作是静默 no-op**。直接学原始动作，随机策略几乎每步都在打空气，
学习信号会淹死。两条对策，都已实现：

**a. 宏动作 = 「朝完成意图走一步」的贪心实现。** farmer 头的每个选项是一个
意图（"浇最近的未浇水作物"、"喂最近的饿动物"），执行器把它翻译成本回合的
一个原始动作：站在目标上就执行，否则朝最近目标贪心走一步；需要物资的意图
（FEED 要小麦、FERTILIZE 要肥料）自动插入去 shed PICKUP 的腿。执行器无状态，
每回合重新决策，policy 随时可以换意图。这把有效 horizon 从 720 压到 ~百级
（榜首的动作直方图：每个有效动作只花 1.09 步移动）。

**b. 合法性掩码。** 每个头输出前对 logits 加 mask（无未浇水作物 → WATER
被掩掉；shed 里没货 → SELL 被掩掉）。掩码只管机制可行性，不管好坏——
"什么时候卖"是学的，"卖空气"是掩的。掩码从宽：漏掩的动作执行器兜底成 PASS。

两个头，每步各采样一个：

- **farmer 头（23）**：PASS，4 方向微操，WATER / HARVEST / FEED / CARE /
  COLLECT_FERT / FERTILIZE / DIG_WEED（各取最近目标），PLANT×5，
  BUILD_COOP / BUILD_PASTURE，PLACE×3，DROP（回 shed 卸货）。
- **market 头（21）**：NOOP，SELL_ALL×9，BUY_SEED×5，BUY_WHEAT(×5)、
  BUY_FERT(×1)，BUY_ANIMAL×3，BUY_LAND。每回合最多一条指令（上限是 10，
  留给 M2/外包装模式用）。

**v0 故意不含 HIRE。** 雇工是支配性的轴（crew 55% vs 不雇 ~35%），但每个
雇工要一个动作、雇工每天重生成，是脚手架之外的一整块（共享策略、可变数量
单位）。M2 第一优先级。

## 5. Reward 设计

- **终局真值是胜负（±1），不是钱。** 竞赛只记 win；这个项目已经被钱这个
  proxy 坑过一次（CLAUDE.md「Watch rank against money」）。
- **过程用 dense shaping 启动学习**：每步 `Δ net_worth`，其中
  `net_worth = 钱 + shed 存货按当前价 + 种子按买价 + 圈里/棚里的动物按买价
  + 在田作物按种子价 + 未收 yield 按当前价`。把在田资产计进势函数，
  种地/放animal才不会被瞬时惩罚。
- 组合：`r_t = Δnet_worth/3000 · w_shape + 终局 win·1.0`，`w_shape` 计划从 1
  退火到 0.2——shaping 负责起步，胜负负责收尾。
- **已知 hacking 风险**：net_worth 用边际价估存货，大仓位实际清仓价更低；
  卖到 $1 地板的单位不进市场库存。如果学习曲线涨而 eval 胜率不涨，先查这里。
  **汇报数字永远来自 `tools/eval.py`，不来自训练曲线。**

## 6. 网络选择

- **v0：MLP**。`obs(~5.5k) → 512 → 256 → {farmer 头, market 头, value 头}`，
  约 3M 参数。理由：环境近乎全知、观测已手工特征化，先让管道证明自己。
- **刻意保持小**：提交端约束是 1 s/回合纯 CPU，而且计划**导出 npz 用 numpy
  写前向**——提交包不带 torch 依赖，`package.sh` 直接打包，规避 Kaggle 端
  环境不确定性。这个尺寸的 MLP numpy 前向 <1 ms。
- v1 升级项（按需，不预支）：棋盘段上小 CNN；若发现需要记忆（对手建模、
  市场趋势）再加 GRU——先试帧堆叠（价格近 k 步差分进观测），大概率够。

## 7. 训练方法

- **PPO**，CleanRL 风格单文件自写（`rl/train_ppo.py`，M1）。不引 SB3/RLlib：
  因子化双头 + 动作掩码 + 自定义环境，自写比改框架短。两个头的 log-prob
  相加当联合动作；GAE(λ=0.95)，γ=0.999（720 步 horizon，γ 不能低）。
- **并行**：SubprocVecEnv 式多进程 rollout worker（环境 2.6 s/局是瓶颈）。
  调试在 salloc 交互节点，长跑 `sbatch`（CPU-only，32–64 核）。
- **课程**：starter → barnyard → bench3 → `agents/spar/`（真实榜首轨迹重建的
  对手）。固定对手先学会赢，再混对手池防过拟合；league/自博弈是 M3 选项。
- **种子纪律**：训练随机 seed；评估固定池且与 `eval.py` 的 10_000+ 段隔离。
  episode 对 (seed, 双方) 确定，同 seed 重复不加信息。

## 8. 训练数据

- **主来源：on-policy rollout**，PPO 自产自销。
- **加速器（M2 选项）：行为克隆预训练。** `tracelib` 剧本库（`dist/`，3 MB）
  有 156 条真实榜首轨迹——先监督学习「状态 → 榜首动作」，再 PPO 微调。
  这是把「剧本」知识注入 RL 的最直接管道，也是方式 1（学外包装）的天然起点。
  注意宏动作空间和剧本的原始动作需要一层反向映射（原始 → 最近意图），
  做之前先量映射覆盖率。

## 9. 评价体系

- **训练内**（只用于调参，不用于汇报）：平均终局钱、对固定对手滚动胜率、
  各动作使用率（宏动作退化成全 PASS 是最常见的死法，要在曲线上看得见）。
- **汇报**：`tools/eval.py h2h <exported>.py <opponent> --seeds 96 -j 32`，
  双席位 + Wilson 区间。最终 yardstick 是 panel 1,920 局，规矩同所有 agent。
- **任何导出的 agent 先过**：`stress.py` 28/28，`trace.py` 人工看一集，
  `package.sh` 自验（`get_last_callable` 陷阱：模块级最后一个可调用对象
  必须是 agent 本身——numpy 前向的辅助函数要么藏进列表要么 `del`）。

## 10. 依赖与部署

- torch 只进**独立的训练 venv**（不动主 `venv/`，agent 运行时不依赖它）：
  ```bash
  # 在 salloc/sbatch 内，不要在登录节点装
  module load python/3.11 && python -m venv $SCRATCH/kg-rl-venv
  source $SCRATCH/kg-rl-venv/bin/activate
  pip install --no-index torch numpy
  ```
- 提交物 = `rl_agent.py`（numpy 前向 + obs/actions 两个模块的拷贝）+
  `weights.npz`，`tools/package.sh` 打包。快照进 `submissions/<date>-<name>/`，
  命名遵守仓库规矩：语义名（如 `groundhog.py`），**没有版本号**；basename
  是数据库主键，别和现有 agent 撞名。

## 11. 预先登记的风险

1. **720 步稀疏胜负 + shaping 仍学不动** → 宏动作已压 horizon；下一档是
   BC 预训练（§8）；再下一档是切方式 1（外包装模式 farm 侧全部固定）。
2. **Reward hacking**（§5 已列）→ 每次汇报走 eval.py，观察 rank-vs-money。
3. **非传递性**：对 starter 学出的策略对 wrapped 可能一文不值——本仓库
   实测过「本地全胜、天梯打平」。课程后期必须混 `agents/spar/`，验收看 panel。
4. **对手固定导致过拟合对手**：对手池随机采样 + 评估用 held-out 对手。
5. **训练吞吐不够** → 先量（M1 第一天就有数字），不够就 sbatch 多节点
   collect + 中心学习器；每核 275 步/s × 1,536 核的上限在那，够 PPO 用。
