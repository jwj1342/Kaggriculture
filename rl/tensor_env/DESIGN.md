# tensorize 分支立项设计 — 棋盘与策略的 GPU 张量化

**状态：B0–B4 全部完成（2026-08-18）；合作者入口是同目录 `README.md`。** 本文档是这个分支的宪法：目标、阶段、每阶段的
验收门、GPU 申请理由、风险登记。实现必须按阶段推进，**过门才许进下一阶**。

背景与前史：`rl-baseline` 分支（见其 `rl/README.md` 终局判词与 §13 复盘）。
本分支继承了那条线的已验证地基（见 §2），服务两个下游：RL 线的重启
（更大网络、逐雇工控制）与仓库路线 C 的**计划空间搜索**——后者是天梯顶端
结构，批量 rollout 正是它的算力形态。

## 1. 目标与范围

把**环境（棋盘模拟）与策略（网络前向/反向）**全部搬上 GPU，使一次
`step` 是对形状 `(B, ...)` 张量的一组运算、B 个对局并行推进，环境与策略
之间零主机往返。

- **目标吞吐**：单张 L40S ≥ 200k 步/秒（当前 CPU 基线：32 核 9.2k 步/秒;
  用户预期区间 20–400×，本目标取 ~22× 为底线，B=4096 时的理论上限远高于此）。
- **范围内**：训练采集、自博弈、计划空间搜索的批量评估。
- **范围外（明确不做）**：竞赛部署端推理不需要 GPU（numpy 前向 <1ms,
  1s/回合约束下毫无压力）；`tools/eval.py` 评测纪律**永远**留在参考
  kaggle 引擎上——训练引擎的任何残余偏差必须表现为 train/eval 失配,
  而不是污染测量。参考引擎一行不改。

## 2. 继承的地基（已在本分支）

| 文件 | 角色 |
|---|---|
| `engine_np.py` | 参考引擎的逐字节移植（**已过 3×720 步全状态一致门**），本分支所有张量实现的**测试预言机** |
| `verify.py` | 逐字节验证挂具：同 (seed, 动作序列) 下与 kaggle 引擎逐步 diff 全状态 |
| `adapter.py` | engine_np 的 gym 风格适配（对手加载语义与真实 loader 一致） |
| `../actions.py` `../obs.py` `../fused.py` | 特征栈规格与参照实现（宏动作/掩码/编码/势函数），张量版特征化对着它们过逐位门（模式同 `test_fused.py`） |

验证链条：**kaggle 引擎 ⇐(verify.py)⇐ engine_np ⇐(新门)⇐ 张量引擎**。
链条上每一环都是逐字节/逐位判等，没有"近似正确"。

## 3. 核心设计决策（先定死，实现不许偷改）

### D1. 状态全整型，浮点只在参考引擎有浮点处

游戏状态几乎全是整数（库存、yield、天数、位置、价格 `int(round())`）。
张量状态用 int32/int64；唯一的浮点是 money（参考引擎为 float）与价格
计算的中间量。**这是跨设备逐字节一致可行的根基**——整型运算在
CPU/CUDA 上无舍入分歧；浮点段（价格公式、money 加减）按参考的运算次序
逐条移植，float64 中间量。

### D2. 每日 RNG 留在 CPU（混合步进）

`random.Random((seed*1_000_003) ^ day)` 的马特赛特旋转流、逐格行主序
杂草抽取、`rng.choice(sorted(SHOPS))`——在 GPU 上复刻 CPython RNG 字节流
不值得。**设计：每天 23 个回合纯 GPU 推进，日界处同步一次 CPU**（收尾
刷新 + 杂草 + 商店抽取，然后写回设备）。成本：1/24 的步做一次 D2H/H2D,
每次数据量 ~B×几 KB；换来的是逐字节门在 GPU 阶段仍然成立。

### D3. 市场逐单位 lockstep 的批量化是最难的一段，单独立门

per-unit 结算循环（两名玩家同价快照、逐单位提交、每单指令后刷新价格）
是天然串行的。设计：单位循环保持串行（上限 10 指令 × 有限单位数），但
**跨 B 维向量化**——同一"单位序号"的所有对局并行结算。最坏情形逐单位
循环 ~几百次迭代，每次是 (B,) 张量运算，可接受。此段单独设立 B1.5 子门
（随机市场指令风暴 + 双人同品类对冲的对抗种子集）。

