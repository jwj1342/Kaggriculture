# rl/ — 强化学习线

每回合读取棋盘状态、在 720 步时序上学习的模型驱动 agent。这条线经历了两代：
`rl-baseline`（手写 CPU PPO，按收敛证据收口，判词与复盘见下）与 `tensorize`
（GPU 批量张量引擎，`tensor_env/README.md`）；2026-08-18 两者并入 `main`，
以 **TorchRL 作为统一训练框架**粘合。本文其余部分是初版方案的全部选择及其
理由，以及它的复盘——**§13 的结构性结论至今成立**，统一层解决的是工程形态
（一套引擎、一套策略、可换算法），不是那面结构的墙。
**这条线是研究性质的，一切最终验收仍走 `docs/VALIDATING.md` 的规矩。**

## TorchRL 统一层（2026-08-18 起）

CPU 线与 GPU 线的二元性由 TorchRL 消掉：`EpisodeT` 本就是设备无关的批量
引擎，包一层 `EnvBase`（`tensor_env/trl_env.py`，VMAS/Brax 同款模式）后，
`--device cpu/cuda` 就是全部切换。采集是 TorchRL collector，优势估计是
`GAE`，更新是可替换的 loss 模块——**换算法 = 换 `--algo`**（ppo/a2c；往
`rl/train.py` 的 `_LOSSES` 加一行即是第三个）。

    pip install --no-index -r requirements/rl.txt  # 作业内装；torch 锁 ~=2.10.0（wheelhouse tensordict 的硬要求）
    python rl/tensor_env/test_trl.py               # 四道门：策略/环境/GAE 逐位对齐 + 双算法冒烟（CPU，分钟级）
    python rl/train.py --device cuda --B 1024 --iters 60     # A/B 规模；--device cpu 同一份代码
    sbatch slurm/rl_ab.sh                                    # 手写 vs TorchRL 同预算 A/B（本仓库唯一 GPU 作业）
    RUN=trl-ab CKPT=trl.pt NAME=<name> sbatch slurm/rl_eval.sh   # 导出 numpy agent + 十对手花名册 h2h

组件对应：`tensor_env/trl_policy.py` 的 ActorNet/CriticNet 与 `policy_t.py`
同名同序（checkpoint 键 `model` + `hidden`，`export_agent.py`、weights.npz
八数组契约、`tools/package.sh` 提交管线原样可用）；`TwoHeadMasked` 分布与
手写掩码双头数学逐位一致（`test_trl.py` 门 (i)）。`train_ppo.py` 与
`tensor_env/train_t.py` 是被取代的两代手写循环，暂留作 A/B 对照臂，
A/B 通过后退役。

> ## 终局判词（2026-08-15，给后来者——先读这个）
>
> 这条线已按收敛证据收口。**终态：本地花名册 4/10**（random/starter 100%,
> 两条真实录音 79.2%/63.5% 宽区间锁定），1.2 亿步、四个收敛信号并发后停止;
> 交付物 `rl/runs/m2/deliverable-guarded.pt` + `rl/out/deliverable-guarded/`,
> 预估天梯 ~550–700（barnyard/enhanced 档 ~857，天梯顶端 2599）。
>
> **上限在哪、为什么**：一句话——我们用 RL 的零件搭了一台在线调度器,
> 所以收敛到了在线调度器的天花板（与本仓库原子库撞的是同一面墙,
> `docs/ROADMAP.md` §7A）。瓶颈不在优化器,在结构。完整的七因分析在
> **§13 复盘**,三条出路及其置信度排序在 §13 末尾与 `TODO.md`。
>
> 顺带的资产：训练吞吐基建（逐字节验证的引擎移植 43×、融合特征栈、整局
> 异步采集,合计 ~900→9,200 步/秒）对任何后续路线可直接复用——尤其是
> 路线 C 的计划空间搜索,它的算力成本被这套东西打下来了 40 倍。

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
- **market 头（22）**：NOOP，SELL_ALL×9，BUY_SEED×5，BUY_WHEAT(×5)、
  BUY_FERT(×1)，BUY_ANIMAL×3，BUY_LAND，HIRE。每回合最多一条指令
  （上限是 10，留给外包装模式用）。

