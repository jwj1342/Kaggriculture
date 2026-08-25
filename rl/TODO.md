# RL TODO - 当前执行路线（2026-08-25）

本文件只维护当前执行队列，不再兼作实验日记。已完成、已证伪和被取代的工作归档在
[docs/RUNS.md](../docs/RUNS.md)，架构历史保留在 [rl/README.md](README.md)。没有新证据时，
不要把文末归档表里的旧项目重新排入队列。

## 当前诊断

剩余瓶颈是**稀有长期战略决策的信用分配**，不是吞吐、网络宽度、动作词表、对手强度，
也不是同一 PPO 配方训练得还不够久。

- 训练参数为 `gamma=0.999`、`lambda=0.95`。相隔 `k` 回合的 GAE 残差权重是
  `(gamma * lambda)^k`：36 回合为 0.152，142 回合为 0.000596，200 回合为
  0.0000287。单独的 `gamma^200` 仍为 0.819；问题来自 eligibility trace 与 critic
  误差的组合，不能只归因于折扣。
- BUY_SEED 到对应 PLANT 的实测延迟是中位 6 回合、均值 36、p90 142。因此长程信用是真
  问题，但不是唯一问题：`P(BUY_SEED | legal)` 中位只有 0.02%，多数有用替代动作根本
  没有被采样。
- 把 lambda 提到 0.99 的 `longcredit` 在正确同场对照上只增加 689，而且建设行为没动；
  打开市场通道的 `bzt` / `bothheads` 也没有超过免训练的 decode-only `bazaar`。
- 现有 farmer 宏动作是无状态的单回合意图。它们缩短了走路序列，但不是持久 Option，
  也没有把整季转换成战略层面的 Semi-MDP。

## 执行纪律

1. 不再给未改变结构的 flat PPO 排新的标量奖励、词表、对手混合或单纯延长训练实验。
2. 以下每阶段都有诊断门。门失败就停止后续阶段，不能自动退化成调小学习率或多跑几轮。
3. 反事实比较必须使用配对 lane：相同 seed、席位、对手、RNG、checkpoint 和后续策略，
   只改变被检验的干预。
4. 同时最多保留一个开发 worktree 和一个冻结实验 worktree；合并或形成判词后移除，不能
   重建“一条假说一个 gen 目录”的膨胀模式。清理前必须给 run 产物建立 manifest。
5. 本地 money 只作诊断，不再外推天梯分。最终门看原始胜负、配对 margin、行为读数和
   held-out 对手。
6. 正式训练统一使用 `tools/submit_rl.py`（细则见 `docs/INFRA.md`）：已提交的干净代码、
   预登记假设/阈值、短 pilot、`afterok` 链；默认 CPU，GPU 必须给出实测理由。

## Phase 0 - 冻结可复现基线与测量工具

本阶段不训练新模型。

进度（2026-08-25）：批量基线/critic/行为审计与配对反事实工具已在 `f6ff76a` 落地，
受 manifest 约束的 Slurm 提交入口在 `64a99ee` 落地。完整统一基线作业 `20464673`
（32 lanes × 4 对手 × 双座位）按预登记规则选出 `anvil/latest.pt`；Phase 1 随后完成，
结果见下节与 `docs/RUNS.md` 顶部。

- [x] 从主树仍存在的产物中选择一个低层 checkpoint。候选包括 `chisel`、
  `longcredit`、`cropper` 和 `anvil`；必须在新的同场评估中选择，不能混用历史上不同
  panel 的数字。记录 checkpoint SHA-256、源码 commit、参数和对手场。
- [x] 在 CPU 重跑 `bank_t.py` fork/restore 门，并在拿到 GPU 时补 CUDA 门。CPU 门于
  2026-08-24 通过；CUDA 门由作业 `20467057` 于 2026-08-25 通过：step 200 fork 后跨
  两个游戏日重放 64 回合，状态逐字节一致。