### D4. 对手也必须张量化，否则吞吐被 Python 对手拖回原形

批量对局的对手不能是逐局 Python 函数。三层供给：
(a) **自博弈/联赛成员**：本来就是策略网络，天然批量；
(b) **starter / 脚本教师**：逻辑简单，张量移植（各设逐字节门：与
    Python 版在相同 obs 序列上动作一致）；
(c) **参考场地对手（barnyard/ghost/spar 等）**：不移植——它们只出现在
    CPU 参考引擎的评测里（§1 范围外），训练分布用 (a)+(b) 承担。

### D5. 特征化与掩码在设备上、从张量状态直接切片

`fused` 的单趟分析在张量状态下退化为几十条切片/scatter——特征成本趋近
于零。逐位门对着 CPU fused 实现（模式照抄 `test_fused.py`）。

## 4. 阶段与验收门

| 阶段 | 内容 | 验收门（硬性） |
|---|---|---|
| **B0** | 张量状态布局规格书（本文件附录 A，开工前补全字段表） | 设计评审：每个字段对得上 engine_np 的状态项，无遗漏（对照 `snapshot()` 结构逐项打勾） |
| **B1** ✅ 2026-08-16 | torch **CPU** 批量引擎（`engine_t.py`） | G1/G2 全绿（含子代理额外的对抗差分：仓满、pending_care、FERTILIZE 覆盖 + first_diff 阴性对照）。CPU 吞吐：B=1 9.2k / B=64 39.6k / **B=256 47.4k** lane-steps/s |
| **B1.5** ✅ 2026-08-16 | 市场 lockstep 批量化专项 | G3 风暴门全绿（同品类对冲、清仓风暴、原子序、买不起的尾单） |
| **B2** ✅（正确性）2026-08-16 | `device="cuda"`（L40S） | **三道门在 CUDA 上全绿**——一致性目标在设备上成立。吞吐首测 16.9–18.1k（B=256→4096 近平坦，每步耗时随 B 线性涨）：**宿主侧 O(B) 开销主导**（逐 lane 动作解析、日界 RNG 宿主循环、微内核发射风暴），GPU 算力远未触及——优化归 B3/B4，不是正确性问题 |
| **B3a** ✅ 2026-08-16 | 设备上特征化 + 双头掩码（`features_t.py`） | 逐位门全绿（720 步 × 3 lanes × 双视角，encode+双掩码处处一致；唯一宿主计算 = money 的 log1p 两槽，libm 不可跨设备复现，已文档化）。B=256 时 81.6µs/lane/step，已低于 CPU fused 参照（136µs）。**CUDA 上同门全绿**（2026-08-17，修复挂具的 device 字符串断言后） |
| **B3b** ✅ 2026-08-16 | 张量原生动作路径 `step_idx`（`engine_t_idx.py`） | 等价门全绿：`step_idx(f,m)` ≡ `step_raw(decode(...))` 逐字节（720 步全程、含风暴 lane）；两项回归保持全绿。CPU B=1024 真实负载 17.8k lane-steps/s（对 step_raw 的 11.9k = 1.8×；masks+采样仅 10µs/lane-step）。张量对手移植遗留到 B4 |
| **B4a** ✅ 2026-08-17 | 张量态 starter 对手（`opponents_t.py`，(B,) gather 直取决策，免 snapshot 重建） | 门全绿：与参考 starter 逐动作一致（720 步 × 4 lanes 全程） |
| **B4b** ✅ 2026-08-18 | 吞吐工程：设备上 MT19937 浮点重建（杂草/商店，逐字节）、(B,2) 融合市场 lockstep、LUT 宏解码、内核惯用法（aten 调用 19.3k→6.9k/步） | 四门全绿（CPU+CUDA，含 CUDA f32 除法 1-ulp 回归的修复）。**单卡 L40S B=4096：step_idx 228.6k lane-steps/s（≥200k 目标达成）**，含掩码+采样 142.5k；CPU B=4096 173.5k。torch.compile 试过不采用（记录在案） |
| **B4c** ✅ 2026-08-18 | 训练闭环同驻 GPU（`train_t.py`：`PolicyT` + 设备端势函数 `potential_t` + PPO） | (i) 势函数 4,320/4,320 与 CPU 参照**逐位相等**；(ii) starter 索引路径解码后逐动作一致；(iii) **学习曲线**（L40S，B=1024，60 iters，44M 步，18 分钟）：胜率 0→0.62（it18）→0.93（it24）→**1.00**（it30 起），收入 7→25k；端到端 ~40k lane-steps/s（采集占 95%——PPO 更新已不是瓶颈） |
| **B5**（可选） | 计划空间搜索原型（路线 C）：进化/束搜 720 步动作序列的批量评估 | 每小时可评估候选数 ≥ 10⁶（对照仓库路线 C 的算力账） |