**雇工 = 战略雇佣、脚本劳动。** crew 轴支配其他所有轴（crew 55% vs swarm
10%），不能留在动作空间外；但逐雇工的 RL 控制（共享策略、可变数量单位）
是一整块工程。折衷：market 头拥有 HIRE（何时雇、雇多深入 fib 成本曲线），
调度器把每个雇工派给一步免耗材杂务（收获 > 浇水 > 照料 > 捡肥 > 除草，
背满 8 件回 shed 卸货）；FEED 因为要小麦物流留给农夫。策略的杠杆是雇工
规模与时机，不是微操。逐雇工 RL 控制降级为后续可选项。

## 5. Reward 设计

- **终局真值是胜负（±1），不是钱。** 竞赛只记 win；这个项目已经被钱这个
  proxy 坑过一次（CLAUDE.md「Watch rank against money」）。
- **过程用 dense shaping 启动学习**：每步 `Δ net_worth`，其中
  `net_worth = 钱 + shed 存货按当前价 + 种子按买价 + 圈里/棚里的动物按买价
  + 在田作物按种子价 + 未收 yield 按当前价 + 已购土地按地价`。把在田资产
  和土地计进势函数，种地/放动物/买地才不会被瞬时惩罚。
- 组合：`r_t = Δnet_worth/3000 · w_shape + 终局 win·1.0`，`w_shape` 计划从 1
  退火到 0.2——shaping 负责起步，胜负负责收尾。
- **已知 hacking 风险**：net_worth 用边际价估存货，大仓位实际清仓价更低；
  卖到 $1 地板的单位不进市场库存。如果学习曲线涨而 eval 胜率不涨，先查这里。
  **汇报数字永远来自 `tools/eval.py`，不来自训练曲线。**

## 6. 网络架构与 actor-critic 参考（`rl/policy.py`）

给合作者的完整参考：结构、每个函数是什么、在哪条路径上被谁调用。

### 6.1 结构（两张独立的网，刻意不共享）

```
actor（策略侧，会被导出）           critic（价值侧，永不导出）
obs (4867)                          obs (4867)
  │ l1: Linear 4867→512, relu        │ v1: Linear 4867→256, relu
  │ l2: Linear 512→256, relu         │ v2: Linear 256→256, relu
  ├─ farmer: Linear 256→23 logits    └─ value: Linear 256→1
  └─ market: Linear 256→22 logits
```

- 观测 4867 维 = 两张 (24,10,10) 棋盘块（自己+对手）+ 67 维全局向量（§3）。
- **actor 与 critic 零共享参数**——不是风格偏好，是事故结论（§11 缺陷 2）：
  共享主干时"只训 value 的热身"仍会顺着主干反传、拆掉 BC 克隆好的策略
  （实测 30k 教师塌到 $200）。分开之后 `--freeze-policy-until` 才真正成立。
- 初始化：主干正交初始化 gain√2；**两个动作头 gain 1e-4（近零）**——未训练
  策略在合法动作上近似均匀，探索从掩码指向的地方开始而不是 logit 空间的
  随机角落。隐藏层尺寸随检查点携带（`--hidden H1 H2`，恢复/导出端自适应）。

### 6.2 因子化动作与掩码机制

两个头各是一个独立的 Categorical；**联合动作 = (farmer, market) 一对**，
联合 log-prob = 两头 log-prob 之和，联合熵 = 两头熵之和。采样前对 logits
`masked_fill(mask==False, -1e9)`——非法动作零概率、零梯度（§4b）。

### 6.3 函数逐个说（policy.py 的公共接口）