- [x] 增加分时段 critic 诊断：分别报告 day 0-4、5-11、12-19、20-29 的 explained
  variance 或 return error。`anvil` 四段平均 explained variance 为 `0.233 / 0.491 /
  0.739 / -0.292`，直接定位到最后十天失真；其他候选的最后十天均值也全部为负。
- [x] 冻结一组 seed/opponent 审计场，至少包含被动对手、反应式中档对手、
  `closer_cleo` 和一个 held-out wall。
- [x] 记录基线 BUY_LAND/BUY_SEED/BUY_ANIMAL/HIRE 概率，以及 land、seeds、herd、crop、
  crew、money、margin 分布。

通过条件：checkpoint 能干净导出，配对模拟器确定性成立，并且加入任何干预前能复现基线。

## Phase 1 - 反事实 rollout 审计

这是第一个实现任务，优先于 COMA 和任何 HRL 训练。

### 干预形式

- 只在战略资格事件触发：每天开始、某项采购首次可负担、容量出现空位，或当前 Option
  终止。
- 初始最小集合比较 `FOLLOW_POLICY` 与 `EXPAND_LAND`、
  `ESTABLISH_CROP(crop)`、`SCALE_HERD`、`PRESERVE_CASH` 等候选。
- 干预必须持续到成功、变得不可行或达到预注册 timeout。只强制一个回合 BUY_LAND 不是
  有效反事实，因为基线可能下一回合照样购买。
- 两个分支均冻结低层策略。对手可以响应分支状态；仅通过共同随机数固定环境随机性。

### 测量

- [x] 基于 `EpisodeT` 与 `bank_t.fork/restore` 实现批量审计工具（`rl/macro_audit.py`）。
- [x] 测量 24、72、168 回合后及终局的配对差值。中间的 `future_worth` 只作诊断；
  终局 money、margin、wins 是主指标，因为 potential 本身已有代理失真记录。
- [x] 按 trigger、day、Option、opponent、seat 分层报告。不能把一次稀有且有价值的开局
  决策与数百个无关回合平均在一起。
- [x] 保存完整干预定义和原始配对结果；只有“build”标签而没有承诺窗口不可复现。

### 2026-08-25 判词：一个条件式 Option 通过，Phase 2 解锁

首轮全局 Option 均未过门：增加 2 羊为 `+1,149 [-100,+2,557]` 且 held-out `w49`
反向，增加 4 羊退化到 `-12,059`；全程接管饲养的 `OPERATE_HERD:SHEEP` 更退化到
`-9,948`。但后续发现收益有明确状态异质性：只在第一次可购买时现金位于
`$1,500–1,900` 才执行“增加 1 羊”，在全新 seed `270825+` 的 128 个张量配对上终局
margin `+2,334`，95% CI `[+1,125,+3,542]`，`closer_cleo` 与 held-out `w49` 四格
均同号，64/64 次选中的 Option 完成。

真实导出随后在官方 Python 引擎、全新 seed `280825+`、两个强墙、双座位的 128 个配对
决策上复现：margin `+2,474`，按 32 个 seed 聚类的 95% CI
`[+1,280,+3,737]`；`closer_cleo +865`、`w49 +4,084`，均同号，所有 256 局正常结束。
因此该 Option **通过 Phase 1 并解锁 Phase 2**。限制同样明确：两边仍是 0/128 胜，
且机械地允许第二次相同 Option 在新 seed pilot 中为 `-881 [-2,570,+648]`，不继续扩跑。

进入 Phase 2 的门：至少一个持久建设 Option 在预注册场上的终局配对收益区间排除 0，
在 held-out 对手上保持同号，并且移动的是目标行为而非奖励代理。若没有 Option 通过，
应先修改执行器或战略动作集合，不能直接训练高层 controller。

## Phase 2 - option-lite 分层控制器

只训练高层 controller，冻结已验证的低层策略/执行器，避免一开始就同时学习两层造成
非平稳性。