## 4.5 基准实测（2026-08-16，bench.py，2×L40S 作业）

以 kaggle 参考引擎为 1×。noop = 纯引擎地板；replay = 录制的真实动作流:

| 引擎 | noop | replay |
|---|---|---|
| kaggle | 802 (1×) | 731 (1×) |
| engine_np 单局 | 31.8k (40×) | 24.5k (34×) |
| engine_t CPU B=1024 | **52.2k (65×)** | 11.5k (16×) |
| engine_t GPU 单卡 | 18.4k (23×) | 4.5k (6×) |
| engine_t 双卡 map-reduce | 36.1k（**~95% 线性效率**） | 8.7k |

诊断：真实负载下 `step_raw` 的逐 lane 字典解析是 O(B) 宿主开销（B=4096
每步解析 8,192 份 dict），淹没张量收益——**B3/B4 的首要任务 = 张量原生
动作接口**（策略在设备上出 (B,P) 索引、设备上解码），字典路径只留给
验证门。多 GPU 管理原型（每设备一进程分片 + 父进程归并）扩展性已验证,
待单卡基础速率修复后再横向扩。

## 5. GPU 申请理由（新负载形态说明）

仓库与集群规则写明"CPU-only、永不申请 GPU"——**那条规则针对的负载**是
单线程 Python + 框架 deepcopy（42% 墙钟），GPU 帮不上任何忙，申请即浪费。
本分支的负载是**另一种形态**：

- 环境 = 对 `(B, C, 10, 10)` 整型张量的批量运算，B≈2048–8192；
- 策略前向/反向与环境同驻设备，无主机往返；
- GPU 利用率来自环境+策略的连续张量流水，不存在"GPU 等 Python 喂数据"。

资源申请形态（按集群规范）：`--gpus-per-node=l40s:1`，`--cpus-per-task=16`
（≤16 核/卡的配额），短链任务；显存账：B=8192 × 状态 ~4KB/局 + 网络与
优化器 ~百 MB，一张 48GB L40S 富余一个数量级。**在 B2 门过掉、CPU 版
吞吐数据在手之前，不提任何 GPU 作业**——申请理由必须带着 B1 的实测数字。

> **更正（2026-08-23，实测；`docs/RUNS.md` 同日判词）。上面这段显存账错了约
> 三个数量级,`B≈2048–8192` 这个区间在 H100 80GB 上跑不起来。**
>
> 错因:它算的是**引擎状态**(~4 KB/局),漏了 **PPO 为每一个时间步保存的观测**。
> 每条 lane 是 719 步 × 4867 float32 × 4 B × 2 份(`observation` 与
> `("next","observation")`)= **28 MB,不是 4 KB**,差 ~7,000×。
> 于是 B=8192 的采集批本身就要 229 GB。
>
> `rl/train.py --mem-report` 在 B=1024 上的实测:
>
> | | 峰值 | 跨采集边界的常驻 |
> |---|---|---|
> | 原样 | **60.97 GiB** | 43.37 GiB |
> | `--rb-free` | **47.34 GiB** | 29.74 GiB |
>
> 采集批 27.68 GiB,其中 `observation` 与 `next.observation` **各 13.35 GiB**。
> **B 的实测天花板是 1024**:B=1536 峰值 68.17 GiB 后 OOM,2048/3072 直接死。
>
> 两条原判**成立**:(i)"GPU 不等 Python 喂数据"——`nvidia-smi` 447 个采样点
> 利用率中位 **98%**;(ii) B 确实是吞吐杠杆——B=1024→1536 是
> **10,593 → 15,166 lane-steps/s**(1.5× 的 lane 换 1.43× 吞吐,而迭代墙钟只从
> 69.5 s 到 72 s),**证实发射延迟主导**。所以想要更大的 B 必须先省显存,
> 而 `next.observation` 那 13.35 GiB **对损失没有贡献**
> (`trl_env.py` 里 `terminated = done`,`truncated` 从不设置,自举被乘 0),
> 但**不能直接删** —— TorchRL 里它就是下一个状态(`step_mdp` 会把它提升为
> `observation`)。可行路径是 float16 观测(`train_t.py --obs-half` 的先例;
> 特征都归一化在约 [-1,1],量程安全),**它改变更新看到的输入,要先做 A/B**。
>
> `--cpus-per-task=16` 也是错的形态:`sacct` 显示每个 link 只用 **0.99 核**,
> 线程扫描 1/4/8 完全平坦(10,504/10,549/10,564)。已改为 2 核
> (`slurm/rl_train.sh`)。而 CPU 不是 GPU 的替代:同一配置同一 B=1024 下
> CPU 2 线程只有 **2,124 lane-steps/s**,GPU 快 5.0×。