| 函数 | 输入 → 输出 | 谁在什么路径上调用 |
|---|---|---|
| `trunk(x)` | obs → 256 维策略特征 | forward/evaluate 内部；BC 训练直接用它接头算 CE |
| `value_of(x)` | obs → V(s) 标量 | critic 独立前向；GAE 的价值来源 |
| `forward(x, fmask, mmask)` | → (farmer 分布, market 分布, V) | act/evaluate 的公共底座 |
| `act(x, fm, mm, deterministic)` | → (fa, ma, joint logp, V)，no_grad | **采集路径**：锁步 VecEnv 模式下主进程每步调用（采样）；评测/部署用 argmax 等价物 |
| `evaluate(x, fm, mm, fa, ma)` | → (新 logp, 熵, V) | **更新路径**：PPO minibatch 里对存储的动作重算 logp——`ratio = exp(new_logp − old_logp)` 的分子 |
| `state_np()` | → 8 个 float32 数组（l1w/l1b/l2w/l2b/fw/fb/mw/mb） | 权重快照：episode_pool 按代际发布给 worker；export_npz 落盘 |
| `export_npz(path)` | 写 weights.npz | 导出 agent / 联赛镜像刷新 |

### 6.4 三条路径上的 actor-critic 分工

- **采集（episode 模式，现行）**：worker 内用 `state_np()` 快照做 **numpy
  前向**（减最大值的 softmax 采样，数学与 torch 侧一致），记录 (obs, 掩码,
  动作, logp, reward)。critic 不进 worker——价值在主进程算。
- **更新（train_ppo.py）**：`value_of` 对整批 obs 出 V → 逐局 GAE
  （γ=0.999, λ=0.95，episode 模式终局 bootstrap=0，因为回合定长无截断）→
  优势标准化 → `evaluate` 出新 logp/熵 → PPO 裁剪目标（clip 0.2）+
  0.5·value MSE − 0.003·熵，梯度裁剪 0.5，Adam 1e-4。
  `--freeze-policy-until N`：global_step < N 时策略项置零、只训 critic
  （BC 后热身 + 每次课程晋级自动重冻结 100k 步）。
- **部署（导出 agent）**：只带 actor 的 8 个数组，numpy 前向 + 掩码 +
  **argmax**（确定性）。critic 不随部署走——它只服务训练期的优势估计。

### 6.5 尺寸与升级项

- 默认 512/256 约 3M 参数（actor 侧 ~2.6M）：1 s/回合纯 CPU 约束下 numpy
  前向 <1ms；容量实验的前置条件见 `TODO.md` #6。
- v1 升级项（按需，不预支）：棋盘段小 CNN（编码已保留 (C,y,x) 结构）；
  需要记忆再加 GRU——先试帧堆叠（价格近 k 步差分进观测），大概率够。

## 7. 训练方法

- **PPO**，CleanRL 风格单文件自写（`rl/train_ppo.py`，M1）。不引 SB3/RLlib：
  因子化双头 + 动作掩码 + 自定义环境，自写比改框架短。两个头的 log-prob
  相加当联合动作；GAE(λ=0.95)，γ=0.999（720 步 horizon，γ 不能低）。
- **并行**：SubprocVecEnv 式多进程 rollout worker（环境 2.6 s/局是瓶颈）。
  调试在 salloc 交互节点，长跑 `sbatch`（CPU-only，32–64 核）。
- **课程**（`train_ppo.py` 里自动推进，滚动胜率 ≥0.85 进下一阶段，进阶后
  30% 的局仍抽早期对手防遗忘）：starter → barnyard → w49 → w100（后两个是
  101 录音循环赛里最弱的两条，14–15% 胜率、中位收入 ~50k——它们是「打败
  一个录音」这一目标的靶子）。league/自博弈是 M3 选项。
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