**状态：已解锁；先做 CPU 离线宏观优势模型，当前仍不申请 GPU 训练。**

2026-08-25 的首个状态条件模型已按门停止。开发集上冻结的
`demand_milk <= 1` 单羊规则在全新 `320825+` seed、四个强墙、双座位的 256 个配对上
总体 margin 为 `+2,067 [+977,+3,145]`，但 `closer_cleo` 两个席位分别为 `+593` 与
`-1,127`，且胜负仍为 0；不满足逐墙逐席位同号的预注册门。事后叠加现金阈值也未修复
该格，因此不再调这条规则。下一项改为能同时承诺容量、生产资产和执行窗口的完整建设
阶段 Option；仍先做反事实审计，不直接训练 controller。

- [x] 导出 `FOLLOW_POLICY` / 条件式 `BUY_ONE_SHEEP`，并在真实 Python 引擎复现
  张量反事实的正向效果；默认关闭时保持原策略行为。
- [x] 扩充反事实数据的宏观状态，加入实时价格、市场库存和商店消费强度；按 seed 分组、
  按对手留出训练首个宏观优势模型。它没有超过简单现金规则，冻结的需求量 stump 又在
  全新 seed 的 `closer_cleo` 席位门失败，因此不部署。
- [ ] 实现并审计完整建设阶段 Option；只有它通过逐墙逐席位门后，才将其暴露给高层
  controller。单羊 `$1,900` 规则保留为已验证的组件和对照，不继续调阈值。

- [ ] 高层动作使用显式、带掩码的 categorical 分布并保存 log-prob。不要使用连续意愿值
  加硬 threshold；硬阈值会把真正的因果决策藏在 PPO 梯度之外。
- [ ] 在环境中持久保存 `{option_id, start_state, elapsed, termination_reason}`。只在
  Option 终止或战略 trigger 出现时重新决策，不再每回合重选。
- [ ] 构造 Semi-MDP transition。Option 持续 `tau` 回合时，累计区间内回报，并用
  `gamma^tau * V_macro(s')` bootstrap。
- [ ] 初版只使用 Phase 1 通过的 Option，并由确定性执行器或冻结低层执行；
  `FOLLOW_POLICY` 必须作为对照动作保留。
- [ ] 增加可用性、持久性、timeout、终止与导出门。全程选择 `FOLLOW_POLICY` 时必须与
  冻结基线行为一致。
- [ ] 记录每季高层决策数、Option 完成率、持续时间、因果回报和逐 Option 熵；不能再只看
  聚合熵。

进入 Phase 3 的门：相对冻结低层基线，配对 margin 的置信区间排除 0，held-out 不崩，
并且对 `closer_cleo` 96 局中至少出现 1 胜。只有本地中位数小涨、行为机制不动，不通过。

## Phase 3 - 离线宏观搜索与蒸馏

只有 Phase 1 产出有效 Option 后才搜索。第一用途是离线生成教师数据，不是在提交 agent
里实时跑 MCTS。

**状态：等待 Phase 2 controller 的胜负门；仓库目前没有现成 beam/CEM/MCTS 骨架。**

- [ ] 在同一 Option 接口上比较 beam search、CEM/evolution 和 MCTS，以单位模拟步的
  validation return 选型，而不是预先指定算法名称。
- [ ] 搜索必须跨多个 seed、席位和对手；只优化一个确定赛季会重现旧 open-loop tape
  的泛化失败。
- [ ] 算力允许时精确 rollout 到 Option 终止或整局结束。Phase 0 的分时段校准通过前，
  不能拿当前 turn-level critic 当 MCTS 叶子；可以改用 Phase 1 反事实目标训练 macro
  critic。
- [ ] 保存 `(macro_state, legal_options, selected_option, return-to-go)`，再用事件平衡
  采样把搜索策略蒸馏进 Phase 2 controller。
- [ ] BUY_LAND 等稀有门控动作必须单独分层；普通逐步 BC 的频率权重已经在 `tutor2` 中
  把它们压掉过一次。