## 6. 风险登记（预先，不是事后）

1. **浮点跨设备分歧**：D1 把面缩到 money/价格；若 CUDA 上 float64 序仍有
   分歧，退路是价格段也走整型定点（价格本就 `int(round())` 落地）。
2. **RNG 字节流**：D2 绕开；若日界同步成为吞吐瓶颈（不太可能，1/24 频率）,
   再评估预生成随机表。
3. **引擎再平衡**：竞赛方改平衡（发生过一次）→ 三层链条全部要重验。
   纪律：升级 kaggle-environments 后先跑 `verify.py`，红了先修 engine_np。
4. **对手分布收窄**（D4c 的代价）：训练场没有 barnyard 级参考对手。缓解:
   评测频率提高（CPU 参考引擎便宜且并行）+ 教师脚本张量版尽早进池。
5. **lockstep 批内发散**：B 局在同一步的市场指令数不同 → 掩码化的
   无操作填充，注意不要让"最长对局"拖垮批（720 步定长，天然对齐,
   风险主要在市场单位循环内，见 B1.5）。

## 附录 A：张量状态布局（B0，已定稿 2026-08-16）

约定：`B`=批内对局数，`P`=2 玩家，`N`=10，`H`=32（雇工上限，fib 成本使
实际雇佣远低于此；越界断言报错而非静默截断），`I`=12 件套（9 产品+3 动物,
顺序 = kg_rules.PRODUCTS + ANIMALS），`C5`=5 作物，`S8`=8 商店（sorted 序）。
所有对局同步复位、同一 step 计数（720 定长，天然 lockstep）。

### 棋盘（每格）

| 字段 | shape/dtype | 对应 engine_np | 初始化 |
|---|---|---|---|
| `tile_kind` | (B,P,N,N) int8 | None=0 / LOCKED=1 / WEED=2 / COOP=3 / PASTURE=4 / PLANT=5 | NW 象限 0，其余 1 |
| `tile_animal` | (B,P,N,N) int8 | 无动物 −1；否则动物 idx（仅 kind∈{3,4} 时有效） | −1 |
| `tile_crop` | (B,P,N,N) int8 | plant["crop"] idx（仅 kind=5 有效） | 0 |
| `yield_units` | (B,P,N,N) int8 | plant/animal 共用（引擎里两者互斥同格） | 0 |
| `planted_day` | (B,P,N,N) int16 | plant["planted_day"] | 0 |
| `placed_day` | (B,P,N,N) int16 | animal["placed_day"]（与上分开存，刷新公式不同） | 0 |
| `watered_today` | (B,P,N,N) bool | plant["watered_today"] | False |
| `consec_unwatered` | (B,P,N,N) int8 | plant["consecutive_unwatered"] | 0 |
| `max_lifespan_step` | (B,P,N,N) int32 | plant["max_lifespan_step"]（−1 表 ongoing） | 0 |
| `fert_until_day` | (B,P,N,N) int16 | plant["fertilized_until_day"]（−1 语义保留） | 0 |
| `fed_today` / `cared_today` / `fert_avail` | 各 (B,P,N,N) bool | animal 三态 | False |
| `consec_unfed` | (B,P,N,N) int8 | animal["consecutive_unfed"] | 0 |
| `pending_care` | (B,P,N,N) int8 | animal["pending_care_bonus"] | 0 |