**M1 目标花名册**（`slurm/rl_eval.sh`，固定十个本地对手，48–96 seeds × 双席位）：
random、starter、barnyard、enhanced/main、bench3/ledger_lena、bench3/broker_bea、
wrapped/w49、w100、w88、w50。目标 = 对其中至少一半 h2h 胜率 > 50%，且
至少一个 wrapped 录音被打过 50%。已知强度参照（arena 数据库）：starter ~3.5k、
barnyard 34–45k、enhanced/main 31–37k、lena/bea ~73–80k、最弱录音 ~50k。

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

## 11. 结果记录（本分支的 §11——合并主线时迁移到 docs/）

### 2026-08-15 ghost 里程碑达成

`milestone-ghost.pt` / `rl/out/milestone-ghost/`（BC → 19M 步 PPO，best.pt 棘轮）,
留出种子带（10k+）、双席位、n=288/只：

| 对手 | 胜率 | 95% CI | 钱差 |
|---|---|---|---|
| ghost-89825016（训练内） | 56.9% | [51.2%, 62.5%] | +2.9k |
| **ghost-89830307（留出）** | **60.4%** | [54.7%, 65.9%] | +5.2k |

同日全花名册（48 seeds × 双席位）：random 100%、starter 100%（中位收入
21.8k）；barnyard/enhanced/lena/spar/w49 全部 0%——并且对手对我们的收入是
其历史场地中位数的约 2 倍（barnyard 对我们 ~87k vs 场地内 34–48k）：
**对不压制市场的对手，所有强 agent 都会超常发挥**。这就是切换联赛自博弈
并加入竞争性塑形（`--opp-lambda`）的依据。

### 训练途中修掉的五个结构性缺陷（每个都有复现记录）

1. 导出加载器仿真错误：真实 `get_last_callable` 无 `__file__` 且 append
   sys.path → 独占模块名 + 从已导入模块推导权重路径。
2. 共享主干 + 价值热身毁掉 BC 克隆（30k 教师塌到 $200）→ 独立 value 网络。
3. 按市价 mark-to-market 的势函数让"不生产"在对手倾销时成为局部最优
   （12k→2k 蚀两次）→ 固定基准价计价。
4. argmax 终局烧钱（$14k 买永不成熟的种子、囤满仓不卖）→ 机制死线掩码 +
   势函数终局资产衰减。
5. 峰值-回落震荡（0.38→0.10）→ 熵 0.01→0.003 + best.pt 峰值棘轮。

### 2026-08-15 过夜攻坚的负结果账（负结果与胜利等值——仓库 §11 纪律）

目标是花名册第 5 分（main/barnyard/spar/lena/w49 档，对我们发挥 60–150k）。
以下每条都有 48–96 seed 双席位测量：

1. **联赛 PBT（λ=0.3，8 小时，~20M 步）**：镜像充胀滚动胜率至 0.84 并驱动
   best.pt 棘轮，**换掉了 ghost 技能**（56.9%→9.4%）。里程碑靠冻结副本存活。
   教训：棘轮指标必须与交付指标同构。
2. **λ=1.0 纯零和塑形**：策略学会"同归于尽"——对 main 96 局全部以恰好 $0
   收场（现金全部烧进市场对抗）。−69.9k，比 λ=0.3 更差。
3. **barnyard 神谕克隆（两轮）**：farmer 映射覆盖 98.6%、教师在我方席位挣
   48–51k，但克隆部署即塌（中位 $0/$23）。第一轮死于卖单标签 bug；第二轮
   暴露类别失衡（market 头 90% NOOP 标签 → 学成永远沉默）+ 79% 单步保真度
   在 720 步上的复利漂移。修复需类别加权 + DAgger，按止损规则停。
4. **ghost 带覆盖测量（20 只均匀抽样 × 24 局）**：里程碑 agent 带内胜率
   8.8% [6.5, 11.6]，赢 2/20。高编号（竞赛后期）ghost 全部 24-0 碾压——
   录音强度与回放时期强相关，花名册双 ghost 处在带的最弱端。
5. **复合市场指令**（清仓连卖、雇佣爆发）：方向正确（收入 12.5→15.7k）但
   不构成档位跃迁。