进入 Phase 4 的门：搜索教师在未见 seed 和 held-out 对手上击败 Phase 2 controller，
蒸馏后的 controller 保留实质性收益。否则保留离线 planner，不增加联合训练复杂度。

## Phase 4 - 联合分层训练

这一阶段刻意放在最后。

- [ ] 让低层策略以所选 Option 为条件，并暴露终止/失败信号。
- [ ] 高低层使用独立 critic 与 replay/advantage 流；高层消费 Semi-MDP transition，低层
  消费逐回合 transition。
- [ ] 从 Phase 2 的冻结组件开始，交替更新或显著降低高层更新频率。第一个实验禁止两层
  同时从零初始化训练。
- [ ] 保留 `FOLLOW_POLICY` 与冻结执行器作为消融对照，确保收益来自联合适应，而不是
  宏规则悄悄改变。

最终研究门：纯学习控制必须对 `closer_cleo` 产生可重复的非零胜率，相对冻结低层的
边际贡献为正，并且在 held-out 场上不反向。只有过门后，提交天梯才有信息价值。

## 降级候选

- **COMA 式因子化 baseline**：仍可能改善同一状态下 farmer 与 market 的归因，但它依赖
  对一个几乎不被采样的动作学出可靠 Q。先做模拟器反事实审计，再考虑 COMA。
- **Decision Transformer**：保留为离线序列备选，但现有 open-loop 数据有状态分布错位和
  稀有事件失衡。只有拿到 Phase 1 的事件平衡数据或搜索轨迹后再议。
- **推理期市场优化器**：策略足够强之后可作为部署 wrapper；单步卖出优化不是缺失的
  整季 planner。
- **继续扩模型容量**：保留 critic 分时段诊断，但不再排 width-only 实验。容量曾经是
  约束，后续延长已经不能移动战略平台。

## 旧 TODO 收口表

| 旧事项 | 截至 2026-08-24 的状态 |
|---|---|
| 张量化脚本对手 | `barnyard_t.py` 与 tape 对手均已落地；继续移植不是当前路线的前置条件。 |
| 推理期市场优化器 | 降级为后续部署 wrapper，不是当前学习实验。 |
| 离线 N x N Bradley-Terry 重排 | 工具已存在；没有新候选群时不是战略瓶颈。 |
| 榜单轨迹 BC | open-loop BC/kickstart 已测；`tutor2` 仅 +133 且压低稀有 BUY_LAND。事件平衡蒸馏保留到 Phase 3。 |
| 容量实验/容量路线图 | `draught` 证明容量曾经绑定，长续训随后平台；关闭单独扩宽路线。 |
| 反事实信用分配 | 升为 Phase 1；顺序由 COMA 优先改成模拟器 rollout 优先。 |
| Decision Transformer | 降级为依赖更好数据的备选。 |
| SELL_HALF | 已实现；状态级保真度只从 57.0% 到 57.7%，关闭单独路线。 |
| tape/k06 集成与定价观察 | 已集成并完成后续实验；tape 课程最终平台在 7/12。 |
| 死动作掩码与继续扩词表 | 必要机械修复已吸收，多轮词表/解码实验已平台，不再作为独立轴。 |
| 土地信用 | `furrow` 买了地却留下更多空地；直接抬资产信用的处方被否。 |
| 小麦饲料 cap | `granary` 改善训练墙上的产量，但没有广泛迁移；不再单独排队。 |

## worktree 清理后的工作区

2026-08-24 按用户决定移除了全部 31 个辅助 worktree，对应 Git branch 仍保留。辅助树内
被忽略的 checkpoint 与导出产物已经丢弃。主树仍有 `chisel`、`longcredit`、`cropper`、
`anvil` 等可用 checkpoint 和 fork/restore 实现。`RUNS.md` 中类似
`Kaggriculture-gen41/rl/runs/bazaar` 的历史路径只说明当时在哪里运行，不代表产物当前仍
存在。