### 农场标量 / 单位

| 字段 | shape/dtype | 对应 | 初始化 |
|---|---|---|---|
| `money` | (B,P) float64 | farm["money"]（参考为 float，运算次序照抄） | 3000.0 |
| `farmer_xy` | (B,P,2) int8 | farm["farmer"] | 出生点 (4,4) |
| `hands_xy` | (B,P,H,2) int8 | farm["hands"]（前 `hands_n` 个有效） | 0 |
| `hands_n` | (B,P) int8 | len(hands) | 0 |
| `hires_today` | (B,P) int16 | farm["hires_today"] | 0 |
| `quad_unlocked` | (B,P,3) bool | NE/SW/SE ∈ unlocked_quadrants | False |
| `unit_inv` | (B,P,1+H,I) int16 | private["inventories"]（0 号=农夫） | 0 |
| `shed` | (B,P,I) int16 | private["shed"] | 0 |
| `seeds` | (B,P,C5) int16 | private["seeds"] | 0 |

### 市场 / 城镇 / 时钟

| 字段 | shape/dtype | 对应 | 初始化 |
|---|---|---|---|
| `mkt_inv` | (B,9) int32 | market["inventory"]（双方共享） | 10000 |
| `mkt_price` | (B,9) int32 | market["prices"]（`int(round())` 后整型落地） | base |
| `shops_seq` | (B,S8) int8 | town["unlocked_shops"] 抽取序（−1 填充；顺序参与 snapshot 判等） | −1 |
| `step` | python int | 全批同步计数 | 0 |
| `done` / `reward` | (B,) bool / (B,P) float64 | 终局态 | False / 0 |
| `ep_seed` | (B,) host int64 | 每日 RNG 的种子（D2：日界 CPU 段用） | 构造参数 |

### snapshot 契约

`snapshot(lane)` 从张量重建与 `engine_np.Episode.snapshot()` **完全同构**的
dict（含 tiles 的 None/"LOCKED"/dict 三态、dict 键序、shops 列表序）——
所有验收门都在这个重建层上判等，张量内部表示自由，重建必须无损。

## 附录 B：B4c 训练闭环设计（开工前定稿）

目标：采集与 PPO 更新同驻一张卡，零宿主往返，对张量 starter 出现可复现的
学习曲线（定性对照 CPU 管线：rl-baseline 上 BC 起步对 starter 从 ~40%
爬到 >90%；这里从零起步，验收只要求单调爬升并越过 50%）。

### 组件（全部新文件，`rl/tensor_env/train_t.py` 为入口）

| 组件 | 说明 |
|---|---|
| `PolicyT` | 与 rl-baseline `policy.py` 同构（actor 4867→512→256→双头，critic 独立 4867→256→256→1）;可选 `--hidden` |
| 采集器 | 单进程、单设备：`ep=EpisodeT(B)`, 每步 `encode_t`+`masks_t`（双方视角）→ actor 前向 → 掩码采样 (B,2) 索引 → `step_idx`;对手席位由 `opponents_t.starter_actions` 或镜像策略提供;轨迹存设备端 (T,B,…) 缓冲 |
| 奖励 | 势函数塑形（与 rl-baseline 同：基准价 net_worth，终局衰减、流动性溢价）**在设备上**从张量状态直算 + 终局 ±win_bonus；不再走 obs dict |
| PPO | 逐局 GAE（终局 bootstrap=0，定长 720）、优势标准化、裁剪目标、独立 critic、熵项、梯度裁剪——同 rl-baseline 系数 |
| 门 `test_b4c.py` | (i) 设备端势函数 vs CPU `obs.net_worth` 逐位一致（gate 复用 test_b3 模式）；(ii) 一次 ≤10 分钟的小训练（B=256，CPU 或 GPU）胜率单调爬升过 50%；(iii) 端到端 lane-steps/s 报告 |

### 纪律
- 评测仍在参考引擎（`tools/eval.py`）：导出 numpy agent（沿用 rl-baseline
  的 export_agent 契约）后跑，训练引擎偏差只能表现为 train/eval 失配。
- 不动 engine_t / features_t 的语义；B4c 只**消费**它们。