**结构性结论**：BC+PPO 在线策略在此宏动作空间的竞争收入天花板 ~20k；
60k+ 档需要能力跃迁，路径按成本排序在 `TODO.md`（market 头类别加权克隆
重试 → 分布式收集 → 张量化引擎）。这与仓库 §7A"在线调度器封顶"互证。

### 2026-08-15 下午：吞吐革命与自毁修复（正结果）

三次干预各自兑现，复利生效：

1. **吞吐 ×10**：引擎逐字节移植（43×）→ 特征单趟融合（逐位一致门）→
   整局异步采集（worker 内 numpy 推理）。训练 ~900 → ~9,200 步/秒。
2. **两个深 bug**：fork-BLAS 死锁（spawn 修复）；导出模块缓存串号——我们
   自己的两个导出同进程时第二个静默用第一个的权重（联赛自博弈曾失真,
   对外评测不受影响；per-export 模块名修复）。
3. **自毁模式治愈**：策略学出"全押开局"，坏杂草 roll 的种子上破产死亡
   （40% 局面 $0，连 starter 都掉到 58%）。修复 = HIRE 去穷雇地板 +
   势函数流动性溢价（前 $800 现金按 1.5×计）。修复后 starter/random 双
   100%（收入下限 20.9k，$0 局绝迹）。

**当前交付物**（`deliverable-guarded.pt` / `rl/out/deliverable-guarded/`,
1.03 亿步）：花名册 4/10 全部宽区间锁定——random 100% (+29.2k)、starter
100% (+23.9k)、ghost-89825016 79.2% [70,86]、ghost-89830307（留出）63.5%
[54,72]。中位收入 22–28k、下限 ~18k。ghost 全带 11.0%（后期录音健康剧本
30k+ 档仍不可及），60k+ 档（barnyard/main/spar/lena/w49）维持 0–2%。

### 2026-08-15 收敛判定与终版交付

1.196 亿步处四信号并发：win 平台（0.65±0.05，2,000 万步无提升）、熵单调降
（0.68→0.51）而性能不涨、value loss 平坦、快照间各对手 ±10pp 盆地震荡
（最新快照对 ghost-89825016 56.2% vs 冻结版同种子 79.2%）。**当前
"容量×奖励×对手分布"配置已到边界；继续训练是围着局部最优打转。**

**终版交付物 = `deliverable-guarded.pt` / `rl/out/deliverable-guarded/`**
（1.03 亿步快照，全花名册数字见上节：4/10 宽区间锁定）。goal 第三条
（本地 50%）终态 4/10；第 5 分需要换配置（TODO #1/2/6 三条路线）。

## 12. 预先登记的风险

1. **720 步稀疏胜负 + shaping 仍学不动** → 宏动作已压 horizon；下一档是
   BC 预训练（§8）；再下一档是切方式 1（外包装模式 farm 侧全部固定）。
2. **Reward hacking**（§5 已列）→ 每次汇报走 eval.py，观察 rank-vs-money。
3. **非传递性**：对 starter 学出的策略对 wrapped 可能一文不值——本仓库
   实测过「本地全胜、天梯打平」。课程后期必须混 `agents/spar/`，验收看 panel。
4. **对手固定导致过拟合对手**：对手池随机采样 + 评估用 held-out 对手。
5. **训练吞吐不够** → 先量（M1 第一天就有数字），不够就 sbatch 多节点
   collect + 中心学习器；每核 275 步/s × 1,536 核的上限在那，够 PPO 用。

## 13. 复盘：为什么收敛在手写调度器档位（2026-08-15，本分支最有价值的一节）

终态是 4/10、收入档 22–28k，与本仓库手写调度器（barnyard/enhanced，~857
天梯档）之下一档。1.2 亿步、十次大干预（λ 三档、课程重定向、联赛 PBT、
复合指令、教师克隆、护栏）之后仍然如此。七个原因，按权重排序，每条都有
本分支内的测量支撑：

**1. 动作空间内嵌了手写调度器的天花板（最重）。** 雇工——crew 是支配一切
的轴——跑的是手写固定优先级调度器，策略网络真正控制的执行量约三成。
RL 在"我们自己手写代码的天花板之下"优化。证据：barnyard 的 farmer 动作
被宏空间覆盖 98.6%（表达力不缺），缺的是它 11 雇工按阶段协同的调度 vs
我们的一条静态优先级表；市场侧它每回合 10 条组合拳 vs 我们等效 2–3 条。

**2. BC 锚定平庸教师 + PPO 是局部搜索。** 冷启动克隆 30k 档脚本教师;
PPO 把这个盆地打磨到极致，但跳向质变策略要穿越"中间态全更差"的谷地,
on-policy 梯度过不去。对照组：无 BC 的纯 PPO 五百九十万步没摸到 barnyard
断崖的边。被夹在"不用 BC 学不起来、用了 BC 出不了盆地"之间。

**3. 塑形奖励是代理目标。** 基准价计价、终局衰减、流动性溢价、λ 竞争项
每一项都必要、也每一项都把最优点从真实胜负挪开一点。一路修掉的四个退化解
（市值计价瘫痪、终局烧钱、全押开局、λ=1.0 同归于尽）全是塑形的影子;
修完后活下来的最优点仍是塑形函数的最优点。

**4. 前沿处真信号为零。** 对 60k 档胜率 0% = 胜负奖励在最需要梯度的地方
一次没开火。"第 10 天就该建立体量翻倍的经济"这类非局部反事实，1.2 亿步
没能从均匀惨败的轨迹里提取出来。结构性缺失，非调参可解。

**5. 环境物理学偏向离线计划（与仓库主线结论互证）。** 近乎全知、交互集中
在市场、随机性有限 → 最优玩法接近离线规划问题。天梯顶端是"录好的计划 +
市场外包装"（2599），所有在线反应式方案封顶 ~857（§7A 整节的实测）。
在线策略每回合付"反应税"（贪心一步意图、无前瞻）；手写调度器至少把前瞻
硬编码成了规则——我们最后也是靠把 LAST_PLANT_DAY/清仓纪律硬编码成掩码和
势函数才修掉退化行为的。**这条 RL 线是又一台在线调度器，撞的是同一面墙。**

**6. 联赛自博弈没能供给缺失的探索。** 种群（镜像+历史检查点+锚点）全活在
同一盆地：锚点两端无梯度（被碾压或碾压我们），PFSP 正确地把算力集中在
~50% 对手上——而那些全是自己的克隆。联赛把盆地挖深了，没翻出盆沿。

**7. 对照基线站在巨人肩上。** barnyard/enhanced 背后是整个赛季的领域沉淀
（§11：9 个落地改动、17 次否决、几十万局 A/B）。RL 侧是 30 小时。同档
结果说明管线健康，只是没有奇迹。

### 出路（按置信度排序，前置条件见 TODO.md）

1. **顺环境物理学：计划空间搜索（最高置信）**——用 43× 引擎直接进化/束搜
   720 步动作序列，跨种子跨对手评估，产出"剧本+外包装"= 仓库路线 C、
   天梯顶端的结构。本分支的吞吐基建恰好把它的算力成本打下来 40 倍。
2. **拆掉雇工调度器**，共享策略逐雇工控制——移除第 1 条的天花板，训练
   难度上一个台阶。
3. **推理期市场精确搜索**（kg_rules 价格模型逐单位精确评估 + value 网络,
   毫秒级）——给反应式策略装前瞻。
4. 干净数据上的真容量实验（TODO #6 前置条件）。

**一句话总结：这次收敛不是 RL 失败，而是它忠实找到了我们给它的问题的
最优解——只是"反应式在线调度"这个问题的最优解，本来就只值这么多分。**
