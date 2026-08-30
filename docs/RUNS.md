# Run log

Provenance for every experiment that produced a number cited anywhere in this
repo. Append a row when you run something; the point is that a claim can always
be traced back to the episodes behind it.

## 当前 RL 总览（截至 2026-08-29）

这一节是下面一万多行逐次记录的索引，不替代原始证据。结论只比较同一对手场、同一
评估路径上的数字；本地数字不再换算成天梯分。**本文件正序阅读，最新判词在文件末尾。**

**2026-08-29 收口（本文件末尾 24 条判词，`08c676b … 58376fd`）。这一天没有排出任何一条
有效训练臂，产出全部来自纯读盘；缺口从一个不透明的数字变成一条设计约束。按重要性倒序：**

- **🔑 唯一的可操作输出：农场侧 × 市场侧的交互项是 +68,972，而单独换任一侧都是负的**
  （农场 −4,381、市场 −20,385、联合 +44,206；两道逐位机械门通过）。
  **所以单侧的标量/旗标/奖励项/教师项在结构上不可能跨过它。**
  这追溯解释了 `8db606f`（判 B 可预测）、08-25 的 scope 消融、第 2 阶段的 0/23、
  `expand_crop` 的 2–22/256 —— **本项目全部 ±1% 结果的图样。**（`28da6ef`）
- **缺口的 88% 是同一份资产上的执行质量**：把脚本缩到我们的足迹
  （19.7 对 19.8 株、9.3 对 9.0 帮手、1.00 对 1.00 象限），它赚 79,588 而我们赚 34,738，
  **对手收入只差 644**。四条结构性框架同时退场：物种 −412、规模 +5,054、
  土地不绑、帮手此足迹上 ≈0、市场压制 644。**分解闭合到 2.7%。**（`9176aae`）
- **第一次同仪器实测缺口**（把我们的网放进张量环境，不必给路线做官方引擎导出）：
  路线值 +50,206，劈成我们少赚 29,239 + 对手多赚 20,966；
  **margin 对钱的杠杆 ×1.717**，三个独立读数一致 ×1.7–2.1。（`3507af9`、`a65c20d`）
- **cleo 无人对抗时赚 133,695**（此前从未测过）。据此我们的网是**正资产 +60,292、
  已达路线 54.6%**；`starter` 才是负资产（比不动差 14,016）。
  **"负资产"此后必须说明设定：从零可用、接手赢家局面即破坏，两者都真。**（`1e3f278`）
- **量级表量纲逐行核对**：五行里四行是「钱」、一行是「配对 margin」，而分母是 margin。
  最大杠杆 7.9% → **13.5%**；"需要几倍于历史最佳"12.7 → **7.4**。排序不变。（`ea3879e`）
- **市场头逐作物拆开**：`P(BUY_SEED_WHEAT|legal)` 在 87–100% 合法率下中位与均值都是
  **0.00%**，两个血统同图样；而 `BUY_SEED` 家族读作 0.14%/8.00% —— **家族聚合掩盖了
  活头内部的死动作**，是 08-23「求和熵掩盖死头」下移一层。（`6e2b2c2`）
- **"照料吞吐"框架整体退休**：渴死 0.2/天对赢家 0.3/天（我们更少）、`MOVE` 手位占比
  44.0% 对 48.6%（赢家更多）、闲置+可雇 4.9 ≥ 赢家多干的 3.1。**产能从不稀缺。**（`3dac7f5`）
- **本日已关闭/否掉**：势函数 Δφ 符号（预登记 B 分支，`e9407c8`）、`--fixed-market-profile`
  （判 B 且**产物无法部署**，`8db606f`）、帮手动作空间上限、化肥收入线、
  逐帮手观测盲视（`BASE_G` 已携带采购所需的一切，`0451fae`）、"多雇人"
  （曲线单峰、峰在 11.2，`267017a`）、小麦跑步机（消融只值 −412，`d02e4cb`）。
- **纠错账**：一次已发布后撤回（`33cc1c9`，"两把锁"是 10→39 词表稀释）、
  一次发布后立即自纠框架（`a65c20d`）、三次发布前抓住仪器错误
  （`env.steps[t].action` 属于状态 `t−1`；市场数量是**下单量**不是成交量；
  一道不可执行的有效性门）、一次算术门失败于是不排臂（`0451fae`）。
- **仪器纪律新增**：动作计数读数默认按 **A 类（棋盘直读）/ B 类（下单量）** 标注；
  每个胜负作业带一个已知阳性；不许留下解释不了的桶（本日三次靠它逼出错误）。

**2026-08-28 收口（`9080478 … 8ec1c96`）。这一天把 G1 战术计划的
第 2–5 阶段第一次全部执行完，答案一致为阴，并把缺口从一个数字变成一个带刻度尺的窗口：**

- **官方引擎首次正式量四堵墙**：`anvil-fix` 是 **0 胜 / 1,536 配对局**，
  margin **−65,044 ~ −71,024**。这是当前 RL 线的权威数字。
- **四类干预家族关闭且各有复现**：解码层（23 个候选 0 过门，最好 +808）、
  墙入训练池（29 个 cleo 迭代 +532、始终 0 胜）、教师 CE（**与教师质量无关地有害**，
  一个好我们 31k 的教师同样一个迭代内打塌）、市场熵下限（去混淆后两个阶段都更差）。
- **找到并定位一条基础设施缺陷**：`granger.yaml` 的 `kickstart: barnyard` 是
  从旧检查点热启动塌陷的**必要条件**（2×2，`dd561a4`）；关掉后热启动第一次单调改善。
  **该配置项截至 08-29 仍未移除**，移除需自带 A/B。
- **新靶子**：把 k01（天梯 2302）的开局交给我们的网，量出执行器毁掉约 46,000；
  逐天扫九档把破坏定位到 **day 18–24 这六天（占 52.5%）**，机制是**照料吞吐塌陷**，
  **上界已知可达**（k01 从同一局面走完是 +14,293），并自带胜负刻度尺
  （交到 day 24 = 28/64、day 26 = 48/64）。
- **三次仪器错误，其中一条已发布后撤回**（`57a5c0b`）：`macro_audit` 的 `win` 字段是
  `None`，`or 0` 把空值数成败局。正确指标是 `margin > 0`。由此立下的规则是
  **每个胜负作业都要带一个已知阳性**——正是它逼出了这个 bug。
- 唯一未解释的根量仍是 **`productive / MOVE` 0.38 对 cleo 的 0.84**，
  两个最直觉的解释（空间聚集、作物数少）都已被否。08-27 的首个 option-lite 高层 pilot 已
完成：Semi-MDP 与训练链路通过，但三动作 selector 没有超过固定路线。随后四候选正式
筛选确认选择性施肥稳定正向，但所有候选仍为 0 个强墙胜局；当前已经转入短时域低层农场
执行技能。08-25
完成了统一基线/critic/行为审计；一个条件式单羊 Option 已跨张量反事实与官方 Python
引擎两道独立验证门，Phase 2 已解锁。08-25 又补齐帮手 BUILD/PLACE、lane 级原始动作覆盖
和整段 Option 审计，并验证“照着高分资产配额建设”仍不足以跨过强墙。当前没有天梯提交，
也没有启动 GPU 作业。最后有完整 PPO 训练结论的仍是 08-23 收口的 `bzt` /
`bothheads` 两条链（详见文末）。

部署恢复线与纯学习研究线分开记。当前自包含 `agents/champ/k01.py` 是第三方公开 meta
轨迹及其市场 wrapper，不是我们的 RL；它已在当前引擎上重新通过 768 局四强墙验证，
并与历史 2302.2 归档代码等价。候选包已生成但尚未提交，故不能把历史分数写成当前活跃
天梯分。纯学习线只在 256 个新状态中的 1 个跨过 `closer_cleo`，远未达到稳定胜出或
1287 的标准。

### 2026-08-27 · 路线候选正式筛选：施肥正向，但动作集合仍过不了胜负门

作业 `20642095` 使用提交 `46ba6a3`、冻结 checkpoint `anvil/latest.pt`，在
`closer_cleo / ledger_lena / budget_bea / w49`、双座位、每格 32 个配对 seed 上比较
`k01_route_s34` 与三种新路线。8 CPU 在 16 分 17 秒内完成；每个候选均跑完 256/256 个
反事实分支，峰值 RSS 约 1.06 GiB。

以相同 seed、席位和对手直接减去 `k01_route_s34`，并按 32 个 seed 聚类：

| 候选 | 配对 margin 差（95% CI） | 分格结论 | 强墙胜局 |
|---|---:|---|---:|
| `k01_route_s34_fert` | **+3,865 [+2,683,+4,920]** | 八个墙/席位格均正 | 0 |
| `k01_route_s34_bulk6` | **-3,152 [-5,023,-1,125]** | 八格均负 | 0 |
| `k01_route_s34_logistics` | +531 [-1,292,+2,305] | cleo/lena/bea 近零或负；仅 w49 两席约 +3.5k/+3.7k | 0 |

completed-only oracle 相对冻结 anvil 可改善约 `+37,460`，但仍没有胜局。预注册门要求候选
区间排除 0、held-out 两席非负，且至少产生一个 `closer_cleo` 胜局；施肥只满足前两项，
因此整个动作集合判负，不启动同一高层 selector 的扩大训练。批量买粮永久停止；物流只
保留作 `w49` 条件特征；施肥保留为下一代执行 Option 的已验证组件。

同日独立开发 seed 上，把麦季末从 day 24 延长到 day 27：单独晚麦约 `+666
[-12,+1,356]`；与施肥组合约 `+4,446 [+1,072,+8,515]`。这只是开发信号，尚未经历
四墙正式门。阶段式高层现已支持在 day 12 后开放施肥、day 25 后开放施肥加晚麦；短 smoke
证明 action mask 和训练链可用，但因为正式集合仍 0 胜，没有把 smoke 当作新训练结论。

阶段账本给出了下一条路线：完整教师相对 `route_s34` 的终局 margin 约高 40k，主要缺口
在 day 1--12 形成。相同 day-1 现金下，教师约 19 株作物而路线约 16 株；到 day 12 约为
56 株/14 畜与 40 株/12 畜。路线整季多约 500 次移动和 160 次零碎 PICKUP，却少约 150 次
HARVEST 与 49 次实际种植。所以下一实验不再调高层 PPO，而是把开局执行拆为短时域低层
学习问题，先提高单位路线、播种和收获吞吐，再作为持久 Option 接回 Semi-MDP。

### 2026-08-27 · option-lite pilot：链路成立，三动作集合触顶

作业 `20641453` 使用提交 `03ab781`、`anvil/latest.pt` 冻结低层、32 lanes，训练墙为
cleo/lena/bea，评估墙为 cleo 与 held-out w49。高层只在六个资产/日历里程碑及残局
决策，动作是 `FOLLOW_POLICY / k01_route / k01_route_s34`；Option transition 使用
`gamma^tau` bootstrap。预更新的 32 局配对探针逐美元等于固定 `route_s34`，说明 selector
与固定路线对照没有实现漂移。

pilot 共完成 5 个 PPO iteration、160 个训练赛季。训练没有 NaN，单轮约 34 秒；但第 4
轮确定性评估仍在所有阶段选择 `route_s34`，32 局配对 margin 差仍严格为 **0**，绝对
margin `-31,704`、胜局 0。随机训练轨迹每季平均决策数为 `6.56..6.72`，原因是若干
route 在 240 回合 timeout 后直接越过一个阶段；固定确定性评估则保持每季恰好 7 次决策。
这违反了预登记的“每个完整赛季恰好七次决策”字面门，同时更关键地没有产生任何性能
收益，因此不续跑这个 checkpoint。

判词是**动作集合上限，不是 HRL 训练链失败**：`route` 与 `route_s34` 在正式验证中只差
约 1k，`FOLLOW_POLICY` 又通常差 27k；selector 最多只能复现固定 `route_s34`，没有可供
学习的强反事实分支。下一步先用同 seed 阶段账本定位路线与完整教师之间约 25k--40k 的
现金流/联合时序差，再生成新的复合低层 Option；只有新集合的 completed-only oracle
出现强墙胜局，才重训高层。最终目标仍是 learned RL/HRL 策略稳定超过 1287，第三方
`k01` 回放只作教师与诊断上界。

### 2026-08-26 · 恢复 RL：累计建设承诺与选择性持久路线

用户澄清目标是 **RL/HRL 路线本身稳定超过 1287**，不是提交第三方轨迹 `k01` 恢复
榜分。此前因把两者混同而等待 Kaggle 授权属于错误停滞；本轮恢复 Phase 2 执行。

逐日同 seed 诊断发现 `k01_state` 把甜瓜的 20 株累计建设目标误作当前存量目标：一次性
甜瓜收获消失后被反复补种，导致第 12 天草莓仅约 7 株，而专家约 29 株。新
`k01_commit` 持久记录 Option 生命周期内已完成种植；新 `k01_route` 还让
`BUILD/PLANT/PLACE` 的目标格、操作和参数跨回合保持，同时仍允许浇水、喂养、照料和
收获就地抢占。

三批不重叠探索 seed 的小样本结果均对 `closer_cleo`、双席位：累计承诺相对旧执行器
约 `+4.9k`；选择性路线相对累计承诺约 `+6.0k`，自身收入约再增 `+5.2k`，最大作物
增约 5.4 株。全任务路线锁定、开局强制保畜、第 10 头牛、8/16/24 销售上限和按土地
阶段切换作物配额均退化，已停止。草莓目标从 30 调至 34 在两批探索中仅增加约
`+0.5k..+1.45k`，38/42 已受容量约束而无额外行为。最终候选 `k01_route_s34` 在
`2880825+` 的 16 局探索中对 cleo 出现 1 胜；这只是开发信号，必须经全新 seed、四墙
正式验证后才能作为高层动作。

正式作业 `20563910`（提交 `fc11ca9`，seed `3080825+`，cleo/lena/bea/w49、双座位
各 32 pairs）在 11 分 12 秒内完成，8 CPU、峰值 RSS 约 1.1 GiB。每个候选均完成
256/256 个整季 Option：

| Option | 相对 anvil margin（95% CI） | 自身 money 差（95% CI） | held-out w49 两席位 | cleo 胜局 |
|---|---:|---:|---:|---:|
| `k01_route` | **+26,856** `[+22,323,+31,187]` | +21,400 `[+15,297,+27,444]` | +17,307 / +17,705 | 1/64 |
| `k01_route_s34` | **+27,446** `[+22,999,+31,473]` | +22,405 `[+15,963,+28,940]` | +18,123 / +18,255 | 1/64 |

completed-only oracle 在八个 opponent/seat 格全部为正，总体 margin 提升
`+29,871 [+26,204,+33,505]`，选择 `FOLLOW_POLICY / route / route_s34` 的次数为
`20 / 98 / 138`，并保留同一个 cleo 胜局。因此预注册的最低动作集合门通过，可以开始
训练高层 categorical controller。限制同样重要：两个候选的绝对强墙 margin 仍约
`-29k..-39k`，总胜率只有 `1/256`；这个结果解锁 HRL 基础设施，**不代表接近 1287**。

| 阶段 | 代表 run | 真正取得的进展 | 停下来的位置 |
|---|---|---|---|
| 管线与自博弈 | `pitchfork` / `foothold` | TorchRL、恢复链、课程、league 全部跑通 | 只会击败自己；花名册仍 2/10 |
| 把真墙放进训练 | `siege` / `breach` | 强对手梯度和逐雇工控制都已提供 | barnyard margin 约 -48k 至 -67k，更多训练反而漂远 |
| 容量与基础经济 | `granger` / `draught` | 4x 网络把 barnyard 从 0 胜推到 56.8%，证明容量曾经绑定 | 延长到 420 iter 后停在约 42k 的奶业盆地 |
| 作物与劳力词表 | `sower-v3` / `cropper` / `reeve` | PLANT、施肥信用、宽网把收入抬到约 46–57k，花名册从 5/12 到 7/12 | 土地、种子和稀有建设决策仍不起量 |
| 磁带课程与墙池 | `harrow` / `anvil` / `forge` / `chisel` / `longhaul` | 学到可迁移的通用经济，最好约 54k；单墙 margin 改善约 8k | 300–1,200 iter 均停在 7/12；cleo/lena/bea/w49 仍是 0 胜 |
| 奖励、课程、模仿、探索 | `ledger` / `vise` / `haymaker` / `prospect` / `longcredit` / `tutor2` | 找到多个真实机制，单项最多 +5,115 | 改善量级远小于约 59k 缺口，且经常牺牲泛化或走捷径 |
| 开局/残局拼接 | `hybrid-cleo12` / `hybrid-endgame20` / `hybrid-d12net20` | 证明晚段技能存在，脚本开局可把本地收入推到约 89–91k | 主要价值来自录音；接上 RL 网让 cleo 天梯 1287.2 降到 696.8 |
| 最后一项结构假说 | `bzt` / `bothheads` | 验证“同一市场回合可卖又可买”和 hand-spill | 47,337 / 47,743，均低于免训练 decode-only 的 49,495；假说阴性 |

### 2026-08-25 · k01 重新验证：恢复 1287 有强证据，但尚未提交

`agents/champ/k01.py` 在全新 seed `810825..810920`、双座位、每堵墙 192 局的官方
Python 引擎结果如下。四个作业均为 CPU，32 workers，约 50–54 秒，峰值 RSS
4.5–4.7 GiB；所有 768 局正常结束。

| Slurm | 对手 | 胜负 | 胜率（95% Wilson CI） | 平均 margin（95% bootstrap CI） |
|---|---|---:|---:|---:|
| `20524057` | `closer_cleo` | 189–3 | **98.4%** `[95.5%,99.5%]` | **+15,938** `[+14,753,+17,041]` |
| `20524058` | `ledger_lena` | 188–4 | **97.9%** `[94.8%,99.2%]` | **+14,009** `[+12,913,+15,103]` |
| `20524059` | `broker_bea` | 188–4 | **97.9%** `[94.8%,99.2%]` | **+14,370** `[+13,275,+15,462]` |
| `20524060` | `w49` | 175–17 | **91.1%** `[86.3%,94.4%]` | **+8,132** `[+7,215,+9,023]` |

当前文件的 719 步 `_TRACE` 与历史 `55484175`（收敛分 2302.2）归档逐项相同；把当前
文件内嵌的 trace 与旧包分离的 `plan.py` 视作同一常量后，两份策略 AST 也完全相同。
作业 `20525210` 的 96 局直接对照进一步给出配对平均 margin `0`。该对照同时发现
`tools/eval.py` 的 h2h 汇总漏给平局计半胜：32W/32L/32T 被错误显示成 33.3%；现已与
tournament/pool 口径统一为 50%，并加回归测试。

`tools/package.sh` 也修复了纯 Python agent 没有 `.npz` 时因 glob 非零退出而中止的
问题。新归档为 `submissions/2026-08-25-k01-revalidation/submission.tar.gz`，主文件
SHA-256 与 `agents/champ/k01.py` 同为
`be1671054b7c4f133cb948f2dd363989a03237243ca02003b51fba16a66a6476`；解包后最后一个
callable 是 `agent`，720 步冒烟收入 132,361，压力门 28/28。**它已具备提交条件，
但上传和替换活跃槽位仍须用户明确授权。**即使再次达到 2000+，归因也必须写成第三方
公开轨迹恢复，不得算作纯学习突破。

### 2026-08-25 · Phase 0/1：固定 Option 失败，条件式单羊 Option 通过

完整 Phase 0 是 Slurm `20464673`、源码 `0d956e8`，审计场固定为 `starter`、
`barnyard`、`closer_cleo`、`w49`，双座位各 32 lanes。四个 checkpoint 按预登记的
全场平均终局 margin 排名：`anvil -10,585`、`chisel -11,310`、`longcredit -20,362`、
`cropper -54,453`，因此冻结 `anvil/latest.pt`（SHA-256
`a5979c09af4e352c1376711b0cb2d0db077b04d26aaaa31139d7944e110f3b29`）。`anvil` 对
starter/barnyard 接近全胜，对 cleo/w49 仍为 0 胜；这不是新强模型，只是统一场里的低层
起点。

配对状态门也在 CPU 和 CUDA 两条路径完成：GPU 作业 `20467057` 使用 H100 10GB MIG，
在 step 200 fork 后重放 64 回合、跨两个游戏日，3 lanes 的完整 snapshot 逐字节一致；
作业运行 18 秒。GPU 可用性因此不再是 Phase 0 未决项。

`anvil` critic 的分时段平均 explained variance 为 day 0–4 `0.233`、5–11 `0.491`、
12–19 `0.739`、20–29 `-0.292`。其建设行为也仍稀薄：合法时 BUY_LAND 选择率
`0.147%`、BUY_ANIMAL `1.38%`，而 BUY_SEED `7.52%`、HIRE `5.31%`。这直接支持
“后程 value 校准崩掉 + 稀有门控动作采样不足”的诊断；单独调 lambda 没有修好它。

Phase 1 的每个数字都是相同初态 fork 后的配对终局 margin 差，四对手、双座位、每格
32 pairs；完整定义与原始记录在对应 `rl/runs/<name>/result.json`：

| Option / 变体 | 全场 margin 差（95% CI） | held-out / 机制 | 判词 |
|---|---:|---|---|
| day-0 `EXPAND_LAND` | **-44,407** `[-47,474,-41,537]` | w49 两座位约 -54k/-55k | 明确有害 |
| day-0 `ESTABLISH_CROP:STRAWBERRY` | **-8,133** `[-10,263,-6,081]` | 完成 256/256，仍挤掉约 2 头牲畜 | 明确有害 |
| day-4/8 `EXPAND_LAND` | +2,354 / +3,067 | 收益来自 starter；w49 仍负 | 不泛化 |
| `$1k` 余量 `EXPAND_LAND` | **+2,820** `[+1,224,+4,578]` | w49 `-182/+228`，两座位反号且 CI 跨 0 | 不过门 |
| 买地 + 8 草莓 | -275 `[-2,098,+1,562]` | w49 `-3,311/-3,715` | 不过门 |
| 增加 2 牛 | **-1,829** `[-3,316,-403]` | w49 约 -8.3k | 明确有害 |
| 增加 2 羊 | +1,149 `[-100,+2,557]` | money/future-worth 上升，w49 约 -1.1k | 最接近，仍不过门 |
| 增加 4 羊 | **-12,059** `[-13,861,-10,245]` | 完成率 155/256 | 剂量退化，关闭 |
| 保留 `$3k` 现金 | **-38,722** `[-42,076,-35,309]` | 0/256 达标，生产链断流 | 明确有害 |

首轮结论不是“HRL 无效”，而是**无条件执行的这些 Option 不是可靠的高层动作**。买资产
会挤掉别的生产链；只买地不保证利用容量，组合种植又牺牲牲畜，强制扩群则缺乏持续维护。

后续 `SCALE_HERD:SHEEP` 目标 1 的 discovery（作业 `20488876`，16 seed × 两个强墙 ×
双座位）显示收益集中在首次可购买时现金较低的状态。预先冻结规则“day >= 4、购买后保留
`$1,000`、触发现金 <= `$1,900`、最多增加一只羊”后，作业 `20490165` 用全新
`270825+` seed 验证：128 个配对决策的终局 margin `+2,334`，95% CI
`[+1,125,+3,542]`，64/64 次被选择的 Option 完成，`closer_cleo`/`w49` 四个席位格
全部同号。该规则因此是 Phase 1 第一个通过门的高层动作。

导出实现于 `4b8b7d3`，配对统计按 seed 聚类的修正于 `10d54a2`。官方 Python 引擎作业
`20491630` 再用全新 `280825+` seed 比较导出规则与原始 greedy `anvil`：128 个匹配
场景上 margin `+2,474 [+1,280,+3,737]`，自身 money `+1,832 [+650,+3,020]`；分墙为
`closer_cleo +865`、`w49 +4,084`，256/256 局状态均为 DONE。两者仍然都是 0/128 胜，
所以这是“Option 可用”的证据，不是“接近 1287”的证据。

机械重复同一规则的作业 `20492949` 随即失败：最多两次相对最多一次的 margin
`-881 [-2,570,+648]`，`closer_cleo -1,762`、`w49 0`。候选自身多赚 `$1,603`，但对手
因共享市场/RNG 多赚 `$2,484`，说明 Option 收益不可线性叠加；该变体停止。下一步转为
记录价格、市场库存和商店消费强度，学习单次 Option 的状态条件。GPU 当前不是阻塞点。

状态条件数据作业 `20493659` 收集了 6 个对手、双座位、64 seed 的 768 个配对决策。
包含实时价格、市场库存和商店消费强度的 ridge 模型在 held-out `w49` 上只有 `+2,166`，
没有超过简单现金规则的 `+2,198`，更低于该批次无条件执行的 `+3,017`。开发对手上冻结
出的浅规则 `demand_milk <= 1` 随后进入全新数据验证，而不是在同批样本上继续报分。

验证作业 `20494234` 使用全新 `320825+` seed、`closer_cleo/lena/bea/w49`、双座位各
32 pairs。总体 margin 是 `+2,067 [+977,+3,145]`，199/256 个决策被选中且 199/199
完成；但胜负差仍为 0，最关键的 `closer_cleo` 两格为 `+593/-1,127`，违反预注册的
逐墙逐席位同号门。其他格虽然为正，也不能抵消这一失败。事后追加 `$1,900` 现金条件
没有修复 cleo，因此不再在该验证集上调阈值。Phase 2 的下一步改为完整建设阶段 Option，
不把这个 stump 嵌入导出体。

完整建设执行器随后把 `land/crops/herd` 设成绝对里程碑，并只覆盖必要的采购、建设、
放置以及最多两名 FEED/PLANT 帮手。第一版把其余帮手全部改成 AUTO，作业 `20496109`
虽 64/64 完成却为 `-2,612 [-3,966,-1,322]`；这证明“有限职责”必须落实到每个帮手，
不能用另一种全局调度替代冻结策略。限制为只优先复用 IDLE/AUTO 槽位后，作业
`20496510` 在新 seed 的 128 pairs 上得到按 seed 聚类的
`+4,904 [+1,910,+8,218]`，八个墙/席位均同号，但 240 回合 timeout 截断了 3 个分支。

预注册验证 `20497469` 只把 timeout 延长到 264，并使用再一批 `380825+` seed：
256/256 完成，但总体 margin 回落到 `+1,117 [-1,103,+3,501]`；自身 money
`+2,125 [-850,+4,952]`。`closer_cleo` 两席位为 `-666/-976`，held-out `w49` 为
`-600/-750`，且没有任何 cleo 胜局。固定 `2 land / 28 crops / 7 herd` 目标因此停止，
不导出。工具仍保留，因为它已经能审计耦合建设计划；下一步先量多 Option 的逐状态
oracle 上限，确认动作集合足够后再训练选择器。

### 2026-08-25 · 多 Option oracle：选择有价值，但现有技能集合连一局强墙都赢不了

`ac13f1a` 给每个建设 Option 加入独立绝对目标，并按 `(opponent, seat, seed)` 合并同一
fork 状态的分支；输出同时包含允许任意分支与只允许已完成 Option 的逐状态 oracle。
这里的 oracle 看过终局，只是**不可部署的乐观上限**，用途是先判断动作集合是否承重。

作业 `20498667`（commit `ac13f1a`）在 `480825+` 的 16 个新 seed、cleo 双席位上枚举
`1-3 land / 20-36 crops / 5-9 herd` 六档。所有两地目标 32/32 完成，三地目标 16/32
完成；严格 oracle 相对 `anvil` 为 `+12,630 [+7,903,+17,602]`，32 个状态中 24 个改善。
但绝对 margin 仍为 seat0 `-49,081`、seat1 `-49,619`，胜局 **`0 -> 0/32`**；最好一局
也还差 `$20,403`。按预注册门，不训练只会选择建设强度的 controller。

随后扩了三类不同执行技能：

| 作业 / Option | 配对 margin 差 | completed-only oracle | 强墙胜局 |
|---|---:|---:|---:|
| `20499629` 全程 `hands_auto` | **-21,081** `[-29,973,-12,398]` | `+10,581`（含建设控制） | `0 -> 0/32` |
| `20499629` 建设后 `AUTO`，32/8 | +3,744 `[-3,334,+10,806]` | 同上 | 0 |
| `20500743` day-4 冻结专家切换 | d0/chisel +2,277；d12/d20 **-10k 至 -13.5k** | `+7,494 [+3,507,+12,062]` | `0 -> 0/16` |
| `20501341` 建设 32/8 后切 d12 | **+6,530** `[+3,078,+10,189]` | `+8,242 [+5,643,+11,594]` | `0 -> 0/16` |

最后一行相对同批纯建设控制 `+5,119 [+1,028,+9,541]` 有一点协同，但 oracle 的绝对
margin 仍约 `-49k`。晚段专家只有拿到高质量农场才强；从 anvil 的 day-4 状态直接接手会
退化，先做当前建设里程碑再接手也没有把状态推到其训练分布。`hands_auto` 的重度阴性还
复核了历史 hand-spill 判词：局部调度不是那 40-60k 缺口的主因。

实现提交为 `90d497e`（持久生产 Option）、`d81fb7b`（冻结 `policy_npz` Option 与输入
哈希）和 `8e0aca1`（建设后切专家）。四个作业均为 CPU，耗时分别 `2:31 / 4:06 /
7:23 / 3:00`，峰值 RSS `1.10 / 1.03 / 1.02 / 1.30 GiB`；没有理由为这类审计申请 GPU。
下一步不在这些标签上训练高层分类器，而是先从强轨迹抽取状态闭环技能，或用短视宏观
搜索生成能真正翻转 cleo 胜负的新动作。

### 2026-08-25 · 强轨迹 Option 拆解：2000 分行为可达，但“同配额状态机”仍为 0 胜

提交 `3f48329` 增加了帮手 `BUILD/PLACE`、按 lane 覆盖原始复合动作、录像前缀 Option，
以及保持默认 `barnyard` 逐动作不变的 `industrial` / `k01_state` 状态闭环诊断 profile。
所有数字使用 `anvil/latest.pt`、`closer_cleo`、seed `620825..620832`、双座位共 16 个
配对分支；这是开发集机制定位，不是正式 held-out 验收。

| 干预 | 配对 margin 差（95% CI） | 强墙胜局 | 判词 |
|---|---:|---:|---|
| 只做首回合专家采购篮子 | -29,297 `[-58,729,+135]` | 0/16 | 冻结低层无法利用资产 |
| 24 回合状态闭环开局 | +9,044 `[-16,252,+34,339]` | 0/16 | 方差大，仍未建成 19 株 |
| 专家录像前 24 回合 | -2,843 `[-15,073,+13,783]` | 0/16 | 一天开局不是主缺口 |
| 专家录像前 288 回合 | +35,974 `[+21,469,+50,480]` | 0/16 | 12 天仍不能把弱后程带过墙 |
| 专家录像前 480 回合 | +35,053 `[+23,886,+45,930]` | **2/16** | 首次跨过 Option 胜负门，但仍是开环教师 |
| 默认 `barnyard` 前 480 回合 | -24,527 `[-30,839,-18,640]` | 0/16 | 28 头动物目标挤掉作物 |
| 只改为 13 头 / 高密度作物 | -17,882 `[-26,275,-12,283]` | 0/16 | 配额修正不够 |
| `k01_state` 完整 720 回合 | -6,650 `[-12,043,-2,165]` | 0/16 | 状态闭环执行器仍不及冻结网络 |
| 专家录像完整 720 回合 | **+67,111** `[+59,821,+72,700]` | **16/16** | 绝对 margin 均值 `+15,277` |

`k01_state` 不是录像回放：只有首回合采购篮子与日级容量目标来自 k01，之后的移动、建设、
种植、维护和销售都依据当前状态。它修掉了两个具体执行浪费：日工一次搬 8 份饲料导致
日终丢失，以及每回合重选远端任务；在单局中能达到 3 块地、约 50–58 株、13 头，但
完整验证仍是 0/16，且相对基线显著退化。农场动作与市场动作的交叉替换也都失败：状态
农场 + 专家市场平均 margin `-84,528`，专家农场 + 状态市场 `-129,107`，只有完整专家
序列为 `+14,331`、16/16 胜。两层的时序是强耦合的，不能分别模仿后再拼接。

**判词**：2000 分并非环境或动作可达性问题，仓库内的完整专家轨迹已再次通过强墙；但
它仍是第三方开环教师。按相同资产配额写一个无记忆优先级调度器，哪怕加入持久目标和复合
市场单，也不能恢复其收益。下一项有效工作应抽取跨回合的单位路线和带库存约束的市场队列
状态，形成真正持久的低层 Option；在它产生 held-out 胜局前，仍不训练高层 selector。

后续开发批次只改执行器，不改目标配额：加入与教师一致的 30 天日工预算、优先完成脚下
任务、末两日保留收获工，以及按日持久计数的选择性施肥。相同 16 个 cleo 配对中，相对
anvil 的 margin 改善从上表的 `-6,650` 提到 **`+12,264 [+7,443,+16,331]`**；自身
money 均值 42,829，绝对 margin 仍为 **-39,569**，胜局仍是 **0/16**。因此这些改动
先保留为低层 Option 基础设施；这个开发集正增益本身不能算过门，更不能当成已打过
1287，随后使用全新 seed 做正式验收。

提交 `50be4ce` 后的预注册 held-out 作业 `20527366` 使用全新 seed `1180825+`、
cleo/lena/bea/w49、双座位各 32 pairs。256/256 个整季 Option 完成；相对 anvil 的总体
margin 为 **`+16,997 [+12,703,+21,442]`**，八个对手/席位格全部为正。cleo 两席位分别
改善 `+22,454/+27,812`，并首次出现 **1/64** 胜；held-out w49 为
`+2,305/+2,460`。这通过了登记的最低动作集合门。

仍需保留两个限制。第一，绝对 margin 仍为 cleo `-37,733/-36,274`、其他墙约
`-43k..-52k`，所以离稳定胜墙还很远。第二，自身 money 增量只有
`+6,420 [-139,+12,887]`，而对手 money 下降 `-10,577 [-19,922,-806]`；总体 margin
虽可靠，机制同时含共享市场/RNG 对对手的抑制。这个 Option 从第 0 回合接管整季，只有
它与 `FOLLOW_POLICY` 两个动作时训练 selector 没有意义。下一步先拆成日级可触发的路线
和现金流 Option，再做同状态 oracle/离线搜索。

现金流拆分的首个 16-pair pilot（seed `1280825+`、cleo、双座位）也按门停止：在同一
批配对上，保留价格底线并仅按 `$1,500/$3,000` 现金缺口扩大卖单的 `k01_cashflow`
相对 anvil 只改善 **`+2,214 [-4,158,+8,150]`**，而原 `k01_state` 为
**`+10,795 [+4,986,+16,335]`**，直接退步 `-8,581`，两者均为 0/16 胜。说明销售
节流不能只看当前现金缺口；它和未来采购、库存容量及价格路径仍是耦合队列。该 profile
不进入主线，也不扩大样本；下一版必须把待采购承诺和跨日库存目标显式放进 Option 状态。

### 2026-08-25 · 日级窗口与 scope 消融：最短有效承诺约 10 天，农场/市场不可拆

提交 `6f1594d` 后，`macro-k01-window-d{00,05,10,15,20,25}-pilot` 在相同新 seed
`1380825+`、cleo、双座位各 16 pairs 上，分别让 Option 只接管一个 5 天窗口。审计器
现在允许 `tape_prefix` / `barnyard_prefix` 在 `--min-day` 日初触发；旧的 day-0 语义
保持不变。下表均为相对冻结 anvil 的终局 margin：

| 接管日 | `k01_state` | k01 开环教师 |
|---:|---:|---:|
| 0–4 | +5,849 `[-1,329,+13,248]` | +15,695 `[+8,918,+22,669]` |
| 5–9 | -5,234 `[-10,451,+118]` | -45,846 `[-53,001,-39,373]` |
| 10–14 | +3,022 `[-1,112,+6,960]` | -29,298 `[-34,798,-23,720]` |
| 15–19 | -4,472 `[-6,733,-2,098]` | -18,407 `[-24,142,-12,576]` |
| 20–24 | +339 `[-640,+1,360]` | -10,687 `[-14,221,-7,336]` |
| 25–29 | +387 `[+171,+609]` | -4,676 `[-6,565,-2,778]` |

中途硬接教师全部有害，因为录像依赖自己此前形成的资产与位置，不能当成任意状态可用的
Option。`macro-k01-prefix-{early,late}-pilot` 在另一批 seed `1480825+` 从 day 0 累计
接管，5/10/15/20/25/30 天依次为 `-2,089 / +12,202 / +8,193 / +6,963 /
+13,508 / +17,756`；除 5 天外，后五个区间均排除 0，但全部 0/32 胜。最短可靠承诺是
连续前 10 天，不是一个可任意插入的 5 天技能。最初的 12-cell 作业 `20534058` 按节点
实测速率预计会越过 20 分钟墙钟，运行 4:56 后主动取消并拆成 `20534706/20534707`；
两者分别用 2:28/4:23、峰值约 1.2 GiB 完成。

提交 `1ebe796` 增加了 `farm` / `market` 局部 override。全新 seed `1680825+` 的
`macro-k01-scope-ablation-pilot`（32 pairs）显示：farm-only 为
`-3,759 [-14,747,+6,498]`，market-only 为 **`-42,380 [-52,306,-32,382]`**，只有
联合接管为 **`+17,432 [+7,847,+27,057]`**，三者仍均为 0 胜。市场单独接管还使对手
收入增加 32,113，证实共享市场反馈是关键耦合项，不能把两层独立交给 selector。

最后测试的 `k01_urgent` 会在全局有饿死/满仓任务时禁止低优先级脚下工作抢占。它在一个
机制种子中保住了原本逃走的动物，但正式 `20537879`（新 seed `1780825+`、64 pairs）
相对原 `k01_state` 的自身收入为 `+4,598`，对手收入却为 `+8,895`，直接 margin
**退步 `-4,297 [-9,238,+477]`**，仍为 0 胜。按预注册门删除该 profile。判词是：当前
状态执行器的收益来自至少 10 天的联合资产/路线/市场闭环；下一动作必须带显式前置里程碑
和联合内部状态，不能再把日历段或 farm/market scope 当成独立 Option。

### 为什么反复训练没有继续进步

**主因是学习问题的形状，不是训练吞吐或迭代数。** 达到强经济需要按正确顺序完成
`卖出维持现金流 -> 买地/种子/动物 -> 分配雇工 -> 连续浇水/施肥/收获`。买地等门控
动作一季只有几次，收益却在数百步后出现；当前逐步 PPO 在 719 步轨迹上更容易强化
已经高频、立即回款的卖出/奶业/小麦动作。`longhaul` 把同一配方延长到约 1,200 iter
仍停在 7/12，是“再多训一些”已经被直接否掉的对照。

**现有 dense potential 能提供坡，但不能提供这条序列的反事实信用。** 调高某个资产的
权重时，策略反复找到更便宜的代理路径：`haymaker` 通过少养牲畜而非种小麦获益，
`foreman` 雇满 12 人却因无活可干亏约 10k，`penner` 多 BUILD/PLACE 后反而养死牲畜。
这些不是优化器没收敛，而是它成功优化了一个不等于“建成大农场”的局部目标。

**强对手制造的是提前数日决定的产品组合问题。** 策略看得到价格和库存，因此不是
观测缺失；但当 cleo 倾销牛奶时，牛早已买下。把市场价直接塞进 potential 的
`bourse` / `vise` / `ledger` 会针对训练墙改善、同时在 held-out 对手上崩，说明固定
base-price potential 其实承担着正则化。当前算法没有既保留跨对手泛化、又给早期建设
决策正确信用的机制。

**动作可表达性曾经是墙，但已不是剩余主墙。** FEED、PLANT、FERTILIZE、PLACE、批量
采购、逐雇工头等扩展确实打开过第一轮跃迁；之后八类词表/解码改动七类阴性，正向项
通常只有 1.8–3.8k且不能相加。最新 `bzt` 进一步表明，取消“卖出与采购争同一回合”
仍没有让训练后的 `BUY_SEED` 或土地规模起来。

**监督和课程也在放大频率偏置。** 开环磁带约一半市场标签在学习者状态上非法；合法
标签又由高频动作主导。`tutor2` 抬高 BUY_SEED 的同时把一季只发生两次的 BUY_LAND
几乎压没。反向课程学会残局但不能向第 0 天迁移；强墙池能教会一般经济，却不能替代
开局的稀有资产决策。

**最后还有测量问题。** 本地面板曾把两个真实天梯 agent 排反 266 分，四个行为尺子
也无法区分它们；所以“小幅本地上涨”从来不等于天梯进步。08-24 又发现
`tools/eval.py` 把 `wilson()` 返回的 0–100 百分数当成 0–1 比例，导致历史 stdout 的
CI 多放大 100 倍、自动 `VERDICT` 对多数非零胜率误报 A 胜。JSON 中原始胜负、收入和
百分数值没有损坏，本文的汇总读数也不依赖那些自动判词；代码已修并加回归门。

### 现在可以停止重复的方向

更多同配方迭代、扩大墙池、单独再加词表、继续调 potential 标量、强制追逐帮手/土地/
空地等相关指标，以及用本地中位收入外推天梯分，均已有直接反证。下一代若仍以 RL 为
主，必须改变**稀有长期决策的信用机制**，而不是再改一个权重。

2026-08-24 对外部建议的取舍已同步进 `rl/TODO.md`：先冻结基线并补 critic 分时段诊断；
再用模拟器 fork 做配对反事实 rollout，验证哪些持久建设 Option 真的提高终局结果；通过后
只训练轻量高层 controller；再用同一 Option 接口做离线 beam/CEM/MCTS 搜索并蒸馏；最后
才考虑高低层联合 HRL。连续“建设意愿 + 硬阈值”不作为首选，因为因果决策会落在 PPO
梯度之外；反事实差值先作审计/监督目标，不在无校准时直接注入现有逐回合 PPO。验收先要求
纯 RL 对 `closer_cleo` 出现非零胜率并让其边际贡献不再为负，再谈 2000。

Everything from run #1 onward lives in `data/arena.sqlite` and can be re-queried:

```bash
python tools/db.py stats
python tools/db.py top --run 2 -n 40
sqlite3 data/arena.sqlite "SELECT * FROM runs"
```

---

## Tournaments in the database

| Run | Label | Shape | Agents | Episodes | Headline |
|---|---|---|---|---|---|
| **#1** | `library-screen-594` | panel, 8 seeds | 594 | 56,944 | `orchardherd` sweeps the top — later shown to be an artefact of two engine bugs |
| **#2** | `confirm-38-representative` | roundrobin, 20 seeds | 38 | 28,120 | `barnyard` 14th; first sign that rank and money had decoupled |
| **#5** | `enhanced-vs-field` | roundrobin, 20 seeds | 36 | 25,200 | first enhanced cut ranks 8th; herd deadlocked at nine |
| **#6** | `enhanced-fixed-vs-field` | roundrobin, 20 seeds | 36 | 25,200 | after the deadlock and land fixes: 75.8% against the field leader |
| **#7** | `ladder-field-spar` | roundrobin, 24 seeds | 34 | 26,928 | first field with opponents we did not write; `enhanced` ranks **27th of 34** |
| **#8** | `factorial-screen-960` | panel, 12 seeds | 960 | 184,224 | balanced produce×land×muck×market; the three reconstructed ladder shapes take the top three |
| **#9** | `factorial-confirm-40` | roundrobin, 48 seeds | 40 | 74,880 | `enhanced` **39th of 40**; `compost` good for strawberry, bad for melon |
| **#11** | `refine-labour-intel` | panel, 12 seeds | 640 | 122,856 | `crew` beats every labour option by 39+ points; **`intel` is worth nothing** |
| **#12** | `crop-ladder` | panel, 24 seeds | 72 | 27,552 | the strawberry ladder peaks at 28 tiles — on the pre-`compost` engine |
| **#13** | `crop-confirm` | roundrobin, 64 seeds | 24 | 35,328 | `bigberry` 1st at 86.1% |
| **#14** | `labour-recross` | panel, 24 seeds | 112 | 42,912 | `crew` (11 hands, 6%) still optimal on the fixed engine |
| **#15** | `crop-ladder-2` | panel, 24 seeds | 72 | 27,552 | 28 tiles still the peak after watering got cheaper |
| **#16** | `melon-recross` | panel, 32 seeds | 48 | 24,448 | more melon does not help locally, though ladder winners out-sell us on it |
| **#17** | `berryflood-confirm` | roundrobin, 64 seeds | 27 | 44,928 | `berryflood` (50 strawberry, copied from the 113k opponent) does not reach the top 11 |
| **#18** | `late-filler` | panel, 32 seeds | 32 | 16,256 | late-season carrot/wheat fillers rank 10-12; filling idle tiles is worse than leaving them |
| **#19** | `final-confirm` | roundrobin, 96 seeds | 14 | 17,472 | `marketgarden` 1st at 78.3% — fertilizing makes 18 strawberry tiles beat 28 |
| **#20** | `wheat-filler` | panel, 32 seeds | 24 | 12,160 | wheat on `smallhold` loses; the ladder winners' wheat is not what makes them win |
| **#21** | `wheat-after-ramp` | roundrobin, 64 seeds | 20 | 24,320 | wheat retried after the hiring ramp, still loses |
| **#22** | `bench-baseline` | roundrobin, 96 seeds | 12 | 12,672 | **the old reference field had saturated**: everything beat the anchors 97-100% |
| **#23** | `cand-vs-bench` | panel, 96 seeds | 6 | 11,520 | hiring ramp worth **+33 points** against a field that can rank; two identical builds score identically, validating the measurement |
| **#24** | `mg-sweep` | panel, 96 seeds | 9 | 17,088 | smaller and denser wins: `mgtight` 90.2% against `marketgarden` 59.1% |
| **#25** | `mg-sweep-2` | panel, 96 seeds | 8 | 15,360 | the shape brackets — 16 strawberry beats 14 and 18 |
| **#26** | `mgtight-confirm` | roundrobin, 96 seeds | 14 | 17,472 | `mgtight` / `mgtightwide` tied at the top, 14 points clear of the submitted shape |
| **#27** | `axis-recheck` | panel, 32 seeds | 144 | 92,160 | every axis re-measured on a field with spread; all previous choices confirmed |
| **#28** | `liquidate-day` | panel, 96 seeds | 5 | 9,600 | liquidate on day **29**, monotone: 92.9 / 90.2 / 85.9 / 76.0 |
| **#29** | `mgtight-fillers` | panel, 96 seeds | 7 | 13,440 | fillers on the tight base lose three ways — the idle time is not convertible |
| **#30** | `final3-confirm` | roundrobin, 96 seeds | 17 | 26,112 | with the here-pass, the wheat filler **flips** and `mgtightgrain` reaches the top |
| **#31** | `duel-final` | roundrobin, 256 seeds | 14 | 46,592 | `mgtightgrain` 86.7% and $75,727 over 46,592 episodes; beats `mgtightwide` 58.8% head to head |
| **#32** | `resweep-new-engine` | panel, 64 seeds | 24 | 30,208 | invalidated by the filename collision — `bench2` shares names with the roster |
| **#33** | `resweep-clean` | panel, 96 seeds | 7 | 13,440 | redone with unique names |
| **#34** | `herd-resweep` | panel, 96 seeds | 7 | 13,440 | herd size re-measured on the new scheduler: 7+3 still optimal, monotone both ways |
| **#36** | `axis-recheck-2` | panel, 32 seeds | 144 | 92,160 | every axis re-measured **again** after the here-pass; nothing flips |

Runs #10 and #35 were duplicate ingests of #11 and #36 and were deleted; `PRAGMA integrity_check`
is clean and the totals below exclude it.

**Twelve further A/B ablations were analysed straight from their shard JSONL and
deliberately not ingested**, because each is one change against one control
rather than a ranking: sticky assignment, idle pre-positioning, alternate-day
watering, CARE priority, `paced` selling, `shopwise`, the fertilizer reserve, the
carrying threshold, the ramp shape, the inverted scheduler, two-pass and zone
scheduling, the here-pass and the tile hold. Every one is written up with its arm
size in `docs/ROADMAP.md §11` — **eleven landed, seventeen were rejected**.

**Three more on 2026-08-11**, also read from shard JSONL rather than ingested,
and for a second reason: all three carry builds that share basenames across
directories, and `short(path)` is the basename, so ingesting would merge them
into one ratings row — the defect that corrupted runs #22 and #32.

| label | arms | episodes | outcome |
|---|---|---|---|
| `bootlock` | 3 engines × 6 produce × 2 land | **137,664** | the opening seed freeze is a trade, not a deadlock — rejected, `ROADMAP.md` §11 |
| `handover` | 17 handover days + anchors | 62,016 | no handover day helps; the curve runs to 100% recording — `ROADMAP.md` §3 D |
| `handover-adopt` | same, targets adopted at handover | 39,936 | ±4 points, no change in shape |
| `endgame` | 3 endgame variants × 10 shapes | 109,440 | keeping the task list alive on the liquidation day loses; so does never liquidating |
| `endhire` | hire on the liquidation day, ± the task list | 109,440 | **landed**, +1.66 points — the workforce was being dismissed on the most valuable day |
| `endhire-ghosts` | the same two engines vs 156 ladder trajectories | 3,120 | independent confirmation, +4.55 points |
| `endD-shape` | 10 shapes under the new engine, 192 seeds | 72,960 | disagrees with the ghost field on the produce axis — tiebreaker `endD-ref` in flight |
| `tracelib` | 959 post-rebalance top episodes mined for distinct plans | 1,894 traj | **201 distinct plans**, 9:1 duplication — `ROADMAP.md` §10 |
| ~~`metaduel`~~ | 12 mined plans + champion | 28,080 | **void** — the replays were one turn late; see `ROADMAP.md` §10 |
| `duel101` | 101 mined plans, one shared wrapper, 48 seeds | **477,225** | champion 64th at 36.5%; 3.3% of triples are cycles but none inside the top 12 — `ROADMAP.md` §10 |

Reproduce any of them without the database:

```bash
python - <<'PY'
import glob, json, collections, os
w = collections.Counter(); g = collections.Counter()
for s in glob.glob("data/shards/bootlock/shard-*.jsonl"):
    for line in open(s):
        r = json.loads(line)
        for i, side in enumerate(("left", "right")):
            a = r[side]
            if "/bench3/" in a or "/ref/" in a: continue    # panel, not candidate
            g[a] += 1                                       # key on the full path
            w[a] += (r["money"][i] > r["money"][1-i]) or 0.5*(r["money"][i] == r["money"][1-i])
for a in sorted(g, key=lambda k: -w[k]/g[k])[:5]:
    print(f"{100*w[a]/g[a]:5.1f}%  {a}")
PY
```

Runs #8 and #9 were the first sharded runs: 48 array tasks × 32 cores = 1,536
cores, `KG_FAST_ENV=1`. Run #8's 184,224 episodes took about six minutes of wall
clock against the ~9 hours the same work would have taken on one 32-core job.

**3,397,241 episodes total** across 87 runs, plus 737 real ladder episodes. Regenerate these three numbers with `python tools/db.py stats` -- they are the only figures here that drift, and they drift every time anyone runs anything.

The `文档` table in the top-level `README.md` indexes every document by question.

Runs #1–#6 ran on an engine with two defects that hurt crop plans much more than
herd plans, and on a library that could not issue `FERTILIZE`. **Do not compare
their numbers with #7's.** `docs/ROADMAP.md §11` §4 has the controlled A/B and
what each fix was worth.

## Ladder episodes (real opponents)

| Pulled | Submissions | Episodes | Kept | Headline |
|---|---|---|---|---|
| 2026-08-09 | `55332339`, `55358912` | 94 | 125 KB of digests, 1.9 GB of replays discarded | 48% overall; `enhanced` 49%, `barnyard` 47% — a 384/384 local gap is worth two points here |

`ladder_episodes` in `data/arena.sqlite`. Re-query with
`python tools/ladder.py stats`.

Run #1's roster is the whole `all` plan from `tools/registry.py`. Run #2's roster
is run #1's top 8, the best carrier of every atom option, all eight boundary
corners, plus `barnyard` and `starter`.

---

## Earlier experiments (JSON in `logs/`, pre-database)

These predate the SQLite store. Kept because published conclusions cite them.

| What | Scale | Output | Headline |
|---|---|---|---|
| Tunable league | 8 agents × 24 seeds × 2 seats = 1,344 eps | `logs/league_v1.json` | `HAND_CAP=11` beats the then-default 14; `TARGET_COWS=10` confirmed |
| Probe league | 21 agents × 16 seeds × 2 seats = 6,720 eps | `logs/league_probes.json` | `one_quadrant` 1st, `dump_all` 2nd *above* `barnyard`, `product_only` last on $78 |
| Adversary league | 8 agents × 24 seeds × 2 seats = 1,344 eps | `logs/league_adv.json` | pure denial (`parasite`) went 0/168 and made opponents *richer* |
| A/B: `dump_all` vs `barnyard` | 192 seeds × 2 seats = 384 eps | `logs/eval_dump.json` | 71.4% win, CI [66.6%, 75.6%], while earning ~25% less |
| A/B: `one_quadrant` vs `barnyard` | 192 seeds × 2 seats = 384 eps | `logs/eval_1q.json` | 93.2% win, CI [90.3%, 95.3%], earning *more* |
| A/B: `enhanced` vs field leader | 384 eps | `logs/eval_enh_vs_top.json` | **75.8% win**, CI [71.3%, 79.8%], margin +3,016 |
| A/B: `enhanced` vs `barnyard` | 384 eps | `logs/eval_enh_vs_barn.json` | **100% win** (384/384), margin +25,753 |
| Quadrant sweep | 4 configs × 8 seeds | — | 1→49,078 · 2→68,738 · 3→68,892 · 4→68,892 |
| Crop-scale sweep | 6 configs × 8 seeds | — | scaling the crop plan up is monotonically worse |
| Stress suite | 28 pathological configs | — | `barnyard` 28/28 clean, worst turn 145 ms |

Grand total including these and the ablations: **well over 1.3 million episodes**.

---

## Submissions

| Date | Submission | Agent | Snapshot | Local evidence | Ladder |
|---|---|---|---|---|---|
| 2026-08-13 | `55489160` | `kawashigi-k06` — the same team's strongest recorded line, chosen on the panel | `submissions/2026-08-13-kawashigi-k06/` | Panel win rate **98.5%** [97.8, 98.9] over 1,920 episodes against 92.4% [91.2, 93.5] for the incumbent, and **60.8%** [57.3, 64.2] head to head over 768. Beats all ten panel members; the incumbent's weakest matchup is 78.6%. 28/28 stress clean; 720/720 actions identical after packaging. | pending — **this is the prospective test of the panel, see below** |
| 2026-08-13 | `55484175` | `topline` — a recorded top-of-ladder plan under the `closer_cleo` market layer | `submissions/2026-08-13-topline/` | 92.4% over 1,920 episodes against the ten strongest plans previously mined (best incumbent 79.9%), **and** the highest-rated source team of the 371 in the library (カワシギ, #1 at 3,240). Two independent signals converge. Submitted as calibration, not as an answer — see the null result below. 28/28 stress clean; 720/720 actions identical after packaging. | **2144.1 and still climbing** — 21–1 over 22, so **not yet a score**: see the one-third rule below. Beats 1218.6 for the plan it replaced, on opponents of the same strength ($73,884 vs $77,991 mean opponent money, +$6,421 margin against +$1,135). |
| 2026-08-12 | `55458466` | `closer_cleo` + terminal at 714 (resubmit) | `submissions/2026-08-11-closercleo-term714/` | 91.7% [90.9, 92.5] over a 28,080-episode round robin against the twelve most-played plans mined from 959 post-rebalance ladder episodes, beating all twelve. The field is strictly transitive, so no ensemble has anything to exploit. 28/28 stress clean. | **1218.6** — the same file scored 1363.7 five days earlier, see below |
| 2026-08-11 | `55442784` | `closer_cleo` + terminal at 714 | `submissions/2026-08-11-closercleo-term714/` | Threshold sweep over 384 seeds against `bench3`, 10,800 episodes an arm: 714 reaches a 98.1% plateau against 95.2% unchanged. | **1363.7** — our best to date |
| 2026-08-11 | `55439740` | `closer_cleo` (third-party, unmodified) | `submissions/2026-08-11-closercleo/` | 99.2% of `bench3`+refs over 3,072 episodes and 99.4% of the 156 ghost trajectories, against 60.9% / 57.7% for our best engine. First of five in a 3,072-episode round robin among the trace agents at 92.7%, beating `slotter_silas` 88.0% and `ledger_lena` 91.9%. Raw replayed trajectories score **0.0%** against all four wrapped agents, so the value is the adaptive layer and not the trace. 28/28 stress clean. | **1287.2** — our own change is worth less than the gap between two runs of it |
| 2026-08-07 | `55332339` | `barnyard` | `submissions/2026-08-07-barnyard/` | ~67k median vs `starter`; 28/28 stress | 621.4; **47% over 59 real episodes** |
| 2026-08-08 | `55358912` | `enhanced` (tar.gz, 5 modules) | `submissions/2026-08-08-enhanced/` | 100% vs `barnyard` and 75.8% vs the field leader, both over 384 episodes | 623.6; **49% over 35 real episodes**, level with `barnyard` |
| 2026-08-09 | `55385371` | `marketgarden` | `submissions/2026-08-09-marketgarden/` | 34.9% vs `orchardherd` 16.1% over the balanced 960-cell factorial | 700.1 over 12 episodes |
| 2026-08-09 | `55385995` | `bigberry` | `submissions/2026-08-09-bigberry/` | 1st of 24, 86.1%, over a 35,328-episode round robin | 647–837 over 10 episodes; **71% win rate (5 of 7 pulled)** |
| 2026-08-09 | `55386385` | `bigberry` + alternate-day watering | `submissions/2026-08-09-bigberry-altwater/` | 82.2% against 71.1%, 3,072 episodes an arm | 780.4 over 10 episodes |
| 2026-08-09 | `55386857` | + fertilizer price gate | `submissions/2026-08-09-bigberry-fertgate/` | 85.0% against 83.3%, 3,072 an arm | 711.4 over 4 episodes |
| 2026-08-09 | `55386…` | + `shopwise` herd | `submissions/2026-08-09-bigberry-shopwise/` | 71.9% against 68.4%, 6,144 an arm | pending |

| 2026-08-10 | `55402695` | `mgtight` | `submissions/2026-08-10-mgtight/` | 1st of 24 over 35,328 episodes | **759.9** over 41 episodes |
| 2026-08-10 | `55404837` | + liquidate on day 29 | `submissions/2026-08-10-mgtight-liq29/` | monotone sweep, 92.9/90.2/85.9/76.0 | **838.4** over 47 — the liquidation day is worth +69 on the ladder |
| 2026-08-11 | `55418588` | `mgtightgrain` | `submissions/2026-08-11-mgtightgrain/` | 86.7% over 46,592 episodes | 781.1 over 38 — **bundled two changes, see below** |
| 2026-08-11 | `55424…` | `mgtight` + here-pass, no wheat | `submissions/2026-08-11-mgtight-here/` | 2×2 factorial: here-pass +42, wheat −31; agreed by three fields | pending |

### The wrapped field does not measure strategy strength (2026-08-13)

This is the largest measured null result in the repo and it invalidates the way
§10 of `docs/ROADMAP.md` was reading its own numbers.

Every plan in `agents/wrapped/` was recorded from a real team's episode, and that
team has a real ladder rating. So the local ranking can be checked against the
thing it is supposed to predict, without submitting anything. Over all 100 plans:

```
local win% vs the source team's ladder score   pearson -0.038   spearman -0.054   n=100
local win% vs the team's median rating         pearson -0.110   spearman -0.126
single-episode best $ vs ladder score          pearson -0.014   spearman +0.114
```

**Zero.** With n=100 this rules out any correlation above about 0.2. The 477,225
-episode round robin ranks 101 agents against each other very precisely and that
ranking carries no information about which agent is actually good.

The mechanism is visible without any statistics. Several teams appear in the
field more than once, because we mined several of their episodes:

| Team | Ladder | Plans mined | Local win% across them |
|---|---|---|---|
| THUNDER THUNDER | #364 @ 2,594 | 16 | **14% – 93%** |
| HealthStone | #234 @ 2,741 | 14 | **15% – 81%** |
| Seb (allegedly) | #801 @ 1,997 | 11 | 24% – 76% |
| カワシギ | **#1 @ 3,240** | 3 | **26% – 83%** |

Same team, same agent, same week. The median within-team spread is **52.6
points**, against a full-field spread of 81.1 — **65% of the entire field's
spread is reproduced inside one team's own episodes.** A wrapped plan's win rate
measures which episode it was recorded from, not who recorded it.

Two further facts fall out of the same check:

* **The "101-agent field" is 20 sources.** 63 of the 100 plans belong to a single
  team each, and those come from just 19 teams; two teams supply 30 of the seats.
* **The frequency filter in `tools/wrap.py` was mostly inoperative.** Only 57
  eligible lines have `count >= 2`, so 43 of the 100 seats were filled from 290
  tied single-sighting lines in dictionary order. `agents/darkhorse/` (40 lines
  picked by best single-episode money instead) put **18 of 40 above the old
  field's tenth-place threshold**, and its best, `d08`, scores 92.4% against the
  ten strongest incumbents where the best incumbent gets 79.9%.

The darkhorse result is real but it does not mean what the pre-registered
criterion in `docs/TODO.md` said it would. Selecting by single-episode money
selects for a *productive action sequence that transplants*, which is genuinely
what an open-loop replay needs. It does not select for strategy.

**What survives.** Nothing local predicts ladder strength today. The only
grounded signal left is external: the rating of the team a plan was recorded
from. `submissions/2026-08-13-topline/` was chosen where both signals happen to
agree, and exists to measure how much of a #1 team's plan survives open-loop
replay.

**What this does not say.** It does not say `term714` is strong. Its 64/101 and
36.5% are uninformative in both directions — but its ladder scores, 1363.7 and
1218.6 against a 3,240 top, are direct evidence and they stand.

### What an open-loop replay costs, in ladder points

`closer_cleo` submitted unmodified is an open-loop replay of the **shared public
meta line** wearing this exact market layer. It scored **1287.2**. The 93 teams
still on the board who play that same line score:

```
max 3,108   p75 2,848   median 2,588   p25 2,005   min 98
```

Same plan. **1,301 points below the median team that plays it, 1,820 below the
best.** That difference is everything the recording does not carry: reacting to
the shop draw, to weeds, to what the opponent is doing to prices.

Applied to `topline` (recorded from カワシギ, #1 at 3,240.2), the pre-registered
prediction for `55484175` was **1,400 – 1,950, point estimate ~1,650**, with a
stated implication that replaying recordings tops out near 1,900.

> ### ~~That prediction~~ — falsified the same day
>
> `55484175` reached **2144.1** within ninety minutes and was still climbing,
> at 21 wins in 22. Both the range and the ceiling are wrong.
>
> **The arithmetic double-counted.** `closer_cleo` scored 1287.2 while carrying
> the *shared public meta* plan -- a weak plan (47.4% locally, the most-copied
> line in the library). So
>
> ```
> 1287.2  =  a weak plan  +  the replay penalty
> ```
>
> Subtracting the whole 1,301–1,820 gap from 3,240 charged all of it to replay
> and implicitly priced plan quality at zero -- which is the quantity the
> submission exists to measure. Swapping the plan alone is worth **at least
> +857** (2144.1 − 1287.2) and had not finished.
>
> Keep the anchor, drop the conclusion: 1287.2 vs a 2,588 median for the teams
> playing that same plan is still a real measurement of *something*. It is just
> not a ceiling, because the plan and the replay penalty were never separated.

### The replay penalty, measured: 877 points

This is what `55484175` was submitted to find out, and it converged at 54
episodes (50.0% over the trailing 18, opponent strength flat).

```
カワシギ, the team whose episode we replay      3,236.5
topline, our open-loop replay of it            2,359.5
-----------------------------------------------------
open-loop replay penalty                         877
```

A recording under a market layer keeps **73%** of the rating of the adaptive
agent that produced it. The estimate this replaced was 1,301–1,820 -- **too
pessimistic by roughly a factor of two.**

Both numbers are from 2026-08-13 16:52 UTC, when the leaderboard as a whole was
flat over the preceding 3.5 hours (top 3,240.2 -> 3,236.5, tenth 3,094.4 ->
3,089.0, median 738.5 -> 739.4, 4,259 -> 4,288 teams), so the +1,145 from
`term714` to `topline` is movement and not inflation.

**What it costs the road.** A prize place needs 3,089.0 and we are at 2,359.5.
Cloning the single best recording available, with no loss at all, would reach
3,236.5 -- and 877 of that is not obtainable, because it is not in the plan.
Copying recordings cannot reach the prize zone; this measures by how much.

### The prospective test of the panel (written before the result)

Every claim about local measurement in this repo so far has been checked *after
the fact* -- correlate a local ranking against ladder scores that already exist.
That is how §10.5's null result was found, and it is also why it could not say
whether a *better* local measure would work. `55489160` is the first prospective
version: a prediction recorded before the number arrives.

**The design.** Two submissions, active at the same time, facing the same pool:

|  | incumbent `55484175` | challenger `55489160` |
|---|---|---|
| source team | カワシギ, #1 | **the same team** |
| market layer | `closer_cleo`, MIT | **the same file** |
| recorded episode | 92125421 | **92135733** |
| panel win rate | 92.4% [91.2, 93.5] | **98.5% [97.8, 98.9]** |
| head to head | — | **60.8% [57.3, 64.2]**, n=768 |
| ladder | **2359.5**, converged | *this is the prediction* |

Everything is held fixed except which episode was recorded, so the ladder is
being asked one question: **does a 6.1-point panel edge correspond to a real
ladder edge?**

**What each outcome means.** Read only after `55489160` has lost a third of its
trailing 18 (rule 7 in `SUBMISSION_POLICY.md`):

* **Clearly above 2359.5** -- the panel has predictive power with the source team
  held constant. The open item at the top of `docs/TODO.md` is half solved, and
  local optimisation becomes possible for the first time.
* **Level with it** -- the panel separates plans that the ladder does not. It
  stays useful as a filter and is worthless as an objective; do not search
  against it.
* **Clearly below** -- the panel is anti-predictive at the top, which would be
  the strongest result of the three and would mean the ten-agent panel is
  selecting for something the ladder punishes.

There is no outcome here that is not worth having, which is the point.

### A ladder score does not count until the agent loses a third of its games

A new submission enters low and climbs by beating weaker opponents. Until it has
climbed, the number on the leaderboard is a floor that is still moving.

```
losing < 1/3   still climbing. The score means "at least this much" and nothing else.
losing ~ 1/3   near its level. Start reading it.
losing ~ 1/2   converged. This is its score.
```

Measure it on a **trailing window of ~18 episodes**, never cumulatively --
cumulative lags forever, because the early wins against weaker opponents never
age out. At 54 episodes `55484175` was 22.2% cumulative and 50.0% over the last
18. Its three blocks ran 5.6% -> 11.1% -> 50.0% while mean opponent money went
$61,245 -> $82,795 -> $82,194: **opponent strength stopped rising and the loss
rate kept climbing, which is what convergence looks like.**

`55484175` read **1695.2** at 11 episodes (11–0) and **2144.1** at 22 (21–1) --
+449 points in forty minutes, same file, the only change being that it was still
ascending. The prediction above was made against the first reading and broke
against the second.

The converged counter-example is in the same table: `term714` over 130 pooled
episodes sits at exactly **50.0%**, and its 1363.7 / 1218.6 are real readings.

**Episode count is the wrong stopping rule.** `SUBMISSION_POLICY.md` rule 1 asks
for ≥40 episodes; that is necessary, not sufficient. `55484175` was at 95.5%
after 22 and would still have been climbing at 42. Episodes buy sample size,
**the loss fraction is what tells you it has found its level.** Recorded as rule
7 there.

### The same file, submitted twice, moved 145 points

`55442784` and `55458466` are the same agent. They scored **1363.7** and
**1218.6**. Nothing changed but the opponents the ladder happened to draw.

Every ladder comparison in this document smaller than ~145 points is inside that
band, including the +69 attributed to the liquidation day. Treat single-ladder-run
differences as hypotheses; `docs/VALIDATING.md` §6 has the arm sizes that settle
them locally.

### One submission, two changes, and why that was a mistake

`55418588` changed the production shape *and* added the here-pass. It landed at
781.1 against the incumbent's 838.4, and that number could not say which change
was responsible — exactly what `docs/SUBMISSION_POLICY.md` rule 3 forbids, and
the rule was written before the mistake was made.

A 2×2 factorial separated them, 512 episodes a cell:

| | no here-pass | here-pass |
|---|---|---|
| **no wheat** | 48.2% (the incumbent) | **90.6%** |
| **wheat** | 1.5% | 59.7% (what was submitted) |

The here-pass is worth **+42 points** and the wheat filler **−31**. Three
independent fields agree: direct head to head, the meta-inclusive `bench3`
(55.9% against 47.4%), and 156 replayed top-player trajectories (58.3% against
54.5%, with the incumbent at 33.3%).

**The best combination had never been submitted.** It is now.

### Submitting too often destroys the measurement

Only the **latest two** submissions stay active, and the ladder plays roughly ten
episodes an hour per active agent. Six submissions in one afternoon meant every
one of them was deactivated after 4–12 games:

| submission | episodes completed before deactivation |
|---|---|
| `55385371` | 12 |
| `55385995` | 10 |
| `55386385` | 10 |
| `55386857` | 4 |

Ten games cannot separate 700 from 900 — `55385995` read 837 at five games and
647 at ten, and neither number meant anything. It also starves
`tools/ladder.py`: the diagnosis that produced most of today's gain came from 94
replays, and no agent here collected more than twelve.

**Rule: submit at most once per half-day, and only when the local evidence is a
completed A/B.** The feedback loop here is measured in hours; the local one is
measured in minutes, and running the slow loop at the fast loop's cadence throws
the slow loop's data away.

*(A third row, `55348834 rl_models.zip`, appears on the submissions page with
status ERROR. It was not produced by this repo.)*

**The local-versus-ladder correlation is now measured, and it is weak.** Over 94
real episodes, `enhanced` wins 49% and `barnyard` 47% — the two agents that are
384/384 apart locally. `docs/ROADMAP.md §11` is the diagnosis: the field we were
ranking against could not express the winning strategy, and the engine's bugs
penalised crop plans far more than herd plans. This is the single most useful
thing measured in the project so far, and it took 94 episodes.

---

## Reproducing a run

Tournaments are deterministic given `(seed, both agents)`, so a run reproduces
exactly if the agent files have not changed. `agents/lib/manifest.json` records a
source hash per strategy; the `agents` table stores it too.

```bash
sbatch slurm/tournament.sh panel --lib agents/lib --seeds 8 --label "screen-repro"
python tools/db.py top --run latest
```

If numbers differ from the table above with the same seeds, the engine version
changed — check `pip show kaggle-environments` against 1.32.6 and re-diff
`reference/engine/kaggriculture.py`.

---

## Data integrity incidents

**2026-08-09 — 48 concurrent array tasks corrupted the database; fully recovered.**
A sharded tournament was submitted as a 48-task Slurm array. The shard code path
was written specifically so that array tasks never touch SQLite — but the
roster/manifest step ran *before* the shard branch, so all 48 tasks opened
`data/arena.sqlite` and ran `register_agents` at the same instant. SQLite on a
shared Lustre filesystem does not survive that:

```
sqlite3.DatabaseError: database disk image is malformed
Tree 2 page 2 cell 0: 2nd reference to page 57875
```

Recovery, in order:

1. `cp -a` the damaged file to `data/arena.sqlite.corrupt-20260809` before
   anything else, so the recovery could be retried.
2. `sqlite3 <corrupt> .recover | grep -v sqlite_sequence | sqlite3 <new>`.
   (`.recover` emits a `sqlite_sequence` insert that the fresh database rejects;
   `.dump` is the wrong tool here because it stops at the first bad page.)
3. `PRAGMA integrity_check` → **ok**, and every run's row count matched the
   count logged in its `runs` row exactly: 56,944 / 28,120 / 25,200 / 25,200 /
   26,928 = **162,392, nothing lost**. `ladder_episodes` intact at 94.
4. `agents` came back with 603 of its rows; re-registered from the three
   manifests, which is where that table comes from anyway.
5. Run #7's `n_episodes` had been in a damaged page; recomputed from `episodes`.

The 160 duplicate `(run_id, seed, left, right)` keys found in run #1 during
verification are **not** recovery damage — they are byte-identical rows created
by `plan_panel` when an agent appears in both the roster and the panel, and they
predate this incident.

Fixes, both in `tools/tournament.py`:

* Shard mode now resolves `con = None` and never opens the database. `--shard`
  with `--from-run` is a hard error, because that is the one roster source that
  needs a read; resolve it on the submitting host and pass `--agents`.
* Verified rather than asserted: the shard path was re-run under a monkeypatched
  `sqlite3.connect` that raises on any path containing `arena.sqlite`, and the
  live database's md5 was compared before and after.

This is the third incident in this project caused by SQLite access patterns, and
the second where a tool reported success while doing the wrong thing. The rule
that would have prevented all three: **exactly one process writes the database,
and it is never a Slurm array task.**


**2026-08-08 — duplicate runs written by a test, removed.** A test of
`tools/sync.py merge` intended to write into a scratch database wrote into
`data/arena.sqlite` instead, adding runs #3 and #4 as exact copies of #1 and #2
(85,064 → 170,128 episodes). Both were deleted and the database vacuumed; runs
#1 and #2 were never modified and all counts are back to 85,064 / 633 / 594.

Two real bugs caused it, both now fixed:

* `db.connect(path=DB_PATH)` bound its default **at import time**, so reassigning
  `DB.DB_PATH` had no effect on where writes went — while log messages happily
  reported the new path. `connect()` now resolves `DB_PATH` at call time, and
  `sync.py merge` takes an explicit `--into`.
* `cmd_merge` never closed its connection. In WAL mode that left the committed
  rows in the `-wal` file, producing a **0-byte database that had just reported a
  successful merge**. Writers now checkpoint and close via `db.close()`.

A third bug surfaced during the cleanup: `cmd_merge` passed `atoms` to
`register_agents` as the JSON string it had read, and `register_agents`
`json.dumps()` whatever it is handed — so all 594 agent rows ended up
double-encoded, and `tools/leaderboard.py` crashed on the next run. Fixed at the
source and all 594 rows repaired.

The lesson worth keeping: a path reported in a log is not evidence of the path
written to. The round-trip test in the scratchpad exists because of this, and it
is what caught all three.

## Diagnosis: why the first enhanced cut ranked 8th

Run #5 put the first version of the enhanced baseline 8th of 36 — comfortably
ahead of `barnyard` (15th) but behind all seven `homestead-crew-orchardherd-*`
variants. Comparing digests across the same tournament made the cause obvious:

| | enhanced (first cut) | field leader |
|---|---|---|
| quadrants owned | 2 | **1** |
| animals at the end | **9** | 15 |
| idle tiles | **32** | 7 |
| wool sold | 30 | 48 |

Two independent defects:

**The herd deadlocked at nine.** `feed_solvent` required
`shed_wheat >= (n+1) * FEED_DAYS_REQUIRED`, but the reserve it was checking
against is capped at `WHEAT_RESERVE_CAP = 28`. At nine animals the requirement is
30 — unreachable — so no tenth animal could ever be bought. Two constants that
had to agree, and did not.

**Two quadrants were worse than one, for this agent.** With 18 pens and 12 melon
tiles planned against 50 tiles, 32 sat idle while the hands walked further. The
leader used 18 of 25. Land does not add production; it spreads the same labour.

Both fixed, and the result reverses: 75.8% against that same leader over 384
episodes, and 13–15 animals with 7 idle tiles instead of 9 and 32.

## Known caveats attached to these numbers

- **Run #1's top tier is saturated.** Eight strategies went undefeated against
  the panel, so Bradley-Terry diverges and their relative order is arbitrary.
  That is what run #2 exists to resolve.
- **Runs #1 and #2 disagree on atom effects** — `ranchmix` goes from second-best
  to worst, `frontrun` from marginal to top. Both are honest; they measure
  different fields. The strategy space is non-transitive
  (`docs/ANALYSIS.md`).
- **Main effects in `docs/LEADERBOARD.md` are unbalanced** by construction, because
  the composition plans do not sample the axes evenly. The balanced versions are
  in `docs/ROADMAP.md §11` and they reverse some orderings.
- **The pre-database leagues used ad-hoc agent generators** (`agents/legacy/`)
  that had bugs the library engine later fixed. Treat their absolute numbers as
  indicative and their comparisons as valid only within a league.

## Can we interfere with the market? Two waves, 106,000 episodes (2026-08-13)

The question came from a specific model of the field: *if* every ladder opponent
is a recording plus a market wrapper, there must be some way to move prices
against them, because an open-loop agent cannot react. The engine says the
premise is half right. There are exactly two channels between the two farms --
the shared market inventory, and the end-of-day RNG, whose draw count depends on
each farm's empty-tile count and which therefore decides which shop unlocks and
so which market recovers. Only the first is usable on purpose.

Every arm is `agents/champ/k01.py` with market constants rewritten by
`tools/perturb.py` and played against a byte-identical copy of itself. `_TRACE`
never varies, so planting, harvesting, hiring and buying are identical in every
arm and nothing but market behaviour can move the result.

**Controls first.** `mctl` (byte-identical copy) and `mnul` (interference overlay
present, all dials empty) both returned 50.0% [45.7, 54.3] with a paired margin
of $+0 ± 429. The harness is unbiased and the overlay is inert.

### Every attempt to disrupt the market made the opponent richer

Nineteen arms dumped, hoarded or re-slotted supply. **Not one produced a negative
change in the opponent's bank.**

```
C.fr_straw   win 0.8%   us -$8,706   them +$9,608
C.fr_melon   win 1.0%   us -$8,132   them +$9,133
E.fuse_d20   win 0.0%   us -$82,229  them +$60,996
```

The reason is that we are already the disruption. The baseline lists 3,511 units
a season and closes fertilizer and milk at $1, and that sustained selling is what
holds the price down for the opponent. Anything that makes us sell less -- or
wrecks our own farm so we produce less -- *removes* pressure we were already
applying. In one traced episode the arm that hoarded wool left milk closing at
$183 against the baseline's $1.

Withdrawing as a seller is the largest gift available in this environment.

### The one dial that won is a self-play artefact

Extending the donor's clone-detection front-run from 1 turn to 3 scored **78.7%
[75.0, 82.0]** against a mirror; turning it off scored 22.9%. Money barely moved
-- Δus +$176, Δthem -$242, paired margin +$418 ± 431, which spans zero. A mirror
match finishes near a tie by construction, so a few hundred dollars of consistent
edge flips a quarter of the outcomes. The competition scores wins only, which is
exactly why `docs/VALIDATING.md` ranks on win rate and not on money.

Wave 2 crossed 7 horizons x 4 item sets x 2 slot policies and played all 56 cells
against the mirror **and** against four wrapped ladder recordings. Against the
recordings every one of the 58 agents returned **(901 wins / 992 games)** --
identical to the episode, not merely indistinguishable. `_front_run` needs
`_CLONE_CONFIDENCE >= 2`, which needs the opponent's public farm signature within
distance 1; self-play satisfies that by construction and no real recording ever
does. **None of the 78.7% transfers.**

### The interaction table, and why the main effect lies

```
mirror win rate            all9     melon     prem4      wool
h0 (off)                  21.8%     21.8%     21.8%     21.8%
h1                         4.8%     21.8%     59.9%     59.9%
h2                         4.8%     21.8%     78.8%     78.8%
h3                         4.8%     21.8%     80.2%     80.2%
h8                         4.8%     21.8%     79.0%     79.0%
```

The horizon effect exists only in one column. It is exactly zero for melon, and
*negative* for the widened item set. `prem4` and `wool` agree in every cell,
which means the mechanism only ever fires on wool and the four-product set is
decoration. The marginal main effect of h3 is 46.8% -- an average over cells
worth +58, 0 and -17 points, and a number that would have been read as a modest
win by anyone who did not print the interaction.

### Nobody on the ladder plays this dimension, and there is little room to

`tools/tracefeat.py` extracts fourteen behavioural features of the market queue
from all 371 mined lines and scores them against `wins/plays` -- real outcomes in
real ladder episodes, not anything this repo simulated. Null: best |spearman|
<= 0.28, the top-ranked feature changes with every play threshold, and
`prem_unit_share` reverses sign between subsets.

The structural measurement underneath it is the more useful one. Across 266,749
recorded turns:

```
53.61%  place no market order at all
29.87%  place exactly one
82.26%  contain no SELL order
```

Ten slots, and 83.5% of turns use none or one of them. Slot ordering has nothing
to order in most turns -- though 306 of 371 lines do fill all ten at some point,
so the capacity is used in bursts and not unknown to them.

### What this closes and what it leaves open

Closed: market interference as a route for a recording-plus-wrapper agent. The
channel exists, the baseline already sits at its aggressive end, and every
implementable move along it is self-harm.

Also closed: the fertilizer-subsidy hypothesis. Fertilizer has no sink anywhere
in the engine -- no shop and no town-centre line consumes it -- so a buyer is the
only thing that lowers its inventory, and we close it near $1 every season. The
arm that bought it cheap scored 15.1% at a $5 cap and 4.1% at $20, and made the
opponent richer. Buying lifts the price, which pays the seller.

Left open: the queue is 10 wide and 83.5% of turns use at most one slot. The
unused capacity is in *actions*, not in ordering -- HIRE and BUY_LAND are market
orders too. Nothing here tested that.

Caveat on all of it: the "field" condition is four wrapped recordings, not four
adaptive agents. The replay penalty is 877 points, so a recording is not the team
that produced it, and an adaptive opponent could react to a price move in ways no
recording can.

## Wave 3: what is the wrapper actually worth? (2026-08-13, 54,560 episodes)

Waves 1 and 2 closed market interference. Wave 3 turns the same instrument on the
agent's own structure, sweeping three thresholds that are literals in the donor
rather than named constants -- `tools/perturb.py` hoists them by regex and fails
loudly if a pattern does not match exactly once. Controls: `pctl` 49.6%
[43.4, 55.8], `pnul` 49.6%, paired margin $+34 ± 514.

### Buying land is not optional: 0.0% in both conditions

`_X_NO_LAND` suppresses the tape's BUY_LAND orders -- k01 buys two for $3,000,
and all 371 mined lines buy two or three. The arm won **zero of 5,208 mirror
episodes and zero of 20,832 field episodes**. It is the largest effect measured
in three waves.

This also fences off an earlier note. `RUNS.md` records that a second quadrant
made *our own engine* worse -- 32 of 50 tiles idle while hands walked further.
That was our engine. The ladder disagrees: across 643 real ladder episodes the
opponent's median holding is 3 quadrants with 40 idle tiles. Idle tiles are not
the cost they looked like.

### Starting liquidation at 600 instead of 680: +17 points, mirror only

```
mirror (vs an identical copy)          field (vs w39/w48/w16/w68)
          l600    l680    l720                  l600    l680    l720
t708     69.2%   46.4%   46.0%                 91.8%   91.2%   91.2%
t714     66.5%   49.6%   52.8%  <- donor       91.8%   91.4%   91.4%
t717     66.5%   49.6%   52.8%                 91.8%   91.4%   91.4%
t720     64.9%   50.4%   50.8%                 91.8%   91.4%   91.4%
```

`t714.l600` is 66.5% [60.4, 72.1] against the control's 49.6% -- clean and
significant. The same cell against the field is 91.8% [90.0, 93.4] against
91.4% [89.5, 93.0]. Intervals almost entirely overlap.

Third time in three waves that a large mirror effect is worth nothing against a
non-identical opponent. Selling earlier than your clone is front-running your
clone; a stranger is not on the same schedule.

### The only board-reading component in the agent is worth $4

`_terminal_action` reads tiles, assigns every hand a harvest/carry/drop task and
sells what it collected. It is the sole closed-loop part of the file, and it owns
six turns of seven hundred and twenty. `t720` disables it completely:

```
seed 777        t714 $83,465    t717 $83,465    t720 $83,461
step 717 farmer      NORTH           WEST            WEST
step 719 farmer    HARVEST         HARVEST         WATER
```

The actions genuinely differ; the money does not. Field win rate is 91.4% with it
and 91.8% without. Running it *longer* degrades monotonically -- 91.2% at t708,
88.0% at t696, 69.3% at t672, 31.5% at t624 -- because it harvests and carries but
never plants, waters or feeds. Disabling `_terminal_liquidation` (`l720`) costs
nothing either.

Note against a past decision: submission `55442784` was justified entirely by
moving this threshold from 717 to 714, measured at +2.9 points with disjoint
intervals against `bench3`. Here t717 and t714 return identical win rates in all
six cells and identical money on every seed tried. That does not refute the
bench3 measurement -- the field is different and the space is non-transitive --
but the effect does not reproduce.

### What this means for the route

The agent's strength is the recording. The wrapper's two terminal components are
worth nothing measurable, and the third (sell ordering) has only ever been
measured against a mirror -- wave 1's `A.sort_off` cost 37 points there while
moving nothing at all against `starter`. Nobody has run the sort dials against
the field; that is the cheapest open question left and it is one job.

If the wrapper is worth as little as this suggests, the 877-point replay penalty
is not a wrapper problem to be tuned away. It is the plan, and Road C is the only
lever.

## What actually couples the two players (2026-08-13)

Three questions, all answerable from data already on disk.

### In a mirror, weeds are the only tie-breaker

Two byte-identical agents on the same seed. Set `weedSpawnChance` to 0 and every
mirror episode ends in an **exact tie**, to the dollar, on every seed tried.
Restore it and the margins reappear.

The mechanism is in `_end_of_day`: one `random.Random((seed * 1_000_003) ^ day)`
serves both farms in player order, and `_spawn_weeds` draws only on empty tiles
(Python short-circuits `tiles[y][x] is None and rng.random() < chance`). Player 0
consumes the first N draws, player 1 the next M. Different draws, same stream.
Nothing else in the engine is asymmetric: market slots resolve index by index
against the same pre-commit inventory, and the town is shared.

Pooled over 2,048 control-vs-`k01` mirror episodes across three waves:

```
exact ties                     804 / 2,048  = 39.3%
non-tie margin, median         $717      (25th $180, 75th $1,857, 90th $7,448)
```

On the real ladder, 664 episodes, **zero exact ties**, median margin $10,392.
That is the useful contrast: a monoculture of one recording plus one wrapper
would tie 39% of the time. The ladder does not, so the field is not a
monoculture -- and it also explains why a few hundred dollars of consistent edge
flipped 28 points of mirror win rate in wave 1. The baseline margin is literally
zero.

### Where `topline` loses on the ladder: it peaks at day 15

59 ladder episodes, 46-13. Our own digest is identical in wins and losses --
open-loop replay -- so every difference is the opponent's.

```
our lead, median      d5      d10     d15      d20     d25     d29
wins                 -407   +1,490  +9,602  +8,994  +8,572 +11,284
losses                +80     +537  +7,200  +3,981    +837    -632

still ahead in losses:  d15 92%   d20 77%   d25 54%   d29 31%
```

We are ahead at day 15 in twelve of thirteen losses. The lead then decays
monotonically. In wins it grows. Day 15 is where we stop gaining, not where we
fall behind.

What the opponents who beat us do differently -- and it is not selling more of
what we sell:

```
                 us    opp (we win)   opp (we lose)
cows             10         8              8
milk sold       279       241            320
wool sold       120       138            154
strawberry      227       286            300
fertilizer    1,708       235            300
wheat         1,037       455            479
weeds left       13         5              5
```

**Ten cows produce 279 milk for us; eight cows produce 320 for the agents that
beat us.** 28 per cow against 40. We hire more (277 orders against 266), own more
animals, sell more than twice the total volume, and lose -- because 2,745 of our
3,511 units are fertilizer and wheat, one dumped at 3.5x its depth to a $1 close
and the other floored at $17.

### The shop draw is a coupling channel worth up to 20 points

Eight shop instances are drawn with replacement from eight shops, one every three
days, and each consumes fixed products every fourth step. That draw decides which
markets stay above the price floor. Measured over 4,096 episodes of an unmodified
`k01` against four mined ladder lines:

```
milk-consuming instances   n     win%          our $     their $   final milk price
0                        100    64.0%         58,964     61,066         $1
1                        392    88.8%         73,578     67,866         $1
2                      1,036    84.9%         76,804     71,487         $1
3                      1,024    92.6%         92,108     80,446         $1
4                      1,048    95.4%        105,930     94,344        $47
5                        420    98.1%        111,990     99,652       $197
```

The right-hand column is the mechanism. At three milk shops or fewer the milk
market is saturated and closes at the floor; at four the town drains enough to
keep it alive, and at five it closes near base price. Win rate spans 64% to 98%
and our bank spans $58,964 to $111,990 across a variable neither player controls.

Carrot shops run the other way (-6.4 points at three or more) because the eight
instance slots are zero-sum: a PET_CAFE is a slot that is not draining anything
we sell.

Two refinements that matter more than the headline:

**It is opponent-specific.** Against `w48` the effect is +20.0 points
(78.1% -> 98.0%, disjoint); against `w16` +10.5; against `w39` +2.0 and `w68`
+0.6, both nothing. The shop draw decides a matchup only when the two plans have
different product mixes. This is the coupling asked about, and it is not the
market inventory directly -- it is whose product mix the town happens to want.

**Earlier is better, monotonically.** Position of the first milk shop in the
unlock order: d3 96.4%, d6 90.4%, d9 89.6%, d12 83.0%, d15 79.2%, never 64.0%.
Cumulative drain explains this without needing an adaptation story.

### The opening this leaves

`obs["town"]["unlocked_shops"]` is public and fills up one entry every three
days, so by day 12 an agent has seen four of eight. Which markets will stay
liquid is therefore *knowable in-season*, and it is worth up to 20 points against
a given opponent. An adaptive agent can shift its product mix toward the draw. A
recording cannot -- it plants what it planted.

That is a concrete, measured mechanism for part of the 877-point replay penalty,
and unlike everything else in these four waves it is not a mirror artefact.

## Wave 4: the sell-ordering layer is the one part of the wrapper worth having

72 cells over `_SORT_KEY` x `_SELLS_FIRST` x `_RACE_WEIGHT` x promotion policy,
94,720 episodes, mirror and four mined ladder lines. Controls `qctl` and `qnul`
both 50.0% [43.9, 56.1], paired margin $+0 ± 503.

```
_SORT_KEY   field win%      interval        per opponent
impact        91.0%     [89.1, 92.6]    w39 93  w48 86  w16 87  w68 98   <- donor's
gross         87.5%     [85.3, 89.4]
off           86.9%     [84.7, 88.8]    <- reordering disabled
unit          81.2%     [78.6, 83.4]
```

`impact` against `off` is +4.1 points with disjoint intervals, and against the
worst key +9.8. **This is the first effect in four waves that survives a
non-identical opponent.** It is also the only dial in the file whose ranking rule
assumes the opponent is selling at all: `impact` ranks a sell by the revenue lost
to going second -- quantity times its own price impact -- rather than by revenue
at stake. Market competition is real, worth about four points, and the donor
already found the right rule for it.

Everything else in the layer is a mirror artefact or nothing. `_SELLS_FIRST`
scores 69.3% in the mirror and 91.0% in the field, identical to leaving it off.
`_RACE_WEIGHT` costs 5.7 points in the mirror and 0.4 in the field. Dropping
`_PROMOTE_IF_OPP_MONEY` -- the only rule in the whole agent that reads the
opponent's bank -- moves the field from 91.0% to 91.3%, well inside the interval.

### The wrapper, priced

```
sell ordering (_SORT_KEY='impact')      +4.1 points vs disabling
_terminal_action (board-reading)        $4 on $83,465; 91.0% with, 91.3% without
_terminal_liquidation                   0
_RACE_WEIGHT / _SELLS_FIRST / _PROMOTE  0 in the field
_RESERVE / _RAMP_* / _SHED_PRESSURE     dead code, and _RESERVE is broken
```

Four points. That is what the adaptive layer is worth against real recordings,
and it is already at its best setting. The 877-point replay penalty is not in
here.

## Wave 5: correcting the demand model does not rescue the shop-aware dial

`_remaining_drain` is the only code in the agent that reads
`town.unlocked_shops`, and it does not match this engine -- it fires the town
centre every 12 steps with a 1/2/4 multiplier stepping up on days 10 and 20,
where the engine fires it every 24 with multiplier 1. Against 200 real ladder
shop draws it overestimates by 1.3-1.8x on most products and 4.7-6.7x on melon,
whose entire estimate is the wrong term because no shop consumes melon.

It feeds `_race_factor` alone. 20 cells, 56,320 episodes, controls 50.0%/50.0%,
and the design's own pre-registered self-check passed: at `r0` the donor and
fixed cells are identical to the decimal, confirming the model is unreachable
when the weight is zero.

```
pooled over every race > 0 cell, field, 16,384 episodes each
  donor model   86.27%  [85.73, 86.79]
  fixed model   86.62%  [86.09, 87.13]     +0.35, intervals overlap

pooled over both models, field, 8,192 each
  r0 (off)      87.67%  [86.94, 88.37]     <- donor's value, and the best
  r05           87.21%
  r1            86.63%
  r2            86.24%
  r4            85.69%  [84.92, 86.43]     disjoint from r0
```

Racing is monotonically harmful under both models. Fixing the model does not
rescue it.

**A pre-registered prediction, refuted.** The design file said a truer model
reports less remaining demand, so `_race_factor` fires harder, so the corrected
version should be *worse*. It is marginally better instead, and inside noise. The
mechanism offered for wave 1's result was therefore wrong in direction; the
honest reading is that correcting the model barely changes which products get
raced, because the mechanism is worthless either way.

Production cannot respond either: PLANT names its crop in the action and the
engine drops every plant request for a crop when seeds are short, so editing
BUY_SEED redirects nothing and can destroy a turn's planting.

That closes shop-response through the market layer. The 34-point spread the shop
draw controls is reachable only on the production side, and the production side
is the tape.

## The prospective test of the panel, resolved (2026-08-14)

Written before the result, in `RUNS.md` and `docs/TODO.md`: two agents from the
same source team, the same market layer, the same packaging, differing only in
which recorded episode they replay. `k01` scored 92.4% on the fixed ten-opponent
panel and `k06` 98.5%. Three outcomes were declared in advance -- clearly above,
level, or clearly below.

```
submission          eps   W-L    cum loss  trail-18  trail-30  2nd half   score
55489160  k06        94  74-20     21.3%     27.8%     26.7%    25.5%   2612.3
55484175  k01        59  46-13     22.0%     27.8%     40.0%    40.0%   2391.6
```

**Clearly above, by 220.7 points.**

Rule 7 is satisfied in the way that matters, though not in the way it is written.
`k01` has converged: its trailing-30 loss rate is 40.0%, past the one-third line,
and its score has turned over (2413.9 -> 2418.2 -> 2421.9 -> 2391.6). `k06` has
*not* -- 26.7% trailing-30, still winning three in four, still climbing. But it
has 1.6x the episodes of the converged incumbent and sits 220.7 points above it.
The rule exists because a climbing agent's score is a floor; a floor that is
already 220 points clear of a settled comparison can only move away from it.

**Panel win rate predicts the ladder when the source team is held constant.**
That is the first local measurement in this repo with any validated relation to
real strength, and it is a pre-registered prediction rather than a correlation
found afterwards -- `docs/ROADMAP.md` §10.5 is what happens when you look for the
correlation first.

**It is n=2.** One comparison, in the predicted direction, with the confound that
killed §10.5 (different source teams) deliberately removed. It does not license
ranking across teams, and it does not license using the panel as a search
objective without a second confirmation.

### Two numbers that change with it

**The replay penalty is 630.8 points, not 877.** `カワシギ` is still #1 at 3235.7
and our copy of their recording now scores 2604.9 on the leaderboard: **80.5%
retained**, against 73% when measured with `k01`. Picking a better episode from
the same team recovered about 246 points of the penalty, which is most of what
plan selection can be worth.

**"Copying recordings cannot reach the prize zone" was too strong.** The top-ten
threshold is 3061.4 and a perfect copy of the #1 team would be 3235.7 -- the
ceiling is inside the prize zone. The barrier is retention: reaching tenth from a
#1 recording needs 94.6% where we get 80.5%. Whether a recording can ever retain
94.6% of an adaptive agent is a different question, and the honest answer is
probably not, but the arithmetic no longer rules it out on ceiling alone.

### Where the team stands

```
4,356 teams.   RL is all you need: #348, 2604.9, top 8.0%

  rank    1  3235.7        1 -> 10    19.37 points per rank
  rank   10  3061.4       10 -> 20     3.95
  rank   50  2916.2       50 -> 100    1.20
  rank  100  2856.3      100 -> 200    1.22
  rank  348  2604.9  <-  200 -> 348    0.88
  rank 2000   817.8      348 -> 500    1.16
```

At our position one point is roughly one rank -- #344 to #352 spans 4.4 points
across nine teams. +130 reaches #200 and +251 reaches #100. The top ten is a
different regime: 174 points across nine ranks.

## The TorchRL unification A/B (2026-08-18, one H100, 2 × 44.2M lane-steps)

The `rl-baseline` and `tensorize` branches merged to main today, with TorchRL
as the training framework gluing them: `EpisodeT` wrapped as a batched
`EnvBase` (`rl/tensor_env/trl_env.py`), the masked two-head policy as a custom
distribution (bit-exact against the hand-written math, `test_trl.py` gate i),
and the update loop as swappable loss modules (`rl/train.py --algo ppo|a2c`).
Per the repo rule -- an engine-adjacent change gets an A/B, not an argument --
both trainers ran the same budget on the same GPU before the hand-written
loops were declared superseded.

Setup: B=1024 episodes per iteration, 60 iterations, seed 0, learner vs the
tensor starter, identical coefficients (GAE 0.999/0.95, clip 0.2, entropy
0.003, Adam 1e-4). `slurm/rl_ab.sh`, job 20053670 (arm A) / 20057312 (arm B).

```
arm  trainer                 steps        win@36  final win  final money  mean sps
A    train_t.py (hand)       44,175,360    1.000     1.000       14,859     49,177
B    rl/train.py (torchrl)   44,175,360    1.000     1.000       24,966     46,440
```

Arm B's curve: 0.014 (it 12) -> 0.47 (it 18) -> 0.92 (it 30) -> 1.000 (it 36
on), against arm A's 1.000 from it 30. Same milestone, one-arm-later; the
TorchRL arm then keeps improving the margin (24,966 vs 14,859 final money)
where the hand arm plateaus at ~14k. Framework tax on throughput: -5.6%.

Caveats, so this table is not over-read: money-vs-starter is the shaped
training objective, not a ladder statement; the two arms share coefficients
but not sampling RNG paths, so curves are not lane-comparable -- equality of
the mathematics is established by the bit-exact gates in
`rl/tensor_env/test_trl.py`, and this A/B only had to show the framework does
not *lose* anything at equal budget. It gained instead.

Two failures on the way, both now in the code as comments: the first arm-B
attempt OOMed inside torchrl's GAE (`torch.stack` of obs + next.obs wanted
26.7 GiB on top of the collector's two 29 GiB copies; fixed with
`shifted=True` + buffer-reuse collection), and the first eval-chain attempt
died printing checkpoint metadata (`global_step` is the rl-baseline key,
torchrl checkpoints carry `iter`). The dependency-chained eval job followed a
failed parent and had to be cancelled -- `afterok` on an OOM-bound job wastes
a queue slot, nothing more.

The acceptance chain then ran end to end on the arm-B checkpoint: export as
`pitchfork` (numpy agent + weights.npz) -> ten-opponent roster, 48 seeds a
side, 96 episodes per pair (`slurm/rl_eval.sh` with RUN/CKPT/NAME env vars,
job 20059228, 2.5 minutes at -j 32):

```
opponent            games    win                 margin
random                96   100.0% [96.2,100.0]  +20,615   BEATEN
starter               96   100.0% [96.2,100.0]  +16,562   BEATEN
ghost-89825016-0      96    44.8% [35.2, 54.7]   -3,158   unresolved
ghost-89830307-0      96    40.6% [31.3, 50.6]   -3,492   unresolved
barnyard/enhanced/ledger_lena/spar x2/w49        0.0%     LOST
```

2/10 beaten. This checkpoint is the A/B artifact -- plain PPO against the
starter, no BC, no curriculum, no league -- so what this table certifies is
the pipeline, not the agent: a torchrl checkpoint now flows unmodified
through export -> roster -> scorecard (`rl/eval_summary.py --run trl-ab`).
The closed line needed BC + curriculum + league to reach its 4/10; those are
the hooks to wire into `rl/train.py` next (the league's opponents are already
representable on-device via `trl_env.FrozenPolicyOpponent`).

## foothold: the smoothing stack works; self-play still cannot leave its own basin (2026-08-19)

First combined run of the smoothed-gradient machinery (`rl/configs/foothold.yaml`):
residual policy over the pitchfork prior, curriculum starter -> pitchfork with
a handicap ladder (800 -> 400 -> 200 -> 0), league self-play snapshots, bounded
terminal margin 1.5 + win bonus 1.5, 5% opponent noise. Jobs 20078618/20078619
(chained via --resume), eval 20078620. 240 iterations, 176.7M lane-steps,
mean 35.5k sps (frozen-net opponents cost ~25% vs starter-only).

Mechanically, everything did its job: the curriculum climbed the entire ladder
inside the first 23 minutes, the resume chain restored pool state across jobs,
and by the end the policy beats its own prior 96% of the time at zero handicap
(money 26k vs 0.2k in those batches). Against its own league, this agent is a
monster.

The roster says none of it transferred:

```
opponent            foothold          pitchfork (prior)
ghost-89825016-0    42.7% [33.3,52.7]  44.8% [35.2,54.7]   level
ghost-89830307-0    38.5% [29.4,48.5]  40.6% [31.3,50.6]   level
barnyard margin     -48,013            -49,006             unchanged
w49 margin          -136,709           -136,480            unchanged
beaten              2/10               2/10
```

Reading: post-mortem §13-vi reproduced at higher fidelity. Crushing your prior
and your snapshots deepens the basin; it does not leave it. The smoothing
tools (margin, handicap) ran correctly but had nothing strong to grade
against -- the strongest tensor-representable training opponent IS the prior.
The binding constraint is now unambiguous and it is not the optimizer:
it is training-opponent strength. TODO #1 (tensorise barnyard/ghost) and
TODO #0 (per-unit action heads, Kilo's structural idea) are the two levers;
the margin/handicap machinery is built and gated, waiting for exactly them.

## siege: a real wall as a training opponent -- the gradient arrives, the action space cannot spend it (2026-08-19)

First run with tensorised barnyard as a curriculum stage (`rl/configs/siege.yaml`:
starter -> pitchfork -> barnyard, handicap ladder, margin tanh at scale 50k,
league, residual over pitchfork). Jobs 20083634/20083635, eval 20083636.
240 iterations, 176.7M lane-steps; barnyard batches run at ~21-23k sps
(the serial task-assignment loop costs ~2x vs starter batches), mean 34k.

The curriculum climbed both early stages inside link 1 (starter, then the
full pitchfork handicap ladder 800->0) and spent ~110 iterations on barnyard
at handicap 800 without ever passing a gate: batch win 0.000 throughout,
learner money on barnyard batches 10.3k -> 11.6k (it ~105) -> back to
~9-10.5k, against barnyard's steady ~55k. The margin signal was present and
graded every one of those episodes; the policy could not convert it.

```
opponent            siege             foothold          pitchfork (prior)
barnyard margin     -48,444           -48,013           -49,006     unchanged
ghost-89825016-0    43.8% [34.3,53.7] 42.7%             44.8%       level
ghost-89830307-0    50.0% [40.2,59.8] 38.5%             40.6%       drifted up, CIs overlap
beaten              2/10              2/10              2/10
```

Reading: this is the cleanest evidence yet for the post-mortem's exit-② claim.
foothold showed self-play lacks the signal; siege supplied the signal --
a full-strength barnyard, margin-graded, 50% of batches for ~45M steps --
and the macro action space still could not shorten the loss by a dollar.
To out-earn barnyard you need its labour engine (a dozen hands cycling
harvest/feed/care at scale), and the macro space's hands run a fixed
priority cascade the policy cannot steer. The per-unit multi-head action
space (rl/TODO.md #0) is now the live hypothesis, with this run as its
baseline: the A/B question is precisely "does -48k move when the policy
can allocate labour".

## breach: labour control does not breach the wall either -- and the probes watched it drift (2026-08-19)

siege + --multi-head (`rl/configs/breach.yaml`): per-hand task heads,
AUTO-biased so iteration 0 plays exactly siege's scheduler. Jobs
20086618/20086619, evals 20086620 (best.pt) and 20093298 (latest.pt).
The early stopper ended the run at iteration 160 of 240 -- six stage-3
probes without improvement -- its first production firing, ~35 GPU-minutes
saved, chain and eval unharmed.

The deterministic probes tell the whole story vs barnyard (fixed seeds,
argmax, no handicap): -34,640 on arriving at stage 3, then -47.5k, -45.9k,
-46.5k, -48.5k, -42.3k, -67.9k -> stop. While the policy crushed the rest
of the pool (batch win ~1.0, money 20-23k vs snapshots/pitchfork), its
barnyard margin DRIFTED AWAY. The reference-engine eval agrees with the
last probe almost exactly (-67,270 vs -67,915 -- the probe machinery is
well calibrated): ghosts 39.6%/36.5%, still 2/10.

```
barnyard margin   pitchfork era  foothold  siege    breach(latest)
                  -49,006        -48,013   -48,444  -67,270
```

Two mechanism findings along the way: best.pt's probe ratchet compared
scores across frontiers (a 0.97-win stage-2 probe outranks every 0-win
stage-3 probe; best.pt froze at ~iter 80) -- fixed to final-stage probes
only; and probe-vs-eval agreement validates fixed-field probes as a cheap
stand-in for reference-engine evals during training.

Reading: exit ② alone is not the key. The gradient reaches the policy
(siege), the policy can allocate labour (breach), and it still walks
downhill toward the pool mix instead of the wall. The two live hypotheses:
(a) objective -- nothing prices the ANIMAL ENGINE that makes barnyard's
55k; Kilo's future-credit potential (--potential future, already ported
and gated) does exactly that, one flag away from an A/B; (b) pool
dynamics -- the beatable half of the pool owns the reward hill; a
barnyard-weighted or barnyard-only phase would isolate it. Both are
single-variable follow-ups on breach's config.

## The 2x2 on breach's config: solvency and sell timing learned; the wall is made of labour (2026-08-20)

The breach verdict pre-registered two hypotheses -- (a) the objective is
blind to the animal engine, (b) the beatable half of the pool owns the
reward hill -- and both are single flags on breach's config, so they ran
as a factorial with breach as (0,0): `foresight` (+ `--potential future`),
`grudge` (`opponents: barnyard` alone, league off), `vendetta` (both).
Jobs 20163860-71: three ~50-min links per arm, dependent roster eval on
best.pt. foresight completed 240 iterations (176.7M lane-steps); grudge
and vendetta early-stopped at 179 (stagnated, 132.5M).

Probe shape, identical in all three arms: pinned at -66..-68k (the breach
endpoint band) for the first ~70 barnyard iterations, then a ~20k jump
once each arm had ~50M lane-steps of margin-graded barnyard batches, a
peak near -41..-43k, and then degradation -- vendetta's last probe fell
all the way back to -68.5k. Peak-then-collapse is the regime's normal
behaviour, not an accident of breach; the final-stage-only best.pt
ratchet is why the artifacts keep the peak (vendetta eval -40,990 vs its
best probe -40,800 -- calibrated again). Win stayed 0.000 against
barnyard everywhere: no arm took a single game off the wall.

Roster (96 games per pair, best.pt), breach alongside:

| arm | barnyard | ghost-25016 | ghost-30307 | spar-grazier | beaten |
|---|---|---|---|---|---|
| breach (0,0) | -67,270 | 39.6% | 36.5% | -- | 2/10 |
| foresight (a) | **-36,607** | 0.0% (-21.7k) | 0.0% (-21.2k) | -67.8k | 2/10 |
| grudge (b) | -42,801 | 39.6% (-4.3k) | **45.8% (-2.6k)** | **-46.7k** | 2/10 |
| vendetta (ab) | -40,990 | 12.5% | 10.4% | -68.9k | 2/10 |

Three findings:

1. **What the recovered ~25-30k is made of.** Seed-1000 traces of the
   peak policies against barnyard: both potentials fixed the bankruptcy
   (cash buffer held, hands paid and retained, weeds ~zero -- breach's
   farm lost its whole crew to unpaid wages by day 9) and both learned
   first-harvest timing (sell day 11 at ME 136-152 for +10-13k; breach
   held until the price hit $1). Solvency plus sell timing, nothing else.
2. **The future potential buys wall margin with generality.** foresight
   is 6k better on barnyard and CATASTROPHIC everywhere else: ghosts
   40->0%, spar margins worse than breach. grudge (networth) kept the
   ghosts at 40-46% -- ghost-30307 at 45.8% is the multi-head line's best
   recording result -- and improved spar. The narrow specialist earns
   ~12k absolute; that loses to any opponent that simply farms well.
3. **Neither hypothesis was THE constraint.** All four factorial cells
   stall at 0 wins. The traces say why identically: NEITHER PEAK POLICY
   EVER BUYS AN ANIMAL. foresight goes dormant on day 22 with 100 melons
   rotting in the shed; grudge tiles the farm with 25 EMPTY pastures.
   The mechanical cause was measured while these arms ran: barnyard's
   hands do 83% of its feeding (181 hand-FEEDs/episode plus the wheat
   logistics), an animal escapes at two unfed days, and the hand
   vocabulary had no FEED task -- the 55k engine was unreachable in the
   action space no matter what the objective priced or the pool sampled.

The FEED hand task is now built and gated (M1-M5 incl. a behavioural
gate: hands alone sustain a herd, device == CPU bit-exact; BARN/B3B/TRL
suites green), alongside two tools from the literature review for the
rounds after: `--pfsp` (win-rate-weighted pool sampling, AlphaStar
f_hard) and `--kickstart barnyard` (annealed teacher CE on the learner's
own states, Schmitt et al. / the Lux-S1 recipe; gates K1-K3). Next:
`herdsman` = vendetta + FEED, the single-variable action-space test, and
`drover` = herdsman + kickstart on top.

## parrot: pure BC of the current-balance top ladder collapses on deployment (2026-08-20)

The cold-start experiment the recordings invited: 55 post-rebalance
episodes (both seats, ~3.1k players, 100-146k games) -> 74,776
(obs, head-label) pairs by inverse decode (state-level fidelity: farmer
94.3%, hand work 85.1%, market 55.9% -- the metered-sell gap, TODO #8)
-> 12 epochs of class-weighted CE on MultiActorNet (val acc 0.61 / 0.90
/ 0.58, market argmax-NOOP held at 0.60 by the weights). Jobs 20172754
(train, CPU) / 20172755 (roster).

Roster: **1/10** -- loses even to starter (-564). The trace says why in
one line: it builds 4-6 pastures on day 0-1 and then freezes, money
pinned at $3,000 to day 27. Per-step accuracy is dominated by mid-game
states; the ~110 opening sequences that decide everything drown, argmax
locks onto the modal action, and one step off-distribution has no
recovery -- the same compounding drift that killed the old line's
barnyard clone at 79% per-step fidelity. Pure BC without on-policy
correction or search stays a dead artifact at this scale, exactly as
both the Kaggle-winners survey and our own §11 history said it would.

What survives: the dataset and its fidelity ledger (the market head's
55.9% is measured motivation for SELL_HALF), the sell-pattern
measurements, and the contrast experiment -- drover's kickstart puts
teacher labels on the LEARNER's own states, which is immune to this
exact failure by construction. mynah (BC-init + RL fine-tune) stays
staged but unlaunched: a frozen-pasture prior is a worse basin than
pitchfork.

## The anatomy of a 231k season (2026-08-20, 40 top-ladder seats, current balance)

Sell-revenue decomposition of the kept replays (price-at-sale, 20
episodes x both seats -- everyone here is a ~3.1k player):

| product | share | units |
|---|---|---|
| FERTILIZER | **29.7%** | 63,294 |
| WHEAT | 21.3% | 43,922 |
| STRAWBERRY | 16.6% | 10,815 |
| MILK | 13.4% | 10,398 |
| WOOL | 9.9% | 6,712 |
| MELON | **7.0%** | 3,996 |
| TOMATO+CARROT+EGG | 2.2% | -- |

The top of the ladder's #1 income line is SELLING FERTILIZER -- the
animal engine's real cash product, collected at herd scale -- with a
wheat-crop cash flow second and melons a 7% afterthought. Trajectory:
~4 animals by day 2 (animals FIRST, not after a melon harvest), 9 by
day 8, plateau 14.6 with ~12 hands, land 1->2->3 by day ~10, ~60 crop
tiles including ongoing strawberries. Mean sell revenue $231,656/seat.

Every arm this line has trained is anchored to the melon monoculture
the pitchfork prior discovered against the starter -- the top meta's
smallest revenue line. This table is the target program: fertilizer
and wheat throughput, early animals, strawberries, metered sells
(SELL_HALF just landed for exactly this).

## herdsman: expressiveness is ruled out -- FEED alone does not summon the herd (2026-08-20)

vendetta + the FEED hand task, single variable (rl/configs/herdsman.yaml,
jobs 20169415-18, eval 20169419). Ran the full 240 iterations, 176.7M
lane-steps; the probe ratchet walked -68k -> -38.8k (it 79, ahead of
vendetta's whole run at the matched checkpoint) -> -33.8k peak.

Roster (best.pt): barnyard **-33,965** -- the line's best wall margin
(vendetta -40,990, breach -67,270) -- with broad margin gains
(enhanced/main -59k -> -45k, ghosts -18k -> -12k) and still **2/10**,
win 0.000 on the wall.

The mechanism question is answered by the trace: **zero animals in
176.7M steps**. The whole gain is melon-economy polish (first wave sold
day 11 at 16.1k, second wave still rots). FEED made the animal engine
REACHABLE; nothing made it REACHED -- the BUY -> BUILD -> PLACE -> FEED
chain never assembles under on-policy exploration, whatever the
potential pays for it once assembled. After siege (signal), breach
(labour steering) and herdsman (task vocabulary), the wall's remaining
suspects are exploration and the objective's blindness to the
fertilizer stream -- which is what drover (teacher CE on own states,
running) and granger (kickstart + measured build-curve credit + no
melon anchor + an opponent-noise ladder, launched from the rebalance
worktree) are for.

## drover at 170 iterations: the kickstart trades the wall for the field (2026-08-20)

herdsman + --kickstart barnyard (rl/configs/drover.yaml, jobs
20169420-24, eval 20169425; the 5-link chain ran out at 170/240 -- 9.6k
sps under the double barnyard compute -- so an extension chain
20181559-61 continues it; this is the interim verdict).

The teacher CE annealed to zero by ~110M steps, batch money then climbed
to 18.5k -- the highest any wall arm has shown. The roster is the exact
MIRROR of herdsman's trade:

| | herdsman (FEED alone) | drover (+kickstart) |
|---|---|---|
| barnyard | **-33,965** | -40,824 |
| ghost-25016 | 0.0% (-12.2k) | **24.0% (-17.9k)** |
| ghost-30307 | 1.0% (-12.0k) | **38.5% [29,49] (-12.9k)** |
| spar grazier | -65,738 | **-45,079** |
| spar berrybaron | -80,832 | **-63,420** |
| beaten | 2/10 | 2/10 |

herdsman's pure-RL exploration polished one narrow melon line to a
better wall margin and total mode collapse everywhere else; the teacher
CE kept drover honest across the field -- ITS ARGMAX does not collapse
against the ghosts (the sampled-inference A/B on herdsman showed the
same 28-37% ghost strength hiding inside herdsman's weights: sampling
recovered it at the cost of ~10k wall margin; a T-sweep found no single
temperature that keeps both). ghost-30307 at 38.5% with the CI touching
48.5% is one nudge from this line's first recording win.

Alongside: granger (worktree stack: no melon anchor, kickstart,
build-curve credit, opponent-noise ladder now actually reaching
override opponents) posted the line's FIRST NONZERO WINS against
barnyard -- win 0.028 by the end of its noise-0.40 link, a live win
gradient at last. The ladder steps down 0.25 -> 0.10 -> 0 over its
remaining links.

### drover addendum: the stopper had already ruled, and sampling touches even (2026-08-20)

The 170-iteration state IS final -- the fifth link's early stopper fired
(stagnated: six flat probes at ~-50k) and wrote the chain-safe marker;
the extension links exited cleanly by design. And the sampled-inference
variant of the same weights closes the day's arc: **ghosts 40.6%
(margin -1,322, CI to +864) and 39.6% (-1,848, CI to +151)** -- both
recording matchups statistically indistinguishable from even, the
closest this line has come to its first recording win. Spar stays 0%
sampled. rebalance-1327 merged to main (d388291) now both chains are
concluded; granger continues from the worktree it was launched on.

### The ghost matchup is bimodal, not marginal (2026-08-20, 192 games x2)

Per-seed decomposition of drover-samp vs both ghosts (the "even-touching"
matchups): only 12/192 games land within +-3k. The shape is ~50 blowout
wins (+8k) against ~50 blowout losses (-8k): OUR income is tight (p10-p90
15.9k-24.9k) while the GHOST's is wide (12.9k-26.3k) -- we beat broken
tapes and lose to intact ones. No seat effect. The +1k the liquidation
mask recovered moved margins, not outcomes (41% before and after),
because mid-band losses sit at -4.4k median. Flipping the matchup needs
median income ~19.4k -> ~26k -- absolute economy, the animal/fertilizer
gap, not endgame crumbs. That is granger's lane (its noisy-wall batch
money passed 27.4k while this was measured).

## The animal engine turns over (2026-08-20, granger mid-run)

Seed-1000 trace of granger's link-4 checkpoint (zero-noise batches,
money 34.7k and climbing): wheat bought day 0, TWO COWS placed by day 5,
hands feeding on the wheat loop, MILK accumulating (12 -> 30 by day 15),
FERTILIZER stocking (22 units by day 28), liquidation-day sell to a
24,280 finish. Every link of BUY -> BUILD -> PLACE -> FEED -> PRODUCE ->
SELL is alive for the first time in this line's history -- the chain
that 176.7M steps of pure exploration (herdsman) never assembled, put
together by teacher labels + the measured build-curve credit + no melon
anchor. What remains is SCALE (2 cows vs barnyard's 21) and the crop
engine it cannibalised (4-7 melons; capital went to pastures) -- and
the checkpoint tree (steward/reveille/shepherd, forked from this trunk
with the hoarding-subsidy and gamma-annuity fixes) is already searching
the continuations.

## The recordings fall: steward-sampled takes both ghosts at 84-90% (2026-08-20 night)

First generation of the checkpoint tree, first verdicts. steward (the
granger trunk + the two reward-hacking fixes; chain 20189919-21, KILLED
EARLY at 150 iterations by the argmax-probe stopper -- this family's
strength lives in the sampled distribution and the argmax probe is a
lagging indicator, so the stopper and the plain roster BOTH mis-read it:
argmax roster 1/10, loses to starter). The sampled export of the same
checkpoint:

| opponent | win | margin |
|---|---|---|
| ghost-89825016 | **84.4% BEATEN** | +16,336 |
| ghost-89830307 | **89.6% BEATEN** | +18,131 |
| barnyard | 12.5% | **-7,814** |
| main | 0% | -23,465 |
| lena / w49 | 0% | -107,549 / -105,642 |

**4/10 beaten including both recordings** -- the acceptance line's
recording requirement is met; one more opponent (main at -23k or
barnyard itself at -7.8k) reaches >=5/10. This morning these ghosts
were coin flips and the wall was -34k. Alongside: granger's plain
ladder finished at ZERO-noise batch win 0.208 (0.010 -> 0.208 across
L4-L5), reveille (fixes+backplay) ended its L2 at 0.320 blended, and
the k-line stretch test measured the mountain above: k01/k06 out-earn
our best 20:1 (herdsman's argmax earns literally $0 under their market
pressure -- the starkest overfitting exhibit yet; drover-samp holds
6.5k). Discipline for this family from here: dual-mode rosters always,
stoppers off or batch-win-keyed, sampled exports as the deliverable.

### granger's own verdict: the wall at arm's length (2026-08-20 night)

The plain noise-ladder chain completed (L4-L5 at zero noise, batch win
0.010 -> 0.208), and its sampled roster is the line's new high-water
mark: **ghosts 92.7% / 92.7% (+20k), barnyard 27.1% at margin -3,285**,
lena/w49 margins up 55k from the morning (-94/-95k), 4/10 with both
recordings. The argmax roster of the same weights is 1/10 -- the
dual-mode discipline is now mandatory for this family. The trunk's
artifacts are preserved to the main tree and the rebalance worktree is
released; the second generation (steward revival at 300 iters with the
stopper off, reveille and shepherd finals) is on the cards to close the
last -3.3k.

### reveille's verdict and the third generation (2026-08-20 late night)

reveille (fixes + backplay bank) finished all 240: the bank taught even
the ARGMAX mode to fight the wall (barnyard 25.0% at -6,246 argmax --
every earlier argmax was 0%), and its sampled roster opened a fifth
front: **main 15.6% (-9,908, from 0%/-24.6k)**, ghosts 82.3%/82.3%,
barnyard 28.1% (-3,961). Still 4/10. Gen-3 forks from its endpoint:
yeoman = mixed pool (barnyard + the w49 tape via tape_t, pfsp 2.0,
league snapshots), the re-generalization + k-pressure arm.

## draught interim: capacity was binding -- the wide net eats the ladder (2026-08-21 early)

The 4x-wide probe (1024/512 trunk + 512 critic, ~12M params, identical
granger recipe, jobs 20197340-45) against granger's own rung finals:

| noise rung | granger final win | draught final win |
|---|---|---|
| 0.40 | 0.028 | ~0.47 EMA mid-rung |
| 0.25 | 0.396 | **0.918** |
| 0.10 | 0.485 | **0.736** (money 40.6k > wall 36.1k) |

Bigger-is-more-sample-efficient (Neumann & Gros) reproduced exactly: at
matched rungs and fewer steps the wide net dominates every reading. The
decisive zero-noise links are queued behind other users' GPU jobs. The
research verdict (TODO #9) stands confirmed at rungs 1-3: our 3M MLP --
93% of whose weights are the input projection -- was a binding
constraint all along. steward's line is pruned (revival to 300 iters
plateaued at win 0.13; its final sampled roster stays 4/10 with ghosts
at 90.6/96.9%); reveille's lineage continues through yeoman (mixed
pool, L2 final 0.249 blended).

### yeoman (gen-3, mixed pool with the w49 tape): the tape teaches the argmax (2026-08-21)

480 iterations from reveille's endpoint with barnyard + tape:w49 +
league snapshots under pfsp 2.0. The headline: **its ARGMAX beats both
ghosts (93.8% / 86.5%)** -- training against a recorded line fixed the
mode collapse against recordings without inference-time sampling; the
sampled roster pushes them to 99.0% / 96.9%, the line's best. The cost:
the wall slipped (sampled barnyard 11.5% at -36k) as PFSP moved mass to
the beatable tape and snapshots. 4/10 either mode. Lesson for gen-4
pool design: keep the wall's mass floored (f_var-style or a fixed
anchor share) when adding tapes.

## draught: capacity confirmed, and the wall shows a positive margin (2026-08-21 morning)

The 4x-wide probe finished all 280 iterations (12M params, granger
recipe, jobs 20197340-45). Rung-by-rung it dominated the 3M control at
every noise level (0.918 vs 0.396 at 0.25; 0.736 vs 0.485 at 0.10) and
at ZERO noise ended at batch win 0.449 vs the full-strength wall --
granger's control finished 0.208. Capacity was a binding constraint;
TODO #9's roadmap (bigger critic, LayerNorm prerequisites, CNN trunk as
the structural line) is now evidence-backed, not speculative.

The roster: **draught-sampled vs barnyard 55.2% [45.3, 64.8], margin
+504 -- the line's first positive margin against the wall.** Ghosts
75.0% / 82.3%. The eval marks barnyard "unresolved" (CI spans 50%), so
a 384-game resolution run (job 20213873) decides whether the fifth
roster slot -- and with it the acceptance line -- has fallen. Its argmax
mode stays broken (0% wall, 34-41% ghosts): the sampled export IS this
family's deliverable.

## THE ACCEPTANCE LINE FALLS: draught-samp resolves barnyard at 56.8% (2026-08-21 morning)

The 384-game resolution run (job 20213873): **218W-166L, 56.8%
[51.8, 61.6], interval entirely above 50% -- the eval's own verdict:
"A is better."** With random, starter and both ghosts already beaten,
the roster stands at **5/10 including two recordings**: the acceptance
bar this line has chased since its first eval is met. Mirror match is
seat-fair (margin +0 +-1.7k). Full evidence pack with the honest ladder
estimate (~800-950 if submitted; 2000 needs the lena/w49 mountain) and
the user's decision options: docs/ACCEPTANCE-2026-08-21.md. Nothing has
been submitted -- that call is the user's, per standing instruction.

The arc, for the record: 26 hours ago this line had never taken a game
off barnyard (-67,270) and its best roster was 2/10. The pieces, in
landing order: FEED (the vocabulary), the 2x2 (solvency + sell timing),
the anatomy (the target economy), kickstart (drift-immune imitation),
the noise ladder (the first win gradient), the reward-hacking fixes
(the hoarding subsidy), sampled inference (the mode-collapse unlock),
the checkpoint tree (parallel search), and capacity (the 4x net that
carried it over). Every one measured, gated, and archived.

## wrangler: the tape ladder opens (2026-08-21 pre-dawn, jobs 20218380-83)

carter's audit found its curriculum gate unreachable: `advance-at 0.85`
vs barnyard when this line's best-ever EMA is ~0.50 means carter spends
all 480 iterations on stage 0 -- in practice it is a league/pfsp A/B of
draught (50% barnyard / 50% self-snapshots), and the w49 tape it was
named for never enters the mix. Kept running as that A/B; the real
mixed-pool arm is **wrangler**, launched from the k6tape worktree
(91e36bb, deposit-PLACE fix): draught trunk (~350 iters) + granger
recipe, opponents `barnyard -> tape:w49 (84k) -> tape:k06 (100k)` with
**advance-at 0.45** -- a gate the trunk's carried-over EMA (~0.47)
steps through immediately, putting the mix at 50% w49 tape / 50%
barnyard from the first links (the yeoman floor arrives free as the
pool's "earlier" mass). This is the user's requested mixture -- higher
tiers blended in by ratio -- rather than a wall we never summit.
Single variable vs draught-ext: the opponent mixture. Smoke on CPU
verified 3-anchor pool construction and trunk resume under the k6tape
tree; the k06 tape itself is gate-proven dollar-exact (100,032).
Watch: batch win vs w49 tape will read ~0 at first (an 84k open-loop
economy) -- the signal to track is MONEY under tape pressure, not win.

## Why the 35 tiles stay empty: the planting chain is reachable, not reinforced (2026-08-21)

Action census of cropper-peek (sampled export, 3 reference-engine
episodes vs barnyard, 2,157 farmer turns): BUY_SEED 12, PLANT 5,
HARVEST 20 -- the chain works end to end (wheat is ongoing; 5 plants
yielded 20 harvests), it is just never scaled: ~1.7 plants a game
against the anatomy's ~60. Where the capacity actually goes: FEED 635
+ PICKUP 169 + 1,146 movement turns (53% of the farmer's life is
walking the dairy loop), and the market head -- one action a turn --
spends 18% of them on DEAD HIRE (397 orders with hands already at 12:
silent no-ops, zero cost, zero gradient, so the habit never prunes,
yet each one displaces a possible BUY_SEED). Verdict: not a mask bug,
not an exploration hole -- a credit/scale problem. The marginal crop
has tiny ROI while the farmer is saturated and AUTO hands won't orbit
1-2 plants; there is no smooth gradient from 1.7 to 30 crops.
Side-notes: seed 2000 produced this line's first 70k game (70,762 vs
61,317); seed 3000 lost 42.6k vs 64k -- variance is huge. gen-7
candidates that follow: mask HIRE at the hand cap (kill the dead 18%),
and whatever cropper's 30/crop curve verdict says about the credit
side. (Probe: $CLAUDE_JOB_DIR/tmp/probe_plant.py pattern, worth
promoting to tools/ if reused.)

## The w49 anatomy: planting is hand labour, and our hands cannot plant (2026-08-21)

Census of the w49 tape itself (2 reference episodes vs barnyard,
163k/98k finals): revenue is six lines -- STRAWBERRY 30.4%, MILK 22.3%,
WOOL 20.8%, MELON 11.4%, WHEAT 7.7%, FERTILIZER 7.3% -- on ~177 seeds
a game (we plant ~1.7). The structural fact: **hands do the crops**
(hand ops: WATER 1,744, HARVEST 680, PLANT 352, FERTILIZE 168; the
farmer planted ZERO times), while the farmer specialises in animals
(CARE 150, COLLECT_FERT 146, FEED 134) and walks only 32% of turns to
our 53%. Meanwhile our HAND_TASKS vocabulary is AUTO/IDLE/HARVEST/
WATER/CARE/COLLECT_FERTILIZER/DIG/FEED -- **no PLANT**: the planting
chain we measured this morning is farmer-only by construction, which
is why no credit scheme can scale it -- the farmer has no spare turns.
This is FEED all over again (83% of barnyard's feeding was hand
labour; adding the task moved the wall -48k -> -36k), except bigger:
crops are ~50% of w49's revenue. gen-7 headline: the PLANT hand task
(one new index; crop choice stays in the market head via BUY_SEED --
plant the most-held seed; empty-tile claims serialised like FEED's
wheat reservations). Also noted: w49 spams HIRE too (520 orders, cap
12) -- dead-HIRE masking (TODO #11) loses nothing against the meta.

## sower: the PLANT arm launches on a widened head (2026-08-21, jobs 20220387-90)

The handplant branch (worktree Kaggriculture-gen7, commit ba99608)
gives HAND_TASKS its ninth word: PLANT -- task-only like FEED, empty
tiles as targets, crop = most-held viable seed (deadline-aware; the
market head owns the mix via BUY_SEED), seed-budgeted serial claims.
Full battery green including a new M6 (hands-only planting: 138 PLANTs
across two crops, peak 22 in the ground, farmer never planted, device
== CPU byte-exact) and both tapes still dollar-exact. The era cross:
rl/widen_hands.py Net2Net surgery -- draught trunk (~420 iters), old
head rows copied hand-major, PLANT column zero-weight at bias -4,
self-check proves the policy identical on old columns. sower runs
--init-from that surgery ckpt (fresh optimizer, kickstart re-anneals
from 0.5 -- deliberately: barnyard's hand-PLANT intents now label the
new column, they were AUTO-lossy before). Single variable vs
draught-ext: the vocabulary. Opponents barnyard-only, 200 iters, 4
links. The gen-7 question in one line: with the word available, the
observation channels already present (seeds at g[38:43]), the teacher
labelling it, and the build curve paying for crops (cropper's arm),
does the crop economy finally scale past 1.7 plants a game?

## The k06 anatomy: industrial fertilizer, and the third-tier vocabulary gaps (2026-08-21)

Census of the k06 tape (2 reference episodes vs barnyard, 167k/92k):
revenue FERTILIZER 31.8% (qty 3,342 -- eight times w49's volume),
WHEAT 17.8% (qty 2,132; 276 wheat seeds a pair -- feed AND commodity),
WOOL 14.9%, MILK 14.4%, STRAWBERRY 13.5%, MELON 7.3%. The k-line's
structural step over w49 is fertilizer-led volume production: hand
COLLECT_FERTILIZER 600, hand FERTILIZE 118 (crop yield boost), hand
PLACE 100 (the shed-deposit metering the tape gate needed). Our
infrastructure already covers the big pieces (COLLECT task, SELL
vocabulary, cropper's fert-credit potential term, and now PLANT);
the remaining vocabulary gaps are third-tier: hand FERTILIZE and hand
PLACE, an order of magnitude smaller than PLANT was (118/100 ops vs
352). Herd size is the fertilizer feedstock -- k06 buys ~14
animals/game, our build curve's plateau. Seed variance is huge even at
the top (k06: 167k on seed 1000, 92k on seed 2000).

## draught-ext: the plateau is real -- the recipe has converged (2026-08-21, job 20220502)

The 140-iteration extension (280 -> 420) of the accepted draught trunk,
sampled roster at 96 games/opponent: barnyard 47.9% [38.2, 57.8]
margin -2,217 (the accepted draught-samp resolved 56.8% at 384 games --
not dethroned, not improved), ghosts 75.0%/76.0% (same band),
enhanced/main 0% at -33.6k (was -36.8k), spar/lena/w49 walls unmoved.
Training money sat at 41-43k the whole extension. Verdict: **the
draught recipe is done** -- more compute on the same recipe buys
nothing; the 42k dairy plateau is structural (the anatomies say the
next income lines are crops and fertilizer volume, which this
vocabulary cannot express). The deliverable remains draught-samp@280.
The three levers already in flight are exactly the diagnosis: sower
(PLANT vocabulary), wrangler (tape market pressure), cropper (crop
credit + fert-credit).

## sower-v1 KILLED at iter 3: a fresh kickstart anneal is a wrecking ball on a mature trunk (2026-08-21)

Three iterations: win 0.436 -> 0.000, money 42,948 -> 21,520, entropy
6.84 -> 4.64, while barnyard fattened to 56.8k on our collapsed market
presence. The mechanism: --init-from resets the step counter, so ks
re-annealed from coef 0.5 -- a CE loss of ~1.2 against a policy-gradient
term of ~0.03. Forty-to-one. When granger ran that ratio the policy was
RANDOM and the teacher was pure gain; on a trained 42k dairy machine the
same pull scrambles a coherent strategy into half-barnyard incoherence
within minutes. Chain scancelled (20220387-90), 3 GPU-links saved.
Rule for every future warm restart: **teacher coefficient scales down
with trunk maturity** -- a mature trunk gets a whisper (<=0.05), not
the cold-start dose. sower-v2 relaunches from the same surgery init
with ks 0.05/40M, plus the gen-5 credit terms (aa38644 merged into
handplant cleanly): the crop credit, not the teacher, should carry the
planting gradient.

## Hands are DAY LABOUR, and the 4-hand plateau was our own decode (2026-08-21)

Chasing TODO #11's "dead HIRE" hypothesis with a per-day probe
overturned it completely. The engine's _end_of_day does
`farm["hands"] = []` -- **the whole crew is fired every night**. Hands
are day labour: a full 12-hand day costs fib(0..11) = $376, re-bought
every morning; the tops' HIRE spam (k06: 554 orders in 2 episodes) is
simply the daily payroll, and so were our census's "397 dead HIREs".
Nothing was dead. What WAS broken: our HIRE decode bursts at most 4
hires per action, so a 12-hand morning needs the policy to press HIRE
three times before the day's work -- a habit no arm learned in 400+
iterations. The probe showed it plainly: day 21 hired to 8, day 22
back to 4; a permanent 4-hand farm run by an action cap we wrote
ourselves. Fix (handfert branch, with the FERTILIZE task): burst cap
4 -> 10 (the order-slot bound), budget cap unchanged -- one HIRE
action now buys the working day. Effect available to every future arm:
3x labour for pennies, which is exactly the workforce the crop economy
(PLANT/WATER/HARVEST/FERTILIZE at scale) was missing. TODO #11's
masking premise is retired; measured before masked, and a good thing.

## sower pivots to the gen-8 basket; the whisper dose is validated (2026-08-21)

sower-v2's 43 iterations answered the dose question: at ks 0.05
(annealed to 0.01) the trunk did NOT collapse -- money held 41-42k
throughout, entropy climbed 6.5 -> 8.0 as the policy paid an
exploration tax (win 0.44 -> 0.27-0.32) hunting new behaviour. The
maturity rule holds. But v2 was hunting under-equipped: the gen7 tree
still had the 4-hire burst (a 4-hand farm cannot run a crop economy)
and the first-come-first-served PLANT semantics gate_m2 later proved
wrong. Killed at it 43 (checkpoint preserved in the gen7 worktree) and
relaunched as sower-v3 (20223777-81, roster 20223782) from the gen8
tree: PLANT + FERTILIZE + 10-hire day-labour burst + atomic-PLANT
physics + crop/fert credits + whisper ks. One arm, the full basket.

Interpretive note for every verdict now in flight: draught, carter,
cropper and wrangler all trained under the 4-hire burst -- their
shared 42k plateau has a concrete mechanical reading (a 4-hand farm
against the meta's 12), which the anatomies' labour numbers said all
along. The plateau was never about training method; it was about the
size of the workforce the action space could buy.

## cropper takes the wall at 69.8%; carter trades it for generalisation (2026-08-21, jobs 20220646 / 20213998)

Two verdicts, one morning. **cropper-samp (the credit arm: crop curve
+ fert-credit 0.3 over the draught recipe): barnyard 69.8%
[60.0, 78.1], margin +1,875 -- the interval clears 50% whole, at 96
games; ghosts 96.9% / 91.7%; random/starter 100/99.** The previous
best was draught-samp's 56.8% at 384 games. Single-variable answer:
the gen-5 credit terms work, +13pp on the wall -- and this under the
4-hire day-labour cap, with the planting we know it still doesn't do.
Roster stands 5/10 with fatter margins everywhere; main 0% (-38.7k),
spar/lena/w49 walls unmoved. cropper-samp is the acceptance
front-runner now.

**carter-samp (league/pfsp): the yeoman pattern** -- the wall slips to
8.3% (-33.6k) while ghosts hit the line's best-ever 93.8% / 94.8%, and
**main 10.4% (-10.1k): the first nonzero win rate any arm has taken
off enhanced/main**, at a third of draught's margin deficit. Mixed
self-play pools trade the anchored wall for breadth; as a deliverable
it loses, as evidence it says the pool composition steers exactly
what the theory said it would.

Both arms trained at 4 hands. The gen-8 basket (sower-v3) holds the
credit terms cropper just validated, plus the workforce to use them.

## reeve opens gen-9: the strongest trunk takes the tape ladder with a full crew (2026-08-21, jobs 20224217-20)

The behavioural census of final cropper (3/3 wins over barnyard)
attributed its 69.8% to a tighter dairy loop and doubled fertilizer
collection (COLLECT 15 vs 7) -- PLANT stayed at 5; the crop economy is
still locked behind hand labour, as diagnosed. So gen-9 stacks
everything at once: **reeve** = cropper trunk (surgery 8 -> 10,
verified) x the gen-8 basket (PLANT + FERTILIZE + the 10-hire
day-labour burst + atomic physics + the very credits cropper just
validated) x wrangler's tape ladder (barnyard -> w49 -> k06 at the
reachable 0.45 gate), whisper teacher 0.05. Three arms now in flight:
wrangler (tapes, 4-hand era, control), sower-v3 (basket vs barnyard,
attribution), reeve (the confluence bet). Rosters queued at every
tail. If reeve's hands plant under tape pressure, the w49 margin is
the number to watch.

## First light: the crop-and-fertilizer economy assembles (sower-v3, iter ~28/200)

Mid-link census (3 episodes, sampled export): **hand PLANT 87** (~29
plants a game, from 1.7), hand WATER 180, hand HARVEST 265, **hand
COLLECT_FERTILIZER 567 + farmer 62 = 629 -- k06-tape volume (600)**,
BUY_SEED 143 orders (96 wheat + 46 melon, from 24), HIRE 663 orders =
the daily payroll flowing. The pieces the whole night was built for --
day-labour burst, PLANT/FERTILIZE vocabulary, credit terms -- are
running simultaneously for the first time. Not yet monetised: hand
PASS is 41% of hand-turns (idle workforce), score 1W-2L in close games
(52.6/62.4/20.7k vs 60.4/61.4/22.1k), entropy 12.2 still climbing --
the exploration tax is buying structure. 170 iterations of the chain
remain; the number to watch is win rate converting as crops and
fertilizer reach the market.

## wrangler verdict: pressure without means moves nothing (2026-08-21, job 20220535)

The tape-mixture arm (4-hand era, 50% w49 tape / 50% barnyard after its
reachable gate): barnyard 59.4% [49.4, 68.7] (above draught-ext's
47.9%, below cropper's 69.8%), ghosts 80.2/79.2%, and the number the
arm existed for -- **w49 margin -98,844, statistically where draught
left it (-99,970)**. lena -111.6k, main 0%/-43.0k. Verdict: market
pressure alone cannot conjure an economy the action space cannot
produce; training against a 126k-income open-loop opponent taught
price-crash survival, not production. The attribution matrix closes:
credits +13pp on the wall (cropper), league/pfsp trades the wall for
breadth and the first nonzero on main (carter), tapes alone ~nothing
on the target tier (wrangler). What remains in flight is the only
combination the matrix leaves standing: vocabulary + workforce +
credits (sower-v3, recovered to trunk level at it 55 with the crop
economy inside), plus the same under tape pressure (reeve).

## The night's lineage merges to main, battery-sealed (2026-08-21, job 20227171)

main <- handfert: the deposit-PLACE (k06 tape), hand PLANT, hand
FERTILIZE, the 10-hire day-labour burst, the atomic-PLANT physics fix,
the gen-5 credit terms, and the generalised head surgery
(rl/widen_hands.py) -- 7 files, one clean merge, and the full battery
green on main afterwards (MULTI M1-M7 / B3 / B3B / BARN / KICK / TRL /
PIN / both tapes dollar-exact). Worktrees k6tape, gen5, gen7 are
superseded; gen8 keeps running the two live chains on the identical
code. Anything launched from main is now gen-8-native.

## tiller: the trunk-comparison cell (2026-08-21, jobs 20227799-804)

Third live arm, filling the matrix cell the night still lacked:
**tiller** = the CROPPER trunk (reeve's own widened init, reused) x the
gen-8 basket x plain barnyard, seed 1. Against sower-v3 it isolates
the trunk (draught vs cropper at a fixed recipe); against reeve it
isolates the tapes (same trunk, same basket); and it doubles the
night's chance that one basket arm monetises by morning -- the
checkpoint-tree parallelism the project was asked for. Six links
queued (~260 iters), tail roster 20227805.

## The plateau breaks in training: sower-v3 crosses 0.52 (2026-08-21, iter 74-77)

Twenty iterations after recovering the trunk's level with the crop
economy inside (it 55: 0.429), sower-v3 reads **win 0.513-0.542** --
through the 0.42-0.48 batch-win ceiling that defined every 42k-era arm
of this project, with the teacher at zero and the slope intact
(+0.10 win in 20 iters). The assembled economy is monetising. Money
still ~42k vs 43k (win rate is moving first -- more games tipped, not
yet more income; the income lift is what w49 needs). ~320 iterations
of runway remain; tiller (cropper trunk, same basket) just started
L1 and reeve climbs toward its tape gate behind them.

## Census at iter 100: the economy deepens, the mix shifts to melon (sower-v3)

L2 closed at **win 0.574** (0.43 -> 0.52 -> 0.574 across 33 iters).
Census, 3/3 wins (+14.5k/+6.3k/+2.7k): hand WATER doubled to 363 (the
crops are being maintained, not just planted), hand PLANT holds at
82, COLLECT_FERTILIZER 628, idle hand-turns down (5,594 from 6,027) --
and the seed mix flipped on its own: **MELON 56 > WHEAT 35** (was
96 wheat / 46 melon at iter 28). The policy is discovering melon
pricing under the hinge without any anchor pointing at it -- the
credit terms are crop-agnostic. Money at parity-plus (43.6k vs 43.6k
batch means, wins by margin); the income lift phase is next. L3
runs; ~300 iterations of runway remain.

## reeve crosses the gate: the tape stage begins, this time with means (2026-08-21)

reeve's barnyard EMA touched 0.45 around iter 90 and the pool advanced
to stage 2/3 -- half its batches now face the w49 tape's 84-126k
economy. Tape-batch money starts at ~27k, exactly where wrangler's
sat for its whole run; the difference is that reeve carries the
vocabulary, the day-labour burst and the credit terms. Whether
tape-batch money CLIMBS from here is the entire question wrangler's
verdict posed ("pressure without means moves nothing" -- now the
means are aboard). Runway ~300 iterations.

## Another first: the learner out-earns the wall (sower-v3, iter 102-105)

win 0.60-0.65 and **money 43.6k vs barnyard's 41.6k -- the first
positive batch-mean income margin in the project's history** (every
prior era sat 2-3k under). The curve: 0.43 (it 55) -> 0.52 (77) ->
0.574 (88) -> 0.64 (105), slope intact. The win-rate phase is rolling
into the income phase on schedule; what the w49 wall needs is for
this margin to keep widening as the crop economy scales.

## Deploy check at iter ~110: the curve is real (sower-v3)

Reference-engine validation of the mid-chain checkpoint: **67.7%
[57.8, 76.2] vs barnyard, margin +1,659, median money 45,878** -- the
training climb transfers to deployment intact, and at a third of its
runway sower-v3 already matches cropper-samp's tail (69.8%). Median
income 45.9k is the highest this line has recorded (the 42k era is
over). The tail roster (12 opponents, tier-2 anchors included) will
say what the income curve bought against the walls.

## The counterfactual answers: tape-batch income moves (reeve, iter 96-133)

Under the w49 tape's crashed market, reeve's income climbs 27.0k ->
30.5k across 37 iterations -- the exact number wrangler sat on for its
entire run without means (26-27k, flat). Pressure with vocabulary,
workforce and credits aboard IS trainable signal. Slow (+~1k/10 iters)
but structural; ~270 iterations of runway remain, and every 1k here is
1k off the -98k w49 margin at the tail. tiller tracks sower-v3's
recovery arc on schedule (0.361 at it 46).

## Census at iter ~160: the economy is land-gated now (sower-v3)

3/3 wins (+12.0k/+3.7k/+6.2k, margins growing), but the structure
says the next wall is LAND: BUY_LAND stuck at 1/game (2 quadrants)
while the 60-crop economy needs 3-4. The policy has adapted around
the constraint rather than through it -- seed buying tightened from
143 to 77 orders (it buys what it can plant), idle hand-turns ticked
back up (no land -> no crop chores). Diagnosis: land is underpriced
in the potential (LAND_VALUE = 300 flat, vs the ~5k of downstream
crop credit a quadrant actually unlocks), and the BUY_LAND gradient
arrives only through a two-step chain. First concrete gen-10 design
input from tonight's data: **value land by what it unlocks** (raise
the build-curve land term or make LAND_VALUE scale with seed/crop
flow) -- recorded in rl/TODO.md #13.

## Census at iter 228: the top meta's anatomy, reproduced from scratch (sower-v3)

**win 0.909-0.927, money 52.1k vs barnyard's 42.7k (+9.5k batch
margin).** The census explains it: hand WATER 1,205 (was 405; w49's
tape does 1,744), hand PLANT 126 = 42 crops a game (was 82), HARVEST
441 (was 264), FERTILIZE 30 (was 1), idle hand-turns HALVED to 3,351
(was 6,463) -- and the seed mix moved again, on its own:
**STRAWBERRY 144 > MELON 31 > WHEAT 9**. Strawberry is the top meta's
LARGEST revenue line (30.4% of w49's season, RUNS.md 2026-08-21) and
nothing in the reward names it: the crop-agnostic credit terms plus a
workforce that can water 1,200 times found it. 3/3 census wins by
+13.9k / +18.8k / +13.9k. A 12-opponent roster on this exact
checkpoint is running (job 20233430) rather than waiting for the chain
tail -- if it clears 70% on barnyard this is the new deliverable.
Two arms confirm the arc: tiller 0.761 / 49.5k at it 143, reeve 0.838
/ 52.5k at it 259 (its barnyard batches, while half its diet is the
w49 tape).

## BREAKTHROUGH: sower-it228 rewrites every number (2026-08-21, job 20233430)

Twelve opponents, 96 games each, sampled export of the it-228
checkpoint -- and it is a different agent from anything this project
has produced:

| opponent | sower-it228 | previous best | delta |
|---|---|---|---|
| barnyard | **92.7% [85.7, 96.4]** +11,336 | cropper 69.8% +1,875 | **+23pp** |
| ghost-89825016 | **100%** +34,494 | cropper 96.9% | +3pp |
| ghost-89830307 | **100%** +36,017 | cropper 91.7% | +8pp |
| enhanced/main | **19.8%** -9,753 | carter 10.4% -10,106 | **+9pp** |
| spar grazier | **6.2%** -11,096 | 0% -13,255 | **first nonzero vs spar** |
| spar berrybaron | 0% -18,564 | 0% -28,058 | margin -9.5k |
| **closer_cleo** | 0% **-82,184** | 0% -102,609 | **+20,425** |
| broker_bea | 0% -89,552 | 0% -104,832 | +15,280 |
| ledger_lena | 0% **-91,168** | 0% -105,129 | +13,961 |
| w49 | 0% **-84,468** | 0% -95,976 | +11,508 |

Roster 5/12 with both recordings at 100%, and -- the number that
matters for the ladder -- **every tier-2/3 wall closed by 11-20k in a
single generation**. The 1364-tier deficit went from 2.5x income to
~2.0x. Nothing here is a tuning artefact: the same checkpoint's census
shows 42 crops a game, 1,205 hand waters, strawberry as the lead crop,
idle labour halved. The breakthrough protocol is firing: mirror +
packaging (job 20233780). The chain has ~170 iterations left and the
slope has not bent -- this is a mid-chain checkpoint, not a tail.

## plowman: the land A/B, forked off the breakthrough (2026-08-21, jobs 20234101-04)

The iter-160 census named the next wall (land: BUY_LAND stuck at 1/game
while a 60-crop economy needs 3-4 quadrants) and diagnosed why -- the
potential prices a quadrant at Kilo's flat $300 while it unlocks ~5k of
downstream crop credit. `--land-value` (main tree, default off,
test_trl green) is the lever; **plowman** is the A/B: the sower trunk
forked at iter 251 with ONE change, land 300 -> 1500. The control is
the sower chain itself, still running the same recipe at 300, which
makes this the cleanest single-variable test the project has run --
same trunk, same recipe, same seeds stream, one constant. Four links
(~170 iters), roster 20234105. Watch BUY_LAND per game (1 -> 3?) and
whether crops move past 42.

## The income curve keeps going: 56.9k, and reeve's tape batches hit 38.7k (2026-08-21)

sower-v3 at iter 258-259: **win 0.945, money 56.9k vs the wall's
45.6k** -- +11.3k batch margin, and the income is now 35% above the
42k plateau that stood for the project's whole history. plowman forked
from this trunk reads the same on its first iterations (0.945 / 57.7k
at land 1500, too early to attribute).

reeve, meanwhile, answers wrangler's question completely: its
**tape-batch income is 38.7k, up from 27.0k when the stage opened**
(iter 96 -> 301). wrangler, without the means, sat at 26-27k for its
entire chain. +11.7k of income earned inside a market the w49 tape has
crashed -- that is the mechanism that closes the -84k margin, measured
directly.

## harrow: a pure top-economy diet (2026-08-21, jobs 20234367-69)

Fifth arm, fifth GPU. reeve proved income is trainable under tape
pressure (27.0k -> 38.7k); harrow asks how far that goes when the diet
is ONLY the target economies: the breakthrough trunk (sower @ 251) vs
tape:w49 -> tape:k06, gate 0.30, no barnyard mass, no teacher (ks 0 --
barnyard's intents are the wrong teacher for a 100k economy). reeve is
the mixed control. The known risk is the documented one: open-loop
tapes are exploitable, so the roster (barnyard / main / spar / ghosts
/ tier-2 anchors) is the judge, not the training win rate -- which
will read ~0 by construction. The number that matters: tape-batch
income, and whether the tail roster's w49/lena/cleo margins fall
below -80k.

## SUBMITTED: sower-it228, the RL line's first ladder read (2026-08-21)

User authorised one submission. Pre-flight per SUBMISSION_POLICY: stress
**28/28 clean, worst turn 238ms** (limit 1000), mirror margin +0, package
unpacked-and-played ($60,365), snapshot in
`submissions/2026-08-21-sower-it228/`. Uploaded 19.8 MB; 4 submissions
left today. Side effect noted at submit time: only the latest two are
active, so this retires 55489160 (2035.9 -- a mined top-of-ladder plan
replayed open-loop, not ours and not RL) and leaves the RL v2 baseline
(55542013, 506.9) plus this one. That is the point of the read: RL v2
scored 506.9 while losing 0/96 to barnyard; this agent beats barnyard
92.7% and takes 19.8% off enhanced/main, so the gap between those two
numbers calibrates the whole local->ladder mapping for this line.
Expect a floor, not a level, for the first hours (rule 7: a score does
not count until the agent has lost a third of its games).

## Two tails, two firsts, and a clean complementarity (2026-08-21)

**sower-samp (tail, it 286; basket vs barnyard):** barnyard 96.9%
+15,437, **enhanced/main 55.2% [45.3, 64.8] margin +2,020 -- the first
time this project's RL line has WON against main**, spar grazier 28.1%
(was 6.2% at it 228), w49 -78.1k. Interval spans 50 so main is
"unresolved" pending a 384-game run, but the point estimate and the
margin are both positive for the first time.

**reeve-samp (gen-9 confluence; 50/50 barnyard + w49 tape):** barnyard
94.8%, **spar grazier 61.5% [51.5, 70.6] -- interval entirely above 50,
the first outright win over an `agents/spar/` agent (the field
reconstructed from real ladder replays)**, and the best wall margins
this project has recorded: **cleo -79.1k, lena -78.7k, bea -79.7k,
w49 -70.4k**. Its weakness is exactly where sower is strong: main 8.3%.

The complementarity is the finding: **tape pressure buys wall margin,
barnyard/self-play buys reactive skill against reactive opponents.**
sower is +47pp on main; reeve is 6-22k better on every tier-2/3 wall.
Neither dominates. The next arm has to be the mixture, and that is
what sheaf (below) is.

For the record, the arc of the wall margins in one night:
draught -100.0k -> cropper -96.0k -> sower-it228 -84.5k ->
sower-tail -78.1k -> reeve -70.4k (w49); and cleo -102.6k -> -79.1k.

## sheaf and granary: the mixture and the leak (2026-08-21, jobs 20237088-91 / 20237170-73)

**sheaf** (gen-11 mixture): reeve's trunk -- the best wall margins on
record -- on barnyard + w49 tape + k06 tape **with league snapshots and
pfsp**, plus land 1500. The two tails proved tape pressure and reactive
self-play buy different things and trade off; sheaf trains both at once,
which is the only combination the verdict matrix leaves untried.

**granary** (gen-11 A/B): sower's tail continued with exactly one
change, `--wheat-feed-cap 2.0`. It runs from the gen11 worktree
(c401c8c, WHEAT-PASS: cap-off twins byte-equal, cap-on twins agree and
differ, the promise verified pointwise on a synthetic grid). The
control is sower's own tail roster, already archived. Expected value if
the measurement holds: +21k a game, a third of current income, and the
same again off every wall margin.

Five arms now: tiller and plowman (land A/B) finishing, harrow (pure
tape diet), sheaf, granary. Rosters queued at every tail.

## bourse: the missing term gets an A/B (2026-08-21, jobs 20238051-54)

The gap analysis traced hoarding, the wheat churn and the absent
sell-timing skill to ONE missing term -- the potential believed a sale
does not move the price. `--potential future-exec` (gen12, 37e8623,
EXEC-PASS) values shed stock at what the engine would actually pay for
it, unit by unit down its own price curve. The gate quantified the old
distortion: **a 300-unit milk hoard was overvalued by 37,436** -- more
than a whole game's income. bourse forks sower's tail with that single
change; granary forks the same trunk with the wheat cap; sower's own
tail roster is the shared control. Queued behind tiller's last link to
hold GPU concurrency at five.

## tiller verdict: the arc reproduces, the trunk does not decide it (2026-08-21, job 20227805)

tiller = the cropper trunk on the same gen-8 basket that sower ran on
the draught trunk. Roster: barnyard 94.8% +17,325 (the largest wall
margin any arm has posted), main 37.5% -3,502, spar grazier 19.8%,
ghosts 100/100, w49 -83.9k, cleo -86.5k, income distribution median
40.9k with 16% of games under 20k.

Against sower's tail (barnyard 96.9%, main 55.2%, w49 -78.1k, 10%
under 20k) it is a shade weaker everywhere except the barnyard margin.
Verdict: **the basket, not the trunk, is what carries this generation**
-- two different trunks converge to the same behaviour within noise,
which is the cleanest evidence yet that the vocabulary/workforce/credit
package is the causal ingredient. Trunk choice for future forks can
therefore be made on income-distribution floor rather than lineage.

## The frozen farm, explained: the shaping term punished growth (2026-08-21)

A per-day trace of the submitted agent (sower-it228 vs barnyard, seed
1000) shows the shape of every arm's ceiling: **8 cows and 8 structures
by day 6, then twenty-three days without buying a single animal,
structure or quadrant, while cash climbed from $0 to $46,230 and sat
idle.** No animals died (8 stayed 8). Feeding was 220 farmer actions and
**zero hand actions**. The farm did not fail to grow; it stopped
choosing to.

The cause is in the potential, stacked from two Kilo constants:

1. `ANIMAL_CREDIT 0.4` / `PLANT_CREDIT 0.5` price future production at
   40-50%, so a cow that really returns +720 (7 milk x 160, cost 400)
   reads +48;
2. `UNFED_RISK 0.8` + `UNCARED_RISK 0.3` are charged off the DAILY
   fed/cared flags, so a newly placed animal is charged **1.1x its own
   cost the moment it lands** -- and "not fed yet today" is every
   animal's normal morning state.

Measured deltas for one more cow, net of its price: **day 10 -392,
day 16 -584** -- the dominant reward term was telling the policy that
growth is a mistake, all season, in every arm. That single fact explains
the frozen herd, the 2-quadrant board, the idle cash, and a good part of
the income gap to the 1364 tier (their farms are 3 land / 13 animals).

Fix (gen13, d896f4a, CAPITAL-PASS): `--capital-credit` replaces both
haircuts; `--risk-mechanic` charges neglect the way the engine does
(escape at 2 unfed days, costing that animal's own credited production).
The pair moves day 10 to **+600** and day 16 to **+120** while keeping a
genuinely bad day-22 purchase negative. **byre** (jobs above) is the
A/B: sower's tail trunk, that pair, sower's own tail roster as control.

## harrow rewrites the field: 7/12, the best floor, and wrangler's verdict inverted (2026-08-21, job 20234370)

The pure top-economy diet -- gen-8 basket, w49 then k06 tape, no
barnyard mass, no teacher -- is the strongest product this project has
produced, on every axis at once:

| opponent | harrow | previous best |
|---|---|---|
| barnyard | **100%** +11,804 | sower-tail 96.9% |
| **enhanced/main** | **64.6% [54.6, 73.4]** +3,893 | sower-tail 55.2% (CI spanned 50) |
| **spar grazier** | **84.4% [75.8, 90.3]** +7,037 | reeve 61.5% |
| spar berrybaron | 36.5% -1,879 | reeve 1.0% |
| ghosts | 100% / 100% | 100% / 100% |
| closer_cleo | 0% **-70,040** | reeve -79,128 |
| ledger_lena | 0% **-70,661** | reeve -78,703 |
| broker_bea | 0% **-70,036** | reeve -79,656 |
| w49 | 0% **-68,661** | reeve -70,354 |

**7/12 beaten** (random, starter, both ghosts, barnyard, main, grazier),
income median **47,218** and -- the number the ladder losses pointed at --
**only 4% of games under 20k** (sower-it228, the submitted one: 20%).

And it inverts wrangler's verdict. wrangler concluded "pressure without
means moves nothing": tapes alone, in the 4-hire era, left w49 at
-98.8k. With the means aboard (vocabulary, day-labour crew, credits),
**tape pressure is the best diet we have** -- better than barnyard
self-play (sower) and better than the 50/50 mixture (reeve). The tapes
are not opponents to beat; they are a 100k economy to imitate under
market pressure, and the policy learns the production side from them.

Acceptance chain running (job 20240482: mirror, stress, packaging).
This is the submission candidate whenever the next slot is authorised.

## The library has a 186k tape (2026-08-21) -- threshing takes the pool

harrow reached 7/12 on ONE tape that replays at 83.8k, and its pool
never even advanced past stage 1. Checking what else the mined library
holds, all four gate-verified byte-exact on the current engine:

| tape | replayed money (this engine) | recorded (manifest) |
|---|---|---|
| **w03** | **186,101** | 155,241 |
| k06 | 100,032 | -- |
| w10 | 96,168 | -- |
| w01 | 86,215 | 157,577 |
| w49 | 83,778 | -- |
| w02 | 80,265 | 155,280 |

w03 replays at over twice w49 and above k06 -- the richest economy
available to train against, and it was sitting unused all along.
**threshing** (jobs 20243698-704, roster 20243705) is harrow's recipe on
the pool {w49, w10, k06, w03} with pfsp weighting toward whichever the
policy loses to hardest, forked from harrow's own trunk. If tape
imitation is what carried harrow to 7/12, a library twice as rich is the
cheapest multiplier on the board.

## The walls were always trainable: cleo, lena and bea are wrapper-plus-tape (2026-08-21)

`agents/bench3/closer_cleo.py` and `agents/wrapped/w49.py` are the same
637-line file with a different `_TRACE`: the tier-2 anchors ARE the same
wrapper-plus-plan construction as the mined tapes. So their plans load
straight into `tape_t` -- and they gate byte-exact on the current engine:

| anchor | tape replay (this engine) | ladder rating |
|---|---|---|
| closer_cleo | **155,344** | 1363.7 |
| ledger_lena | **150,635** | 1364 tier |
| broker_bea | **150,150** | 1364 tier |

**The tier this project has never taken a single game from -- 0/96 on
every roster it has ever appeared in -- has been available as a training
opponent all along.** docs/GAP-2000.md called this the hardest wall on
the way to 2000 ("no reactive 1364-tier opponent can be trained
against") and estimated real work to fix; the actual fix was one command,
because cleo shares w49's wrapper.

Caveat, stated plainly: the tape is the PLAN, not the agent. The wrapper
(terminal liquidation from step 680, sell reordering, front-run) is worth
about 26k -- `tape:w49` replays at 83.8k while the wrapped w49 earns
~110k against us -- so these are open-loop 150k economies, not reactive
1364-tier play. Open-loop tapes are exploitable, which is why the roster
judges and the pool keeps five of them with pfsp.

**anvil** (jobs 20244318-21, roster 20244322): harrow's trunk on the pool
{k06, bea, lena, cleo, w03} -- the actual walls plus the two richest
tapes -- gate 0.25, pfsp hardest-first. threshing (generic strong tapes)
is the control: does training on the EXACT walls beat training on
comparable strangers?

## plowman verdict: land pricing is real but the barnyard-only diet caps it (2026-08-21, job 20234105)

Land at 1500 instead of 300, single variable off sower's trunk:
barnyard **100% +27,642** (the largest margin any arm has posted against
the wall), grazier 63.5% (beaten), main 34.4%, ghosts 100/100,
cleo -76.6k, w49 -76.6k, lena/bea -84.3/-84.6k. **6/12**, income median
45.7k, 12% of games under 20k.

Read against its control (sower's tail: barnyard 96.9%, main 55.2%,
cleo -85.4k, 10% under 20k) and against harrow (100%, main 64.6%,
cleo -70.0k, 4% under 20k): **the land term clearly works on the
production side** -- +8k of self-play income, +10k of wall margin
against cleo/w49 -- but on a barnyard-only diet it does not touch the
reactive matchups the way tape pressure does, and its floor is worse
than harrow's by 8 points. The lesson matches sheaf's premise: the
potential fixes and the opponent diet are orthogonal, and the diet is
what moves the tier-2 walls. The four potential arms (land, wheat,
market impact, capital credit) are therefore best judged as ingredients
to fold into a TAPE arm, not as products on their own.

## harvest: both halves multiplied (2026-08-21, gen15 b728e61)

plowman's verdict separated the two things this project has been fixing:
the **reward's truthfulness** (four measured falsehoods, each now a
gated flag) and the **opponent diet** (tape pressure, which is what moves
the tier-2 walls). Each was tested alone. **harvest** multiplies them:

  diet   tape:{cleo 155k, lena 151k, bea 150k, w03 186k, k06 100k}, pfsp
  reward land 1500 + future-exec + wheat-feed-cap 2.0
         + capital-credit 1.0 + risk-mechanic
  trunk  harrow's tail (the 7/12 product)

gen15 merges all four flag sets into one tree (wheatgate into capcredit)
and passes the whole battery -- WHEAT-PASS, CAPITAL-PASS, EXEC-PASS,
test_trl, MULTI-PASS -- plus an all-flags-on training smoke. Five links,
roster at the tail. This is the arm the last twelve hours of measurement
were aiming at.

## sheaf verdict: the mixture buys the best floor (2026-08-21, job 20237092)

barnyard + w49/k06 tapes + league snapshots + pfsp, land 1500, from
reeve's trunk: barnyard 100% +15,303, grazier 83.3%, main 58.3%
[48.3, 67.7] +3,006 (interval spans 50), berrybaron 42.7%, ghosts
100/100, walls cleo -71.7k / lena -71.0k / bea -70.0k / w49 -73.3k.
**6/12**, and the distribution is the best on record: **income median
51,933, only 3% of games under 20k** (harrow 47.2k / 4%; the submitted
it228 35.7k / 20%).

Head to head with harrow (pure tape diet): harrow wins main outright
(64.6% with the interval clear of 50) and takes 7/12; sheaf has the
better income distribution and matching walls. Since the ladder's losses
are floor events, both are live candidates -- a 384-game resolution of
sheaf's main matchup (queued) decides whether the mixture matches
harrow's roster too.

## SUBMITTED: harrow-samp, the second RL read (2026-08-21)

User authorised this one plus one more overnight if a stronger arm lands.
Uploaded 19.8 MB, 3 submissions left today. Active pair is now
harrow-samp + sower-it228 (544.0 and climbing, 21 games 10W-11L), so the
first read stays live as the control -- the displaced slot was the old
2026-08-16 RL v2 baseline (507.9).

Pre-flight, all archived above: 7/12 roster, mirror margin +0, stress
28/28 with a 66.7ms worst turn, package unpacked and played ($73,703),
income median 47.2k with 4% of games under 20k against the submitted
predecessor's 20%. Honest expectation stated to the user before
submitting: **900-1300, not 1500** -- a ladder rating is where you stop
winning, and the cleo/lena/bea tier (1287-1364) is still 0/96 locally.

## granary verdict + sheaf resolved (2026-08-21, jobs 20237174 / 20247922)

**granary** (the wheat feed cap, single variable off sower's trunk):
barnyard **100% +28,243** (largest wall margin on record, edging
plowman's +27.6k), grazier 72.9% beaten, main 43.8% +413, ghosts
100/100, walls cleo -78.6k / lena -80.5k / bea -79.8k / w49 -72.1k.
**6/12**, income median 46.3k, 13% under 20k. The cap does what the
measurement promised on the production side (+8k of self-play income,
the wall margin up 12k over its control) but, like plowman's land term,
a barnyard-only diet leaves the reactive matchups and the floor behind
harrow's. Third confirmation that reward truth and opponent diet are
orthogonal.

**sheaf's main matchup resolved**: 384 games, **58.6% [53.6, 63.4],
margin +2,851** -- interval entirely above 50, so sheaf beats
enhanced/main outright and its roster is **7/12**, matching harrow with
a better floor (3% vs 4%) and a better median (51.9k vs 47.2k). Two
7/12 products now, both tape-fed; the difference between them is the
mixture (sheaf keeps barnyard mass + league snapshots).

## bourse verdict: the truest reward term, and it made the agent worse (2026-08-21, job 20238055)

The market-impact potential (`future-exec`, stock valued at execution
revenue) is the most defensible term in the whole potential -- X2 of its
gate proves the valuation equals the engine's payment to the dollar --
and as a single variable off sower's trunk it produced the **largest
self-play income of any arm (70.4k) and the biggest barnyard margin
(+31,133)**, while the roster went the other way:

    BEATEN 5/12 (was 5/12 for the control, but the shape is worse)
    grazier   0.0% (control 28.1%, harrow 84.4%)
    main     15.6% (control 55.2%)
    lena  -90.5k, bea -89.3k (control -100.2k / -102.1k)
    income median 41.2k, **20% of games under 20k** (control 10%)

Read plainly: pricing market impact taught the policy to hoard less and
sell into thin markets, which maximises money against a passive
opponent and **collapses against anyone who competes for the same
demand** -- exactly the matchups (grazier, main) where it fell. The
honest lesson is the one this repo already has in ROADMAP §11: a term
being TRUE is not the same as a term being USEFUL, and only the A/B
tells you which. `future-exec` stays in the tree, off by default, and it
does NOT go into the harvest package.

Correction filed for harvest: it currently runs with `--potential
future-exec`. The three fixes that measured well (land, wheat cap,
capital credit + risk mechanic) stay; the market-impact term should be
dropped from the combination. Rebuilding the arm with
`--potential future-mkt` and keeping the rest.

## Both reads climbing; harrow's floor shows up on the ladder (2026-08-21 evening)

| submission | score | games | our income (ladder) |
|---|---|---|---|
| sower-it228 (55668491) | 498.4 -> 544.0 -> **558.2** | 21 (10W-11L) | median ~52k, four games at 14-36k |
| **harrow-samp (55673426)** | **593.3** (entering) | 11 (5W-6L) | **median 61.8k, minimum 27.8k** |

harrow's first eleven ladder games confirm what the local distribution
predicted: **its worst game is 27.8k where it228's worst four were
14-36k**, and its median income is 61.8k against it228's 52k. Every loss
so far is to an opponent earning 33-84k -- it is losing to production,
not collapsing. The 4%-floor property is the one that transfers.

## byre verdict: the biggest wall margin ever recorded, and still 5/12 (2026-08-21, job 20239591)

The investment-truth pair (capital-credit 1.0 + risk-mechanic) off
sower's trunk: **barnyard 100% with margin +40,459** -- half again the
next best (granary +28.2k) and nearly four times the control's +15.4k --
plus the highest self-play income any arm reached (72.0k). Walls
cleo -73.4k / w49 -76.3k (control -85.4k / -78.1k), lena/bea -83.5k.
And yet: grazier 40.6%, main 30.2%, **5/12**, median 44.6k, 13% under
20k.

Same shape as plowman, granary and bourse: **a reward fix that is
mechanically right buys production and buys nothing against reactive
opponents.** Four independent confirmations now. The wall margin ranking
is almost the inverse of the roster ranking:

| arm | barnyard margin | BEATEN | main |
|---|---|---|---|
| byre | **+40,459** | 5/12 | 30.2% |
| bourse | +31,133 | 5/12 | 15.6% |
| granary | +28,243 | 6/12 | 43.8% |
| plowman | +27,642 | 6/12 | 34.4% |
| harrow (tape diet) | +11,804 | **7/12** | **64.6%** |
| sheaf (tape+mix) | +15,303 | **7/12** | **58.6%** |

Beating barnyard harder is not progress; it is overfitting to barnyard.
The tape arms win less crushingly against the wall and far more against
everything that fights back. Every future product line goes through a
tape diet -- that is now settled by six arms, not an argument.

## harvest killed at iter 50, and why: base-priced credit lies under tape pressure (2026-08-21)

harvest (three reward fixes on the wall-tape pool) degraded instead of
adapting: tape-batch income 39.6k -> 37.3k -> 34.0k -> 32.6k across 50
iterations, against anvil's 44.5k and threshing's 44.2k on the same diet
with no reward changes. Killed; four GPU-links saved.

The mechanism is bourse's lesson in a second costume. `capital-credit
1.0` credits future production at **base** price. That is exactly right
when you can sell at base -- which is the barnyard world, where byre
posted a +40k wall margin -- and it is a lie when a 150k tape is dumping
into the same market and realised prices sit far below base. The
potential then over-values production, so the policy over-invests into a
crashed market and its income falls. Both of the two reward terms that
looked most principled (execution pricing, base-priced capital credit)
fail specifically under the diet that matters.

**harvest3** (jobs above) keeps only the diet-agnostic fixes: land 1500
(a quadrant unlocks 25 tiles regardless of price), wheat-feed-cap 2.0
(pure churn prevention, no price assumption) and risk-mechanic (removes
a spurious placement penalty). capital-credit stays in the tree, off,
with this verdict attached: **it belongs to barnyard-diet runs only.**

## threshing verdict: the richer library buys the best main and w49 numbers (2026-08-21, job 20245143)

harrow's recipe on the pool {w49 84k, w10 96k, k06 100k, w03 186k} with
pfsp, 300 iterations: **main 68.8% [58.9, 77.1] +5,991** (harrow 64.6%,
the best reactive-matchup number this line has posted), **w49 -66,334**
(harrow -68.7k, the smallest tier-3 deficit on record), cleo -68.9k,
lena -74.1k, bea -77.7k, grazier 63.5%, ghosts 100/100, barnyard 89.6%
+9,003. **7/12**, income median 48.6k, 5% under 20k.

Against harrow (single w49 tape): main +4.2pp, w49 margin +2.3k, cleo
-1.1k, barnyard -10.4pp, floor +1pp. So the richer library helps exactly
where it should -- the matchups that require production and adaptation --
and costs a little of the barnyard saturation nobody needs. Three tape
arms now sit at 7/12 (harrow, sheaf, threshing), each with a different
mixture, and all three beat main; the four barnyard-diet reward arms sit
at 5-6/12 with none beating main. The diet finding is now overdetermined.

Still 0% on cleo/lena/bea/w49. The margins have come from -103k (cropper,
this morning) to -66k, i.e. 36% of the gap closed in one day, but no arm
has taken a single game off that tier yet.

## anvil verdict AND submitted: training on the walls themselves (2026-08-21 night, jobs 20244322 / 20258070)

The arm that trains on the tier it has never beaten -- pool {cleo 155k,
lena 151k, bea 150k, w03 186k, k06 100k}, pfsp, no barnyard, no teacher:

| axis | anvil | harrow (previous best) |
|---|---|---|
| enhanced/main | **72.9% [63.3, 80.8]** +6,262 | 64.6% |
| spar grazier | **72.9%** +1,878 | 84.4% |
| ghosts | 100/100, **+45.1k / +46.1k** | 100/100, +41k |
| ledger_lena | **-67,688** | -70,661 |
| closer_cleo | **-68,087** | -70,040 |
| broker_bea | **-69,281** | -70,036 |
| w49 | -74,491 | **-68,661** |
| income median | **52,998** | 47,218 |
| **games under 20k** | **2%** | 4% |
| BEATEN | 7/12 | 7/12 |

Training against a tier moves that tier: the three anchors it trained on
all improved, and w49 -- the one strong tape NOT in its pool -- got
worse. That is the cleanest causal statement about opponent diet this
project has produced, and it is a recipe, not a coincidence: to close a
wall, put that wall in the pool.

Also the best deliverable on both ladder-relevant axes: median income
53.0k and a 2% catastrophic tail (the submitted first read had 20%).
Acceptance: mirror margin +0 [-800, +766], stress 28/28 worst turn
68.2ms, package unpacked and played $74,983. **Submitted** under the
user's overnight authorisation (2 submissions left today); active pair is
now anvil + harrow (632.9), with sower-it228 (568.3) retired to make
room -- harrow stays as the control.

## forge: every tape-able wall in one pool (2026-08-21 night, jobs 20258762-66)

anvil established the rule and its own gap proved it: the three anchors
in its pool improved (cleo -70.0k -> -68.1k, lena -70.7k -> -67.7k,
bea -70.0k -> -69.3k) while w49, the one strong tape left out, regressed
(-68.7k -> -74.5k). forge applies the rule completely -- **seven tapes,
every wall this project can compile**: cleo 155k, lena 151k, bea 150k,
w03 186k, k06 100k, w10 96k, w49 84k, pfsp hardest-first, from anvil's
own trunk.

Checked and excluded: `agents/spar/*` (0 of 30 files carry a `_TRACE` --
they are generated atom agents, not wrapper-plus-plan) and
`agents/enhanced` (hand-written). Those stay eval-only, which keeps three
genuinely held-out opponents on the roster -- spar grazier, spar
berrybaron and enhanced/main -- so forge cannot be scored against a field
it trained on.

## The margin has two terms, and we had only ever measured one (2026-08-22)

Measuring the OPPONENT's income on the roster's own 48 seeds, for the
first time:

| opponent | alone (vs passive starter) | with harrow present | with anvil present |
|---|---|---|---|
| w49 | **159,195** | 101,952 (**-57,244**) | 118,491 (-40,704) |
| closer_cleo | **148,150** | 106,204 (-41,946) | 112,769 (-35,382) |

Three things follow, one of them a correction of my own claim.

**(1) Correction: the "tape replay value" numbers were single-seed
noise.** The tape gate replays on seed 424242, where w49's plan earns
83,778 -- but on the roster's 48 seeds the same plan averages 159,195
against a passive opponent. So "the library has a 186k tape" (w03)
overstated w03's specialness: every one of these plans is a 150k+
economy, and the ordering I read off single-seed replays was mostly
seed luck. The pool choices survive (they were all strong), the ranking
does not.

**(2) The wrapper is worth ~nothing on the same board.** Wrapped w49 vs
starter 83,684 against the pure tape's 83,778; wrapped cleo 154,165
against 155,344 -- both slightly LOWER. So `GAP-2000.md`'s "the wrapper
is worth about 26k" was a confounded comparison (tape-vs-starter against
wrapped-vs-us) and is withdrawn. The terminal-liquidation port
(gen16 tapewrap, TAPEWRAP-PASS) adds +109 for cleo and +0 for w49
because **the recorded plans already liquidate**. It stays in the tree,
default on, as a correctness nicety, not a lever.

**(3) The real decomposition, and where the next gain is.** margin =
our income - theirs, and both halves are ours to move:

    harrow:  we 33.6k, w49 102.0k  ->  margin -68.4k   (suppresses -57.2k)
    anvil:   we 43.0k, w49 118.5k  ->  margin -75.5k   (suppresses -40.7k)

**anvil earns 9.4k more than harrow and lets w49 earn 16.5k more, so its
margin is worse.** Every arm so far has been optimised for the first term
only. Beating the 1364 tier needs both: earn ~100k AND hold them near
100k. That reframes the "0% on four walls" number -- we are not one
production doubling away, we are one production doubling plus a
suppression policy away.

## vise: the suppression term was saturated all along (2026-08-22, jobs 20260935-38)

The terminal margin reward is `margin_bonus * tanh((mine - theirs) /
margin_scale)` with scale 50,000. Against the tier we care about our
margin sits at -70k, i.e. **tanh(-1.4) = -0.89 -- saturated, slope
~0.06.** Every arm has therefore trained with the second half of the
objective effectively switched off: crushing the opponent's income by
20k and losing by 50k instead of 70k earned it almost nothing.

vise unsaturates it -- scale 150,000 (slope ~0.8 in the operating range)
and weight 3.0 -- with everything else identical to anvil: same trunk,
same five-tape pool, same potential. If the suppression half of the
margin is trainable at all, this arm is where it shows, and the number
to read is not our income but **the opponent's** in the tail roster
(w49 101.9k under harrow, 118.5k under anvil, 159.2k alone).

## harvest3 verdict: three fixes that each worked, broken by their combination (2026-08-22, job 20252023)

The three "diet-agnostic" reward fixes together (land 1500 + wheat cap
2.0 + risk-mechanic) on the wall-tape pool, and the roster says
**bankruptcy**:

    starter        38.5%   (it LOSES to the scripted starter 61% of the time)
    random         86.5%   (100% for every other arm)
    p05 income     0       (at least 5% of games end at zero money)
    under 20k      21%     (anvil 2%, harrow 4%)
    w49            -138,796  (w49 earns 148,180 -- unsuppressed)
    BEATEN         5/12

Losing to `starter` and a p05 of exactly zero is a collapse signature,
not a weak strategy. The mechanism fits an interaction nobody tested:
**wheat-feed-cap limits the feed stock while risk-mechanic removes the
daily unfed penalty**, so the policy is free to under-feed, the herd
escapes (the engine takes an animal at two unfed days), and on the seeds
where that starts early the farm never recovers. land-value 1500 then
compounds it by pulling cash into quadrants.

Each of the three measured *well* on its own (plowman 6/12, granary
6/12, byre 5/12 with the biggest wall margin on record). **Their
combination is worse than any of them and worse than doing nothing.**
That is the third distinct way this project has now seen reward terms
fail -- untrue (land at 300), true-but-useless (execution pricing,
base-priced capital credit), and individually-fine-but-jointly-toxic.
Recorded rule: **potential terms compose non-linearly; a package needs
its own A/B, never inheritance from its parts.**

Product line unchanged: the tape-diet arms (harrow, anvil, threshing,
forge, vise) carry the line; the reward fixes stay off by default.

## chisel: the single-point attack on the 1364 tier (2026-08-22, jobs 20264844-47)

Four walls at 0/96 is the most stubborn number on the board, and anvil
proved the rule that moves walls (put the wall in the pool). chisel puts
exactly ONE wall in the pool -- closer_cleo, the 1364-tier anchor -- with
vise's unsaturated margin reward, and asks a diagnostic question instead
of a product one: **can this line take a single game off that tier, and
what does the board look like when it does?**

The cost is known and accepted: one open-loop tape is exploitable, so the
tail roster (12 opponents, three of which -- spar x2 and enhanced/main --
are never trained against) prices the overfit. What we want out of it is
not a deliverable but an answer: if chisel beats cleo even 5% of the time,
the deficit is a production gap that scale can close; if it stays at 0%
with the margin term unsaturated and the opponent in the pool, then
something structural is missing and the next generation needs a different
idea, not more of this one.

## Suppression is not a separate lever: production is upstream of both terms (2026-08-22)

vise (margin term unsaturated: weight 3.0, scale 150k) and chisel (one
wall in the pool, same margin term) both ran ~40 iterations past their
forks, and the opponent's income did not budge:

    vise    it 81 -> 117:  ours 48.2k -> 47.6k,  opponent 118.9k -> 117.6k
    chisel  it  0 ->  36:  ours 42.2k -> 46.0k,  opponent 107.5k -> 107.3k

Our own income rose (chisel +3.8k in 36 iterations); **theirs is flat.**
So the premise behind vise -- that the second half of the margin is an
untapped lever -- is wrong in an instructive way. You suppress a market
opponent by OUT-SELLING them: pushing inventory into the products they
sell so their prices collapse. That requires production. The policy is
already selling everything it grows, so re-weighting the reward toward
margin cannot buy more suppression; it just buys more production, which
is what the numbers show.

**Corrected model: production is upstream of both terms.** The -62k
deficit against cleo (we 44k, they 106k, and they earn 148k when left
alone) decomposes as "we suppress 42k already, and we need ~60k more of
our own output". There is no cheap second axis. What remains is the
anatomy gap itself -- 3-4 quadrants, 13-14 animals, ~60 crops, 5-6
revenue lines -- and the open question is how to grow production under
tape pressure, given that the two reward terms which grew it on the
barnyard diet (land value, base-priced capital credit) both fail when a
150k opponent crashes the prices those terms assume.

## The -62k is a PRICE gap, not a production gap (2026-08-22, anvil-samp probe)

Same policy (anvil-samp), same three seeds, weak opponent vs the 1364
tier, counting physical units sold and the price each fetched:

| | vs barnyard | vs closer_cleo |
|---|---|---|
| units sold | 3,324 | **4,407 (+33%)** |
| sale revenue | 299,703 | 276,757 (-8%) |
| **average unit price** | **90.2** | **62.8 (-30%)** |
| our final money | 37-59k | 19-37k |

**We produce MORE against the strong opponent and earn less.** The deficit
is price, not output. Per line:

| product | vs barnyard | vs cleo | price change |
|---|---|---|---|
| MILK | 552 u @ **141.3** | 578 u @ **49.5** | **-65%** |
| STRAWBERRY | 357 u @ 228.2 | 270 u @ 177.4 | -22% |
| WHEAT | 1,742 u @ 43.8 | 2,862 u @ 46.0 | **+5% (held)** |
| MELON | 159 u @ 178.9 | 143 u @ **225.6** | **+26%** |
| FERTILIZER | 514 u @ 69.2 | 554 u @ 65.4 | -5% |

cleo dumps milk and our **second-biggest line loses two thirds of its
price**, while wheat holds (the town's steady demand) and melon actually
pays MORE (cleo barely sells it). Our economy is dairy-heavy; that is
precisely the economy this tier destroys.

Two consequences, both testable:

1. **Product-mix adaptation is the missing behaviour.** The prices are in
   the observation, so the policy CAN see the crash -- but its production
   is committed days earlier (a cow bought on day 6 makes milk on day 20
   whatever the price), so the reallocation has to happen at BUILD time,
   not sale time. Against a fixed tape that is learnable.
2. **And the potential blocks it**: future animal/crop output is credited
   at BASE price, so under a milk crash the potential still says a cow's
   milk is worth 160 when the market pays 49. That is the third
   appearance of the base-price assumption, and this time it has a
   specific cost: the policy cannot see that dairy is the wrong economy
   against this tier. A mark-to-market production credit is the obvious
   A/B -- with the caveat that two previous repricing terms
   (execution-priced inventory, base-priced capital credit) both failed,
   so it gets its own arm and its own roster, inheriting nothing.

For the record, the top meta is diversified exactly where we are not:
w49 is strawberry 30% / milk 22% / wool 21%, k06 is fertilizer 32% /
wheat 18%. Ours is wheat 49% / milk 19% / fertilizer 16%.

## Ladder calibration: the three reads are indistinguishable (2026-08-22)

| submission | local roster | ladder trajectory |
|---|---|---|
| sower-it228 | 5/12, floor 20%, median 35.7k | 498 -> 544 -> 558 -> 568 -> **555** |
| harrow-samp | 7/12, floor 4%, median 47.2k | 593 -> 633 -> 607 -> **616** |
| anvil-samp | 7/12, floor 2%, median 53.0k | 627 -> **572** |

harrow and anvil are locally two tiers apart from the first submission
(7/12 against 5/12, a floor of 2-4% against 20%, +12-17k of median
income) and **on the ladder all three sit in one 550-620 band**, with
anvil currently BELOW harrow despite the better roster.

Two honest readings, and the repo already warned about the first:
CLAUDE.md's "a ranking against a field we wrote is not evidence about the
ladder" applies exactly here. The second is sample size -- 12 to 25 games
each, where a 50-game swing is ordinary noise (the project's own rule 7
was written for this). Neither read is usable for choosing between harrow
and anvil yet; what IS usable is that the first submission's 20% floor
did show up as the lowest of the three trajectories.

Consequence for the next choice: **stop treating small local roster gains
as ladder gains.** The next submission should wait for either a
qualitative change (a nonzero win rate against the 1364 tier) or a much
larger local gap than 7/12-vs-7/12.

## Observability is not the problem (2026-08-22, ruling out a class)

Before attributing the missing product-mix adaptation to the reward, the
cheaper explanation had to be ruled out: maybe the policy simply cannot
SEE the dumping. It can. `features_t._globals` already carries

    g[8:17]   the nine current market prices, normalised by base
    g[17:26]  market inventory deviation, (I0 - inv) / T

so both the price collapse and its cause (inventory piling above target)
are in every observation, every step. The 4,867-dim observation was never
the constraint.

That leaves the reward, which is exactly what ledger tests: the policy
sees milk trading at 49 and the potential tells it a cow's milk is worth
160. One class of explanation eliminated for the cost of one grep.

## What 2000 actually looks like on our own scale (2026-08-22, job 20274290)

Running the two tape-replay submissions that scored **2035.9** and
**2302.2** through the exact 12-opponent roster our arms are judged on:

| agent | ladder | BEATEN | income median | p05 | under 20k |
|---|---|---|---|---|---|
| **topline** | **2035.9** | **12/12** | **118,374** | **63,999** | **0%** |
| kawashigi-k06 | 2302.2 | 12/12 | 124,373 | 68,971 | 0% |
| anvil-samp (our best) | ~572-627 | 7/12 | 53,0 | ~23,2 | 2% |
| harrow-samp | ~607-616 | 7/12 | 47,2 | ~21,3 | 4% |

**A 2035-scoring agent beats every one of our twelve opponents --
including cleo, lena, bea and w49 -- and its FIFTH PERCENTILE income
(64.0k) is higher than our MEDIAN (53.0k).**

This replaces every estimate I have made about the distance to 2000, and
it is much larger than the one I gave last night:

    BEATEN          7/12  ->  12/12
    median income   53k   ->  118k   (2.2x)
    p05 income      23k   ->  64k    (2.8x)

My earlier "+18% of income" figure came from comparing LADDER-game
incomes (61k ours against a weak ladder field, 72k for the 2035 agent) --
same-field arithmetic on a field that is far softer than our roster. The
roster comparison is the honest one because it holds the opponents fixed,
and it says the gap is a **doubling**, not a nudge.

Two consolations, both real. First, the target is now a measurable
local number instead of a ladder guess: 12/12 and a 118k median, on a
roster we run in 45 minutes. Second, the 2035 agent is an open-loop
replay of a human team's plan -- it proves the ECONOMY is reachable on
this engine (118k median against our whole field), not that a policy
must be superhuman to get there.

## vise verdict: best cleo margin on record, worst generality (2026-08-22, job 20260939)

Unsaturating the margin term (weight 3.0, scale 150k) off anvil's trunk:
**closer_cleo -66,320 -- the smallest deficit against the 1364 tier this
project has recorded** (anvil -68.1k, harrow -70.0k), and lena -69.9k.
But main 44.8% (anvil 72.9%), grazier 55.2% (anvil 72.9%), w49 -78.6k,
**5/12**, income median 48.9k, floor 4%.

So the margin re-weighting does exactly what the trajectory suggested: it
buys production and pressure against the tapes it trains on, and pays for
it in the matchups that need adaptation. Same trade as byre and bourse
made on the barnyard diet, one tier up. The suppression half of the
objective remains, as recorded earlier today, not a separate lever.

## forge verdict: the best main number yet, and the seven-tape pool plateaus (2026-08-22, job 20258767)

Every tape-able wall in one pool (cleo, lena, bea, w03, k06, w10, w49),
376 iterations: **enhanced/main 75.0% [65.5, 82.6] +9,826 -- the best
reactive-matchup number this project has recorded** (anvil 72.9%,
threshing 68.8%, harrow 64.6%), grazier 84.4% (ties harrow's best),
barnyard 99.0% +23,456, ghosts 100/100. **7/12**, income median 51.0k,
floor 5%.

But the walls did not move further: cleo -70.6k (anvil -68.1k),
lena -77.2k (anvil -67.7k), bea -80.7k (anvil -69.3k), w49 -69.7k
(anvil -74.5k, threshing -66.3k). **Seven tapes is not better than five
on the walls -- it is better on the held-out reactive opponents.** With
pfsp spreading the sampling mass across seven 100-186k economies, each
individual wall gets less attention than it did in anvil's five-tape pool
(and anvil's own gap already showed the mechanism: the pool member gets
the gain).

So the tape-diet family has converged to a plateau: **five arms
(harrow, sheaf, threshing, anvil, forge) all land at 7/12 with medians
47-53k and floors 2-5%**, differing only in which axis they favour. The
calibration says 2000 needs 12/12 and 118k. More tapes, more pfsp and
more iterations at this scale are not going to close a 2.2x income gap --
the next generation needs a different lever, and the two candidates on
the board are the mark-to-market production credit (ledger, running) and
whatever chisel's single-wall attack reveals.

## chisel's answer: the deficit is proportional, not a missing behaviour (2026-08-22, job 20264848)

313 iterations against nothing but closer_cleo, with the unsaturated
margin term, and the diagnostic question -- can this line take a single
game off the 1364 tier? -- has an answer: **no. 0/96, still.** But the
numbers around that zero are the informative part:

    closer_cleo margin  -59,762   (best of any arm: anvil -68.1k, vise -66.3k)
    our income vs cleo  median 45,236, MAX 100,478
    cleo's income       median 111,791, MIN 51,107
    the closest game    we 18,211 vs cleo 51,107  (-32,896)

Three readings:

1. **The gap is proportional, not situational.** We earn ~40% of cleo's
   money on rich boards (100k against its ~140k) and ~35% on poor ones
   (18k against 51k). The closest game is not a near-miss on a board that
   suited us -- it is a poor board where both farms earned little and we
   still lost by 33k. There is no board type where we are close.
2. **Concentrating all training on one wall bought 8k of margin (-68k ->
   -60k) in 313 iterations and no wins.** The same recipe against five
   walls bought the same 7/12. So the ceiling is the recipe, not the
   attention allocation.
3. **And chisel is nonetheless the best all-round product we have**:
   7/12, main 71.9%, grazier 82.3%, income median **53,997**, floor
   **2%** -- the best median and floor of any arm, from a pool of exactly
   one opponent. Overfitting to one tape cost almost nothing measurable,
   which says the tapes are teaching a general economy rather than an
   exploit.

Taken with forge's plateau and the 2035-agent calibration (12/12, 118k
median), the conclusion is unavoidable and worth stating plainly: **this
generation's recipe tops out around 7/12 and a 50k median. Closing a
2.2x income gap needs a different idea, not more of this one.** The one
untested idea still on the board is ledger's mark-to-market production
credit; after that, the honest next moves are structural (a real
opponent model, or a search/planning layer at inference, or the CNN trunk
the capacity roadmap has been holding).

## ledger verdict, and the regularity behind four failures: a price-blind potential is a regulariser (2026-08-22, job 20269437)

Mark-to-market production credit (future crop/animal output at
min(market, base)) off anvil's trunk: **cleo -65,539** (second-best
recorded, behind chisel's -59.8k), and then the same collapse the other
repricing arms showed -- **main 36.5%** (anvil 72.9%, forge 75.0%),
**grazier 37.5%** (anvil 72.9%), w49 -86.7k (the worst on record),
**5/12**, median 48.8k.

That completes a set of four, and the pattern is now unmistakable:

| arm | change | trained-pool effect | held-out effect (main / grazier) |
|---|---|---|---|
| bourse | inventory at execution revenue | barnyard margin +31k | main 15.6%, grazier 0% |
| harvest | production at base x 1.0 credit | income fell 39.6k -> 32.6k | killed at iter 50 |
| vise | margin term unsaturated | **best cleo -66.3k** | main 44.8%, grazier 55.2% |
| ledger | production at min(market, base) | **cleo -65.5k** | main 36.5%, grazier 37.5% |

**Every attempt to make the potential more truthful about prices has cost
generality**, and always in the same place: the opponents we never train
against.

The explanation that fits all four: **the base-price valuation is a
regulariser.** It is a fixed yardstick that does not move when an
opponent dumps, so the economy the policy learns is invariant to who is
across the table. Feeding market prices into the potential injects the
opponent's behaviour into our own reward signal, and the policy duly
learns opponent-specific responses -- better against the pool it trains
on, worse against anything held out. Kilo's "deliberate simplification"
turns out to be load-bearing.

Practical rule, recorded: **price-dependent terms belong in the
OBSERVATION (where they already are -- g[8:17] prices, g[17:26] inventory)
and not in the potential.** The reward should describe what we want built;
the observation should describe what the market is doing. Four arms and
about twenty GPU-hours bought that sentence.

## longhaul: the control the plateau claim needs (2026-08-22, 12 links to ~1200 iterations)

Every "the tape-diet family plateaus at 7/12" verdict rests on chains of
300-400 iterations -- and chisel's own income slope had **not** flattened
when its chain ended at 313 (42k -> 51k, still climbing). So the claim is
underdetermined: it might be the recipe's ceiling, or it might be where we
happened to stop.

**longhaul** is that control: chisel's trunk, anvil's five-wall pool,
nothing else changed, **twelve links to ~1200 iterations** (roster
20284697). Two clean outcomes:

* still 7/12 and ~54k median at 3x the compute -> the plateau is a
  property of the recipe, and the remaining ideas (inference-time search,
  CNN trunk) are the only way forward;
* it moves -> every verdict in the last two days was measured too early,
  and the cheapest lever available was patience.

Running alongside the two action-layer arms (reaper: metered selling;
sweeper: metered selling plus the sell sweep), which share anvil's trunk
and pool and differ from it by one decode rule each. Three-point ladder
in flight: anvil (dump) -> reaper (meter) -> sweeper (meter + sweep).

## reaper verdict: metering wins the price and loses the matchups (2026-08-22, job 20289583)

Metered selling (floor 0.85 x base) as the single variable off anvil's
trunk: **6/12**, ghosts at record margins (+47.3k / +48.0k, the largest
this project has posted), grazier 81.2% +6,330, barnyard 96.9%, income
median 51.9k, floor 5%. Against anvil (7/12, main 72.9%, median 53.0k,
floor 2%): **main falls to 40.6%**, cleo -73.2k (anvil -68.1k), lena and
bea both worse, w49 -68.8k (better).

So the gate's finding was real but incomplete. Metering does raise the
realised price per unit -- that is arithmetic, and the training income
was consistently 1-2k above anvil's at equal iterations. What the roster
adds is the cost: **holding stock for a better price means holding stock,
and an opponent who competes for the same demand sells it out from under
you.** Against the tapes (open loop, never adapting) metering is free
money; against main and cleo it is inventory left on the shelf.

That is the same shape as every reward-side price experiment, arriving
from the action side: **price-aware behaviour helps against opponents who
do not react and hurts against opponents who do.** The regularity now
spans both halves of the design -- reward and action -- and the honest
summary is that our price sophistication is worth less than our
production. sweeper (metering plus the sell sweep) is still running and
its training income has been consistently BELOW reaper's, which fits:
sweeping sells the stock metering was holding.

## grange: the only production lever the regularity does not forbid (2026-08-22, jobs above)

Two things are now established by measurement. Production is what
separates us from the 1364 tier (they earn 2.5x on every board type, and
chisel's 313 focused iterations moved the margin 8k without a single
win). And price sophistication does not pay: four reward-side experiments
(bourse, harvest, vise, ledger) and now one action-side experiment
(reaper) all helped against open-loop tapes and hurt against reactive
opponents.

`--build-bonus` is the exception that fits both facts. It credits
structures, animals and crops **by count** against the 231k-season
anatomy curve, with no price anywhere in the term, so it cannot inject an
opponent's behaviour into our objective -- and the traced gap is exactly
count-shaped:

    animals   8   vs the ladder field's 13, k06's ~14
    quadrants 2   vs the field's 3 (50 tiles LOCKED all game)
    crops     42  vs the top meta's ~60 standing, ~177 seeds bought

granger.yaml has run this at 1.0 in every arm since gen-4. grange runs
**3.0**, single variable off anvil's trunk and pool. If the count credit
at triple weight does not move the build numbers, then the shaping term
is not what is holding production back and the remaining explanations are
structural (capacity, or search at inference).

## sweeper closes the three-point ladder: price sophistication is monotonically negative (2026-08-22, job 20284158)

The three-point ladder, same trunk (anvil), same five-wall pool, one
decode rule apart at each step:

| arm | selling rule | BEATEN | main | grazier | barnyard | median | floor |
|---|---|---|---|---|---|---|---|
| anvil | dump the holding | **7/12** | **72.9%** | 72.9% | 92.7% | **53.0k** | **2%** |
| reaper | meter to floor 0.85 | 6/12 | 40.6% | **81.2%** | 96.9% | 51.9k | 5% |
| sweeper | meter + sweep all lines | **5/12** | **27.1%** | 47.9% | 76.0% | 46.3k | 10% |

**Monotone, in the wrong direction, on every axis that involves a
reacting opponent.** Each increment of price sophistication cost roughly
13 points of main and 2-5 points of floor; sweeper even lost barnyard
down to 76%. Against the non-reacting opponents it is the reverse (ghost
margins peak at reaper/sweeper), which is exactly the signature of the
regularity now established six times over:

**price-aware machinery pays against opponents who do not adapt and costs
against opponents who do -- in the reward (bourse, harvest, vise, ledger)
and in the action space (reaper, sweeper) alike.**

The mechanism for the action side is concrete: metering means holding
stock for a better price, and a competitor sells the same product before
that price arrives. Holding is only free when nobody else is selling.

Practical consequence, recorded: **stop building price machinery.** The
remaining candidates are production (grange, running: count-based build
credit at 3x) and compute (longhaul, running: the same recipe at 1200
iterations). If both come back flat, the honest conclusion is that this
architecture tops out here and the next step is structural -- capacity or
inference-time search -- not another knob.

## THE OPENING WAS THE GAP: a 12-day scripted opening, zero training, +1 opponent and every wall 20-26k closer (2026-08-22)

The trajectory diff localised the deficit to the first twelve days (the
1364 tier reaches 3 quadrants / 14 animals / 37-61 crops by day 12; we
reach 1-2 / 8-9 / 16). Testing that needed no training at all: replay a
tier tape's first 288 steps, then hand the board to our own network.

| opponent | anvil | + cleo's 12-day opening | delta |
|---|---|---|---|
| barnyard | 92.7% +10,926 | **100% +37,244** | +3.4x margin |
| **spar berrybaron** | **10.4% -7,977** | **99.0% +15,443** | **the 8th opponent falls** |
| enhanced/main | 72.9% +6,262 | **99.0% +34,664** | +26pp |
| spar grazier | 72.9% +1,878 | 83.3% +18,483 | +10pp |
| ghosts | 100% +45k/+46k | 100% +54k/+55k | +9k each |
| closer_cleo | 0% **-68,087** | 0% **-42,248** | **+25,839** |
| ledger_lena | 0% -67,688 | 0% -43,999 | +23,689 |
| broker_bea | 0% -69,281 | 0% -43,335 | +25,946 |
| w49 | 0% -74,491 | 0% -52,299 | +22,192 |
| **BEATEN** | 7/12 | **8/12** | |
| income median | 53.0k | **64.4k** | +11.4k |
| p05 income | 23.2k | **39.6k** | +16.4k |
| games under 20k | 2% | **0%** | floor gone |

w49's opening gives nearly the same (8/12, median 64.0k, walls -45 to
-54k), so this is the tier's SCHEDULE paying off, not one tape's luck.

Three things follow.

1. **Our network is competent at the harvest and incompetent at the
   opening.** Given a farm it has never managed to build, it runs it well
   enough to add 11k of median income and erase the catastrophic tail
   entirely. Every arm since gen-4 has been spending its capacity
   re-deriving a capital-formation schedule that the library already
   contains.
2. **The remaining wall gap is the harvest, and it is smaller than we
   thought**: from the tier's own day-12 position they earn ~110k against
   us and we earn ~64k, so ~42k of the original 68k is post-opening play.
   That is now the well-posed target.
3. **This is the cheapest result of the entire project**: no GPU, no
   retraining, one export-time change. It also vindicates the 2035.9
   tape-replay submission from a new angle -- following a proven
   trajectory beats discovering one, and the correct use of RL here is to
   improve what happens AFTER the script, not to rediscover the script.

## The opening-length sweep, and what it says about our policy's value (2026-08-22)

Splicing cleo's first D days in front of anvil's network, D swept, four
opponents (one trained-against wall, two held-out reactive agents, and
the tier):

| D | barnyard | main (held out) | berrybaron (held out) | cleo | income median |
|---|---|---|---|---|---|
| 6 | 100% | 87.5% | 75.0% | -62,010 | 60.0k |
| 8 | 99.0% | 97.9% | 89.6% | -58,002 | 57.2k |
| 12 | 100% | 99.0% | 99.0% | -42,248 | 64.3k |
| 16 | 100% | 100% | 100% | -38,549 | 68.0k |
| **20** | **100%** | **100%** | **100%** | **-22,648** | **78.0k** |

**Monotone in D on every axis.** Every extra day of the recorded plan
replacing our policy makes us better. There is no phase of the game where
our trained policy is worth more than a replay of a human plan -- and the
sweep is, read literally, an interpolation between our agent and the tape
whose full replay scored 2035.9.

The useful reading is a decomposition. At D=20 the remaining deficit
against cleo is **-22,648 over the last ten days from cleo's own day-20
position** (banked: both seats at 35.7k, 3 quadrants, 14 animals). The
endgame arm trains exactly that and reproduced the number at iteration 1
(we earn 67.4k, they earn 91.1k). So:

    beat the 1364 tier over a season   = a 68k problem, 0/96 after five generations
    beat their last ten days from their own farm = a 23k problem, now being trained

Two supporting readings from the same day, both negative and both
consistent: **grange** (count-based build credit tripled to 3.0) sits at
44.5k at iter 132, no better than anvil's ~45k, so the shaping weight is
not what caps production; and **longhaul** (the same recipe at 1200
iterations) reads 49.6k at iter 312, so compute is not it either.
Neither shaping nor patience is the bottleneck -- **the trajectory is.**

## A calibrated answer to "what level is it": the spar field as an instrument (2026-08-22, job 20292544)

The 12-opponent roster cannot place an agent between 763 and 1287 because
our field has no rung there. The 30-agent `agents/spar/` field can, because
**we submitted nine members of that generator ourselves** and know their
ladder scores: 647, 700, 721, 729, 742, 749, 751, 759, 763 (mean 729).

Running two products across all 30, 24 seeds each (1,440 episodes each):

| | anvil-samp | hybrid-cleo12 |
|---|---|---|
| overall win rate | **33.0%** | **86.8%** |
| opponents beaten (CI > 50) | 10/30 | **28/30** |
| income median | 39,376 | **61,390** |
| p05 income | 24,137 | **44,471** |
| worst matchup | **0%** (three marketgarden lines) | **60%** |

**The instrument validates itself.** Elo from the field mean:
729 + 400·log10(0.330/0.670) = **606** for anvil, whose actual ladder read
is **572-627**. The same arithmetic gives hybrid-cleo12
729 + 400·log10(0.868/0.132) = **1056**.

So the estimate is **~1050 +- 150**, and the +-150 is not hand-waving:
the same submitted file scored 1363.7 and 1218.6 on two different runs.
Placed against everything this project has measured:

    2302 / 2035   full tape replays of other teams' plans
    1364 / 1287   closer_cleo (third-party) and our one-line change to it
    ~1050         hybrid-cleo12  <- scripted opening + our network
    763 ... 647   the best of our own generated agents (nine submissions)
    623 / 621     enhanced / barnyard
    627 ... 555   this RL line's three submissions

Caveats, all real: the spar field is our own reconstruction (though it
just predicted anvil's ladder score to within noise); the Elo step assumes
transitivity in a game this repo has documented as non-transitive; and the
first twelve days of the product are cleo's plan, not ours.

## SUBMITTED: hybrid-cleo12 (2026-08-22, user-authorised)

Uploaded 19.8 MB; **3 submissions remaining today** (the count includes a
collaborator's `Pure Python Agent v1`, 385.6, at 07:30 -- not ours and not
from this line). Active pair is now hybrid-cleo12 + that collaborator
submission, so anvil (592.3) rotates out.

What was submitted, stated plainly in the submission message itself: the
first twelve days (288 steps, 40% of the episode) replay closer_cleo's own
`_TRACE`; the remaining 60% is our trained multi-head policy at sampling
temperature 1.0. Pre-flight: mirror +0 [-764, +754], stress 28/28 with a
55.4ms worst turn, package unpacked and played $91,970 with
`get_last_callable` resolving to `agent`.

Calibrated expectation on record before the read arrives: **~1050 +- 150**,
from the spar-field instrument that predicted anvil's 572-627 as 606. If it
lands there it is the best result this project has produced outside of
whole-tape replays, and the first time the line clears 1000 -- with the
caveat, permanently attached, that the opening is not ours.

## grange verdict: tripling the count-based build credit changes nothing (2026-08-22, job 20289928)

`--build-bonus 3.0` (against granger.yaml's 1.0), single variable off
anvil's trunk, 309 iterations: **6/12**, barnyard 94.8%, grazier 82.3%,
main 46.9%, berrybaron 1.0%, walls cleo -68.2k / lena -68.6k / bea -68.8k
/ w49 -77.6k, income median 46.3k, floor 7%. Against its control (anvil:
7/12, main 72.9%, cleo -68.1k, median 53.0k, floor 2%) it is **slightly
worse on every axis**, and its training income never left the 44-46k band
that anvil occupied.

This was the last price-free production lever on the board -- the one
mechanism the "price machinery does not pay" regularity could not
forbid, aimed at a gap that is exactly count-shaped (8 animals vs 13,
2 quadrants vs 3, 42 crops vs ~60). Tripling its weight moved neither
the build numbers nor the roster.

Read together with longhaul (the same recipe at 1200 iterations, flat at
48-50k) and the opening sweep (monotone: every day of a recorded plan
substituted for our policy improves every axis), the conclusion is
narrow and well-supported: **the shaping term is not what caps our
production, and neither is compute. The policy's own trajectory is.**
The one arm still showing a slope is endgame, which works because the
problem was reframed rather than reweighted: given the tier's own day-20
farm, close their last ten days -- -23,784 at iteration 1, **-9,676 at
iteration 161, 59% of it gone.**

---

## 2026-08-22 · hybrid-cleo12 的天梯读数坐实了,并且换掉了"2000 = 118k"这把尺子

**读数**:705.9,12 局,4 胜 5 负(这批 9 局)——**输掉的比例已过三分之一,
按 `SUBMISSION_POLICY.md` 规则 7,这个分数是真实水平,不是还在爬的地板**。
它是 RL 线历史最高(此前 610.1 harrow),但仍在 700 档。

**首次把五发提交放在同一张天梯表上对齐(`ladder_episodes`,收入按胜/负分栏)**:

| 提交 | 局数 | 胜率 | 我方中位 | 对手中位 | 胜局:我/对手 | 负局:我/对手 |
|---|---|---|---|---|---|---|
| sower-it228 | 21 | 48% | 49,104 | 42,993 | 60,552 / 36,546 | 36,250 / 51,920 |
| harrow-samp | 11 | 45% | 61,828 | 49,278 | 62,774 / 20,256 | 57,948 / 70,076 |
| anvil-samp | 13 | 54% | 59,891 | 52,878 | 65,398 / 29,962 | 48,292 / 72,554 |
| **hybrid-cleo12** | 12 | 50% | **66,662** | **67,860** | 64,668 / **50,927** | 68,626 / 87,104 |
| **topline(2035.9)** | 94 | **79%** | **84,264** | 76,196 | 86,470 / **74,720** | 70,679 / 78,323 |

**三条读法,第二条是最有用的那条:**

1. **我方收入确实一路在涨**:49.1k → 61.8k → 59.9k → **66.7k**。脚本开局那
   一发是最高的,且它面对的场地也最硬(对手中位 67.9k,前三发只有 43–53k)
   ——**天梯按分数配对,分数越高对手越强,所以"胜率没涨"掩盖了实力在涨**。

2. **差距的最锐利表述在"胜局的对手收入"这一栏**:topline 赢的是**挣 74.7k
   的对手**;我们赢的是**挣 50.9k 的对手**。我们不是赢得少,是**只能赢穷板**。
   跨过 2000 需要的不是"多赢几局",而是**把能赢的对手收入线从 51k 抬到 75k**。

3. **修正我 08-22 上午的校准**:我当时说 2000 分 = 收入中位 118k。那是**本地
   12 对手花名册**的尺子(topline 在花名册上确实是 118,374)。**天梯场地远软
   于花名册**:同一个 topline 在真实天梯上只挣 84,264。天梯原生的表述是
   **在一个 76k 的场地里挣 84k(+8k 的相对优势)**,而我们现在是**在一个 68k
   的场地里挣 66.7k(−1.2k)**。两个数字都对,但**别再拿 118k 当天梯目标**
   ——它会让人以为要产能翻倍,实际需要的是 +26% 收入外加把对手压下去。

**连带确认了脚本开局的价值不是本地过拟合**:hybrid 在天梯上的收入比 anvil
高 6.8k,面对的场地却硬 15.0k。这是本地花名册结论(+11.4k 中位)在真实天梯上
的独立复现。


## 2026-08-22 · 把顶端磁带当**老师**而不是对手,量出了一条谁都没查过的缺口

五代以来我们只把 150k 的磁带当对手打,从没模仿过它们;而我们唯一的
kickstart 教师是 `barnyard`(约 40k)——对 2000 分的目标来说是错的教师。
AlphaStar / VPT / OpenAI Five 的共同起点都是**先监督模仿专家、再 RL**。
新工具两个:`rl/tensor_env/project_tape.py`(词表覆盖率)与
`rl/tensor_env/tape_labels.py`(把磁带编成逐步标签 + 四臂定位)。

**一、词表覆盖率(满 719 步,五条磁带)**

| 磁带 | 农夫 | 市场整单 | 市场首单 | 指令/回合 | 帮手 | 帮手/回合 |
|---|---|---|---|---|---|---|
| closer_cleo | 96.1% | 54.5% | 64.8% | 1.05 | 94.3% | 8.40 |
| ledger_lena | 75.8% | 35.2% | 38.9% | 1.64 | 95.8% | 9.17 |
| broker_bea | 75.8% | 36.2% | 43.7% | 1.58 | 95.9% | 9.23 |
| w49 | 86.5% | 64.8% | 69.7% | 0.86 | 96.8% | 8.17 |
| k06 | 95.7% | 56.6% | 66.6% | 1.25 | 97.2% | 8.62 |

帮手侧未覆盖的 op:**PICKUP 104–234、DROP 8–88、PLACE 13–50、
BUILD_PASTURE 9–13**(每局)。市场侧未覆盖的首单以 **SELL** 与
**BUY_PRODUCT** 为主,原因不是品类而是**数量**:顶端一次卖
**中位 4–7 个单位**(p90 10–19,最大 49–65),一局卖 159–523 次;
我们的词表只有"全卖"与"半卖"。他们一局买 **264–967 个单位的小麦**
(全是 `BUY_PRODUCT WHEAT`)——**这顺带推翻了我们"小麦周转是漏损"的诊断**
(granary 臂的前提):顶端买小麦的量是我们的四倍,漏的不是买,是买了不转化。

**二、决定性的定位:arm B(磁带自己的市场 + 标签驱动的农场)**

| 臂 | 第 6 天 | 第 12 天 | 第 18 天 | 第 24 天 | 第 29 天 | 终局 |
|---|---|---|---|---|---|---|
| A 全部我方 | 2 株 / 0 兽 | 3 / 0 | 6 / 0 | 4 / 0 | 2 / 0 | 1,122 |
| B +磁带市场 | 6 / 0 | 4 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 3,532 |
| D 全部磁带 | **18 / 6** | **38 / 14** | 58 / 14 | 48 / 14 | 37 / 14 | **155,344** |

**动物一只都没上场,尽管 arm B 里磁带自己的市场在第 0 步就买了 3 头牛。**
机制:**顶端是用帮手放置动物、用帮手建牧场的**(覆盖率表里 PLACE 13–50、
BUILD_PASTURE 9–13 全在帮手栏且全部未覆盖);我们的 `HAND_TASKS` 只有
8 项杂活,没有 BUILD、没有 PLACE。所以买回来的动物只能排队等**唯一的
农夫**去放——**农夫是我们建设产能的串行瓶颈,而顶端把它并行到 8–9 个帮手上**。

这条假设与本项目已知的两次最大跃升同型:帮手词表补 PLANT/FERTILIZE、
HIRE 连发帽 4→10,两者都是"顶端用帮手做的事,我们的帮手不会做"。

**三、必须自己纠正的一条:DRIVE 比值不是词表判词**

`tape_labels.py` 的 DRIVE 臂(用我们的选项执行磁带的意图)读数 0.0–8.5%,
初版输出把它解释成"词表是天花板"。**这个解释是错的,我撤回它。** 两个混淆:
(1) 我们的 `BUY_*` 选项**自带数量**(HIRE 一次雇 10、BUY_WHEAT 按畜群成批),
把磁带 275 条小额买单换成我们的大额选项会直接**把农场买破产**(w49 那臂剩 0 元);
(2) 队列化市场指令后更差(1,122 → 500),因为积压峰值 127 条、过期丢弃 338 条。
**我们自己训练的网络用同一套选项能挣 40–65k,所以词表显然不是 0.7% 的天花板。**
DRIVE 能支持的结论只有一条,而它已经写在第二节里:**磁带的分工方式在我们的
动作空间里无法表达**。

**记档规则**:一个仪器给出的读数低于**同一套代码里已知的下界**(我们自己的
策略),先怀疑仪器。今天这条差点被我写成"五代奖励工程都被动作空间锁死"的
大结论,而真相是我的标签坏了两处,真正的缺口只是帮手词表里的两项。

## 2026-08-22 · 实收单价:我们的卖法没问题,**卖的东西**不对(并撤回"数量表达不足")

`probe_price.py` 按引擎的定价方式精确计价每一笔卖单(卖 q 个从库存 I 起,
收入 = Σ price(i, I+k)),库存取自真实重放。对手统一为脚本 starter。

| 谁 | 单位 | 笔数 | 收入 | 实收/单位 | 单笔中位 |
|---|---|---|---|---|---|
| 磁带 cleo(155,344) | 1,223 | 231 | 189,572 | 155.0 | 4 |
| 磁带 k06(100,032) | 3,515 | 434 | 261,831 | 74.5 | 7 |
| anvil-samp(78,430) | 1,472 | 274 | 134,435 | 91.3 | 4 |
| chisel-samp(35,270) | 1,650 | 239 | 93,848 | 56.9 | 6 |

**撤回今天上午那条推断。** 我根据覆盖率表(市场整单只有 35–65% 可复现)推断
"我们只会全卖/半卖,顶端小批量卖,所以我们卖不出好价"。**实测两条都不成立**:
我们的单笔中位是 **4–6**,与顶端的 4–7 相同(反复半卖 + 已有的计量机制自然
composes 出小批量);我们的 MILK 实收 234/单位、STRAWBERRY 233/单位,与 cleo
的 244 / 241 持平。**卖法不是病灶。**

**病灶是产品组合。** 同板对比每品类的单位数:

| 品类 | cleo | anvil | 差额 × cleo 单价 |
|---|---|---|---|
| STRAWBERRY | 270 | 88 | **−182 × 241 = −43.9k** |
| MELON | 132 | 44 | **−88 × 249 = −21.9k** |
| WOOL | 164 | **0** | **−164 × 72 = −11.8k** |
| FERTILIZER | 236 | 236 | 0 |
| MILK | 230 | 213 | −4.0k |
| WHEAT | 191 | **891** | +700 × 38 = +26.6k(最便宜的品类) |

**收入差 189,572 − 134,435 = 55.1k,上表几乎逐项对上(−55k)。** 我们不是
少卖,是**多卖了全场最便宜的东西、少卖了最贵的三样,而且一根羊毛都没有**
(没有羊)。

**而那 891 单位小麦不是产出,是买进来又倒出去的。** 种子与饲料的采购账:

| 谁 | 买种子 | 买小麦(饲料) | 峰值作物 |
|---|---|---|---|
| cleo | WHEAT 68, STRAWBERRY 41, MELON 26 | 275 | — |
| k06 | WHEAT 138, STRAWBERRY 34, MELON 20, CARROT 15 | 495 | — |
| anvil | STRAWBERRY 41, MELON 10 | **1,126** | 草莓 31 + 甜瓜 9 = 40 |
| chisel | MELON 29, STRAWBERRY 2 | **1,298** | 甜瓜 15 + 草莓 2 = 17 |

引擎的 FEED **每只动物每天恰好吃 1 单位小麦**(参考引擎第 510 行),所以
8 只的畜群整季需要约 240 单位。**我们买了 1,126–1,298,再把 891–1,119 倒回
市场。** 原因是一行代码:`BUY_WHEAT` 的数量是 `max(5, 2 * herd)`,**从不减去
棚里已有的存货**,每按一次就再买 2×herd。granary 臂的 `WHEAT_FEED_CAP` 只
封了掩码(棚里超过 cap×herd 就不许买),**数量那一行没动**,所以周转被限幅
而没有消除。

**已开的实验**:`WHEAT_BUY_EXACT`(gen25 `feedcap`)把数量改成"补足两日目标
的差额",并在目标已满时把这个动作判为非法。这是**零训练 A/B**——权重、种子
全同,只有动作层这一个变量,所以它是纯 CPU 的(job 20295480,9 个对手 × 48 局
× 两臂)。

**记档规则(今天第二次用到)**:一个从覆盖率表推出来的机制假设,必须先在
真实重放上量一次才算数。我今天两次从"词表覆盖率低"推出错误结论——一次说
天花板在动作空间(实为标签坏),一次说卖不出价(实为组合不对)。**覆盖率
说的是"能不能说出这句话",不是"说出来值多少钱"。**

## 2026-08-22 · endgame 判词:换问题比换奖励有效(反向课程的立论依据)

**304 迭代,margin −23,784 → −7,697(收窄 68%),对 cleo 的胜率 0% → 14.1%。**

这是本项目**唯一一条有斜率的臂**。它和其他十几条臂的差别不在奖励、不在
算力、不在对手池,而在**问的问题**:它不从第 0 天开始,而是从 **cleo 自己
第 20 天的状态库**开始训练(`data/banks/cleo-0480.pt`)。

对照两条同期的阴性:
- **longhaul**(1200 迭代算力对照,同配方从第 0 天):it 572 仍然 50–52k、
  **胜率 0.000**、对手 119–121k。算力翻倍不动。
- **grange**(势函数权重 ×3):6/12,阴性。

**结论**:我们训练不出顶端经济,不是因为奖励说错了话或迭代不够,而是因为
**从第 0 天出发的策略永远走不到那个状态分布里去**,于是它在自己那 50k 的
盆地里被优化得很好。给它顶端的中局状态,同一套奖励、同一套算力立刻产生
斜率——这就是 backplay / 反向课程(Resnick et al.)的全部内容。

**已启动的主线**:`backplay-d16 → d12 → d8 → d4`,每段从上一段权重继续
(链 20294386..97,尾部花名册 20294398)。库已建好:第 4/8/12/16/20 天,
双方资金 405 → 683 → 10.2k → 21.7k → 35.7k。**最关键的性质**:如果走通,
最终产物**自己打完整局,不需要 hybrid 那段脚本开局**——那才是"用 RL 达到
2000",而不是"用别人的录音达到 700"。

## 2026-08-22 · 反向课程改成**累积**起始分布(以及第 0 天收尾段)

第一版课程是"平移"的:d16 段只从第 16 天开局。**这会逐段遗忘。** endgame 用了
304 迭代才把第 20 天从 −23,784 做到 −7,697;一个只有 255 迭代、又从不回访
第 20 天的 d16 段,会把迭代花在重新学回第 20 天上。

引擎的 step 计数器在整个批次里是**标量锁步**的,所以单个状态库不可能混不同
天数(库文件里 `step` 就是一个 int)。但 `--bank` **本来就接受逗号分隔的列表**,
环境每次 reset 随机抽一个库——所以抗遗忘不需要改代码,只需要传累积列表:

| 段 | 起始状态分布 | bank-frac |
|---|---|---|
| endgame(已完成) | 第 20 天 | 1.0 |
| d16 | 第 16、20 天 | 1.0 |
| d12 | 第 12、16、20 天 | 1.0 |
| d8 | 第 8、12、16、20 天 | 1.0 |
| d4 | 第 4、8、12、16、20 天 | 1.0 |
| **d0(新增 4 link)** | 第 4–20 天 **+ 一半真正的第 0 天开局** | **0.5** |

d0 段是整条链的目的:**产物必须自己打完整局**。hybrid 那条线(脚本开局 +
网络)本地已经很强——20 天开局对 starter 中位 118,460,比 12 天那发(已提交,
天梯 705.9)高 26k,其中 8.6k 是 endgame 训练带来的——但它有 **20/30 天是
第三方录音**,所以它回答的不是"用 RL 达到 2000"这个题。**两条线要分开记:
hybrid 是提交候选,课程是目标本身。**

诚实标注:d16 段的第 2、3 个 link 会在中途捡起这个改动(第 1 个 link 用的是
平移版)。它只增加状态覆盖、不改目标,而第 20 天的本事已由 endgame 段建立,
所以我没有重启它。

## 2026-08-22 · hybrid-endgame20:第一次在完整局里赢下那三堵墙

把 **endgame 训练过的网络**(304 迭代,从 cleo 自己第 20 天的状态库出发,
margin −23,784 → −7,697)接在 **cleo 自己 20 天的开局**后面。对照 `hyb-d20`
是**同一段开局 + 未训练的 anvil 网络**——开局相同、种子相同、对手相同,所以
差额恰好是 endgame 训练买到的东西。每臂 **1,152 局**(12 对手 × 48 种子 × 双席)。

| 对手 | hyb-d20 胜率 / margin | **hybrid-endgame20** |
|---|---|---|
| closer_cleo(池内) | 0.0% / −22,648 | **15.6% / −7,774** |
| ledger_lena | 1.0% / −21,849 | **15.6% / −6,150** |
| broker_bea | 1.0% / −22,261 | **16.7% / −6,377** |
| w49(未在任何池) | 0.0% / −33,576 | 0.0% / **−21,413** |
| enhanced/main | 100% / +54,112 | 100% / **+64,709** |
| barnyard | 100% / +56,553 | 100% / **+70,434** |
| **收入中位** | 80,934 | **94,835** |
| **p05** | 47,584 | **54,642** |
| 灾难局 <20k | 0% | 0% |

**这是本项目第一次在完整局里赢下 cleo / lena / bea**(此前每一条臂、每一次
花名册都是 0/96)。三堵墙的 margin 从 −22k 一齐收到 −6~−8k,而且 **w49 也
收窄了 12k,尽管它不在 endgame 的池里**——这是泛化,不是对池过拟合。

与校准锚点对比(topline,天梯 2035.9,同一套 12 对手花名册):

| | BEATEN | 中位 | p05 | 灾难局 |
|---|---|---|---|---|
| topline(2035.9) | 12/12 | 118,374 | 63,999 | 0% |
| **hybrid-endgame20** | **8/12** | **94,835** | **54,642** | **0%** |
| hybrid-cleo12(已提交,705.9) | 8/12 | 64,436 | 39,600 | 0% |
| chisel(此前最强纯网络) | 7/12 | 54,000 | ~23,000 | 2% |

**收入中位 64.4k → 94.8k(+47%),离锚点只差 23.5k。**

**必须挂在这条判词上的限制**:hybrid-endgame20 的**前 20 天(30 天里的 20 天)
是第三方录音**。它是提交候选,**但它回答的不是"用 RL 达到 2000"**。它证明的
是另一件更有用的事:**只要把顶端的中局状态交到网络手上,同一套奖励和算力就
能把那三堵墙打成 15% 胜率。**这正是反向课程赌的那件事,现在有了 1,152 局的
证据——所以课程那条链的先验从"值得一试"升级为"机制已验证,只剩能否把开局
也学会"。

## 2026-08-22 · 小麦 A/B 判词:小幅为正(+1,743),而且**否掉了我的"带宽"假设**

零训练 A/B,`WHEAT_BUY_EXACT`,权重/种子/对手全同,9 个对手 × 96 局 × 两臂:

| 对手 | 胜率 off → on | 收入中位 off → on |
|---|---|---|
| grazier(spar) | 72.9% → **88.5%**(+15.6) | 33,909 → 37,260 |
| barnyard | 92.7% → 95.8% | 57,030 → 62,154 |
| ledger_lena | 0% → 0% | 38,567 → **46,396**(+7,830) |
| closer_cleo | 0% → 0% | 43,028 → **49,551**(+6,523) |
| enhanced/main | 72.9% → 78.1% | 53,382 → 49,266(−4,116) |
| berrybaron(spar) | 10.4% → **5.2%**(−5.2) | 44,472 → 38,298(−6,174) |
| w49 | 0% → 0% | 43,010 → 40,284(−2,726) |
| **9 个对手均值** | **+2.1 点** | **+1,743** |

**结论:留着,但它不是杠杆。** 9 个对手里 6 个收入变好、3 个变差,均值 +1,743
——按本项目的分辨率(96 局分辨 10 点差距),这是"大概真实但很小"。

**它同时否掉了我提出的两个假设,两个都要撤回:**

1. **"周转在漏 27k"**——错。我按"891 单位 × 38/单位"算出的 27k 是**营收**,
   不是**损失**:买入推高价格、卖出压低价格,一次往返近似价格中性。真实价值
   就是这 +1,743。
2. **"市场头的槽位被小麦占满了,腾出来就能多买种子"**——错。小麦用量从 1,126
   降到 387(−65%)之后,`BUY_SEED` 的按压次数是 51 → 46(**下降**),草莓
   种子 41 → 35,作物峰值不变。**槽位不是稀缺资源,策略只是不想买种子。**

所以那 77.6k 的产品组合缺口(草莓 −43.9k、甜瓜 −21.9k、羊毛 −11.8k)必须
**正面攻**,不能靠腾带宽绕过去。

## 2026-08-22 · hybrid-endgame20 验收通过(提交与否归用户)

- **镜像**:胜率 44.8%,margin **+0**,CI [−574, +566] —— 席位公平。
- **压力**:**28/28 clean**,最坏回合 **77.1 ms**(预算 1000 ms)。
- **打包**:解包后 `get_last_callable` 解析到 `agent`,跑完整 720 步一局
  **$116,275**。快照在 `submissions/2026-08-22-hybrid-endgame20/`(20.3 MB)。
- 本地花名册见上一条判词:8/12,中位 94,835,p05 54,642,灾难局 0%。

**我不会自己提交。** 今天剩 3 个名额;如果要发,命令在
`submissions/2026-08-22-hybrid-endgame20/` 里。诚实标注要随附:**前 20 天
(30 天里的 20 天)是 closer_cleo 的录音**,MIT 覆盖其市场层,provenance 在包内。

## 2026-08-22 · 势函数按 base 计价是错的:794 局真实天梯价格给出的表

上一条判词说产品组合缺口必须正面攻。攻法找到了,而且它是**一个可以直接验证的
错误**,不是一个新启发式。

`ladder_episodes.prices` 里有本项目**所有 794 局真实天梯对局**的收盘市价。
和势函数用来给产量计价的 `kg_rules` base 价对比:

| 品类 | base | 天梯中位 | p25–p75 | 比值 | 势函数 |
|---|---|---|---|---|---|
| MELON | 250 | **22** | 4–43 | 0.09 | **高估 11.4 倍** |
| FERTILIZER | 100 | 16 | 8–30 | 0.16 | 高估 6.2 倍 |
| MILK | 160 | 66 | 1–229 | 0.41 | 高估 2.4 倍 |
| WHEAT | 25 | 52 | 46–55 | 2.06 | 低估 2.1 倍 |
| STRAWBERRY | 120 | 201 | 55–257 | 1.68 | 低估 1.7 倍 |
| TOMATO | 60 | 87 | 77–100 | 1.45 | 低估 1.4 倍 |
| EGG | 50 | 63 | 58–68 | 1.26 | 低估 1.3 倍 |
| CARROT | 35 | 42 | 41–42 | 1.20 | 低估 1.2 倍 |
| WOOL | 200 | 218 | 5–242 | 1.09 | 大致正确 |

**机制**:商店消耗作物的速度超过两个农场的供给(整局作物库存都在 I0 **以下**,
所以作物价高于 base),而动物产品与肥料堆在 I0 **以上**。这是 SHOPS 机制与
产出速率决定的,**与对手无关**——本地一局的实测(hybrid-endgame20 对 cleo)
给出同样的方向:草莓库存 9,915 / 实价 197,牛奶 10,044 / 实价 68。

**为什么这解释了我们的行为**:势函数给一块甜瓜地 **750**、一块草莓地 **240**,
所以策略去种甜瓜——`chisel` 买了 **29 颗甜瓜种子、2 颗草莓种子**。而甜瓜在
天梯上每个单位 **22 元**。换成实价表后两者变成 **66 与 402**,偏好翻转
(门 R3 就是钉这个)。动物侧:一头牛的信用 512 → **211**,一只羊 507 → **552**
——**羊变得比牛好**,而顶端每局卖 164 单位羊毛,我们卖 **0**。

**为什么这不是 bourse / ledger / mtm 那四条阴性的重复**(ROADMAP §11:四个
价格相关的势函数项,四次失败):**这张表是静态的**,不读任何实时市场状态,
所以不可能把对手行为注入我们的目标;唯一的输入是"这块地产出什么品类"。
诚实标注写在源码里:MELON 的四分位距是 4–43、MILK 是 1–229,中位数是一个
双峰分布的中心。

`--realised-price W`(0 = base,1 = 实测表),`REALISED-PASS`
(R1 逐元判等 / R2 五个品类的比值全对 / R3 偏好翻转 / R4 对 W 单调)。
**assay 臂**从 chisel 权重起训(iteration 0 = chisel),链 20296292-96,
第一个 link 以 `afterok` 挂在门电池 20296291 上——门不过就不烧 GPU。

## 2026-08-22 · 种子批量 A/B:收入 +2,238 而胜率 −2.1 点(方向相反,先不采纳)

`BUY_SEED_<c>` 每个市场订单只买 **1 颗种子**,而市场头每回合只发 1 条,
所以**种植吞吐被锁在每回合 1 块地**——而 8–12 个帮手每人一回合能种一块。
顶端每局在种子上花 62–112 个市场槽位。`SEED_BATCH=6` 改成"按能下地的空地
成批买"(减去棚里已有种子,再受现金约束)。零训练 A/B,权重/种子/对手全同:

| 对手 | 胜率 off → on | 收入中位 off → on |
|---|---|---|
| closer_cleo | 0% → 0% | 43,028 → **50,688**(+7,660) |
| ledger_lena | 0% → 0% | 38,567 → **44,697**(+6,130) |
| starter | 100% → 100% | 68,766 → 74,802(+6,036) |
| grazier(spar) | 72.9% → **60.4%**(−12.5) | 33,909 → 39,318(+5,408) |
| barnyard | 92.7% → **86.5%**(−6.2) | 57,030 → 56,207(−823) |
| **9 个对手均值** | **−2.1 点** | **+2,238** |

**收入涨、胜率跌——这是个警号,不是胜利。** 对固定策略而言对手是确定性的,
所以"我们更富但输更多"只能来自棋盘交互:多种的地要多浇水,帮手的工时被
挤占。按 `CLAUDE.md` 的"看排名对钱"那条规则,方向相反的改动不该默认采纳。
**`SEED_BATCH` 默认保持 1。**

小麦那条是 +2.1 胜率 / +1,743 收入,和这条方向恰好相反,所以起了第三臂
**两个一起开**(`both-on`,数组 20296587,报表 20296607),四臂同基线对比。
若两者相消,则这两个动作层修正都不值得带上。

**顺带量清一条结构性上限**:顶端在 **18–41% 的回合发 2–10 条市场指令**
(cleo 有 19 个回合发满 10 条,lena 有 41% 的回合 ≥2 条),而我们的市场头
每回合只有 **1 条**。但总量只差 4.6%(cleo 752 条 / 719 回合),**所以它不是
主要限制**;失去的是时机上的集中度,这一点还没测。

**手写日程(`probe_ceiling.py`)的诚实结论**:它建到了 3 块地、6 只动物,
但作物停在 10–14 且最终破产。**一个差的日程证明不了词表不行**——这正是
DRIVE 那一臂被撤回的原因,所以我不把它当证据。它确认的是:顶端建设的**每个
部件在我们的动作空间里都单独可表达**(3 块地 1000/2000/4000、14 只动物走帮手
PLACE、37–61 株在种子预算内),做不到的是**同时把三样都融资出来**——那是
策略的经济学问题,不是词表缺口。

## 2026-08-22 · stockman 的行为读数:**帮手拿到了新词却不用**(以及为什么)

it 57 的检查点,一整局的动作统计:

| | 帮手 BUILD_PASTURE | 帮手 PLACE | 农夫 BUILD/PLACE | 畜群峰值 |
|---|---|---|---|---|
| stockman it 57 | **4** | **0** | 3 / 4 | **4** |

**新词几乎没被用,农夫仍然包办建设。** 机制是我事先量到一半的:

- **空牧场在势函数里恰好值 +0**(一株草莓 +240,一个带牛的牧场 +640),
  所以 **BUILD 是零梯度动作**;
- **PLACE 在没有空栏时是被掩码的**,所以链条中**有奖励的那一半从没有信号的
  那一半出发不可达**。

单靠熵探索要在同一局里先偶然 BUILD、再偶然 PLACE、再喂活它,才能拿到一次
正反馈——57 个迭代里一次都没成。

**修法不动奖励,动动作的组合**:`PLACE_BUILDS`——一个抱着动物、没有空栏的
帮手,**自己在最近的空地上建牧场**,于是整条链作为**一个动作**拿到 +640 的
动物信用。这和 `_with_stock` 把"走到棚、PICKUP、再执行消耗动作"复合成一个
选项是同一个手法。

**门 H4 是关键的那个**:帮手**只给 PLACE**、全程不发 BUILD 任务、农夫 PASS,
畜群还必须立起来——它们自己建了 6 个牧场、立起 6 只,设备与 CPU 逐元一致。

`penner` 臂(gen27)从与 stockman **相同的拓宽后 chisel 权重**起训,配方相同,
**只差这一处复合**。stockman 剩下的 3 个 link 已取消(它的假设已在 it 57 被
按我预测的方式否掉),GPU 让给这条;它的花名册改挂在正在跑的那个 link 上,
读到的是 it ~150 的检查点,仍是一个有效数据点。

**记档规则**:一个新动作如果它自己没有奖励、而它解锁的那个动作又被掩码,
**词表加了等于没加**。加动作时要同时问"这个动作的第一次正反馈从哪来"。

## 2026-08-22 · 动作层经济学四臂对比:采纳小麦,拒绝种子,**两个一起开会抵消**

同一份 anvil 权重、同一批 48 种子 × 双席、9 个对手,只换动作层常量:

| 臂 | 平均胜率 | vs 基线 | 收入中位 | vs 基线 |
|---|---|---|---|---|
| legacy(现行) | 38.8% | +0.0 | 43,028 | +0 |
| **wheat**(`WHEAT_BUY_EXACT`) | **40.9%** | **+2.1** | **46,396** | **+3,368** |
| seed(`SEED_BATCH=6`) | 36.7% | −2.1 | 45,736 | +2,708 |
| **both** | 39.1% | **+0.3** | 42,630 | **−398** |

**两个一起开把彼此抵消掉了**(+0.3 胜率 / −398 收入),尽管单独一个 +2.1、
另一个 +2,708 收入。已归档的"势函数项非线性叠加,组合包必须自己做 A/B"
这条规则,**对动作层的修正同样成立**——现在有了直接证据。

**决定**:采纳 `WHEAT_BUY_EXACT`(下一次提交的导出里打开),拒绝 `SEED_BATCH`,
拒绝组合。注意非传递性一如往常:`both` 对 enhanced/main 是四臂最高的 91.7%,
对 w49 却是最低的 36,817。

**未办事项**:`WHEAT_BUY_EXACT` 目前只有 CPU 侧;如果要**带着它训练**,必须
补设备孪生(`mrem` LUT),否则训练与部署的动作层不一致。零训练使用(导出时
打开)不需要它。

## 2026-08-22 · 课程的难度剖面:**前四天的状态库几乎没有用**,而这重述了差距

`train.py` 的 it 0 就是未训练策略从某个状态库出发的表现(d16 的 −24,627 就是
这么读的)。用 chisel 的权重、对 cleo、CPU、64 车道,对六个起点各跑 1 迭代:

| 起点 | 我方收入 | 对手收入 | margin | 相对第 0 天 |
|---|---|---|---|---|
| 第 0 天(完整局) | 47,076 | 101,925 | −54,849 | — |
| **第 4 天** | 49,730 | 109,291 | **−59,561** | **更难** |
| 第 8 天 | 53,700 | 108,444 | −54,744 | +105 |
| 第 12 天 | 58,781 | 105,007 | −46,226 | +8,623 |
| 第 16 天 | 60,442 | 98,915 | −38,473 | +16,376 |
| 第 20 天 | 66,530 | 87,132 | −20,602 | +34,247 |

**状态库恢复的是双方的状态**,所以"第 4 天"这一行的意思是:**把 cleo 自己
第 4 天的农场(19 株作物)交到我们手上,我们用剩下 26 天挣 49,730,而 cleo
在同一个起点上挣 109,291。** 第 4 天的库不但没帮上,还比从零开始更差
——因为 cleo 第 4 天只有 405 元,资本还没形成,而它的**计划**已经领先。

**这要求重述"开局是差距"这句话。** hybrid 的结论(把前 12/20 天换成录音,
收入 +26k)是对的,但它对的原因不是"我们不会开局",而是**我们不会复利**:
给同样的农场,我们把它经营成 50k,顶端经营成 109k。开局录音之所以有效,是
因为它同时替我们完成了**前 20 天的每一个经营决定**,而不只是"开局摆位"。

**对课程的两条推论:**
1. **有用的梯段是第 12–20 天**(+8.6k / +16.4k / +34.2k),**第 4、8 天两段
   几乎等于从零开始**。所以链里 d8、d4 两段(6 个 link)的边际价值最低。
2. 但**逐段继承确实在起作用**:d16 从 chisel 起是 −38,473,而从 endgame 权重
   继承后 it 0 是 −24,627、26 迭代后 −7,694。**同一个起点,继承把它从 −38.5k
   打到 −7.7k(收窄 80%)。** 所以课程的机制成立,只是最后 12 天的复利技能
   要靠 d12/d8/d4/d0 四段自己长出来。

**两条在跑的臂正好都打在这一点上**:`assay`(势函数按天梯实价——前 12 天的
现金引擎是小麦,2 天一收、天梯 52 元/单位,而策略被 base 价骗去种甜瓜,
天梯 22 元)、`penner`(帮手复合建栏——建设产能)。它们改的都是**复利速度**,
不是开局摆位。

## 2026-08-22 · d16 段判词 + 按剖面重排课程的 GPU 预算

**d16 收在 margin −7,688、对 cleo 胜率 11.4%**,起点 −24,627。它在 **it 29 就
到 −7,694**,之后 30 个迭代一直平在那里——**一段收敛后再加迭代不再有用**。

对照 chisel 从同一个第 16 天状态出发是 **−38,473**(难度剖面)。所以
**逐段继承把同一个起点从 −38.5k 打到 −7.7k,收窄 80%**,而只用了 26 个迭代。

**按剖面重排预算**(判词见上一条):第 4、8 天两段的 margin 与从零开始几乎
相同(−59,561 / −54,744 对 −54,849),边际价值最低;而 **d0 段的累积库本来
就包含第 4、8 天的库**(`seq 0 4 20` → 4/8/12/16/20),所以砍掉这两段
**不丢任何状态覆盖**。改成:

    endgame(第 20 天, 已完成) → d16(已完成) → d12(3 link) → d0(6 link)

d0 的起始分布是**一半真正的第 0 天开局 + 一半第 4–20 天的库**,即完整梯段。
省下的 6 个 link 给了最终那一段——它才是"产物自己打完整局"的地方。

**penner 的 A/B 基线已核实**:it 0 money **51,249**,与 stockman 的 it 0
逐位相同(两者都从同一份拓宽后的 chisel 权重出发),所以之后每一分差异
都只来自 `PLACE_BUILDS` 这一处复合。

## 2026-08-22 · 复合还不够:**帮手的任务每回合重新采样,所以多回合的行程几乎从不完成**

`penner`(PLACE 复合建栏)在 step 11 的读数:

| | 帮手 PLACE | 帮手 BUILD_PASTURE | 帮手 PICKUP | 农夫 PLACE / BUILD | 峰值畜群 |
|---|---|---|---|---|---|
| stockman it 57 | 0 | 4 | — | 3 / 4 | 4 |
| penner step 11 | **0** | 2 | **5** | 20 / 18 | 6–7 |

**取货支腿动了(PICKUP 5 次),放置一次都没完成。** 病因是这个动作空间的一个
性质,我此前没有把它算进去:**每个帮手的任务每回合都重新采样**,所以一趟需要
多回合的行程,只有在策略**连续多回合选同一个任务**时才会走完——而一个新的
PLACE 头概率大约 **2%**。帮手抱起一头牛,下一回合被派去浇水,然后抱着它走完
整局。

**修法与已有的"载重 ≥8 就 DROP"支腿同型:让手里拿着什么来决定,而不是被派了
什么。** `CARRY_COMPLETES`——抱着牧场动物的帮手,走到最近的空栏放下,没有空栏
就在最近的空地上建一个。

只处理**牧场动物**(牛/羊):鹅要鸡舍而帮手建不了,而真实天梯场地的畜群几乎
全是牛羊;这个限制让**所有帮手共用一个目标平面**,于是设备孪生是一个静态平面
且不需要认领(CPU 侧这条支腿用 `_goto_do`,和 FEED/FERTILIZE 的取货支腿一样
不占用池条目)。

门 `test_herd` 加上这条支腿后:H2 峰值畜群 6 → **7**、放置 6 → **9**;
H3 从农夫速率的 3.8 倍到 **4.4 倍**;H4(帮手只给 PLACE、不发 BUILD)自建牧场
6 → **9**、放置 6 → **13**。四个门全程设备与 CPU 逐元一致。

`penner` 已从 `init.pt` 干净重启(正在跑的那个 link 用的是没修的代码,
PLACE 必为 0,那 50 GPU 分钟本来就是废的)。

**记档规则(今天第二条同类)**:加一个动作时要问两件事——"它的第一次正反馈
从哪来"(零梯度问题),以及"**它需要几个回合才能兑现,而策略会不会连续选它**"。
在这个动作空间里,**任何跨回合的动作都必须自己完成,不能依赖策略的持续性。**

## 2026-08-22 · 帮手动作分布:hyb-eg20 已经"像顶端在操作",而 26% 闲置是**症状不是原因**

同板(对 starter / 磁带自身重放)的帮手动作占比:

| 帮手动作 | cleo | k06 | anvil(已提交) | **hyb-endgame20** |
|---|---|---|---|---|
| 走路 | 50.3% | 51.8% | 54.6% | 53.4% |
| **PASS(闲置)** | **6.8%** | 9.5% | **26.0%** | **9.9%** |
| WATER | 13.8% | 14.8% | 8.9% | 14.6% |
| HARVEST | 5.0% | 5.8% | 2.8% | 4.4% |
| FEED | 4.5% | 3.3% | **0.0%** | 2.8% |
| PICKUP | 3.9% | 1.7% | 0.0% | 2.5% |
| PLANT | 2.0% | 2.8% | 0.9% | 1.6% |
| FERTILIZE | 1.6% | 1.0% | 0.1% | 0.8% |
| 每回合帮手数 | 8.39 | 8.62 | 7.88 | 7.94 |

**第一条读法**:`hybrid-endgame20` 的分布**几乎就是 cleo 的**(闲置 9.9% 对 6.8%、
浇水 14.6% 对 13.8%、收获 4.4% 对 5.0%),而 anvil 的完全不是。这是 endgame
训练价值的**独立佐证**——它不只是收入高,它的**操作节奏已经是顶端的节奏**。
顺带:anvil 的帮手**一次都不喂食**,喂食全压在农夫身上(农夫 152 个回合在喂),
而顶端把它分给帮手。

**第二条读法要撤回我自己的推断(今天第五次)。** 我看到 anvil 闲置 26%,推断
病因是**掩码逐帮手独立计算**:8 个帮手都能合法选 WATER 而只有 1 块地缺水,
7 个 PASS。于是做了 `BUSY_HANDS`(家族被抢空就退回 AUTO 而不是 PASS)并零训练
实测——**闲置率只从 26.0% 掉到 24.4%**。AUTO 回退**也找不到活干**,所以那
24% 是**棋盘上真的没有活**:地都浇了、没有可收的、没有草。

**所以 26% 闲置是"农场太小养不住 8 个帮手"的症状,不是原因。** cleo 的 6.8%
来自它有 37–61 株作物和 14 只动物要照料;我们有约 40 株和 4–9 只。
**`BUSY_HANDS` 放弃,不占一次数组。**

**这条阴性把今天所有测量收成了一个故事**:闲置、收获率低、没有羊毛、甜瓜过重、
畜群只有 4–9 只、不会复利——**全部是"农场的规模与构成"这一件事的下游**。
所以现在**不该再加调度类的杠杆**,而在跑的两条臂正好打在两个上游成因上:
`assay`(该种什么——势函数把甜瓜高估 11.4 倍)和 `penner`(建得多快——
帮手复合建栏 + 抱着就放)。

## 2026-08-22 · 两份花名册:stockman 阴性坐实,longhaul 证明**算力会把策略做坏**

**stockman(帮手 BUILD+PLACE 两个独立任务,it 119,1,248 局)**

| | BEATEN 留出 | 训练过 | 收入中位 | p05 | 灾难局 |
|---|---|---|---|---|---|
| chisel(基线) | 7/10 | 0/2 | 54,000 | ~23,000 | 2% |
| **stockman** | **7/10** | **0/3** | **51,344** | 23,705 | 2% |

与 it 57 的行为读数完全一致:**新词没被用,所以唯一的净效果是把手部头从 10 拓到
12、稀释了策略**——中位低了 2.7k。四堵墙全部 0%(cleo −58,611、lena −68,648、
bea −68,209、w49 −68,179、k06 −75,129)。**这条阴性的价值在于它把病因钉死在
"零梯度 + 掩码链",而不是"词表不够"**;修好之后的 penner 正在跑。

**longhaul(1200 迭代算力对照,读到 it 629,1,152 局)**

| | chisel(313 迭代) | **longhaul(629 迭代)** |
|---|---|---|
| BEATEN 留出 | 7/10 | **5/10** |
| 收入中位 | 54,000 | **43,355** |
| p05 | ~23,000 | **17,817** |
| 灾难局 <20k | 2% | **8%** |
| enhanced/main | 71.9% | **39.6%** |
| grazier(spar) | 82.3% | **7.3%** |

**两倍算力把每一个轴都做差了。** 此前归档的判词是"算力是空杠杆"(它在训练
日志里一直平在 50–52k、胜率 0.000);花名册说得更重:**它不是平,是退化**。

机制:训练日志里的 money 是**对训练池**的,而池里三条磁带的胜率始终是 0.000
——**目标函数在一个它赢不了的池子上被优化了 629 个迭代**,于是策略朝"在必输
局里少输一点"的方向漂,把对留出对手的通用性交出去了(grazier 82.3% → 7.3%
是最刺眼的一格)。

**记档规则**:**长链必须有留出集上的早停**,否则"训练指标不动"会掩盖"留出
指标在掉"。我们的 `--probe-every` 是确定性探针,不是留出花名册;这次是花名册
才看见退化。今天这条和"算力不是杠杆"合并成一条更强的:**在一个你赢不了的池子
上加算力,会主动损害泛化。**

## 2026-08-22 · penner 行为读数(step 102):链条通了,**没有第三个结构性障碍**

| | 帮手 PLACE | 帮手 BUILD_PASTURE | 帮手 PICKUP | 农夫 PLACE / BUILD | 峰值畜群 |
|---|---|---|---|---|---|
| stockman it 57(两个独立任务) | **0** | 4 | — | 3 / 4 | 4 |
| penner 未修 step 11(只复合建栏) | **0** | 2 | 5 | 20 / 18 | 6–7 |
| **penner + CARRY_COMPLETES step 102** | **4** | **25** | 12 | **13 / 10** | 5–6 |

(三局合计,17,696 个帮手动作;收入 57.3k–62.3k,基线 chisel 中位 54.0k。)

**帮手第一次真的在放动物和建牧场**,农夫的建设份额从 20 次降到 13 次。所以
"帮手 PLACE 恒为 0"不是第三个结构性障碍,就是前两条:零梯度 + 跨回合行程
不自完成。两条都修掉之后链条通了。

**新的瓶颈是发起频率**:carry 支腿只在帮手**手里有动物**时触发,而拿到动物要
先被派 PLACE 一次——`widen_hands` 的新任务偏置是 **−4.0**(为了让 it 0 与
stockman 逐位相同,A/B 才干净),所以取货每局只有 4 次。它在往上走(0 → 4),
链上还有 3 个 link;**先不动偏置,保住基线**。如果 roster 显示畜群仍停在 5–6,
下一臂的变量就是这个偏置(−4.0 → −2.0),而不是再加动作。

## 2026-08-22 · assay 行为读数(it 149):作物组合按预测翻转,动物侧还没动

| | 买种子 | 峰值作物 | 畜群 |
|---|---|---|---|
| chisel(基线) | MELON 29, **STRAWBERRY 2** | MELON 15, STRAWBERRY 2 | 牛 8 |
| **assay it 149** | MELON 21, **STRAWBERRY 14** | **STRAWBERRY 12**, MELON 9 | 牛 7 |

草莓种子 **2 → 14**(7 倍),草莓已取代甜瓜成为主力作物——正是门 R3 钉的那个
偏好翻转(base 价下甜瓜 750 对草莓 240;实价下 66 对 402)。**势函数说的是真话,
策略就跟着改种什么。**

**动物侧尚未动**:仍是 8 头牛、**0 只羊**,尽管实价表给一只羊 552、一头牛 211。
候选原因:市场头的 `BUY_SHEEP` 从未被按过,而畜群构成不像作物那样由种子采购
间接决定——它需要策略直接选那个市场选项。若 roster 出来后羊毛仍是 0,下一步
是查 `BUY_SHEEP` 的掩码与被按频率(纯观测/掩码问题),而不是再改势函数。

训练日志的 money 仍平在 51.6k,但那是**对训练池**(三条不可战胜的磁带)的读数
——longhaul 的判词刚说明这个指标会掩盖留出集上的变化。**判词等花名册。**

## 2026-08-22 · 动物的价值次序在 base 与天梯之间**完全反转**,以及第六次撤回

**一、为什么我们的畜群是 8 头牛、0 只羊、0 只鹅**

| 动物 | 成本 | 产品 | base 价/天 | **天梯价/天** | 天梯回本 |
|---|---|---|---|---|---|
| SHEEP | 500 | WOOL 200 → **218** | 66.7 | **72.7** | 6.9 天 |
| GOOSE | 300 | EGG 50 → **63** | 50.0 | **63.0** | **4.8 天** |
| **COW** | 400 | MILK 160 → **66** | **80.0** | **33.0** | **12.1 天** |

**在 base 价下次序是 牛 > 羊 > 鹅;在真实天梯价下是 羊 > 鹅 > 牛。完全反转。**
一头牛在天梯上要 12 天回本,而动物通常在第 8–12 天才放下去——**它几乎不回本**。
我们的策略学的是 base 价的次序,所以买满一圈牛。这是 assay 那条判词的动物侧,
也解释了它为什么需要时间:要推翻三百多个迭代学来的"牛最好"。

**二、第六次撤回:`PLANT_BY_VALUE`——杠杆没有作用对象**

我看到帮手的 `PLANT` 选的是**持有最多**的种子(不是最值钱的),推断这是单一
栽培偏置:要种草莓,策略得先在仓里赢一场"数量竞赛",而市场头每回合只能买
一颗种子。于是做了按天梯价值选作物的规则(草莓 804、番茄 348、小麦 312、
胡萝卜 168、甜瓜 132),零训练 A/B。

**anvil 与 chisel 的四个种子上,两臂逐位相同。** 查清了原因:

- 作物**全是帮手种的**(农夫 PLANT 计数为 0;chisel 的帮手种了甜瓜 30、草莓 2),
  所以规则确实是决定性的;
- 但 **720 个回合里,仓库同时持有两种种子的只有 1 个回合**。规则最多能在一个
  回合上产生差异。

**所以真正的约束是市场头买什么种子,不是帮手怎么挑。** `BUY_SEED` 每个市场
槽位一颗,策略买了甜瓜 29 / 草莓 2,仓里就几乎从来没有可选项。**这反过来
加强了 assay 的地位:作物组合 100% 由 `BUY_SEED_<c>` 的按压决定,而按哪个由
势函数对该作物的估值决定** —— assay 改的正是这一处,它的草莓种子已 2 → 14。

`PLANT_BY_VALUE` 与 `BUSY_HANDS` 一样保留在默认关闭的标志后面,把测量写在
注释里,因为下一个看到"帮手按数量选种子"的人会有同样的想法。

**记档规则**:动作层的规则只在**有多个候选**时才有影响力。改规则前先量一次
"这条规则每局真正被调用、且候选多于一个的回合数"——今天这个数是 **1**。

## 2026-08-22 · 1,588 份真实天梯农场记录:分档的是**收获效率**,不是建设

`ladder_episodes.our_digest / their_digest` 里每一局都有逐日的资金/畜群/帮手
轨迹、土地数、首块地日期、买卖明细——**双方都有**,即 794 局对局共 **1,588 份
真实农场记录**。按终局收入分档:

| 档 | 收入中位 | 畜群@15 | 土地 | 首块地 | 资金@15 | 卖草莓 | 卖羊毛 | 卖甜瓜 |
|---|---|---|---|---|---|---|---|---|
| 前 10% | 120,772 | 14 | 3.0 | 7 | 21,360 | **270** | **164** | 120 |
| 中 40–60% | 68,975 | 12 | 3.0 | 7 | 14,284 | 138 | 120 | 114 |
| 后 10% | 29,940 | 12 | 3.0 | 9 | 8,664 | **35** | **39** | 114 |

**三条反直觉的读数:**
1. **畜群构成三档完全相同**(买牛 8、羊 6、鹅 0)。**没有人买鹅**,尽管鹅的
   天梯日产值(63/天)是牛(33/天)的近两倍、回本 4.8 天对 12.1 天——整个
   场地集体否决了鹅,这本身是信息。所以"牛是最差动物"的算术为真,但**畜群
   构成不是分档的原因**。
2. **土地三档都是 3.0 块**,首块地第 7–9 天。**建设也不是分档的原因。**
3. **甜瓜成交量与收入完全不相关**(120/114/114)。甜瓜不是有害,**只是不是杠杆**。

**分档的是草莓(270 → 35,7.7 倍)与羊毛(164 → 39,4.2 倍)。**

## 而我们的缺口在**收获**,不在种植

把我们自己的天梯农场对上场地前 10%:

| | 收入 | 土地 | 首块地 | 畜群@15 | 资金@15 | 草莓 | 羊毛 | 买羊 |
|---|---|---|---|---|---|---|---|---|
| 场地前 10% | 120,772 | 3.0 | 7 | 14 | 21,360 | 270 | 164 | 6 |
| anvil(纯 RL) | 59,891 | 2.0 | 10 | 6 | 14,405 | 98 | **0** | **0** |
| **hybrid-cleo12** | 66,662 | **3.0** | **7** | 11 | **24,594** | 96 | 114 | 6 |

hybrid-cleo12 靠脚本开局在**土地、首块地、资金@15、羊、羊毛**上都追平了前 10%
(资金@15 还更高),**只剩草莓 96 对 270**。

**每颗种子的产出**才是病灶:

| | 买草莓种子 | 卖草莓 | **单位/种子** |
|---|---|---|---|
| 场地前 10% | 37 | 270 | **7.3** |
| 场地后 10% | 14 | 35 | 2.6 |
| **anvil** | **54** | 98 | **2.0** |
| hybrid-cleo12 | 38 | 96 | 2.3 |

**anvil 买的草莓种子比前 10% 还多(54 对 37),每颗只榨出 2.0 个单位对他们的
7.3。** 种植时机也不是原因:hyb-eg20 的草莓种植日与 cleo 完全相同(41 株、
中位第 11 天、p90 13),浇水/收获频率也几乎相同(14.6%/4.4% 对 13.8%/5.0%)。

**同一批地的三方对照(同板,对 starter):**

| 谁在收这 41 株草莓 | 草莓单位 | 单位/种子 | 收入 |
|---|---|---|---|
| cleo 自己 | **270** | 6.6 | 155,344 |
| **endgame 训练过的网(hybrid-endgame20)** | **206** | **5.0** | 118,442 |
| 未训练的网(hyb-d20) | 138 | 3.4 | 103,955 |

**训练买到的正是收获效率:3.4 → 5.0 单位/种子,把与 cleo 的差距合了一半。**
而收获效率恰好就是天梯前 10% 与后 10% 的分界线(7.3 对 2.6)。

**这是反向课程最强的论据**:它改善的东西,正是真实天梯上区分 120k 与 30k 的
那一件事;而 hybrid 之所以有效,是因为它把**收获窗口**也交给了录音——草莓从
第 10 天起每两天出一次,12 天的开局把整个收获期留给我们的网,20 天的开局只
留最后十天。

**下一条要查的**:收获效率的物理原因。浇水频率与收获频率都已追平,所以
剩下的候选是(a)收获的**时点**——持续产出作物有 max_held 上限,不及时收就
浪费后续周期;(b)帮手的收获**目标选择**是最近优先,可能反复走向同一区域。
两者都能在本地一局里数出来。

## 2026-08-22 · 收获效率的物理原因:**施肥让每次产出翻倍,而我们几乎不施肥**

从参考引擎读出持续产出作物的确切机制(`_daily_refresh_plants`,第 787–803 行):

- 产出事件在 `days_since_first % interval == 0` 时发生,**总共 `max_yield` 次**
  (草莓:第 10、12、14、16 天,共 4 次);
- 每次加 **1 个单位**,**若当天浇过水且在施肥期内则加 2**;
- `yield_units` 的上限是 `max_yield`(4),所以**不及时收,后续事件就撞上限浪费**;
- 第 `max_yield` 次产出后 `max_lifespan_step` 被设定,之后 `_decay_plants`
  每 2 步扣 1 点,**到期未收的产量会烂掉**,归零后变杂草;
- 另一条通道:`consecutive_unwatered >= 2` → **整块地立刻变杂草**。

**所以一株草莓的产出区间是 4(不施肥)到 8(施肥且每次都及时收)个单位。**
非持续作物(小麦/甜瓜)更极端:它们的 `yield_units` **只在产量窗口内浇水时
累积**,施肥同样翻倍——小麦不施肥上限是 3,施肥才是 6。

**同板测量(对 starter,seed 424242):**

| | 施肥动作 | 收获动作 | 卖出草莓 | **单位/种子** |
|---|---|---|---|---|
| chisel | **0** | 90 | 6 | 3.0 |
| anvil | **5** | 171 | 88 | 2.3 |
| **hybrid-endgame20** | **46** | 283 | 206 | **5.2** |
| cleo(1.6% × 6,039) | **≈97** | — | 270 | 6.6 |
| 场地前 10%(天梯) | — | — | 270 | **7.3** |

**施肥次数的排序(0 → 5 → 46 → 97)与每颗种子产出的排序(3.0 → 2.3 → 5.2 →
6.6)几乎一一对应**,而引擎机制正好解释它:施肥把每次产出事件从 1 个单位变
2 个,上界从 4 抬到 8。**前 10% 的 7.3 就是"施肥 + 及时收"的理论上限 8 附近。**

**一条要撤回的小推断**:我先看到"39 株草莓有 26 株变成杂草(67%)"就报了警,
但读完 `_decay_plants` 才知道**每株作物寿终都会变杂草**,所以那个比例大部分
是正常的,不能当旱死的证据。(hybrid-endgame20 的比例是 82% 而它的产出最高,
本身就说明这个指标不可用。)

**下一条杠杆是现成的**:`--fert-credit` 已在每条臂的配方里(granger.yaml 用
0.3),也就是说**施肥已经被计入势函数,策略却仍然只做 5 次**。所以下一臂的
单变量应该是把它**调高**——机制上的预期效果是作物产出最多翻倍,而作物是
天梯前 10% 与后 10% 的分界线。这条比再加动作或再加算力都便宜。

## 2026-08-22 · `IDLE_FERTILIZES`:单一对手说 +6,548,九对手说 −438(不采纳)

施肥的**机制**是真的(见上一条判词:每次产出事件 1 → 2 个单位)。但"让闲置
的帮手去施肥"这个动作层补丁**没有兑现它**。

零训练 A/B,同权重同种子。先看**只对 starter、4 个种子**:

| 臂 | 施肥动作 | 卖草莓 | 单位/种子 | 收入中位 |
|---|---|---|---|---|
| legacy | 6 | 62 | 2.9 | 77,700 |
| fert-on | **38** | 77 | **4.2** | **84,248(+6,548,4 个种子全部改善)** |

再看**九个对手 × 96 局**:

| 对手 | 胜率 Δ | 收入中位 Δ |
|---|---|---|
| grazier(spar) | **+12.5** | +2,892 |
| barnyard | +5.2 | +2,145 |
| starter | +0.0 | +690 |
| w49 | +0.0 | +951 |
| ledger_lena | +0.0 | −518 |
| enhanced/main | −2.1 | −2,146 |
| berrybaron(spar) | −3.1 | −2,272 |
| k06 | +0.0 | −2,548 |
| closer_cleo | +0.0 | **−3,136** |
| **均值** | **+1.4 点** | **−438** |

**对被动对手全是正的,对会反应的对手全是负的**——这正是已归档六次的那条规律
(价格相关的机器对不反应的对手有用、对反应者有害)。机制上讲得通:施掉的肥料
就是卖不掉的肥料,而多出来的草莓要卖进一个对手也在卖的市场。

**+1.4 点在 96 局的分辨率下不可解(档案:96 局分辨 10 点差距),不采纳。**

**方法论判词,今天最该记住的一条**:**单一对手 4 个种子给 +6,548,九对手给
−438,相差 7k,而且四个种子全部同向**——种子内部一致性**完全没有**告诉我
它会在别的对手上成立。`docs/VALIDATING.md` 早就写了"要在平衡子集上比较",
今天这条是它的一个昂贵实例:**我差点把 +6,548 当成结论。** 今后任何动作层
标志,**没跑过九对手数组就不算测过**。

**施肥这件事的正确做法仍在奖励侧**:`--fert-credit` 已在配方里(0.3),把它
调高是让**策略自己**决定何时施肥比卖肥料更值——而不是用动作层强制。那是下一
臂的单变量。

## 2026-08-22 · 训练买到的不是"学会施肥",是**照料吞吐**——而这三件事是乘性互补

问题:endgame 训练把每颗种子的产出从 3.4 抬到 5.0,是因为学会了施肥吗?
同一段 20 天开局、同一批地、同一批种子,只换网络(三个种子的中位):

| | 施肥 | 浇水 | 收获 | 卖草莓 | 单位/种子 | 收入 |
|---|---|---|---|---|---|---|
| hyb-d20(未训练的 anvil 网) | 37 | 774 | 238 | 138 | 3.5 | 103,955 |
| hybrid-endgame20(训练过) | **45** | **913** | **283** | **200** | **5.0** | **118,442** |
| 增幅 | +22% | +18% | +19% | **+45%** | **+43%** | +14% |

**答案是不。它三件事各多做约 19%,产出多 43%。** 引擎的机制解释了这个超线性:

- 没浇水 → **当天没有产出事件**;连续两天不浇 → **整块地变杂草**;
- 浇了水但不在施肥期 → 每次事件只有 **1 个单位而不是 2**;
- 不及时收 → `yield_units` 撞上限(4),**后续事件白费**;过期后
  `_decay_plants` 每 2 步扣 1,**存着的产量会烂掉**。

**所以浇水、施肥、收获是乘性互补,漏掉任何一环整个事件就折损。** 吞吐提高
19% 之所以能换来 43%,是因为它同时抬高了三个乘数。

**这条一次解释了三件此前分散的事**:
1. **`IDLE_FERTILIZES` 为什么失败**(上一条判词,九对手 −438):它只填三个
   乘性槽位里的一个,还要付出"肥料卖不掉"的代价。**单动作补丁打不动乘积。**
2. **为什么反向课程会继续付钱**:它改善的是**每回合的照料吞吐**,而吞吐在这个
   乘积结构里有杠杆。endgame 已经把 3.4 → 5.0,顶端是 6.6、场地前 10% 是 7.3。
3. **为什么 anvil 的 26% 闲置既是症状又要紧**:在小农场上没活干(症状),但在
   一个建起来的农场上,闲置就是直接的产出损失——hyb-d20 的产出动作占比 18.4%,
   训练过的是 21.7%,差的这 3.3 个百分点换来 43% 的草莓。

**对下一臂的修正**:我上一条判词写的"下一臂调高 `--fert-credit`"**不够好**
——它只抬一个乘数。正确的单变量是**抬高整个照料三件套的吞吐**。势函数里
已有的 `WATER_STRESS`(未浇水扣分)是三者里唯一被点名的;`--fert-credit` 抬
第二个;而"及时收"目前**完全没有信号**(收获只在钱到账时才被间接奖励,而
`SHED_DISCOUNT 0.9` 反而让棚里的存货比现金便宜)。**最便宜的单变量是给
"撞上限的产量"一个惩罚项**:一块 `yield_units == max_yield` 的地,它下一次
产出事件必然浪费——这个量在观测里已经有,而它是纯物理的、与对手无关。

## 2026-08-22 · 第六条臂 `furrow`:同一个旋钮,从未测过的配方

**天梯上 100% 的场地都有 3 块地**——前 10%、中间、后 10% 三档全部是 3.0 块,
首块地第 7 天(前/中)或第 9 天(后)。**我们的纯 RL 产物只有 2.0 块,而且第 10
天才买第一块。** 势函数给一块地 `LAND_VALUE = 300`,而 iter-160 普查测出每块
地约 **5,000** 的下游作物信用;地价本身只有 1000 / 2000 / 4000。

`--land-value` 只测过一次(**plowman,1500,barnyard 食谱**,6/12),而那一代
**每一条 barnyard 食谱的臂都是 5–6/12,不论修的是什么**。档案里最强的规律是
**"食谱决定一切"**,所以同一个旋钮在**磁带食谱**下是一个未测的变量,不是重复。

`furrow` = chisel 权重 + 磁带池 + `--land-value 2500`,其余与 assay / gleaner
完全相同。**不需要新代码**——这个旗标从 plowman 起就在,而 `land_value=300`
就是门在钉的逐元默认值。

**为什么这条值一个 GPU 名额**(按今天的检查清单过一遍):
- (a) 它不是"新动作",不存在零梯度/掩码链的问题;
- (c) 它每回合都在势函数里生效,不需要"候选多于一个";
- (e) 它抬的不是乘性三件套里的一环,而是**乘积的定义域**——多一块地就是多
  25 格可种植、可放牧的面积,三个乘数同时有更多对象;
- 它是纯物理量(拥有的象限数),不读市价,所以不属于已归档的四条价格阴性。

判据同样是 HELDOUT 与"土地数是否到 3、首块地是否提前到第 7 天"。

## 2026-08-22 · 反向课程**不向前迁移**:它把开局做坏了(主线的中心假设被推翻)

反向课程的全部前提是"从富的中局状态学到的技能会向前迁移到早期"。**这可以直接
测**:`train.py --iters 1` 且**不挂状态库**,it 0 就是"这份权重从第 0 天打完整局"
——第 0 天基线 −54,849 就是这么读的。对 cleo、64 车道、CPU:

| 权重 | 我方收入 | 对手收入 | margin | 熵 |
|---|---|---|---|---|
| chisel(从没见过状态库) | **47,076** | 101,925 | **−54,849** | 13.25 |
| backplay-d16 | 33,298 | 119,068 | **−85,770** | 7.58 |
| **backplay-d12** | **29,398** | 119,892 | **−90,494** | 7.79 |

**它不但没有迁移,还把整局收入做低了 37%,margin 恶化 35.6k。** 熵从 13.25 塌到
7.79——策略在状态库的分布上变得非常确定,而那份确定性在第 0 天是错的。

**机制:灾难性遗忘,而且是我的设计缺陷。** 我把起始分布做成了**累积**的
(第 d..20 天,判词见 08-22 "反向课程改成累积起始分布"),这解决了段与段之间的
遗忘——d16 因此 26 个迭代就追上了 endgame 用 304 个迭代达到的水平。但**没有
任何一段包含真正的第 0 天开局**:库只有第 4/8/12/16/20 天,而第 4 天的库里
cleo 只有 405 元、什么都还没建,所以它**替代不了**第 0 天。于是四段训练下来,
开局这一段从未被采样过,直接漂掉了。

**这同时解释了另一个此前的读数**:难度剖面里"第 4 天的库比第 0 天还难"
(−59,561 对 −54,849)——不是库没用,是**第 0 天这件事本身没有任何一段在练**。

**已经做的调整**(d0 段还没开始,所以来得及):
- 原计划 6 link、`--bank-frac 0.5`(一半真第 0 天)→ 改为 **8 link、
  `--bank-frac 0.35`(65% 真第 0 天开局)**,因为它现在要从 −90.5k 把开局
  重新学回来,比原计划的工作量大;
- 初始权重仍取 **d12**(不是 chisel):d12 从第 12 天出发是 −8.2k 而 chisel 是
  −46.2k,**晚段的本事很值钱,要保住**。所以 d0 段的形状就是"学出来的 hybrid"
  ——用真第 0 天开局把前 12 天补回来,同时用库把后 18 天钉住。

**设计规则入档(下一次做课程必须遵守)**:**反向课程的每一段都必须保留一部分
真正的初始状态开局**(`bank_frac < 1` 全程),否则最终阶段要从一个比起点更差的
开局重新学。文献里这条是标准做法,我只做对了一半(把库做成累积的),漏掉了
"库里必须包含 day 0"——而 day 0 没有库,所以只能靠 `bank_frac`。

**判据也要改**:此前每段的判词看的是"该段起点的 margin"(d16 −7,688、
d12 −8,152),那个数**只说明它在库的分布上变好了**。真正要盯的是**第 0 天整局
的 margin**,而这条判词就是它第一次被测出来。d0 段的花名册是最终判据。

## 2026-08-22 · 课程的价值和它的失败要分开算:**晚段本事值 +11.8k**

上一条判词说课程不向前迁移(从第 0 天打整局比 chisel 差 35.6k)。但那不等于
课程没用——它学到的东西**localised 在第 12–30 天**,而这可以直接兑现:把
`backplay-d12` 的权重接在**同一段 12 天 cleo 开局**后面,与已提交的
`hybrid-cleo12`(天梯 705.9,同一段开局 + anvil 的网)逐对手对比。每臂 **864 局**:

| 对手 | hybrid-cleo12 | **hybrid-d12net** | Δ |
|---|---|---|---|
| closer_cleo | −42,248 | **−24,354** | **+17,894** |
| ledger_lena | −43,999 | **−24,682** | **+19,317** |
| broker_bea | −43,335 | **−25,409** | **+17,926** |
| w49(未在任何池) | −52,299 | **−37,259** | **+15,040** |
| enhanced/main | 99.0% / +34,664 | **100% / +45,479** | +10,815 |
| grazier(spar) | 83.3% / +18,483 | **91.7% / +33,899** | +15,416 |
| berrybaron(spar) | 99.0% / +15,443 | **100% / +28,949** | +13,506 |
| barnyard | +37,244 | **+50,410** | +13,166 |
| starter | +77,773 | +68,975 | **−8,798** |
| **收入中位** | 61,152 | **72,959** | **+11,807** |
| **p05** | 37,354 | **47,259** | **+9,905** |

**除 starter 外每个对手都变好,四堵墙各收窄 15–19k,而这只是 d12 段的第 66 个
迭代。** 唯一的退步(starter)正是可预期的**池专化**:d12 全程 `bank-frac 1.0`、
只对着 cleo/lena/k06 三条磁带从库里训练,**它从没见过弱对手**。

**所以当前的账是这样的:**
- 课程**确实**产出了更强的晚段网络(比已提交产物的网络多 11.8k 中位);
- 课程**没有**产出更好的开局(第 0 天整局 −90.5k 对 chisel 的 −54.8k);
- 两者合起来的形状,就是 d0 段要学的东西:**保住晚段、把前 12 天补回来**。
  d0 段已按此重建(8 link、`bank-frac 0.35` 即 65% 真第 0 天开局,初始权重取
  d12 而不是 chisel)。

**顺带一条方法论**:hybrid-d12net 对 **starter 单一对手**是 71,800 对 83,828
(更差),对九个对手是 **+11.8k 中位**(更好)。**又一个"单一对手会给出反向
结论"的实例**——今天第二次,前一次是 `IDLE_FERTILIZES`(+6,548 对 −438)。
检查清单第 (d) 条再确认一遍。

## 2026-08-22 · 四个 hybrid 对齐:**课程的晚段训练 ≈ 八天录音**

同一批 9 个对手(864–1,152 局/臂),把开局长度与网络质量交叉:

| 臂 | 开局 | 网络 | 收入中位 | p05 | cleo | lena | w49 |
|---|---|---|---|---|---|---|---|
| hybrid-cleo12(已提交 705.9) | 12 天 | anvil | 61,152 | 37,354 | −42,248 | −43,999 | −52,299 |
| **hybrid-d12net** | 12 天 | **课程 d12(66 迭代)** | **72,959** | 47,259 | −24,354 | −24,682 | −37,259 |
| hyb-d20 | **20 天** | anvil | 74,801 | 44,408 | −22,648 | −21,849 | −33,576 |
| **hybrid-endgame20** | **20 天** | **endgame(304 迭代)** | **88,810** | **50,512** | **−7,774** | **−6,150** | **−21,413** |

**两项贡献几乎等量,而且可加**:
- 12 天开局下把网络从 anvil 换成课程网:**+11,807**;
- anvil 网下把开局从 12 天延到 20 天:**+13,649**;
- 20 天开局下把网络换成训练更久的 endgame:**+14,009**。

**最有用的是这条等价关系:课程网 + 12 天开局(72,959)≈ 未训练网 + 20 天开局
(74,801)。也就是说,课程的晚段训练大约值"八天第三方录音"。**

这给纯 RL 线一个可计量的目标:**hybrid-endgame20 的 88,810 = 20 天录音 + 304
迭代的晚段训练。若 d0 段能把"八天录音"那一份换成自学的开局,我们就能在
不用任何录音的情况下站到 74k–89k 之间**——而 chisel 从第 0 天出发的整局中位
是 47k。要补的正好是这个差。

**提交候选确认**:`hybrid-endgame20` 在这张表上每一项都最好(中位 88,810、
p05 50,512、四堵墙 −6k~−21k),它仍是唯一通过全部验收的候选。诚实标注不变:
20/30 天是录音,所以它是提交候选而**不是**"用 RL 达到 2000"的答案。

## 2026-08-22 · 第七条臂 `seedling`:**正向课程(局长)**,反向课程的互补方向

反向课程教不了开局(判词:从第 0 天整局 −90,494 对 chisel 的 −54,849,因为没有
任何一段采样过第 0 天)。互补的方向是**把局缩短,让开局成为唯一的问题**。

**为什么取 15 天**:1,588 份真实天梯农场记录里,最强的单一分档量是**资金@15**
——前 10% 是 **21,360**,我们是 **14,405**(中间档 14,284,所以我们**就在中位**)。
15 天局的终局回报直接就是这个量。

**为什么它不会教出"清仓"**:Ng 型 shaping 逐步是 `γφ(s') − φ(s)`,望远镜求和到
**`γ^T φ(s_T) − φ(s_0)`**,所以**截断处的势能在回报里**。目标于是是"**建出最好的
第 15 天局面**",而不是"第 15 天前把东西卖光"。这一点是这条臂能不能成立的关键,
所以写在这里。

**为什么它不可能有遗忘问题**:后面没有东西可忘。这正是反向课程失败的那个机制的
反面。

**顺带的效率**:15 天局是 360 步而不是 719,所以同样算力下**每单位时间的对局数
翻倍**,而开局这一段被采样的次数是原来的 4 倍(2 倍对局 × 每局全部在开局)。

**形状**:A 段 3 link,`--steps 361`(15 天);B 段 3 link,`--steps 720`(整局),
从 A 段权重继续。这是标准的正向课程/局长退火。起点仍是 chisel 权重,所以 it 0
与其余六条臂可比。**不需要新代码**——`--steps` 从一开始就在。

**判据**:B 段尾部的 12 对手花名册(HELDOUT),外加**第 0 天整局的 margin**
(要好过 chisel 的 −54,849,那是反向课程做不到的那一格)。

### 补记(同日,烧掉 GPU 之前核实承重假设)

`seedling` 的整条臂压在一句话上:"截断处的势能在回报里,所以短局优化的是建设
不是清仓"。我是从 Ng 公式推的,在提交之后回去**读了代码核实**,结果对了一半:

**对的那一半**(`trl_env._finish_step`):`r = (γ·φ(s') − φ(s)) / shape_scale`
**每一步都算,包括最后一步**;`done` 时的 `win_bonus` / `margin_bonus` 是
**相加**(`r = r + ...`)而不是替换。所以第 15 天局面的势能确实进了回报。

**错的那一半**:`granger.yaml` 带 **`win_bonus: 1.5`**,而它比较的是
**终局谁的现金多**。**1364 档在早期故意持有更少现金、更多资产**——cleo 第 12 天
只有 **10,195** 元而它的农场值好几倍。所以在 15 天局里这一项**恰好在推向不投资**,
正是这条臂要避免的那个畸变。

**已改**:A 段(15 天)加 `--win-bonus 0 --margin-bonus 0`,**只留 shaping**,
目标就是纯粹的"最好的第 15 天局面";B 段(整局)恢复,因为第 30 天现金**就是**
比分。

**记档规则**:**一条臂如果压在某个奖励项的行为上,提交后要回去读那段代码。**
今天这一次核实同时确认了一半、推翻了一半,而被推翻的那一半会把 3 个 GPU link
花在优化"第 15 天现金比对手多"上——那与目标相反。

## 2026-08-22 · 累积状态库 ≈ **4.6 倍算力**(设计的第一份直接证据)

同一段 20 天 cleo 开局,只换后面的网络,同一批 9 个对手(432–1,152 局/臂):

| 网络 | 训练 | 中位 | p05 | cleo | lena | bea | w49 | main |
|---|---|---|---|---|---|---|---|---|
| anvil | 未见过状态库 | 74,801 | 44,408 | −22,648 | −21,849 | −22,261 | −33,576 | +54,112 |
| **d12** | **累积库(第 12/16/20 天),66 迭代** | **90,788** | 50,016 | **−7,273** | **−4,917** | **−5,252** | −21,963 | **+67,878** |
| endgame | 单点(只第 20 天),**304 迭代** | 88,810 | **50,512** | −7,774 | −6,150 | −6,377 | **−21,413** | +64,709 |

**66 个迭代的累积库训练与 304 个迭代的单点训练打平**:中位、cleo/lena/bea 三堵墙、
enhanced/main 上 d12 略优,p05 与 w49 上 endgame 略优——差距在 432 局的分辨率内
属于**持平**。**所以累积状态库大约值 4.6 倍算力。**

这是这个设计(今天引入,判词"反向课程改成累积起始分布")的**第一份直接证据**;
此前只有间接的一条(d16 用 26 个迭代追上 endgame 用 304 个迭代达到的 margin)。
**机制**:单点库只教"从第 20 天的那一种局面继续",累积库教"从第 12–20 天的
任意局面继续",后者的状态覆盖宽得多,而这个游戏的晚段本来就是同一套照料动作
在不同规模的农场上重复——覆盖宽度直接换成样本效率。

**对交付物的影响**:`hybrid-d12net20`(20 天开局 + d12 网)中位 **90,788**,是
本项目**目前最强的本地产物**,略高于已打包的 `hybrid-endgame20`(88,810)。而
**d12 段还有 2 个 link 没跑完**,所以链尾重建一次这个 hybrid 会更强。**若用户
批准提交,应该等 d12 链尾再打包一次**,而不是发现在这个 66 迭代的中间检查点。

**但它仍然不是"用 RL 达到 2000"的答案**:20/30 天是录音。这条判词量的是
**课程设计的效率**,不是纯 RL 的进度。

## 2026-08-22 · d0 段劈成初始权重的 A/B(**晚段便宜、开局贵**这个不对称性)

今天两条测量合起来说明我给 d0 段选的初始权重可能是错的:

| 从哪个权重出发 | 第 0 天整局 margin | 从第 12 天出发的 margin | 修好的代价 |
|---|---|---|---|
| **chisel** | **−54,849(好)** | −46,226(差) | **晚段便宜**:d16 用累积库 **26 个迭代**从 −38.5k 到 −7.7k |
| **backplay-d12** | −90,494(差) | **−8,152(好)** | **开局贵**:迁移测试说明它只会退化,要从 −90.5k 重学 |

**晚段便宜、开局贵**,所以理应从**开局更好**的那个出发,让 `bank-frac 0.35` 里那
35% 的库把晚段快速补回来。**但这是推断,不是测量**——所以把原本 8 个 link 的
d0 段劈成两条各 4 个,**唯一的变量就是初始权重**:

- `d0-chisel`(链 20300332-45,花名册 20300346)
- `d0-d12`(链 20300347-52,花名册 20300353)

两条都是 `--bank-frac 0.35`(65% 真第 0 天开局)+ 累积库(第 4–20 天),独立的
run 目录以免共用 `latest.pt`。**判据是第 0 天整局的 margin**,加上 HELDOUT 花名册。

**这条 A/B 本身也是一条判词**:如果 `d0-chisel` 赢,那么"反向课程"在这个环境里
的正确用法不是"逐段后退",而是**"从一个会开局的策略出发,用库把晚段补上"**
——那和 hybrid 的结构完全一致,只是晚段那一半是学出来的而不是录音。

## 2026-08-22 · 把两个 2000+ 锚点放上同一把尺子:**候选的预期是 ~1,500,不是 2000**

`calib-topline` 与 `calib-kawashigi-k06` 的花名册一直在仓库里,但我从没在
**与候选完全相同的 9 个对手**上重算过它们。现在算了:

| 产物 | 天梯 | BEATEN | 中位 | p05 | cleo | lena | w49 |
|---|---|---|---|---|---|---|---|
| kawashigi-k06 | **2302.2** | **9/9** | 114,620 | 64,642 | **+18,713** | **+17,120** | **+10,195** |
| topline | **2035.9** | **9/9** | 110,960 | 61,408 | **+17,891** | **+13,778** | **+7,733** |
| hybrid-d12net20 | ? | 5/9 | 90,788 | 50,016 | −7,273 | −4,917 | −21,963 |
| hybrid-endgame20 | ? | 5/9 | 88,810 | 50,512 | −7,774 | −6,150 | −21,413 |
| hybrid-cleo12 | **705.9** | 5/9 | 61,152 | 37,354 | −42,248 | −43,999 | −52,299 |

**2000 分的两个锚点是"把那三堵墙打赢"**(margin +17.9k / +13.8k / +7.7k,BEATEN
9/9)。我们最好的候选**仍然输给它们**(−7.3k / −4.9k / −21.9k,BEATEN 5/9)。
**所以差距不是中位 90.8k → 111k(+22%),而是每堵墙 25–30k 的翻转。**

**预登记的天梯预期**(用两个真实天梯锚点对中位收入插值,斜率 0.0267 与
0.0299 分/元):

| 候选 | 中位 | **预期天梯** |
|---|---|---|
| hybrid-endgame20(已打包) | 88,810 | **1,444 – 1,532** |
| hybrid-d12net20(待重打包) | 90,788 | **1,497 – 1,591** |

**要 2000 分,中位需要 104,500 – 109,600。** 我们差 14–19k。

**这把尺子比我此前用过的都可靠**:两个锚点是**真实提交的真实天梯分数**,而且是
**同一批对手、同一套 eval 代码**测出来的中位。此前我两次估错(一次说这一代能到
900–1300 实际 550–630;一次用"场地相对收入"绕了一圈),原因都是尺子不是同板的。
**记档规则:预测天梯分只用"同板测过的真实天梯锚点"插值,不用任何间接论证。**

**对提交决定的影响(仍归用户)**:候选值一发,但它**不会到 2000**——预期 ~1,500。
它相对已提交的 705.9 是 **+800 左右**,这本身是这条线迄今最大的一步;但要跨过
2000,需要的不是"再打磨这个 hybrid",而是**把三堵墙从 −7k 打到 +18k**。
而那正好是六条在跑的臂共同瞄的东西(收获效率 2.0 → 7.3 单位/种子就是这 25k)。

## 2026-08-22 · 差距是**每天约 2,100 元的均匀损失**,不是某个阶段的失败

把"录音天数"当自变量,同一批 9 个对手的中位收入当因变量(不需要新算力,全部是
已有的花名册):

| 产物 | 录音天数 | 我们的网打几天 | 中位 | 相对全录音的损失 | **每天** |
|---|---|---|---|---|---|
| topline(全录音) | 30 | 0 | **110,960** | — | — |
| hybrid-d12net20 | 20 | 10 | 90,788 | 20,172 | **2,017** |
| hybrid-endgame20 | 20 | 10 | 88,810 | 22,150 | **2,215** |
| hybrid-d12net | 12 | 18 | 72,959 | 38,001 | **2,111** |
| hybrid-cleo12(已提交 705.9) | 12 | 18 | 61,152 | 49,808 | **2,767** |
| chisel(纯 RL) | 0 | 30 | 47,076 | 63,884 | **2,129** |

**每天的损失几乎是常数(2,017–2,767),与我们的网接手多少天无关。**

**这纠正了我自己 08-22 上午的框架"开局就是差距"。** 如果病灶在开局,那么让我们的
网只打最后 10 天时,每天的损失应该**明显低于**打 30 天时——因为它避开了病灶。
实测是 2,017 对 2,129,**几乎一样**。所以病灶**在每一天**,而不是在某个阶段。

**这正是"浇水/施肥/收获乘性互补"那条判词预测的形状**:一个每天都成立的照料
吞吐缺口,会给出一个每天都成立的收入缺口。而 hybrid 之所以有效,不是因为它
"修好了开局",而是因为**它把那些天从我们手里拿走了**——每拿走一天省 2,100。

**训练确实在压这个日损失**:同为"最后 18 天",anvil 的网是 2,767/天,课程 d12
的网是 2,111/天(**降 24%**);同为"最后 10 天",endgame 2,215 → d12 2,017。

**目标于是有了最紧的表述:**
- **hybrid 路线(20 天录音)**要到 2000,日损失要从 2,017 降到 **600–1,100**;
- **纯 RL 路线(0 天录音)**要到 2000,日损失要从 2,129 降到 **约 0–200**
  ——也就是"每一天都打得和天梯顶端一样好"。

这两个数把"还差多少"从"中位再多 14–19k"翻译成了**每天再多挣 900–2,100 元**,
而收获效率 2.0 → 7.3 单位/种子正是这个量级的来源。

## 2026-08-22 · **重要纠正:`sold` 与我的价格探针都在数"下单量"而不是"成交量"**

引擎会把一条 SELL 截到棚里实有的存货。直接量"每步棚里减少多少"(实际离开棚的量),
对 topline 一局:

| 品类 | SELL 下单量 | **实际离开棚** | 倍数 |
|---|---|---|---|
| FERTILIZER | 1,708 | **342** | **5.0×** |
| STRAWBERRY | 227 | **140** | 1.6× |
| MELON | 120 | **30** | 4.0× |
| WHEAT | 1,037 | 886 | 1.2× |

**而且不同 agent 超额下单的倍数不同**,所以任何用下单量做的跨 agent 比较都不成立。
`ladder_episodes` 的 `sold` 字段与我的 `probe_price.py` **都有这个缺陷**。探针已修
(改为量棚的流出),`sold` 字段是历史数据、不能重算。

### 必须撤回的四条

1. **"收获效率:我们 2.0 单位/种子,前 10% 是 7.3"**——按**实际成交**重算:

   | 产物 | 草莓种子 | 实际成交 | **单位/种子** | 终局中位 |
   |---|---|---|---|---|
   | topline(2035.9) | 34 | 140 | **4.1** | 79,945 |
   | hybrid-d12net20 | 41 | 115 | 2.8 | 55,185 |
   | hybrid-cleo12(705.9) | 35 | 96 | 2.7 | 45,235 |
   | **chisel(纯 RL)** | 30 | 137 | **4.6** | **50,917** |

   **chisel 的榨取率是全场最高的(4.6 > topline 的 4.1),而它的钱最少。**
   **榨取率与收入不相关。** 那条"2.0 → 7.3 就是那 25k"的推论一并作废。
2. **"分档的是草莓(270→35)与羊毛(164→39)"**——这两列是下单量,不能跨 agent 比。
3. **"品类缺口:化肥 +22.8k"**——化肥 1,671 是下单量,实际约 342。
4. **"训练把草莓从 138 抬到 206(+45%)"的那个数字**——是下单量;**但结论本身
   用修好的探针复现了**:实际成交 **124 → 189(+52%)**,钱 103,955 → 118,442。

### 站得住的(全部与"量"无关,或已用修好的工具复现)

- **所有的钱**:margin、中位、p05、BEATEN、天梯分——货币量不受影响;
- **每天约 2,100 元的均匀损失**(10/18/30 天都是 2,017–2,129/天)——基于终局钱;
- **同板天梯尺子与 ~1,500 的预期**——基于中位钱;
- **794 局的实价表**(MELON base 250 / 天梯 22 等)——那是**价格**不是量;
- **动作计数**:施肥 5 / 46 / 97,浇水与收获占比,闲置 26% 对 6.8%——是动作;
- **引擎机制**:乘性互补、撞上限浪费事件、连续两天不浇变杂草——是源码;
- **天梯普查里的结构列**:三档都是 3.0 块地、都是 8 牛 + 6 羊、资金@15
  21,360 对 14,405、首块地第 7 天——这些是**棋盘上的计数**,不是下单量。
  **"我们 0 只羊"也站得住**(那是畜群计数)。

### 记档规则(今天最贵的一条)

**在这个引擎里,"下单"与"成交"是两个量,差最多 5 倍。** 任何用成交量做的论证,
必须用**棚的流出**或引擎的账来量,不能用动作里的数量字段——包括
`ladder_episodes.sold`。**凡是我今天用 `sold` 或旧探针得出的量化结论,默认作废,
除非上面列在"站得住"里。**

对在跑的臂的影响:`gleaner`(`--harvest-urgency`)的动机从"榨取率 2.0 对 7.3"
降级为"**收获时点在势函数里没有任何项,而引擎确实在撞上限时丢弃产出**"——后者
是源码事实,仍然成立,所以这条臂保留;但它不再是"最有证据的那一条"。

## 2026-08-22 · 又一处相关量当杠杆:**资金@15 是相关量,第 15 天的局面才是靶子**

我上一条把 `seedling` 说成"证据最硬"时,用的动机是"资金@15 是 1,588 份记录里最强
的分档量(前 10% 21,360,我们 14,405)"。**那个动机是错的**:

| | 终局 | 资金@15 | **畜群@15** | 帮手@15 | **土地** | 首块地 |
|---|---|---|---|---|---|---|
| 场地前 10% | 120,772 | 21,360 | **14** | 10 | 3.0 | 7 |
| 场地中 40–60% | 68,975 | 14,284 | 12 | 11 | 3.0 | 7 |
| 场地后 10% | 29,940 | 8,664 | 12 | 10 | 3.0 | 9 |
| **hybrid-cleo12(705.9)** | 66,662 | **24,594** | 11 | 10 | **3.0** | **7** |
| **anvil(纯 RL)** | 59,891 | 14,405 | **6** | 10 | **2.0** | **10** |

**hybrid-cleo12 的第 15 天现金比前 10% 还多(24,594 对 21,360),土地相同、首块地
同日、帮手相同、畜群 11 对 14 —— 第 15 天的局面基本已经是顶端的 —— 而终局只有
他们的 55%。** 所以**资金@15 是相关量,不是杠杆**;顶端第 15 天现金少,是因为钱
都投出去了。这与 `win_bonus` 是同一个陷阱(今天第二次)。

**而这一条把两条看似矛盾的判词调和了**:
- 对 **hybrid 路线**,第 15 天局面已达标,所以剩下的全部差距就是**我们的网每天
  约 2,100 元的经营损失**(它接手 18 天 × 2,100 ≈ 38k,与终局差 54k 同量级);
- 对 **纯 RL 路线**,第 15 天局面**是真的差**:畜群 **6 对 14**、土地 **2.0 对 3.0**、
  首块地 **第 10 天对第 7 天**。

**所以 `seedling` 的正确动机是"第 15 天的局面",不是"第 15 天的现金"** ——
而它优化的恰好就是 **φ(第 15 天)**(势函数把资产计入,而 `win_bonus` 已被去掉),
所以**臂的设计是对的,只有我的动机陈述要改**。靶子写清楚:**畜群 6 → 14、
土地 2.0 → 3.0、首块地 10 → 7**,这三项都是棋盘计数,不受"下单量"污染,而
hybrid-cleo12 证明它们**是可达的**。

**记档规则(今天第二次)**:一个量在**场地内**能分档,不等于它是**我们**的杠杆
——要先检查"我们在这个量上已经追平甚至超过时,结果有没有跟着变"。资金@15 与
榨取率都是这样被否掉的。

## 2026-08-22 · **势函数在惩罚买地**,而我给 furrow 选的值不够(改前抓到)

`BUY_LAND` 从**第 0 步就合法**(掩码只要 `money >= price`,而起始现金 3000、
第一块地 1000),三个产物的实际行为:

| | 首次合法 | 实际按下 | 终局象限 |
|---|---|---|---|
| chisel(纯 RL) | 第 0 天 | 第 **11** 天(一次) | 2 |
| anvil | 第 0 天 | 第 **10** 天(一次) | 2 |
| **topline(2035.9)** | 第 0 天 | **第 6 天、第 11 天** | **3** |

**所以土地的差距不是"买不起"也不是"不合法",纯粹是估值。** 算术:

| `LAND_VALUE` | 第 1 块(1000) | 第 2 块(2000) | 第 3 块(4000) |
|---|---|---|---|
| **300(现行)** | **−700** | **−1,700** | **−3,700** |
| 2500(我原本选的) | +1,500 | +500 | **−1,500** |
| **5000(普查测的下游价值)** | **+4,000** | **+3,000** | **+1,000** |

**现行的 300 让买地在 shaped reward 里是净负的**,所以策略拖到第 10–11 天才买一块、
再也不买第二块——**这是"农场冻结"机制往上一层**(判词 08-21:势函数给第 16 天的
牛 −584,策略于是停止投资)。

**而我原本给 `furrow` 选的 2500 不够**:第三块地要 4000,2500 下它仍是 −1,500,
而 topline 恰好买了第三块。已在链启动前改成 **5000**,那是 iter-160 普查测出的
下游作物信用,也是唯一让三块地全部为正的值。

**这条同时把我先前的降级判断纠正回来**:我因为"天梯三档都有 3.0 块地"把 furrow
降到 2 link,理由是"它是阈值不是杠杆"。但**我们只有 2.0 块**,而三档**全部**是 3.0
——所以我们在这个量上是**低于整个场地**的,包括后 10%。它仍留 2 link,但判据改成
**纯行为的**:两个 link 之后如果 `first_land_day` 降到 ~6 且象限到 3,就延长。

**记档规则**:一个势函数项的**数值**要用它要驱动的那笔交易的**价格**来定,不是
凭手感。300 对 1000/2000/4000 是净负的,2500 对 4000 仍是净负的——这两件事都可以
在写下旗标之前用一行算术看出来。

## 2026-08-22 · **班组平台期是势函数里的一个常数**,不是学习失败(第八条臂 `hirer`)

引擎每晚解雇全部帮手,所以班组每天早上按**斐波那契价**重买:1, 2, 3, 5, 8, 13,
21, 34, 55, 89, 144, 233。而势函数给每个帮手**一个平的 40**。

| 第 n 个帮手 | 工资 | φ 净变化 @40 | @250 |
|---|---|---|---|
| 1 | 1 | **+39** | +249 |
| 8 | 34 | **+6** | +216 |
| **9** | 55 | **−15** | +195 |
| 12 | 233 | **−193** | **+17** |
| 21 | 17,711 | −17,671 | −17,461 |

**平的信用对上上升的价格,必然有一个盈亏平衡班组数——这里是 8。** 十二人班组
一天工资 608,势函数只给 480,**净 −128**。

**而我们的产物实测跑 7.88–7.94 人/回合。平衡点是 8。差 0.1 人。**
顶端跑 **8.39–8.62 平均**,摘要里 **hands@15 = 10、hands@20 = 13**,工资照付。

**所以班组平台期不是学习失败,是这个常数。** 这和一小时前那条土地判词是**同型**
(LAND_VALUE 300 对地价 1000/2000/4000),规则也是同一条:**势函数项的数值要用
它要驱动的那笔交易的价格来定。**

**第八条臂 `hirer`**(gen30 `crew`):`--hand-value 250` —— 让十二人班组净为正
(第 12 个 +17),同时第 21 个仍是 −17,461,**不会放出无上限的班组**。门
`CREW-PASS`(C1 逐元 / C2 平衡点位置 + 上下界 / C3 线性且只碰帮手)。链
20301121-24 挂在门 20301120 的 afterok 上,花名册 20301125。

**为什么它可能是今天最强的一条**:帮手是那个**乘性三件套(浇水/施肥/收获)的
产能**,所以它是唯一"不改调度、只改工人数量就同时抬高三个乘数"的旋钮;而它的
证据是**算术精确预测了观测到的平台**(8 对 7.9),不是相关性。

`gleaner` 的额度让给了它(保留 1 个正在跑的 link + 花名册,判词仍会出)。

## 2026-08-22 · 势函数价格审计**全表**:动物从第 12 天起被惩罚,而 assay 会把我们推进一个没人测过的市场

`hirer` 与 `furrow` 是同一个模式的两个实例("信用对不上价格"),所以把策略必须
做的**每一笔交易**都算一遍。净 φ 变化 = 信用 − 价格;**负数 = 势函数在惩罚这笔交易**:

| 交易 | 价格 | 第 4 天 | 第 8 天 | **第 12 天** | 第 16 天 | 第 20 天 |
|---|---|---|---|---|---|---|
| 买 GOOSE | 300 | +160 | +80 | **+0** | −80 | −160 |
| 买 COW | 400 | +240 | +112 | **−16** | −144 | −272 |
| 买 SHEEP | 500 | +113 | +7 | **−100** | −207 | −313 |
| 种 WHEAT | 10 | +65 | +65 | +65 | +65 | +65 |
| 种 CARROT | 20 | +50 | +50 | +50 | +50 | +50 |
| 种 TOMATO | 50 | +70 | +70 | +70 | +70 | +40 |
| 种 STRAWBERRY | 100 | +140 | +140 | +140 | +80 | −40 |
| **种 MELON** | 80 | **+670** | **+670** | **+670** | **+670** | **+670** |
| 买土地(已判) | 1000/2000/4000 | −700 / −1700 / −3700 | | | | |
| 雇帮手(已判) | fib(n) | 第 9 个起为负 | | | | |

**第三处同型错误(新)**:**势函数从第 12 天起惩罚买任何动物**,而顶端的畜群@15
是 **14**、我们是 **6** —— 正好是需要从 6 加到 14 的那段窗口。作物则全程为正,
而 **MELON 的 +670 是所有作物里最大的**(天梯实价 22,这是 assay 要修的那个)。

注意 `capital_credit`(抬 ANIMAL_CREDIT)已经试过并失败(08-21:收入 39.6k → 32.6k,
50 迭代内杀掉),所以**"动物从第 12 天起为负"不能简单地靠抬系数解决**。

### 必须预登记的一条:assay 会把我们推进一个**没人供给过**的市场

同一张表在 assay 的天梯实价下:

| 动物 | 价格 | 第 4 天 | 第 8 天 | 第 12 天 |
|---|---|---|---|---|
| **GOOSE** | 300 | **+280** | **+179** | **+78** |
| SHEEP | 500 | +169 | +52 | −64 |
| **COW** | 400 | **−136** | **−189** | −242 |

**它会让策略完全停止买牛**(牛在天梯上确实最差:33/天、12.1 天回本)**并转向鹅**。
牛的次序修对了,但**鹅这一格靠不住**:真实天梯的**三档全部是 8 牛 + 6 羊 + 0 鹅**
—— **没有人养鹅**,而 EGG 的天梯中位 63 **正是在几乎没有供给的市场里测出来的**
(档案 08-21 早有一条:"蛋价生态位 107–149 无人养鹅")。**一个无人供给的价格,
撑不住我们去供给它。**

**所以 assay 的实价表分两类**:对**场地已经在供给**的品类(草莓、牛奶、羊毛、
小麦、甜瓜、肥料)它是可信的;对 **EGG 不可信**,因为那个价格没有被任何供给
检验过。**读 assay 花名册时的预登记判据**:如果它的畜群变成鹅为主,先查
**EGG 的实际成交价**(用棚流出法,不是下单量),而不是直接相信收入变化——
那会是"进入一个未测市场"而不是"修好了估值"。若成立,下一版的表应把 EGG 钳回
base(50),只保留有供给检验的那几格。

## 2026-08-22 · 逐日轨迹:动物那条判词是**对的**,但我们**养不住**畜群(新)

| 畜群(中位) | 第 5 天 | 第 10 天 | 第 15 天 | 第 20 天 | 第 25 天 | 第 29 天 |
|---|---|---|---|---|---|---|
| 场地前 10% | 5 | **12** | **14** | 14 | 14 | **14** |
| 场地中 40–60% | 5 | 10 | 12 | 12 | 13 | 13 |
| 场地后 10% | 4 | 6 | 12 | 13 | 13 | **11** |
| **hybrid-cleo12** | 5 | **12** | 11 | 10 | 10 | **8** |
| **anvil(纯 RL)** | 4 | **5** | **6** | 6 | 6 | 6 |

| 帮手(中位) | 第 5 天 | 第 10 天 | 第 15 天 | 第 20 天 | 第 29 天 |
|---|---|---|---|---|---|
| 场地前 10% | 4 | 11 | 10 | 12 | 10 |
| hybrid-cleo12 | 4 | 8 | 10 | 10 | 10 |
| anvil | **7** | 9 | 10 | 10 | 10 |

**三条读法,两条纠正我自己:**

**(一)"势函数从第 12 天起惩罚买动物"是对的,不是错的。** 顶端第 15 天到 14 只
之后**一直平到第 29 天**,**没有人在第 15 天后扩群**——所以势函数的符号是对的,
**不需要为它开第九条臂**。真正的缺口在**第 0–10 天**:anvil 第 10 天只有 **5 只**,
顶端已有 **12 只**。而那段时间势函数给的是 **+240 / +112**(正的),所以那不是
估值问题,是**建栏速率**问题——正是 `penner` 在攻的东西(帮手能建能放 +
抱着就放)。

**(二)新发现:我们的网养不住畜群。** 录音在第 10 天把 **12 只**交到
hybrid-cleo12 手上,它一路掉到 **8 只**(12 → 11 → 10 → 10 → 8)。**引擎里连续
两天不喂就失去动物**,所以这是喂食失败。而它**本身就是分档量**:前 10% 平在 14,
后 10% 从 13 掉到 11。**"会不会养"和"会不会建"是两件事,我们两件都差。**

**(三)`hirer` 的动机陈述要改。** 摘要显示**双方第 15 天都是 10 个帮手**
(anvil 第 5 天甚至有 7 个、比场地的 4 个还多),所以**班组规模不是缺口**。
我先前用的是**每回合平均**(7.88 对 8.39),而那个差别的来源不是"雇不到第 9 个",
是**每天早上多晚才把班组重建起来**——`HIRE` 一次连发 10 个,所以一天只需按一次,
按在第 3 个回合平均是 8.75,按在第 5 个回合才会掉到 7.9。**臂本身仍可能有效**
(抬高帮手价值会让它更早按 HIRE),但**它修的是时机不是规模**,判词要按这个读。

**记档规则(今天第三次)**:一个"我们比顶端少"的量,先看它的**逐日轨迹**再下
结论。畜群的静态差(6 对 14)藏着两个不同的病(建得慢、养不住),而帮手的静态
差(7.9 对 8.4)根本不是规模差。

## 2026-08-22 · `FEED_FIRST`:机制成立、账不成立(畜群规模也不是杠杆)

引擎里每只动物每天吃 1 单位小麦,连续两天不吃就失去它。测出**喂食动作/天 与
保住的畜群几乎一一对应**:

| 产物 | FEED/天 | 峰值畜群 | 终局畜群 | 走失 |
|---|---|---|---|---|
| topline(2035.9) | **11.1** | 14 | **14** | **0** |
| hybrid-endgame20 | 10.6 | 14 | 11 | 3 |
| **hybrid-cleo12** | **8.2** | 14 | **6** | **8** |
| anvil(纯 RL) | 6.1 | 9 | 9 | 0 |

**hybrid-cleo12 是判别性的那个:录音在第 10 天把 12 只交到它手上,它并不把喂食
提上去**,于是丢掉 8 只。所以因果是"**我们的网不会随畜群扩大而加喂**",不是
"畜群小所以不用喂"。

修法与 `CARRY_COMPLETES` 同型:`FEED_FIRST` —— **有动物没吃就先去喂,不管被派了
什么任务**(只有和未喂动物数一样多的帮手会被抽走,且只在小麦可取时)。

**机制完全生效**:喂食 **8.2 → 14.3 次/天**,终局畜群 **6 → 13**,走失 **8 → 1**。

**账不成立**:九个对手 × 96 局,**每一个对手上收入都降**,均值 **−5,751**
(胜率 +0.5,噪声):

| 对手 | 收入 Δ | | 对手 | 收入 Δ |
|---|---|---|---|---|
| barnyard | **−8,870** | | k06 | −6,940 |
| grazier | −7,585 | | w49 | −6,066 |
| enhanced/main | −6,801 | | closer_cleo | −3,966 |
| starter | −5,836 | | ledger_lena | −3,248 |

**因为那 13 只是牛,而牛是天梯上最差的动物**(33/天、12.1 天回本;羊 72.7/天)。
把 14 只手工时/天花在维持一群牛上,不如拿去浇水收获。顶端的 14 只是
**8 牛 + 6 羊**,而我们有 **0 只羊**。

**所以"畜群 6 对 14"也不是杠杆——除非那些动物是羊。** 这是今天第三个被测掉的
"缺口":

| 被测掉的"缺口" | 判据 |
|---|---|
| 榨取率 2.0 → 7.3 | 用实际成交量重算后 chisel 最高(4.6)而钱最少 |
| 资金@15 14,405 → 21,360 | hybrid-cleo12 是 24,594、超过前 10%,终局只有 55% |
| **畜群 6 → 14(以牛计)** | **保住 13 只使九对手收入全降 −5,751** |

**还活着的候选杠杆**(诚实清单):**畜群构成**(0 只羊对 6 只,assay 在攻)、
**土地**(2.0 对 3.0,而势函数在惩罚买地,furrow 在攻,算术支撑)、**班组时机**
(每回合均值 7.9 对 8.4,hirer 在攻)、**整个开局**(d0-chisel / d0-d12 /
seedling)、以及唯一稳健的聚合量:**每天约 2,100 元的均匀损失**。

`FEED_FIRST` 与 `BUSY_HANDS` / `SEED_BATCH` / `PLANT_BY_VALUE` / `IDLE_FERTILIZES`
一样,留在默认关闭的标志后面并附上测量,因为下一个看到"我们畜群只有 6 只"的人
会有同样的想法。

**记档规则**:"顶端有 14 只我们只有 6 只"是**规模**差;在补规模之前先问**那 14 只
是什么**。以牛补齐规模是净亏的。

## 2026-08-22 · **本地花名册检验不了"以天梯实价为动机"的改动**(assay 的判读警告)

用动作层把 `BUY_COW` 重定向成买羊(`HERD_SHEEP`),零训练问一句:同一个策略,
换成羊群会不会多挣?

| | 畜群 | WOOL 实际成交 | MILK 实际成交 | 收入中位 |
|---|---|---|---|---|
| cowherd | 9 牛 | 0 | 182 | **46,352** |
| sheepherd | 5 羊 | 150 | 0 | **12,729** |

**本地羊群差 3.6 倍。** 但这**不是**对"羊比牛好"的反驳,而是揭示了一个更要紧的事:

| 品类 | **本地实收/单位** | **天梯中位** |
|---|---|---|
| MILK | ~230 | **66** |
| WOOL | ~70–90 | **218** |

**本地和天梯的相对价格是反的。** 原因是供给量:天梯的牛奶价被压到 66,正因为
**整个场地都养 8 头牛**(1,588 份记录里三档都是 8 牛 + 6 羊);而本地花名册
(三条磁带 + spar + barnyard)的供给量小得多,加上引擎里**商店每步消耗掉每个
品类各 1 个**(最多 8 家店 = 192/天),所以本地市场吸收得掉,价格不塌。

**推论(对今天最重要的一条臂):`assay` 用天梯实价训练,却会在本地花名册上被
评测,而那张表在本地不成立。** 它的花名册判词**可能既不能证实也不能否证**这个
改动对天梯的价值。**预登记的读法**:assay 的 HELDOUT 若变差,先不要判它阴性
——要先量它在本地的**实收单价**;如果它在本地把甜瓜换成草莓、把牛换成羊,而
本地这些品类的相对价格与天梯相反,那么本地变差是**预期的**,而唯一能判决它的
是**天梯**(要一个提交名额)。

**这也把"羊 vs 牛"这条杠杆的地位改了**:它在天梯上有 794 局的价格证据支持,
但**本地不可测**。所以它属于"只能靠提交来判决"的那一类,而不是能在集群里跑出
判词的那一类。

`HERD_SHEEP` 与其余五个被否的标志一样默认关闭并附测量。它的价值在于**发现了
本地/天梯价格反转**,而不是它自己的读数。

**记档规则**:一个改动如果动机来自**天梯的市场状态**,那么**本地花名册不是它的
裁判**——本地的供给量与商店消耗决定了本地价格,而那和天梯不是同一个市场。
这条规则同时解释了档案里那条老规律为什么成立:"价格相关的机器对不反应的对手
有用、对会反应的有害"——反应式对手改变的正是**供给**。

## 2026-08-22 · **纠正:那张"天梯实价表"是收盘价,不是成交价**;正确的表在此

`tools/ladder.py` 第 178 行:`obs = steps[-1][0]["observation"]` —— 摘要的
`prices` 字段是**最后一步的市价**。而最后一步双方都已清仓、市场库存最高、
**价格在谷底**。**我把它当成交价用了**,而 `assay` 整条臂建立在它上面。

正确的量法是每笔成交时的市场库存(和 08-22 那条"下单 vs 成交"同一个教训)。
4 局强对手(topline / hybrid-endgame20 × cleo / k06):

| 品类 | base | **成交单价** | 天梯收盘(误用) | **成交/base** |
|---|---|---|---|---|
| **MILK** | 160 | **25** | 66 | **0.16(高估 6.3×)** |
| **MELON** | 250 | **67** | 22 | **0.27(高估 3.7×)** |
| **WOOL** | 200 | **64** | 218 | **0.32(高估 3.1×)** |
| FERTILIZER | 100 | 51 | 16 | 0.51(高估 2.0×) |
| STRAWBERRY | 120 | 157 | 201 | 1.31(低估) |
| WHEAT | 25 | 43 | 52 | 1.71(低估) |
| **CARROT** | 35 | **134** | 42 | **3.83(低估 3.8×)** |

**方向对了 5/7,但量错了,而且两处次序错了**:收盘表说 WOOL 218 ≈ base
"大致正确",成交价说它**被高估 3.1 倍**;收盘表说 CARROT ≈ base,成交价说它
**被低估 3.8 倍**——而胡萝卜种子只要 20,**是全场对种子成本回报最高的作物之一,
而整个场地一局只卖 14–20 个单位**。

### 由此得到的正确经济模型

| 作物 | 种子 | 每块地(成交价 × max_yield) | 对种子的倍数 |
|---|---|---|---|
| **CARROT** | 20 | 536 | **26.8×** |
| **WHEAT** | 10 | 258 | **25.8×** |
| STRAWBERRY | 100 | 628 | 6.3× |
| MELON | 80 | 402 | 5.0× |

| 动物 | 产品日产值 | 成本 | 仅产品的回本 |
|---|---|---|---|
| COW | 12.5 | 400 | **32.0 天** |
| SHEEP | 21.3 | 500 | **23.4 天** |

**一头牛靠牛奶在 30 天赛季里根本回不了本。** 那为什么真实天梯**三档全部**养
8 牛 + 6 羊?**因为动物是化肥工厂**:`_daily_refresh_animals` 每天给每只动物
`fertilizer_available = True`,`COLLECT_FERTILIZER` 收 1 个单位,成交价 51 ——
**是牛奶(12.5/天)的 4 倍**。加起来日产值 63.5、**回本 6.3 天**。这正是档案里
k06 解剖那条"**化肥工业(31.8%/量 3342)**"的机制,而它从没被当成过一条杠杆。

**而我们在少收**:topline 做 **311 次** `COLLECT_FERTILIZER`(14 只动物 ≈ 每只
每天一次,满收);anvil 的帮手做 165 次、6–9 只动物,约**每只每天 0.6 次**。

**这也解释了 `FEED_FIRST` 为什么赔钱**:它把 14 个手工时/天花在喂食上,却没有
同时把化肥收上来——而动物的价值 80% 在化肥里。

### 对 `assay` 的处置

它的表**方向对、量错**,而且漏掉了 CARROT 这一格。它已经跑了 2 个 link,剩 2 个。
**不杀它**:方向对的表仍能回答"按更真的价格计价有没有用"这个方向性问题;但
**读它的判词时要知道它用的量是错的**,而且**不能**用它来判断 WOOL/CARROT。
下一版的表用上面这张成交价表,并且**必须**同时把化肥收集计入动物的价值。

**记档规则(今天第三个同类)**:摘要里的字段要先读**它是在哪一步记的**。
`sold` 是下单量、`prices` 是收盘价——两个字段、同一个教训:**引擎的量要在
它发生的那一刻量**。

## 2026-08-22 · `HERD_SHEEP` 探针**无效**(它弄坏了策略,不是重新定价)

九个对手 × 96 局:胜率 **−25.0 点**、收入中位 **−17,911**,对 starter 68,766 →
**4,139**、对 enhanced/main 53,382 → **9,840**。

**这种量级的崩塌不是"羊比牛差",是探针本身坏了。** `market_mask` 用
**COW 的 400** 判可负担性,而我在解码里让它买 **500** 的羊——现金在 400–499 时
购买**静默失败**(引擎的 `_commit_unit` 直接 return),策略反复按 `BUY_COW` 却
什么都没买到。实测只放下 **5 只羊**对 **9 只牛**,而它的整个后续计划(喂食、
建栏、卖奶)都是按有一群动物写的。

**所以这条探针的读数作废,它对"畜群构成是不是杠杆"什么都没说。**
畜群构成只能靠**让策略自己学会买羊**来测(assay 的动物侧),不能靠重定向按压。

**仍然成立的是它顺带发现的那件事**(那是独立测量,不依赖这个探针):**本地与
天梯的相对价格是反的** —— 而进一步用**成交价**重量之后,连"天梯价"那张表也
要重写(见上一条判词),真正的结论是 **base 高估牛奶 6.3 倍、羊毛 3.1 倍、
甜瓜 3.7 倍,低估胡萝卜 3.8 倍**,而**动物的价值 80% 在化肥里**。

**记档规则**:一个"重定向按压"式的探针,必须检查它有没有破坏**掩码与实际代价
的一致性**。掩码按 A 的价格放行、解码去买 B,会让购买静默失败——而在这个引擎
里非法动作**不报错**,所以崩塌看起来像"策略变差了"。

## 2026-08-22 · `VALUE_SCHED` 阴性,而这次能说出原因:**有余量的劳力下,最近优先是近优的**

按(价值 − 15×距离)选杂活,而不是按最近。价值用成交价:收一块熟草莓 628、
救一块要旱死的地 258–628、窗口内浇水 43–157、收一个化肥单位 51、care 一头牛 25
——**跨度 25 倍,而现行级联完全按距离**。一个回合的手工时约值 11(2,100/天 ÷
8 帮手 ÷ 24 回合),所以多走 3 格花 33 换 603,算术上压倒性划算。

**九个对手 × 96 局:胜率 −27.2 点、收入中位 −12,313,九个对手全降。**
行为上:走路占比 **53.2% → 69.4%**(+16 点),PASS 28.1% → 17.2%,而浇水
9.0% → 6.3%、收获 2.7% → 1.8%——**产出动作反而更少了**。

**原因(这是这条判词的价值所在)**:我给动作定的价是**那件事的全部价值**,但
一个帮手去做它的**边际价值**不是那个数——**因为别的帮手反正也会去做**。
我们测过帮手 **26% 的时间闲置**,也就是**劳力有余量**;在有余量的系统里每件杂活
最终都会被做掉,所以"走远路去抢高价值杂活"的边际收益接近零,而多走的路是实打实
的成本。**最近优先之所以近优,正是因为它最小化总走动,而完成集合不变。**

**记档规则(可推广)**:**在有余量的容量下,贪心最近是近优的;价值加权只在容量
真正吃紧时才有意义。** 所以调度类的改动应该等到"闲置率接近 0"之后再谈——而
闲置率高本身是农场太小的症状(判词 08-22)。这条同时事后解释了 `BUSY_HANDS`
(把闲置回退到 AUTO,26.0% → 24.4%,无效)与 `IDLE_FERTILIZES`(九对手 −438)
为什么都动不了:**它们都在重排一个有余量的系统里的工作顺序。**

这是第七个被否的动作层标志,和前六个一样默认关闭并附测量。**七个里有六个的
共同结构是"重新分配手工时"**,而这条判词说明那一整类为什么打不动。

## 2026-08-22 · 收束:**势函数偏爱小农场**,而这是每天 2,100 的根

动作层七个标志、六个被否,而被否的原因收成了一条原理(有余量的劳力下贪心最近
近优)。所以每天 2,100 的损失只能来自**有多少东西可干**,即资产基数。把资产
基数直接在势函数里计价(第 12 天,基准=1 地/0 兽/0 株/0 人):

| 农场 | φ 增量 | 建造成本 | **φ − 成本** |
|---|---|---|---|
| 顶端 3 地 / 14 兽 / 40 株 / 10 人 | 15,976 | 12,831 | **+3,145** |
| 我们 2 地 / 6 兽 / 40 株 / 10 人 | 12,604 | 7,631 | **+4,973** |
| 我们 + 补到 3 地 | 12,904 | 9,631 | +3,273 |
| 我们 + 补到 14 兽 | 15,676 | 10,831 | +4,845 |
| **只有 40 株(无兽无地)** | 10,000 | 4,231 | **+5,769** |

**势函数的盈余在最小的农场上最高。** 每一次边际获取都让 φ − 成本下降:
crops-only +5,769 > 我们 +4,973 > 补地 +3,273 ≈ 顶端 +3,145。
**也就是说:势函数在奖励"保持小"。** 这一条把今天三处分散的判词合成一句
——土地 −700/−1700/−3700、动物第 12 天起为负、帮手第 9 个起为负,都是同一个
毛病的三个切面:**φ 把现金按 1:1 计,把资产按低于买价计。**

### 而现金轨迹说明我们不是在囤钱

| 手上现金(中位) | 第 5 天 | 第 10 天 | 第 15 天 | 第 20 天 | 第 29 天 |
|---|---|---|---|---|---|
| 场地前 10% | 580 | **1,836** | 21,360 | 50,759 | **113,900** |
| 场地后 10% | 432 | 463 | 8,664 | 14,028 | 29,250 |
| hybrid-cleo12 | 820 | 1,696 | 24,594 | 35,954 | 66,966 |
| **anvil** | 55 | **1,765** | 14,405 | 24,481 | **58,157** |

**第 10 天两边现金几乎相同(1,836 对 1,765),所以"我们囤钱"是错的。**
但同样的现金下,顶端第 10 天已有 **12 只动物**(轨迹判词)与 **19 株作物**
(轨迹诊断),我们是 **5 只**与约 **10 株**。**同样的钱换出两倍的资产。**
于是前 10 天他们挣约 8,000、我们约 3,300,而 **第 15 天之后差距开始复利**
(21,360 对 14,405 → 113,900 对 58,157)。

**头 10 天的收入几乎全来自作物**(小麦第 2 天出、胡萝卜第 2 天出;牛第 8 天才
出奶),而**作物数量受种子供给限制**(`BUY_SEED` 每个市场槽位 1 颗)。
所以链条是:**势函数偏爱小农场 → 少买地少买兽少下种 → 前 10 天资产只有一半
→ 前 10 天收入只有 40% → 复利到终局的 2 倍差距 → 表现为"每天均匀少挣 2,100"。**

### 这条收束对在跑的八条臂的意义

- **`furrow`(土地 5000)与 `hirer`(帮手 250)是直接对症的两条**:它们把两种
  获取的价格补正;
- **`assay`**(按更真的价格计价)是第三条,但它的表要按成交价重写(判词见上);
- **`d0-chisel` / `d0-d12` / `seedling`** 攻的是"前 12 天",而上面这条链说明
  前 10 天的资产形成正是全部差距的源头 —— **它们攻的位置是对的**;
- **动作层不必再试**:七个标志的结论是"重排一个有余量系统的工作顺序打不动"。

**唯一还没有臂在攻的一格**:`PLANT_CREDIT` 与种子供给。作物是头 10 天唯一的
收入来源,而 `BUY_SEED` 每槽位 1 颗、`SEED_BATCH` 的九对手读数是收入 +2,238 /
胜率 −2.1(边际)。若 furrow/hirer 的判词为正,下一代应把"每一种获取的价格"
一次性补正,而不是逐个试。

## 2026-08-22 · `gleaner` 判词(step 75):边际阴性,与动机降级后的预期一致

`--harvest-urgency 0.5`(每块 `yield_units` 撞上限的地扣 W×crop_base),1,248 局:

| | BEATEN 留出 | 训练过 | 中位 | p05 | 灾难局 |
|---|---|---|---|---|---|
| chisel(基线,313 迭代) | 7/10 | 0/2 | 54,000 | ~23,000 | 2% |
| **gleaner(75 迭代)** | **7/10** | 0/3 | **51,109** | 22,428 | 3% |

**BEATEN 不变、中位 −2,891。** 四堵墙全 0%(cleo −55,689、lena −67,149、
bea −66,956、w49 −67,895、k06 −77,148)。

**诚实的限定**:它只跑了 **1 个 link(75 迭代)**,因为我在 `hirer` 出现后把它的
额度让了出去;chisel 的基线是 313 迭代。所以这不是收敛态的对比,只能说
"**75 迭代的 harvest-urgency 没有把任何轴推上去**"。

**这与它动机被降级后的预期一致**:它原本的动机是"榨取率 2.0 对 7.3",而那条
证据在"下单量 vs 成交量"的纠正中崩掉了(按实际成交量,**chisel 的榨取率是全场
最高的 4.6 而钱最少**)。降级后剩下的动机只是"收获时点在势函数里没有项,而引擎
在撞上限时确实丢弃产出"——**源码为真,但没有金额证据说我们在那里亏钱**。
这份判词就是那句话的实测版本。

**记档规则**:一条臂的动机若在它跑的过程中被别的测量削弱,**判词要按削弱后的
动机读**,不要按最初写下的那个读。gleaner 是今天唯一一条"动机中途崩掉但仍跑完"
的臂,它的读数正好落在削弱后的预期上。

## 2026-08-22 · `furrow` 行为读数(it 56):**行为判据满足了,钱崩了** —— φ 没有预算约束

`--land-value 5000`。三个种子对 cleo:

| | BUY_LAND 按下(天) | 终局象限 | 峰值作物 | 峰值畜群 | 收入中位 |
|---|---|---|---|---|---|
| chisel(基线) | [11] | 2 | **28** | 6 | **50,917** |
| **furrow it 56** | **[10, 11, 11]** | **4** | **24** | 5 | **28,663** |

**这是今天第一条行为真的动起来的臂**(stockman 与 gleaner 都没动行为):买地的
按压从 1 次变 3 次、象限从 2 变 **4**,首次按压提前到第 10 天。**预登记的行为
判据(象限到 3)被超额满足。**

**但收入从 50,917 掉到 28,663,而且作物反而从 28 掉到 24、畜群 6 → 5。**
机制清楚:三块新地要 **1,000 + 2,000 + 4,000 = 7,000**,而第 10 天手上现金只有
约 1,800(现金轨迹判词),所以钱全压在地上,**种子和动物就没钱买了**,75 格
新地空着——**买了地却填不满,比不买更差**。

**而顶端只买 3 块地,不是 4 块。** `land_value 5000` 让第四块(4,000)也变成
**+1,000**,于是过冲。要让它买满 3 块而不买第 4 块,数值必须落在 **2,000–4,000**
之间(第 3 块的地价是 2,000、第 4 块是 4,000)。

### 这条判词的一般化(比它自己的读数更重要)

**φ 是一堆彼此独立的信用之和,没有任何现金流约束。** 所以"把某一种获取的价格
补正"会导致**那一项被过度购买**,因为它不知道这笔钱本来要买种子。今天我按
"用交易价格定势函数项数值"这条规则改了两处(土地 300 → 5000、帮手 40 → 250),
**这条判词说明那条规则不完整**:它给出了单项的**下界**(不能低于买价),但
**上界要由预算竞争决定**——多花的每一块钱都是别处少花的一块。

**对 `hirer` 的预登记警告**:同样的过冲风险。`--hand-value 250` 让 12 人班组
净为正,而一天 12 人的工资是 608;若它把班组推到 12 人而挤掉种子与动物,读数
会和 furrow 一样。**读 hirer 时先看它有没有挤掉作物/畜群**,别只看班组数。

**下一代的形式**:不要逐项补价,而要么(a)把 φ 的资产项整体按"这笔钱的替代
用途"折算(即让 φ 对现金的边际价值随资产基数上升),要么(b)只补正**最紧的
那一项**并把其余保持不变。furrow 与 hirer 的花名册会告诉我们哪一项最紧。

## 2026-08-22 · 最紧的那一项找到了:**势函数把回报最高的作物按 13% 计价**(第九条臂 `grocer`)

`furnow` 的判词说 φ 没有预算约束、逐项补价会导致过冲,并要求"先找出最紧的那一项"。
把每种作物的 φ 信用与它按**成交价**的真值并排:

| 作物 | 种子 | φ 信用 | 成交价真值 | **信用/真值** | 真值/种子 |
|---|---|---|---|---|---|
| **CARROT** | 20 | 70 | **536** | **0.13** | **26.8×** |
| WHEAT | 10 | 75 | 258 | 0.29 | 25.8× |
| STRAWBERRY | 100 | 240 | 628 | 0.38 | 6.3× |
| **MELON** | 80 | **750** | 402 | **1.87** | 5.0× |

**势函数把全场回报最高的三种作物按真值的 13–38% 计价,把最差的甜瓜按 187% 计价。**
胡萝卜对种子成本的回报是 **26.8 倍**,而它拿到的信用只有真值的 **13%**——
**这是最紧的那一项**,而且**统一抬 `PLANT_CREDIT` 修不了它**(误差跨 0.13× 到 1.87×,
统一抬只会让甜瓜更过)。

**正确的形状就是 assay 的形状(按品类计价),但要用成交价表。** 而 assay 用的是
收盘价表,它把胡萝卜错成 ×1.20(真值 ×3.83)、把羊毛错成"大致正确"(真值 0.32×)。

**第九条臂 `grocer`**(gen31 `txprice`):`--tx-price 1.0`。门 `REALISED-PASS`:
- R2 五个作物比值逐一精确;
- R3 **胡萝卜 70 → 268(3.83×)并超过甜瓜**(201),草莓 240 → 314 也超过甜瓜;
  动物侧 **牛 512 → 80、羊 507 → 162**——**两者都变便宜,而羊超过牛 2 倍**
  (对上成交价日产值 21.3 : 12.5),这正好与 `FEED_FIRST` 的判词一致(养一群牛
  不值那个手工时);
- TOMATO 与 EGG **保持 base**,因为它们在我们的对局里成交量为 0——刻意如此,
  避免把畜群推进那个"无人供给过"的蛋市场。

**同时腾出的额度**:`furrow` 剩下的 link 已取消。它的教训已经学到(行为达标、
收入崩塌、过冲到 4 块地),而正确的读法是**土地本来就不该被重新计价**——φ 对
土地的价值本来就通过"地上种的东西"实现(`plant_val` 是逐格的),`LAND_VALUE`
只是个小推力,抬到 5000 等于**为空地付钱**。它的花名册仍会出(读 it 56 的检查点)。

**臂的账**:九条臂里,`grocer` 是第一条**由一条被否的臂(furrow)直接推导出来**的
——furrow 的价值不在它自己的读数,而在它证明了"逐项补价会过冲",从而迫使我去
找最紧的那一项。

## 2026-08-22 · **撤回中心叙事"势函数偏爱小农场"** —— 它算在不物理的状态上

那张表(判词"收束:势函数偏爱小农场")把 40 株作物放在**1 个象限**的农场上。
但重置时棋盘是 **25 格空地 + 75 格 `K_LOCKED`**,一个象限只有 25 格(减去 4 格
棚 = 24 格可用)。**"1 象限 + 40 株"物理上不存在**,而 φ 只检查
`kind == K_PLANT`,所以它照算了。

第二次尝试同样失败:**设 `quad_unlocked` 标志并不会把 LOCKED 格子改成 EMPTY**
(引擎在 `BUY_LAND` 生效时才改 `kind`),所以"3 象限"那行仍然只放下 24 样东西
——三行数字其实是同一个农场。

**所以那条"最小的农场盈余最高"以及由它推出的"φ 在奖励保持小"整条叙事,撤回。**
要正确算它,需要一个尊重解锁机制的状态构造器(把对应象限的 `kind` 从
`K_LOCKED` 改成 `K_EMPTY`),这一步今天没做。

### 哪些结论**不**受影响(都是逐格/逐只的边际量,与格子合法性无关)

1. **φ 的逐格作物信用是错的**:CARROT 信用 70 对成交价真值 **536(13%)**、
   WHEAT 29%、STRAWBERRY 38%、MELON **187%**。φ 只是对每个 `K_PLANT` 格子求和,
   所以"一格草莓值多少信用"这个读数是 φ 的算术本身,不依赖那格是否可达。
   **这是 `grocer` 的动机,它成立。**
2. **φ 的动物项完全没有化肥流**(`a_val` 只用 `_A_BASE` = 动物产品的基价)。
   每只动物每天 1 个单位化肥、成交价 51,是牛奶(12.5/天)的 4 倍;仅算产品时
   一头牛要 32 天回本(赛季只有 30 天),算上化肥约 6 天。**这个洞是真的**,
   而且它解释了为什么每一次动物相关的改动都失败(capital_credit 抬错了量、
   FEED_FIRST 养活了牛却不去收它的化肥)。已加进 gen31。
3. **成交价 vs base 的比值表**(MILK 0.16×、MELON 0.27×、WOOL 0.32×、
   CARROT 3.83×)——那是逐笔成交的实测,与状态构造无关。
4. **每天约 2,100 的均匀损失**、**同板天梯尺子与 ~1,500 的预期**、**动作层七个
   标志的结论**——全部基于真实对局的钱与动作,不受影响。
5. **土地是硬容量约束**:一个象限 25 格,LOCKED 格子不能种。**我们 2 象限
   (50 格)放 6 兽 + 40 株 = 46 格,几乎满了**;顶端 3 象限(75 格)用 54 格。
   所以"要更多作物就必须先买地"是对的——而 `furrow` 的失败是**买了地却没钱填**,
   不是"土地不该被计价"。**上一条判词里"土地本来就不该被重新计价"这句话,
   下调为"土地的计价必须与填满它的现金一起考虑"。**

**记档规则(今天第四个同类)**:**用手工构造的状态去读势函数之前,先确认那个
状态是引擎能达到的。** `sold`(下单量)、`prices`(收盘价)、锁住的格子——
三次都是同一个毛病:**没有先问"这个数是在什么条件下产生的"。**

## 2026-08-22 · 行为对照:**我们的网不种地,它在倒卖小麦**;而浇水的代价被低估 7.6 倍

今天前面所有的推演都在读势函数。这一条改成读**动作**:框架把每一方提交的动作
记在 `env.steps[i][p].action` 里,所以任何 agent 文件都能按**下单量**统计——
和磁带 `_TRACE` 的单位完全一致,不用碰数字摘要里那个被我误读过的 `sold`。

### 三个我们自己的纯网 + 天梯冠军,同一个对手(cleo)

| 网 | 钱 | WATER | PLANT | HARVEST | 买**小麦成品** | 卖化肥 |
|---|---|---|---|---|---|---|
| cropper-samp | 25,536 | **16** | **0** | 59 | 1,882 | 206 |
| sower-it228 | 25,586 | 260 | 20 | 114 | 1,426 | 234 |
| anvil-samp | **53,762** | **508** | 40 | 155 | 1,058 | 176 |
| k06(天梯 2302) | ~174,711 | **915** | — | — | — | **1,671** |

**钱在四个点上单调跟着 WATER 走**,而"买小麦成品"反向单调:农场越弱,越用买来
的小麦替代自己种的东西。cropper 一整局只浇 16 次水、一次都没种过地——它买 1,882
份小麦、卖 1,723 份,**它是个小麦贩子,不是农场**。手上最常见的动作是 PASS
(1,420–1,952 次),而 k06 最常见的是 WATER。

### 引擎读法两处更正(`reference/engine/kaggriculture.py` 775–802)

1. **ongoing 作物不浇水也会按 interval 产出。** 我此前写的"不浇水就没有生产
   事件"是错的。浇水只管两件事:`consecutive_unwatered >= 2` → 地块变
   `WEED`;以及 `fertilized = was_watered and ...` ——**施肥的 +2 加成必须当天
   浇过水才算**。
2. **第 222 行:种下的当天 `consecutive_unwatered` 就已经是 1。** 所以新种的地
   必须在一天之内浇上,否则当晚直接变杂草。**这就解释了我们的网为什么学会了不
   种地**:种了不浇等于当场烧掉种子和一格地,而它没学会可靠地浇水。
   cropper(PLANT 0 / WATER 16)→ anvil(PLANT 40 / WATER 508)是同一条曲线。

### 势函数把这件事低估了 7.6 倍,而且信号迟到一晚

6 株草莓,第 10 天,只改浇水状态:

| 状态 | φ | 每株 |
|---|---|---|
| 健康(今天浇过) | 4,080 | 信用 **+180** |
| 今天还没浇、consec=0 | 4,080 | **±0 ——今天做决定时,φ 是平的** |
| 干了一晚 consec=1 | 3,918 | **−27** |
| consec=2(明晚变杂草) | 3,918 | 还是 −27 |
| 已经变杂草 | 2,850 | **−205** |

`stress = ((~watered) & (consec_unwatered >= 1)) * 0.15`。夜里浇过水的地块第二天
`consec=0, watered=False`,所以**在"浇不浇"这个决定活着的整个白天里,stress 是
0,浇水这个动作的 shaped reward 恰好等于零**。惩罚也不随杂草时钟增长:
consec=1、2、3 都是 −27。真正的 −205 要等到地块**已经死掉**的那一晚才到,那时
动作早就不可用了,而中间隔着 24 个 turn 和 γ 的折扣。

**所以这不是"缺一项",而是"这一项迟到"**——正是势函数塑形该解决的那类问题。
低估倍数 205/27 = **7.6×**。

### 顺带:两条关于势函数定价的判词

**φ 作为价值代理,在真实轨迹上其实是好的。** 用五条磁带在张量引擎里各打一局
(第 1 座位固定为"最小合法下标"对照),读它们真实到达的状态上的 φ,再看 φ 的
**排序**是否等于最终钱的排序。三个种子一致:base 价的 ρ 从第 8 天起是
+0.89/+0.89/+0.94,到第 25 天 +0.94/+1.00/+1.00。**再加一个什么都不做的对照**
(终局 3,000,φ 全程 2,950–3,000 不动)也排在最后。所以 φ 不是坏的价值代理。

**成交价定价没有更好,第 4 天反而是反的。** 同一张表里 tx+粪肥 的 ρ 在 d12 之后
和 base 完全相同,d8 略低,而 **d4 是 −0.09/−0.09/−0.14**(base 是
+0.60/+0.71/+0.77)。原因看得见:最强的两条(k06、w49)恰好是早期库存被"西瓜
打到 0.27 倍"打掉的那两条。

**但这个探针对 grocer 没有检验力,所以这是"未获支持"而不是"被推翻"。** 五条磁带
的作物结构几乎相同(k06 138 小麦/34 草莓/20 西瓜/15 胡萝卜,其余 66–111 小麦 +
41–44 草莓 + 21–26 西瓜),herd 全是 8 牛 6 羊。**一个五条轨迹共有的定价偏差,
不会改变它们之间的排序。** grocer 继续跑,它的 A/B 才是判据。

**化肥独立地支持 gen31 的粪肥项**:k06 的第一大卖出线是化肥 1,671 单,超过它的
小麦 1,060;我们最好的网只有 176,COLLECT_FERTILIZER 一局 143–170 次。天梯把
化肥当主营业务,而 φ 的动物项里一份都没有。

### 由此起的新臂:waterer(gen32)

`--dry-risk`,默认 0(= 现行行为)。地块 `consec_unwatered >= 1` 且今天仍未浇
时,按它**自己的剩余信用 + WEED_COST** 计入预期损失,而不是打 15% 折。清单:
(a) 它不是"解锁一个被屏蔽的动作",WATER 本来就在 `HAND_TASKS` 里且我们的网确实
偶尔用;(b) 一个回合内自足——今天浇上就没事;(c) 每回合都有 >1 个候选地块;
(e) 水/肥/收是乘性互补,这一条打的是"水"那一维;(j) 量级取自它必须驱动的那笔
交易——**地块自己的剩余价值**,不是一个手调常数。

### 同日更正:grocer 被拆了,因为它是两个变量

上一条判词末尾写的"grocer 继续跑,它的 A/B 才是判据"作废。检查它的命令行时发现
它同时带 `--tx-price 1.0` **和** `--fert-credit 0.3` ——**两个变量**,而且今天
的证据把它们指向了相反的方向(定价那一半未获支持且 d4 反号;粪肥那一半有 k06
1,671 单化肥的直接行为支持)。赢了不知道是哪一半,输了会连带丢掉粪肥项。

而且更糟:我今天上午还在 `potential_future.py` 里**又加了一遍**粪肥流,而
`trl_env.py` 早就有一个 `fert_credit` 包装器。两个一起生效时,第 8 天一只动物被
计 **1,109**,接近一头牛 400 的三倍。已回退势函数里那一份,`test_txprice.py` 的
R5 改成**专门守这个重复计价**:价格档只许按**产品**比率(MILK 0.16×、
WOOL 0.32×)移动一只动物,多一分都算泄漏。

所以 20302604-07 取消,重新提交为单变量的 **muckman**(`--fert-credit 0.3`,
链 20303576-78 + 花名册 20303579)。`--tx-price` 暂不测。

**新臂 waterer**(gen32,`--dry-risk 1.0`)已过全部七道门(`GATES-RC=0`,
门 20303651),链 20303701-03 + 花名册 20303704。W4 **预先登记了它的代价**:
PLANT 单独的即时增量从 +153 变成 −25(种了不浇确实就值这个),而"当天种+浇"这
一对仍然是 +180。势函数不改变最优策略,只改变会找到哪一个——但梯度形状确实变了,
所以先写下来,免得阴性结果之后被事后解释。

## 2026-08-22 · 逐日读盘:**我们持有土地却让它空着,而买种子在势函数里是亏的**

前一条的"WATER 单调"是**混淆**,我自己撤回它。逐日读真实对局(`tools/order_mix.py`
的思路 + 每天读棋盘),得到的是另一幅图。

### 棋盘:天梯"永远不留空地",我们"买了地就不管了"

| 空着的**已解锁**格子 | d3 | d6 | d9 | d12 | d15 | d18 | d24 | d28 |
|---|---|---|---|---|---|---|---|---|
| k06(天梯 2302) | 1 | 25 | 2 | 6 | 6 | 2 | **0** | 5 |
| anvil-samp(我们最好的纯网) | 10 | 4 | 0 | **24** | 19 | 18 | 24 | **27** |

k06 的 d6 那个 25 是它**刚买下的第二象限**,三天内填满。它 **第 0 天就买 19 颗
种子、种下 19 格**,到第 27 天还在每天种 12 格。我们的网第 12 天买下第二象限,
**从此再没填过**,第 18 天之后**一颗种子都不买**,站着的作物从 26 格缩到 12 格
——地块到期了没人补种。**我们不是缺地,是拿着地不种。** 一局买的种子:
**47 对 207**。

### 为什么不买:**在势函数里,每一次买种子都是即时亏损**

第 6 天,每个决定的即时 φ 变化(现行势函数):

| 决定 | φ 变化 | | 决定 | φ 变化 |
|---|---|---|---|---|
| BUY_SEED WHEAT(花 10) | **−5** | | PLANT WHEAT | +70 |
| BUY_SEED CARROT(花 20) | **−10** | | PLANT STRAWBERRY | +190 |
| BUY_SEED MELON(花 80) | **−40** | | BUY_LAND 第二象限(花 1000) | **−700** |
| BUY_SEED STRAWBERRY(花 100) | **−50** | | | |

原因是**基准不一致**:一颗种子按 `seed_cost × SEED_RESIDUAL` 计价(草莓 100×0.5
= 50),而它变成的地块按 `expected × 市场基价 × PLANT_CREDIT` 计价(4×120×0.5
= 240)。**同一个未来的作物,两个基准。** 于是"买+种"这一对是强正的,但**第一步
是负的**。k06 第 0 天那 19 颗种子,在这个项下大约值 **−400 到 −700 的塑形奖励**。
一个跟着 φ 走的策略当然不买。

### 新臂 seedsman(gen32,`--seed-credit 0.5`)

一颗持有的种子按 **0.5 × "今天种下去会得到的信用"** 计价。**没有任何可调常数**:
0.5 就是势函数自己到处在用的 `SEED_RESIDUAL`,只是**换到正确的基准上**。于是
草莓 BUY **+20**、PLANT **+120**,两步都正;`w=1` 会把 PLANT 归零并放出仓库里那个
"囤货"旧病(所以是 0.5 而不是 1)。门 `test_seed.py` S1–S5,其中 **S4 钉住作物
排序完全不变**(买+种的总额也不变),所以这一臂**不是定价问题的伪装**——它只改
信用**什么时候**到账。链 20304316-18 + 花名册 20304319,门 20304313。

### 路上造了两条臂又自己撤掉,都没花掉 GPU

**`--dry-risk` 撤回:那是个混淆。** WATER 手数和钱一起涨,只因为两者都随**站着的
地块数**涨。**按每块地算,我们的网浇得比 k06 还多(29.9 对 21.7)**——天梯浇得少
是因为它施肥,而施肥把浇水需求砍半(`tools/registry.py` 的 `compost` 注释早就
写了)。而且**杂草对谁都不超过 3 格,k06 到第 24 天之前是 0**。地块不是旱死的,
是到期没补种。我把结果当成了原因。

**`--idle-land` 撤回:反向激励。** "空着的已解锁格子按一格小麦的机会成本计价"
听起来对(k06 空 0–6 格,我们空 18–27 格),但 **BUY_LAND 在现行势函数下已经是
−700**(花 1000 换 300 的 land_value),而引擎在成交的同一刻把那 24 格改成
`K_EMPTY`,所以这一项会**再加 −1,800**,去压制 k06 做了三次的那个动作。

两条都留在树里、默认关、门照跑(`test_water.py`、`test_idle.py`),注释里写清
为什么**不要**当臂用。

**记档规则**:**相关量要先除掉规模再看。** WATER、HARVEST、卖出量全都随地块数
走,所以它们的绝对值对"谁做得对"没有信息;**每块地的 WATER** 才有,而它把结论
翻了个方向。

## 2026-08-22 · 六条臂的花名册汇总:**中位数 43k–51k,而对三条磁带全部 0/3**

有几份花名册跑完了却没人读过(仓库文档里那条"ingest 不是自动的、忘掉才是默认"
的同类失败)。一次读齐:

| 臂 | 变量 | HELDOUT | 中位钱 | p05 | <20k |
|---|---|---|---|---|---|
| stockman | 帮手 BUILD+PLACE 词表 | 7/10 | **51,344** | 23,705 | 2% |
| gleaner | `--harvest-urgency` | 7/10 | 51,109 | 22,428 | 3% |
| furrow | `--land-value 2500` | 7/10 | 48,703 | 18,682 | 6% |
| grange | — | 6/10 | 46,268 | 18,207 | 7% |
| longhaul | 长链对照 | 5/10 | 43,355 | 17,817 | 8% |

(前三条是 13 个对手 1,248 局;grange 与 longhaul 的池里只有 2 条磁带,1,152 局。)

**三件事一起看:**

1. **每一条都对三条磁带 0/3**(cleo、lena、k06),margin −62k 到 −77k。
2. **彼此之间只差 8k**(43,355 到 51,344),而**到目标还差 60k**(同板锚点
   `calib-topline` 是 110,960)。**臂与臂之间的差异,小于它们共同的缺口。**
3. 所以"再调一个势函数系数"这条路线的**整个家族**都停在同一条带子上。这反过来
   加强了逐日读盘那条判词:真正要改的是**行为**——一局 47 颗种子对 207 颗。

**seedsman 的门槛因此是明确的两个数**:要成为最好的一条臂,得过 **51,344**;
要够 2000 分,得过 **104,500**。

### 一个必须带警告标签的数字

`penner-samp` 那份花名册读出 **中位 162、HELDOUT 1/10、100% 的对局低于 2 万**。
**这不是 penner 的判词。** 它是 `scancel` 陷阱的产物:20296738 被取消后,依赖它的
花名册 20296742 的依赖变成 `(null)`,于是**在训练才跑了十几分钟时就导出了检查点**
并在 09:11 跑完。penner 真正的花名册(20296991)还在等它第四个 link。
**这个数字要丢掉,不要记进任何比较。** 记忆里那条"每次 scancel 之后必须回扫
`(null)` 依赖"就是为它写的,而这次是在读数时才抓到的——**所以读数时也要问一句
"这个检查点是什么时候导出的"**。

## 2026-08-22 · **BUY_SEED 一回合只买一颗**——六条臂挤在同一条带子上的结构原因

`rl/actions.py:441`:

    if name.startswith("BUY_SEED_"):
        return [["BUY_SEED", name[len("BUY_SEED_"):], 1]]

**一个市场动作 = 一颗种子。** `BUY_ANIMAL` 同样是 1(第 448 行)。而同一个函数里
`HIRE` 已经是最多 10 连发、`SELL` 在清算日复合卖空整个棚、`BUY_WHEAT` 按畜群规模
放大——注释写得很清楚:"单订单的头,清算和雇人比同段位的每一个对手慢一个数量级"。
**种子和动物被漏在了那次修复之外。**

### 实测(同一局,对手 lena)

| agent | 用掉的市场回合 | 发出的订单 | 订单/回合 | **单回合最多买几颗种子** |
|---|---|---|---|---|
| anvil-samp | 497 | 729 | 1.47 | **1** |
| cropper-samp | 553 | 650 | 1.18 | **1** |
| k06(天梯 2302) | 350 | 902 | 2.58 | **23** |
| closer_cleo | 363 | 754 | 2.08 | **25** |

**我们用掉更多的市场回合(497、553),发出更少的订单(729、650);磁带用更少的
回合(350、363)发出更多订单(902、754)。** 一局 720 回合,anvil 把 **69%** 的
市场槽花掉了才发出 729 个订单。

**要追上 k06 的 207 颗种子,按一回合一颗需要 207 个市场回合**——而卖出、雇人、
买小麦、买地都要抢同一个槽。k06 第 0 天**一个订单**就是 `["BUY_SEED","MELON",12]`。
引擎允许单个订单带数量,所以这不是订单槽的限制,**是我们自己把数量写成了 1**。

### 这解释了那条 43k–51k 的带子

六条臂各改一个势函数项,中位数全部落在 43,355–51,344,对三条磁带全部 0/3。
**势函数无论怎么调,都改不动"一回合一颗种子"这个吞吐上限。** HIRE 那条注释里的
句子逐字适用于种子:"在 4 颗/动作时策略每天需要三次 HIRE,于是从来没学会这个习惯
(4 只手的平台期);改成 10 之后,一个动作买下一整个工作日。"
**我们的平台期是 ~20 格地。**

### 由此起的新臂 sackman(gen33)

`SEED_BURST`:`BUY_SEED_<c>` 的数量从 1 改成 `min(空着的已解锁格子 − 已持有的种子,
现金的一半 ÷ 种子价)`,下限 1。三个界都不是调出来的:格子数是它能种下的上限,
"现金的一半"照 HIRE 的 `cost_cap` 那个形状防全押破产(记忆里"全押破产"是已知病灶),
而单订单带数量是引擎本来就允许的。`BUY_ANIMAL` 同样按牧场空位放大。

**注意这是词表改动而不是奖励改动**,所以它必须过设备孪生的字节相等门
(`test_multi`/`test_b3`)——CPU 解码和张量引擎的市场解码要一起改,否则 A/B 会变成
"两边跑着不同的游戏"。

## 2026-08-22 · 零重训词表 A/B:**SEED_BURST 在 0.5 会让策略破产,悬崖在 0.25**

**词表加宽是唯一能不用 GPU 做 A/B 的臂型**——权重不必变,解码就能变。所以用**同一份
chisel 权重**,分别从窄树和 burst 树导出,四个现金比例各 672 局:

| frac | HELDOUT | 中位钱 | p05 | <20k |
|---|---|---|---|---|
| narrow(现行,一回合一颗) | 2/4 | 46,905 | 20,470 | 4% |
| 0.05 | 2/4 | 47,151 | 20,210 | 5% |
| **0.10** | 2/4 | **47,447** | 19,008 | 6% |
| 0.25 | 1/4 | 40,837 | **0** | 22% |
| 0.50 | 1/4 | 36,910 | 5,749 | 24% |

**我最初造这条臂用的就是 0.5,而它让在位策略自己破产**:对 k06 的 margin 从
−74,920 掉到 −132,848,四分之一的对局收在 2 万以下。**0.25 的 p05 是 0**——有对局
结束时一无所有。悬崖在 0.10 与 0.25 之间。

**0.10 不只是"安全的数",它是对的形状。** 破产来自**贵种子**:0.10 时第 0 天带
3,000 现金仍然买满 25 颗小麦(受格子数限制),但西瓜/草莓只买 3 颗。k06 自己第 0
天的种子支出是 3,000 里的 1,030,所以 0.34 本来就是任何界的上限。

**必须说清这个扫描没有说什么**:0.10 相对 narrow 的中位增益是 **+542 / 672 局,
在噪声里**。它确立的是"**这个加宽不会破坏在位策略**"——那是我给这条臂 GPU 的
**预登记条件**。吞吐到底值不值钱,要由训练后的臂回答。

**机制**:扫描改的是**每份导出产物自己那一份** `SEED_BURST_FRAC`,不是树里的。
`export_agent` 写出的 `kg_rl_actions.py` 是自包含的,所以既不会漏回树里,也不需要
环境变量——**用环境变量会让提交上去的 agent 与训练它的那个跑出不同行为**。

### 顺带修掉一个会让今晚整夜白跑的坑

`agents/bench3/`、`champ/`、`spar/`、`ghosts/`、`wrapped/` 都是 git-ignored,
**所以今天新建的 gen32、gen33 两个 worktree 里一个对手文件都没有**(老的九个都有,
是历史上被填过)。两条链都会在加载磁带对手时失败,产出为空、无人报错。已从主树
复制补齐——**不是重新生成**(`agents/spar` 一旦重新生成就换了对手集)。

**新建 worktree 之后必须做的一步**:确认 `agents/{bench3,champ,spar,ghosts,wrapped}`
都在,否则整条链的对手是空的。

### 排队形状(用户要求贴合 backfill)

- 所有 GPU link 的 walltime 从 55 分钟改成 **30 分钟**、内存 32G → 16G。改完
  **立刻就有作业开始跑**(此前 38 个作业 0 在跑)。训练器**每个迭代都存盘**,所以
  被 walltime 砍掉最多损失一个迭代,`--resume` 接着跑。
- 九个花名册作业从"32 核 × 2.5 小时"的整块,改成**每个对手一个 array task**
  (13 task × 8 核 × 25 分钟)+ 一个 1 核的读数作业。零重训 A/B 的 14 个 task
  **在提交后 100 秒内就完成了 4 个**——这个形状确实能被 backfill 吃掉。

### 同日修正:SEED_BURST **换掉了**"只买一颗"这个选项,而磁带平常买的就是小单

`project_tape.py` 在两棵树上各跑一遍(同样五条磁带、同样种子),问的是"我们的市场头
有没有哪个选项能复现磁带那一步真正发出的订单表":

| 磁带 | farmer | whole-list 窄 → burst | first-order 窄 → burst |
|---|---|---|---|
| cleo | 96.1% | 54.5 → **52.4** | 64.8 → **61.9** |
| lena | 75.8% | 35.2 → **33.4** | 38.9 → **37.1** |
| bea | 75.8% | 36.2 → **34.4** | 43.7 → **41.6** |
| w49 | 86.5% | 64.8 → 64.8 | 69.7 → 69.7 |
| k06 | 95.7% | 56.6 → 56.6 | 66.6 → 66.6 |

**覆盖率一次都没升,三条还降了。** 原因很直接:burst 把"永远买 1 颗"换成了"永远
按上界买满",所以**我们失去了"只买一颗"这个能力**。而磁带平均每回合只发
**1.05–1.64** 个订单——**它们平时买的就是小单**,第 0 天那个 23–25 颗才是例外。

所以这条臂在一个维度上变宽的同时,在另一个维度上**变窄了**。

**但这不等于臂是坏的**:覆盖率量的是"能不能模仿",不是"值不值钱"(今天早些时候
"DRIVE 比例当词表判词"那条已经因为同样的混淆被撤回)。零重训 A/B 在 0.10 的读数是
**无害也无增益**(+542 在噪声内)。两件事合起来说的是:**按上界买满不是对的形状,
对的形状是"1 和批量各占一个选项、由策略自己选"。**

**那需要把市场头从 31 加宽**(`BUY_SEED_BULK_<c>` 另设选项),而头的宽度目前是
**为了检查点能续跑而钉死的**(`_market_action` 的注释:"Head size is unchanged on
purpose -- checkpoints keep resuming")。加宽要走 Net2Net(`rl/widen_hands.py` 是
手部头的先例),是明天的活。

**frac 0.10 那条链照跑**——它已经被测过不伤在位策略,成本是 5 × 30 分钟,而且
"按上界买满"到底行不行,训练后的读数比覆盖率更有说服力。**但预登记结论:如果
sackman 只是持平,原因大概率是这个,下一步是加宽头而不是再调 frac。**

## 2026-08-22 · 加宽市场头:**"1 颗"和"一批"各占一个选项**,零重训验证无回退

前一条判词的结论是"按上界买满不是对的形状,对的是 1 和批量各一个选项"。这一条把它做
出来了,并且**在给 GPU 之前用 CPU 验完**。

`BUY_SEED_BULK_<c>` **追加在 31..35**(`SELL_HALF` 立下的规矩),所以**前 31 个下标
一个都没动**,已有的 31 宽检查点可以用 `widen_hands.widen_flat` 直接加宽——追加的行
从零权重 + `NEW_BIAS = −4` 开始。chisel 加宽输出:
"widened market 31->36; heads verified identical on 8 reset lanes"。

**普通选项仍然买 1 颗,一个字没改。动物也仍然是 1**:实测缺口是**种子数**,动物受
栏位而不是回合数限制,两个一起放宽会让这条臂变成两个变量。

### 零重训安全门(同一份权重,672 局)

| | 窄头 31 | 加宽 36 |
|---|---|---|
| HELDOUT | 2/4 | 2/4 |
| 中位钱 | 46,905 | **48,919** |
| p05 | 20,470 | 20,061 |
| <20k | 4% | 5% |

**中位 +2,014、p05 基本不动、没有回退。** 对比"按上界买满"那一版(中位 36,910、
p05 5,749),差别一目了然:**加宽是安全的,替换不是。**

门:`test_bulk.py` B1–B5 + `MULTI-PASS` + `B3-PASS`。其中 **B1 钉住
`MARKET_ACTIONS[:31]` 与出厂表逐字相同、且普通选项仍然买 1**——这正是"31 宽检查点
可以安全加宽"的依据;B3 钉住**批量选项的合法性与普通选项逐位相同**(设备侧直接复用
普通选项那个表达式,所以合法性不可能漂移);B5 钉住扫描选出的**形状**:frac 0.10 时
第 0 天买满 25 颗小麦(受格子限制)但西瓜只买 3 颗(受现金限制),因为 0.25 以上的
破产来自贵种子。

链 20305591-95(5 × 30 分钟)+ 花名册 array 20305596 + 读数 20305597,门 20305590。

**判据**:HELDOUT 中位要过 **51,344**(六臂最好成绩);行为上看**一局买的种子数**
(基线 47,k06 是 207)、**空着的已解锁格子数**(基线 d18 18 格 / d28 27 格,
k06 是 2 / 5),以及**批量选项到底被选了多少次**——如果一次都不选,那说明 NEW_BIAS
太低,而不是吞吐没用。

## 2026-08-22 · **收入不是产出决定的,是镇上的消耗量决定的**——43k–51k 那条带子的机械解释

追一个不对劲的数字追到了整个经济的账本。起因:k06 卖出 1,671 份化肥,而 14 只动物
一季最多产 420 份。

### 一、`sold` 又骗了我一次(今天第三次同一个毛病)

`_commit_unit` 里 **SELL 一次只成交一个单位**,而外层循环**每个单位都重新报价**
(第 596 行 `market_price(item, market["inventory"][item], ...)`),成交后
`market["inventory"][item] += 1`。所以 `["SELL","FERTILIZER",1671]` 是**一个订单、
1671 次逐单位成交、价格一路往下**,到 `PRICE_FLOOR = 1` 为止。**下单量与成交量的比
可以差一个数量级**,而我第三次拿下单量当收入算了。

### 二、每个产品的池子深度天差地别

从 I0 开始连卖 N 单位的**边际价**:

| 产品 | #1 | #50 | #100 | #200 | #400 | 卖 400 的累计 |
|---|---|---|---|---|---|---|
| **FERTILIZER** | 100 | 90 | 80 | 60 | **20** | **24,040** |
| **MELON** | 250 | 226 | 152 | 1 | 1 | 26,727 |
| **WHEAT** | 25 | 22 | 21 | 21 | **20** | 8,313 |
| CARROT | 35 | 27 | 24 | 19 | 12 | 7,853 |
| STRAWBERRY | 120 | 26 | **1** | 1 | 1 | **4,147** |
| MILK | 160 | 57 | **1** | 1 | 1 | 6,505 |
| WOOL | 200 | 61 | **1** | 1 | 1 | 7,969 |

**草莓一整局倒卖到底只有 ~3,847。** 高基价的产品池子最浅,50–100 个单位就塌到 1 块。

### 三、价格靠**镇上消耗**回升,而消耗量由**解锁了哪些店**决定

`_apply_town_consumption`:每 `shop_interval`(默认 **4 回合**)每家已解锁的店消耗
它卖的产品各 1 份(**单一产品的店 ×2**),每 `center_interval`(**24 回合**)镇中心
把 `TOWN_CENTER_PRODUCTS` 各消耗 1 份。**这就是全部的需求侧。**

于是一局的**可续收入预算**是可以算出来的。某一局(seed 10000,解锁顺序
PIZZA d3 / ICE_CREAM d6 / BRUNCH d9 / PET_CAFE d15 / FARMERS d18 / SMOOTHIE d24):

| 产品 | 季内消耗 | I0 单价 | 可续收入 |
|---|---|---|---|
| **MILK** | 372 | 160 | **59,520** |
| **STRAWBERRY** | 408 | 120 | **48,960** |
| TOMATO | 264 | 60 | 15,840 |
| WHEAT | 534 | 25 | 13,350 |
| CARROT | 282 | 35 | 9,870 |
| MELON | 30 | 250 | 7,500 |
| WOOL | 30 | 200 | 6,000 |
| **FERTILIZER** | **0** | 100 | **0** |
| **合计** | | | **168,840,两家农场分这一个池子** |

那一局两家终局合计 **193,845**(k06 104,927 + lena 88,918),与这个预算同量级——
**预算是真的**。

### 四、由此得到的四条结论

1. **FERTILIZER 不在任何店里,也不在 `TOWN_CENTER_PRODUCTS` 里——没有任何东西消耗
   它。** 它的库存只升不降,所以那是一个**深但永不再生**的一次性池子(~24k)。
   `muckman` 臂(`--fert-credit 0.3`)是在给一个**不再生**的收入线加权,它的量级
   `0.3 × 100 × 剩余天数`(第 8 天 660/只)**远高于它实际能变现的量**。这不是撤回,
   但预登记:如果 muckman 阴性,原因大概率在这里。
2. **MELON 只有镇中心消耗,1/天 = 一季 30 份。** 基价 250、势函数最爱、chisel 买了
   29 颗种子的那个作物,**是全场再生需求最薄的一个**。"西瓜被高估"这个结论对,但
   机械原因是需求而不是价格表。
3. **YARN_STORE 那一局没解锁,所以羊毛需求只有 30 份(6,000)而不是 360 份
   (72,000)。** 同样的 6 只羊,**收入差 12 倍**,只取决于解锁了哪家店。
   `agents/spar` 的 intel 轴里我们是 `blind`。
4. **今天早些时候那张"成交价"表,量的是"乱卖的后果",不是外生价格。**
   MELON 67、MILK 25、WOOL 64 恰好就是把薄池子砸到底之后的均价。所以
   **`assay`(收盘价)和 `grocer`(成交价)两条臂都是在拟合症状。** 这解释了为什么
   φ-vs-money 探针里成交价定价"从来没更好"。

### 五、这才是 43k–51k 那条带子的解释

φ 把产出按 `base × 0.5` 计价,**数量上无界**。真实收入**每个产品都被消耗量封顶**。
所以一个最大化 φ 的策略会**超产高基价作物**(西瓜 250、草莓 120)然后把它们倒进一个
会塌到 1 块的池子里。六条臂各改一个 φ 系数,改的都是**权重**,而错的是**无界**这件事。

**下一条臂 croftr(gen35)**:`--demand-cap` —— φ 对一个产品的预期产出,**只按
"剩余季内消耗量"以内的部分**按 base 计价,超出的部分按地板价计价。量级全部来自引擎
(`SHOPS` × `shop_interval` × 剩余天数 + `TOWN_CENTER_PRODUCTS` × 剩余天数),
**没有可调常数**。这是单变量,而且它打的是"无界"而不是"权重"。

### 同日续:按池子逐个算"我们漏了多少"——而**连冠军也在超产西瓜 4 倍**

有了需求侧的账本,就能把每个池子的**捕获率**量出来。方法:让对手是一个只 PASS 的
agent,于是市场库存的每一点变化都归我们;售出单位 = 库存增量 + 已知的镇消耗量
(店每 4 回合、镇中心每 24 回合)。

| 产品 | 镇要 (k06局/anvil局) | k06 售出 | 捕获率 | anvil 售出 | 捕获率 |
|---|---|---|---|---|---|
| STRAWBERRY | 299 / 569 | 248 | **0.83** | 51 | **0.09** |
| MILK | 227 / 425 | 236 | 1.04 | 241 | 0.57 |
| WOOL | 281 / 29 | 163 | 0.58 | −1 | ~0 |
| **CARROT** | 749 / 569 | 13 | **0.02** | −1 | **0.00** |
| WHEAT | 263 / 533 | 68 | 0.26 | **−213** | **净买入** |
| **MELON** | 29 / 29 | **119** | **4.10** | 32 | 1.10 |
| FERTILIZER | 0 / 0 | 246 | n/a | 183 | n/a |

终局钱:k06 **141,031**,anvil **77,009**(都对 PASS)。

**注意**:两局的"镇要"不同,因为**店的解锁与杂草共用一条 RNG**,而 RNG 又受双方动作
影响(CLAUDE.md 已记),所以消耗量那一列**不可跨 agent 精确比较**,只看方向。

### 三条读数

1. **我们的缺口是产量,不是选品。** 草莓池子我们只拿 **9%**,k06 拿 **83%**。φ 偏好
   草莓胜过胡萝卜(20 格 4,800 对 1,400)其实是**对的**——按池子算草莓
   569 × 120 = 68,280,胡萝卜 749 × 35 = 26,215。所以问题不是种错了,是**种太少、
   卖太少**。这与 seedsman / sackman / bulkhead / croftr 这一族的方向一致。
2. **我们是小麦的净买入方(−213 单位),而镇上想要 533。** 买小麦本身合理(8 头牛
   一季要 240 份),但 k06 养 14 只、要 420 份,却仍是**净卖出 68**——因为它**自己
   种小麦**(138 颗种子)。我们买饲料,它种饲料。
3. **连 k06 也在超产西瓜:卖出 119,而池子一季只要 29——4.1 倍。** 这是一个
   **预登记的机会**:`croftr` 的 `--demand-cap` 把 20 格西瓜的信用从 15,000 砍到
   2,799,而**冠军的这个错误它自己没有修**。如果 demand-cap 起作用,它应该在"西瓜
   种子数下降 + 草莓/小麦上升"这两个行为量上先看到,再反映到钱上。

**胡萝卜那一栏值得单独记一句**:镇上一季要 **569–749 份**(PET_CAFE 一天吃 12 份),
而 **k06 卖 13 份、我们卖 0 份**。按 base 35 那是 ~26k 的池子**几乎没人碰**。它单价低
所以按钱排在草莓之后,但它**种子只要 20、第 2 天就开始产、max_yield 4**——是全场
最便宜的吞吐。这不足以单独起一条臂(φ 的排序已经是对的),但如果 croftr 之后
产量真的上去了,**胡萝卜是下一个该看的池子**。

### 同日续二:**"按节奏卖"是阴性的,而这条阴性把需求判词的适用范围划清了**

既然 SELL 会自己把价格砸下去,那就给它设界:**卖到价格曲线的膝盖为止**
(`I0 − 当前库存`,卖到这里价格正好等于 base)。零重训 A/B,同一份权重,672 局:

| | 全抛(现行) | 按节奏 |
|---|---|---|
| HELDOUT | 2/4 | 1/4 |
| 中位钱 | **46,905** | 40,063 |
| p05 | 20,470 | 17,950 |
| <20k | 4% | 9% |
| 对 k06 margin | −74,920 | −90,579 |
| 对 main 胜率 | 72% | **22%** |

**界本身就是错的:市场库存的初值就是 I0**,所以 `I0 − 库存 ≤ 0` 从第一回合就成立,
这个选项**一整局每次只卖 1 个单位**,把农场的现金流掐死了。只能卖 1 的"节奏"不是
节奏,是静音键。

**但这条阴性的读数比臂本身值钱:在我们这个产量下,价格冲击根本不是约束。**
棚子总共只能放 100 件,草莓要一次卖 ~100 个单位才会塌,而**我们一整局只卖 51 个
草莓单位**(k06 卖 248,池子 299)。**当棚里从来装不满一种东西时,全抛就接近最优。**

**价格冲击只在池子真的很小的地方咬人:MELON,一季 29 份,连 k06 都超卖 4.1 倍。**
那个情形归势函数管(gen35 的 `--demand-cap` 已经处理),不归卖出解码管。

所以这条**收窄了**上一条判词的适用范围,而不是推翻它:需求账本解释的是**经济能付
多少钱**、并且给"势函数无界的作物信用"设了上界;它**不**意味着我们卖得节奏不对。
**我们的问题仍然是产量。**

已留在 gen36 里默认关、数字写进注释,免得有人再推一遍。

## 2026-08-22 · 解码层 2×2:**两个各自为正的修正合起来互相抵消**(非组合律第二次复现),而**解码这条杠杆只值 ±2k**

同一份 chisel 权重、零重训、672 局一格。两个因子:市场头 31 → 36(追加
`BUY_SEED_BULK`)、以及 `WHEAT_BUY_EXACT`(gen25 已采纳但**主树里仍然默认关**)。

| 格 | 中位钱 | p05 | <20k |
|---|---|---|---|
| ① 窄头 31,wheat 关(基线) | 46,905 | 20,470 | 4% |
| ② 头 36,wheat 关 | **48,919** | 20,061 | 5% |
| ③ 窄头 31,**wheat 开** | 48,665 | **21,569** | **3%** |
| ④ 头 36 **+** wheat 开 | 47,283 | **18,763** | 6% |

**各自 +1,760 / +2,014,合起来只剩 +378,而且尾部更差**(p05 21,569 → 18,763,
<20k 3% → 6%)。

档案里那条"动作层修正非线性叠加"是用 `WHEAT_BUY_EXACT` + `SEED_BATCH` 测出来的
(+0.3 胜率 / −398 收入)。**这次换了另一个第二因子,同样的抵消又出现了——所以那条
规则不是 `SEED_BATCH` 专属的,是解码层的普遍现象。凡组合必须自己做 A/B。**

**最好的单格是 ③(只开 wheat、保持窄头)**:它的 **p05 21,569 与 <20k 3% 都是四格
最好**,中位与 ② 在噪声内。用户此前已经指示"若候选获批,导出时打开
`WHEAT_BUY_EXACT`"——**这份读数独立确认了那个指示,并且补上一条:不要同时打开加宽头,
否则比只开一个更差。**

### 但这条判词最重要的部分是它的**上界**

**四格全部是 HELDOUT 2/4、对磁带 0/3**,四格的极差是 **2,014**。而到 2000 分的缺口是
**104,500 − 48,919 ≈ 55,600**。**解码层调参这条路整体只值 ±2k,是缺口的 3.6%。**

所以:`WHEAT_BUY_EXACT` 该在导出里打开(免费的 +1,760 和更好的尾部),但
**它不是路**。路仍然是产量——`seedsman`(种子供给,档案自己点出的"唯一还没有臂在攻的
一格")、`croftr`(需求封顶)、`bulkhead`(吞吐)、以及 backplay 的 d0 段。

### 顺带取消 sackman

`SEED_BURST`**替换** `BUY_SEED` 的数量,而这正是 gen25 的 `SEED_BATCH=6`——
**九对手已经判过:胜率 −2.1、收入 +2,708,被拒绝。** 我今天又造了一遍。
`project_tape` 的覆盖率下降(cleo 54.5 → 52.4、lena 35.2 → 33.4、bea 36.2 → 34.4)
正是它失败的机制:**替换会丢掉"只买一颗"**,而磁带平均每回合只发 1.05–1.64 个订单。
**`bulkhead` 与被拒的设计差别恰好在这一点:它是追加一个选项而不是替换**,所以它保留了
两种数量。sackman 的链已取消,GPU 让给 croftr。

**规则**:**起一条臂之前,先 grep 档案里有没有同名或同形的实验。** 我今天两次撞上
已存在的东西(`--fert-credit` 早就在 `trl_env.py` 里、`SEED_BATCH` 早就被判过),
一次造成重复计价、一次造成重跑已拒方案。

## 2026-08-22 · **CPU 训练不是 GPU 的替代品**(≥14× 慢),这条路封掉

今晚 GPU 排不上(fairshare:`EffectvUsage 0.899`、`FairShare 0.326`,优先级里 fairshare
占 1,630,148/1,632,442),而 CPU 的 array task 整夜秒开。所以问了一个此前没量过的
问题:**`rl/train.py --device cpu` 到底多慢?**

- B=1024 时 **48G 内存 OOM**(MaxRSS 50G),要 160G。
- 32 核 + 160G,**一个迭代跑了 8 分 42 秒还没完**,而 H100 上是 **37 秒**
  (bp12 的 it 125–129 实测 19,000–19,900 sps)。**至少 14 倍慢。**

**结论:封掉。** 3 小时的 CPU 作业约 20 个迭代,一整夜链起来 ~60 个;而它要占 32 核
+ 160G,CPU 的 fairshare(`0.438`,RawUsage 9.3 亿)也不是免费的。**用它换不到值得的
训练量**,而且会挤掉那些秒开的评测 array。

**顺带修掉一个我自己一小时前引入的回归**:`_atomic_save` 写 `path + ".tmp"` 再
`os.replace`,遇到**目标目录不可写**就炸——`--save /dev/null`(吞吐探针的正当用法)
去创建 `/dev/null.tmp`,`Permission denied`,在第一个检查点处杀死整个运行。真实的臂
都存到 `rl/runs/<run>/latest.pt`(可写),所以**没有链受影响**;但旧代码能处理这条
路径而新代码不能,这就是回归。现在加了回退:失败就清掉 temp、直接写。
**原子性是对 walltime 杀死的保险,不是硬要求。** 两条分支都验过。

**今晚的实际处境,说清楚**:十条臂的链与 array 花名册全部就绪、门全过
(`GATES-RC=0`),但 **GPU 份额今天已经用掉九成,所以没有一条训练臂能出结果**。
CPU 这条替代路径刚被量掉。**能在无 GPU 下做的都做了**——需求账本、逐池捕获率、
三次零重训 A/B(加宽头 +2,014、wheat +1,760、两者合起来只剩 +378)、以及
`PACED_SELL` 的阴性。**解码层整体只值 ±2k,是缺口的 3.6%,所以剩下的必须靠训练。**

### 同日尾注:换 GPU 型号也没用——瓶颈是 fairshare 而不是卡

把"今晚还能不能拿到训练结果"这条路走到底,三个出口全部量掉:

1. **CPU 训练**:≥14× 慢(上一条),封掉。
2. **MIG 切片**:`sinfo` 显示 g[30-32,34-36] 有空闲的
   `1g.10gb` / `2g.20gb` / `3g.40gb` 切片,看起来是个缺口。**但那些节点状态是
   `inval`,原因 `gres/gpu count repor…`**——集群侧的 gres 计数不一致,请求会挂在
   `ReqNodeNotAvail`。不可用。
3. **换 A100**(`o1` 有 `gpu:a100:8`、REASON `none`):提交后状态是 **`(Priority)`**,
   和 h100 一样。**所以瓶颈不是卡的型号,是 fairshare 优先级**
   (`EffectvUsage 0.899`,priority 里 fairshare 占 1,630,148/1,632,442)。

**没有再去给臂加 a100 备份提交**:两个型号的同一条链会写同一个 `latest.pt`,
**两个写者会互相毁掉检查点**;要避免就得用不同的 run 目录,那就变成两条不同的臂了。
在这种时候制造更多提交,风险大于收益。

**结论:今晚拿不到训练结果这件事是资源约束,不是还有没试的办法。** 队列里的十条臂
已就绪、门全过;巡检会在读数出现时接手。

## 2026-08-22 · `--kickstart tape:` 接好了:**用 150k 的磁带当老师,而不是 40k 的 barnyard**(已过门,**未提交**)

档案里今天早些时候自己点出过:"五代以来我们只把 150k 的磁带当**对手**打,从没模仿过
它们;而我们唯一的 kickstart 教师是 `barnyard`(约 40k)——**对 2000 分的目标来说是
错的教师**",并且列了 AlphaStar / VPT / OpenAI Five 的共同起点。标签工具
(`tape_labels.py`)也是今天写的。**缺的只是接线。**

`kickstart_labels(ep, player, teacher)` 现在接受 `"barnyard"` 或 `"tape:<agent.py>"`。
`TapeOpponent` 本来就在设备上按**同一套 unit-op 词表**输出 ops,而 `_ks_luts` 就是按
unit-op 索引的,所以 `_tape_ops_as_task` 是**换形状而不是翻译**。

### 弱点先说清楚,因为它决定阴性怎么读

**磁带是开环的**:它第 t 步的动作是为**它自己**的状态选的,不是学习者的。这一点能忍
只因为 `_kickstart_ce` **本来就跳过在学习者掩码下非法的标签**。门里量出来:

| 头 | 标签存活率 |
|---|---|
| farmer | **100%** |
| market | **约 50%** |

**所以市场头只拿到一半的监督——而市场头恰好是我们最需要被教的那个**(买种子归它管:
一局 47 颗对 k06 的 207)。`barnyard_t` 是个闭环、条件更好,它只是瞄着 40k。

### 门 `test_tutor.py` T1–T5(TUTOR-PASS)

T1 钉住 `teacher="barnyard"` 与出厂调用**逐位相同**;T2 三条磁带 × 三个天检查标签在
学习者自己的状态上合法且非空;**T3 钉住它与 barnyard 在 100% 的 lane 上不一致**
(两个一致的老师会让这条臂变成空操作);T4 钉住 `hands_n` 之后的槽是 −1、宽度是
`MAX_HANDS`;**T5 改成报告存活比例而不是要求全合法**——那是开环老师永远做不到的,
我这个门的第一版就错在这里。

### 未提交,以及提交时必须带的那个界

GPU 今晚被 fairshare 卡住(`EffectvUsage 0.899`,0 running / 41 pending),而队列已经
**刻意收窄到六条臂**,好让漏出来的算力落到 croftr / seedsman / bulkhead / backplay d0。
**第十一条臂只会稀释它们**,所以这条只备好、不提交。命令:

    RUN=rl/runs/tutor
    python rl/train.py --device cuda --max-minutes 25 \
      --config rl/configs/granger.yaml --init-from "$RUN/init.pt" \
      --opponents "tape:agents/bench3/closer_cleo.py,tape:agents/champ/k06.py" \
      --kickstart tape:agents/champ/k06.py --ks-coef 0.05 --ks-every 4 \
      --potential future-mkt --shape-gamma 0.999 \
      --hidden 1024 512 --v-hidden 512 --iters 425 \
      --save "$RUN/latest.pt" --resume "$RUN/latest.pt"

**`--ks-coef 0.05` 不是可调项,是 sower-v1 用三个迭代换来的界**:在**成熟**主干上重新
退火 kickstart 是一记铁锤——CE ≈1.2 对策略梯度 ≈0.03,**四十比一**,三个迭代就把一个
连贯的 42k 策略搅成半个 barnyard(胜率 0.436 → 0.000)。chisel 是成熟主干,**只能给
耳语级的 ≤0.05,绝不能给冷启动的 0.5**。

### 同日尾注二:花名册 array 路径已端到端验过,而且评测是**可复现**的

今晚把九个整块花名册拆成了 array(每对手一个 task),但**那个 `ros_array.sh` 从没真跑
过**——十条臂的读数全压在它上面,而"跑完几小时 GPU 然后打印一张空表、正常退出"正是
这个项目记录过的失败模式。所以拿一个**已有的**检查点(gen28 的 gleaner,step 75)跑了
两个 task:两个都 COMPLETED,各自导出到自己的目录、写出 JSON、打出 `ROS-TASK-DONE`。

**顺带得到一个此前没写下来的性质:评测路径是可复现的。** 那两个 task 覆盖掉了 gleaner
真实结果里的 `closer_cleo.json` 与 `ledger_lena.json`,而重读整个目录后**判词逐位复现**:

    BEATEN heldout 7/10  trained 0/3 | p05 22,428  median 51,109  <20k 3%  (1248 episodes)

与此前记录的完全一致。**所以同一个检查点重跑同一批种子给出同一个数,重读花名册是安全
操作**——这条以后可以省掉"要不要重跑"的犹豫。

(能这样是因为 `docs/VALIDATING.md` 那条"给定 `(seed, 双方 agent)` 对局是确定性的"。
这次是它在**导出 + 评测整条链**上的确认,不只是引擎层。)

## 2026-08-22 · `penner` 判词:**动作打出去了,畜群反而更小** —— 词表这条线到此为止

`PLACE_BUILDS` + `CARRY_COMPLETES`(gen27),1,248 局,13 个对手:

    BEATEN heldout 7/10   trained 0/3 | p05 22,328  median 50,639  <20k 3%

**落在带子里,而且低于它本要修的那个设计**(stockman 51,344,差 705,在噪声内):

| 臂 | 变量 | HELDOUT | 中位钱 |
|---|---|---|---|
| stockman | 帮手 BUILD+PLACE 两个独立任务 | 7/10 | **51,344** |
| gleaner | `--harvest-urgency` | 7/10 | 51,109 |
| **penner** | `PLACE_BUILDS`+`CARRY_COMPLETES` | 7/10 | **50,639** |
| furrow | `--land-value 2500` | 7/10 | 48,703 |
| grange | — | 6/10 | 46,268 |
| longhaul | 长链对照 | 5/10 | 43,355 |

### 机制:它修好了零梯度,然后**把畜群喂死了**

stockman 的病是零梯度(帮手拿到 BUILD/PLACE,一整局用了 2 次和 0 次)。penner 修好了
这一点——**帮手 PLACE 0→4、BUILD 2→25,动作确实打出去了**。但按判据量行为:

| | penner | anvil(基线) |
|---|---|---|
| 象限(第 18 天) | 2.0 | 2.0 |
| 作物 | 24 | 26 |
| **兽** | **4** | **6** |
| 每回合帮手 | 7.78 | 7.90 |

**土地没到 3、帮手没从 7.9 抬起、而畜群从 6 掉到 4。** 一条以"让帮手多建栏多放兽"为
目的的臂,**结果是兽更少**。

机制是引擎的维护成本:`FEED` 每只动物**每天恰好 1 份小麦**,**连续两天没喂就失去那只
动物**(引擎第 814–817 行)。帮手的时间被 BUILD/PLACE 占掉,就从 FEED / WATER /
COLLECT 那里挪走了——**盖了更多栏,却喂不动已有的兽**。

**这正是清单第 (i) 条的同族**:"有余量的劳力下贪心最近近优,调度类改动别再试"——那七个
动作层标志六个被否就是这条。penner 补上的新一句是:**当劳力是维护的瓶颈时,重排它的
去向不是零收益,而是负收益**——因为维护漏掉的东西会**死掉**,不是只是没产出。

### 收束:词表 / 动作层这条线,八次里七次阴性

`SEED_BATCH`(−2.1 胜率)、`BUSY_HANDS`、`IDLE_FERTILIZES`、`PLANT_BY_VALUE`、
`FEED_FIRST`、`HERD_SHEEP`、`VALUE_SCHED`、stockman、penner —— **只有
`WHEAT_BUY_EXACT` 是正的(+2.1 / +3,368),而它和加宽头一组合就抵消掉**
(今日 2×2)。**加上"解码层整体只值 ±2k = 缺口的 3.6%",这条线可以宣布关闭。**

剩下的四条都在**别的**层:`croftr`(需求封顶,打 φ 的**无界**)、`seedsman`(种子供给
的即时亏损)、`bulkhead`(吞吐,追加而非替换)、backplay 的 d0 段(开局分布)。

### `penner` 判词补两笔(用新的 `tools/arm_behaviour.py` 统一量出来)

把行为读数收进一个工具后,penner 那条判词多出两个数:

| | penner | anvil(基线) | k06 |
|---|---|---|---|
| 空着的已解锁格子 d18 / d28 | **12 / 11** | 18 / 25 | 2 / 5 |
| 一局买的西瓜种子 | **19** | 9 | 20 |
| 一局买的草莓种子 | 32 | 38 | 34 |

**一、penner 的地其实填得更满**(d18 空 12 对基线 18、d28 空 11 对 25),**却更不赚钱**。
所以"空地"这个判据**不是单调的**——把地填满但填错东西,比留空更糟。这一条要写进判据的
读法里。

**二、它买了 19 颗西瓜种子,是基线的两倍**,而西瓜一季的镇上需求只有 **30 个单位**。
**注意归因**:penner 只改了帮手的 BUILD/PLACE,西瓜是市场头买的,所以这**不是那个标志
的机械后果**,是训练轨迹的差异。但它说明**超买西瓜在我们的检查点里是普遍现象**
(anvil 9、penner 19、chisel 29),而这正是 `croftr` 的 `--demand-cap` 要压的那一项——
第 8 天 20 格西瓜的信用从 15,000 砍到 2,799。

**判据修订**:"空着的已解锁格子"要和"填的是什么"一起读。penner 填得更满、买了更多
西瓜、拿到更少钱——三件事是一致的。

## 2026-08-22 · `repack` 完成:候选 `hybrid-d12final20` 已在 d12 链尾重建并过完整验收链

作业 20300279 在 `kg-bp12` 的最后一个 link(20294391,30:19 后 TIMEOUT——这是我把
walltime 砍到 30 分钟的预期行为,`_atomic_save` 保住了检查点)之后自动跑完:

    BEATEN heldout 5/7   trained 0/2 | p05 51,930  median 90,255  <20k 0%   (864 局)
    MIRROR  win 45.8%  margin +0  ci [-884, 900]
    stress  28/28 clean, worst 50.3 ms
    get_last_callable -> agent()   解包后整局: [117,024, 3,532]
    submissions/2026-08-22-hybrid-d12final20/submission.tar.gz  20,305 KB

| 候选 | 中位 | p05 | <20k |
|---|---|---|---|
| hybrid-d12net20(it66) | **90,788** | — | — |
| **hybrid-d12final20**(链尾重建) | **90,255** | **51,930** | **0%** |
| hybrid-endgame20 | 88,810 | — | — |

**链尾重建没有超过更早的 d12net20 快照**(90,255 对 90,788,差 533,在噪声内)。
所以"训练更久的 d12 尾巴会更好"这个预期**没有实现**——两者同级。

**但 `p05 51,930` 与 `<20k 0%` 值得单独记**:我们的纯网 p05 在 20k 附近、
2–9% 的对局收在 2 万以下,而这个候选**一局都没有崩**。脚本开局买来的不只是中位数,
更是**尾部**。

### 一个必须在批准前说清的事实:**这个包里没有 `WHEAT_BUY_EXACT`**

指示是"若获批,导出时打开 `WHEAT_BUY_EXACT`"。**但打包件里根本没有这个常量**——
`kg_rl_actions_d12_final.py` 里一个都没有,因为 repack 从 **gen23**(backplay 树)导出,
而那棵树在这个标志出现之前就分出去了(第 444 行仍是
`return [["BUY_PRODUCT", "WHEAT", max(5, 2 * herd)]]`)。

**所以那不是"翻一个开关",而是:把标志移植进 gen23 → 重新导出 → 重跑验收链。**

而且**它的收益是在纯网上量的,不是在 hybrid 上**:今晚 2×2 里 `WHEAT_BUY_EXACT`
单开给出中位 +1,760、p05 21,569、<20k 3%(chisel 权重、7 对手)。**这个候选是
p05 51,930 / <20k 0% 的完全不同的机制区间**,那 +1,760 不能直接搬过来。**要用就该在
hybrid 上重测一次,而不是假定。** 我没有动它,也没有提交。

## 2026-08-22 · `WHEAT_BUY_EXACT` 在 **hybrid** 上不起作用:纯网上的 +1,760 搬不过来

指示是"若候选获批,导出时打开 `WHEAT_BUY_EXACT`"。但那个 +1,760 是在**纯网**上量的
(chisel 权重、7 对手、p05 21,569、<20k 3%),而候选处在 **p05 51,930 / <20k 0%** 的完全
不同区间。既然它是提交前的决定,就先测了。

方法:标志**手工打进"已构建的 hybrid agent 目录的一份拷贝"**——gen23(repack 的导出
树)分支早于这个常量,所以包里根本没有它;这样做不碰任何有排队链的树。9 个对手 ×
48 种子 × 双席 = 864 局一臂。

| | 打包件原样 | + `WHEAT_BUY_EXACT` |
|---|---|---|
| HELDOUT | 5/7 | 5/7 |
| 中位钱 | **90,255** | 90,193(**−62**) |
| p05 | **51,930** | 50,459(−1,471) |
| <20k | 0% | 0% |

**逐对手的 margin 全部在几百之内**(w49 略好:−21,631 → −21,442、中位 72,410 → 74,080;
cleo 胜率略差:15.6% → 12.5%)。864 局下 −62 的中位差**深在噪声里**,所以正确的说法是
**"测不出效果"**,不是"更差"。

**标志确实在动**:小麦成品采购 **748 → 419**(砍掉 44%),money 在单个种子上 +2,280。
所以这不是"没生效",是**生效了但换不成钱**。

**机制**:30 天里有 20 天是 cleo 的录音,**标志只能在第 20–29 天起作用**(那之后才由网
接手),而那时农场的饲料需求正被录音期积累的库存覆盖着。它省下的现金没有一个能变成
产出的去处——**这与今晚的中心判词一致:解码层的钱在别处,产量才是缺口。**

### 对提交决定的结论

**若候选获批,直接发打包件原样即可,不要做那个移植。** 移植 `WHEAT_BUY_EXACT` 需要
"改 gen23 → 重新导出 → 重跑验收链"三步,而它在这个候选上**买不到东西**。那条指示对
**纯网**产物仍然成立(+1,760、p05 与尾部四格最好),只是**不适用于 hybrid**。

## 2026-08-22 · 把录音开局往**短**的方向扫:**分数几乎与录音天数成正比**,而"网自己该学会建的每一天"值约 3.5k

候选的问题是 30 天里 20 天是录音。所以往**短**的方向扫——若 8/12/16 天能守住分数,产物
就是"同样的分数、更多的 RL"。同一份 `d12-final` 权重,只改开局长度,9 对手 × 48 种子 ×
双席 = 864 局一臂:

| 录音天数 | HELDOUT | 中位钱 | p05 | <20k |
|---|---|---|---|---|
| **20**(打包件) | 5/7 | **90,255** | 51,930 | 0% |
| 16 | 5/7 | 82,506 | 49,885 | 0% |
| 12 | 5/7 | 72,880 | 48,341 | 0% |
| **8** | 4/7 | **47,549** | 32,148 | 0% |

**没有便宜的减法。** 每少 4 天录音,中位掉 **7,749 / 9,626 / 25,331**(加速下坠),
而 **8 天时它掉进 47,549——正是我们纯网那条 43k–51k 的带子里**。

**所以 hybrid 的全部优势就是那 20 天录音本身,而且几乎线性。** 我们的网**接手**一个
20 天录音建好的农场能挣 90,255,接手一个 8 天建的只有 47,549 ——
**网自己的贡献大致是平的、也是小的;变的是它继承到的那个农场。**

### 这给缺口定了价

从 8 天(47,549)到 20 天(90,255)是 **12 天的建设值 42,706**,即
**"网自己该学会建、而现在建不出来的每一天,约值 3.5k"**。要"用 RL 达到
104,500",网就得自己学会**大约这 12 天的建设,再多一点** —— 这是第一次把
"开局缺口"换算成一个**每天的价格**,而不是一个总额。

### 一个反向的分解:尾部的好处来得早,中位的好处是线性累积的

注意 `<20k` 在**四个长度上全是 0%**,而 p05 即使在 8 天也有 **32,148**
(纯网是 ~20k、2–9% 的对局收在 2 万以下)。**所以录音的"防崩"作用在头 8 天就基本
拿到了,而"抬中位"的作用要一天一天累积。** 这两件事是可分的,而我们此前一直把它们
当一件事说。

**对提交决定的含义**:**不要为了"更像 RL"去缩短开局**——缩到 12 天要付 17.4k,缩到
8 天等于放弃全部优势。若批准,就发 20 天那个原样(且按前一条判词,**不要**做
`WHEAT_BUY_EXACT` 的移植)。**而"用 RL 达到 2000"这道题的答案仍然只能来自让网自己
建farm**,那正是 croftr / seedsman / bulkhead / backplay-d0 四条臂在攻的位置。

### 同上,更锐的一刀:**贵的不是"每天 3.5k",贵的是第 8–11 天(6,333/天)**

把同一组数按**边际**读——"网自己打这 4 天"要付多少:

| 网自己打的那 4 天 | 中位损失 | 每天 |
|---|---|---|
| 第 16–19 天 | 7,749 | **1,937** |
| 第 12–15 天 | 9,626 | 2,406 |
| **第 8–11 天** | **25,331** | **6,333** |

**"平均 3.5k/天"掩盖了 3.3 倍的差异。** 网在**第 16–19 天几乎能自己应付**
(1,937/天),而**第 8–11 天是它最崩的窗口**(6,333/天)。

### 这直接指出反向课程缺了哪一段

`backplay` 的分段是 **d20 → d16 → d12 → d0**。**它没有 d8 那一段**,而 d8–d11 恰好
就是最贵的窗口;`d12 → d0` 这一跳**整段跳过了它**。

这也解释了那条早先的判词"链不向前迁移":从第 0 天起 chisel −54,849 而 d12 −90,494
—— **d12 段学的是"接手一个第 12 天的农场",而它从没见过第 8–11 天那段建设**,所以
从 d12 直接跳到 d0 等于让它在最贵的窗口上从零开始。

**建议(单变量、可立即准备)**:在 d12 与 d0 之间**插一个 d8 段**。银行可以**现在就用
CPU 生成**——今晚已入库的 `make_bank.py --driver tape:<agent.py>` 就是为此:用磁带在
**双席**上跑到第 8 天再 fork,于是起始分布是"一个第 8 天的、由 1364 段位建起来的农场"。

### 更正 + 补一个更强的第 8 天银行

**我上一条里说"现有的银行是 barnyard 建的"——错了。** 我看的是**主树**的
`data/banks/`(里面是 `barnyard-0168/0264/0360`);**gen23 自己的银行是 cleo 磁带驱动的**,
而且**已经有第 8 天那一份**:

| 银行 | 天 | 作物 | 兽 | 象限 | 钱 | 空地 |
|---|---|---|---|---|---|---|
| cleo-0096 | 4 | 19.0 | 4.0 | 0.0 | 405 | 2.0 |
| **cleo-0192** | **8** | **27.0** | **7.0** | 1.0 | 684 | 15.9 |
| cleo-0288 | 12 | 37.8 | 14.0 | 2.0 | 10,196 | 21.8 |
| cleo-0384 | 16 | 55.5 | 14.0 | 2.0 | 21,653 | 3.8 |
| cleo-0480 | 20 | 55.5 | 14.0 | 2.0 | 35,656 | 4.8 |
| **k06d8-0192**(新) | **8** | **30.0** | **9.0** | 1.0 | 40 | 9.9 |

所以**缺的不是银行,是训练段**:`rl/runs/` 里有 `endgame` / `backplay-d16` /
`backplay-d12` / `d0-chisel` / `d0-d12`,**没有 `backplay-d8`**——而 d8–d11 正是
6,333/天 的那个窗口。我生成的 `cleod8-0192.pt` 与 `cleo-0192.pt` 逐位相同,已删。

**新的那一份 `k06d8-0192.pt` 是真的补充**:k06 的第 8 天比 cleo 的**更强**
(作物 30 对 27、兽 9 对 7、空地 9.9 对 15.9),代价是现金只剩 40(它全花光了)。
若要开 d8 段,**这两份银行本身就是一个单变量 A/B**:同一天、同一课程、只差
"继承谁的农场"。

**为什么这可能比再调一个势函数系数值钱**:d12 段收官在 margin −7.7k、对 cleo 胜率
11–14%,而它继承的是 cleo 的第 12 天(37.8 作物 / 14 兽)。**k06 的第 12 天是 55 作物**
——差 17 格地。如果"继承到的农场质量"本身就是天花板,那么换银行比换奖励更直接。

### 已开:`backplay-d8` —— 补上反向课程缺掉的那一段(并放掉 bulkhead 换 GPU)

三条今晚的测量串成一条线,所以这一段值得开:

1. **录音天数与分数近乎线性**(20/16/12/8 天 → 90,255 / 82,506 / 72,880 / 47,549);
2. **边际最贵的是 d8–d11**:网自己打这 4 天要付 **25,331 = 6,333/天**,而 d12–15 是
   2,406/天、d16–19 只有 1,937/天;
3. **`rl/runs/` 里没有 `backplay-d8`** —— 段是 d20 → d16 → d12 → d0,**那一跳整段
   跳过了最贵的窗口**,这正好解释此前"链不向前迁移"(第 0 天 chisel −54,849 对
   d12 −90,494):d12 段学的是"接手第 12 天的农场",而它从没见过 d8–d11 的建设。

**单变量就是"加这一段"**:同一个 `backplay_link.sh`、同一套**累积** cleo 银行
(脚本按 `seq BP_DAY 4 20` 自动装上 d8/12/16/20)、继承 d12 的尾巴。
链 20313640-44 + 花名册 array 20313645 + 读数 20313646。

**判据**:HELDOUT 中位过 **51,344**;以及**第 0 天整局 margin 要好过 chisel 的
−54,849**(这是 d0 两条臂共用的那把尺子)。

**放掉了 `bulkhead` 来换这段的 GPU**:它在词表层,而那条线**已由 penner 收官关闭**
(八次七负),它的零重训 +2,014 也落在"解码层整体 ±2k"这条噪声带里。**用同样的算力
去测一个 6,333/天 的窗口,比去测一个 ±2k 的层更值。**

**第二个单变量 A/B 已备好但没开**:`data/banks/k06d8-0192.pt`(k06 的第 8 天:
30 作物 / 9 兽 / 空地 9.9,对 cleo 的 27 / 7 / 15.9)。同一天、同一课程,**只差
"继承谁的农场"**。若 d8 段本身为正,这就是紧接着该问的问题。

## 2026-08-22 · **判据自查:那条 43k–51k 的带子是在不等的训练量下比出来的**

检查在跑的臂是否在正常累积检查点(五条正常、日志无报错、`backplay-d8` 还没开始所以
没有检查点),顺手把**判词时的迭代数**列出来——结果暴露了我自己读法上的一个缺陷:

| 臂 | 判词时 iter | steps | 判词 |
|---|---|---|---|
| **penner** | **256** | 189,217,792 | 50,639 阴性 |
| stockman | 119 | 88,350,720 | 51,344(带子最好) |
| **gleaner** | **75** | 55,955,456 | 51,109 阴性 |
| **furrow** | **74** | 55,219,200 | 48,703 阴性 |
| croftr(在跑) | 45 | 33,867,776 | — |
| seedsman(在跑) | 94 | 69,944,320 | — |
| muckman(在跑) | 88 | 65,526,784 | — |

**两个方向的结论:**

**一、penner 的阴性比我说的更强。** 它拿到 **256** 迭代——是 gleaner 的 3.4 倍、
stockman 的 2.2 倍——**训练最多,却排在三者最后**。所以"动作打出去了、畜群反而更小"
不是训练不足,是那条路本身不通。

**二、但 gleaner(75)与 furrow(74)是在不到 penner 三分之一的训练量下被判负的。**
它们的"阴性"**可能只是训练不足**。特别是 `furrow`(`--land-value 2500`,攻土地),
它被判词时只有 74 迭代,而带子最好的 stockman 有 119。**这两条应当降级为"未定"
而不是"阴性"。**

**成因**:(a) 各条链原本的 link 数就不同;(b) 我今晚为贴合 backfill 把 walltime 从 55
分钟砍到 30 分钟,于是**后开的臂每个 link 拿到的迭代更少**。两件事叠加,使"同一把尺子"
其实不同长。

**对今晚中心判词的影响,说清楚**:我说过"六条臂彼此只差 8k,而共同缺口 60k,所以差异
小于缺口"。**那个 8k 的比较是被训练量污染的**,不能用来排臂间高下。但**不受影响的是
那句共同结论**——七条臂(含 penner 的 256 迭代)**全部远低于 104,500、全部对三条磁带
0/3**,而这与训练量无关。**"势函数系数这一族改不动量级"这个结论站得住;"哪一条系数
稍好"这个排序站不住。**

**判据修订**:**花名册读数必须附上判词时的迭代数**,否则不同臂不可比。在跑的三条会在
~135(seedsman/muckman)与 ~240(croftr)出读数,与 stockman 的 119、penner 的 256
大致同量级——可比。**而 gleaner 与 furrow 若要定论,得补训到同一量级再读一次。**

### 更正:`furrow` 的 `--land-value` 是 **5000**,不是我写的 2500(档案里错了四处)

检查点的 `args` 里 `land_value: 5000.0`,`iter: 74`。**用户的提示词一直是对的,是我在
本文件里四处写成了 2500**,并且在几轮汇报里重复了这个错。以此更正为准:

> `furrow`(主树)= `--land-value **5000**`,判词时 **74 迭代**,
> HELDOUT 7/10、中位 48,703、对磁带 0/3。

这个数字错得不算无害:势函数原本给一块地 300,而地价是 1000/2000/4000。**5000 意味着
买地的 shaped reward 从 −700/−1700/−3700 变成 +4000/+3000/+1000(全部转正)**;而 2500
只会让第一块转正(+1500)、后两块仍然是负(−500/−2500)。**所以这条臂比我描述的激进
得多**——它把三块地全部变成了正收益,而结果仍然只有 48,703。

### 已开:`furrow` 与 `gleaner` 的补训(不是新臂,是同一配置继续训)

上一条自查说这两条是在 74–75 迭代下被判负的,而带子最好的 stockman 有 119、penner 有
256,**所以它们的"阴性"可能只是训练不足**。补训两个 link(≈+96 迭代 → 约 170),
然后重读花名册:

- `furrow`:链 20314196-97 + array 20314198 + 读数 20314199
- `gleaner`:链 20314200-01 + array 20314202 + 读数 20314203

**这不违反单变量**:配置一个字没改,只是 `--resume` 继续训到可比的量级再读一次。
**判词必须附迭代数**,否则臂间不可比(上一条已入档的判据修订)。

## 2026-08-22 · `muckman` 判词:**带子里最好的一条**,而我预登记它会是阴性 —— **预登记错了,而且错在哪里可以指出来**

`--fert-credit 0.3`(gen31),1,248 局、13 对手,**判词时 iter 133**:

    BEATEN heldout 7/10   trained 0/3 | p05 23,437  median 52,377  <20k 2%

按迭代数排好的带子(判据修订后必须附 iter):

| 臂 | iter | 中位钱 | p05 |
|---|---|---|---|
| **muckman** | **133** | **52,377** | 23,437 |
| stockman | 119 | 51,344 | 23,705 |
| gleaner | 75 | 51,109 | 22,428 |
| penner | 256 | 50,639 | 22,328 |
| furrow | 74 | 48,703 | 18,682 |

**+1,033 相对 stockman、训练量相近(133 对 119)。这在噪声里,所以正确的说法是
"与 stockman 同级、居带子之首",不是"胜出"。** 它仍然对三条磁带 0/3,离 104,500 还差
52k。

### 我的预登记错了,而错因是只算了一个通道

我预登记过:"若 muckman 阴性,最可能因为**化肥的镇消耗恒为 0**"(它不在任何
`SHOPS` 里、也不在 `TOWN_CENTER_PRODUCTS` 里,库存只升不降)。**结果它不但不阴性,还是
带子最好的一条。**

行为读数指出了通道:

| | muckman | stockman | anvil(基线) |
|---|---|---|---|
| **畜群** | **6** | 5 | 6 |
| **第 0 天整局 margin** | **−49,850** | −53,268 | −64,731 |
| 一局种子 / 其中西瓜 | 45 / 16 | 42 / 16 | 47 / 9 |
| 土地 | 2.0 | 2.0 | 2.0 |

**`--fert-credit` 抬高的是"动物"的信用,而畜群从 5 变成 6。** 而动物产的
**MILK 是全场最大的可续收入线(一局 59,520)**、WOOL 次之——**两者都有镇上需求。**
所以这一项**很可能是通过畜群→奶/毛起作用的,而不是通过化肥**。

**我错在只顺着它名义上的通道(化肥)推,没有算它实际抬高的那个量(动物)。**
这正是清单第 (g) 条"压在某奖励项上的臂,事后要回去读那段代码"的反面教训:我读了
`_A_BASE` 只含产品基价、也读了化肥消耗为 0,却没问"这一项到底把**什么**的信用抬高了"。
**一个奖励项的名字不等于它的作用通道。**

### 顺带:muckman **过了课程臂那把尺子**

第 0 天整局 margin **−49,850,好过 chisel 的 −54,849**(stockman −53,268 也过,
anvil −64,731 没过)。那把尺子本来是给 `d0-chisel` / `d0-d12` / `bpd8` 用的,
**而一条势函数臂顺手过了**——说明"第 0 天 margin"这个判据**不是只有课程能动**。
(2 个种子的读数,噪声大,只看方向。)

**共同结论仍然不变**:八条臂全部对磁带 0/3、全部远低于 104,500。**土地全部停在 2.0、
一局种子 42–47(k06 是 207)、西瓜两条臂都买到 16(基线 9)。** 后面这一项正是
`croftr` 的 `--demand-cap` 要压的,而它还在跑。

## 2026-08-22 · `seedsman` 崩了:**我造了一台奖励泵,而我的门问错了问题**

`--seed-credit 0.5`(gen32),1,248 局、13 对手,**iter 147**:

    BEATEN heldout 4/10   trained 0/3 | p05 99  median 18,844  <20k 51%

**这不是边际阴性,是崩溃**:对 k06 中位 **384**、对 w49 中位 **158**,而且**输给
barnyard(0%、−34,320)和 grazier(0%)**——那是其他每条臂都以 85–100% 打赢的对手。

### 机制:它囤了 266 颗西瓜种子

| | seedsman | anvil(基线) |
|---|---|---|
| 一局买的种子 | **332** | 47 |
| 其中**西瓜** | **266** | 9 |
| 站着的作物 | **12** | 26 |
| 畜群 | 3 | 6 |
| 第 0 天整局 margin | **−103,277** | −64,731 |

因为这一项把持有的种子按 `0.5 × (max_yield × base × PLANT_CREDIT)` 计价:

| 作物 | 种子价 | 持有信用 @0.5 | **买入的净 φ** |
|---|---|---|---|
| WHEAT | 10 | 38 | +28 |
| CARROT | 20 | 35 | +15 |
| STRAWBERRY | 100 | 120 | +20 |
| **MELON** | **80** | **375** | **+295** |

**买一颗西瓜种子是 +295 的塑形奖励。** 策略不需要种、不需要浇、不需要卖——**只要买
就行**。这正是档案里那条"五次运行囤了 62–100 个西瓜,因为势函数把死库存按 48 倍市价
计价"的旧病,换了个入口重现。

### 我的门为什么没抓到:问错了问题

`test_seed.py` 的 S3 我明确测了"**在 w=0.5 每笔买入转正、且种植仍为正**",并且推理
"w=1 会把 PLANT 归零、放出囤货,所以 0.5 安全"。

**但正确的问题不是"PLANT 还正不正",而是"只买不种在 φ 里赚不赚"。** 在 +295/颗西瓜
的情况下,答案是"赚得极多"。**PLANT 为正并不能阻止囤货——只要买入本身足够正,策略
就永远不必走到 PLANT 那一步。**

**判据新增一条(给所有"给持有资产计价"的项)**:不只要问"下一步动作是否仍为正",
**必须单独问"买入并持有这个资产、什么都不做,在 φ 里是不是正收益"。** 若是,那就是
一台泵,与后续动作的奖励无关。

### 而这条崩溃直接指向 `croftr`:两项必须合起来测

**我今晚早些时候已经测出西瓜的问题**:base 250、成交价 67、**而一季的镇上需求只有
30 个单位**。`--seed-credit` 用的是 `max_yield × base`,**所以它满强度继承了西瓜那个
被吹起来的 base**——我造这一项时没有把这两个已知事实连起来。

`croftr` 的 `--demand-cap` 恰好是修那个的:第 8 天 20 格西瓜的信用从 15,000 砍到
**2,799(0.19×)**。**所以 `--seed-credit` 与 `--demand-cap` 必须合起来测,而不是分开**:
单开 seed-credit 是泵,单开 demand-cap 只封产量,而两者合起来会把持有一颗西瓜种子的
信用压到 0.19 × 375 ≈ **71**,低于它 80 的成本——**泵就没了**。

**下一步(等 croftr 的读数出来再定)**:把 `--seed-credit` 移植进 gen35(它已有
`demand_cap`),按"seed-credit + demand-cap"作为**一个**组合臂测,并在门里补上那条
"买入并持有必须非正"的检查。**注意这不违反单变量**:seed-credit 已被单独测过(崩),
demand-cap 正在被单独测,组合是第三个需要自己 A/B 的东西——档案里"势函数项非线性
叠加"那条规则要求的正是这个。

## 2026-08-22 · `furrow` 定案:**判据达成了、而且超额,钱反而更差** —— 土地不是约束,填地的现金与种子才是

补训后重读(`--land-value 5000`,主树,**iter 164**,对比它 74 迭代时的 48,703):

    BEATEN heldout 7/10   trained 0/3 | p05 16,571  median 47,511  <20k 8%   (1248 局)

**补训没有救它**(47,511 对 48,703,−1,192 在噪声内;p05 16,571 对 18,682、<20k 8% 对
6% 反而略差)。**所以这条判词现在是安全的阴性**,在与 muckman(133)、stockman(119)
可比的训练量下。

### 但它在**你指定的判据上完全达成了,而且超额**

| | furrow @164 | anvil(基线) | 天梯 |
|---|---|---|---|
| **象限** | **4.0** | 2.0 | 3.0 |
| **空着的已解锁格子 d18 / d28** | **66 / 64** | 18 / 25 | 2 / 5 |
| 首块地买在 | 第 10 天 | 第 10 天 | — |
| 站着的作物 | 23 | 26 | 37–61 |
| 钱(2 种子) | 29,717 | 53,762 | — |

判据是"**象限是否到 3**"——它到了 **4**,把四个象限全买下来了(`--land-value 5000` 让
三次买地的 shaped reward 变成 +4000/+3000/+1000,全部转正)。**而它把 66 格地空着。**
它为从没填过的地付了 1000+2000+4000 = **7,000**。

("首块地是否提前到第 6–7 天"这一条**没有**达成:仍然是第 10 天,与基线相同。所以
`land_value` 改的是"买几块",不是"什么时候买第一块"。)

### 两个方向都失败,而这恰好定位了真正的约束

- **奖励买地**(`--land-value 5000`):象限 2 → **4**,空地 18 → **66**,钱 53.7k → 29.7k。
- **惩罚空地**(`--idle-land`,今晚已撤回):BUY_LAND 本来已经是 −700,再加 −1,800
  会**压制买地**本身。

**所以"土地"这一维在两个方向上都推不动钱:给它加价就买一堆空地,给空地罚款就不买地。
真正的约束不是土地,是填满土地所需的现金与种子。** 这与今晚另外两条独立测量吻合:
一局买的种子 42–47 对 k06 的 **207**;而 `seedsman` 想修种子供给,却因为满强度继承了
西瓜被吹起的 base 而变成一台奖励泵(囤 266 颗西瓜种子)。

**判据修订**:"象限是否到 3" **不能单独作为判据** ——必须与"**空着的已解锁格子**"一起
读。furrow 把象限判据做到 4 而空地做到 66,是这条修订的直接证据。这与 penner 那条
"填得更满但填错东西比留空更糟"互为镜像:**土地类判据必须成对读(买了多少 / 填了多少)。**

## 2026-08-22 · 收束三条阴性:**它们都做到了自己瞄准的那件事,而都因为"互补品缺位"而失败**

今晚三条已定案的阴性,机制是同一个:

| 臂 | 它抬高的量 | **确实动了** | 缺的互补品 | 结果 |
|---|---|---|---|---|
| `penner` | 帮手能建栏/放兽 | PLACE 0→4、BUILD 2→25 | **饲料**(每兽每天 1 小麦,断 2 天就死) | 畜群 6→**4** |
| `furrow` | 买地的信用(+4000/+3000/+1000) | 象限 2→**4** | **种子与现金** | 空地 18→**66** |
| `seedsman` | 持有种子的信用 | 一局种子 47→**332** | **种下去**(买入本身已 +295/颗西瓜) | 作物 26→**12**,中位 18,844 |

**三条都不是"没生效"——三条都精准地生效了,然后把现金变成了一件闲置资产。**

### 这把清单第 (e) 条推广了

档案原本写的是"**浇水 / 施肥 / 收获是乘性互补,单动作补丁打不动乘积**"。今晚的三条说
这条规律**不限于那三者,而是贯穿整条资产链**:

> **土地 × 种子 × 劳力 × 饲料 全都是互补品。单独抬高其中任何一个,得到的不是产出,
> 而是一件闲置资产 + 少掉的现金。**

penner 有栏无料、furrow 有地无种、seedsman 有种不下地——**同一个错误的三个投影。**

### 而这条规律预测 `croftr` 不该栽在同一处

`--demand-cap` **不是"抬高某件资产的信用"**,它是**取消一个错误的高估**(西瓜的 base
250 对一季 30 单位的需求;20 格西瓜的信用 15,000 → 2,799)。**它减的是分子而不是加的是
资产**,所以它不引入新的闲置资产,不受这条失败模式支配。**这是一个可以事先说出来的
区分**,而它也解释了为什么 seedsman 的解药正是 croftr:两者合起来会把持有一颗西瓜种子
的信用压到 ≈71 < 成本 80,泵消失。

**预登记**:若 croftr 也阴性,那么按这条规律它的失败**不应该**表现为"某件资产闲置",
而应该表现为"**产出结构变了但总量没变**"——即西瓜种子下降、草莓/小麦上升,而中位不动。
**那会是完全不同的一种阴性,读法也不同。**

### `backplay-d8` 第一次提交是我的 bug:四个 link 在 2 秒内全 FAILED

`d8_link.sh` 用 `exec <path>` 调 `backplay_link.sh`,而后者**没有可执行位**——
`Permission denied`,四个 link 各在 0–2 秒内失败,**这条臂根本没训练过**。

**但花名册诚实地报了 "0 of 13 opponents present" 而不是打印一个假数字**——`ros_read.sh`
里那句"先数 JSON 个数再读"救了我。这正是今晚为什么要端到端验那个 array 脚本:
**空表能被识别出来是空表,而不是被当成一个中位数。**

已改成 `exec bash <path>` 并补上可执行位,重开链(4 link + array + 读数)。

**记档规则**:**提交一条链之后,要回头确认第一个 link 真的开始训练了**(不是只确认门的
`GATES-RC=0`)。检查方法:`sacct -j <first> --format=State,Elapsed`——`Elapsed` 小于一分钟
就说明它根本没跑起来;以及 `rl/runs/<run>/latest.pt` 是否出现。今晚我已经有"scancel 后
回扫 `(null)` 依赖"和"读花名册时追问检查点导出时间"两条,**这是第三条同族的**:
**链的三个环节(门、link、花名册)每一个都要单独确认它真的动了。**

## 2026-08-22 · `gleaner` 判词**翻了**,而两条最好的臂与三条失败的臂正好是**相反的机制**

补训后重读(`--harvest-urgency 0.5`,gen28,**iter 166**,原判词是 75 迭代的 51,109):

    BEATEN heldout 7/10   trained 0/3 | p05 24,082  median 52,199  <20k 2%   (1248 局)

**它变好了**(+1,090 中位、p05 22,428 → 24,082、<20k 3% → 2%),**所以此前那句"边际阴性"
是训练不足造成的**。自查降级为"未定"是对的,而补训确认了降级的必要。**它现在与
muckman 并列带子之首。**(仍然对磁带 0/3、仍然离 104,500 差 52k——"不是阴性"不等于"够用"。)

### 附迭代数的完整带子

| 臂 | iter | 中位钱 | p05 | <20k |
|---|---|---|---|---|
| **muckman**(`--fert-credit`) | 133 | **52,377** | 23,437 | 2% |
| **gleaner**(`--harvest-urgency`) | 166 | **52,199** | 24,082 | 2% |
| stockman(帮手 BUILD/PLACE 词表) | 119 | 51,344 | 23,705 | 2% |
| penner(`PLACE_BUILDS`) | 256 | 50,639 | 22,328 | 3% |
| furrow(`--land-value 5000`) | 164 | 47,511 | 16,571 | 8% |
| **seedsman**(`--seed-credit`) | 147 | **18,844** | **99** | **51%** |

### 而这补上了上一条收束的**另一半**

上一条说三条失败的臂(penner / furrow / seedsman)机制相同:**它们各自抬高了一件资产的
信用,资产确实增加了,但互补品缺位,于是现金变成闲置资产。**

**现在看两条最好的:它们都不增加任何资产,而是提高"已经在场的资产"的使用价值。**

| | 做了什么 | 加资产? |
|---|---|---|
| `muckman` | 抬高**已有动物**的信用 → 畜群 5→6,而奶/毛有镇需求 | **否**(改的是既有动物的估值) |
| `gleaner` | 让**已种下的地**"撞上限就在浪费"被看见 → 收获时点 | **否**(改的是既有作物的使用) |
| — | — | — |
| `penner` | 让帮手能造**新栏**放**新兽** | 是 → 饲料缺位,兽死 |
| `furrow` | 让买**新地**变正 | 是 → 种子缺位,66 格空着 |
| `seedsman` | 让持有**新种子**变正 | 是 → 种植缺位,囤 266 颗西瓜 |

**结构判词**:在这个游戏里,**给"新资产"加信用会失败,给"既有资产的更好使用"加信用会
(边际地)成功**。原因就是互补性:新资产需要它的全部互补品同时到位,而"更好使用"只需要
那件资产本身已经在场。

**这对 `croftr` 是个正面预兆**:`--demand-cap` **既不加资产、也不抬高使用**,它**取消一个
高估**(西瓜 base 250 对一季 30 单位需求)。按分类它落在"不引入闲置资产"那一侧,
**但它是三类里的第三类,没有先例。** 上一条的预登记仍然有效:若它阴性,应表现为
"产出结构变了而总量没变"(西瓜种子下降、草莓/小麦上升、中位不动),而不是某件资产闲置。

## 2026-08-22 · 按**量级**给五个族排序:只有课程那一族的数量级对得上

上一条给出了"哪一类 φ 项会成功"。这一条问下一个问题:**成功的那一类,量级够不够?**

| 族 | 已测样本 | 每项的量级 | 到 104,500 需要 |
|---|---|---|---|
| φ:给**新资产**加信用 | penner、furrow、seedsman | **负**(−1k 到 −33k) | — |
| φ:给**既有资产更好使用**加信用 | muckman +1,033、gleaner +855(对 stockman) | **≈ +1k** | **约 52 项** |
| 解码层(动作数量/时机) | 2×2 四格 + `PACED_SELL` | **整层 ±2k** | — |
| 词表(新动作/新任务) | 八次七负 | ≈ 0 | — |
| **课程(继承什么状态)** | 录音开局长度扫描 | **d8–d11 6,333/天;12 天 = 42,706** | **1–2 段** |

**这是今晚最有用的一次排序,而它是靠"两条成功的臂只值 +1k"才成立的。**
`muckman` 与 `gleaner` 是"更好使用"这一类里最好的两条,而它们各自只比 stockman 高约
**1k**。缺口是 **52k**。**所以即使这一类的项能完美叠加,也需要约五十项——它不是路。**

(而且它们大概**不能**完美叠加:档案里"势函数项非线性叠加、组合必须自己 A/B"这条今晚
在解码层已经复现了两次——`WHEAT_BUY_EXACT` 与加宽头各自 +1.8k/+2k,合起来只剩 +378。
所以"muckman + gleaner"这个组合虽然是**第一对可测的正向组合**,但按量级它最多值 +2k,
**不值得占 GPU**。这是一个明确的不做决定。)

### 由此重排剩下的工作

**唯一量级对得上的是课程**:`backplay-d8`(已修 bug 重开)与 `d0-chisel`/`d0-d12`。
那一族的单位不是"每项 1k",而是"**每天 3.5k,最贵的窗口 6,333/天**"。

**`croftr` 是唯一还没定量级的族**(取消高估,三类之外的第四类)。它剩 1 个 link。
**若它也只值 ~1k,那么按这张表,φ 系数这条路可以整体收档**,剩下的全部押在课程上——
而课程正是"让网自己建农场"的那条,也就是"用 RL 达到 2000"这道题字面意义上的答案。

## 2026-08-22 · d0 初始权重 A/B:**两个判据给出相反的答案,而按你指定的那个,从 chisel 起胜出**

`d0-chisel` vs `d0-d12`(gen23,`--bank-frac 0.35`,1,248 局 × 13 对手):

| | d0-d12 | d0-chisel | anvil(基线) | 天梯 |
|---|---|---|---|---|
| iter | 214 | 178 | — | — |
| **花名册中位** | **50,748** | 49,521 | — | — |
| HELDOUT | 6/10 | 6/10 | — | — |
| **第 0 天整局 margin** | −56,081 | **−46,730** | −64,731 | — |
| 每回合帮手 | **8.40** | 7.90 | 7.90 | 8.4–8.6 |
| 一局买的种子 | 32 | **50** | 47 | 207 |
| 站着的作物 | 16 | **28** | 26 | 37–61 |
| 空着的已解锁格子 d18/d28 | 26/24 | **14/14** | 18/25 | 2/5 |

**两个判据不一致:**
- 按**花名册中位**,`d0-d12` 胜(50,748 对 49,521);
- 按**你为这两条指定的判据(第 0 天整局 margin)**,`d0-chisel` **决定性地胜**
  (−46,730 对 −56,081),**而且只有它过了 chisel 的 −54,849**(超出 8,119);
  `d0-d12` 反而没过。

**−46,730 是今晚测到的最好的第 0 天 margin**(muckman −49,850、stockman −53,268、
furrow −53,621、anvil −64,731)。

### 这与反向课程的前提**相反**,而它把 `backplay-d8` 抬成了关键

`d0-d12` 的意思是"从 d12 课程的尾巴初始化",而反向课程的前提是**逐段继承会带来迁移**。
**实测是反的:从 chisel(没有课程)初始化,在第 0 天反而更好。** 行为读数说得更清楚:
d0-chisel 买 **50** 颗种子、站着 **28** 格作物、只空 **14** 格;而 d0-d12 只买 32 颗、
站 16 格、空 26 格。**d12 尾巴专门学过"接手一个第 12 天的农场",它把这个专长带到第 0 天
时反而更不会自己建。**

这正是此前那条"链不向前迁移"的判词,**现在在同一个 d0 段上、用两个初始权重并排确认了**。
而按今晚"边际最贵是 d8–d11(6,333/天)、而反向课程从来没有 d8 段"那条测量,
**`backplay-d8` 正是这个缺口的补丁**——它已修 bug 重开(20319521-24)。

**唯一一个不该被忽略的正面读数**:`d0-d12` 的**每回合帮手 8.40** 是今晚唯一进入天梯
8.4–8.6 区间的臂(其余全是 7.9)。**所以 d12 尾巴确实带来了一样东西——班组规模——只是
它同时带来了"不会自己种地"。** 若要合并两者的好处,该问的是"能不能只继承班组习惯而不
继承'等着接手农场'这个假设",而**这不是一个 `--bank-frac` 能表达的问题。**

**判据修订(第三条)**:课程臂必须**同时**报"花名册中位"和"第 0 天 margin",
**因为它们会给出相反的排序**。今晚若只看中位,我会选错那一条初始权重。

## 2026-08-22 · **`croftr` 是在标志关闭的情况下跑完的** —— 一条看起来完全合理的假判词,以及它意外给出的对照

读 croftr 的花名册时顺手读了检查点的 `args`:**`demand_cap 0.0`**。

**`--demand-cap` 从来没进过它的命令行。** 我是用 `sackman_link.sh` sed 出 `croftr_link.sh`
的,而 sackman 用的是**代码级**标志(`SEED_BURST`,写在 `actions.py` 里)而不是 CLI 标志,
所以那一行压根不存在。门(`test_croft.py` C1–C5)验的是**代码**,它全过;**而臂从来没
打开过那个变量。**

**这比 `backplay-d8` 那次 permission-denied 危险得多**:bpd8 是**响亮地**失败(花名册报
"0 of 13 opponents present"),而 croftr **跑完了 230 迭代并给出一个完全合理的数字**:

    BEATEN heldout 6/10   trained 0/3 | p05 22,516  median 50,063  <20k 3%   @ iter 230

**50,063 正落在带子里。若我没去读 `args`,就会记下"demand-cap 值 −1k"这条假判词**,
而且它会和其它七条并列进那张量级表,把"取消高估"这一族错判为已测。

### 但这个错误意外给了我一样此前没有的东西:一个**同配方对照**

那 230 迭代跑的是**不带任何新变量的标准配方**,从 chisel 起。**这正是带子一直缺的
对照组**——此前我拿 stockman(它自己也是一条臂)当基线。已把它保留为
`rl/runs/control230`。

| 臂 | iter | 中位钱 | 相对**对照** |
|---|---|---|---|
| **control230**(无变量) | 230 | **50,063** | — |
| muckman(`--fert-credit`) | 133 | 52,377 | **+2,314** |
| gleaner(`--harvest-urgency`) | 166 | 52,199 | **+2,136** |
| stockman(词表) | 119 | 51,344 | +1,281 |
| penner | 256 | 50,639 | +576 |
| d0-d12 | 214 | 50,748 | +685 |
| d0-chisel | 178 | 49,521 | −542 |
| furrow(`--land-value 5000`) | 164 | 47,511 | −2,552 |
| seedsman(`--seed-credit`) | 147 | 18,844 | −31,219 |

**所以"更好使用"这一类的量级从 +1k 上修到 +2.1–2.3k**(对真正的对照,而不是对另一条臂)。
量级表的结论不变——**+2.3k 对 54k 的缺口,仍然差二十倍以上**——但基线现在是对的。

### 判据修订(今晚第四条,也是最该早有的一条)

**花名册读数必须同时报"这条臂自己那个标志的实际取值",从检查点的 `args` 里读。**
迭代数(第二条)能发现训练量不等;**标志取值能发现臂根本没打开变量**——而后者会伪装成
一个合理的数字,比空表危险得多。

已修 `croftr_link.sh`(补上 `--demand-cap 1.0`)并重开(20320858-61 + array + 读数)。
**这是今晚第二个发射期 bug**(前一个是 `exec` 缺可执行位),两个都不是代码错、都是
**提交脚本没带上它要测的东西**。

### 回溯审计:把"标志实际取值"这条判据倒查全部九条臂 —— **只有 croftr 一条中招**

既然 croftr 是在标志关闭下跑完并给出一个合理数字的,那必须倒查其余每一条。
从各自检查点的 `args` 读**实际取值**:

| 臂 | iter | 标志 | 实际 | 应为 | 结论 |
|---|---|---|---|---|---|
| muckman | 133 | `fert_credit` | 0.3 | 0.3 | OK |
| gleaner | 166 | `harvest_urgency` | 0.5 | 0.5 | OK |
| furrow | 164 | `land_value` | 5000.0 | 5000.0 | OK |
| seedsman | 147 | `seed_credit` | 0.5 | 0.5 | OK |
| d0-chisel | 178 | `bank_frac` | 0.35 | 0.35 | OK |
| d0-d12 | 214 | `bank_frac` | 0.35 | 0.35 | OK |
| control230 | 230 | `demand_cap` | 0.0 | 0.0 | OK(它就是对照) |
| **croftr(第一次)** | 230 | `demand_cap` | **0.0** | **1.0** | **中招,已重开** |

**而这暴露了那条判据本身的一个缺口**:`stockman`、`penner`、`longhaul`、`grange` 用的是
**代码级**标志,`args` 里查不到。补查它们各自树里的实际状态:

- `gen27`(penner):`PLACE_BUILDS = True`、`CARRY_COMPLETES = True` — **OK**
- `gen24`(stockman):**没有布尔标志**,它的变量是 `HAND_TASKS` 加了两项。
  实测 `N_HAND_TASK 12`、`BUILD`/`PLACE` 都在表里(主树是 10 / 都不在)— **OK**

**判据补全(第四条的第二半)**:CLI 标志查检查点 `args`;**代码级标志要查"那棵树里那个
常量/列表的实际值"**,而不是查命令行——因为命令行里根本没有它。两种都要查,否则
"臂没打开变量"这个失败模式会在代码级标志上继续隐形。

**审计结论**:九条已判的臂里**八条的变量确实开着**,一条(croftr)没开、已重开。
**所以那张量级表除 croftr 那一格外全部有效**,包括它意外产出的对照 `control230`。

### 更正自己那张量级表:课程那一族的 42,706 是**磁带**做到的,**课程还没证明能接住它**

那张表把课程列为"唯一量级对得上"的族,依据是录音开局长度扫描:**12 天的建设值
42,706**(8 天 47,549 → 20 天 90,255)。**但那测的是"磁带能建出多少",不是"课程能学会
多少"。** 这两件事今晚已经被分别测过,而结果相反:

| 测的是什么 | 数值 |
|---|---|
| **磁带**建 12 天的价值 | **+42,706** |
| **课程**继承一个 d12 农场再训到第 0 天 | 第 0 天 margin **−56,081** |
| 不继承(直接从 chisel 训 d0) | 第 0 天 margin **−46,730** |

**继承反而更差 9,351。** 所以"课程 = 1–2 段就能补上缺口"这个估计**建立在迁移有效这个
前提上,而 d0 的 A/B 正好否掉了这个前提**。

**表要这样读才对**:
- **上界**(磁带能做到的):12 天 = 42,706 —— 这是**目标**,不是**已实现的量级**;
- **课程目前实测的量级**:d0 段最好的是 `d0-chisel` 的 −46,730,比 anvil 基线
  (−64,731)好 **18,001**,但**那一条恰好是没有继承课程的那一条**。

**所以严格说来:今晚没有任何一族被证明能达到 5 万量级。** 课程是唯一**有可能**的
(因为磁带证明了那些天值那么多钱),但**迁移这一步是断的**——而 `backplay-d8` 测的正是
"把缺掉的 d8–d11 那段补上,迁移是否就通了",**不是"课程有效"**。这个区分决定了它阴性
时该怎么读:若 bpd8 也不能把第 0 天 margin 推过 −46,730,那么**"逐段反向课程"这条路
本身要被怀疑**,而不是再去补下一段。

## 2026-08-23 · **把最好的纯网臂换进 hybrid,反而差 13–14k** —— 反向课程是有效的,但只在它自己的分布里

候选的网段(第 20–29 天)来自 `d12-final`,即**反向课程 d12 段的尾巴**。muckman 与
gleaner 是**从 chisel 起、无课程**的两条最好纯网臂(对 control230 分别 +2,314 / +2,136)。
把它们换进同一个"20 天 cleo 录音 + 网"的结构,同样 9 对手 × 48 种子 × 双席:

| 网段来自 | 中位 | p05 | <20k |
|---|---|---|---|
| **`d12-final`(d12 课程尾巴)** | **90,255** | **51,930** | 0% |
| muckman(chisel 起) | 76,297 | 44,449 | 0% |
| gleaner(chisel 起) | 77,159 | 44,673 | 0% |

**−13,958 / −13,096。** 我预登记的是"大概不迁移"(照 `WHEAT_BUY_EXACT` 那次 +1,760 → −62
的先例),**实际是大幅变差**。

### 这与 d0 那条 A/B 恰好对称,而两条合起来才是完整判词

| 在哪个分布上测 | 有课程 | 无课程 | 差 |
|---|---|---|---|
| **第 0 天开局**(d0 A/B,margin) | d0-d12 **−56,081** | d0-chisel **−46,730** | 课程 **−9,351** |
| **第 20 天接手**(hybrid,中位) | d12-final **90,255** | muckman 76,297 | 课程 **+13,958** |

**反向课程把网**专门化**成"接手一个已建好的农场"**:在那个分布里它值 **+14k**,在分布外
(第 0 天从零建)它值 **−9k**。**所以此前那条"链不向前迁移"说对了一半——不是"没学到东西",
是"学到的东西只在它训练的那个状态分布里兑现"。**

**而这修正了我昨夜那张量级表最重要的一格**:课程族的量级不再只是"磁带能做到 42,706"这个
**上界**,而是有了一个**实测值:+13,958**,在它自己的分布里。**这是今晚所有族里实测最大的
效应**——势函数"更好使用"类是 +2.3k,解码层整层 ±2k,词表 ≈0。

### 说清混淆项

muckman/gleaner 与 `d12-final` 相差的不只是"有没有课程":它们还各带一个 φ 项、迭代数也不同
(133 / 166 对 d12-final 的链尾)。**所以"+13,958"不能纯归因于课程。** 但方向与量级足够大,
最稳的表述是:**打包候选的网段无法用现有最好的纯网臂替换掉——在它自己的机制区间里,它比
两者都好 13–14k。**

**对提交决定的含义**:**候选不要动网段。** 这是今晚为它测清的第三件事(前两件:不要移植
`WHEAT_BUY_EXACT`、不要缩短录音开局)。

## 2026-08-23 · "课程段要与录音长度匹配"这个假说**被否**,而它让上一条判词更强

上一条测出"课程尾巴的网在 hybrid 里比 chisel 起的臂好 13–14k",我据此推出一个假说:
**候选把 `d12-final`(训练时接手第 12 天的农场)配了 20 天录音,是错配**;若专门化是分布性的,
那么"接手第 20 天农场"训出来的网才该配 20 天开局。

**测法**:固定 20 天 cleo 录音与 9 个对手,**只换课程段**(录音长度扫描做不到这一点——它变
开局而固定网段,于是"录音越多越好"把结论盖住了)。

| 网段(全部 @20 天录音) | 训练时接手 | iter | 中位 | p05 |
|---|---|---|---|---|
| **backplay-d16** | 第 16 天 | 179 | **90,409** | 51,840 |
| **d12-final**(打包候选) | 第 12 天 | 链尾 | 90,255 | **51,930** |
| **endgame** | **第 20 天(匹配)** | **303** | **88,810** | 50,512 |

**"匹配"的那一个是三者里最差的**,而且它的训练量最多(303 迭代)——**所以既不是匹配效应,
也不是训练量效应**。三者极差 1,599,基本同级。

### 假说否掉,而机制判词因此更干净

不是"d12 恰好匹配第 20 天",而是:**任何一个反向课程段,在 hybrid 里都比 chisel 起的臂好
约 13k,而具体是哪一段无关。**

| 网段来源 | hybrid 中位 |
|---|---|
| 任一课程段(d12 / d16 / d20) | 88,810 – 90,409 |
| chisel 起的臂(muckman / gleaner) | 76,297 – 77,159 |

**所以课程的价值是"二元的"——训练时见过没见过"接手一个已建好的农场"——而不是与开局长度
成比例的匹配。** 这比上一条的表述更强,也更容易检验:它预测**任何**在银行状态上训过的网都
落在 88–90k,而**任何**没训过的落在 76–77k。

### 对候选的实际含义:没有改进空间,打包那个就是最好的之一

`backplay-d16` 的 90,409 只比打包候选的 90,255 高 **154**(而候选的 p05 51,930 反而更好)。
**所以"换一个课程段来改进候选"这条路是关的。** 这是今晚为提交决定测清的**第四件事**:

1. 不要移植 `WHEAT_BUY_EXACT`(hybrid 上 −62);
2. 不要缩短录音开局(缩到 12 天付 17.4k);
3. 不要用纯网臂替换网段(−13~14k);
4. **不要换课程段(±154,在噪声内)。**

**打包件原样发即可。**

## 2026-08-23 · 我自己那个"二元"说法**被否**:决定 hybrid 能力的不是"见过银行",是**从谁初始化**

上一条我发了一个可证伪的预测:"课程在 hybrid 里的价值是二元的——网有没有在银行状态上
训过",并预测 `d0-chisel`(`bank_frac 0.35`,**见过**银行)会落在 88–90k。**它落在 77,484。**

固定 20 天 cleo 录音、同样 9 对手 × 48 种子,只换网段:

| 网 | `bank_frac` | 从哪初始化 | hybrid 中位 | p05 |
|---|---|---|---|---|
| backplay-d16 | 1.0 | 课程链 | **90,409** | 51,840 |
| d12-final(打包候选) | 1.0 | 课程链 | 90,255 | 51,930 |
| endgame | 1.0 | 课程链 | 88,810 | 50,512 |
| **d0-d12** | **0.35** | **d12 尾巴** | **87,723** | 49,912 |
| **d0-chisel** | **0.35** | **chisel** | **77,484** | 46,020 |
| gleaner | 0 | chisel | 77,159 | 44,673 |
| control230 | 0 | chisel | 76,330 | 44,537 |
| muckman | 0 | chisel | 76,297 | 44,449 |

**分组不是按"有没有银行",是按"从谁初始化"**:`d0-chisel` 有 35% 的银行暴露,却和三条
**完全没有**银行的臂并列(77,484 对 76,297–77,159);而 `d0-d12` 同样 35%,却保住了
87,723(只比 d12-final 低 2,532)。

**所以准确的机制是:hybrid 区间的能力沿着权重的血统传递——它由 `bank_frac 1.0` 的段
造出来,而在最后一段给 35% 的银行暴露只能"保住已经带来的",造不出"原本没有的"。**

### 这把 d0 那条 A/B 的反转解释干净了

| | 第 0 天 margin | hybrid 中位 |
|---|---|---|
| d0-d12(带课程血统) | **−56,081** | **87,723** |
| d0-chisel(无课程血统) | **−46,730** | **77,484** |

**同一个 `bank_frac 0.35`、同一段训练,两个初始权重换来一个此消彼长**:带血统的保住了
hybrid 的 10k,却在第 0 天差 9.4k;不带血统的换到第 0 天的 9.4k,却拿不到 hybrid 的 10k。
**这是一条轴上的取舍,而不是"课程好/不好"。**

### 对"用 RL 达到 2000"的直接含义

要 104,500,需要**同时**拿到两样:**从第 0 天自己建**(d0-chisel 这一侧)与**接手后
把农场用好**(d12 血统那一侧)。今晚测出的是:**在 `bank_frac` 这一个旋钮上,这两样
互斥**——0.35 保住其一而得不到其二。

**所以下一代该问的不是"再加一段课程",而是"能不能让一个网同时具备两者"。**
`bank_frac` 表达不了这个;可能的形式是**同一批次里混两种起始状态**(一部分真第 0 天、
一部分银行),而这**已经是 `--bank-frac` 的字面语义**——`d0-chisel` 的 0.35 就是那个混法,
**而它没能同时拿到两者**。**所以要么混合比例不是那个旋钮该调的东西,要么这需要两个网
(一个建、一个接),而后者在单一 agent 的提交格式下是可以做到的(按天切换)——那正是
hybrid 在做的事,只不过它的"建"那一半是录音而不是网。**

**这条判词第一次把"hybrid 是录音"这件事和"RL 该怎么做"接上了**:hybrid 之所以有效,
是因为它**用两个不同的策略分别负责两个分布**。用 RL 达到同样效果,需要的不是一个更好的
网,而是**两个网 + 一个切换点**——而"建"那个网就是 d0 段该产出的东西。

## 2026-08-23 · 全 RL 两段式:切换这个**形状**只值 +5,324,而磁带的**建设质量**值 +40,681

上一条判词说 hybrid 之所以到 90k,是因为它"用两个策略覆盖两个分布",并指出把"建"
那一半也换成网就得到全 RL 的答案。**今晚把它做出来测了,形状那一半几乎不值钱。**

`tools/build_netnet.py`:网 A(`d0-chisel`,第 0 天 margin 最好的建设者)建到第 D 天,
交给网 B(`backplay-d16`,hybrid 中位最高的接手者)。零 GPU,两个网都已存在。九对手
× 48 种子,两个端点都测了,所以这是一条曲线而不是一个点:

| 切换日 | 中位 | p05 | <20k |
|---|---|---|---|
| **0 = 接手者独自打全局** | **32,706** | **1,762** | **19%** |
| 8 | 39,718 | 21,675 | 2% |
| 12 | 42,324 | 22,232 | 3% |
| 16 | 49,358 | 21,465 | 3% |
| **20** | **49,728** | 22,912 | 2% |
| **30 = 建设者独自打全局** | **44,404** | 22,842 | 2% |

**三件事同时被读了出来。**

**一、接手者独自从第 0 天开始是灾难性的,而且是新的一种坏。** 32,706、p05 **1,762**、
**19% 的对局低于两万**。它不是"打得差",是**近乎破产**——之前任何一条臂的 `<20k` 都在
0–3%。这是血统判词另一半最强的确认:带课程血统的网**完全没有**第 0 天的能力,不是弱,
是没有。

**二、交接确实赢过它自己的两半,但只赢一点。** 最好的切换点(第 20 天)49,728,对建设者
独自 44,404、接手者独自 32,706——**比更好的那一半只高 5,324**。而且**交接太早会亏**:
第 8 天交接(39,718)比建设者自己打完(44,404)**低 4,686**。接手者的价值只在**残局**,
把建设阶段交给它就是浪费。

**三、这是一次完美的单变量对照,而它给出了整个项目最干净的一个数。**
`nn-d20` 与 `hyb-backplay-d16-20` **用的是同一个接手网**,20 天的切换点也一样,
**唯一的差别是那 20 天由谁来打**:

| 前 20 天由谁建 | 后 10 天 | 中位 |
|---|---|---|
| cleo 磁带 | backplay-d16 | **90,409** |
| `d0-chisel`(我们最好的 RL 建设者) | backplay-d16 | **49,728** |

**+40,681。** 磁带不是"形状"上赢的,是**建设质量**上赢的。

### 这否掉了我自己上一条的乐观读法

上一条写"hybrid 有效是因为两个策略覆盖两个分布",隐含"所以把录音换成网就能全 RL 拿到
90k"。**测出来是:形状值 5,324,内容值 40,681——比例 1:7.7。** 所以
**90k 不属于两段式结构,它属于 cleo 那 20 天。**

### 缺口现在有了唯一的落点

要 104,500,而我们最好的**全 RL** 产物是 **49,728**。缺口 54,772,其中
**40,681 就是"我们的网不会建农场"这一件事**。而"不会建"是有具体读数的、五代都没动过的
同一组数:地 2.0 对天梯 3.0、每回合帮手 7.9 对 8.4–8.6、整季种子 **47 对 k06 的 207**、
第 18/28 天空地 **18/27 对 2/5**。

**所以剩下的所有 GPU 都应该花在同一个问题上:让网学会建。** 而这一晚测过的五个家族
(新资产计价、更好用途计价、解码层、词表、课程)全部 ≤2.3k,**没有一个能碰到 40,681
这个量级**——它们攻的都不是这件事。**唯一还没试过的、直接攻建设行为的杠杆是模仿:
用 150k 磁带当老师(gen38 `--kickstart tape:<agent.py>`,门 TUTOR-PASS)。**
它今晚已经作为预门开跑(`tutor` 对 `tutorctl`,同一 `--seed 0` 因此随机初始化与环境流
逐字节相同,唯一变量是老师),读的是**行为**而不是钱:种子/地/帮手动不动。

**为什么必须从随机初始化开始**:`chisel/init.pt` 是 iter 324 / 2.39 亿步的**成熟**主干,
正是档案里 sower-v1 在第 3 个迭代被杀掉的那个情形(CE ≈1.2 对策略梯度 ≈0.03,四十比一)。
成熟主干只能给 `--ks-coef ≤ 0.05`,而那太弱,装不进"一季买 207 颗种子"。随机初始化没有
连贯策略可以砸坏——这也是 AlphaStar/VPT 的顺序。

## 2026-08-23 · **整晚的诊断都对着账本的错误一侧**:33,114 的缺口在**支出**,而 φ 里没有饲料这一项

`tools/build_netnet.py` 把缺口钉在"网不会建农场"(40,681)之后,下一个问题是"不会建"
具体表现为什么。答案不在收入侧,而在**支出侧**——而这是这个项目从未看过的一侧。

`tools/ledger.py`,4 个种子,`d0-chisel` 对 k06(整局,第 0 天开始):

| | 我们 | k06 |
|---|---|---|
| 收款 | 92,140 | 132,007 |
| **付款** | **62,915** | **29,303** |
| 期末 | 32,225 | **105,704** |

缺口 73,479,其中收入侧 39,867(54%)、**支出侧 33,612(46%)**。而支出的构成:

| 支出桶 | 我们 | k06 |
|---|---|---|
| **买产品(饲料)** | **54,050(占 85.9%)** | **20,936(占 71.4%)** |
| 雇工 | 3,145 | 6,724 |
| 种子/动物/土地 | 5,720 | 1,643 |

**饲料一项差 33,114 —— 几乎就是整个支出缺口。** 而种子构成解释了为什么:

| 整季买种子 | 我们 | k06 |
|---|---|---|
| **WHEAT** | **0** | **138** |
| STRAWBERRY | 14 | 34 |
| MELON | 19 | 20 |
| CARROT | 0 | 15 |

**引擎事实(已读源码)**:`op == "FEED"` 执行 `_inv_take(inv, "WHEAT", 1)`——
**每只动物每天从自己棚里吃掉 1 份小麦**。所以小麦不是一种"卖得便宜的作物",
**它是牲畜的运营成本**。k06 把 66% 的种子钱花在小麦上,自己种饲料;我们买 0 颗小麦种子,
然后到市场上买饲料。而**小麦市价整局从 27 涨到 49**(两家合计净买入 538 份),
所以买饲料这条路是**越走越贵**的。

### 机制:φ 给动物记了产出,**没有记它的饲料负债**

`potential_future.py` 的动物项是
`rem_a × a_base × ANIMAL_CREDIT − (~fed) × a_cost × UNFED_RISK − (~cared) × …`。
`~fed` 是**当前状态标志**上的风险罚,不是**未来要吃掉多少小麦**的负债。
整个文件里 `feed` 出现 **0 次**。

而同一个 φ 给一块地的计价(`max_yield × base`,PLANT_CREDIT 之前):

| 作物 | 种子 | max_yield | base | **φ 给一块地** |
|---|---|---|---|---|
| MELON | 80 | 6 | 250 | **1,500** |
| STRAWBERRY | 100 | 4 | 120 | 480 |
| **WHEAT** | **10** | 6 | **25** | **150(九种里最低)** |

**两半错误指向同一个行为**:买牛(记 `rem_a × 160 × 0.4`,饲料免费)+ 别种小麦
(一块地只值 150,是最差的用途)= **买动物、不种饲料、到市场买饲料**。这正是测出来的行为。

**量级(按准则 (j),用它要驱动的那笔交易定价)**:一头牛剩 25 天要吃 25 份小麦,
按 28–48 的市价是 **700–1,200**,而 φ 给这头牛记 `25 × 160 × 0.4 = 1,600`。
**所以 φ 把一头牛高估了 44–75%**;换成自己种,4.2 块小麦地 = 42 块钱的种子,
比买饲料便宜 **17–29 倍**。

### 这条判词也是一次准则 (h) 的现场事故,必须记下来

在算出上面这些之前,我先用**动作流**给两边的卖出计价,得到"k06 靠化肥赚 100,777、
占它总收入 53%"——**这个数是假的**。市场库存整局只从 10,000 涨到 **10,316**,
而两家提交的化肥卖单合计 1,821 份:**只有约 22% 的卖单真的成交了**。
**非法动作是静默空操作**,所以一个每回合对着空棚子提交 `SELL FERTILIZER x40` 的
agent,在动作流里看起来是个大卖家。**动作流能读"它想做什么",不能读"发生了什么";
钱能读,而且是分家的。** `tools/ledger.py` 的注释里记了这一条。

### 为什么之前五代都没看到

所有工具读的都是动作流或收入侧(需求账本、池子捕获率、"缺口是产量不是选品")。
**收入侧确实差 39,867,但支出侧差 33,612,而且支出侧只有一项**。而今晚测过的五个
家族全部 ≤2.3k——**它们全都在收入侧**。

**下一条臂(唯一一条量级对得上的):给 φ 加饲料负债。** 按每只动物剩余天数 × 1 份小麦 ×
市场买价扣减,并让棚里的小麦/小麦地在有牲畜时按**同一个买价**计价而不是按 base 25。
`BUY_SEED_WHEAT` 已在市场头第 10 位、`FEED` 已是帮手任务第 7 位,**动作早就有了,
不缺候选(准则 (c))——缺的是价格信号(准则 (a) 的反面:动作有奖励,只是记错了)**。

### haymaker 的预登记(在结果之前写下)

gen39 `--feed-debit 1.0`,单变量,与 chisel 配方其余部分完全一致(所以可比
`control230` 的 50,063)。`test_hay.py` H1–H6 **HAY-PASS**。

**近端预测**(这条臂如果起作用,必须先看到):

1. **整季买小麦种子从 0 涨到 >50**(k06 是 138)。这是唯一直接的行为读数。
2. **饲料支出从 54,050 下降**。

**结果预测**:九对手中位(第 0 天起整局)**超过 `control230` 的 50,063**。

**护栏(这条臂自己的失败模式,先写下来)**:`test_hay.py` 测出**光牛在
`feed_debit 0.9` 就变成 φ-负**,1.0 时是 −10(第 4 天)到 −122(第 20 天)。
配对(牛 + 自种饲料)是 +1,015 换 50 块种子钱,所以梯度指向**这一对**;但如果网
因此**连第一头牛都不买**,它就永远发现不了小麦能养活它——这是一个探索陷阱。
**所以:若第 18 天的畜群跌破对照的 6 只,判定为陷阱触发,后续是 `--feed-debit 0.5`
(那里光牛是 +159),而不是放弃这条思路。**

**为什么这条臂和今晚其它五个家族不同**:它是**第一条从支出侧来的**。前五个家族
(新资产计价、更好用途计价、解码层、词表、课程)全部 ≤2.3k 且全部在收入侧;
而饲料一项就差 33,114。**量级第一次对得上。**

## 2026-08-23 · 饲料论的独立确认:**接手后的最后 10 天,网自己花掉 23,680 买饲料**

`tools/ledger.py`,3 个种子,全部对 k06,整局:

| | 期末 | 付款 | 其中饲料 | 整季小麦种子 | 缺口里支出占比 |
|---|---|---|---|---|---|
| **cleo 磁带(自己打完)** | **74,424** | **30,539** | **16,291** | **68** | **2%** |
| **hybrid = cleo 20 天 + 我们的网** | 72,158 | **52,130** | **39,971** | 35 | **89%** |
| k06 | 92,584–96,784 | 30,134 | 21,089 | 138 | — |

**三条读数,每一条都是新的。**

**一、天梯层已经解决了支出侧,我们是异类。** cleo 的付款 30,539 与 k06 的 30,186
**几乎相同**,它对 k06 的缺口里**只有 2% 是支出**——剩下全是收入。也就是说
"支出侧差 33,612"是**我们自己的病**,不是这个游戏的普遍难点。

**二、hybrid 的付款比纯 cleo 高 21,591,几乎全是饲料(+23,680)。**
机制清楚:网在第 20 天接手一个**已经建好、带着畜群**的农场,然后**停止种小麦**
(整季小麦种子从 cleo 的 68 掉到 35,而那 35 全是 cleo 前 20 天买的),
转而到市场上买饲料。**它继承了畜群,却没继承养畜群的办法。**

**三、对 k06 这个具体对手,hybrid 比纯 cleo 还差 2,266。** 也就是说
**我们的网在最后 10 天里是负贡献**——它拿到一个 74,424 的农场,交出 72,158。
(**边界**:3 个种子、单一对手;九对手中位上 hybrid 是 90,255,对手场不同。
但方向与机制一致,而且机制是代码事实。)

### 这给 haymaker 一个更锐利的预测

`--feed-debit` 如果按设计工作,**网的饲料支出应该从 54,050 向 cleo 的 16,291 靠**,
而不只是"下降"。而这条判词也给出了这条思路的**上界**:cleo 把支出侧做对了,期末
74,424;所以修好支出侧大致值把我们从 32,225 拉到 cleo 的量级,**离 104,500 还差
30,076**,那部分是收入侧(cleo 对 k06 的缺口 18,160 里 98% 是收入)。

**所以完整的路线现在是两段,而且两段都有了具体的数**:支出侧 ~+42,000(到 cleo),
收入侧 ~+30,000(cleo 到 k06)。此前五代所有的臂都在**收入侧那 30,000 里**做 ≤2.3k
的改动,而**更大的、更简单的那一段一直没人碰**。

## 2026-08-23 · 磁带长度扫描:**网的边际贡献在每一个时点都是负的,约 −801/天**

上一条(饲料论的确认)说我们的网在最后 10 天对 k06 是负贡献。把它放到**九对手 ×
48 种子**上,只改一个变量——磁带跑多少天,之后交给**同一个网**(`backplay-d16`):

| 录音天数 | 中位 | p05 | 打败(held-out) |
|---|---|---|---|
| 20(打包候选的形状) | 90,409 | 51,840 | 5/7 |
| 24 | 93,191 | 50,004 | 5/7 |
| 26 | 94,861 | 50,552 | 5/7 |
| **30 = 纯 cleo,完全没有网** | **98,420** | **53,043** | **6/7** |

**单调递增。** 每交给网一天大约损失 **801**((98,420 − 90,409) / 10)。
**也就是说:打包好的那个候选,比它自己的磁带原样打完还差 8,011。**

### 这对候选意味着什么(**提交决定仍然归用户**)

`submissions/2026-08-22-hybrid-d12final20/` 的中位 90,255,而**同一块地上
`agents/bench3/closer_cleo.py` 原样跑是 98,420**。在**这个对手场上**,
候选被它自己的开局磁带打败,而且不是勉强。

**必须同时记住的边界,否则这条读数会被误用**:

1. **cleo 是我们自己重建的磁带,而且它本身就在这个对手场里**——它的数字有自指成分。
   CLAUDE.md 写得很直白:"**对着我们自己写的场排出来的名次,不是关于天梯的证据**"。
   实际证据是:`hybrid-cleo12` 在天梯上是 **705.9**。
2. 所以这条判词的可用部分是**相对的那一半**:同一个网、同一个场、只改磁带长度,
   得到单调曲线。**"网的边际贡献是负的"是单变量结论;"98,420 说明纯磁带能上天梯"不是。**

### 这和 haymaker 是同一件事

负贡献的机制上一条已经量出来了:网在第 20 天接手一个**带畜群**的农场,然后停止种小麦,
把 39,971 花在市场买饲料上(cleo 是 16,291)。**每天 −801 × 10 天 = −8,011,
而饲料多花的是 +23,680 —— 同一个数量级,同一个原因。**

**所以 haymaker 的成功判据现在有了第二个、更严的读数**:除了"九对手中位超过
`control230` 的 50,063",还应该看**把 haymaker 的网接在 cleo 20 天后面,能不能把
90,409 往 98,420 推**。如果饲料是主因,这个数应该动;如果不动,饲料只是伴随现象。
**这个检验零 GPU**——链跑完导出一次就能做。

## 2026-08-23 · **更正**:45,885 不是饲料账单,是小麦的来回倒手;而真正的约束是**市场头每回合只出一种单**

上一条判词把 45,885 叫做"饲料支出",并据此说"饲料一项差 33,114"。**这个归因是错的,
现在更正。** 触发更正的是我为了零 GPU 检验它而做的 `tools/build_feedfix.py`:
强制网在畜群缺料时买小麦种子(0 → 73 颗,确认真的成交、真的种下、真的收割),
**饲料支出只从 54,050 掉到 47,401,而收款掉了 10,758,净效果是白搭。**

顺着这个反常查下去,拿到三组硬数:

| | 我们 | k06 |
|---|---|---|
| **第 2/6/10/14/18/22/26 天畜群** | 2,3,4,4,4,3,3 | 4,6,12,14,14,14,14 |
| **整局 FEED 次数** | **85** | **321** |
| 小麦买单 / 卖单 | 946 / 855 | 495 / 1066 |

**一、3–4 头牲畜一季只吃约 110 份小麦,不可能吃掉 45,885。** 而这 45,885 是干净的
——它落在 **224 个"只提交了 BUY_PRODUCT"的回合**上,没有和 HIRE 混。所以钱是真的
花在买产品上,**但买的量是畜群能吃的十倍**。棚里小麦全程在 0–10 之间,说明它没囤。

**二、它在做小麦的来回倒手。** 买 946 卖 855;市场小麦库存整局 10,000 → 9,462
(两家合计净买 538),所以两边的单子大部分确实成交了。**它买进来又卖回去,
自己把价格从 27 推到 49,再在被自己推低的价上卖出。** 真实损失是**它自己造成的价差**,
**不是 45,885,也不是 33,114**。

**三、这才是那条真正的约束:我们的网每回合只能出一种单。**

| 收款来自什么样的回合 | 我们 | k06 |
|---|---|---|
| 只有 SELL | **66,677(100%)** | 35,326(43.7%) |
| HIRE + SELL | 0 | **31,871(39.4%)** |
| BUY_SEED + SELL | 0 | **10,243(12.7%)** |

**k06 有 56% 的收款来自"边卖边干别的"的回合;我们是 0。** 市场头选一个
`MARKET_ACTIONS` 索引,于是**每一次买种子、每一次雇工,都要顶掉那个回合的卖出**。
`feedfix` 买了 73 颗小麦种子、丢了 10,758 收款,**就是这条约束的直接测量**。

### 对 haymaker 的修正(它还在跑,不改代码)

`--feed-debit` 攻的那个漏洞**是真的**:φ 里 `feed` 出现 0 次,动物只记产出不记饲料,
而引擎每天每只吃 1 份小麦。**但它的预期机制和量级都要改**:

- **不要**再用 33,114 当它的目标。那个数是错的归因。
- 它现在的预期作用是两条:(1) 让 φ **不再乐意把畜群要吃的小麦卖掉**(棚里小麦一旦
  被计入"已有饲料",卖掉它就会推高负债);(2) 让"把牲畜养住"这件事有价值——我们的
  畜群**在缩小**(4 → 3),而 k06 稳在 14。
- 预登记的护栏不变(畜群跌破 6 则用 0.5),而**近端预测里"饲料支出下降"应替换为
  "整局 FEED 次数从 85 上升"和"第 18 天畜群从 4 上升"**——那两个是状态量,不受
  下单量陷阱影响。

### 下一条臂的候选(比 haymaker 更贴这次的读数)

**让市场头能在一个回合里既卖又买。** 这是词表改动,而档案说词表值 ≈0(8 条里 7 条阴性)
——**但那 8 条全都是"加一个新的单一动作",没有一条是"把两种单合成一次输出"。**
`_market_action` 已经能返回多张单(有 19 个回合出了 10 张),所以机制是现成的。
**这条要先量"一个回合出两种单"能挽回多少收款,再决定值不值一条 GPU 链。**

## 2026-08-23 · thrift 被拒,而它把上面两条判词一起改正了:**支出缺口是个红鲱鱼,产量诊断是对的**

`rl/actions.py` 的 `BUY_WHEAT` 解码成 `max(5, 2 * herd)` 份小麦,**没有任何地方看一眼
棚里已经有多少**——不在掩码里,不在解码里。所以网在 224/720 个回合上反复买同样两天的
饲料。`tools/build_thrift.py` 在"棚里已有 N 天饲料"时把这个动作掩掉,零 GPU。

**单个种子对 k06:15,576 → 49,334(+33,758)。** 而九对手 × 48 种子:

| 臂 | 中位 | p05 | <20k | 打败(held-out) |
|---|---|---|---|---|
| 基线(`nn-d0-chisel` 第 0 天起) | 44,404 | **22,842** | **2%** | 3/7 |
| th2(棚里 2 天) | 45,407 | **0** | **11%** | 3/7 |
| **th4** | **47,672** | **0** | **12%** | 3/7 |
| th8 | 44,904 | **0** | **11%** | 3/7 |
| th-hyb20(同一守卫放在 hybrid 上) | **90,409** | 51,840 | 0% | 5/7 |

**一、单种子那个 +33,758 是噪声。** 真值是 **+3,268**(44,404 → 47,672),
正好落在档案早就写下的"解码层值 ±2k"那个带子里。**CLAUDE.md 的第一条测量纪律
——"种子间方差超过大多数调参效应"——在这里是 10 倍的差距。**

**二、而且它把尾部打坏了**:p05 从 **22,842 掉到 0**,`<20k` 从 **2% 涨到 11–12%**。
守卫在某些局里挡掉了真正需要的饲料采购,畜群饿跑。**中位 +3,268 换尾部九分之一的崩盘
——拒绝。**

**三、`th-hyb20` 的中位与未打补丁的 hybrid **一模一样到个位**(90,409)。**
这不是巧合而是信息:cleo 把棚存压得很低,所以 `棚里小麦 ≥ 4 × 畜群` **几乎从不成立**,
守卫在 hybrid 区间**从不触发**。同一份权重、同样种子,行为逐字节相同,数字自然相同。

### 这两点合起来,推翻我几小时前自己那两条判词的核心

把采购单量砍掉 23%(946 → 730)只换来中位 +3,268。**说明那 45,885 基本是自融资的
——买进来的小麦大体又卖了回去,真实损失只是它自己造成的价差,而那个价差很小。**

**所以支出侧那 23,858 的差额不是浪费,而是被对应的收款抵掉了。**
`th4` 的账本(3 种子对 k06)把这件事写得很清楚:收款 **102,658 对 154,182**,
付款 58,295 对 29,779——**收款差 51,524,而付款差 28,515 里几乎没有可回收的部分。**

**结论:这个项目原本的诊断——缺口是产量/收入——是对的。** 我今晚基于
`tools/ledger.py` 的两条判词(「整晚都在诊断账本的错误一侧」与那条更正)**把方向带偏了**,
现在收回:**`ledger.py` 的收款/付款拆分本身是准确的,但"付款差额可回收"这个推论是错的。**
可回收性必须**测**,而这就是那个测量。

### 对 haymaker 的影响(它还在排队,不改代码)

φ 里没有饲料项**仍然是真的**,而且畜群**在缩小**(4 → 3,k06 稳在 14)、整局只 FEED
85 次(k06 是 321)**也仍然是真的**——这些是状态量。**但不要再期待它值 30k。**
它现在的合理预期是:让畜群养得住,从而**提高产量**(收入侧),量级参照收入侧那 51,524
里"更多牲畜产出"能占的份额,而不是支出侧的任何数字。
**它的验收仍然是九对手中位对 `control230` 的 50,063,加上"FEED 次数从 85 上升"
与"第 18 天畜群从 4 上升"这两个状态读数。**

## 2026-08-23 · 帮手撞车是真的、可修的,而它仍然只值 +1,803 —— **解码层的 2–3k 带子第三次被确认**

对着"缺口是产量"这条修正后的诊断,量了帮手在干什么:

| 整局帮手动作 | 我们 | k06 |
|---|---|---|
| 总数 | 5,604 | 6,198 |
| **PASS** | **2,763(49%)** | 584(9%) |
| 移动 | 2,199(39%) | 3,209(52%) |
| **真正干活** | **642(11.5%)** | **2,405(38.8%)** |

**帮手人数几乎一样(7.8 对 8.6),而我们的帮手干活的比例只有它的 3.7 分之一。**
而且**我们 2,763 次 PASS 里有 96% 发生在板上还有活的时候**:2,048 块没浇水、
1,223 块能收、987 只没喂、849 只没照料。**所以这不是"农场小所以没活干",是站着不干。**

**机制**:12 个帮手头在给定状态下**条件独立**,没有任何东西阻止它们全选同一个家族;
而 `rl/actions.py` 按帮手顺序占用目标,"一个家族没有目标剩下就 PASS"。
**前几只手把该家族的目标占完,其余的就站住,哪怕别的家族还有活。**

`tools/build_crew.py`:先用网自己的任务解码,把结果是 PASS 的手改成 AUTO 再解码一遍
(AUTO 从它管的每个家族里按同样顺序占用)。**保留拿到活的那些手的原任务**——因为
AUTO 永不播种,全改 AUTO 会让农场彻底停止播种。

单个种子:PASS 2,763 → 2,011,干活 +43%,第 18 天作物 9 → 15。九对手 × 48 种子:

| 臂 | 中位 | p05 | <20k |
|---|---|---|---|
| 基线(第 0 天起) | 44,404 | 22,842 | 2% |
| **`cr-d0-chisel`** | **46,207(+1,803)** | 21,196(−1,646) | 3% |
| hybrid 基线 | 90,409 | 51,840 | 0% |
| **`cr-hyb20`** | **90,496(+87)** | 52,113 | 0% |

土地利用**真的**改善了:第 18/28 天空地 18/27 → **14/14**,作物 25 → 28。
**而钱只动了 +1,803,而且 p05 还掉了 1,646——净效果是个平手。**

### 这是今晚第三次,而且它讲的是同一件事

| 解码层的臂 | 缺陷真不真 | 中位效应 | 尾部 |
|---|---|---|---|
| `WHEAT_BUY_EXACT`(档案) | 真 | +2.1 胜率 / +3,368 | — |
| `thrift`(今晚) | 真(采购无停止条件) | **+3,268** | **崩(p05 →0,12%<20k)** |
| `crew`(今晚) | 真(帮手撞车,96% 有活不干) | **+1,803** | 平(p05 −1,646) |

**三个各自独立、机制上都被验证为真的缺陷,每一个都落在 +1.8k 到 +3.3k。**
**所以这个带子不是"修得不好"的结果,它是"钱不在这里"的结果。**
40,681 不是由解码层缺陷组成的——**它是策略的经营规模**:地 2.0 对 3.0、
整季种子 45 对 207。**修掉帮手撞车之后,45 颗种子还是只能填 45 块地。**

**留档结论**:`crew` 是今晚唯一一个"中位涨了而尾部没崩"的解码改动,可以在将来任何
导出里带上;但它值 +1,803,不值一条 GPU 链,也**不改变缺口的位置**。

## 2026-08-23 · **40,681 不是奖励塑形问题**:φ 每颗西瓜种子已经付 +670,而网一季只买 45 颗

这是今晚最后一次测量,也是最有用的一次,因为它解释了**为什么六条势函数臂全部 ≤2.3k**。

先把"是不是带宽不够"排掉。整局 720 个市场回合的去处:

| 市场回合用在 | 我们 | k06 |
|---|---|---|
| **完全没出单** | 216(30.0%) | **370(51.4%)** |
| SELL | 208(28.9%) | 123(17.1%) |
| BUY_PRODUCT | **224(31.1%)** | 28(3.9%) |
| BUY_SEED(含与 SELL 同回合) | **29(4.0%)** | **93(12.9%)** |
| HIRE | 38 | 32 |

**k06 空转的回合比我们还多**(370 对 216)。所以**不是没有回合可用**。
而我们那 216 个空回合里,**212 个当时 BUY_SEED 或 SELL 是合法可用的**。
**网有回合、有钱、动作合法,它就是不买。**

然后是关键的一步:**φ 对这件事说什么。**

| 作物 | 种子价 | 买入时 φ | 种下时 φ | **一对合计** |
|---|---|---|---|---|
| WHEAT | 10 | −5.0 | +70.0 | **+65** |
| CARROT | 20 | −10.0 | +60.0 | +50 |
| TOMATO | 50 | −25.0 | +95.0 | +70 |
| STRAWBERRY | 100 | −50.0 | +190.0 | +140 |
| **MELON** | **80** | **−40.0** | **+710.0** | **+670** |

(`seedc` 就是种子价,`SEED_RESIDUAL 0.5`,`PLANT_CREDIT 0.5`;所以买入 φ = −价×0.5,
种下 φ = `max_yield × base × 0.5 − 价×0.5`。)

**φ 已经在朝正确方向付钱,而且付得很重:每颗西瓜种子 +670。网不拿。**

### 这就是那六条臂为什么都是 2k

`muckman`、`gleaner`、`seedsman`、`croftr`、`furrow`、以及正在排队的 `haymaker`——
**全部都在调一个已经指对方向的信号。** 把 +670 改成 +900 不会让一个不肯拿 +670 的策略
开始拿。**所以 40,681 不是奖励塑形问题。**

**它是信用分配 / 优化问题,而且有一个具体的结构原因**:那 −40 由**市场头**付,
那 +710 由**帮手头**在若干回合之后收(买种子 → 帮手走到空地 → 选中 PLANT 任务)。
两个头是同一时刻的独立分布,共享一个标量优势;买入那一步的优势要靠价值网**预期**到
后面的 +710 才为正。**而 φ 给袋里种子记的 +40 残值,恰好只抵掉买入成本的一半。**

### 对后续的直接含义(不改任何在跑的东西)

1. **不要再排新的势函数权重臂。** 六条已测,带子是 ≤2.3k,而现在有了机制上的解释。
2. **也不要再排解码层臂。** 今晚三次独立确认 +1.8k 到 +3.3k(`thrift` 还崩了尾部)。
3. **值得试的是"让买入那一步看得见 +710"这一类改动**,例如:把 `BUY_SEED` 与 `PLANT`
   合成一个动作(买入即落地,两笔 φ 在同一步结算);或者把帮手头改成**自回归解码**
   (顺序采样,后面的头看得见前面的选择——这同时也是 `crew` 那条判词里撞车的根因)。
   **这两个都是结构改动而不是权重改动,所以它们不在已测的两个带子里。**
4. `haymaker` 仍然会读完(已经排了队,不改),但**它的先验现在应当是 +2k 左右**,
   与其它塑形臂同一带子;它的价值主要是那两个状态读数(FEED 次数、畜群规模)。

### longcredit 的预登记(在结果之前写下)

主树 `--lam 0.99` 对 chisel 配方的 0.95,**一个旋钮,零新代码**,排在 haymaker 之后。

**为什么是这个旋钮**:上一条判词把 40,681 从"奖励塑形"改判为"信用分配"——
φ 每颗西瓜种子已付 +670 而网不拿,回合有(216 个空市场回合、其中 212 个 BUY_SEED 合法)、
买了的种子 100% 都种下了。而 −40 由市场头付、+710 由帮手头在很久之后收。

**实测买单到对应 PLANT 的延迟:中位 6 回合,均值 36,p90 142。**
GAE 对 36 回合后那笔奖励的权重是 `0.95^36 = 0.16` 对 `0.99^36 = 0.70`——
**回到"付钱那一步"的信用多 4.3 倍。**

**它不在今晚测出的两个带子里**:势函数权重 ≤2.3k、解码层 +1.8k…+3.3k,而它两者都不改。

**近端预测**:整季种子从 45 上升(k06 是 207);第 18/28 天空地从 18/27 下降。
**结果预测**:九对手中位超过 `control230` 的 50,063。
**护栏**:λ 调高会放大优势方差。**若 p05 像 `thrift` 那样崩(22,842 → 0),
说明旋钮过头,下一步是 0.97,而不是放弃这条思路。**

**共用对照的说明(诚实标注)**:`haymaker` 和 `longcredit` 都以 `control230`(50,063)
为参照,而那是 gen35 里同配方、变量关掉的一条链——**不是本树同时跑出来的对照**。
两条臂共用同一个不完美参照,所以它们之间可比;与今晚其它数字比较时要记住这一点。

## 2026-08-23 · `backplay-d8`:**反向课程饱和了**。补上缺掉的那一段只值 +10,而三段都停在"磁带减 8k"

`backplay-d8` 是为了补反向课程缺掉的 d8–d11 窗口(当时的理由:那是 6,333/天 的最贵窗口)。
**训练量是够的**:iter **199**,比兄弟 `backplay-d12`(178)和 `backplay-d16`(179)还多,
`bank_frac 1.0`、同一批银行。所以下面两个读数都不是欠训。

**第 0 天整局(13 对手,1,248 局)**:中位 **24,022**、p05 **14,122**、**30% 低于两万**、
held-out 打败 4/10。对 cleo 的 margin −104,858、对 k06 −122,742。

**但第 0 天是错的尺子**,而今晚的血统判词已经预告了这一点:`bank_frac 1.0` 的网
**完全没有第 0 天能力**(接手者独自打全局是 32,706 / p05 1,762 / 19% 低于两万)。
所以按它自己的区间(20 天 cleo 录音 + 它接手)再读一遍,九对手 × 48 种子:

| 课程段 | hybrid 中位 | p05 |
|---|---|---|
| backplay-d16 | 90,409 | 51,840 |
| backplay-d12 | 90,255 | 51,930 |
| **backplay-d8(补上的那一段)** | **90,419** | 50,446 |
| **纯 cleo 磁带(完全没有网)** | **98,420** | 53,043 |

**三段课程的跨度只有 164。** 补上"最贵的那个窗口"买到 **+10**。

### 判词:课程饱和,而且饱和在一个固定的罚分上

**d16 → d12 → d8 三段,hybrid 数字全部落在 90.3–90.4k**,而磁带自己跑是 98,420。
**也就是说:每一个课程网都收敛到"cleo 的磁带减去约 8,000"。**
那 8,000 正是磁带长度扫描量出来的 **−801/天 × 最后 10 天**——
**网接手后的负贡献。加课程段不会改变它,因为它不是"课程不够"造成的。**

**反例(为什么不能读成"课程无用")**:课程**在它自己的区间里**是有效的——
无课程血统的网做 hybrid 只有 76,297–77,484,课程血统的是 88,810–90,419,
**差 13k**。课程买到的是"接手一个建好的农场"这件事;**它已经买满了**,
再加段数买不到更多。

### 对清单的处置

- 任务 #15(反向课程 d20→d16→d12→d8→d4→d0)与 #29(bpd8)**到此判完**:
  **不要再加课程段**。d4、d0 段没有理由再排——d8 已经是 +10,而 d0 段的两个变体
  (`d0-chisel` / `d0-d12`)今晚已经测过,是"第 0 天能力"与"hybrid 能力"的互斥取舍。
- 这条也与今晚的中心判词一致:**90k 属于 cleo 那 20 天,不属于我们加在它后面的任何东西。**

## 2026-08-23 · `croftr`(`--demand-cap 1.0`)**机制没有按设计触发**:西瓜种子一颗没少,而它仍然领先——训练量不等,已补齐

十三对手 × 96 局(1,248 局):

| | 中位 | held-out | p05 | <20k | **iter** |
|---|---|---|---|---|---|
| `control230`(同配方,`demand_cap 0.0`) | 50,063 | 6/10 | 22,516 | 3% | **230** |
| **`croftr`(`demand_cap 1.0`)** | **50,764** | **7/10** | 21,202 | 3% | **175** |

**+701 中位、+1 个 held-out 对手,而它少训练 55 个迭代(24%)。**
所以这个 +701 是**下界**,不是判词——今晚已经在 `furrow`/`gleaner` 上栽过一次同样的坑。
**已排 2 个补训 link + 阵列 + 读数器(20329571-72 → 20329574 → 20329575),
排在 `longcredit` 之后,不与任何东西抢卡。**

### 但机制读数是现在就能定的,而它说这条臂没做它该做的事

`--demand-cap` 的全部目的是**压掉西瓜泵**:西瓜一季只被镇上吃掉 30 份,而 φ 按 base 250
× max_yield 6 给一块地记 1,500,是九种里最高的。`test_croft.py` 的 C4 门也是按
"20 块西瓜地要排到 20 块草莓地之下"来验的,而且过了。

行为(3 种子对 cleo,**机制读数,不是验收判据**):

| | croftr | control230 |
|---|---|---|
| **西瓜种子** | **15** | **15** |
| 草莓种子 | 36 | 24 |
| 第 18 天作物 | 31 | 20 |
| 畜群 | 6 | 4 |
| 每回合帮手 | 8.12 | 7.32 |

**西瓜一颗没少。** 动的是草莓(+12)、作物总数(+11)、畜群(+2)、帮手(+0.8)。
**所以如果这条臂真的有效,它不是通过它被设计的那个通道生效的。**

**这已经是第二次了**:`muckman` 的名字是"粪肥计价",而它实际是通过 畜群→牛奶/羊毛 生效的
(我当时的预登记预测是阴性,因为化肥需求为 0,结果它是同带最好)。
**判词:一个奖励项的名字不是它的通道;门电池验的是"这一项按公式动了",不是"网会因此改行为"。**
`test_croft.py` C4 证明了 φ 的排序翻转,**而排序翻转没有翻转策略**。

**另一条边界(为什么 3 种子那栏的钱不能用)**:同一对照里 3 种子对 cleo 的钱是
57,493 对 26,303(+31,190),而十三对手 1,248 局是 +701。**差 44 倍。**
今晚 `thrift` 已经栽过同一个坑(单种子 +33,758,864 局 +3,268)。
**行为量(种子、作物、畜群、帮手)在 3 种子下还算稳,钱不行。**

### tutor2 的预登记(在结果之前写下):**唯一绕开信用分配的那条路**

gen38,`--kickstart tape:agents/bench3/closer_cleo.py --ks-coef 0.05 --ks-anneal 120e6
--ks-every 2`,**从 chisel 的 324 迭代成熟主干起**,3 个 link,排在所有队列之后
(20329673-75 → 20329681 → 20329682)。

**为什么现在排它**:重构判词已经把 40,681 从"奖励塑形"改判为"信用分配"——
φ 每颗西瓜种子已付 +670 而网不拿(六条塑形臂 ≤2.3k、三条解码臂 ≤3.3k 都是这个结论的证据)。
**模仿是唯一直接绕开信用分配的做法**:它是在学习者自己的状态上做**监督**,
所以不需要任何东西从 PLANT 那一步传回 BUY 那一步。

**为什么这次便宜**:被取消的 `tutor` 预门从随机初始化起,需要 8–10 个 link 才能说话。
这条从成熟主干起,用 `--ks-coef 0.05`——**正是档案在 sower-v1 于第 3 个迭代被杀之后
定下的上界**(成熟主干上新起 CE 是 ~1.2 对策略梯度 ~0.03,四十比一)。
**从没被试过的是"这个上界 + 一个 150k 的老师"**:我们的 kickstart 老师一直只有
barnyard,而它瞄的是 40k。

**已知会穿过掩码多少**(`test_tutor.py` T2/T5 测过):在我们自己的状态上,
farmer 头保留磁带标签的 **100%**,**market 头约一半**。而 market 头正是那个要学会买种子的头,
**所以读到阴性时要记住这个二分之一。**

**近端预测(模仿的读数是行为,不是钱)**:整季种子从 45 涨向 cleo 的 68(k06 是 207);
每回合帮手从 7.9 抬起。**结果预测**:九对手中位对 `control230` 的 50,063。
**护栏**:成熟主干 + 新起 CE 就是 sower-v1 的死法。若 p05 崩、或 money 跨 link 单调下降,
说明主干正在被砸坏,**停,不要靠加 link 硬撑**。

## 2026-08-23 · **根本原因**:市场头已经塌缩——`P(BUY_SEED | 合法)` 中位 **0.02%**,而熵奖励加在 14 个头的**和**上,所以塌缩既不被惩罚也不被显示

前一条判词说"40,681 是信用分配不是奖励塑形",因为 φ 每颗西瓜种子已付 +670 而网不拿。
**但"不拿"有两个互斥的版本,处方完全不同**:策略**根本不采样**那个动作(熵塌缩),
还是**采样了但后续跟不上**(协调失败)。零 GPU 直接把 softmax 读出来就能分开。

在网**自己走到的状态**上(96 个采样点,`nn-d0-chisel`):

| | mean | **median** | p90 | max |
|---|---|---|---|---|
| **`P(任一 BUY_SEED)`,在买种子合法的状态上** | 4.03% | **0.02%** | 9.82% | 98.41% |
| `P(PLANT)` 每只手,在该手能种的状态上 | 21.29% | 21.43% | 55.34% | 55.34% |

**读法**:**播种没有塌缩**(每只手 21%),**塌缩的是买种子**——中位 0.02%,即五千分之一。
分布极度双峰(mean 4%、max 98.4%):它在极少数状态上几乎必买(那就是它一季那 29 次下单),
**在其余绝大多数状态上概率为零**。

**所以不是协调失败,是动作塌缩。** 而这直接解释了"为什么改奖励没用":
`720 回合 × 2e-4 ≈ 每局 0.14 次`。**策略梯度拿不到"多买种子"这个替代动作的样本,
所以无论 φ 把它标价成 +670 还是 +900,梯度都是零。** 六条塑形臂 ≤2.3k 不是巧合。

### 为什么这个塌缩没被任何人发现:熵是**加总**的

`rl/train.py` 用 `ClipPPOLoss(entropy_bonus=True, entropy_coeff=args.ent_coef)`,
**一个标量系数**作用在复合分布的**熵之和**上。而头的构成是
farmer(23)+ market(31)+ **12 个帮手头(各 10)**,理论上限约
`ln23 + ln31 + 12·ln10 ≈ 3.1 + 3.4 + 27.6 ≈ 34`。

**于是 12 个帮手头的熵可以独自把熵奖励喂饱,而市场头安静地塌到 0.0002——
日志里的 `ent` 列(实测 6.45–13.49)看着完全健康。**
**一个头死了,既不在损失里被惩罚,也不在日志里被看到。**

### 而所有资产形成都只走这一个头

市场头是**唯一**能买种子、买地、买牲畜、雇工的头(`MARKET_ACTIONS` 31 个全是单一用途,
没有一个既卖又买)。**所以整条"农场怎么变大"的通道,全部挤在这一个 31 路 categorical 上,
而它塌了。** 下游的读数全是这一条的推论:

整季种子 45(k06 207)→ 只能填 45 块地 → 第 18/28 天空地 18/27(k06 是 2/5)→
土地 2.0(天梯 3.0)→ 畜群 4(天梯 14)→ 收款 92,140 对 132,007。

### 这一条把今晚每一个阴性结果都解释了,而且是同一个原因

| 层 | 实测 | 为什么必然是这个量级 |
|---|---|---|
| 势函数权重(6 条臂) | ≤2.3k | 改的是一个**不被采样**的动作的价格 → 梯度为零 |
| 解码层(3 条臂) | +1.8k…+3.3k | 改的是**已采样分布内部**的执行质量 |
| 反向课程(3 段) | 跨度 164 | 银行状态递给它一个**已建好**的农场;"经营"不需要大量买种子,**塌缩照旧** |
| `croftr` 的机制 | 西瓜 15 对 15 | φ 的排序翻转了,而**策略没有那个动作可翻** |

**反例(为什么不能读成"网太弱")**:同一个网**接手**一个建好的农场能打到 90,419,
只比纯磁带低 8k。**它会经营,不会扩张**——而扩张的那个头塌了。

### 两条处方,恰好对应两条已排的臂

1. **`tutor2`(已排,队尾)——直接对症。** 交叉熵是**监督**,它把动作**写进**策略,
   **不需要策略先采样到它**。这正是"梯度被饿死"的解法,也是这条根本原因给出的唯一
   已排的正确处方。
2. **`longcredit`(已排)——对症但对的是次要那条。** λ 0.95→0.99 改善的是
   **已被采样**动作的信用传播;对 `P=2e-4` 的动作,传播多少信用都乘以零。
   **先验因此下调:预期 ≤2k。**

**还没排的、直接攻塌缩的那条:给市场头单独的探索压力。**
最小实现不是改损失(TorchRL 的复合分布要拆开算 per-head 熵),而是在**采集时**
把 ε 份"合法动作上的均匀分布"混进市场头,并**按混合分布记 `sample_log_prob`**
(这样 PPO 的重要性比仍然正确)。一个旋钮 `--market-eps`,
**既不在势函数权重那个带子里,也不在解码层那个带子里。**

### prospect 的预登记(在结果之前写下):**第一条直接攻塌缩的臂**

gen40 `--market-eps 0.05`,单变量,4 link,挂在 `haymaker` 末链之后(20331632-35 →
20331636 → 20331637),与 `longcredit` 交错跑——这是有意的:按根本原因判词,
**`longcredit` 的先验已下调到 ≤2k,而这一条是先验最高的那个**,不该排在它后面。

**它攻的是被测出来的那个量本身**:`P(任一 BUY_SEED | 合法)` 中位 **0.02%**。
`--market-eps` 把 ε 份"合法动作上的均匀分布"混进市场头,**混合发生在分布内部**,
所以采集与 PPO 的重要性比用的是同一个策略——这是在正确地优化一个 ε-下界策略,
不是把 off-policy 采样硬塞进 on-policy 损失。

`test_eps.py` E1–E6 **EPS-PASS**,ε 买到的东西:

| ε | 每个合法动作的下界 | **`P(BUY_SEED)`** | 基线 |
|---|---|---|---|
| 0.02 | 0.00143 | 0.00717 | 0.00003 |
| **0.05** | 0.00357 | **0.01789** | 0.00003 |
| 0.20 | 0.01429 | 0.07145 | 0.00003 |

**ε=0.05 把塌掉的那个量抬了约 600 倍**,即每局约 13 次探索性买种子,而现在是 0.14 次。
**梯度第一次不是零。**

**近端预测(按发现它的同一种方式量,不用钱)**:`P(任一 BUY_SEED | 合法)` 的**中位**
必须从 0.02% 抬起;随后整季种子从 45、第 18/28 天空地从 18/27 动。
**结果预测**:九对手中位对 `control230` 的 50,063。
**护栏**:ε=0.05 相对导出所用的**未混合**策略是市场头 KL **0.25**(E6 记录)。
若 p05 像 `thrift` 那样崩,说明下界太高,下一步是 **0.02**(KL 0.083),而不是放弃。

**一个必须一起记的实现事故(它差点变成一条静默的阴性)**:`train.py` 是**平铺**
`import trl_policy` 的(`sys.path` 带了 `tensor_env/`),所以 setter 必须走同一个模块对象;
写成 `from tensor_env import trl_policy` 会**新建第二个模块**,分布永远读不到那个全局,
于是**命令行写着 0.05、实际按 0 训练**。已改并验证 setter 确实改到分布读的那个全局。

**门电池自己也先假过一次,已记在文件里**:第一版用均匀随机 rollout 造状态,
而随机策略会把两家农场打到破产,于是第 12 天**市场掩码每条 lane 只剩 1 个合法动作(NOOP)**
——门在测一个单动作分布的情况下变绿了。**这与 `croftr` 的 C4 是同一种假阳性**
(公式动了,结果没意义)。现在下界与采样两组门用**受控掩码**(14 个合法动作,
即网选 `BUY_PRODUCT` 那 224 个回合的实测中位,且必含全部 5 个 `BUY_SEED`),
真实状态只留给逐字节与合法性那两组门。

## 2026-08-23 · 根本原因的**修正与收紧**:真正死掉的是 `BUY_LAND`(中位与均值**都是 0.00%**),而 `BUY_SEED` 是"尖峰但被饿死"

`tools/head_health.py`(已进仓库):从任何导出上直接读每个头的熵与**按家族**的概率质量,
一局约 3 秒,所以链跑到任何一个 link 都能查,不必等几小时的九对手阵列。
两个刻意的设计:状态取自**真实对手的对局**(均匀随机 rollout 会把两家打到破产,
第 12 天掩码只剩 `NOOP`——`test_eps.py` 第一版就是在那种退化状态上假过门的);
每个家族都**条件在"该家族合法"**上(无条件的 `P(BUY_SEED)` 会把"策略不肯买"
和"买被掩码掉了"混在一起,而这两者的处方相反)。

对 k06 一局,每 7 步采一次:

| | H(mkt) | 上限 | BUY_SEED | **BUY_LAND** | BUY_ANIMAL | HIRE | SELL | BUY_WHEAT | PLANT |
|---|---|---|---|---|---|---|---|---|---|
| | | | 中位/均值 | 中位/均值 | 中位/均值 | 中位/均值 | 中位/均值 | 中位/均值 | 中位/均值 |
| `nn-d0-chisel` | 1.15 | 2.48 | 0.02/**4.03%** | 0.00/**0.00%** | 0.00/0.54% | 0.00/5.47% | 27.7/37.0% | 22.7/26.6% | 20.6/21.3% |
| `nn-backplay-d16` | 0.92 | 2.56 | 0.00/3.54% | 0.00/**0.01%** | 0.00/0.50% | 0.00/5.27% | 12.6/24.2% | 17.9/30.8% | 18.5/17.4% |

### 修正:我上一条把"塌缩"说得太宽了

上一条只报了 `BUY_SEED` 的**中位** 0.02%,并据此说"市场头塌缩"。
**加上均值以后,四个采购家族分成了两类,而这个区分很重要:**

- **`BUY_LAND` 是唯一中位与均值**都是** 0.00% 的——它是真的死了。**
- `BUY_SEED` 中位 0.02% 但**均值 4.03%**:它是**尖峰**的(一季 29 次下单集中在少数状态),
  不是死了,是**被饿死**——绝大多数状态上为零。
- `HIRE` 中位 0.00% / 均值 5.47%,而每回合帮手到 7.8:**尖峰但功能正常**。
  **所以只看中位会把一个能用的动作误判成死的**——这就是为什么工具两个统计量都打。
- `BUY_ANIMAL` 均值 0.54%,对应畜群 4(天梯 14):极低但非零。

### 而 `BUY_LAND` 死掉这件事,和档案里最早的那条诊断对上了

iter-160 census(`docs/RUNS.md` 2026-08-21)当时的结论是
**"经济是被土地卡住的"**。现在有了机制:**买地这个动作的概率是零。**
土地 2.0 对天梯 3.0,而一个象限是 25 块地——**第三个象限就是那 25 块空地的来源。**

### 这让 `prospect` 的预期更具体,而且更好

`--market-eps 0.05`,`n_legal` 中位 12 → 每个合法动作的下界是 `0.05/12 = 0.42%`/回合。

| 家族 | 现在(均值) | ε=0.05 的下界 | 每局期望次数:现在 → 之后 |
|---|---|---|---|
| **`BUY_LAND`** | **0.00%** | **0.42%** | **≈0 → ≈3** |
| `BUY_SEED`(5 个动作) | 4.03% | 2.1% | 29 → 泛化到全局状态 |
| `BUY_ANIMAL`(3 个动作) | 0.54% | 1.25% | 4 → ≈9 |

**买地从"精确为零"抬到"每局约 3 次"是这三条里最值钱的一条**,因为
`BUY_LAND` 是唯一**门控**其它一切的动作:没有第三个象限,种子和牲畜都无处安放。
**所以 prospect 的近端读数应该先看 `BUY_LAND` 的均值离开 0.00%,再看土地是否到 3。**

## 2026-08-23 · `haymaker` 判词:**+723,而它用的机制是"少养一头牛",不是"自己种小麦"**——预登记的近端预测失败、护栏触发

九对手 × 48 种子(864 局),对 `control230` 的 50,063:

| | 中位 | held-out | p05 | <20k |
|---|---|---|---|---|
| `control230`(同配方,变量关闭) | 50,063 | 6/10 | 22,516 | 3% |
| **`haymaker`(`--feed-debit 1.0`)** | **50,786(+723)** | 4/7 | 24,585 | 2% |

**预登记的三条(commit 79297b2)对了一条、错了两条:**

| 预登记 | 结果 |
|---|---|
| 近端:整季小麦种子 0 → **>50** | **WHEAT 1。失败。** |
| 近端:饲料支出从 54,050 下降 | **29,836。成立(−24,214)。** |
| 护栏:第 18 天畜群**不得**跌破 6 | **5。触发。** |
| 结果:九对手中位超过 50,063 | 50,786,+723(在 ≤2.3k 带子内,先验 ≈+2k) |
| 第 0 天整局 margin 好过 chisel 的 −54,849 | **−57,347。失败。** |

### 机制:它满足新奖励项的方式是**缩小畜群**,而不是种饲料

饲料支出确实掉了 24,214,而**小麦种子只有 1 颗**、畜群从 6 掉到 5。
**所以那 24,214 不是"自己种出来的",是"少养了牲畜所以少吃"。**

**这正是根本原因判词预测的行为**:新的奖励项说"要么种小麦、要么少养牲畜",
而**"种小麦"需要 `BUY_SEED_WHEAT`,那是被饿死的那个动作**;
**"少买牲畜"是它已经能采样的动作。策略选了它已经有的那条路。**
这是"改奖励改不动一个不被采样的动作"最干净的一次直接演示——
**奖励项本身生效了(账本上 −24,214 是真的),而它生效的通道是错的那一条。**

### 更正 `d25007a`:`BUY_LAND` 的 0.00% 是 `nn-d0-chisel` 一个网的性质,不是这一族的

`tools/head_health.py` 现在还打**合法率**那一栏(因为"策略不肯"与"策略不能"处方相反):

| | H(mkt) | BUY_SEED 中位/均值/**合法率** | BUY_LAND 中位/均值/**合法率** |
|---|---|---|---|
| `nn-d0-chisel` | 1.15 | 0.02 / 4.03 / **93%** | 0.00 / **0.00** / **67%** |
| **`c230-samp`(对照,变量关闭)** | 1.09 | 0.00 / 4.99 / 87% | 0.00 / **1.44** / 66% |
| `croftr-samp-t0` | 1.10 | 0.04 / 6.93 / — | 0.00 / 1.39 / — |
| `haymaker-t0` | 1.03 | **0.43** / 6.13 / 88% | 0.00 / 1.39 / 71% |

**对照本身的 `BUY_LAND` 就是 1.44%,不是 0。** 所以我上一条写的
"`BUY_LAND` 中位与均值都是 0.00%,它是真的死了"**是拿一个网推广到一族,收回。**
准确的说法是:**`BUY_LAND` 在整族里都极低(0.00–1.44%),在 `nn-d0-chisel` 那条
血统上恰好是 0.00%**;而四个网**全部**停在土地 2.0。

**而新加的合法率那一栏给出了一个更硬的事实**:
**`BUY_LAND` 在 66–71% 的回合上是合法的。** 所以**这不是"买不到",是"不买"**——
可用性充足,概率极低。**这正是 `prospect` 的 ε 下界能碰到的那一类。**

### 唯一的正面信号,以及它为什么还不够

`haymaker` 是**目前唯一把 `BUY_SEED` 中位抬起来的臂**:0.02% → **0.43%,21 倍**。
但 **0.43% 仍然远远不够**——它一季买 47 颗种子(对 k06 的 207),
而钱的效应落在 +723,和其它五条塑形臂同一带子。

**所以这条臂的价值不在那 +723,在于它把根本原因判词从"论证"变成了"演示":
一个真实生效的奖励项,在通道被塌缩堵住时,会从旁边那条已经通的路上流走。**

**后续处置**:护栏说的 `--feed-debit 0.5` **不排**——因为把权重减半只会让"少养牲畜"
这条路更划算,而堵塞的那条路不会因此打开。**正确的顺序是先解塌缩(`prospect`),
再回来看饲料负债是否终于走对通道。** 这条留档为"等 prospect 之后再议"。

### prospect 预登记的**方法学更正**:`head_health.py` 读不到 ε 下界,它读的是**学到的**头

`prospect` 第 1 link(iter 36,检查点里 `market_eps 0.05` 确认在)导出后测:

| | H(mkt) | BUY_SEED 中位/均值 | BUY_LAND 中位/均值 | BUY_WHEAT 中位 |
|---|---|---|---|---|
| `c230-samp`(对照) | 1.09 | 0.00 / 4.99% | 0.00 / 1.44% | 20.85% |
| `pros-probe`(iter 36) | 1.21 | 0.01 / 4.58% | 0.00 / **0.00%** | **12.03%** |

**看起来"没动",但这个读法是错的**,而错在我的预登记而不在这条臂:
**`export_agent.py` 导出的是"未混合"的策略**(`test_eps.py` E6 已经把这件事记成
KL 0.25),所以 `head_health.py` 在 `prospect` 的导出上量到的是**原始 logits**,
**看不到训练时加在分布里的那个 ε 下界。**

**所以预登记里"`P(任一 BUY_SEED | 合法)` 的中位必须抬起"这一条,
量的是"策略自己学没学会",不是"下界有没有加上"。** 而那是**链跑完之后**才能问的问题
——ε 的作用机制是:探索先把动作采样出来 → 有了梯度 → **策略自己把 logits 抬上去**。
**iter 36 抬不起来是正常的,不是阴性。**

**这条同时是一个必须记住的部署事实**:因为导出没有 ε,
**`prospect` 学到的东西必须体现在原始 logits 上才在天梯上有意义**。
换句话说,**ε 是脚手架,不是产品**;若链跑完后原始头仍然没动而只有九对手中位动了,
那要怀疑是别的东西在起作用。

(已经在动的两个数:`H(mkt)` 1.09 → 1.21,`BUY_WHEAT` 中位 20.85% → 12.03%。
**但这不是判词——按准则 (d),没跑九对手阵列不算测过。**)

## 2026-08-23 · `prospect` **阴性(−3,663)**:ε 探索在这个游戏里是**直接的收入税**,因为探索预算和收入通道是同一个稀缺资源

九对手 × 48 种子(864 局),对 `control230` 的 50,063:

| | 中位 | held-out | p05 | <20k |
|---|---|---|---|---|
| `control230` | 50,063 | 6/10 | 22,516 | 3% |
| **`prospect`(`--market-eps 0.05`)** | **46,400(−3,663)** | 4/7 | 21,922 | 3% |

**预登记(da839e9)全部失败,而且是"往反方向"失败的:**

| 预登记 | 结果 |
|---|---|
| 近端:整季种子从 45 上升 | **40。下降。** |
| 近端:第 18/28 天空地从 18/27 下降 | **22/23。变差。** |
| 结果:中位超过 50,063 | **46,400。−3,663。** |
| 第 0 天 margin 好过 −54,849 | **−64,115。失败。** |
| 护栏:p05 是否像 thrift 那样崩 | **没崩**(21,922 对 22,516),`<20k` 都是 3% |

**护栏没触发,所以这不是"旋钮调过头"——是这条思路本身不对。**

### 机制:ε 花掉的是**市场回合**,而市场回合就是收入本身

链跑完后原始头几乎没动(`head_health.py`):

| | H(mkt) | BUY_SEED 中位/均值 | BUY_LAND 均值 | SELL 中位 |
|---|---|---|---|---|
| `c230-samp`(对照) | 1.09 | 0.00 / 4.99% | 1.44% | 32.80% |
| `prospect-t0` | 1.24 | 0.03 / **5.45%** | **1.52%** | 21.62% |

**买种子的均值只从 4.99% 动到 5.45%,买地从 1.44% 到 1.52%。** 四个 link(约 150 迭代)
没能把探索转成 logits 的变化。**而代价是立刻付的**:

**市场头每回合只出一种单**(这是今晚早先测过的:我们 100% 的收款都来自"只有 SELL"的回合,
而 k06 有 56% 来自混合回合)。所以**把 5% 的市场回合换成均匀随机抽,就是把 5% 的卖出扔掉**
——而 SELL 是这个头唯一的收入动作(均值 37%)。**探索预算和收入通道是同一个资源。**

**这和常见的 ε-greedy 场景不同**:在多数环境里随机一个动作近乎中性,
而这里 720 个市场回合是硬预算、且是收入的唯一出口,**所以 ε 是一笔直接的收入税**。
再加上**导出的是未混合策略**(`test_eps.py` E6,KL 0.25),
**下界本身在部署时消失,只剩下学到的那点残余** —— 于是这条臂**付了训练期的税,交付的却只有残余**。

**所以不排预登记里那个 `ε=0.02` 的回退**:0.02 只是**更小的税配更小的下界**,同一笔交易、
同一个符号,没有理由期待翻转。**护栏写的是"崩了就降",而它没崩,是"不划算"。**

### 这条阴性把 `tutor2` 的先验**抬上去**了

**监督不花回合。** 交叉熵直接改 logits,**不需要策略先把动作采样出来,也不占用任何市场回合**
——正是这条阴性揭示的那笔税,`tutor2` 完全不付。
**所以在"塌缩"这个诊断下,唯一还站得住的处方是模仿,而不是探索。**
`tutor2`(gen38,`--kickstart tape:closer_cleo.py --ks-coef 0.05`,3 link)仍在队列尾部。

**同时保留的反面证据**:`prospect` 的 `H(mkt)` 确实从 1.09 抬到 1.24,`BUY_ANIMAL` 均值
0.31% → 0.92%(3 倍)。**所以 ε 机械上是生效的**——它没有失败在实现上,
**失败在这个游戏的动作预算结构上。**

## 2026-08-23 · 操作事故:`longcredit` 的四个 GPU link 白跑了测量(训练没丢),因为 sed 换了运行名没换**树路径**

`lc_array.sh` 是从 `hay_array.sh` sed 出来的(`s/haymaker/longcredit/g`),
而 `hay_array.sh` 第 6 行是 `cd /scratch/jwj/Kaggriculture-gen39`——**haymaker 的树**。
`longcredit` 训练在**主树**。于是九个任务在 gen39 里 `cp rl/runs/longcredit/latest.pt`
(不存在)、导出失败、`eval.py` 失败,**而每个任务照旧打印 `LC-TASK-DONE`**
(脚本是 `set -u` 不是 `set -e`),九个 eval JSON **一个都没写**,读数器在 `arm_behaviour`
那一步才炸出 `FileNotFoundError`。

**为什么我早先那次"阵列对读数器"的路径审计没抓到**:我比对的是**相对路径**
(两边都是 `rl/runs/longcredit/eval`,一致),**而它们在不同的树里。**
**相对路径一致不等于同一个目录。**

**修法**:重跑的 `lc2_array.sh` 里每一步都加了硬检查——
`test -f` 检查点、`||` 退出的 `cp`/`export`/`eval`、以及最后 `test -s` 确认 JSON 非空,
**所以它要么产出数据,要么以非零码失败,不会再"打印 DONE 而什么都没做"。**
训练检查点在主树里完好(iter 147、`lam 0.99`),**所以只重跑 CPU 测量,不重跑 GPU**。

## 2026-08-23 · `longcredit` 也是**阴性(−3,703)**,尾部还更差 —— 两条"信用分配侧"的臂**用同一个理由输**

九对手 × 48 种子(864 局),对 `control230` 的 50,063:

| | 中位 | held-out | p05 | <20k |
|---|---|---|---|---|
| `control230` | 50,063 | 6/10 | 22,516 | 3% |
| `prospect`(`--market-eps 0.05`) | 46,400(−3,663) | 4/7 | 21,922 | 3% |
| **`longcredit`(`--lam 0.99`)** | **46,360(−3,703)** | **3/7** | **20,206** | **5%** |

预登记(da68252)同样全败:整季种子 45 → **37**(下降)、第 18/28 天空地 18/27 → **24/29**(变差)、
第 0 天 margin **−65,493**(尺子 −54,849)。**护栏也没触发**(p05 22,516 → 20,206,掉 10%,
不是 `thrift` 那种崩到 0),**所以同样不是"旋钮过头",是思路本身不成立。**

### 两条臂的失败共用一个结构性理由

我把 40,681 从"奖励塑形"改判为"信用分配"之后,排了两条攻信用分配的臂。**两条都是 −3.7k。**

| 臂 | 它想改什么 | 为什么在这个游戏里必然亏 |
|---|---|---|
| `prospect` ε=0.05 | **让被塌缩的动作被采样到** | 采样要花**市场回合**,而市场头每回合只出一种单、我们 100% 的收款来自"只有 SELL"的回合 → **ε 是直接的收入税** |
| `longcredit` λ=0.99 | **让 PLANT 的信用传回 BUY 那一步** | 传回来的信用要乘上**那个动作的概率**,而 `P(BUY_SEED)=2e-4` → **信用 × 0 还是 0**,换来的只有优势方差变大(尾部 p05 −2,310、`<20k` 3%→5%) |

**所以"信用分配"这个诊断是对的,但它给出的两个自然处方在这个动作空间里都自带一笔它们付不起的代价。**
`prospect` 付的是收入,`longcredit` 付的是方差。**而堵住的那条路,两条都没打开**
(`prospect` 的原始头 `BUY_SEED` 均值只从 4.99% 动到 5.45%)。

**不排 `--lam 0.97` 的回退**,理由和不排 `ε=0.02` 一样:**更小的方差配更小的传播,同一笔交易、同一个符号。**

### 于是本晚测过的层已经全部收口,只剩一条没测

| 层 | 臂数 | 结果 |
|---|---|---|
| 势函数权重 | 6(muckman/gleaner/seedsman/croftr/furrow/haymaker) | **≤+2.3k**;`haymaker` 演示了奖励项会从旁边通的路流走 |
| 解码层 | 3(`WHEAT_BUY_EXACT`/`thrift`/`crew`) | **+1.8k…+3.3k**,`thrift` 还崩了尾部 |
| 反向课程 | 3 段(d16/d12/d8) | **跨度 164**,饱和在"磁带减 8k" |
| **信用分配 / 探索** | **2(`prospect`/`longcredit`)** | **两条都 −3.7k** |
| **模仿** | **1(`tutor2`)** | **还在队列里,唯一没测的** |

**`tutor2` 现在是唯一剩下的处方,而它恰好不付上面那两笔代价**:
**交叉熵直接改 logits——不需要先采样到动作(不付 `prospect` 的收入税),
也不依赖信用穿过时间(不付 `longcredit` 的方差税)。**
它在队列尾部(gen38,3 link,20329673-75 → 20329681 → 20329682)。
**如果它也阴性,那么"在这个动作空间里用 RL 从第 0 天建起一个 10 万级的农场"这条路
在本代框架下就没有已知的可行处方了**,而下一步只能是改**动作空间本身**
(让一个市场回合能同时卖和买,从而让探索不再与收入争抢同一个资源)。

## 2026-08-23 · 吞吐剖析:**GPU 在 B=1024 上几乎白拿** —— 采集占 97%,而采集里引擎是发射延迟受限的;唯一大杠杆是 B

用户问"耗时最高的地方在哪"。日志自带的拆分已经给了第一层答案,三条链一致:

| | 每迭代 | 其中 collect |
|---|---|---|
| `croftrTU` | 38.6s | **37.4s(96.9%)** |
| `prospect` | 40.8s | **39.5s(96.8%)** |

**PPO 更新只占 1.2–1.3s。** 每迭代 736,256 lane-steps ÷ B=1024 = **719 个批量 step**,
即 **54.9 ms / 批量 step**、**53.65 µs / lane-step**。对一张 H100 上 1024 条 lane 的
整型张量运算,54.9 ms 不可能是算力,**是 Python 每步 + 上千个小 kernel 的发射延迟。**

### 决定性的对照:CPU 4 线程比 GPU 还快

同一份引擎,CPU:

| | lane-steps/s |
|---|---|
| **GPU,B=1024(实测训练)** | **18,000** |
| CPU 1 线程,B=512 | 18,957 |
| **CPU 4 线程,B=512** | **29,833** |
| CPU 8 线程 | 18,492 |
| CPU 16 线程 | 8,473 |

**线程扩展性是负的:4 线程是最优,8 线程比 1 线程还差,16 线程差 2.2 倍。**
引擎是成千上万个小算子,线程池开销压过收益 —— 这也解释了为什么评测作业
`OMP_NUM_THREADS=1` + 进程级并行是对的。**而我们的训练作业设的是
`OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`=6,已经过了最优点。**

### 但 CPU 全流程并不更快,因为策略前向在 CPU 上很贵

`obs_dim = 4867`。B=512、4 线程下**策略前向 16.59 ms/step**,和整个引擎(约 15–17 ms)相当:

| | ms/step | 折算 sps |
|---|---|---|
| CPU:引擎+掩码+φ | ~15–17 | — |
| CPU:策略前向 | **16.59** | — |
| **CPU 合计** | **~34** | **~15,200** |
| GPU 实测 | — | **18,000** |

**所以 GPU 挣的是策略那一半(4867→1024→512 是真 FLOPs,在卡上近乎免费),
亏的是引擎那一半(发射延迟)。CPU-only 不是提速,是略慢。**

### 于是杠杆只有一个,而且档案自己早就写了

`DESIGN.md §5` 的 GPU 申请理由是按 **B≈2048–8192** 写的,显存账算的是
**"B=8192 × 状态 ~4KB/局,一张 48GB L40S 富余一个数量级"**。
`README.md §5` 的实测是 **单卡 L40S、B=4096、真实策略负载 228.6k(含掩码+采样 142.5k)**,
以及 **"端到端训练吞吐 ~40k(采集占 95%)"**。

**而我们在一张 80GB H100 上跑 B=1024、18k。** 也就是说:
**B 比设计小 4–8 倍,吞吐比自己记录的端到端数字低 2.2 倍,比 B=4096 的基准低 8 倍。**

**因为引擎是发射延迟受限、策略是 FLOPs 受限,提高 B 两边都赢**:
每步的 kernel 数量不变,而每个 kernel 处理的 lane 变多。**B=1024 → 4096 的现实目标是 ~8×**
(25 分钟一个 link 从 40 迭代变成约 320)。

**代价必须写清楚:B 改了 PPO 的有效批量,今晚整条带子
(塑形 ≤2.3k、解码 +1.8…3.3k、信用侧 −3.7k)全部以 B=1024 为基线,
所以换 B 之后必须重跑一个对照才能继续比。这是一笔真实的账,不是免费加速。**

### 三条不需要动 B 的、今晚就能拿的

1. **`--cpus-per-task` 6 → 4**(实测最优点),并把 `OMP_NUM_THREADS` 跟着改。
   既不丢吞吐(6 已过最优),又让作业成为更轻的调度目标 —— 今晚的真实瓶颈是排队,
   不是算力(02:00 前后有整段 0 卡可用,07:28–07:37 又空了 9 分钟)。
2. **不要再把 GPU 链串起来。** 我今晚用 `afterany` 把 5 条链串成一条,理由是"避免自相竞争";
   但真实约束是**空卡数**,06:07 和 07:42 各有两张卡空出来时,只有两条链能用上,
   其余都被自己的依赖挡住。**独立的链会吃掉每一张空出来的卡。**
3. **对手座位的 φ 已经被 `opp_lambda` 门住了**(`trl_env.py:594/671`),而所有臂都没开它,
   所以 φ 每步只算一次 —— **我上面第一版微基准给两个座位都算了,高估了 φ 的占比;
   这一条更正在此,不改结论(φ 单座位约占 15%,引擎仍是最大项)。**

**没有的东西**:`torch.compile` / CUDA graphs / AMP 在当前路径里**一个都没有**。
而 `engine_t.py` 里有 **9 处依赖张量值的分支**(`.item()`/`bool()`/`.any()`/`.all()`),
**会打断 CUDA graph**,所以 `mode="reduce-overhead"` 不是一行能加上的 —— 它是一条独立的工程,
而且必须过 `test_rules_pin`/`test_multi`/`test_b3` 那几道逐字节门才能信。

## 2026-08-23 · **更正四条判词的符号**:今晚所有臂都在 9 对手场上,而我一直拿 13 对手场的对照跟它们比

`control230` 在**同一个 9 对手场**上重测(纯 CPU,同一份导出 `c230-samp`):

| `control230` 测在哪个场 | 中位 | held-out | p05 | 局数 |
|---|---|---|---|---|
| **13 对手(我一直引用的那个)** | **50,063** | 6/10 | 22,516 | 1,248 |
| **9 对手(与今晚所有臂同场)** | **45,671** | 3/7 | 21,761 | 864 |

**同一个 agent、同一份权重,换个场差 +4,392。** 13 场 = 9 场 + `{k06, random, ghost×2}`,
其中三个我们 100% 赢且钱很高(`random` +61,557、两个 ghost +44,371/+45,108),
一个碾压我们(`k06` −75,783)。**三赢压过一负,所以 13 场的中位系统性偏高。**

### 按同场对照重算,四条臂**全部为正**,其中两条我把符号写反了

| 臂(9 对手,864 局) | 中位 | **对同场对照 45,671** | held-out | 我之前发的 |
|---|---|---|---|---|
| **`haymaker`** | 50,786 | **+5,115** | 4/7 | ~~+723~~ |
| **`croftrTU`** | 48,141 | **+2,470** | 4/7 | (本条首次) |
| **`prospect`** | 46,400 | **+729** | 4/7 | ~~**−3,663**~~ |
| **`longcredit`** | 46,360 | **+689** | 3/7 | ~~**−3,703**~~ |
| `control230-n9` | 45,671 | — | 3/7 | — |

**错因**:`control230` 是早先用 13 对手的花名册脚本测的;今晚的臂用的是我新写的 9 对手
阵列模板,**而我换了场却没有重测基线**。**这不是统计噪声,是拿两个不同的场做减法。**

### 哪些结论要改,哪些不改

**要改**:
- **`prospect` 与 `longcredit` 不是阴性,是边际正**(+729 / +689)。所以我写的
  "**两条信用分配侧的臂用同一个理由输**"**不成立,收回。** ε 的收入税与 λ 的方差税
  **都是实测存在的机制**(收款 100% 来自"只有 SELL"的回合;信用 × 2e-4),
  但它们的净效应是**大致抵消**,不是压倒。
- **`haymaker` 是今晚最好的一条,+5,115,已经越过我宣布的"塑形 ≤2.3k"那条带子。**
  那条带子的上界本身也是拿 13 场对照算的,**所以整条带子的数值都要按同场重算才可信**。

**不改**(因为它们是行为读数,不依赖中位):
- `haymaker` 是靠**缩小畜群**(6→5)而不是种小麦(1 颗)满足新奖励项的;
- `prospect` 的原始头几乎没学动(`BUY_SEED` 均值 4.99% → 5.45%);
- `croftr` 的西瓜种子一颗没少(15 对 15);
- 市场头塌缩本身(`P(BUY_SEED|合法)` 中位 0.02%)、`BUY_LAND` 合法率 66–71%、
  帮手 96% 的 PASS 发生在有活时 —— **全部是状态/概率量,与对手场无关。**

**留档的操作纪律**:**换对手场等于换尺子,必须同场重测基线,而不是复用旧数字。**
今晚的教训序列已经三条同源:相对路径一致不等于同一个目录(`longcredit` 的树错)、
中位一致不等于同一个分布(`th-hyb20` 逐字节相同)、**现在是"对照数字一致不等于同一个场"。**

## 2026-08-23 · `tutor2`(模仿)**+133,等于零** —— 但机制是新的:**开环磁带的交叉熵有"逆频率偏置",它教会常做的动作、压死罕做却门控的那个**

九对手 × 48 种子(864 局),对**同场** `control230-n9` 的 45,671:

| | 中位 | held-out | p05 | <20k |
|---|---|---|---|---|
| `control230-n9` | 45,671 | 3/7 | 21,761 | 3% |
| **`tutor2`(`--kickstart tape:cleo --ks-coef 0.05`)** | **45,804(+133)** | 3/7 | 23,078 | 2% |

**护栏没触发,而且明确没触发**:money 跨三个 link 是 **43,041 → 44,240 → 45,009**(在涨,不是单调降),
CE 稳在 1.31–1.39 而系数按计划退火 0.04 → 0.02 → 0.01,p05 还比对照好 1,317。
**所以 sower-v1 那种"成熟主干被 CE 砸坏"没有发生 —— `ks-coef 0.05` 是安全的,也是无效的。**

**预登记的近端预测失败**:整季种子应从 45 涨向 cleo 的 68,**实测 43**;
小麦种子只有 **3**(cleo 68、k06 138)。

### 但头确实动了,而且动的方向解释了一切

| | `BUY_SEED` 中位/均值 | **`BUY_LAND` 均值** | `HIRE` 均值 | 第 18/28 天空地 |
|---|---|---|---|---|
| `c230-samp`(对照) | 0.00 / 4.99% | **1.44%** | 7.03% | 13 / 12 |
| **`tutor2-t0`** | **0.87** / 6.11% | **0.08%** | 8.35% | **22 / 26** |

**`BUY_SEED` 的中位 0.00% → 0.87%,是今晚所有臂里抬得最高的**(`haymaker` 是 0.43%)。
**而 `BUY_LAND` 的均值从 1.44% 掉到 0.08%,几乎被抹掉。**

**机制**:交叉熵把概率推向**被标注**的动作,于是**未被标注的动作被一并压下去**。
而开环磁带的标签分布是按**频率**来的:cleo 一局买几十次种子、雇几十次工,
**但只买 2 次地**。所以land 这种"一局两三次、却门控其它一切"的动作**几乎拿不到标签质量,
反而被挤下去**。

**这就解释了为什么它的行为整体变差**:种子买得略多(43)、帮手略多(8.11),
**但地还是 2.0,而空地从 13/12 恶化到 22/26** ——
**它学会了多买种子,却失去了买地来种它们的能力。**

**判词:开环磁带的模仿有逆频率偏置。它能传"高频的操作习惯",不能传"低频的资产决策"——
而这个游戏的瓶颈恰好是后者。** 这与两条信用分配臂的失败是**不同的**失败:
那两条是代价付不起,这一条是**标签本身没有那个信息**。

### 今晚五个层全部测完,同场重算后的全貌

| 层 | 臂 | 对同场 45,671 |
|---|---|---|
| 势函数权重 | **`haymaker`** | **+5,115** |
| 势函数权重 | `croftrTU` | +2,470 |
| 探索 | `prospect` | +729 |
| 信用视野 | `longcredit` | +689 |
| **模仿** | **`tutor2`** | **+133** |
| 解码层(另测) | `crew` / `thrift` / `WHEAT_BUY_EXACT` | +1.8k…+3.3k(`thrift` 崩尾) |
| 反向课程(另测) | d16/d12/d8 | 跨度 164,饱和 |

**最好的一条是 +5,115,而缺口是 ~58,800(45,671 → 104,500)。所有已测的杠杆合起来
也不到缺口的两成,而且它们互相不叠加(解码层已两次证明不叠加)。**

**剩下唯一没被测过的形状是改动作空间本身**:让一个市场回合能**同时卖和买**。
它同时解掉今晚两条独立测出来的约束 ——
`prospect` 的收入税(探索不再与卖出争抢同一个回合)与
市场头的塌缩诱因(买地/买种子不再需要牺牲一次卖出)。
**而 `tutor2` 这条判词又给它加了第三个理由**:如果买地不再与卖出竞争,
它就不必靠"抢一个稀缺回合"来发生,**低频门控动作被挤压的那个机制也随之消失。**

## 2026-08-23 · `bazaar`:**让一个市场回合同时卖和买 = +3,824,零 GPU、零重训** —— 动作空间这条假设第一次拿到正面证据

三条臂今晚各自以不同方式失败,而三者的机制都归到同一处结构:**31 个市场动作全是单一用途,
没有一个既卖又买,所以每一次采购都要付掉那一回合的卖出。**

**我原本的设想会把头从 31 加宽到 42 —— 而档案里加动作的臂 8 条 7 阴。** 所以改成
**不加任何动作**:`tools/build_bazaar.py` 在**解码层**给"这一回合有采购、且还没卖"的动作
附上一笔"当前最值钱的卖出"。同一个 31 路头、同样掩码、同样宽度,**现有检查点直接可用**
—— 于是可以在现成导出上零 GPU 测,这也是它在申请任何一张卡之前就被测掉的原因。

**同一份导出(`c230-samp`),九对手 × 48 种子:**

| | 中位 | **对同场 45,671** | held-out | p05 | <20k |
|---|---|---|---|---|---|
| `control230-n9`(未打补丁) | 45,671 | — | 3/7 | 21,761 | 3% |
| **`bz-all`**(卖全部) | **49,312** | **+3,641** | **4/7** | **22,855** | 3% |
| **`bz-half`**(卖一半) | **49,495** | **+3,824** | **4/7** | 21,293 | **2%** |

**尾部没有变坏**(`bz-all` 的 p05 甚至比对照高 1,094),held-out 从 3/7 涨到 **4/7**。
**而 `bz-half` ≈ `bz-all`(差 183,噪声内)—— 说明收益来自"没丢掉那个回合",
不是来自卖多少。** 这正是机会成本那个说法的形状。

**混合回合从 0 变成 168**(占有单回合 35%),形态上向 k06 的 56% 靠。

### 第 0 天 margin 是今晚最好的,而且好得不止一点

| 臂 | 第 0 天整局 margin |
|---|---|
| **`bazaar`(bz-all)** | **−35,080** |
| `croftrTU` | −42,220 |
| chisel 的尺子 | −54,849 |
| `haymaker` | −57,347 |
| `tutor2` | −63,625 |
| `prospect` | −64,115 |
| `longcredit` | −65,493 |

**它是今晚唯一明显好过那把尺子的**,而且账本上**支出占缺口的比例掉到 10%**
(最初是 46%)。

### 单种子第三次骗人,这次是反方向

提交阵列**之前**我在预登记里写了:"单种子说钱**降了**(27,765 → 24,681),
所以这条很可能是阴性"。**864 局的真值是 +3,641/+3,824。**
今晚单种子误导过三次:`thrift` 单种子 +33,758(真值 +3,268)、
`bazaar` 单种子 −3,084(真值 +3,824)。**方向都不可信,幅度更不可信。**

### 这条证据到底证明了什么,以及没证明什么

**证明了**:机会成本这个机制是真的,而且**可以在不加动作的前提下拿到**。
+3,824 落在解码层带子(+1.8k…+3.3k)的**上沿**,略微越过 —— 与它仍然是解码层改动一致。

**没证明**:它不能证明"训练时把这条通道打开,策略会去利用它"。
**这才是动作空间假设的真正检验** —— 因为采购不再付掉卖出之后,
市场头塌缩(`P(BUY_SEED|合法)` 中位 0.02%)就失去了它的经济理由。
**这条 CPU 结果的作用是:它让那条 GPU 臂第一次值得申请卡了**,而不是替代它。

**预登记里"中位上升而收款不下降"只验证了一半**:中位确实升了,
而对照那侧的账本我没测(`c230-samp` 的 receipts 未量),所以**收款那半留着,
不当成已验证。**

### bazaar 训练臂的预登记(在结果之前写下)

gen41 `--bazaar`,单变量,4 link,**每个 link 只申请 2 核**(见下)。
作业 20344664-67 → 阵列 20344668 → 读数 20344669。

**它检验的是解码层那条测不了的一半**:解码层版本 +3,824 证明了机会成本机制是真的,
**但证不了"训练时开着这条通道,策略会去利用它"**。而后者才是关键 ——
采购不再付掉卖出之后,**市场头塌缩(`P(BUY_SEED|合法)` 中位 0.02%)就失去了它的经济理由。**

**要打败的基线不是对照,是解码层版本本身。**

| 参照 | 中位 |
|---|---|
| `control230-n9`(同场对照) | 45,671 |
| **解码层 `bz-half`(同一份权重,只改解码)** | **49,495** |
| **`bazaar` 训练臂必须超过的** | **49,495** |

**护栏(写在读数器里)**:**若中位落在 49,495 或以下,说明训练那一半什么都没加,
动作空间这条假设就是被否定的 —— 报告它,不要回头调参。**

**近端预测**:`P(任一 BUye_SEED | 合法)` 的中位必须从 0.02% 抬起;
土地必须离开 2.0;第 18/28 天空地必须离开 18/27。

### 实现上必须记的两条

**一、一个常量驱动两条解码路径。** `actions.BAZAAR` 同时被
`actions._bazaar_tail`(python)与 `engine_t_idx._idx_decode_market`(张量热路径)读取。
**用模块常量而不是环境变量是刻意的**:导出会把 `actions.py` 复制过去,
所以**提交上去的 agent 与训练它的读同一个值**;环境变量会让两者分叉(档案里扫参数时
就发生过)。而且阵列脚本在导出后 `sed` 把导出那份的 `BAZAAR` 也设成 `True` 并回显确认。

**二、逐字节门抓到了一个真 bug,而它正是"训练的游戏与提交的游戏不同"那一类。**
第一版把 bazaar 块放在 **HIRE 爆发**与**清算日复合卖出**之前 —— 那两者都会重写槽位 0..k,
于是在 HIRE 爆发的回合里,**张量路径的附加卖出被覆盖掉,而 python 路径保留了它**;
表现为第 35 步 `farms[1].money` 50 对 150。**改成函数里的最后一个写入者**之后:
480 步 × 16 lane × 2 座位逐字节相同,期间跑过 218 个混合市场回合。
**默认关闭时四道门全过**(`MULTI-PASS` / `PIN-PASS` 2,022 点 / `test_trl` 全过 / `B3-PASS`)。

### 资源形状按实测改了(与今晚其它所有链不同)

`sacct` 显示今晚每个 GPU link **申请 6–8 核、`TotalCPU ≈ 墙钟`,即实际只用 0.99 核**
(采集是单个 Python 线程在发 kernel,张量都在卡上,`OMP_NUM_THREADS` 无处可用)。
一夜下来**预留约 40 核·小时、实际用约 7**,~33 核·小时在共享集群上占着空转,
而 **fairshare 按预留计费**。**所以这条臂每个 link 只要 2 核** ——
既不丢吞吐(6 已过最优点,实测 4 线程最优、8 线程比 1 线程还差),
又是更轻的调度目标,而今晚的真实瓶颈就是排队。

## 2026-08-23 · `bazaar` **不叠加**(第三次确认),而这次有具体机制;它对打包候选也**完全无效**(−6)

零 GPU、同权重、只改解码,九对手 × 48 种子:

| | 中位 | held-out | **p05** | <20k |
|---|---|---|---|---|
| `control230-n9` | 45,671 | 3/7 | 21,761 | 3% |
| `bazaar` 单独(在对照上) | **49,495(+3,824)** | 4/7 | 21,293 | 2% |
| `haymaker` 单独 | **50,786(+5,115)** | 4/7 | 24,585 | 2% |
| **`bz-hay` = 两者合用** | **48,296** | **3/7** | **26,585** | **1%** |

**两条各自 +3,824 与 +5,115 的改动,合起来是 48,296 —— 比 `haymaker` 单独还低 2,490。**
**第三次确认解码层的改动不叠加**(前两次:`WHEAT_BUY_EXACT`+`SEED_BATCH` 是
+0.3 胜率/−398;`WHEAT_BUY_EXACT`+加宽头是各自 +1,760/+2,014 而合起来只剩 +378)。

### 但这次能说清楚为什么,而不只是观察到

**两者作用在同一个预算上,而 `haymaker` 先把它花掉了。**
`bazaar` 的收益**与"有采购的回合数"成正比** —— 它做的是"采购的那一回合顺手把货卖掉"。
而 `haymaker` 的效果恰恰是**把采购减少**:饲料支出从 54,050 掉到 29,836,
买产品的回合随之大幅减少。**采购回合少了,`bazaar` 能修的东西也少了。**
**所以这不是两个正效应互相抵消的巧合,是一个改动吃掉了另一个的作用面。**

### 一个反向的、值得留住的读数:尾部是今晚最好的

| | p05 | <20k |
|---|---|---|
| 对照 | 21,761 | 3% |
| `bazaar` 单独 | 21,293 | 2% |
| `haymaker` 单独 | 24,585 | 2% |
| **`bz-hay` 合用** | **26,585** | **1%** |

**合用把 p05 推到 26,585、`<20k` 压到 1%,两项都是今晚最好。**
所以它是一笔**中位换尾部**的交易(−2,490 中位 / +2,000 p05)。
**若将来要的是"少崩盘"而不是"高中位",这个组合是目前最稳的一个** —— 留档,不是拒绝。

### 对打包候选:完全无效

| | 中位 | p05 |
|---|---|---|
| `hybrid-d12final20`(候选原样) | 90,255 | 51,930 |
| **`bz-cand`(候选 + bazaar)** | **90,249(−6)** | 49,534 |

**−6,噪声都算不上。** 机制也清楚:**在 hybrid 里,前 20 天是磁带
(而磁带本来就会下混合单 —— 未打补丁时已有 33 个混合回合),网只打最后 10 天,
那时棚子正在清算,**几乎没有采购可以配一笔卖出**。所以这条通道在候选身上无处施力。

**这也顺便给"要不要给候选打补丁再提交"一个明确答案:不要,它一分钱都不值。**

## 2026-08-23 · `ladder.py stats` 的「idle tiles 43.5」差点被我读成"天梯层不种地" —— 它是**收割完之后的残局**,不是建设指标

等 GPU 的间隙我回头看 `tools/ladder.py stats`(794 局真实天梯对局的对手摘要),
那里有两行看着像是在推翻今晚所有的空地判据:

| 真实天梯场(对手摘要,终局) | 中位 |
|---|---|
| 象限 | 3.0 |
| 动物 | 13.0 |
| **终局作物** | **3.0** |
| **空地** | **43.5** |
| 卖出:WHEAT 419 / FERTILIZER 234 / MILK 214 / STRAWBERRY 205 | — |

**"终局只剩 3 块作物、43.5 格空地"** 与我整晚用的判据("第 18 天空地 18 对 k06 的 2")方向相反。
**先确认了两件事,才敢下结论:**

**一、`empty` 数的是 `t is None`,而锁住的格子根本不在 `tiles` 里。**
实测:`None` 数 + 各 kind 数 **正好等于已解锁格数**(重置 25、第 18 天与终局 75)。
所以 43.5 是**真的空着的已解锁地**,不是"含锁住的格子"。

**二、一次性作物收割时会把格子清空**(引擎:`farm["tiles"][fy][fx] = None`,已读源码)。
于是同一局 k06 的轨迹是:

| k06(3 象限 = 75 格) | None | PLANT | PASTURE | WEED |
|---|---|---|---|---|
| 第 18 天 | **2** | **59** | 14 | 0 |
| 终局 | **36** | 5 | 14 | 20 |

**第 18 天把地填满(只剩 2 格空),终局却空出 36 格 —— 因为它把作物全收了。**

**判词:终局快照(`crops at end`、`idle tiles`)不能当建设质量的目标,它量的是"到点时还剩什么"。
第 18 天才是对的切面,而在第 18 天 k06 是 2 格空、我们是 18 —— 所以今晚的判据是对的,
天梯摘要并没有推翻它。**

**但这一行数字就摆在 `ladder.py stats` 的输出里、位置显眼、极易误读**(我自己就先读错了一步),
所以记档:**凡是"at end"的量,先问"一次性作物收割会不会清掉它"。**
这与今晚另外几条同源:`sold` 是下单量、`prices` 是收盘价、相对路径一致 ≠ 同一目录、
对照数字一致 ≠ 同一个场。**全都是"看着是那个量,其实不是"。**

**顺带一个真的新读数**:k06 终局留了 **20 格杂草**,而天梯场中位是 6 格。
杂草在 φ 里是 −25/格的机会成本,而**冠军放着 20 格不管** —— 说明终局阶段除草不值得,
这和"最后几天该清算而不是维护"一致。

## 2026-08-23 · **天梯记录本身推翻了我今晚用的目标算法**:2000 已经被跨过两次,但都是**回放别人的计划**;而 RL 线的天梯天花板是 692.2,连第三方参考 agent(1287.2)都打不过

等 GPU 的间隙我读了 `kaggle competitions submissions kaggriculture`(**只读,没有提交**)。
今晚所有的缺口算术都建立在"同板锚点插值 → 104,500 钱"上,而**天梯自己的记录说的是另一件事**。

### 全部相关提交的真实分数

| ref | 日期 | **公开分** | 是什么 |
|---|---|---|---|
| **55484175** | 08-13 | **2302.2** | 别人的顶端计划开环回放,描述里明写 **NOT OUR PLAN** |
| **55489160** | 08-13 | **2035.9** | 同类,另一段录音,也明写 **NOT OUR PLAN** |
| 55442784 | 08-11 | 1363.7 | `closer_cleo` + 终局控制器 |
| **55439740** | 08-11 | **1287.2** | **`closer_cleo`,第三方 MIT 参考 agent,原样提交** |
| 55458466 | 08-12 | 1209.4 | `closer_cleo` 变体 |
| **55688747** | 08-22 | **692.2** | **hybrid-cleo12:12 天录音 + RL 网** |
| 55673426 | 08-21 | 610.1 | RL 线第二发(纯顶端经济饮食) |
| 55676605 | 08-21 | 601.5 | RL 线第三发 |
| 55668491 | 08-21 | 555.4 | RL 线首个过本地验收的(sower-it228) |

### 三条结论,每一条都改变今晚的判断

**一、2000 不是遥不可及的,它已经被跨过两次 —— 但两次都不是 RL,而且都不是我们的策略。**
`55484175`(2302.2)与 `55489160`(2035.9)的描述里都明写 **NOT OUR PLAN**:
它们是用 `tools/tracelib.py` 重建的**别人**的顶端对局,开环回放。
**所以"2000 分"这个目标是可达的,而"用 RL 达到 2000"仍然未达成。**

**二、钱不是决定分数的量,我今晚的目标算术是错的。** 按天梯实测的每次提交均值:

| ref | 天梯均值(我方钱) | 分数 |
|---|---|---|
| 55489160 | **89,168** | 2035.9 |
| 55484175 | **86,467** | **2302.2** |
| 55439740(cleo) | 83,951 | 1287.2 |
| 55458466 | 80,865 | 1209.4 |

**89,168 拿 2035.9,而 86,467 拿 2302.2 —— 钱更多的那个分数更低。**
84–89k 这个窄区间里分数从 1209 铺到 2302。
**所以"要到 2000 需要 104,500 的钱"是错的:实测 86k 就够了,而钱本身只是弱相关。**
决定分数的是**在被匹配到的对手场里赢谁**,而那个场随你上升而变硬。

**三、天梯独立确认了今晚最重要的那条本地判词。**
今晚在同板上测出"网的边际贡献约 −801/天"(纯 cleo 磁带 98,420 > hybrid 90,409)。
**天梯上是同一个方向,而且幅度更大**:

| | 天梯分 |
|---|---|
| **`closer_cleo` 原样(第三方参考)** | **1287.2** |
| **hybrid-cleo12 = cleo 12 天 + 我们的 RL 网** | **692.2** |

**把我们的 RL 网接在 cleo 的开局后面,让它掉了 595 个天梯分。**
本地九对手场和真实天梯**各自独立**地说了同一件事,而这是我今晚唯一拿到跨场确认的判词。

### 于是"用 RL 达到 2000"的真实台阶被量出来了

**不是 45,671 → 104,500 的钱,而是这条阶梯:**

| 台阶 | 天梯分 | 差距 |
|---|---|---|
| RL 线现状(最好:hybrid-cleo12) | **692.2** | — |
| **先要打过的:第三方 `closer_cleo` 原样** | **1287.2** | **+595** |
| 我们自己改过的 cleo 变体 | 1363.7 | +671 |
| 目标 | 2000 | +1,308 |
| 已达到过(回放别人的计划) | 2302.2 | — |

**第一道门不是 2000,是 1287.2 —— 一个我们没写、原样提交的第三方 agent。
在 RL 线打过它之前,谈 2000 都是跳步。**
而今晚测出的所有杠杆(塑形 ≤+5,115、解码 ≤+3,824、课程饱和、探索/信用/模仿 ≤+729)
**都是在 692 这一档里挪动**,没有一条被证明能跨过那 595 分。

## 2026-08-23 · **把尺子校准到天梯**:`hands@20` 的 ρ = **+0.96**,而钱只有 +0.73;卖小麦是**负**相关

上一条判词说本地九对手中位这把尺子把 cleo(1287.2)与 hybrid(692.2)的关系读反了。
既然手上有 **794 局真实天梯对局的摘要**加**18 次提交各自的真实分数**(555–2302),
就可以直接问:**哪些可测量真的预测天梯分?**(Spearman ρ,n=18)

| 特征 | ρ 对天梯分 |
|---|---|
| **`hands@20`(第 20 天每回合帮手数)** | **+0.96** |
| `sold_STRAWBERRY` | +0.88 |
| **`herd@20`** | **+0.84** |
| `herd@15` | +0.82 |
| 终局动物数 | +0.82 |
| (局数 — 混杂项,见下) | +0.81 |
| `sold_MELON` | +0.77 |
| **钱(中位)** | **+0.73** |
| `sold_WOOL` | +0.70 |
| **首次买地的日子** | **−0.61**(越早越好) |
| 胜率 | +0.44 |
| **`sold_WHEAT`** | **−0.27** |
| `hands@10` | +0.04 |

### 四条读数

**一、`hands@20` 是压倒性的第一,而钱只排第六。** ρ=+0.96 对 +0.73。
**而"每回合帮手数"在统一判据里一直只是第三列**,我整晚把它当次要指标读。

**二、`hands@10` 是 +0.04,`hands@20` 是 +0.96 —— 差别不在"早雇",在"到第 20 天还养得住"。**
帮手是**日工**(引擎每天结束解雇全部),所以这量的是**持续负担一支大队伍的能力**,
不是一次性的雇工动作。

**三、卖小麦是负相关(−0.27),而天梯场卖小麦的中位量是最大的(419)。**
两件事同时成立的唯一读法:**高分的那些不是不产小麦,是把小麦喂掉而不是卖掉。**
这与 `haymaker` 那条判词(引擎 FEED 每天每只吃 1 份小麦、k06 买 138 颗小麦种子而我们买 0)
指向同一件事,**而且这次是天梯分在说。**

**四、首次买地越早分越高(−0.61)。** 这给"土地要到 3"补上了时间维度:
不只是终局有几个象限,而是**多早拿到**。

### 必须一起写的边界(否则这条会被误用)

**这 18 个点跨越完全不同的 agent 家族**(第三方 cleo 变体、别人计划的回放、RL 线四发),
所以相关性里混着"属于哪个家族"。**`games` 的 +0.81 就是混杂的证据**:分高的被匹配到更多局。
**所以 `hands@20` 是一把更好的尺子,不是一个已证的杠杆** ——
它可能是 cleo 家族(雇工很深)的**标记**而非**原因**。

**但作为尺子它是明确更好的**:本地九对手中位把 cleo/hybrid 读反了,
而 `hands@20` 把 555–2302 这个区间排得几乎单调。
**而它已经在 `tools/arm_behaviour.py` 的 `crew` 那一列里**,零成本可用。

**立刻可用的一条**:我们的 RL 网本地 `crew` 是 **7.9–8.4**,
而提交上天梯的那些在第 20 天是 **11–12**(794 局的轨迹表)。
**RL 线比天梯场低 3–4 个帮手,而这正好是 ρ=+0.96 的那个量。**

## 2026-08-23 · `hands@20` 不是钱的影子,是**策略把免费的帮手放着不雇** —— k06 每一个检查点都顶着预算上限,我们从第 15 天起就留着 2 个不雇

上一条把 `hands@20`(ρ=+0.96)标为"更好的尺子,但可能只是家族标记"。
**最担心的混杂是"钱 → 帮手 → 都与分数相关"**,因为 `rl/actions.py` 的 HIRE 爆发被
`fib(hires_today + j) <= 0.05 * money` 门住 —— 穷农场雇不起大队伍。**这条能直接测。**

斐波那契工资表:第 4 个帮手 5、第 8 个 34、第 10 个 89、**第 11 个 144、第 12 个 233**。
按 `0.05 * money` 折算,要雇到第 11 个需要 money ≥ **2,880**、第 12 个需要 ≥ **4,660**。

**实测(对 k06,种子 10000):**

| 第 20 天 | 帮手 | 钱 | 预算还允许 | 判定 |
|---|---|---|---|---|
| `nn-d0-chisel` | 10 | 15,191 | **+2** | **策略没雇** |
| `haymaker` | 10 | 21,081 | **+2** | **策略没雇** |
| **k06** | **12** | 36,987 | **0** | **钱卡住** |

第 15 天同样:我们 10 个、预算允许 12;k06 12 个、顶满。
**只有第 10 天双方都被钱卡住**(那时钱只有几百到两千)。

### 判词:混杂不成立,这是一个真的杠杆

**k06 的雇工规则实际上就是"永远雇到预算上限"** —— 每个检查点都恰好卡在钱上,
一个多余的帮手都不留。**而我们的网从第 15 天起就有 2 个雇得起却不雇的帮手。**
第 20 天时钱是 15–21k,而第 11、12 个帮手只要 144 和 233 —— **边际帮手便宜到可以忽略**。

**所以 `hands@20` 的 ρ=+0.96 对我们不是"钱的影子":我们把免费的东西放在桌上没拿。**

### 而这又是市场头塌缩的同一个症状

`HIRE` 是市场动作**第 21 号 —— 同一个塌掉的 31 路头**。
`head_health.py` 早先测到 `HIRE` 中位 **0.00%**、均值 5.47–8.35%:**尖峰但没顶满**。
所以"不雇满"不是一条独立的病,**是"每回合只能出一种单"的又一个代价**:
雇一次工就要付掉那一回合的卖出。

### 顺带给 `bzt`(已在排队)补一条预登记

`bazaar` 让采购不再付掉卖出,**而 `HIRE` 正是 `_ACQ` 里的一员**。
**所以若机制为真,`bzt` 的 `crew` 应该从 10 往 12 抬** ——
而那正好是 ρ=+0.96 的那个量。**这条写在结果之前**:
`bzt` 的 `arm_behaviour` 若 `crew` 仍是 10 上下,说明通道打开也没让它去雇满,
**那么"不雇满"就还有第三个原因,不是机会成本。**

## 2026-08-23 · `foreman` **重度阴性(−10,299 / −12,828)**:`hands@20` 是**标记不是杠杆**,而帮手规模是农场规模的**结果**,不是原因

按 k06 的实际规则(每回合雇到 `0.05 * money` 的预算上限)做成解码层补丁,零 GPU。
**机制先验证过**:`hands@15` 与 `hands@20` 都从 10 抬到 **12**(与 k06 一致),平均队伍 7.66 → 10.01。
然后上九对手 × 48 种子:

| | 中位 | 对基线 | held-out | p05 | <20k |
|---|---|---|---|---|---|
| `c230-samp`(未打补丁) | 45,671 | — | 3/7 | 21,761 | 3% |
| **`fm-c230`** | **35,372** | **−10,299** | **2/7** | **13,856** | **17%** |
| `haymaker`(未打补丁) | 50,786 | — | 4/7 | 24,585 | 2% |
| **`fm-hay`** | **37,958** | **−12,828** | **1/7** | **9,761** | **15%** |

**这是今晚最大的单条负效应**,而且尾部崩得很彻底(`<20k` 从 2–3% 涨到 15–17%)。

### 预登记的分叉走了阴性那一支,而这是个干净的答案

预登记原文:"**若中位不动,`hands@20` 就是家族标记而不是杠杆**"。
**结果比"不动"更强:把队伍顶到 k06 的 12 个,反而砸掉一万多。**
**所以 ρ=+0.96 是标记 —— 尺子可以用来排序,但不能当靶子追。**

### 机制:帮手是日工,而我们的农场根本用不上第 11、12 个

帮手每天被引擎全部解雇,工资按**当天第 n 次雇**计:
每天雇满 12 个 = `fib(0..11)` 之和 = **376/天**,25 天约 **9,400** ——
**与实测的 −10,299 几乎完全对上。**

而它们干不了活:早先测过我们的帮手**只有 11.5% 的回合在真干活、49% 在 PASS**,
农场只有 25 块作物在 50 格地上。**k06 能养 12 个,是因为它有 59 块作物在 75 格地上要照料。**
**所以因果方向是反的:队伍大是农场大的结果,不是原因。**
顶着预算雇满,只是把 9,400 块钱换成一群站着 PASS 的手。

**这正是用户判据清单里的准则 (i)**——"**有余量的劳力下贪心最近近优,调度类改动别再试**"。
我们**本来就有劳力余量**,所以加劳力是纯成本。**这条准则今晚第一次被正面量化了。**

### 处置:退掉一个判据,和一条还挂在清单上的臂

1. **"每回合帮手数是否从 7.9 抬起"这条判据应当退役。** 它把一个**结果**当成了目标;
   实测把它抬到 12 反而 −10,299。**该看的仍是它,但作为"农场是否变大了"的读数,
   不是要去优化的量。**
2. **`hirer` 臂(gen30,`--hand-value 250`,判据正是"帮手数是否从 7.9 抬起")的目标是错的。**
   φ 里把帮手从 40 提到 250 会让网去雇更多手 —— 而这条判词说那个方向是亏的。
   **建议不要再排它;若已有结果,应按"它是否让农场变大"重读,而不是按帮手数。**
3. **尺子照用**:`hands@20` 与天梯分 ρ=+0.96 仍然成立,`arm_behaviour.py` 的 `crew` 列
   仍是判断"这条臂有没有把农场做大"的最灵敏一列 —— **只是不能反过来推。**

## 2026-08-23 · 那 595 个天梯分,在校准过的轴上**全部落在"采购"**:畜群 6 对 13、首块地第 11 天对第 7 天、草莓 98 对 270

第一道门是 `closer_cleo` 原样的 **1287.2**,而 RL 线是 **692.2**。既然已经把尺子校准到天梯
(`hands@20` ρ=+0.96、草莓卖 +0.88、`herd@20` +0.84、首块地 −0.61、小麦卖 −0.27),
就直接在那几个轴上量这 595 分落在哪。对 `w49`、3 种子:

| agent | `hands@20` | **`herd@20`** | **首块地** | **草莓卖** | 小麦卖 | 期末钱 |
|---|---|---|---|---|---|---|
| **`closer_cleo`(1287.2)** | 11 | **13** | **第 7 天** | **270** | 233 | **98,420** |
| `k06`(冠军磁带) | 12 | 14 | 第 6 天 | 249 | 1,066 | 54,559 |
| **`haymaker`(最好的 RL)** | 10 | **6** | **第 11 天** | **98** | 647 | 31,501 |
| `hybrid-cleo12`(692.2) | 10 | 9 | 第 7 天 | 108 | 1,070 | 69,123 |

**除了那个已经被证明是标记的 `hands@20`,其余三条校准轴我们全错,而且每条都错在被预测的方向上:**

| 轴 | ρ | `closer_cleo` | 我们 | 差 |
|---|---|---|---|---|
| **`herd@20`** | **+0.84** | 13 | **6** | **2.2 倍** |
| **首块地的日子** | **−0.61** | 第 7 天 | **第 11 天** | **晚 4 天** |
| **草莓卖出** | **+0.88** | 270 | **98** | **2.8 倍** |

**而这三样都是"买东西":买牲畜、买地、买草莓种子 —— 全部走那个塌掉的市场头。**
`head_health.py` 早先量到:`BUY_ANIMAL` 均值 0.31–0.92%、`BUY_LAND` 0.00–1.52%、
`BUY_SEED` 4–6%。**三条校准轴对应三个几乎不被采样的动作。**

### 判词:595 分可以归约成一句话

**市场头不采购,而它不采购的那三样,恰好就是天梯分最相关的那三条轴。**

这把今晚所有分散的结论收成一条:
- `haymaker` 的奖励项从"少养牲畜"那条通路流走 → **畜群那一轴**;
- `prospect` 的 ε 探索付不起市场回合 → **采购动作被采样不到**;
- `tutor2` 的开环 CE 把 `BUY_LAND` 从 1.44% 压到 0.08% → **首块地那一轴**;
- `bazaar` 让采购不再付掉卖出,是**唯一在这条轴上拿到正号的**(解码层 +3,824)。

### 一条必须写下的反例,否则这条判词会被过度推广

**`k06` 卖了 1,066 份小麦,比我们的 647 还多,而它是天梯冠军磁带。**
所以"小麦卖得多不好"(ρ=−0.27)这一条**被冠军自己反驳**,不能当准则用 ——
ρ 只有 −0.27,本来就是这五条里最弱的一条。**畜群(+0.84)、草莓(+0.88)、首块地(−0.61)
这三条才是有支撑的,而它们的方向被 `closer_cleo` 与 `k06` 同时确认。**

### 对 `bzt`(排队中)的含义

`bazaar` 攻的正是"采购要付掉卖出"这个机会成本,而 `BUY_ANIMAL`/`BUY_LAND`/`BUY_SEED`
都在它的 `_ACQ` 集合里。**所以 `bzt` 的读数应该按这三条轴看,而不是只看中位**:
`herd@20` 是否离开 6、首块地是否早于第 11 天、草莓卖出是否离开 98。
**这三条比中位更接近天梯,而且是我今晚才有资格这样说的 —— 因为尺子是今天才校准的。**

## 2026-08-23 · `homestead` 也阴性(−5,844),三条采购轴**逐条强推全亏**;而草莓那一轴我读错了杠杆 —— 它是 ongoing 作物,靠**反复收割**不靠多买种子

### 一、`homestead`(强推买地)阴性

`first_land` ρ=−0.61 且土地是三条校准轴里**唯一没有日常开销**的
(象限一次性 1000/2000/4000;动物每天吃 1 份小麦、帮手每天按 fib 重雇)。
所以它是最干净的一条。九对手 × 48 种子,对 `haymaker` 未打补丁的 50,786:

| | 中位 | 对基线 | held-out | p05 | <20k |
|---|---|---|---|---|---|
| `haymaker` | 50,786 | — | 4/7 | 24,585 | 2% |
| **`hs-m5`** | **44,942** | **−5,844** | 4/7 | 20,052 | 5% |

**而行为那一行说清了为什么:**

| | 土地 | 种子 | **第 18/28 天空地** | 作物 |
|---|---|---|---|---|
| `haymaker` | 2.0 | 47 | **18 / 19** | 24 |
| **`hs-m5`** | **3.7** | 50 | **56 / 60** | 27 |

**它把地买了(3.7 象限,超过天梯的 3),却填不上:种子还是 50,空地从 18/19 涨到 56/60。**

**边界(先测过才敢说)**:首块地**压不到** cleo 的第 7 天 —— margin 2/3 会在第 0 天买,
期末钱从 44k 崩到 6.5k;margin 5 的首购仍是第 11 天。
**我们第 7 天根本没钱,cleo 有,因为它赚得快。所以"首块地的日子"本身也大半是结果。**

### 二、三条采购轴逐条强推,全部亏钱

| 强推的轴 | 补丁 | 中位效应 | 机制 |
|---|---|---|---|
| 帮手 10→12 | `foreman` | **−10,299** | 日工工资 376/天 × 25 天 ≈ 9,400,而帮手 49% 在 PASS |
| 土地 2.0→3.7 | `homestead` | **−5,844** | 地买了填不上,空地 18→56 |
| 畜群(奖励侧) | `haymaker` | +5,115 但通道错 | 靠**少养**而非种饲料满足新项 |

**统一的原因:每一样采购只有在农场用得上时才值钱,而卡住的是同一个上游量 ——
种子。45–50 颗种子只能填约 45 格地,所以第三个象限是空的、第 11–12 个帮手无事可做、
第 7 头之后的牲畜喂不起。三条轴都是它的下游,所以逐条强推必然亏。**

### 三、但草莓那一轴我读错了杠杆,而这条更正很重要

我本来要做 `sower2`(强推买草莓种子,因为草莓卖出 ρ=+0.88、我们 98 对 cleo 270)。
**先读了作物表,发现方向错了:**

| 作物 | 种子价 | max_yield | **ongoing** | 首次产出 | 间隔 |
|---|---|---|---|---|---|
| WHEAT | 10 | 6 | False | 第 2 天 | — |
| **STRAWBERRY** | **100** | 4 | **True** | **第 10 天** | **2 天** |
| MELON | 80 | 6 | False | 第 10 天 | — |

**草莓是 ongoing 作物:第 10 天起每 2 天产一次。** 所以一块第 5 天种下的草莓地
到第 29 天能收约 **10 次**;`k06` 只买 34 颗草莓种子却卖出 249,**全部由反复收割解释,
不是靠多买种子。**

**所以"草莓卖 270"这一轴的杠杆是"早种 + 一直收",不是"多买种子"** ——
它落在**帮手头**(HARVEST/WATER)加早期播种,而不是市场头。
而这与早先测到的"我们的帮手只有 11.5% 的回合真干活、基线里 HARVEST 一次都没有"对上,
也解释了 `crew`(把 PASS 的手改派 AUTO,HARVEST 从 0 升到 118)为什么是**唯一
中位涨了而尾部没崩**的解码改动(+1,803)。

**处置:`sower2` 撤掉,不跑九对手阵列。** 理由不是它的单种子读数差
(单种子今天已经在两个方向上骗过我三次),**而是机制上它是错的杠杆**:
对 ongoing 作物多买种子只是把钱花在没人收的地里。
**按准则 (d) 我不会声称任何"测过"的结论 —— 这是在花掉那 9 个任务之前撤回一条设计。**

## 2026-08-23 · 草莓那一轴是**两个头的乘积**,不是独立杠杆 —— 这解释了今晚三条强推为什么必须失败

`sower2` 撤掉之后,先把 98 对 270 拆开再动手(前三条强推都是压在**结果**上才亏的)。
对 `w49`、种子 10000:

| agent | 草莓地块 | **首次种下** | 草莓卖出 | **每块地卖出** | **HARVEST 手数** |
|---|---|---|---|---|---|
| `closer_cleo`(1287.2) | 41 | 第 4 天 | 270 | **6.6** | **342** |
| `k06` | 34 | 第 5 天 | 249 | **7.3** | **388** |
| **`haymaker`(最好 RL)** | **20** | **第 3 天** | **81** | **4.0** | **112** |

**拆解:地块 20 → 41 是 2.05 倍,每块地卖出 4.0 → 6.6 是 1.65 倍,
乘积 3.39 倍,而实测卖出比正是 3.33 倍 —— 对得上。**

**所以差距是两个因子各占一半,不是其中之一。**

**而"早种"不是问题**:我们第一块草莓种在**第 3 天**,比 cleo 的第 4 天、k06 的第 5 天**还早**。
我们早种了,然后既不扩张也不收割。

**`HARVEST` 手数 112 对 342/388,是 3.1–3.5 倍** —— 这就是"每块地卖出"那一半,
与早先测到的"帮手只有 11.5% 的回合真干活(k06 是 38.8%)"是同一件事。

### 判词:ρ=+0.88 的草莓轴是两个已知病灶的**乘积读数**

**草莓卖出 = 地块数(市场头:买种子)× 每块收割次数(帮手头:HARVEST)。**
两个因子分别落在今晚反复测到的**那两个头**上:塌缩的市场头、利用率 11.5% 的帮手头。

**这立刻解释了三条强推为什么必须失败 —— 每条都只动了一个因子,另一个原地不动:**

| 强推 | 动了哪个因子 | 另一个因子 | 结果 |
|---|---|---|---|
| `homestead` 加土地 | 都没动(土地不是因子) | 种子没变 → 地块没增 | −5,844,空地 18→56 |
| `foreman` 加帮手 | 帮手**数量** | 但没活可干 → 49% PASS | −10,299 |
| `sower2` 加种子(已撤) | 地块数 | 收割次数没变 | 机制上无效,未跑 |

**所以草莓轴不是一条可以单独推的杠杆,它是一个读数。**
能移动它的干预必须**同时**修两个头 —— 而今晚三次组合测试(`WHEAT_BUY_EXACT`+`SEED_BATCH`、
`WHEAT_BUY_EXACT`+加宽头、`bazaar`+`haymaker`)**全部证明解码层的改动不叠加**,
所以"同时修两个"在解码层大概做不到,**只能靠训练**。

**这正是 `bzt` 的形状为什么对**:它不是强推采购,而是**把采购的机会成本去掉,
让策略自己在训练里去用** —— 对应地块那个因子。
**而帮手那个因子的对应物是 `crew`(把 PASS 的手改派 AUTO,HARVEST 从 0 升到 118,
+1,803 且尾部没崩)—— 今晚唯一一条"中位涨了尾部没坏"的解码改动。**
**两者的训练版都还没测过,而这条判词说它们必须一起测,不能各自单独判。**

## 2026-08-23 · 帮手侧的病灶定位到**唯一一种**干预:掩掉 IDLE **没用**(PASS 反而上升),所以必须是"家族没目标时回落 AUTO"的溢出

### 一、帮手头实际在选什么(真实状态,1,680 个手-状态,`haymaker`)

| 任务 | 占比 |
|---|---|
| **IDLE** | **34.8%** |
| AUTO | 29.9% |
| WATER | 10.5% |
| COLLECT_FERTILIZER | 7.7% |
| CARE / FERTILIZE / PLANT | 4.8 / 4.8 / 4.6% |
| DIG | 1.5% |
| **HARVEST** | **1.4%** |

**三分之一的手-槽位是被主动选成 IDLE 的** —— 而 `IDLE` 无条件解码成 `["PASS"]`,
帮手是**日工**、工资照付。`trl_policy.py` 的 `MultiActorNet` 本来就把帮手头的 bias
起始设在 AUTO 上(`auto_bias=2.5`),注释写的正是
"**AUTO 是个能干的默认值,而 IDLE 是罢工**" —— **而训练出来的网还是漂到了 IDLE。**
同时 **HARVEST 只占 1.4%**,而"每块地收割次数"正是草莓缺口的一半(4.0 对 cleo 的 6.6)。

### 二、于是先试最便宜的:把 IDLE 掩掉。**没用。**

`tools/build_nostrike.py`(一行:清掉手任务掩码的 IDLE 列,并保证不会掩掉某只手唯一的合法任务):

| | 干活 | **PASS** | HARVEST | 草莓卖 |
|---|---|---|---|---|
| `haymaker` | 819(14.6%) | **1,940** | 101 | 81 |
| **`ns-hay`** | 847(14.7%) | **2,037** | 111 | 88 |
| cleo 参照 | 38.8% | — | 342 | 270 |

**掩掉 IDLE 之后 PASS 反而上升了。** 机制清楚:**那些本来选 IDLE 的槽位,
转而选了"一个没有目标的家族"—— 而那同样解码成 PASS。**
**所以 49% 的 PASS 不是 IDLE 造成的:IDLE 只是通往 PASS 的若干条路之一,
堵掉它不会造出活来。**

**处置:`nostrike` 撤回,不跑九对手阵列**(理由是机制,不是单种子的钱 ——
单种子今天已在两个方向骗过我三次;而"PASS 上升、干活不变"这两个**行为计数**才是判据)。
**按准则 (d),这里不声称任何"测过"的结论。**

### 三、这条阴性把帮手侧的可行干预收缩到唯一一种

**只有"家族没目标时回落到 AUTO"能保证产出非 PASS 的动作** ——
而这正是 `crew`(导出层的双次解码)做的事,也是它的实测:
**PASS 2,763 → 2,011、干活 +43%、HARVEST 0 → 118,中位 +1,803 且尾部没坏
(今晚唯一一条"中位涨了尾部没坏"的解码改动)。**

**训练版的落点也已经找到了**:`engine_t_idx.py` 第 566–569 行,
一个任务手在某格的键是"该家族在此格可用就 `family*100`,否则 `BIG`" ——
溢出就是把那个 `BIG` 换成 AUTO 自己的 `mfk`。
**但必须是"每只手"的开关,不能是"每格"的**:键是 `dist*1024 + family*100 + tile`、
距离主导,所以逐格回落会让更近的 AUTO 杂活压过本家族更远的目标,
**那等于把任务头从"指令"降成"建议"**,语义就变了。
正确形式是先算 famk-only 的每手最小值,若 ≥ `BIG` 再整只手切到 `mfk`;
**而 python 侧 `_hands_actions_multi` 必须逐字同构,由 `test_multi` 的 M2 门把关。**

**这条已经写下,但没有实现** —— 它是一次需要过逐字节门的引擎改动,
而 `bzt` 还没起跑(15:50 预估),所以它的检验窗口在更后面。
**按上一条判词,它必须与 `bazaar` 一起测(`bzt` 作对照),不能各自单判。**

### bothheads 的预登记(在结果之前写下):`bazaar` + `hand-spill`,而**对照是 `bzt` 不是基线**

gen41 `--bazaar --hand-spill`,4 link × 2 核,挂在 `bzt` 末链之后
(20348240-43 → 阵列 20348244 → 读数 20348245),**所以 bazaar 单独那一臂先落地当对照。**

**为什么不是单变量臂**:草莓那一轴(ρ=+0.88)被拆开后是**两个因子的乘积** ——
地块 2.05 倍 × 每块收割 1.65 倍 = 3.38 倍,实测卖出比 3.33 倍。
两个因子分别落在市场头(买种子)与帮手头(HARVEST)。
**今晚三条只动一个因子的强推全部失败**(`foreman` −10,299、`homestead` −5,844、
`sower2`/`nostrike` 机制上撤回),而**解码层的改动三次证明不叠加**,
所以"同时修两个头"只能靠训练。**`bzt` 是它的单变量对照,增量正好是 `hand-spill` 一个。**

**近端读数按那两个因子分开看:**

| 因子 | 落在哪个头 | 我们 | `closer_cleo`(1287.2) |
|---|---|---|---|
| 地块数 | 市场头(买种子) | 草莓地 20 / 种子 47 | 41 / — |
| 每块收割次数 | 帮手头(HARVEST) | HARVEST 112 / 干活 14.6% | 342 / 38.8% |

**护栏(今天刚学到的)**:**`crew` 上升本身不是好消息** ——
`foreman` 把 crew 顶到 12 是 −10,299。**crew 只能与"农场是否变大"一起判**
(作物数、草莓卖出),否则会把结果当成因。

**导出侧已处理**:阵列在导出后把导出那份 `actions.py` 的 `BAZAAR` 与 `HAND_SPILL`
都 `sed` 成 `True` 并回显确认 —— **提交上去的 agent 必须与训练它的读同一组值。**

## 2026-08-23 · 共卡的显存账算出来了:**一张 80GB H100 能放 3 个进程,吞吐 ×3 而且不动 B、不破坏可比性**

之前把"共卡跑 2–3 个进程"列为待定,因为需要实测显存。**其实不用实测,代码里能算出来**,
而 `train.py` 的注释本身就佐证了这个量级("at B=1024 the full batch is ~29 GB of float32 obs")。

`frames_per_batch = B(1024) × ep_len(719) = 736,256`,`obs_dim = 4867`。
`keep` 列表只保留损失要读的键(注释说这一步"把 replay 副本减半"):

| 键 | 每帧元素 | 字节/元素 | GB |
|---|---|---|---|
| **observation** | **4,867** | 4 | **14.33** |
| hand_mask | 120 | 1 | 0.09 |
| action | 14 | 8 | 0.08 |
| farmer/market_mask | 54 | 1 | 0.04 |
| 其余(logp/adv/value) | 3 | 4 | 0.01 |
| **合计(一份)** | | | **14.55** |

**PPO 的 minibatch 洗牌要再留一份,峰值约 22–29 GB。所以 80GB 能放 3 个进程
(3 × 26 ≈ 78GB),网络与优化器只有百 MB,可忽略。**

**而算力一定够**:今天测出采集是**发射延迟受限**(54.9 ms/批量 step、
CPU 4 线程都能跑到 22k sps 而 GPU 只有 18k),**SM 大部分时间是空的** ——
三个进程交错发 kernel 应该接近线性叠加。CPU 侧每个进程只要 1 核(实测 0.99),
3 × 2 核 = 6 核/卡,远在 Nibi 每卡 14 核的配额内。

**实现形式**:Slurm 一般不允许三个作业共用一张卡,所以走"一个作业、一张卡、6 核,
脚本里用 `&` 起三个 `rl/train.py` 再 `wait`"。

**这条的价值在于它不用付那笔账**:提高 B(1024→4096)约 8× 但会改 PPO 的有效批量,
**今晚整张判词表(塑形 ≤+5,115、解码 +1.8k…+3.8k、信用侧 +689/+729、模仿 +133)
全部以 B=1024 为基线,换 B 就要重跑对照**。
**共卡是 ×3 且基线不变 —— 每个进程仍是 B=1024 的独立臂。**

### 顺带一个下一代才能动的观察

**`obs_dim = 4867`**,而棋盘是 10×10 × 约 12 个通道 ≈ 1,200。**观测比棋盘大四倍。**
它同时是显存的主项(14.33 of 14.55 GB)**和** CPU 侧策略前向的主项
(B=512、4 线程下 16.59 ms/step)。**把它砍小会同时放大显存与吞吐两边**,
但改观测维度会让所有现有检查点失效,**所以那是下一代的事,不是一个旋钮。**

## 2026-08-23 · 读了第一道门的源码:**`closer_cleo`(1287.2)的农场行为根本不是算法,是 104 个队共享的 712 回合录音**

整晚我在量 `closer_cleo` 的产出(畜群 13、首块地第 7 天、草莓 41 块地卖 270、HARVEST 342),
**却一次没读它的代码。读了之后,"第一道门"的性质变了。**

它自己的文档写得非常明确:

> "**This agent does not use an original field plan. It executes the shared public
> meta line**:`scripts/cross_team_identity.py` over 530 downloaded replays finds
> **identical 712-turn farmer/hand sequences played by large groups of unrelated
> teams — one group of 29, another of 15, another of 8, with 104 distinct teams**
> appearing in at least one shared plan."
>
> "What is the author's own … is **the market layer**:which product takes the
> earliest slot in the order queue, when to hold, and when to liquidate."

代码结构佐证:`_TRACE` 是 base85+zlib 压的 **712 回合 farmer/hand 序列**;
上面套一层手写的 SELL 重排(带 `_FRONT_RUN_HORIZON` 前瞻)、清算分支、
以及一个把雇工补到 **8** 的 HIRE 顶栏(`max(0, 8 - already)`)。

### 这把"用 RL 达到 2000"的题面改了

**天梯 1287–2302 那一带,坐的全是"开环回放一份共享计划"的 agent:**

| 分数 | 农场行为的来源 |
|---|---|
| 2302.2 / 2035.9 | 别人的顶端对局录音,明写 NOT OUR PLAN |
| **1287.2(第一道门)** | **104 个队共享的 712 回合 meta 录音 + 手写市场层** |
| 555–692(RL 线) | **学出来的策略** |

**所以我们的 RL 线不是在跟"更好的算法"比,是在跟一份 104 个队收敛到的记忆序列比。**
而今晚测出"网接上 cleo 的开局后每天贡献 −801、天梯上掉 595 分",
说明**我们的策略在接手一份专家序列之后会把它弄坏。**

### 由此,唯一被这条事实指向的方法是模仿 —— 而我今天把它砍掉的理由是预算,不是判断

`tutor2`(gen38,`--kickstart tape:closer_cleo --ks-coef 0.05`,从成熟主干起)
拿到 **+133**,并且带着逆频率偏置(`BUY_LAND` 均值 1.44% → 0.08%)。
**但它的系数被档案的"成熟主干上界 ≤0.05"锁住了** —— 那条上界是为了不砸坏一个已有的 42k 策略,
**而如果目标本来就是"复制一份录音",从随机初始化起、用高系数、跑够 link 数才是正确顺序**
(AlphaStar / VPT 都是这个顺序)。**我今天取消那条(`tutor`/`tutorctl`)的理由是
"2 个 link 从随机初始化说明不了任何事",那是预算判断,不是方法判断 —— 现在方法这一侧
有了新的支撑:模仿的对象不是一个近似算法,是一份确定的 712 回合序列,
而它就在我们仓库里(`closer_cleo._TRACE`)。**

**代价要写清楚**:从随机初始化训到可比 chisel 的 324 迭代需要 **8–10 个 link/臂**,
两臂(有老师 / 无老师对照)就是 16–20 个 link。**今晚的 GPU 供给是每 link 约 40 分钟实效
(25 分钟训练 + 15 分钟排队中位),所以那是 11–13 小时。**
**这是一笔要用户点头的预算,不是我该自己花掉的。**

### 一个顺带的细节,与今天的 `foreman` 阴性对上

cleo 手写层的 HIRE 顶栏是补到 **8**,而不是 12。而 `foreman` 把我们的网顶到 12 是 **−10,299**。
**第一道门自己都不雇满** —— 它测出来的 `hands@20 = 11` 里,大部分来自录音本身的 HIRE 动作,
而不是那个顶栏。**这是"帮手数是标记不是杠杆"的又一个独立佐证。**

## 2026-08-23 · 模仿这条线到此为止,理由是**数据**而不是方法:cleo 的整条磁带里 `BUY_LAND` 只有 **2** 次

读了第一道门是"104 个队共享的 712 回合录音"之后,模仿看起来是唯一被指向的方法。
于是我先想"`tutor2` 的 `ks-coef 0.05` 太胆小了"—— 依据是它的护栏没触发
(money 跨 link 43,041 → 44,240 → 45,009 在涨、`pg` 稳在 −0.0004、熵 14 → 13),
**打算提到 0.3 再跑。这个推理是错的,而且在花 GPU 之前就被自己的数据否掉了。**

### 磁带的标签分布(实测)

| 市场单类型 | 在 712 回合里出现 |
|---|---|
| HIRE | 284 |
| SELL | 231 |
| BUY_PRODUCT | 163 |
| BUY_SEED | 62 |
| BUY_ANIMAL | 10 |
| **BUY_LAND** | **2** |

**`BUY_LAND` 占全部市场标签的 0.27%,与 SELL 的比是 1 : 115。**
交叉熵把概率推向**被标注**的动作,所以 `BUY_LAND` 必然被挤下去 ——
`tutor2` 实测正是 **1.44% → 0.08%**。
**提高系数只会挤得更狠,所以"0.05 太胆小"是反的。**

### 而逆频率加权也救不了它 —— 这是数据量的问题

自然的修法是按逆频率给每个类加权(让 `BUY_LAND` 的少数标签算得更重)。
**但整条磁带里只有 2 个 `BUY_LAND` 样本。** 任何加权方案都无法从 2 个例子里教出
"什么时候该买地":115 倍的权重意味着 2 个样本驱动一个很大的梯度,方差爆炸;
截断到 20 倍则等效样本只有 40,对 SELL 的 231 仍然不成比例。
**这不是方法或权重的问题,是数据里根本没有那个信息。**

**判词:开环磁带的模仿能传高频的操作习惯,结构上传不了低频的资产决策 ——
而"低频却门控一切"正好是我们缺的那三条轴(买地、买牲畜、买种子)。**
这与今天早先那条(逆频率偏置)是同一件事,**但现在有了数字:2 次。**

**能不能靠多条磁带凑?** 不能靠现有的:`arena.sqlite` 里 794 局真实天梯对局
**只存了摘要**(~3 KB:`sold`/`bought`/`hire_orders`/`first_land_day`/按日的钱与畜群),
**原始 replay(19.3 MB 一局)是刻意删掉的**,所以没有逐步动作序列。
仓库里 `agents/wrapped/`、`agents/champ/` 的重建磁带每条也只有 2–3 次买地,
凑十条约 20 个样本 —— 仍然远不够。

### 所以剩下的赌注回到已经排队的那两条

**低频门控动作只能靠 RL 自己探索出来,而那被市场头塌缩堵着
(`P(BUY_LAND|合法)` 均值 0.00–1.52%,而它在 66–71% 的回合上是合法的 ——
"不买"而不是"买不到")。`bazaar` 去掉采购的机会成本,是唯一在这条轴上拿到正号的
(解码层 +3,824);`hand-spill` 管另一半(每块地的收割次数)。
两者的训练版 `bzt` 与 `bothheads` 已在队列里,而这条判词说它们就是正确的剩余赌注 ——
不是因为没有别的想法,而是因为模仿那条路的数据上限刚刚被量出来了。**

## 2026-08-23 · **更正我自己的归功**:"2000 是回放别人的计划跨过的"这条,`GAP-2000.md` §1 早就写了;我今天当成发现讲了

回头读 `GAP-2000.md` 的开头(写于 08-22),它第一节的表里已经明明白白列着:

| 提交 | 天梯 | 是什么 |
|---|---|---|
| topline(55489160) | 2035.9 | **第三方天梯计划的开环复现,不是策略** |
| kawashigi-k06 | 2302.2 | 同上 |

**所以今天我读 `kaggle competitions submissions` 之后当作新发现讲的那条("2000 已被跨过两次,
但都不是 RL、也不是我们的策略"),文件里早就有了。归功更正在此。**

**而且 §1 的换算比我今天推的那套更好:**

> | | 我方收入中位 | 对手收入中位 | **赢的是挣多少的对手** |
> |---|---|---|---|
> | hybrid-cleo12(705.9) | 66,662 | 67,860 | **50,927** |
> | topline(2035.9) | 84,264 | 76,196 | **74,720** |
>
> "最有用的一栏是最后一栏……跨过 2000 不是'多赢几局',
> 是把**能赢的对手收入线从 51k 抬到 75k**。"

**这条比我今天算的 ρ 表更接近因果**:ρ 表是"哪些量与分数相关"(而且混着 agent 家族),
而"能赢的对手收入线"直接说的是**天梯的匹配机制在衡量什么**。
**我今晚一直用的"104,500 的钱"这个靶子,恰恰是 §1 第一句就警告过的
"不要用本地花名册的尺子"。**

### 今天真正新增的是这四条(其余是重复劳动)

1. **`closer_cleo` 原样提交 = 1287.2**,而这是**第一道门**的概念 ——
   §1 的表里没有这一行,它列的是 2035.9/2302.2 和我们自己的 555–705。
   **"RL 线要先打过一个我们没写的第三方 agent,差 595 分"是新的。**
2. **把尺子校准到天梯的 ρ 表**(18 次提交 × 真实分),以及
3. **标记 vs 杠杆的实验分离**:`foreman` −10,299、`homestead` −5,844、
   `nostrike`/`sower2` 按机制撤回 —— 证明那三条采购轴都是**结果**。
4. **模仿路线的数据上限**:cleo 磁带里 `BUY_LAND` 只有 **2** 次。

**另外一个小的时间序列读数**:§1 记 hybrid-cleo12 是 **705.9(12 局)**,
今天的列表读到 **692.2** —— **同一份文件,局数变多后分数下降了 13.7 分**,
与规则 7 一致(赢着的时候那个数是地板,还在动)。

### 处置:把验收判据换成"能赢的对手收入线"

**从现在起,任何臂的天梯预期都应该按 §1 那一栏读,而不是按本地中位。**
本地九对手中位已经被证明会把 cleo(1287.2)与 hybrid(692.2)的关系读反,
而"我们能赢的对手挣多少"是天梯原生的量。
**`bzt` 与 `bothheads` 落地后,除了九对手中位,还应该问:
它们让"能赢的对手收入线"从 51k 动了没有** —— 这需要提交才能测,所以它是
**提交后的读数**,不是本地读数;**本地能做的是继续用那三条校准轴
(畜群、首块地、草莓地块×收割次数)当代理。**

## 2026-08-23 · 把 8 个串行 link 换成 4 个**共卡** link:同样的科学,四分之一的排队次数

`bzt` 12:56 提交,**等了 2 小时 25 分钟没起跑**(集群 GPU 全部 8/8)。
问题不在这两条臂,在**形状**:12 个独立预留、8 次串行排队,而 **fairshare 按预留计费**,
所以排队的拖累会自乘。**撤掉重排成共卡。**

**一张卡、两个训练进程**(`bzt` = `--bazaar`,`bothheads` = `--bazaar --hand-spill`)
各推进一个 link,`&` 起、`wait` 收。

**为什么是 2 个而不是 3 个**:保留的批是 **14.55 GB**
(`frames 736,256 × obs_dim 4867 × 4B` 就占 14.33),PPO 洗 minibatch 峰值约 **22–29 GB**。
**两个 = 44–58 GB,在 80 GB 上宽裕;三个 = 66–87 GB,太紧。**

**为什么算力一定够**:采集是**发射延迟受限**(54.9 ms/批量 step;CPU 4 线程 22k sps
而 GPU 只有 18k),**SM 大部分时间空着**,两个进程交错发 kernel 应接近线性叠加。

**为什么核数降到 4**:`sacct` 实测每个进程 `TotalCPU ≈ 墙钟`,即 **0.99 核**;
旧的每 link 6 核一夜白占约 **33 核·小时**,而 fairshare 按预留计费。

**为什么仍然是 30 分钟而不是合成一个 2.5 小时的大作业**:今晚的教训是
**短作业能起、长作业排队**(30 分钟立刻起跑,而 3 小时的等了 78 分钟)。
**4 个共卡 link 替掉 8 个串行 link —— 排队 4 次而不是 8 次,而单个作业形状不变。**

**科学不变**:两条臂仍是独立的 B=1024 运行,`bzt` 仍是 `bothheads` 的单变量对照
(对照关系在于**比较结果**,不在于先后顺序)。两组阵列与读数各自挂在第 4 个共卡 link 之后。

**同时诚实记下这条的期望值上限**:本会话每一层都测出 ≤+5,115,而真实台阶是
**天梯 692 → 1287**。**所以这两条臂即便正向,也不会接近那道门** ——
它们值得跑,只因为现在便宜(4 个 link 约 2 小时)且是**最后一条未测的结构假设**;
若代价是 16–20 个 link,正确的决定是不跑。

## 2026-08-23 · 撤回我自己的一句推测:**观测不是瓶颈**,`log1p(money)/12` 反而把分辨率分配给了决策带

我在给用户的总结里说过"跨那 595 分需要下一代的**动作空间/观测**设计"。
**动作空间那半有证据**(31 个市场动作全单一用途;`bazaar` 去掉机会成本拿到 +3,824);
**观测那半是推测,而我刚测了它,是错的。**

`rl/obs.py` 把钱编码成 `log1p(money)/12`,我怀疑这会把"买得起 / 买不起"的门槛压平。
实际算出来:

| | money | `log1p/12` |
|---|---|---|
| 起始约 1.5k | 1,500 | 0.609 |
| 买第 2 象限(1000) | 1,000 | 0.576 |
| 第 11 个帮手门槛 | 2,880 | 0.664 |
| 第 12 个帮手门槛 | 4,660 | 0.704 |
| 买第 4 象限(4000) | 4,000 | 0.691 |
| 我们第 20 天 | 15,191 | 0.802 |
| k06 第 20 天 | 36,987 | 0.877 |
| cleo 期末 | 98,420 | 0.958 |

**所有采购决策都发生在 1k–20k 这一带,它只占金额范围的 10%,却占了输入动态范围的 25%
(0.576 → 0.826)。而 20k–200k 那段几乎没有决策,只占 0.192。**
**第 11 与第 12 个帮手的门槛差是 0.040** —— 对一个 4867 维输入里的标量,这是完全可分辨的。

**所以 log 压缩不是把决策带压掉了,是把分辨率分配给了它。观测能表达"买得起吗"。**

**这条的价值在于它排掉一个解释,把诊断留在证据所在的地方**:
`BUY_LAND` 在 66–71% 的回合上合法、概率却只 0.00–1.52%,**不是因为网看不见钱够不够,
是因为那个动作从来不被采样**(而熵奖励是一个标量加在 14 个头的和上,所以塌缩不被罚也看不见)。
**这是优化/探索问题,不是表示问题** —— 而 `bazaar` 攻的正是"为什么不值得采样它"
(采购要付掉那一回合的卖出),这也解释了为什么它是唯一在这条轴上拿到正号的。

**给用户的那句话据此更正为**:需要的是**动作空间**的下一代设计,**观测不在其中**。

## 2026-08-23 · 资源利用率实测:**GPU 已经吃满了(利用率中位 98%),真正的墙是显存 —— 一个进程 39.6 GB。提高 B 和共卡两条建议都被推翻**

用户要求:看能否用线程/进程/batch 把 CPU 与 GPU 吃满,因为申请多用得少会拖长排队。
一个 30 分钟的作业扫了 B ∈ {1024,2048,4096,8192} × 线程 {1,4,8} × 共卡 {2,3},
并用 `nvidia-smi` 每 2 秒采真实数据。**结果推翻了我自己此前两条建议。**

### 一、GPU 不是闲着的:利用率中位 **98%**

| | 值 |
|---|---|
| GPU 利用率(447 个采样点) | **中位 98%**,均值 72%,最大 100% |
| 显存占用 | 中位 **64,077 MiB**,最大 **81,031 / 81,090 MiB** |

**我此前根据 54.9 ms/批量 step 与"CPU 4 线程 22k sps > GPU 18k"推断"SM 大部分时间空着",
这个推断错了。** `nvidia-smi` 的 `utilization.gpu` 是"至少有一个 kernel 在跑的时间比例",
所以 98% 与"kernel 很小但背靠背"是相容的 —— **但它明确否掉了"GPU 在等 Python 喂数据"**:
没有空隙可以塞第二个进程。

### 二、提高 B:**不可行,会 OOM**

一个进程在 B=1024 下实测占 **39.6 GiB**。B=4096 时 GAE 的 clone
**试图再分配 53.40 GiB**(另一处 106.79 GiB)→ `torch.OutOfMemoryError`。

| B | 结果 |
|---|---|
| 1024 | 跑通,**39.6 GiB** |
| 2048 | 失败 |
| **4096 / 8192** | **OOM(试图分配 53.4 / 106.8 GiB)** |

**所以"B=1024→4096 拿 8×"这条建议是错的** —— 我先前算的"一份保留批 14.55 GB"
只是 `keep` 列表**更新时保留的**那部分,**采集峰值(含 `next.observation`、logits、GAE 的 clone)
是 39.6 GB**,是我估算的 1.4–1.8 倍。**`DESIGN.md §5` 说的 B=2048–8192 在当前 `obs_dim` 下不成立。**

### 三、共卡:**也不可行**

两个进程各占 **39.57 / 39.59 GiB**,合计 **79.2 GiB**,而卡是 **79.18 GiB** → OOM。
三进程时两个降到 27.81 GiB 后仍然 OOM。
**所以我给用户的"3 个进程 78/80 GB 可行"是错的,实测连 2 个都放不下。**

### 四、线程:确认无关(这一条先前的判断是对的)

| 线程 | sps |
|---|---|
| 1 | 10,504 |
| 4 | 10,549 |
| 8 | 10,564 |

**完全平坦** —— 与 `sacct` 的 0.99 核一致,所以把 `OMP_NUM_THREADS` 定为 1、
`cpus-per-task` 降到 2(commit 3bcc527)是**唯一被实测支持的那条修改**,而且它已经做了。

### 五、于是"吃满"这个问题的真实答案

**GPU 时间已经吃满(98%),显存也接近吃满(一个进程 39.6 / 79 GiB,采样中位 64 GB)。
没有靠线程、进程或 batch 能拿到的余量 —— 三条里两条被显存挡死,一条被证实无关。**

**唯一的方向是降低"每单位有用工作的显存与 kernel 数"**,而主项是
**`obs_dim = 4867` 的 float32 观测**(10×10 棋盘 × 约 12 通道 ≈ 1,200,**观测是棋盘的四倍**)。
两条具体线索:

1. **`rl/legacy/train_t.py` 已经有 `--obs-half`**(把 replay 观测存成 float16)——
   把主项砍半就可能让 B=2048 成立。**当前的 `rl/train.py` 没有这个开关。**
2. 缩小 `obs_dim` 本身会同时改善显存与 CPU 侧前向(实测 16.59 ms/step),
   **但会让所有现有检查点失效,是下一代的事。**

### 六、这次扫描自己的一个 bug(已记,便于重跑)

四组配置全部 `rc=1`,原因是我在 profiling 脚本里用了 `--save /dev/null` ——
`torch.save` 的 zip writer 打不开 `/dev/null`(`_atomic_save` 的直写回退也一样)。
**失败发生在训练之后,所以 sps 数字是有效的**;但重跑时要用真实临时路径。
**这与本会话早先那次"`--save /dev/null` 被 `_atomic_save` 弄坏"是同一个坑,我又踩了一次。**

## 2026-08-23 · 资源利用率定案:用户的三条(线程/进程/batch)**逐条实测,三条都不通**;真正拿到的是 `--rb-free`(峰值 −22%)与核数 8→2,而下一步是 float16 观测

上一条判词只说了"GPU 已经吃满、显存是墙"。这一条把用户提的三条控制手段逐个测完,
并给出**已经做掉的修复**和**下一步的量化路径**。全部数字来自
`rl/train.py --mem-report`(新增)+ 三个作业:20360593 / 20360874 / 20361101。

### 一、线程:GPU 上无关,CPU 上有效 —— 两边的正确形态是相反的

| 线程 | GPU sps | CPU sps(B=1024) |
|---|---|---|
| 1 | 10,504 | — |
| 2 | — | 2,168 |
| 4 | 10,549 | 3,573 |
| 8 | 10,564 | 5,332 |
| 16 | — | **6,304** |

**GPU 侧完全平坦**(`sacct` 每个 link 只用 **0.99 核**,三条臂十一个 link 无例外),
所以 8 核是纯浪费 → 已改 **2 核 + `OMP_NUM_THREADS=1`**(commit 3bcc527)。
**CPU 侧线程是真有效的**(2→16 线程 2.9×),所以**评测/花名册作业保留 32 核是对的** ——
`sacct` 实测它们利用 **63–96%**(`kg-wheatab` 96%、`kg-hybrid` 90%、`kg-*-ros` 63–81%)。
**这两件事此前被我混成一条结论,方向正好相反。**

### 二、共卡(多进程):**决定性地否**,而且不是"放不下",是"放下了也慢 4.5 倍"

| 形态 | 每进程 sps | 聚合 sps | 峰值显存 |
|---|---|---|---|
| 单进程 B=1024 | **10,469** | **10,469** | 47.32 GiB |
| 单进程 B=512 | 5,772 | 5,772 | 23.78 GiB |
| **2 进程 × B=512** | **1,151 / 1,154** | **2,305** | 22.79 GiB ×2(放得下) |
| 2 进程 × B=1024 | — | OOM | — |

**显存放得下的那一档(2×22.79=45.6 GiB)聚合只有 2,305,是单进程 B=1024 的 1/4.5。**
每个进程从 5,772 掉到 1,151(**5.0× 慢**),远坏于公平分享该有的 2×。
**机制**:没有 MPS 时,不同 CUDA context 的 kernel 是**时间片轮转**而不是并发;
对一个**发射延迟主导**的负载,时间片还要在序列化之外再付上下文切换。
**所以"一张卡塞 2–3 个进程"这条(我此前也这么建议过)是错的,两个理由都错:
既不是只差显存,补上显存也不会赢。**

### 三、batch:**是**杠杆,但被显存挡死

| B | sps | 峰值 | 结果 |
|---|---|---|---|
| 512 | 5,772 | 23.78 GiB | ok |
| **1024** | **10,469** | **47.34 GiB**(`--rb-free`)/ 60.97(原样) | ok,**这是天花板** |
| 1536 | **15,166** | 68.17 GiB | **OOM** |
| 2048 / 3072 | — | — | OOM |

**B=1024→1536 是 1.5× 的 lane 换 1.43× 的吞吐,而迭代墙钟只从 69.5 s 走到 72 s** ——
**发射延迟主导已被证实**,所以 B 是这条线上唯一的真吞吐杠杆。它现在不可用,
纯粹因为显存。

### 四、已经做掉的修复:`--rb-free`

`--mem-report` 读出的 B=1024 分解:采集批 **27.68 GiB**,其中
`observation` 与 `next.observation` **各 13.35 GiB**。峰值处曾有三份观测,
第三份是 `ReplayBuffer` 的 `LazyTensorStorage`,而且 `rb.empty()/rb.extend()`
**每个 epoch 重填一次**。它唯一的作用是 `SamplerWithoutReplacement`,
而那正好是 `flat` 的一个随机划分 → 用 `randperm` 代替(5.9 MB int64)。

| | 峰值 | 跨采集边界常驻 | sps |
|---|---|---|---|
| 原样 | 60.97 GiB | 43.37 GiB | 10,593 |
| **`--rb-free`** | **47.34 GiB** | **29.74 GiB** | 10,592 |

**峰值 −22%、常驻 −31%、吞吐不变**;iter-0 的 `pg/vf/ent` 三位小数完全相同
(−0.0006 / 0.0186 / 3.959 对 3.958),之后随 RNG 流分离而缓慢发散 ——
**同一估计量、同一批数据、不同洗牌**的签名。已在
`slurm/rl_train.sh` 与 `rl_ab.sh` 默认带上(93e1822)。
**顺带更正一处我自己的说法**:`flat = td.reshape(-1).select(*keep)` **不是拷贝**
(常驻只涨了 1.84 GiB = 一个 minibatch),所以"三份拷贝"里 `flat` 那份不算,
真正的三份是 `observation` + `next.observation` + rb storage。

### 五、下一步的量化路径:float16 观测

`next.observation` 那 **13.35 GiB 对损失没有任何贡献** —— `trl_env.py` 里
`out["terminated"] = done` 且 **`truncated` 从不设置**,所以最后一步的自举被乘 0
(GAE 的 `shifted` 路径也只在 done 行读它)。**但它删不掉**:在 TorchRL 里
它**就是下一个状态**,`step_mdp` 会把它提升成下一步的 `observation`,
删了 rollout 就走不动。这份重复是 collector 的 (B,T) 存储格式自带的。

于是唯一的省法是**精度**:float16 观测 → 采集批 27.68 → **14.3 GiB**,
峰值 47.34 → 约 34 GiB → **B=2048 放得下** → 按已测的 B 弹性外推**约 2× 吞吐**。
**量程是安全的**:`features_t.py` 里每一项都归一化过
(`log1p(money)/12`、`clamp` 后除以自己的上界 `/3` `/60` `/20` `/12` `/2`),
观测落在约 [-1,1],float16 在那里的精度约 1e-3。
先例是 `rl/tensor_env/train_t.py --obs-half`。
**它改变更新看到的输入,所以要先做 A/B,不能直接开。**

### 六、CPU 不是 GPU 的替代,但**并行臂**可能该走 CPU

同配置同 B=1024:**GPU 10,469 对 CPU 16 线程 6,304 = 1.66×**。
(**撤回**我此前"CPU 4 线程 22,222 比 GPU 18,000 快"的说法 —— 那比的是
**不同的 B 加不同的配置**,不是同一件事。)

但单臂速度不是我们的瓶颈,**并行臂数**才是:一张 H100 给 10,469 sps;
同样的排队代价换成 **6 个 16 核 CPU 作业 = 6 × 6,304 = 37,824 sps 聚合**,
是单卡的 **3.6×**,而且 CPU 节点随时可得、**没有 80 GB 天花板**(140G 内存跑 B=2048 无碍)。
A/B 要的正是并行臂。**这条是有数字支撑的假设,不是判词** ——
还需要量一次两种形态的真实排队等待再定。

### 七、`DESIGN.md §5` 的显存账错了约 7,000×(已加更正段,48d4721)

原文:"显存账:B=8192 × 状态 ~4KB/局 + 网络与优化器 ~百 MB,一张 48GB L40S 富余一个数量级"。
**它算的是引擎状态,漏了 PPO 为每个时间步保存的观测**:每条 lane 是
719 步 × 4867 float32 × 4 B × 2 份 = **28 MB,不是 4 KB**。B=8192 的采集批本身要 229 GB。
**这就是我一整夜"提高 B"和"共卡"两条建议的共同源头。**
同节有两条原判**成立**并已标注:GPU 不等 Python 喂数据(利用率中位 98%),
以及 B 确实是吞吐杠杆。

**补一条(同批,20360874 最后一档):CPU 上加大 B 没有用。**
CPU 16 线程 B=1024 是 6,304 sps,B=2048 是 **6,435**(+2%),而同一步长在 GPU 上是 **+43%**。
**两边的瓶颈不同**:GPU 发射延迟主导 → 更多 lane 摊薄固定开销;
CPU 算力主导 → 更多 lane 就是更多活,吞吐不动。
所以上面第六节里"CPU 没有 80 GB 天花板"这句**要收窄**:CPU 确实放得下更大的 B,
但放大了也不涨 —— **CPU 的优势只在"能同时跑很多个作业",不在"能跑更大的批"。**

## 2026-08-23 · 撤回上面那条"共卡"排布:它的两条技术前提都被实测证伪,`bzt`/`bothheads` 必须**串行**

上面《把 8 个串行 link 换成 4 个共卡 link》那条是**在测量之前**写的,今晚测完了,
**两条支撑它的前提都错**(数字见同日《资源利用率定案》):

| 那条的说法 | 实测 | 判 |
|---|---|---|
| "保留的批 14.55 GB,峰值约 22–29 GB;**两个 = 44–58 GB,在 80 GB 上宽裕**" | 单进程 B=1024 峰值 **60.97 GiB**(`--rb-free` 后 47.34);**两个 B=1024 直接 OOM** | **证伪** |
| "采集发射延迟受限,**SM 大部分时间空着**,两个进程交错发 kernel **应接近线性叠加**" | `nvidia-smi` 447 点利用率**中位 98%**;显存放得下的 2×B=512 聚合 **2,305 sps**,而单进程 B=1024 是 **10,469** —— **差 4.5×**,每进程 5.0× 慢 | **证伪(方向都反了)** |
| "核数降到 4:`sacct` 每进程 0.99 核" | 确认,已降到 2 | **成立** |

**机制**:没有 MPS 时不同 CUDA context 的 kernel 是**时间片轮转**而不是并发,
对发射延迟主导的负载还要在序列化之外再付上下文切换。**"SM 空着"这个推断本身就是错的** ——
我是从 54.9 ms/step 和一个**不同 B、不同配置**的 CPU 对比里推出来的,而不是从卡上读的。

**于是 `bzt` 与 `bothheads` 回到串行**:每条 4 个 link × 30 分钟 × 2 核。
"排队 4 次而不是 8 次"这个好处**拿不到** —— 代价是 8 次排队,这是真实成本,
不是可以靠形状绕开的。**而那条判词自己记下的期望值上限不变**:
本会话每一层 ≤+5,115,真实台阶是天梯 692 → 1287,所以这两条臂即便正向也不接近那道门;
它们值得跑只因为便宜且是**最后一条未测的结构假设**。

**`bzt` 在 gen41 树上按原样跑,不带 `--rb-free`** —— 它所有的对照
(`bazaar` 解码版 49,495、同场基线 45,671)都是在没有这个标志的代码路径上测的,
保持单变量比省 13 GiB 重要。

## 2026-08-23 · 一个**预登记的前瞻检验**在 08-14 被判"面板胜出 +220.7",而收敛后的分数把符号翻成 **−266.3**:面板 + 768 局直接对打**都挑错了**

今晚读天梯(`kaggle competitions submissions`,**只读,没提交**)拿到收敛后的分数,
和 `docs/LADDER_STATE.md` 的 08-14 快照一对,发现一件比今晚所有基建都重要的事。

### 一、检验本身

`55489160`(kawashigi-k06)的提交说明自己写着 **"A PROSPECTIVE TEST of our local
metric, not a tuning step"**,判据事前写死,对照是在场的 `55484175`(topline/k01):

| 本地判据 | k06 | topline | 事前预测 |
|---|---|---|---|
| 面板胜率(1,920 局,十个第三方计划) | **98.5% [97.8, 98.9]** | 92.4% [91.2, 93.5] | **k06 胜** |
| **直接对打(768 局)** | **60.8% [57.3, 64.2]** | — | **k06 胜**(区间不含 50%) |
| 面板最弱对手 | 胜全部十个 | 最弱 78.6% | **k06 胜** |

**三个判据一致指向 k06,而且直接对打的区间排除了 50%。**

### 二、天梯的回答:反的

| ref | 名字 | 08-14 快照 | **今天(收敛)** | 移动 |
|---|---|---|---|---|
| `55484175` | topline / k01 | 2391.6(自称 08-13 已收敛于 2359.5) | **2302.2** | −57 |
| `55489160` | kawashigi-k06 | **2612.3**(94 局,74–20) | **2035.9** | **−577** |

`LADDER_STATE.md:21` 当时按事前判据把它 **resolved 成 +220.7**(2612.3 − 2391.6)。
**收敛后是 2035.9 − 2302.2 = −266.3。符号翻了,幅度 487。**

**所以那次 resolve 是错的,而且错的原因本项目自己写过**:
08-14 时 k06 是 **74–20,输了 21%**,`CLAUDE.md` 的规则是
"**一个天梯分数在这个 agent 输掉三分之一的局之前不算数**"。
**21% < 33%,那次 resolve 违反的是自己的规则**;topline 只掉了 57 分(它当时 46–13 也偏早,
但它自称已收敛且事实上稳),而 k06 掉了 577。**规则是对的。**

### 三、这条为什么比今晚的基建重要

这是本项目**最有利条件下**的一次本地-天梯对照:
**同一支队伍(カワシギ)、同一个市场层(cleo 的 MIT 适应层)、同一天的两段录像、
1,920 局面板 + 768 局直接对打、判据事前写死。** 没有"对我们自己写的花名册过拟合"
这个借口 —— 对手全是第三方挖出来的计划。

**结果是本地判据把两段几乎同源的录像排反了,差 266 分。**

`CLAUDE.md` 已经有"我们写的花名册不算天梯证据",这条更强:
**即使花名册是第三方的、即使有 768 局的直接对打、即使区间排除 50%,
本地排序仍然可以在天梯上反过来。** 所以**任何"本地涨了多少"都不能外推到天梯分数**,
而这正是我今晚(以及此前每一晚)在做的事。

### 四、对我自己昨夜诊断的直接影响

我整夜的行为标靶都取自 **k06**:207 颗种子、第 20 天 12 个帮手、41 块草莓地、
"卖 1,671 份化肥"。**k06 是这两段录像里天梯分低的那一段(低 266 分)。**
标靶本身没被推翻(k06 仍然挣约 100k 且碾压我们),
**但"照 k06 对齐"这件事背后的排序权威消失了** ——
选 k06 当标靶的理由是面板胜率 98.5%,而面板恰好就是被证伪的那个判据。
**唯一还站得住的跨场信号仍然只有那一条**:cleo 1287.2 → hybrid-cleo12 692.2,
接上我们的网掉 595 分,本地同向(纯 cleo 98,420 > hybrid 90,409)。

### 五、顺带三处文档更正(已改)

1. `docs/GAP-2000.md:20` 把 `55489160` 标成 "topline" —— 它是 **kawashigi-k06**;
   topline 是 `55484175`。
2. `docs/LADDER_STATE.md` 的两个分数(2391.6 / 2612.3)是 **08-14 快照**,今天是
   2302.2 / 2035.9;那句 "对照实验已按事前判据 resolved,+220.7" 要改成
   **收敛后 −266.3、面板被证伪**。
3. `LADDER_STATE.md` 开头的常驻警告 **"现在不要提交,会把场上的对照组挤掉" 已经过期**:
   现在的活跃两位是 `55688747` hybrid-cleo12(**696.8**,不是监控里写的 705.9)与
   `55685828` "Pure Python Agent v1"(**245.4**,08-22 07:30)。
   **2000+ 那两个早就失活了,一个活跃槽正被 245.4 占着。**
   所以"新提交会挤掉宝贵对照"这个反对理由不再成立 —— 挤掉的是 245.4。
   **提交决定仍然归用户,这里只更正事实。**

## 2026-08-23 · 接着上一条:**天梯上相差 266 分的那两段录像,本地四把尺子一把也分不开** —— `hands@20` 在 12 处饱和,草莓是反的

上一条证伪了面板。剩下的唯一本地仪器是**校准到 18 个真实天梯分**的 ρ 表
(`hands@20` +0.96 > 草莓 +0.88 > 畜群 +0.84 > 钱 +0.73)。
两段录像都是本地文件(`agents/champ/k01.py` = topline = 2302.2,
`agents/champ/k06.py` = kawashigi-k06 = 2035.9),**所以这把尺子可以在面板失手的同一个
案子上被检验**。预登记写在脚本里:若 `hands@20` 把 k06 排到 k01 之上或并列,
则**没有任何本地仪器已知能排出天梯强度**,那么 `bzt` 的九对手中位也回答不了"是否更接近 2000"。

### 结果(对 `closer_cleo`,12 个种子)

| 尺子 | topline/k01(2302.2) | k06(2035.9) | 判 |
|---|---|---|---|
| **`hands@20`**(ρ=+0.96) | **12.0** | **12.0** | **并列 —— 而 12 就是 `MAX_HANDS`** |
| 畜群@20(+0.84) | 14.0 | 13.9 | 并列 |
| 站着的作物@20 | 58.8 | 57.6 | 并列 |
| 草莓卖单(+0.88) | 227.0 | **248.9** | **反的**(4 与 12 个种子都反) |
| 钱@20(+0.73) | 39,941 | 39,331 | 差 610,**未分辨** |
| 终局钱 | 94,223 | 88,738 | 差 5,485,**未分辨** |
| `crew@28` | 10.0 | 10.0 | 并列 |

**四把尺子:两把结构性并列、一把方向相反、一把差距在噪声内。**
而天梯把这两个分开了 **266 分**,且两者都已收敛(各数百局)。

### 一、`hands@20` 的 ρ=+0.96 是**饱和**造出来的

**两段顶端录像都顶在 12 = `MAX_HANDS`。** 那个 +0.96 全部来自
**"我们在天花板以下(8–10)对他们在天花板上(12)"**这一道台阶,
**在强 agent 之间它没有任何分辨率**。所以它能告诉我们"我们还没顶到天花板",
但**不能区分 1287 与 2302**,而 2000 这个目标正好活在后一个区间里。

**这也顺便从机制上解释了今晚的标记/杠杆之谜**:`foreman` 把帮手推到 12 亏 10,299
不是运气不好 —— **一个饱和的标记按构造就不可能是杠杆**,推到天花板只是让标记
到达它的上界,别的什么都没动。

### 二、于是"本地涨了多少"这件事的处境比上一条更糟

上一条说的是"本地排序可以在天梯上反过来"。这一条更强:
**天梯上 266 分的差别,在本地是完全不可见的** —— 不在持有帮手数、
不在畜群、不在站着的作物、不在草莓量、也不在终局钱里。
**所以区分 2302 计划与 2036 计划的那个东西,不是我们现在测的任何一个量。**
`bzt` 的九对手中位只能回答"它在我们的花名册上更强了吗",
**不能回答"它更接近 2000 吗"** —— 后者需要提交,而提交决定归用户。

### 三、方法论:4 个种子差 29,500,12 个种子只差 5,485

第一次跑 4 个种子时终局钱差 **29,500**,我差点就把它当成"钱是唯一排对的尺子"发出去;
加到 12 个种子后只剩 **5,485**。**这正是档案里记过两次的坑**
(`thrift` 单种子 +33,758 对真值 +3,268;`bazaar` −3,084 对真值 +3,824)。
**而"并列"和"方向相反"那三条在 4 与 12 个种子下都稳定** ——
结构性的结论比数值性的结论便宜也可靠。

**还开着的问题**:钱那 5,485 是真的还是噪声,需要 96 局量级才能定
(本项目标准:96 局分辨 10 点、384 局分辨 5 点)。**没有跑** —— 它不改变上面的结论
(饱和与反向是定性事实),只影响"钱能不能当顶端的尺子"这个次级问题。

### 四、探针自己的两个 bug(都记下来,因为都是档案里的老坑)

1. **`crew@20` 第一次读出 0.0** —— 帮手是**日工**,引擎每晚解雇全部帮手,
   所以**每一天第一个回合读到的都是 0**。必须取当天的**峰值**。
   这就是清单第 (h) 条"在引擎量发生的那一刻测量"。
2. `money` 数组初始化成 `None`,而 720 步只覆盖第 0–29 天,**第 30 天永远没被写过**,
   跨种子累加时 `None + int` 直接崩。

## 2026-08-23 · 操作判词:**训练不该等 GPU** —— CPU 上 9,443 sps 对卡上 10,469(只慢 10%),而 GPU 队列是 1,289 排队对 39 在跑

`bzt` 的 GPU 链 12:56 提交等了 2h25m 没起跑,今晚重排后再次卡在 Priority。查队列:

```
GPU 作业:1,364 总,1,289 PENDING,39 RUNNING     (33 : 1 的积压)
我们的优先级:1,557,000,其中 FAIRSHARE 1,554,750,AGE 只贡献 4
```

**AGE 贡献 4 分,所以"等下去"不是策略** —— 排队时间几乎不改善优先级,
而 fairshare 按预留计费,所以 GPU 预留本身还在加重下一次的等待。

于是按今晚的 CPU/GPU 实测把这条臂**换到 CPU 上重排**(7 个 link × 16 核 × 140G,
而不是 4 个 GPU link —— CPU link 每 25 分钟做的迭代少一些,7 个才够原本预登记的预算)。
**60 秒内就起跑了**(c275),而 GPU 版在 1,289 个排队作业后面。

### 实测吞吐比我 profiling 时估的还好

| | sps | 起跑等待 |
|---|---|---|
| GPU(H100,2 核) | 10,469 | **1,289 个作业排在前面** |
| **CPU(16 核,c275)** | **9,443 / 9,155** | **< 60 秒** |
| CPU(16 核,c402,profiling 时) | 6,304 | — |

**CPU 只慢 10%,不是我 profiling 里说的 40%。** 差别在**节点**:
profiling 跑在 c402 上得 6,304,这条臂在 c275 上得 9,443(1.5×)。
**所以"CPU 比 GPU 慢 1.66×"这个说法要收窄成"取决于落在哪个节点,实测 1.11–1.66×"。**

### 结论

**训练链的默认形态应当是 CPU,不是 GPU。** 理由三条,都是实测:
(1) 吞吐只差 10–40%;(2) GPU 队列 33:1 积压而 CPU 立即起跑;
(3) **AGE 只贡献 4 分**,所以等待不会自己变好,而 GPU 预留会加重 fairshare。
`slurm/rl_train.sh` 仍是 GPU 形态(它已按 2 核修好),
**但"要不要用它"现在有了一个 CPU 的答案** —— 需要几条臂并行时更是如此
(一张卡塞两个进程已被证伪:聚合 2,305 对单进程 10,469)。

**诚实标注**:训练设备从 CUDA 换到 CPU **不是行为中性的** ——
引擎逐字节门在两个设备上都绿,但 f32 有 1-ulp 级差异,轨迹会分叉。
**这是"换了个种子"级别的差异,不是换了算法**;而替代方案是**根本拿不到结果**。
`bzt` 的对照(`bazaar` 解码版 49,495、同场基线 45,671)本身都是用参考引擎在 CPU 上评测的,
评测侧不受影响。

## 2026-08-24 · `bzt` / `bothheads` 收口：最后一个动作空间假说阴性，训练没有让建设通道活起来

Claude 会话因周额度耗尽前没有来得及写判词，但 Slurm 链本身全部完成。两臂都在
`Kaggriculture-gen41` (`c210117`) 上用 CPU 跑了 7 个约 26 分钟的 link；随后各跑
9 对手 × 48 seeds × 双席位 = 864 局，并由 reader 作业完成汇总。当前 `squeue` 为空。

| 臂 | 单变量 | 训练作业 | 最终训练量 | 评估 / reader | 状态 |
|---|---|---|---:|---|---|
| `bzt` | `--bazaar`：同一市场回合允许 SELL 后继续采购 | `20362905`–`20362911` | 134 iter / 98,658,304 steps | `20362912_[0-8]` / `20362913` | 全部 `COMPLETED 0:0` |
| `bothheads` | `bzt` + `--hand-spill` | `20363693`–`20363699` | 158 iter / 116,328,448 steps | `20363700_[0-8]` / `20363701` | 全部 `COMPLETED 0:0` |

CPU 吞吐与前一条操作判词一致：`bzt` 全程均值 9,331 sps，末节约 10.4–11.4k；
`bothheads` 全程均值 10,939 sps。日志里的 `Can't initialize NVML` 是 CPU 节点上
Torch 探测 CUDA 的警告，不是失败；两个链尾都有 `*-LINK-DONE`，18 个评估 JSON
均存在，非空 error log 为零。

### 预登记结果

同场对照是 `control230-n9` 45,671；`bazaar` 的**免训练 decode-only** A/B 已有
49,495 (+3,824)。因此 `bzt` 必须超过 49,495 才能说明“开放通道后，训练学到了
额外的建设理由”；`bothheads` 的单变量对照必须是 `bzt`，不是旧 baseline。

| | `control230-n9` | decode-only `bazaar` | `bzt` | `bothheads` |
|---|---:|---:|---:|---:|
| 9 对手收入中位 | 45,671 | **49,495** | **47,337** | **47,743** |
| 对同场 control | — | +3,824 | +1,666 | +2,072 |
| 对直接前级 | — | — | **-2,158** | **+406** |
| held-out 击败数 | 3/7 | — | 4/7 | 4/7 |
| p05 | 21,761 | — | 21,767 | 23,623 |
| `<20k` | 3% | — | 3% | 2% |

两臂都只击败 starter、barnyard、enhanced/main 与 grazier；对 berrybaron 胜率分别
10/96 与 7/96，对 closer/lena/broker/w49 都是 **0/96**。这不是“样本还不够”：
0/96 的正确 Wilson 95% 上界是 3.85%，明确低于 50%。

近端机制也没有按预登记移动：

| 对 closer，3 seeds | `control230` | `bzt` | `bothheads` |
|---|---:|---:|---:|
| 土地 | 2.0 | 2.0 | 2.0 |
| crew | 约 7.9 | 8.21 | 8.12 |
| 整季种子 | 47 | 44 | 43 |
| 草莓 | — | 27 | 25 |
| 作物 | — | 25 | 23 |
| d18 / d28 空地 | 18 / 27 | 19 / 21 | 18 / 20 |
| money / margin | — | 44,011 / -60,699 | 46,324 / -66,499 |
| `P(BUY_SEED | legal)` 中位 | 0.02% | 0.02% | 0.03% |

**判词一（`bzt`）**：解码层允许“卖后再买”本身值 +3,824，但让 PPO 在这个通道上
继续训练，结果反而低 2,158；采购概率、土地和种子数都没有起来。市场回合机会成本是
一个真实缺陷，却不是导致策略不会建设的充分原因。**动作可用不等于长期信用存在。**

**判词二（`bothheads`）**：增加 hand-spill 后只比 `bzt` 高 406，远小于本项目已见的
约 2.3k 重跑/场地波动，而且它用了更多训练步。作物、草莓与种子没有上升，对 cleo
margin 还更差。两个头的局部可达性同时修好，也没有形成需要的跨日建设序列；最后一个
未测的动作空间组合假说至此阴性。

**总判词**：这两条臂把问题进一步定位到**信用分配与策略层级**，不是缺少动作、网络
不够宽、训练不够久、对手不够强，或采购与卖出不能同回合。继续在同一 PPO 配方上加
link 没有实验动机。下一次训练必须先改变“如何给一季只发生几次、收益延迟数百步的
建设决策记功”，并用 closer 非零胜率/正边际贡献作硬门。

### 同时发现：`eval.py` 的 stdout 判词自 08-12 起存在百分数单位 bug

`tools.stats.wilson()` 返回 **0–100 的百分数**，而 `tools/eval.py` 曾用 `.1%` 再乘
100 显示，并拿区间与 `0.5` 而不是 `50.0` 比较。因此旧日志会把 10/96 打成
`[575.7%,1812.2%]` 并错误打印 `A is better`，把 0/96 错打成 unresolved。

影响边界：对局、胜负、money、margin 和 JSON 内的 Wilson 数值本身均正确；错误只在
`eval.py` 的 CI 文本格式与自动 `VERDICT`。依赖原始胜负或 `tools.stats.resolved()` 的
汇总不受影响。08-24 已统一百分数单位并增加 10/96、64/96、50/100 三个回归检查；
以后不再引用修复前日志中的自动 `VERDICT`，只引用原始计数或重新渲染后的区间。

## 2026-08-24 · 工作区收口：移除 31 个实验 worktree，保留分支与主树证据

用户确认旧实验无需再复现后，移除了 `/scratch/jwj/Kaggriculture-*` 的 31 个辅助
worktree；`git worktree list` 现在只剩主树 `/scratch/jwj/Kaggriculture`。没有删除
任何对应 Git branch，因此所有受 Git 跟踪的代码仍可从分支重建。

删除同时丢弃了辅助树内约 16.9 GiB 被 `.gitignore` 排除的 checkpoint、导出 agent、
评估 JSON、bank 状态，以及 `gen16` 的两项未提交修改；这些内容没有另做备份，不能从
Git 恢复。所以上一条中“18 个评估 JSON 均存在”描述的是**判词生成时的完整性检查**，
不是当前文件系统状态。`bzt` / `bothheads` 的原始产物已经删除，最终指标、作业号、
行为读数与判词保留在本文件中。

主树未受清理影响，仍保有 `chisel`、`longcredit`、`cropper`、`anvil` 等可用 checkpoint，
以及 `EpisodeT` 的 fork/restore 实现。下一阶段从主树重新选定并哈希一个公共低层基线，
不再依赖已删除的 gen 路径。新的执行顺序见 `rl/TODO.md`：反事实 rollout 审计 ->
冻结低层的 option-lite -> 离线宏观搜索/蒸馏 -> 最后才考虑联合 HRL。

## 2026-08-24 · Infra 收口：瓶颈在 rollout 与调度，不在 PPO；正式训练改走受控提交器

重新对齐 `logs/profsweep-20354345/smi.csv`、训练日志和 `sacct` 后，资源判词如下。

| 证据 | 读数 | 含义 |
|---|---:|---|
| H100 B=1024 每轮 | collect 约 68.0s / 训练阶段约 69.5s | rollout 占约 98%，PPO 更新不是优化重点 |
| GPU 2 秒采样（472 点） | util 中位 98%、均值 73.9%；<10% 仅 8.3%，>=90% 为 55.9% | 没有“大段 GPU 空转”；有细粒度 kernel 间隙 |
| `20360593` CPU efficiency | 47.8% of 2 cores，即平均 0.96 核 | GPU link 申请 2 核正确，继续加核无益 |
| `20354345` | 排队 1h28m43s，运行 15m48s | 端到端成本主要可由排队支配 |
| 原 `bzt` GPU job `20344664` | 排队 2h28m29s，0 秒运行后取消 | 等卡不是有效进展 |
| CPU `bzt` 首 link `20362905` | 1 秒开跑，26m17s 完成 | 当前拥堵下 CPU 周转明显更好 |
| CPU 有效链 MaxRSS | 约 76.5 GiB | 原 140G 过量；96G 有约 25% 余量 |

旧 profiling 还有两类直接浪费：`20360377` 因 checkpoint 目录无权限损失 1m39s 卡时；
`20360593` 的 B=1536/2048/3072 等 OOM 臂占掉数分钟。`B=1536` 虽首轮到 15,166 sps，
第二轮 GAE 仍 OOM，因此不能拿“首轮成功”当稳定配置；同卡双进程聚合吞吐也已实测远低于
单进程。这些都要求先有短 pilot，并让 pilot 失败阻断后续链。

已落地的操作改动：

- `rl/train.py` 现在把 collect、GAE、prepare、update、metrics、probe、checkpoint 分开计时，
  写 `timing.csv`。修掉了旧计时把上一轮 checkpoint/probe 错算进下一轮 collect 的问题，
  并区分不含后处理的 `train_sps` 与真实整轮 `wall_sps`。
- `slurm/rl_train_cpu.sh` 成为默认训练形态（16 核、96G、30 分钟）；GPU 模板保持 H100
  单进程、2 核、16G，并每 2 秒记录利用率、显存与功率。
- `tools/submit_rl.py` 强制记录假设、验收阈值、commit 和完整 argv；默认 5 分钟 pilot，
  最多 8 个 link，依赖只用 `afterok`。父任务失败时后续不会运行；由于本集群没有
  `kill_invalid_depend`，残留的 `DependencyNeverSatisfied` job 仍需手工 `scancel`。
  配置、初始化权重、bank/tape 等外部输入同时记录 SHA-256，并在计算节点启动前复核。
  CPU/GPU pilot 分别默认要求 5,000/8,000 sps，NaN/Inf 或吞吐门失败均非零退出。
- `tools/slurm_audit.py` 统一汇总排队/运行时间、CPU efficiency、训练阶段占比和 GPU
  telemetry。完整操作合同见 `docs/INFRA.md`。

**判词**：在当前集群，优先级不是把 H100 的瞬时利用率从 74% 调到 90%，而是避免两小时
无产出的排队和失败链。默认 CPU 是周转时间选择，不是宣称 CPU 单机更快；GPU 只给已经由
pilot 证明需要它的单进程配置。算法侧若要提速，应减少 719 步 rollout 中的小算子/观测
成本，而不是增加 PPO epochs、CPU 核数或共卡进程。

完整回归由 CPU job `20406949` 验证：排队 65 秒、运行 47 秒、退出 `0:0`，
`test_infra.py`、`test_stats.py` 与 `test_trl.py` 全部通过。该测试峰值 RSS 仅 1.3 GiB，
平均只用 0.63 核，因此 `slurm/rl_test.sh` 随即由 4 核/16G 收紧为 2 核/4G。

## 2026-08-28 · G1 定位:**边际损失 100% 产生在 day 12 之后,机制是"接手即套现"** —— 而且它在 day 14 时钱是**领先**的

新增的 G1 门(`rl/TODO.md`「里程碑门」)问的是:把我们的网接到 cleo 的开局后面,它有没有
把那个开局做坏。作业 `20703478`(8 核,10m30s)用 `tools/byday.py` 在 **32 个配对 seed**、
**两个对手**上逐日对比 `closer_cleo` 自己续跑与 `hybrid-cleo12`(cleo 前 12 天 + 我们的网)。

### 一、内建校验先过:day 0–12 逐元相等

两者按构造共享前 288 步,所以逐日钱必须**完全相同**。实测:3,000 / 21 / 437 / 1,004 /
674 / 1,478 / **8,486**(k06 场)与 3,000 / 21 / 439 / 949 / 710 / **9,119**(w49 场),
累计缺口 day 0–12 **全部为 +0**;day 12 的站着作物/畜群两边都是 **38 / 14**。
**所以后面的差是真的差,不是测量噪声。**

### 二、缺口的时间形状:先领先,再崩

| day | 14 | 16 | 18 | 20 | 24 | 28 |
|---|---:|---:|---:|---:|---:|---:|
| 累计缺口(k06) | **+1,851** | +466 | −208 | −5,509 | −12,151 | **−13,051** |
| 累计缺口(w49) | **+1,688** | +296 | −198 | −5,723 | −13,370 | **−13,238** |

**两个对手同号、同量级、同穿零日期(day 18)。** 而 GAP-2000 记的 −8,011 是九对手中位;
在这两个强墙上是 **−13.1k / −13.2k**。

### 三、机制:接手完好农场的**第一天**就套现,而且不再补种

day 12 是精确的开关。那一天两边的农场**完全一样**(38 株 / 14 畜),而动作是:

| day 12 | cleo | hybrid |
|---|---:|---:|
| 买种子 | **13** | **0**(w49 场 1) |
| PLANT 动作 | **14** | **1** |
| **卖出单位** | 31 | **121** |

此后也没有回补:day 12 之后 cleo 还买 3+3 颗种子、种 2+5 株;hybrid 买 1+0、种 2+0。
于是**站着的作物**与**浇水**同步塌掉:

| day | 12 | 15 | 18 | 27 |
|---|---:|---:|---:|---:|
| 站着作物 cleo | 38 | **56** | **58** | **50** |
| 站着作物 hybrid | 38 | **27** | **24** | **9** |
| WATER cleo | 39 | 41 | 48 | 21 |
| WATER hybrid | 25 | 24 | 21 | 8 |

**所以这不是"买不起"或"开局差",是"接手后把继承的资产变现、不再维护"。**
day 14 钱领先 1,851 正是套现的签名:把 38 株的存量卖成现金,然后没有东西可收。

### 四、它更正了此前诊断的落点

`rl/TODO.md`「当前诊断」写的是"day 1 以相同现金只形成约 16 株而非 19 株,到 day 12 约为
40 株/12 畜而非 56 株/14 畜"。那是 `route_s34` 对完整教师的比较,成立;
**但当开局被真的交到网手上时,day 12 两边都是 38/14 —— 开局不是缺口所在,
缺口 100% 在 day 12–29 的维护段。** 这对锚的设计是决定性的:

> **要锚的不是"day 1 的 19 株",而是 day 12 起的"每日买种/落种数"与"卖出量"。**

### 五、它同时统一了五个旧的阴性结果

- `P(BUY_SEED | legal)` 中位 **0.02%** —— 这里量到了它的代价:接手完好农场当天买 0 颗种子。
- 账本的"支出高 79%" —— 不种小麦,饲料就得按被两家推高的市价反复买。
- `foreman`(−10,299)/`homestead`(−5,844) —— 对一个会套现的策略强推采购是纯浪费。
- 唯一正向的路线技能是**选择性施肥**(+3,865 八格全正)—— 施肥是**维护**动作。
- HRL pilot 配对提升 **0** —— option 集里从来没有"别套现、继续补种"这一项。

### 六、一条新的测量陷阱(要进检查清单)

**任何在 day 18 之前读钱的门,都会把这个策略判成比 cleo 更好。** day 14 它领先 1,851。
所以"整局 margin"不能用早期切面代替,而"钱涨了"在这条线上尤其危险 ——
它可以正好是资产被卖掉的度量。

## 2026-08-28 · G1 第一个补救假设**被自己的预登记判据否掉**:强制维护资产在弱对手上 +6k~+9k,在两堵强墙上是负的(w49 的 CI 排除 0)

上一条把机制定位成"接手即套现、不再补种"。最自然的补救是"强制它维护"。三个作业测完了,
**假设阴性**,而且否掉的方式指向一个更深的东西。

### 一、pilot(`20704189`,8 lanes,63 s)先否掉了朴素形式

| option | 完成 | margin |
|---|---:|---:|
| `farm_phase:STRAWBERRY:COW:3:38:14` | 2/16 | **+1,604** |
| `expand_crop:STRAWBERRY` | 0/16 | **−40,458** |

**"多买草莓种子"是灾难性的。** 而 `farm_phase` 的 `option_elapsed=240`(= 整个 timeout)
且 `success=False`:**option 跑满窗口也没达成 38 株里程碑**,`final_crops` 只 +6.4,
而 **`final_crew`=0.0** —— 维护完全没动用帮手。档案记"顶端种植 100% 是帮手劳动",
所以下一步不是把目标从 38 抬到 48/56(执行器连 38 都到不了,那是白跑),
而是**把维护交给帮手**。

### 二、crew 假设在**完成率**上成立,在**钱**上不成立

作业 `20704443`/`20704444`(各 256 配对,四对手双席位,timeout 240 / 408):

| timeout | option | 完成率 | margin |
|---|---|---:|---:|
| 240 | **`crew_build_phase`** | **240/256(94%)** | +1,218 |
| 240 | `farm_phase` | 34/256(13%) | +2,907 |
| 408 | **`crew_build_phase`** | **240/256** | +1,393 |
| 408 | `farm_phase` | 34/256 | **−89** |

**把维护交给帮手把完成率从 13% 提到 94%(7 倍),而且 margin 跨 timeout 稳定**
(+1,218 / +1,393);`farm_phase` 的 margin 从 +2,907 翻到 −89,因为只有 13% 完成,
那个数主要在量"放弃了 option 的分支"。**所以完成率与钱是两个轴,不能互相代替。**

### 三、否决它的是逐对手同号:符号沿"弱对手 / 强墙"分裂

`crew_build_phase`,timeout 240,八格:

| 对手 | seat 0 | seat 1 |
|---|---:|---:|
| starter | **+5,608** | **+8,774** |
| barnyard | **+6,928** | **+6,049** |
| **cleo** | **−1,055** | **−3,646** |
| **w49** | **−6,798** | **−6,121**(CI `[-10403,-3113]` 排除 0) |

`farm_phase` 同形(w49 −5,887 / −5,942,CI 同样排除 0)。
**预登记门要求"四对手八格同号",实测是 +,+,+,+,−,−,−,− —— 门失败,候选族拒绝。**

### 四、机制:市场是**共享**的,所以"多产"对着强卖家不值钱

`final_crops` 的分裂把原因说清了:对 starter 是 **+27**,对 cleo 只 **+6.0**、w49 **+3.2**。
而 GAP-2000 §5 记过:牛奶成交价只有 base 的 **0.16 倍**,因为它被倒了 227–425 个单位
把池子砸到底。**对着一个同样在倾销的强卖家,多出来的产量卖不出它的成本;
对着不怎么卖的 starter/barnyard,同样的产量卖得很好。**

**所以这是第四次"强推强计划的某个相关量"失败**(`foreman` 帮手→12 亏 10,299;
`homestead` 土地 2→3.7 亏 5,844;现在 `farm_phase` / `crew_build_phase` 维护资产)。
cleo 的 38 株之所以值钱,是因为它在 cleo **整套策略**里(含它的市场时机);
把资产数抄过来而不抄市场行为,就退化成同一个错误。

### 五、还站着的与被否的,分清

**站着**:Phase 1 的定位不受影响 —— 网确实在 day 12 套现(买 0 颗种子、种 1 株、卖 121
单位对 cleo 的 13 / 14 / 31),那是直接测量。
**被否**:补救方式。不是"让它保住作物",因为在强墙面前保住作物本身不赚钱。
**下一个该测的**:day 12 起**限制每回合卖出量 / 延迟抛售**,其余不动 ——
因为套现的伤害可能主要不在"作物没了",而在"把 121 个单位倒进一个共享的浅池"。

### 六、一个读数陷阱(同批发现)

`success` 会被基线是否已达标混淆:对 barnyard,`crew_build_phase` 的 `success` 是 32/32
而 `final_crops` 只 +0.06 —— 因为基线自己就已经到 38 株,里程碑是白给的。
**"完成率高"不等于"改变了行为";要和 `final_*` 的 delta 一起读。**

## 2026-08-28 · 账本否掉"倾销压价"假设:**网的 receipts 比 cleo 还高 10,295,钱少 100% 来自支出,而支出差额几乎全是饲料** —— 因为它不种小麦

上一条把"day 12 卖 121 单位对 cleo 的 31"读成"套现 + 倒进浅池压价",并把"限卖"列为
下一个该测的。**同一个作业(`20703478`)末尾的账本直接否掉了这个读法。**

### 一、数字(`tools/ledger.py`,12 seeds,同对手 k06)

| | `closer_cleo` | `hybrid-cleo12` |
|---|---:|---:|
| receipts | 101,636 | **111,931** |
| outlays | 30,468 | **62,291**(2.04×) |
| final | 74,168 | 52,640 |
| **饲料(buying product)** | 16,189(53.1%) | **50,634(81.3%)** |
| 雇工 | 9,612 | 6,739 |
| 种子/动物/土地 | 4,666 | 4,918 |
| 种子构成 | WHEAT **68** / STRAWBERRY 41 / MELON 26 | STRAWBERRY 34 / WHEAT **28** / MELON 13 |

**网卖得更多、挣得也更多(receipts +10,295)。** 钱少不是因为收入,
**是因为支出多 31,823,而其中 +34,445 就是饲料**(其余项互相抵消)。
对同一个对手,缺口分解是:cleo **"4% 是支出"**,hybrid **"59% 是支出"**。

### 二、机制在引擎里,是确定的

`op == "FEED"` 执行 `_inv_take(inv, "WHEAT", 1)` —— 动物每天从**自己棚里**吃 1 个小麦。
所以**不种小麦的农场,就得在一个被两家一起推高的市场上买饲料**,而且畜群越大账单越大。
cleo 种 68 WHEAT 自给;网种 28,把地给了草莓/甜瓜(现金作物),于是饲料靠买。

### 三、这同时解释了上一族为什么会负

`expand_crop:STRAWBERRY` 的 **−40,458** 不再是谜:多加现金作物既花种子钱、又占掉本可
种小麦的地,把饲料账单推得更高。而 `crew_build_phase` 在强墙上为负、在
starter/barnyard 上为正,也与此一致 —— 强墙同样在买卖饲料类商品,把价格推高的正是双方。

### 四、判词的方向修正(第二次修正我自己)

- **不是**"少卖"(receipts 更高是好事,不该压);
- **不是**"保住作物数"(上一条已被八格同号门否掉);
- **是**"把饲料从买改成种" —— 这是一个**输入成本**问题,不是产出问题。

而这条与前四次失败的"强推相关量"**性质不同**:它不是抄 cleo 的资产数字,
而是修一条**引擎里确定的物质流**(每畜每天 1 小麦)。

档案里最接近的一次是 `granary`(小麦饲料 cap):"改善训练墙上的产量,但没有广泛迁移"。
它当时不是从 day 12 起的持续 option,所以不等于本条已被测过。

### 五、已提交的检验

作业 `20704758`(timeout 240)与 `20704759`(408):`farm_phase:WHEAT:COW:3:38:14` 与
`expand_crop:WHEAT`,`--min-day 12`,四对手双席位各 32 配对。
**预登记判据与上一族相同**:终局配对 margin 的 CI 排除 0,**且八格同号**
(这正是 `crew_build_phase` 倒在的那一条);行为侧要看到小麦自给上升,而不是单纯多卖。

## 2026-08-28 · 小麦假设也被否(−5,988 / −15,725,`expand_crop:WHEAT` −57k),而这**第五次**失败把整条链收口了:区分强弱的不是持有什么,是**每回合能执行多少照料**

作业 `20704846`(timeout 240)/`20704847`(408),四对手双席位各 32 配对:

| option | 完成(240 / 408) | margin(240 / 408) |
|---|---|---|
| `farm_phase:WHEAT:COW:3:38:14` | 17/256 · 22/256 | **−5,988 · −15,725** |
| `expand_crop:WHEAT` | 2/256 · 5/256 | **−56,957 · −57,956** |

比强制草莓维护更差(`expand_crop:STRAWBERRY` −40,458)。而完成率的对比也说明问题:
`crew_build_phase:STRAWBERRY` 是 240/256,小麦里程碑只有 17–22/256 —— **要凑 38 块小麦
就得把现金作物全让出去,执行器根本到不了**。

### 一、账本的事实是对的,我从它推出的干预是错的

饲料多花 34,445 是实测。但"所以让它种小麦"隐含了一个假设:
**这笔账单在边际上能用种小麦替掉**。实测说替换比账单本身更贵。原因在每块地的价值:
GAP-2000 §5 记的是 STRAWBERRY **628/块**、WHEAT **258/块** —— 换成小麦,每块地的产出腰斩。
要养 14 头动物需要几十次小麦种植,那是把地从 2.4 倍价值的作物上挪走。

**所以 cleo 的 68 株小麦不是"便宜饲料",而是它撑得起 —— 它站着 56–58 株,
我们只有 24–27 株。cleo 是"额外"种小麦,不是"改种"小麦。**
**饲料账单是低吞吐的症状,不是独立的原因。**

### 二、五次强推全部失败,而且失败的是同一件事

| 被强推的量 | 结果 |
|---|---|
| 帮手 → 12(`foreman`) | −10,299 |
| 土地 2.0 → 3.7(`homestead`) | −5,844 |
| 维持 38 株草莓(`farm_phase` / `crew_build_phase`) | 强墙上负,八格同号门失败 |
| 多买草莓种子(`expand_crop:STRAWBERRY`) | −40,458 |
| 种小麦自给(`farm_phase:WHEAT` / `expand_crop:WHEAT`) | −5,988 / −15,725 / **−57k** |

**每一次都是"抄强计划的一个成分",每一次都失败。** 而它们共同漏掉的那个量是**吞吐**:
从**同一个 day-12 状态、同样的现金**出发,cleo 每天做 **39–48 次 WATER**,我们做 **21–26**;
cleo 站着 56–58 株,我们 24–27。**大约 2 倍的每回合照料量。**

### 三、于是唯一还没被测过的杠杆是**帮手利用率**

引擎里每只手每回合做一件事,所以每回合的动作预算是**固定**的 ——
要把照料量翻倍,只能让本来空转的手去干活。而两个独立读数指向同一处:
档案记我们的帮手闲置 **30–50%**,顶端是 **8–18%**;而本轮所有维护 option 的
`final_crew` 都是 **≈0.0** —— **那些 option 从头到尾没有动用帮手**。

**这不是又一个成分相关量,它就是吞吐本身。** 也正是 `rl/TODO.md` 下一项写的
"减少空走、增加有效种植与收获的闭环执行 Option"。**标着推断**:它是当前证据链上
唯一没被否的方向,不是已证的杠杆。

### 四、方法论:这一轮的价值在于**便宜地否掉**

三个补救假设(强制维护 / 限卖 / 种小麦)全部由我提出、全部被否,总代价是
**5 个 8 核 CPU 审计作业、最长 5 分钟**。同一套预登记判据(CI 排除 0 **且**八格同号)
在几分钟内做掉的事,过去用九对手中位要一整夜才看出来(`foreman`/`homestead` 就是那样)。
**这是把尺子换对之后第一次连续快速否证。**

## 2026-08-28 · actor-turn 构成把根找到了:**PLANT 是 0.09×(46 对 536)**,而移动 +10%、PASS +69% —— 顺带更正我自己两处算错

作业 `20705667`,day 12–29,8 seeds,同对手 k06,统计农夫+全部帮手的每一个动作:

| op | cleo | hybrid | 比 |
|---|---:|---:|---|
| **MOVE\***(NORTH/SOUTH/EAST/WEST) | 20,438 | **22,409** | **1.10×** |
| WATER | 5,248 | 2,474 | 0.47× |
| HARVEST | 2,440 | 1,251 | 0.51× |
| **PASS** | 2,386 | **4,030** | **1.69×** |
| COLLECT_FERTILIZER | 2,000 | 1,295 | 0.65× |
| FEED | 1,880 | 1,268 | 0.67× |
| CARE | 1,872 | 1,362 | 0.73× |
| **PICKUP** | 1,448 | **182** | **0.13×** |
| FERTILIZE | 776 | 282 | 0.36× |
| DROP | 640 | 158 | 0.25× |
| **PLANT** | 536 | **46** | **0.09×** |

合计:cleo total 39,896 / move 20,438 / pass 2,386 / **productive 17,072**;
hybrid total 34,996 / move 22,409 / pass 4,030 / **productive 8,557**。

**它移动得更多、PASS 得更多,而生产性动作只有一半。**
移动+PASS 占比:cleo 57%,hybrid **76%**。

### 一、根是 PLANT,不是它下游的任何一个

`PLANT 0.09×`(46 对 536)是所有生产性动作里**最大的比例缺口**,而整条链顺下来自洽:

> PLANT 0.09× → 站着的作物 24 对 56 → 可浇的水少(0.47×)、可收的少(0.51×)
> → 帮手无事可做,于是 PASS 1.69×、空走 1.10× → 不种小麦,饲料按市价买(+34,445)
> → day 12 卖 121 单位(没有可投的地方)

**所以前五次强推全部在强推 PLANT 的下游后果。** 而这也和检查清单第 (i) 条自洽:
(i) 说有余量的劳力下贪心最近近优 —— 调度没问题,**是农场没有活可派**,
因为网不创造活(不种)。

### 二、张力必须说清:`expand_crop:WHEAT` 强推的正是种植,却是 −57k

如果 PLANT 是根,为什么强推种植会亏?读完成率就明白:
`farm_phase:WHEAT` 只完成 **17–22/256**,`expand_crop:WHEAT` 只 **2–5/256** ——
**option 层根本执行不下去**。所以证据不是"种植没用",而是
**"种植不能靠 option 层外挂,必须让低层策略自己会种"** ——
这正是 `rl/TODO.md` 那条"把开局到 day 12 拆成短时域低层问题、训练闭环执行 Option"。

### 三、更正我自己两处算错(同一批测量里暴露的)

1. **"actor-turn 离上限极远"是错的。** 我拿 WATER 一项除 312 得出 8%/15%,结论说两边都
   不饱和。**实际 TOTAL 是 cleo 251–310/天、hybrid 238–254/天,即 77–99%,两边都接近饱和。**
   正确的差是 cleo 后期用 **310** 而 hybrid 只用 **241** —— 每天约 **70 个 actor-turn
   没被用掉**,与"帮手闲置 30–50%"一致。
2. **"actor-turn 花在移动上"当时没有支撑,现在有了、但方向要写准。** 第一次扩展
   `byday.py` 找的是 `MOVE`,而引擎里movement 是 **NORTH/SOUTH/EAST/WEST**,
   于是打印出 0,漏掉了**最大的动作类**(cleo 一局 3,050 次,约 44%)。改名后测出的是:
   hybrid 移动**更多**(1.10×),不是更少。**动作名要按引擎的词表取,不要按语义猜。**

### 四、下一步(标着推断)

根既然是 PLANT,而 option 层外挂已证明执行不下去,那么下一步是**训练低层去种**,
判据用行为 delta(PLANT / PICKUP 的比值)加同一套八格同号,而不是钱。
**这不是新假设,而是把 TODO 已有的那条从"该做"推进到"有量化靶子":
PLANT 要从 0.09× 抬到接近 1×,PICKUP 从 0.13× 抬起。**

## 2026-08-28 · 头健康解除了 (a) 的阻塞:**BUY_SEED 有 93% 的回合合法,它只是不买** —— 市场头不是塌缩,是**错配到卖出与买饲料**

上一条把根定在 `PLANT 0.09×`。但检查清单 (a) 要求先分清"不能种"与"不想种" ——
若 PLANT 多数回合被掩码,训练它就是训练一个被掩码的动作。作业 `20706194`
(`tools/head_health.py`,13 s)在真实对局状态上读 `hybrid-cleo12` 的导出:

| 市场家族(全部条件于该家族合法) | 中位 | 均值 | **合法率** |
|---|---:|---:|---:|
| **SELL_any** | **26.07%** | 34.95% | 83% |
| **BUY_WHEAT**(饲料) | **11.58%** | 15.19% | 90% |
| BUY_ANIMAL | 0.00% | 2.16% | 88% |
| **BUY_SEED** | **0.79%** | 7.87% | **93%** |
| HIRE | 0.00% | 9.79% | 100% |
| **BUY_LAND** | 0.00% | **0.07%** | **72%** |

`H(mkt)` 1.18,天花板 2.64。PLANT(农夫头)中位 6.5% / 均值 10.5%。

### 一、(a) 不阻塞:种子买得起、也合法

**`BUY_SEED` 的合法率是 93%** —— 不是掩码问题。它中位只有 0.79%(参照:`chisel` 是 0.02%,
所以 hybrid 比塌缩版好约 40 倍,但仍然极低)。**所以 PLANT 稀少的上游是"不买种子",
而买种子这个动作一直摆在那里。** 训练它不是训练被掩码的动作,(a) 通过。

### 二、市场头**不是塌缩,是错配** —— 这是对旧判词的修正

2026-08-23 的根因判词说"市场头塌缩"。用合法率重读:头里**有**质量,
**26% 压在卖出、11.6% 压在买饲料**,而买种子 0.79%、买地 **0.07%**(合法率 72%)。
**"塌缩"会让所有家族都趋零;实测是把质量分给了错的家族。** 这个区别决定干预:
不是"提高熵/唤醒死头",而是**把质量从 SELL/BUY_WHEAT 移向 BUY_SEED**。

### 三、三个独立仪器给出同一个故事

| 仪器 | 读数 |
|---|---|
| 逐日(`byday.py`) | day 12 买 **0** 颗种子、卖 **121** 单位(cleo 13 / 31) |
| 账本(`ledger.py`) | 饲料 **50,634**(81% 的支出);种小麦 28 对 cleo 的 68 |
| 头健康(`head_health.py`) | **BUY_WHEAT 中位 11.58%** 是第二大市场家族;BUY_SEED 0.79% |

**买饲料占掉市场头第二多的质量**,正是账本里那 +34,445。三个仪器、三种量纲、同一结论。

### 四、下一步的前提检查(尚未做,故本条不含训练臂)

`--ks-class-alpha` 的说明正对这个失效模式:*"inverse-frequency exponent; 0.5 protects
rare build/place tasks from water/idle class collapse"*。但 `--kickstart` 的教师只有
**barnyard**,而**本仓库从未测过 barnyard 是否比我们更会买种/种植** ——
我们的网对 barnyard 是 92.7–100% 胜。**在未验证教师的前提上起训练臂,
正是本轮已连续纠正五次的错误模式**,所以先测教师的动作构成,再决定锚谁。

## 2026-08-28 · 教师检查关掉 `--kickstart` 这条路,并**否掉我刚写进 TODO 的一个靶子**;真正的判别量是**每次移动换来多少生产性动作**

起训练臂前的前提检查(判词 `2858a30` 第四节)。作业 `20707017`,day 12–29,8 seeds,同对手:

| op | cleo | hybrid | **barnyard** | hyb/cleo | **barn/cleo** |
|---|---:|---:|---:|---|---|
| MOVE*(NSEW) | 20,438 | 22,409 | **25,697** | 1.10× | **1.26×** |
| WATER | 5,248 | 2,474 | 1,626 | 0.47× | **0.31×** |
| HARVEST | 2,440 | 1,251 | 622 | 0.51× | **0.25×** |
| **PASS** | 2,386 | 4,030 | **111** | 1.69× | **0.05×** |
| COLLECT_FERTILIZER | 2,000 | 1,295 | 2,170 | 0.65× | 1.08× |
| PICKUP | 1,448 | 182 | 545 | 0.13× | 0.38× |
| **FERTILIZE** | 776 | 282 | **0** | 0.36× | **0.00×** |
| PLANT | 536 | 46 | 86 | 0.09× | 0.16× |
| **productive** | **17,072** | **8,557** | **8,411** | 0.50× | **0.49×** |

### 一、barnyard 不能当这条路的教师

`--kickstart` 只接受 barnyard,而它在本条要抬的行为上**不比我们好**:
`PLANT` 只从 0.09× 到 0.16×(86 对 cleo 的 536),而 **`WATER` 0.31×、`HARVEST` 0.25×
都比 hybrid 更差**,`FERTILIZE` 是 **0** —— **而施肥恰恰是唯一实测正向的路线技能**
(+3,865,八格全正)。**朝它做类平衡 CE,会同时教"多种一点"和"完全不施肥"。**
所以 `--ks-class-alpha` 这条路对本靶子**关闭**,需要另一个机制或另一个教师。

**这次检查省下的是一条 8-link 臂(3.3 h × 16 核)。** 而它本身只花 **1m42s / 4 核**。

### 二、它否掉了我在 `cbe6c68` 里写的一个靶子:**"降低 PASS"**

我把 `PASS 1.69× → 降下来` 列成了四个靶子之一。**barnyard 是反例**:它的 PASS 是
**0.05×**(几乎从不空转),而 productive 与 hybrid **实际相同**(8,411 对 8,557)。
**所以 PASS 是症状不是杠杆** —— 可以把它压到近零而产出一点不涨。
`PASS` 从靶子列表里删掉。

### 三、真正的判别量:**productive / MOVE**

| | MOVE | productive | **productive / MOVE** |
|---|---:|---:|---:|
| **cleo** | **20,438**(三者最低) | **17,072** | **0.84** |
| hybrid | 22,409 | 8,557 | **0.38** |
| barnyard | 25,697 | 8,411 | **0.33** |

**cleo 走得最少、干得最多 —— 每走一步换来的活是我们的 2.2 倍。** 而两个弱者
(hybrid 0.38、barnyard 0.33)几乎一样。**这是整条调查里最干净的单一统计量。**

### 四、由此得到的新假设(标着推断,且**不违反 (i)**)

(i) 说有余量的劳力下贪心最近近优 —— 所以 cleo 的优势**不可能**来自"下一个目标选得更好"。
那么 `productive/MOVE` 高 2.2 倍只能来自**空间布局**:作物挤在一起,每一步移动能覆盖
更多活;而我们 24 株散在盘上,每一步只换来 0.38 个动作。

**所以候选靶子从"多种"细化为"种得密"** —— 这是一个**位置**假设,不是数量假设,
也不是调度假设,因此与前五次失败的强推、与 (i) 都不冲突。
**尚未测量**:cleo 与 hybrid 的作物空间聚集度(如已种格的平均最近邻距离)。
那是下一个该做的读数,仍然是几分钟的 CPU 作业。

## 2026-08-28 · 空间假设被否,而这个否证**把整张图收敛到一个量**:`productive/MOVE` 也是下游症状,一切都回到 `BUY_SEED`

作业 `20708041`(57 s,6 seeds),读每个日界棋盘上已种格的坐标:

| day | agent | n | **meanNN** | bbox | **density** |
|---|---|---:|---:|---:|---:|
| 12 | cleo / hybrid | 37.7 / 37.7 | 1.00 / 1.00 | 70 / 70 | 0.54 / 0.54 |
| 15 | cleo | 55.7 | **1.00** | 100 | 0.56 |
| 15 | hybrid | 27.8 | **1.01** | 44.3 | **0.64** |
| 18 | cleo | 57.3 | **1.00** | 100 | 0.57 |
| 18 | hybrid | 24.0 | **1.03** | 42.3 | **0.58** |
| 27 | cleo | 50.0 | 1.00 | 100 | 0.50 |
| 27 | hybrid | 8.5 | 1.17 | 24.0 | 0.48 |

**两边的作物都紧挨着(最近邻 ≈ 1.0),而 hybrid 的密度还略高。** day 27 的 1.17 是
n=8.5 的小样本假象。**所以 2.2 倍的 `productive/MOVE` 不来自"种得密" —— 假设否决。**

### 一、方向甚至是反的,这才是关键

hybrid 的活挤在 **42 格**里,cleo 摊在**整个 100 格**盘上。**小区域本该更省步**,
可它偏偏是 0.38 对 0.84。所以走的那些步**根本不是在作物之间走**。

### 二、算术把它解释掉了:`productive/MOVE` 是"目标太少"的下游

每个生产性动作要走几步:cleo **20,438 / 17,072 = 1.20**;hybrid **22,409 / 8,557 = 2.62**。
而两边的帮手数相当,作物数是 **57 对 24**:

| | 作物 | 每只手摊到的作物 |
|---|---:|---:|
| cleo | 57 | ≈ **4.8** |
| hybrid | 24 | ≈ **2.0** |

**一只手只摊到 2 株、每株一天浇一次水,它就没什么可干,于是把回合花在走动上。**
这与 (i) 完全一致:有余量的劳力下贪心最近近优 —— 但**当活极少时,贪心最近仍然要在
稀疏的目标之间走**,于是每个动作摊到的步数翻倍。

**所以 `productive/MOVE` 不是独立杠杆,它是"作物太少"的第三个症状** ——
和 `PASS 1.69×`(已否)、`WATER 0.47×`、`HARVEST 0.51×` 同一层。

### 三、于是整张图收敛成一条链,且只有一个头

> **`BUY_SEED`(93% 合法,中位 0.79%)→ `PLANT` 0.09× → 作物 24 对 57
> → 每手 2.0 株 → 每动作 2.62 步、`PASS` 1.69×、水 0.47×、收 0.51×
> → 不种小麦 → 饲料 +34,445 → 支出占缺口 59% → 终局 −13,051**

**今天测了七个下游量,全部自洽地指回同一个头。** 而那个头**不是塌缩、不是掩码**:
买种子一直合法(93%),市场头**有**质量 —— 26% 在卖、11.6% 在买饲料、0.79% 在买种子。

### 四、审计能做的到此为止;下一步必须改机制

**五个强推 + 两个位置/调度类解释全部被否**,而剩下的唯一目标是"让市场头去买种子"。
`--kickstart` 已关闭(教师 barnyard 的 `FERTILIZE`=0)。所以下一步不再是 8 核审计,
而是**改损失**,而且档案已经指名了机制:

> 2026-08-23 根因判词:`ClipPPOLoss` 把**一个标量** `entropy_coeff` 加在
> 14 个头的**求和熵**上(农夫 23 + 市场 31 + 12 个手头各 10,上限约 34)。
> **12 个手头就能独自满足这个 bonus,而市场头可以在同时被错配 ——
> 一个错配的头既不被损失惩罚、也不在日志里显形**(`ent` 列全程 6.45–13.49)。

**所以候选机制是"逐头的熵下限/逐头系数",而不是又一个动作或又一个奖励项。**
它不加动作(不触 (a))、不改调度(不触 (i))、不是势函数项(不触 (j)),
而且直接对着已测出的病灶:**质量错配,而非质量消失**。

**这需要改 `rl/train.py` 的损失,是今天第一次动代码而非只做测量。** 按纪律:
先写、跑 `slurm/rl_test.sh` 的门、再用 `submit_rl.py` 起 5 分钟 pilot,判据预登记为
`BUY_SEED` 中位从 0.79% 抬起 **且** `PLANT` 比值上升,而**不是**钱。

## 2026-08-28 · 逐头熵下限:**机制完全成功,策略严格变差** —— 预登记的阴性分支精确触发,而它推翻了"市场头质量错配"这个解读本身

`mktfloor-v1d` 作业 `20715030`(17 个迭代,50 分钟,CPU 16 核),`--mkt-entropy-floor 0.6`
从 `anvil` 热启动。**判词:阴性,按预登记停链。**

| it | `Hmkt` | `floor` | **win** | **money** | opp |
|---|---:|---:|---:|---:|---:|
| 0 | 1.138 | 0.2957 | **0.155** | **40,682** | 47,426 |
| 1 | 1.361 | 0.1484 | 0.001 | 25,173 | 50,861 |
| 3 | 1.517 | 0.0300 | 0.000 | 12,868 | 53,784 |
| 5 | 1.661 | **0.0000** | 0.000 | **10,248** | 55,623 |
| 10 | 1.736 | 0.0000 | 0.000 | 13,680 | 53,626 |
| 16 | **1.780** | 0.0000 | **0.000** | 16,921 | 50,767 |

### 一、机制本身是成功的,这一点要先说清

`Hmkt` 从 **1.138** 单调爬到 **1.780**,越过 `0.6 × ln(n_legal) ≈ 1.58` 的下限,
惩罚项相应从 0.2957 降到 **0.0000**(it 5 起)。**"floor 而非 bonus"的设计成立** ——
越过就松手,没有把头无休止推向均匀。代码、门、日志可见性全部按预期工作。

### 二、结果:胜率归零并保持 15 个迭代,钱腰斩

`win` 0.155 → **0.000**,此后 **15 个连续迭代都是 0.000**;`money` 40,682 → 10,248(it 5 谷底)
→ 缓慢回到 16,921,**仍不到起点的一半,远低于预登记的 35k 阈值**。
对手钱同时从 47,426 涨到 56,218。**这精确触发了预登记的阴性分支**:
"若 `Hmkt` 达约 1.58 后 `floor` 归零而 win/money 未恢复,即为'抬起了熵但抬错了家族'"。

### 三、它推翻的是**我的解读**,不是测量

`2858a30` 我把 `SELL 26% / BUY_WHEAT 11.6% / BUY_SEED 0.79%` 读成**"质量错配"**,
隐含"这个分配是病、纠正它会变好"。**本轮说明那个分配是策略自己挣来的**:
往这个头里灌熵,性能立刻严格下降,而且 17 个迭代没有恢复迹象。

**所以 `BUY_SEED` 只有 0.79% 不是"探索压力不足"** —— 训练过程本来就有机会尝试别的分配,
它收敛到了这里。**"错配"这个词要撤回,改成"在当前策略下是局部最优的分配"。**

**保留的边界**:熵下限必然在短期内损害一个接近确定性的策略,而 17 个迭代的热启动
不足以重新收敛,这是另一种可能的解释。但 money 的回升速率(11 个迭代从 10,248 到 16,921)
外推到 40,682 需要远超预算的迭代数,而 win **一次都没有离开 0.000**;
**按预登记判据,这一条判阴性。**

### 四、今天的计数

**八个假设被否**:五次强推成分(帮手/土地/维持草莓 ×2 式/买草莓种/种小麦)、
两个位置或调度解释(帮手利用率、种得密)、以及本条(逐头熵)。
**唯一没被否的是那条定位链本身**:day 12 之后 100%、饲料 +34,445、`PLANT` 0.09×、
`BUY_SEED` 93% 合法却 0.79%。

**而本条否掉的是最后一个"局部机制"候选。** 局部改一个头、一个动作、一个目标、一个布局,
八次全负 —— 这本身是一个结论:**缺口不在任何单一局部量上**,与
`GAP-2000.md §1b` 那句"需要 4–5 倍于史上最佳杠杆,或一个性质不同的干预"一致。

## 2026-08-28 · 补测把阴性判词从含糊变精确,**并打断了整条因果链**:`BUY_SEED` 涨了 **20 倍**,而 `PLANT` 塌了 **13 倍**

上一条(`c410a96`)只量到 `Hmkt` 升到 1.780 就停链,**没有量 `BUY_SEED` 本身有没有动** ——
那条阴性因此是含糊的。作业 `20721478`(39 s)导出 it-16 检查点后直接读头:

| 家族(条件于合法) | `hybrid-cleo12`(前) | **`mktfloor-it16`(后)** | 变化 |
|---|---|---|---|
| H(mkt) / 天花板 | 1.18 / 2.64 | **1.90** / 2.64 | ↑ |
| **`BUY_SEED`** | **0.79%** / 7.87% / 93% 合法 | **16.42%** / 19.89% / 82% | **↑ 20 倍** |
| **`PLANT`** | **6.5%** / 10.5% | **0.5%** / 1.1% | **↓ 13 倍** |
| `BUY_WHEAT` | 11.58% / 15.19% / 90% | **26.56%** / 27.50% / 72% | ↑ 2.3 倍 |
| `SELL_any` | 26.07% / 34.95% / 83% | 34.19% / 37.18% / 77% | ↑ |
| `BUY_LAND` | 0.00% / 0.07% / 72% | 0.03% / 0.31% / **56%** | 合法率 ↓ |
| `HIRE` | 0.00% / 9.79% / 100% | 1.58% / 10.00% / **80%** | 合法率 ↓ |

### 一、干预精确命中靶子,而目标行为反向

**`BUY_SEED` 从 0.79% 涨到 16.42%** —— 这正是预登记要抬的那个量,抬了 20 倍。
**而 `PLANT` 从 6.5% 塌到 0.5%。** 所以:

> **我假设的因果箭头 `BUY_SEED → PLANT` 是错的。买种子不导致种植。**
> 策略现在大量买种子却**更不种**,同时把更多钱花在饲料上(`BUY_WHEAT` 11.58% → 26.56%),
> 于是农场更穷,**各家族合法率全线下降**(93→82、72→56、88→69、100→80、90→72)。

### 二、这把"根"的位置往下游移了一层

今天此前的链条是:`BUY_SEED` 0.79% → `PLANT` 0.09× → 作物 24 对 57 → 其余七个下游量。
**本条切断了第一个箭头。** 正确的读法是:

> **策略在有种子的情况下依然不种。** 所以瓶颈不在市场头的采购,
> 在**农夫/帮手头的 `PLANT` 本身**。

而这也重新解释了 `expand_crop:STRAWBERRY` −40,458 与 `expand_crop:WHEAT` −57k:
它们强推的是"买种子 + 种",而**买那一半可以被执行、种那一半不能**,
于是净效果就是把钱烧在种子上 —— 与本条观察到的完全一致。

### 三、今天此前的一个测量疏漏,现在要补

`2858a30` 我用合法率解除了检查清单 (a) 的阻塞,但**我只查了 `BUY_SEED` 的合法率(93%),
没有查 `PLANT` 的合法率** —— 头健康表里 `PLANT` 属农夫头、那一列没有 legal%。
**所以 (a) 其实只对市场头验证过,对 `PLANT` 从未验证。**
若 `PLANT` 多数回合不合法,那么"训练它多种"仍然可能是在训练一个被掩码的动作。
**这是下一个必须先量的东西**,而且今天已有一个可疑的上游候选:`PICKUP` 是 **0.13×**。

### 四、判词的净效果

**逐头熵这一条仍然判阴性**(win 归零、money 腰斩),但阴性的**含义**变了:
它**不是**"多买种子有害"的证据,而是
**"把熵灌进市场头能买到种子,但买到种子不产生种植"** ——
即这条阴性只否掉了"用市场头驱动种植"这一整类手段,
**没有**否掉"让策略多种"这个目标本身。

**九个假设被否**,而这一条第一次把"根"从市场头移到了农夫/帮手头的 `PLANT`。

## 2026-08-28 · **降级今天最后两条判词的归因**:那条臂的阴性与熵下限的因果关系**未建立**,因为帮手词表 10→39 的适配本身就会打坏策略;并发现 `export_agent.py` 缺这个适配

补跑纪律 3 要求的对照时(作业 `20723435`)撞到一个更基本的问题。

### 一、`anvil` 用当前代码导出直接触发导出工具自己的哨兵

```
AssertionError: exported agent answers PASS/no-op on the opening state -- suspicious
```

**零训练、只经过帮手词表适配,`anvil` 就退化成开局 PASS。** 而 `mktfloor-it16`
(训练过 17 迭代)导出**成功** —— 说明训练部分修复了适配造成的损伤。

### 二、原因是各调用点的 `new_bias` 不一致,而导出根本没调用

| 调用点 | `new_bias` | 效果 |
|---|---|---|
| `trl_policy.py` 函数默认 | `NEG` | 压制 29 个新任务 |
| `trl_env.py:376` | `NEG` | 压制 |
| `macro_audit.py`(三处) | 默认 = `NEG` | 压制 |
| **`train.py:447`** | **`0.0`** | **不压制,新任务立刻参与竞争** |
| **`rl/export_agent.py`** | **完全没有调用** | **旧检查点导出即损坏** |

`train.py` 用 `0.0` 大概是刻意的(要让新任务可学;`NEG` 会让它们实际冻结),
但后果是:**`--init-from` 一个 08-28 之前的检查点时,训练的起点不是那个检查点的行为,
而是一个被插入 29 个中性偏置新任务后扰动过的策略。**

### 三、于是今天最后两条判词要降级

- `c410a96`("逐头熵:机制成功、策略严格变差")
- `e0a90f8`("`BUY_SEED` ↑20×、`PLANT` ↓13×,箭头被打断")

**两条的观察都成立,归因不成立。** 那条臂的 `it 0` 已经是被扰动过的 anvil,
所以 win 从 0.155 归零、`PLANT` 从 6.5% 塌到 0.5%,**同样可以由词表扩张解释**;
而 money 从 10,248 缓慢回升到 16,921 的形状,恰恰像"策略在围绕 39 个任务重新组织"。
**熵下限的贡献是未知量,不是已测量。**

**缺的对照是"anvil + 10→39 适配 + 17 迭代 + 无下限"**,而它**不能**用零训练的导出替代 ——
因为导出路径根本不做这个适配(见上)。所以这个对照必须真跑一条无下限的臂。

### 四、仍然站得住的部分,要分清

**站得住**:`PLANT` 的合法率读数 —— hybrid **30%**、arm 后 **57%**。
买种子确实让 PLANT 变合法(30% → 57%),这是两个导出之间的直接比较,
与适配无关(两者都读同一套运行时)。所以**"不能种"被排除,是"能种而不种"** 这一条成立。

**不站得住**:把 `P(PLANT|legal)` 6.5% → 0.5% 归因于熵下限。

### 五、一条基础设施缺陷(独立于本臂,影响面更大)

**`rl/export_agent.py` 缺少 `adapt_legacy_hand_head`**,而 `trl_env.py` 与 `macro_audit.py` 都有。
所以**任何 08-28 词表扩张之前的检查点(`anvil`/`chisel`/`cropper`/`longcredit`)
现在导出都会得到一个开局 PASS 的 agent**。
好消息是导出工具的哨兵会拦住它(本次就是这样发现的),**坏消息是这条路径目前不可用** ——
而"从已有检查点热启动/导出评测"正是当前训练线的默认做法。
**这是明天动任何训练臂之前必须先修的东西。**

## 2026-08-28 · 修好导出路径后,原始网的读数**更正了"能种而不种"**:`PLANT` 的**合法率只有 9–10%**,而合法时它选 **20–26%**

`rl/export_agent.py` 补上 `adapt_legacy_observation` + `adapt_legacy_hand_head(new_bias=NEG)`
后(作业 `20724025` / `20725xxx`),两个旧检查点都过了哨兵:

```
export: adapted legacy checkpoint (obs 4867 -> 5047; hands 10 -> 39, new_task_bias -1e9)
opening action: ['BUILD_PASTURE'] market [['BUY_PRODUCT','WHEAT',5]]     ← 不再是 PASS
```

### 一、忠实性有硬证据,不是"看起来对"

`chisel-fix` 的 `P(BUY_SEED|legal)` 中位是 **0.02%**,与档案 2026-08-23 记的
`nn-d0-chisel` 的 **0.02%** **完全一致**;`P(PLANT|legal)` 26.4% 对档案的 21.4% 同量级。
**旧读数被复现,所以 `NEG`(压制那 29 个未训练过的新任务)是正确的部署偏置。**

### 二、完整表,以及它更正的东西

| agent | H(mkt) | `BUY_SEED` med/mean/legal% | **`PLANT` med/mean/legal%** |
|---|---:|---|---|
| **`anvil-fix`**(原始网) | 1.10 | 0.04 / 5.45 / 91% | **20.2 / 20.1 / **10%**** |
| **`chisel-fix`**(原始网) | 1.17 | 0.02 / 5.71 / 92% | **26.4 / 25.1 / **9%**** |
| `mktfloor-it16` | 1.90 | 16.42 / 19.89 / 82% | 0.5 / 1.1 / 57% |
| `hybrid-cleo12` | 1.18 | 0.79 / 7.87 / 93% | 6.5 / 10.5 / 30% |

**上一条我据 hybrid 的"6.5% / 30% 合法"断言"能种而不种"。原始网说的不是这个:**

> **`anvil` 与 `chisel` 的 `PLANT` 合法率只有 10% 和 9%,而合法时它们选 20.2% 和 26.4%。**
> **也就是说:原始网在能种的时候是会种的 —— 绑住它的是合法率,不是意愿。**

所以**检查清单 (a) 确实触发了,但触发在基线网上,不在那条臂上**:
90% 的回合里 `PLANT` 根本不可选,那么"训练它多种"就是在训练一个多数时候被掩码的动作。
**"能种而不种"这个说法撤回。**

### 三、于是靶子第三次被改写,而这次它指向前置条件

| 读法 | 状态 |
|---|---|
| "`BUY_SEED` 0.79% 是根" | 已否(`e0a90f8`:抬 20 倍而 PLANT 塌) |
| "能种而不种" | **本条否掉** |
| **"`PLANT` 的合法率只有 9–10%,前置条件是瓶颈"** | **当前读法** |

而已有一条**实测的**因果:熵臂把 `BUY_SEED` 抬到 16.42% 后,`PLANT` 合法率从
30% 升到 **57%** —— **买种子确实是合法率的一个前置条件,而且效果很大。**
矛盾在于那条臂同时把策略打坏了(词表适配的混淆,见 `79c98d4`),所以
**"提高合法率"与"不破坏策略"目前还没有被同时做到过**。

### 四、下一步(标着推断)

原始网 9–10% 的合法率意味着还有别的前置条件没找到 —— 种子只是其一。
**要量的是:在 `PLANT` 非法的那 90% 回合里,缺的是种子、是空地、还是位置。**
这是纯读盘的测量(棋盘量,按清单 (h) 在它发生的那一刻读),不需要训练,
而它决定"提高合法率"该从哪一项下手。

### 五、修复本身的影响面

`rl/export_agent.py` 此前缺这两个适配,而 `trl_env.py` 与 `macro_audit.py` 都有。
所以**在此修复之前,任何 08-28 词表扩张前的检查点导出都会得到开局 PASS 的 agent**,
而"热启动 → 导出 → 评测"是当前训练线的默认路径。哨兵拦住了它,
**但今天此前用 `rl/out/*` 做的任何旧检查点评测都应视为可疑,须在修复后重跑。**

## 2026-08-28 · 读引擎常量排除了截止日,而这把链**重新接上**并推翻我自己那条"箭头断了"

`rl/actions.py:745` 的 `plant_ok` 是三个合取:

```python
plant_ok = (bool(s["empty"])                                   # 空地
            and any(priv["seeds"].get(c, 0) > 0                # 有种子
                    and day <= PLANT_DEADLINE[c] for c in CROP_LIST))   # 未过截止日
```

### 一、截止日被排除,代价是读一个常量

`PLANT_DEADLINE = {WHEAT: 27, CARROT: 27, TOMATO: 21, STRAWBERRY: 19, MELON: 19}`
(定义是 `29 - first_yield_day`)。整季 30 天(day 0–29),**小麦与胡萝卜到 day 27 都可种**,
即 93% 的赛季。**所以"过了截止日"不能解释 90% 的非法率。**

### 二、于是绑住的是种子,而这条链是自洽的

| agent | `BUY_SEED` 中位 | **`PLANT` 合法率** |
|---|---:|---:|
| `anvil-fix`(纯网) | **0.04%** | **10%** |
| `chisel-fix`(纯网) | 0.02% | 9% |
| `hybrid-cleo12`(cleo 前 12 天 + 网) | 0.79% | **30%** |
| `mktfloor-it16`(熵臂) | **16.42%** | **57%** |

**单调**:买种子越多,`PLANT` 的合法率越高。而 `hybrid` 的 30% 正因为 cleo 的开局替它买了种子。
**所以 `BUY_SEED → PLANT 合法率` 这个箭头是成立的,而且被四个点量到了。**

### 三、我要推翻自己的 `e0a90f8`

那条判词标题写"**箭头被打断**",依据是熵臂里 `BUY_SEED` ↑20× 而 `PLANT` ↓13×。
**那个比较用错了量**:↓13× 是 `P(PLANT | legal)`(条件概率),
而**合法率同时从 30% 升到了 57%** —— 箭头指向的正是合法率,它升了。

> **正确的读法:`BUY_SEED → PLANT 合法率` 成立(30% → 57%);
> 下降的是"给定合法时选它的概率",而那发生在一个同时被词表适配打坏的策略里
> (混淆见 `79c98d4`)。所以 `e0a90f8` 的"箭头断了"这个强断言撤回。**

同时 `3317c97` 的"合法率是瓶颈"**保留**,而且现在有了因果:
**瓶颈是合法率,而合法率的上游就是买种子。**

### 四、剩下的唯一干净实验

四个点说明"抬买种子 → 抬合法率"可行,但**唯一做到过这件事的那条臂同时把策略打坏了**,
而打坏的原因**未分离**(熵下限 vs 10→39 词表适配)。所以:

> **下一个实验是那条缺失的对照:`anvil` + 同样的适配 + 同样迭代数 + **无**下限。**
> 若它同样塌 → 混淆确认,熵下限被洗清,真正的检验要从**词表扩张之后**的检查点重做;
> 若它不塌 → 熵下限确实有害,而"抬买种子"要换别的手段。

**这条对照必须真跑**(零训练的导出替代不了,因为导出路径不做 `new_bias=0.0` 那种适配)。
**它是今天所有分支收敛到的唯一未决问题。**

## 2026-08-28 · 棋盘直读把前置条件钉在**种子**上(而且钱够、只是不买),`NO_EMPTY` 只在 day 5–11 绑;但同一次读数发现 `mktfloor` 的合法率其实是 **98.9%** —— 于是"能种而不种"回到了那条臂身上,前置条件**不再是**瓶颈

上一条(`d370fe1`)判"绑住的是种子",依据是四个 agent 的 `BUY_SEED` 与 `PLANT` 合法率
同向。那是**跨 agent 的四点相关**,而这四个 agent 在别的方面也全不一样;真正便宜的直接
测量一直没做。新工具 `tools/plant_gate.py` 按清单 (h) 在**掩码关闭的那一刻**读棋盘,
把每个非法回合唯一归入一个桶(`NO_EMPTY` / `NO_SEED` / `EXPIRED` / `BOTH` /
`MECH_DEAD`)。不需要前向,但棋盘取决于策略,所以每个 agent 跑自己的对局:
对手 `k06`、seeds `10000,10001,10002`、每回合都读,共 2,157 回合/agent。

**这是行为读数,不是性能判词**,所以不受清单 (d) 的九对手数组约束;它不产生任何名次。

### 一、直读证实了那个推断,并且比它更强:**钱不是约束**

| agent | `PLANT` 合法(回合级) | 扣掉机械死区 | `NO_SEED` 占非法 | `NO_EMPTY` | 非法时均空地 | 均持种 | 已解锁象限 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `anvil-fix`(纯网) | 26.5% | 28.4% | **55%** | 18% | **15.53** | 1.15 | 1.60 |
| `chisel-fix`(纯网) | 14.3% | 15.3% | **80%** | 12% | **17.51** | 0.23 | 1.65 |
| `hybrid-cleo12` | 46.6% | 49.9% | 50% | **0%** | 28.97 | 2.08 | 2.47 |
| `mktfloor-it16`(熵臂) | 92.4% | **98.9%** | 9% | 5% | 24.16 | **33.16** | 2.43 |

两个纯网在非法的那些回合里**平均还有 15.5–17.5 块空地**,持种只有 0.23–1.15。
所以绑住的确实是种子这一项 —— 直读,不再是相关。

而**最便宜的种子是 $10**,`NO_SEED` 回合上的均现金是 **$13,949(chisel)/$19,157(anvil)**,
**买得起的比例是 98.2% 和 99.4%**。所以:

> **不是买不起,是不买。**这与 `2858a30` 的"`BUY_SEED` 93% 合法却只有 0.02–0.79% 被选"
> 是同一件事的两侧,现在两侧都量到了。

### 二、新事实:`NO_EMPTY` 是真的,但只在 **day 5–11** 绑,机制是**从不买地**

按天分层后 `NO_EMPTY` 不是均匀的,而是**整块集中在一个七天窗口**:

| day | `anvil` 合法% | 该桶内 `NO_EMPTY` 占非法 | `chisel` 合法% | 该桶内 `NO_EMPTY` |
|---|---:|---:|---:|---:|
| 0–4 | 35.0% | 0% | 40.3% | 0% |
| **5–11** | **22.0%** | **73%** | **12.3%** | **48%** |
| 12–19 | 58.2% | 0% | 17.7% | 0% |
| 20–29 | 0.0% | 0% | 0.0% | 0% |

机制清楚:两个纯网的**已解锁象限只有 1.60–1.65(满值 4)**,开局那一块地在第 5–11 天
被填满,于是空地清零。**反例在同一张表里**:`hybrid-cleo12` 的 `NO_EMPTY` 是 **0%**,
因为 cleo 的前 12 天把象限开到 **2.47**、空地留到 **28.97**。

> **所以"抬 `BUY_SEED`"在 0–4、12–19、20–29 三个桶里是对的杠杆,在 day 5–11 里是错的
> —— 那里要的是地。**一个只动种子的干预会在这个窗口上无效,而它恰好压在建设期。

### 三、更正上一条的抬头数字:9–10% 是被**死帮手槽位**稀释出来的

`tools/head_health.py` 走 `hand_task_mask` 的全部 `MAX_HANDS=12` 行,把"有任何合法动作"
的行都计入分母;但**超出在役帮手数的行是 IDLE-only**,`PLANT` 在那里永远不合法。
于是它报的比值被 `n_hands / 12` 封顶,并把**队伍规模混进了一个合法率里**。

同 seed 10000 上对齐验证(`plant_gate` 同时打印两个分母):

| 分母 | `anvil-fix` | `chisel-fix` |
|---|---:|---:|
| 全 12 个 `MAX_HANDS` 行(= head_health) | **11.6%** | **10.5%** |
| 档案里 `3317c97` 记的 | **10%** | **9%** |
| 在役槽位 | 17.4% | 15.5% |
| **回合级(真正的合法率)** | **16.1%** | **15.9%** |

均在役帮手 8.0 / 8.1,`8/12 = 0.67`,而 `16.1% × 0.67 = 10.8%` —— **数值对上了,稀释因子
就是它**。修正幅度是 1.5 倍,**方向和结论都不变**(合法率确实低),但抬头数字应记
**回合级 14–27%**,不是 9–10%。

### 四、截止日没有被完全排除,但先要扣掉**机械死区**

`d370fe1` 用常量排除截止日,那在**赛季尺度上对**;逐日读之后要分两块:

- **`MECH_DEAD`**:`day > 27` 时任何 crop 都不可种,**完美玩家也非法**。这是 141/2,157
  = 6.5% 的回合,不算策略失败,已从"live 合法率"里剔除。
- 余下的 `EXPIRED`(有空地、有种、但持有的每种都过了自己的截止日)集中在 day 20–29:
  `anvil` 占该桶非法的 27%、`hybrid` 占 54%。机制是**买晚了错的作物**
  (STRAWBERRY/MELON 19、TOMATO 21),不是截止日太早。
- **但这一项 seed 敏感**:`anvil` 池化三 seed 是 12%,单 seed 10000 上是 **0%**。
  **按纪律只记为"在 2/3 个 seed 上出现",不作为稳定结论。**

### 五、最重要的一条:熵臂的前置条件**已经完全解决**,而它仍然严格更差

`mktfloor-it16` 的 live 合法率是 **98.9%**,剩下的非法**几乎全是 `MECH_DEAD`(86%)**,
均持种 **33.16**。而它的钱是 40,682 → **16,921**、win 0.155 → **0.000**(`train.csv`)。
配上 `head_health` 的 `P(PLANT | legal)` 中位 **0.5%**:

> **它几乎每个 live 回合都能种,而它选择不种。**
> **`3317c97` 撤回的"能种而不种"不是错的,只是挂错了对象 —— 它说的是这条臂,不是纯网。**

由此,**"合法率是瓶颈"这条现在有了上界**:合法率可以被抬到 98.9%,而钱掉了 58%。

> **所以"抬合法率"既被证明可做到,也被证明不充分。前置条件不再是瓶颈。**

同时这**不推翻** `BUY_SEED → 合法率` 那个箭头(它在四个点上仍单调,且第一节直读支持
它);被推翻的是"过了这道门就会种"。

### 六、下一步不变,但它的价值变了

唯一未决问题仍是 `d370fe1` §4 那条缺失对照:**`anvil` + 同样的 10→39 词表适配 +
同样迭代 + 无下限**。已确认仓库里**不存在**这条对照(`rl/runs/*/submission.json` 里
四个 `anvil/latest.pt` + `--multi-head` 的运行**全部**带 `--mkt-entropy-floor`)。

本次读数给它加了一个**第二读数**,让它能分离得更干净:那条臂同时发生了两件事 ——
**合法率 30%→98.9%(下限的功劳)**与 **`P(PLANT|legal)` 塌到 0.5%**。对照要回答的是
后者由谁造成:词表适配,还是下限。

**成本也变小了:塌陷在 `v1d` 的 iter 1 就发生(40,682 → 25,173),不需要 3×50 分钟的链,
一个约 30 分钟的单 link 覆盖到 iter ~8 就够判。**

## 2026-08-28 · 缺失的无下限对照跑完:**塌陷不需要熵下限就会发生** —— A 分支触发,熵下限被洗清"元凶"身份,但它是**次级放大器**;真正的元凶是从旧检查点热启动时给 29 个未训练过的头**立刻分配概率**

作业 `20727690`(run `mktfloor-ctrl`,提交 `9080478`,单 link 30 分钟 CPU,跑到 iter 9)。
= `anvil` + 同一 `granger.yaml` + 同一 seed `280828` + 同样的 10→39 词表适配 + **无**下限,
只移除 `--mkt-entropy-floor 0.6`。预登记三分支见该 run 的 `submission.json`。

### 一、lane 检查先过,所以这个比较是配对的

iter 0 读到 **money 40,682 / win 0.1553**,与 `v1c`、`v1d` **逐位相同** —— 首个 rollout
发生在任何更新之前,seed 相同。**lane 成立,可以判分支。**

### 二、A 分支按预登记判据触发

| iter | 对照 money(**无**下限) | `v1d` money(下限 0.6) | 差 | 对照 `ent` | `v1d` `ent` |
|---:|---:|---:|---:|---:|---:|
| 0 | 40,682 | 40,682 | 0 | 19.68 | 19.97 |
| **1** | **25,708** | **25,173** | **+535** | 20.31 | 20.22 |
| 2 | 20,698 | 17,280 | +3,418 | 20.24 | **17.70** |
| 3 | 18,489 | 12,868 | +5,621 | 20.13 | 17.74 |
| 4 | 16,854 | 11,170 | +5,684 | 20.36 | 18.00 |
| **5** | 17,311 | **10,248** | **+7,063** | 20.21 | 18.26 |
| 7 | 16,841 | 11,031 | +5,810 | 20.21 | 18.32 |
| 9 | 17,430 | 13,299 | +4,131 | 20.02 | 18.99 |

`win` 两条臂都是 iter 0 的 0.1553 → iter 1 起 **0.000**,十个迭代内都没回来。

预登记 A 的判据是"iter 1 的 money ≤ 30,000 且 win ≤ 0.01":**25,708 / 0.000,触发**。
而它与有下限那条只差 **535(2%)**。

> **没有熵下限,塌陷照样发生,幅度相同。所以 `c410a96` 的"逐头熵下限使策略严格变差"
> 与 `e0a90f8` 的归因都失效 —— 它们测到的是词表适配,不是下限。**

### 三、但 A 分支原文写的"熵下限无罪"太强,要就地改窄

轨迹给出了预登记没覆盖的第二个事实:**每一个 iter 2–9 上有下限那条都更低**,
谷底差 **7,063**(iter 5),而 `v1d` 要到 iter 16 才回到 16,921 —— 也就是对照在
**iter 4** 就到的水位。**下限没造成塌陷,但它把谷底压深约 40%、把恢复推迟约 12 个迭代,
并且什么也没换来。**

**机制,而且是可读的**:对照的**求和熵稳在 20.0–20.4**,有下限那条掉到 **17.7–19.0**。
**给市场头加下限,是用另外 13 个头的熵付的账。** 这正是本仓库已记过的
"一个 scalar entropy_coeff 加在 14 头求和熵上会掩盖死头"(`head_health.py` 的由来)
的**反面**:同一个求和结构,这次是被强行抬起的那一个头把别人抽干。

### 四、真正的元凶,以及它的影响面比那条臂大得多

`rl/train.py:447` 在加载 legacy 检查点时执行
`adapt_legacy_hand_head(model, new_bias=0.0)`,把 **29 个从未训练过的新帮手任务
立刻给了与已训练 logits 同量级的偏置**,即立刻可被采样。实测代价:

> **一个 PPO 迭代内:money 40,682 → 25,708(−37%),win 0.1553 → 0.000(全部);
> 十个迭代内稳定在约 17k(−58%),不恢复。**

**这不是笔误** —— `rl/export_agent.py:256` 的注释明确写着部署路径用 `NEG` 而
"train.py 是 0.0",是有意的设计选择。所以判词是:**这个选择被实测为灾难性的**,
而不是"有个 bug"。它同时**静默地污染了**任何在词表扩张之后 `--init-from` 旧检查点的臂 ——
`mktfloor` 四条全在此列,它们在第一个迭代就已经被打坏,之后测的都不是自己想测的东西。

**建议给检查清单加一条 (k)**:*给从未训练过的动作头在加载时立刻分配可采样概率,
会在一个迭代内摧毁策略且不恢复 —— 扩词表后热启动必须压制新头(`NEG`)或另给调度,
不能靠"让它探索"。* 它是 (a)("无奖励又只解锁被掩码动作=白加")的更锋利的兄弟:
(a) 说白加,(k) 说倒扣。

### 五、下一步:同形状的消融,而不是重读本臂

把训练期的 `new_bias` 从 `0.0` 改成 `NEG`(与 `trl_env.py`、与今天修好的导出路径一致),
**跑完全同形状的第三条臂**(同 config、同 seed、同 30 分钟、同 lane 检查)。

- 若塌陷消失 → **热启动被修复**,而这是本轮最大的一个杠杆,因为它不是策略假设而是
  一条被静默吞掉的基础设施缺陷;届时熵下限的真正检验才第一次可做。
- 若塌陷仍在 → 词表扩张本身(而非偏置初值)不可热启动,必须从头训练新词表,
  或只在旧 10 词表上继续。

**判据仍是配对 lane 内的 iter 0 一致性 + iter 1 的 money/win,不外推天梯(纪律 5)。**

## 2026-08-28 · 修好导出后第一次正式量四堵墙:`anvil-fix` 是 **0 胜 / 1,536 局**,margin **−65,044 ~ −71,024** —— 缺口是历史最大单杠杆的 **13 倍**,所以第 2/3 阶段的解码层不可能关掉它

作业 `20731221`(新增 `slurm/wall_eval.sh`,192 配对 seed × 双席位 = 每墙 384 局,
`OMP_NUM_THREADS=1`)。被测文件是 `rl/out/anvil-fix/main.py` —— 用**已修好的 `NEG`
导出路径**(`3317c97`)重导的 `anvil/latest.pt`,也就是提交时会真正上传的那个文件。
之所以必须重量:`3317c97` 判定修复前所有 `rl/out/*` 的旧检查点评测**一律可疑**。

| 墙 | 局数 | 胜 | 胜率 95% CI | margin | margin 95% CI |
|---|---:|---:|---|---:|---|
| `closer_cleo` | 384 | **0** | [0.0%, 1.0%] | **−65,044** | [−66,404, −63,693] |
| `ledger_lena` | 384 | **0** | [0.0%, 1.0%] | **−66,830** | [−68,335, −65,380] |
| `broker_bea` | 384 | **0** | [0.0%, 1.0%] | **−67,923** | [−69,426, −66,412] |
| `w49`(held-out) | 384 | **0** | [0.0%, 1.0%] | **−71,024** | [−72,409, −69,688] |

双席位各自 0/192,所以不是席位效应。自身钱中位 40,314(range 13,568–84,593)。

### 一、导出修复没有改变对墙的站位,而这正是该分开记的两件事

今天有两条独立的 `new_bias` 路径,**只有训练那条是坏的**:

- **导出路径**自 `3317c97` 起就是 `NEG`,所以 `anvil-fix` **从来没有被打坏过** ——
  它 0 胜不是修复前的产物,而是这条线真实的水平。
- **训练路径**到 `a83b8b2` 之前是 `0.0`,那条是坏的(见下一条判词)。

**所以"热启动修复"解除的是第 4 阶段的阻塞,它本身一分也没给对墙的战绩。**
把两者混起来读会得出"修好了就变强了"的假结论。

### 二、这把目标的可行性从推断变成算术

档案里这条线**历史最大的单一杠杆是 +5,115 钱**,而**整个解码层只值 ±2k**
(两次独立复现,记于 `measurement-traps`)。现在缺口被精确量到 **65,000–71,000**:

| 量 | 值 | 相对缺口 |
|---|---:|---:|
| 缺口(对 cleo) | **65,044** | 100% |
| 历史最大单杠杆 | 5,115 | 7.9% |
| 整个解码层的量级 | ~2,000 | **3.1%** |
| 08-27 选择性施肥(八格全正) | 3,865 | 5.9% |

> **第 2/3 阶段筛的就是解码层。即使今天两个筛选作业里出现一个全格显著正的候选,
> 按量级它也只能拿到缺口的百分之几。** 所以第 2 阶段的价值不是"关掉缺口",
> 而是"在花训练机时之前先确定解码层还有没有剩余汁水";把它当成通往 1287 的路径
> 是尺度错配 —— 这正是 `rl/TODO.md` 里那条"G1 需要的不是又一个单标志改动,
> 而是执行吞吐的量变"的量化版本。

### 三、同时它确认了 G1 的框架是对的

`hybrid-cleo12`(cleo 前 12 天 + 我们的网)本地是 **−8,011**,而我们的网**单独**
是 **−65,044**。差的那 **57,000 就是 cleo 前 12 天替我们做掉的部分**。
**所以 G1(把 −8,011 推到 ≥ 0)确实是最便宜、也最该先过的那道门**,
而"我们的网单独取胜"在当前水平下不是一个近期目标。

## 2026-08-28 · 热启动消融判 **C 分支(部分缓解)**,不是 A:`NEG` 把塌陷从 iter 1 推迟到 iter 5,然后照样塌到 **win 0.0 / money 2,913** —— 第 4 阶段仍然阻塞

作业 `20730814`(run `warmstart-neg`,提交 `a83b8b2`,单 link 30 分钟,跑到 iter 10)。
与 `mktfloor-ctrl` 逐字相同,只把新增的 `--legacy-new-bias` 从 `zero` 改成 `neg`。
训练日志确认干预生效:`adapted legacy hand head: 10 -> 39 tasks (new bias -1e9)`。

| iter | `warmstart-neg` win / money | `mktfloor-ctrl`(zero) win / money | `ent`(neg / zero) |
|---:|---|---|---|
| 0 | **0.9482 / 56,217** | 0.1553 / 40,682 | 13.86 / 19.68 |
| 1 | 0.7754 / 48,679 | 0.000 / 25,708 | 14.23 / 20.31 |
| 4 | 0.584 / 46,321 | 0.000 / 16,854 | 11.65 / 20.36 |
| **5** | **0.0137 / 31,006** | 0.000 / 17,311 | 9.70 / 20.21 |
| 8 | 0.001 / **29,938** | 0.000 / 17,047 | 9.10 / 20.02 |
| 10 | **0.000 / 2,913** | — | 6.14 / — |

### 一、按预登记的字面判据,这是 C 不是 A —— 我要就地纠正自己

A 分支写的是三个合取:`iter 1 的 money ≥ 35,000` **且** `win ≥ 0.05` **且**
`iter 1..9 不出现 ≤ 30,000 的谷`。前两项过了(48,679 / 0.7754),
**第三项在 iter 8 破了(29,938)**,而 iter 10 是 2,913。

> **所以判 C:部分缓解。`new_bias=0.0` 确实是元凶之一(iter 0 就差 15,535,
> 那发生在任何更新之前,是加载时的损伤),但压制新头只把塌陷推迟了四个迭代。
> 我在 iter 1 时说"A 分支决定性触发"是读早了,撤回。**

C 分支预登记的下一步照旧生效:**不许事后择一,下一步是给新头单独降学习率或加进入
调度,而不是重读本臂。**

### 二、iter 0 的 15,535 差值只对 barnyard 有意义,不能读成变强

`granger.yaml` 是 `opponents: barnyard`,而本仓库对 barnyard 是 92.7–100% 胜。
所以 `neg` 的 0.9482 是**策略恢复正常**,`zero` 的 0.1553 是**它被打坏**。
**这是修复一条加载路径,不是对墙的能力增益** —— 同日的四墙评测(`de303f5`)独立证实:
导出路径早已是 `NEG`,而 `anvil-fix` 仍然 0 胜 / 1,536 局。

### 三、`ent` 单调下降指向一个新嫌疑,而它不在本臂的检验范围内

`neg` 的求和熵是 13.86 → 6.14 单调下降,`pg` 在 iter 9/10 跳到 0.286/0.205。
这更像**熵塌缩 + 策略不稳**,而不是词表偏置。而两条臂共有的第二个适配是
**`adapt_legacy_observation`:4,867 → 5,047,180 个新观测维用全新权重接进已训练的躯干**。
**它在本次消融里是常量,所以本臂无法区分它** —— 记为下一个待测项,不作为结论。

## 2026-08-28 · G1 第 2 阶段(史上第一次执行)判**全阴**:23 个执行器候选**没有一个**过门,11 个显著更差,最好的点估计是 **+808** 对 65,000 的缺口

作业 `20731080`(OFAT,13 候选)与 `20731095`(2^4 全因子,16 组合),提交 `a83b8b2`,
冻结 `anvil/latest.pt`,`closer_cleo` + held-out `w49`、双席位、16 配对 seed、seed `9280828`。
读数工具新增 `tools/stage2_read.py`(候选**减基线**的配对差,按 seed 聚类 bootstrap)。

**配对一致性检查先过**:裸基线 `k01_route_s34_fert` 在两个作业里的绝对 margin
**都是 −33,926**,逐元一致,所以两作业可以合读。

| 候选(相对裸基线) | 差 | 95% CI | 八格符号 | 判 |
|---|---:|---|---:|---|
| `straw=30` | **+808** | [−249, +1,910] | 4/0 | flat |
| `batch=6` | +770 | [−2,412, +3,780] | 3/1 | flat |
| `fertmul=3.0` | +394 | [−546, +1,350] | 3/1 | flat |
| `wheatlast=27` | +209 | [−132, +518] | 4/4 | flat |
| `fertmul=2.0` | −432 | [−1,142, +218] | 0/8 | flat |
| `handmul=0.8` | −1,552 | [−4,184, +1,231] | 4/4 | flat |
| **`trip=3`** | **−5,751** | [−8,600, −2,882] | 0/4 | **worse** |
| **`trip=6`** | **−5,626** | [−9,397, −1,948] | 0/8 | **worse** |
| `handmul=0.8;trip=6` | −10,832 | [−14,613, −7,077] | 0/4 | worse |
| **`handmul=0.6`** | **−15,640** | [−19,311, −12,009] | 0/4 | worse |
| **`reserve=150`** | **−34,876** | [−38,418, −31,520] | 0/4 | worse |

**0 / 23 过门。** 预登记的阴性分支据此触发:**执行器解码层在这些轴上没有可用杠杆,
下一步转向稠密里程碑残差监督,不是继续扩轴。**

### 一、两个由诊断推出的假设被直接否掉

- **`trip`(PICKUP 合批)是本轮最直接的诊断推论 —— 而它显著更差。**
  actor-turn 构成读到"零碎 PICKUP 0.13×",我据此推断合批有利;实测每趟带 3 或 6 份
  小麦都是 −5.7k,八格全负。**"零碎 PICKUP 多"不蕴含"合批更好"** ——
  这与已确立的清单 (i)(有余量的劳力下贪心最近近优)一致:合批换来的是更长的滞留。
- **"帮手闲置 30–50% 说明人太多"也被否。** 缩编到 0.8 是 −1,552(区间含 0)、
  到 0.6 是 **−15,640**。**闲置率是症状不是杠杆**,与 `PASS` 那一行同一形状
  (`f74fecd`)。

### 二、交互没有超加性,量级上限被再次确认

全因子里每个组合都约等于其成分之和或更差(`handmul=0.8;trip=6` = −10,832 ≈
−1,552 + −5,626 − 3,654),**没有一个超加性组合**。这是"解码层不叠加"的第四次复现。
最好的点估计 **+808** 对 **65,044** 的缺口是 **1.2%**,与档案里"整个解码层只值 ±2k"
的记录同量级。

### 三、于是第 3 阶段(组合复筛)没有输入,应当跳过

第 3 阶段的定义是"存活的 3–5 个组合同场再跑一遍"。**存活数为 0,所以它无输入。**
按第 2 阶段的预登记,路线是转向 `rl/train.py` 的逐日里程碑稠密残差监督
(第 4 阶段的形式),而**那条路当前被热启动缺陷阻塞**(上一条判词判 C)。
**所以下一步的唯一入口是先解决热启动,而不是再排解码层的臂。**

## 2026-08-28 · **上一条判词被我自己推翻**:`warmstart-neg` 不是"NEG 只推迟四个迭代",而是 `NEG × kickstart CE` 产生了 **6.7×10⁸** 的损失项 —— 那条臂改了两个变量,C 分支的解读作废

读训练日志的 `ks` 列(不是 `train.csv` 里有的,要看 `logs/rl-cpu-*.out`):

| 臂 | `--legacy-new-bias` | `ks`(iter 0) | `pg` | `vf` |
|---|---|---:|---:|---:|
| `mktfloor-v1c` / `v1d` / `ctrl` | `zero` | **3.16** | 0.13–0.17 | 0.15 |
| **`warmstart-neg`** | **`neg`** | **674,440,260** | 0.09 | 0.21 |

**相差 2×10⁸ 倍。而 `pg` 是 0.09、`vf` 是 0.21 —— 也就是说那条臂的损失里,
PPO 目标在数值上完全不存在,全部是 kickstart 交叉熵。**

### 一、机制

`granger.yaml` 带 `kickstart: barnyard`、`ks_coef: 0.5`、`ks_anneal: 80e6`。
本臂到 iter 10 只走了 8.1M lane-step,所以系数整程都在 0.45–0.50,**没有退火掉**。
而 `--legacy-new-bias neg` 把 29 个新帮手任务的 logit 设成 **−1e9**。
`_kickstart_ce` 是对教师动作的掩码交叉熵,于是**每当 barnyard 的教师标签落在那 29 个
被压制的任务上,CE ≈ +1e9**。`ks ≈ 6.7e8 / 0.5` 反推出约 **67% 的教师标签落在被压制的
任务上** —— 这与 `barnyard_t` 现在输出 39 词表、其中多数是新的持久任务形式一致,
也解释了为什么这个值在各迭代间几乎不变(6.36e8–7.51e8)。

### 二、于是 C 分支的解读作废,`NEG` 没有被公平检验过

`warmstart-neg` 同时改变了两件事:(i) 新头的部署行为(**本意**),
(ii) kickstart CE 的量级,从 ~3 变成 ~6.7e8(**未预期**)。
**所以"NEG 只把塌陷推迟四个迭代"是错的读法** —— 那条臂在 iter 5 之后是被一个
1e9 量级的梯度拆掉了躯干,不是 NEG 不够。

**而 iter 0–4 才是 NEG 的真实效果**:win 0.948 → 0.584、money 56,217 → 46,321,
全程高于 `zero` 臂的任何一个迭代。**这一段没有被那个损失项污染到崩溃,
是目前关于 NEG 的最好证据,而它是正面的。**

### 三、真正的结论是一条不兼容,而它是基础设施缺陷

> **`--legacy-new-bias neg` 与 `kickstart` 在当前实现下互不兼容:
> 压制未训练任务的手段(−1e9 logit)正好是交叉熵的最坏输入。**

两条修法,记下来但都要各自过门:
1. **`_kickstart_ce` 应当把落在被压制任务上的教师标签掩掉** —— 这是正确的长期修法,
   因为"这个任务不该被部署"和"教师在这一步选了它"应该一起意味着**跳过这个样本**,
   而不是给一个天文数字的惩罚。
2. **或者 NEG 与 `--ks-coef 0` 同用** —— 零代码风险,是下一条臂要跑的那个。

**另外更正我在 `39a76f6` 里写进 `rl/TODO.md` 的一句错话**:我写"`adapt_legacy_observation`
把 180 个新维用**全新权重**接进已训练的躯干"。读代码(`trl_policy.py:464`)是
**zero-pad**:`padded[:, :old_dim] = weight`,新列是 **0**,所以它在加载时是中性的,
**不能解释 iter 0 的损伤**。这个嫌疑以读一行代码的代价被排除。

## 2026-08-28 · 2×2 判决:**`kickstart: barnyard` 是塌陷的必要条件,偏置只决定起点** —— 关掉它以后两个偏置都不塌而且都在涨,第 4 阶段解除阻塞

四格,全部同 seed `280828`、同 `granger.yaml`、同 `anvil/latest.pt`、单 link 30 分钟。
两个新格是作业 `20732913`(`neg`+`--ks-coef 0`)与 `20732526`(`zero`+`--ks-coef 0`)。
**两格的 lane 检查都逐位过**:`neg` 的 iter 0 = 56,217 / 0.9482(等于 `warmstart-neg`),
`zero` 的 iter 0 = 40,682 / 0.1553(等于 `mktfloor-ctrl`)。

| | **kickstart 开**(`ks_coef 0.5`) | **kickstart 关**(`--ks-coef 0`) |
|---|---|---|
| **`zero`** | `mktfloor-ctrl`:0.1553 → **0.000**,40,682 → 17k(塌) | `zero-ks0`:0.1553 → **0.5557**,40,682 → **48,601**(涨) |
| **`neg`** | `warmstart-neg`:`ks`=6.7e8,iter 5 起塌到 **2,913** | `neg-ks0`:0.9482 → **0.9727**,56,217 → **59,549**(涨) |

`neg-ks0` 逐迭代:`0.9482 / 0.9570 / 0.9609 / 0.9590 / 0.9541 / 0.9531 / 0.9727 /
0.9678 / 0.9585 / 0.9727`,money 单调抬到 59,549。**A 分支三个合取全过**
(iter 1..9 money ≥ 40,000、win ≥ 0.30、无 ≤ 30,000 的谷)。

### 一、预登记的第 (b) 种读法触发,而它把两个效应分开了

> **`kickstart` 是塌陷的必要条件** —— 关掉它,两个偏置都不塌。
> **偏置只决定起点(加载时的损伤)** —— iter 0 上 `neg` 是 0.9482 / 56,217,
> `zero` 是 0.1553 / 40,682,差 15,535,而那发生在任何更新之前。

**两者都是真的,而今天此前每一次归因都只看到其中一个,所以都被对方confounded。**
`zero` 的损伤是**可恢复的**(9 个迭代 0.1553 → 0.5557),`neg` 的起点则直接是健康的。

### 二、这条配方与仓库自己的判词矛盾,而矛盾持续了整条训练线

`granger.yaml` 带 `kickstart: barnyard`、`ks_coef: 0.5`、`ks_anneal: 80e6`。
而**判词 `f74fecd` 早在同日之前就判定 `--kickstart` 这条路关闭** ——
理由正是"教师只有 barnyard,而它 `FERTILIZE`=0、`WATER` 0.31×、`HARVEST` 0.25×
都比我们差,朝它做 CE 会同时教'不施肥'"。

> **判词关了这条路,配方却没关。于是每一条用 `granger.yaml` 从强检查点热启动的臂,
> 都在被一个已被判定有害的教师以系数 0.45–0.50 拉了整程(8.1M 步对 80M 退火窗口)。**

**行动项:`rl/configs/granger.yaml` 应移除 `kickstart: barnyard`**(或把 `ks_coef` 归零),
并且这个改动要走它自己的 A/B —— 本 2×2 已经是它的第一份证据。

### 三、`NEG` 与 `kickstart` 的不兼容仍然成立,且现在有了两条修法的排序

`neg` + kickstart 开 = `ks` 6.7e8(压制用的 −1e9 logit 正是交叉熵最坏的输入)。
既然 kickstart 本身该被移除,**第一修法就是移除它**;`_kickstart_ce` 掩掉被压制标签
这条(判词 `412fdf0` 记的长期修法)降级为"若将来重新引入教师时必须先做"。

### 四、对目标的意义,以及仍然没有解决的部分

**解除的**:第 4 阶段。从旧检查点热启动现在可用,而且 `neg-ks0` 在 10 个迭代里是
单调向上的 —— 这是这条线上第一次出现"热启动 + 训练不变坏"。

**没有解除的**:`opponents: barnyard`。0.9727 是对 barnyard 的胜率,而本仓库对它
本来就 92.7–100%。**四堵墙仍然是 0 胜 / 1,536 局(`de303f5`)**,而缺口是 65,044。
所以下一步不是继续对 barnyard 训练,是**把墙放进训练池** ——
`trl_env._make_opponent` 接受 `tape:` 规格(`tape_t.TapeOpponent`),
所以 `--opponents barnyard,tape:agents/bench3/closer_cleo.py` 是可行的。
(注:`rl/tensor_env/trl_pool.py` 的 docstring 说"scripted python agents 不可入池",
**这句对 tape 已经过时** —— `macro_audit` 一直在用 `tape:` 规格。)

## 2026-08-28 · 第 4 阶段两条臂都判**阴**:把墙放进训练池 29 个迭代只动了 **+532** 钱且**始终 0 胜**;而模仿锚定**与教师质量无关地有害** —— 一个比我们好 31k 的教师同样把策略打塌

三条臂,全部同 seed `280828`、同 `anvil/latest.pt`、提交 `dd561a4`。

### 一、`wallpool-cleo`(作业 `20734181→82→83`,37 迭代 / 27M lane-step):**墙入池不动**

本线第一次把强墙放进训练池(`--opponents barnyard,tape:agents/bench3/closer_cleo.py`,
`--legacy-new-bias neg --ks-coef 0`)。课程在 iter 4 推进(排除了预登记的 B 分支),
之后池按 0.5/0.5 交替采样,所以逐迭代要按 `opp_money` 分成两群读:

| 阶段 | 迭代 | money | `opp_money` | win |
|---|---|---:|---:|---:|
| cleo | 4(首次) | 43,483 | 110,822 | **0.0** |
| cleo | 33(末次) | 44,015 | 107,677 | **0.0** |
| barnyard | 36 | 59,096 | 45,865 | 0.9482 |

**cleo 阶段 29 个迭代里 money 只从 43,483 走到 44,015(+532),胜率恒为 0.0。**
**判 C 分支:课程推进了,训练也稳定,但对墙一分没动。**
→ **所以缺口不是"没见过墙"。** 这与四墙评测的 −65,044 独立一致(43,483 对 110,822 = −67,339)。

### 二、`tutor-route` vs `tutor-route-ctrl`:模仿锚定有害,而**教师质量不是原因**

单变量对照,只差 `--kickstart barnyard:k01_route_s34_fert`(教师在同场绝对 margin
**−33,926**,我们的裸网 **−65,044**,即教师好约 **31k**,是历史最大单杠杆 5,115 的六倍):

| iter | `tutor-route`(有强教师) | `tutor-route-ctrl`(无教师) |
|---:|---|---|
| 0 | 0.1553 / 40,682 | 0.1553 / 40,682 |
| 1 | **0.0029 / 28,009** | — |
| 4 | **0.0020 / 26,879** | 0.2686 / 43,336 |
| 6 | **0.0127 / 28,421** | 0.3584 / 45,411 |
| 23 | (已停) | **0.8916 / 56,882** |

**有教师的那条在一个迭代内塌到 28,009 并停在那里;无教师的那条 24 个迭代
从 0.1553 爬到 0.8916 / 56,882。** 预登记的 C 分支触发,而 C 要求先诊断 `ks` 量级:

- **`ks` = 3.139@0.50 —— 数值完全健康**(与 barnyard 教师的 3.16 同量级,
  对比 `neg` 偏置下的 6.7e8)。**所以不是数值爆炸。**
- **熵反而上升**(19.70 → 20.36),**所以也不是熵塌缩。**

> **结论:`--kickstart` 的交叉熵项与这个策略的目标本身冲突,而这与教师好坏无关。**
> `f74fecd` 当初把这条路归因于"教师只有 barnyard 且它比我们差";今天的 2×2(`dd561a4`)
> 证明 kickstart 是塌陷的必要条件;本臂再证**换成好教师照样塌**。
> **所以模仿锚定这条线可以整体关闭,而不是等一个更好的教师。**

**机制(标为推断,未测)**:策略是 14 个独立头的乘积,而 CE 是按头去匹配一个脚本的
**联合**动作。逐头对齐一个联合动作,会拆掉 RL 目标建起来的头间协同 ——
这与"解码层不叠加"是同一个形状,只是发生在损失里而不是解码里。

### 三、附带确认:`zero` 偏置的加载损伤是**可完全恢复**的

`tutor-route-ctrl` 从 0.1553 / 40,682 恢复到 **0.8916 / 56,882**(24 迭代),
接近 `neg-ks0` 的 0.9727 / 59,549(10 迭代)。
**所以 `--legacy-new-bias` 决定收敛速度,不决定天花板** ——
`neg` 的价值是省掉约 15 个迭代,不是解锁新能力。

### 四、目标状态:未达成,而三个独立角度给出同一个数

| 角度 | 读数 |
|---|---|
| `anvil-fix` 对四墙,1,536 配对局 | **0 胜**,margin −65,044 ~ −71,024 |
| 第 2 阶段 23 个执行器候选 | **0 过门**,最好点估计 +808 |
| 墙入池训练 29 个 cleo 迭代 | **0 胜**,+532 |

**缺口 65,044;历史最大单杠杆 5,115(7.9%);解码层 ~2,000(3.1%);
本轮第 2 阶段最好 808(1.2%);墙入池训练 532(0.8%)。**
**今天测过的每一种干预都在缺口的 1% 量级或以下。**

**因此:剩下的不是"再试一个干预",而是上一次复盘里唯一还没实现的那一步 ——
第 0 步的稠密里程碑残差监督(逐日株数/帮手闲置率/每株收获次数作为可测残差,
引擎当验证器),而不是奖励、不是词表、不是教师 CE、不是解码层。**
**注意本轮已经证明:朝教师做 CE 不是它的实现方式(第二节)。**

## 2026-08-28 · 最后一块拼图:**最好的脚本执行器对墙也是 0 胜(0/64)** —— 所以本仓库能构造的一切都打不过强录音,唯一能打过的是被门明确排除的第三方开环回放

顺带更正我自己一次读错:`stage2-ofat` 的 `summary.win` 是**配对差**字段,我把
`closer_cleo` seat 0 的 `delta mean +0.125` 读成了"16 局里赢 2 局"。**直接从
`records` 里数 `intervention.win > 0`:0/16、0/16、0/16、0/16 = 0/64,而基线网同样 0/64。**
`win` 那一列的 delta 不是胜局计数,不能当胜局读。

### 一、于是"谁能打过墙"这张表在本仓库内是空的

| 我们这一侧的东西 | 对四墙的绝对胜局 | margin |
|---|---:|---:|
| `anvil-fix`(RL 裸网,`NEG` 导出) | **0 / 1,536** | −65,044 ~ −71,024 |
| `k01_route_s34_fert`(**最好的脚本执行器**,Phase 1 已过门) | **0 / 64** | −33,926 |
| 第 2 阶段 23 个执行器候选 | 0 过门 | 最好 +808 |
| 墙入池训练 29 个 cleo 迭代 | **0** | +532 |
| 强教师模仿锚定 | — | 塌(−12,000) |
| `agents/champ/k01.py`(**第三方开环回放**) | **91–98% 胜** | 正 |

**唯一打得过的那一行是唯一不计入任何门的那一行**(`rl/TODO.md`「当前诊断」:
第三方开环回放不计入 G1/G2/G3),而且提交决定归用户。

### 二、这条否证也关掉了一个我刚要动手的方向

我本来准备把路线执行器冻结、只学市场头(Phase 2 的定义形态,起点比裸网好 31k)。
**它的前提是"路线执行器能赢",而这一读证明它不能** —— 路线把 margin 从 −65,044
抬到 −33,926,但**一局都没赢**。所以"冻结好执行器 + 学高层"这条路的上限也在墙外,
与 08-27 HRL pilot 的 0 提升是同一堵墙的两次读数。

### 三、由此得到的、不需要再跑臂的结论

**缺口 65,044 不是被某一个干预挡住的,而是被"我们这一侧最好的东西也差 34k"挡住的。**
换句话说:**即使把 RL 完全换成本仓库已验证的最强脚本,离赢仍有 34k。**
所以要跨过去,需要的不是"再一个干预",而是一个**在本项目里还不存在的执行器水平** ——
这是一个设计决定,不是一条可排队的臂,应当由用户在下面三条里选:

1. **改目标为 G1**(把 `hybrid-cleo12` 的 −8,011 推到 ≥ 0)—— 便宜、可判、且它隔离的
   正是"执行器是不是负资产"这个问题;cleo 的前 12 天替我们做掉了 57k。
2. **设计一个新的执行器**(不是解码标志、不是奖励项、不是教师 CE、不是词表 ——
   四类都已带复现地关闭)。
3. **部署恢复线**:`agents/champ/k01.py`。能恢复榜分,不计入任何门,**提交与否是用户的决定**。

## 2026-08-28 · **推翻我自己上一条判词**:`macro_audit` 记录里的 `win` 字段是 `None`,我把空值数成了败局 —— 路线其实是 **2/64** 不是 0/64;而把 k01 的开局交给我们的网,量出执行器**毁掉约 45,000**

上一条(`67ced8b`)写"最好的脚本执行器对墙也是 0 胜(0/64)"。**那是仪器错误,不是测量。**
`counterfactual` 路径的 `intervention.win` / `baseline.win` 是 **`None`**(不是 0、不是
False),而我数胜局用的是 `int((iv.get("win") or 0) > 0)` —— **`None or 0` = 0,于是每一条
记录都被数成败局。** 正确的胜负指示量是 **`margin > 0`**,因为 `macro_audit.py:341`
本身把 `win` 定义为 `money > opp_money`,而 `margin` 就是那个差。

**这是本会话第三次仪器读错**(前两次:`head_health` 的 `MAX_HANDS` 分母、
`summary.win` 是配对差不是胜局计数),**而这一次我已经发过判词了**,所以要就地撤回。

### 一、预登记的工具自检本来就该拦住我,而它确实拦住了

作业 `20741394` 的三个候选里,`720`(整季纯 k01)是我预登记的自检:
"必须出现胜局,否则本作业作废"。按 `win` 字段读是 **0/64**,按 `margin > 0` 读是
**61/64,mean margin +14,293** —— **与档案里 k01 对四墙 91–98% 胜完全吻合**。
**所以自检没有失败,是读法失败了。**(自检的价值正在这里:它把仪器错误逼到了台面上。)

### 二、更正后的表

| 候选 | 胜局(`margin > 0`) | mean margin |
|---|---:|---:|
| **纯 k01 整季** | **61 / 64** | **+14,293** |
| k01 前 **18** 天 → 我们的网 | **0 / 64** | −26,208 |
| k01 前 **12** 天 → 我们的网 | **0 / 64** | −31,798 |
| `k01_route_s34_fert`(脚本路线) | **2 / 64** | −33,926 |
| `...;straw=30` / `...;wheatlast=27` | **2 / 64** | −33,118 / −33,717 |
| 我们的裸网(基线 lane) | **0 / 64** | −61,342 |

**所以"我们这一侧没有任何东西赢过强墙"这句话是错的** —— 脚本路线赢 2/64。
量小,但 **G2 的字面判据是"对强墙出现非零胜局"**,而这是张量侧的读数,
**必须用官方引擎复核才能算 G2 松动**(`slurm/wall_eval.sh`,全新 seed)。
`tools/eval.py` 的 1,536 局 0 胜是**另一套 harness、真实局结果**,那一条不受本更正影响:
**裸网确实 0/1,536。**

### 三、真正的新发现:执行器把一个**必胜**的局面毁掉约 45,000

这是本项目第一次把一个**赢家**的开局交给我们的网:

> **k01 在 day 12 的局面,继续由 k01 走完是 +14,293(61/64 胜);
> 交给我们的网走完是 −31,798(0/64)。差 ≈ 46,000。**
> 交出 18 天而不是 12 天,只把它救回到 −26,208(仍 0/64)。

**这比 G1 用 cleo 量出的 −8,011 干净得多也大得多**,因为 cleo 只有 1287 分而 k01 是 2302:
**把更好的局面交给我们的网,损失更大。** 执行器不是"还不够好",是**负资产**,
而且它的破坏力随着交给它的局面变好而变大。

### 四、由此,靶子第一次有了一个可直接优化的形式

不再是"缩小 65,044 的缺口"(那是网自己从头打),而是:

> **让"k01 前 12 天 + 我们的网"从 −31,798 走向 +14,293。**
> 这是同一个棋盘、同一个对手、同一批 seed 上的配对量,而且**上界是已知可达的**
> (k01 自己走完就是 +14,293),所以它不像 65,044 那样是一个不知道能否达到的目标。

**G1 应当改用 k01 前缀而不是 cleo 前缀**:同样的门(边际贡献 ≥ 0),但信号大 5.7 倍
(46,000 对 8,011),而且它的参照是一个真正赢的对象。

## 2026-08-28 · 逐天扫前缀把执行器的破坏定位到 **day 18–24 这六天(占 52.5%)**,而 day 12–18 只占 12.1% —— 这是本条线上第一个带**已知可达上界**的六天靶子

作业 `20741985`,九个前缀档(288…672 步),同 `anvil/latest.pt`、同 seed `9280828`、
`closer_cleo` + held-out `w49`、双席位、16 lanes。胜负一律按 `margin > 0` 读(`57a5c0b`)。

| 交出步数 | day | mean margin | 胜局 | 比上一档 |
|---:|---:|---:|---:|---:|
| 288 | 12 | −31,798 | 0/64 | — |
| 336 | 14 | −32,031 | 0/64 | −233 |
| 384 | 16 | **−33,391** | 0/64 | **−1,360** |
| 432 | 18 | −26,208 | 0/64 | **+7,184** |
| 480 | 20 | −20,133 | 2/64 | +6,074 |
| 528 | 22 | −10,379 | 8/64 | +9,755 |
| 576 | 24 | −2,015 | 28/64 | +8,364 |
| 624 | 26 | **+2,915** | **48/64** | +4,930 |
| 672 | 28 | +9,347 | 61/64 | +6,432 |
| 720 | 30 | +14,293 | 61/64 | +4,946 |

### 一、预登记的 B 分支触发:损失集中在中段,而且窗口只有六天

| 窗口 | 收益 | 占全段 46,091 |
|---|---:|---:|
| day 12–18 | +5,591 | **12.1%** |
| **day 18–24** | **+24,193** | **52.5%** |
| day 24–30 | +16,308 | 35.4% |

**一半以上的破坏发生在 day 18–24 这六天。** 而且 day 12–16 那一段是**负的**
(−31,798 → −33,391):**把 day 12–16 交给 k01 反而更差**,所以那几天我们的网不是短板。

### 二、三条独立诊断在同一个窗口上重合

- `512c3fa`:边际损失 100% 产生在 day 12 之后,机制是"接手即套现"。
- Phase 0 的 critic 分时段诊断:`anvil` 的 day 20–29 explained variance 是 **−0.292**,
  而且**四个候选的最后十天全部为负** —— critic 在这一段是坏的。
- 本臂:day 18–24 占 52.5%。

**三者指向同一件事:网在赛季后段既不会估值、也不会执行,而那正是作物该被照料与收获、
不该被套现的窗口。** 这不是"再一个假设",是三个不同工具在同一个窗口上的交汇。

### 三、为什么这个靶子和之前所有靶子不同

之前的靶子都是"缩小 65,044",而 65,044 **不知道能否达到**。这个靶子是:

> **把 day 18 之后的执行从 −26,208 推向 +14,293,而上界已知可达** ——
> 同一个棋盘、同一批 seed、同一个对手上,k01 自己走完那 12 天就是 +14,293。
> **所以这是一个有天花板、有中间读数(每两天一档)、且 52.5% 的权重压在六天里的靶子。**

**并且它自带一条可判定的胜负刻度**:交到 day 24 是 28/64(44%)、day 26 是 48/64(75%)。
**也就是说这个量表上"赢一半"对应的执行水平已经被定位在 day 24–26 之间。**

### 四、诚实的界限

上表里出现胜局的那些档,**大部分工作是 k01 做的**(交出 26 天 = 全季 87%),
**所以它们不是可交付物,只是刻度**。第三方开环回放不计入任何门(`rl/TODO.md`)。
**RL 线本身仍是官方引擎 0 胜 / 1,536 局** —— 本条判词不改变那个事实,
它改变的是**下一个干预该打在哪六天**。

## 2026-08-28 · day 18–24 那六天的机制,从已有的 `byday` 读数里直接读出来:**我们的网在那个窗口里作物存量与照料动作同时下降,而 k01 两者都在上升**

不需要新作业 —— 这是把 `byday.py`(k01 对 `anvil-fix`,对手 cleo)已有的行按上一条判词
定位到的窗口重排:

| day | 站着的作物(k01 / 我们) | WATER 次数(k01 / 我们) |
|---:|---|---|
| 18 | 51 / **25** | 45 / **24** |
| 21 | 58 / **24** | 34 / **24** |
| **24** | 58 / **19** | 48 / **18** |
| 27 | 54 / 18 | 37 / 16 |

**在这六天里,我们的网:作物 25 → 19(掉 24%)、WATER 24 → 18(掉 25%)。
k01:作物 51 → 58(涨)、WATER 45 → 48(涨)。** day 24 上 WATER 是 **48 对 18,差 2.7 倍**。

**机制读法(标为推断)**:作物连续缺水会死,而清单 (e) 已确立浇水/施肥/收获是**乘性**互补。
所以这不是"少赚一点",而是**存量在缩**:照料不足 → 作物死 → 可收获的更少 → 后段收入塌。
这与 `512c3fa` 的"接手即套现"是同一现象的两个侧面 —— 资产没有被维持住。

**而这条链的上游已经被否过两次**:`productive/MOVE` 是 0.38 对 cleo 的 0.84
(每步换来的活只有 2.2 分之一),而它的空间聚集度解释已被 `0a29c02` 否掉;
调度类改动按清单 (i) 也已关闭(七个动作层标志六个被否)。
**所以"为什么每步干的活少 2.2 倍"仍然是这条线上唯一未解释的根量,
而它现在有了一个精确的表现窗口(day 18–24)和一把刻度尺(交到 day 24 是 28/64、day 26 是 48/64)。**

**本条不产生任何性能主张,也不改变 RL 线在官方引擎 0 胜 / 1,536 局的事实。**

## 2026-08-28 · 最后一条臂:去掉混淆之后,市场熵下限**在两个阶段上都更差** —— 所以 `BUY_SEED` 不是根,我提出的那条"day 0 缺种子 → 目标稀疏 → 照料塌"的因果链**被自己的干预否掉**

作业 `20742917`(run `mktfloor-clean`,3 link 中跑完第 1 个,iter 0–8 后按已判停止)。
= `wallpool-cleo` **逐字相同**(`neg` 偏置、`--ks-coef 0`、池 `barnyard`+`tape:cleo`、
同 seed `280828`、同 `anvil` 热启动),**只加 `--mkt-entropy-floor 0.6`**。
对照已跑满 37 迭代,所以这是单变量 A/B。**lane 检查过**:iter 0 = 56,217 / 0.9482,
与对照逐位相同。

| iter | 阶段 | `mktfloor-clean` | 对照 `wallpool-cleo` |
|---:|---|---|---|
| 0 | barn | 0.9482 / 56,217 | 0.9482 / 56,217 |
| 1 | barn | **0.9688 / 59,032** | 0.957 / 57,002 |
| 3 | barn | 0.666 / 49,509 | 0.959 / 57,377 |
| **4** | **CLEO** | **0.0 / 31,125** | 0.0 / **43,483** |
| 5 | CLEO | 0.0 / 32,689 | 0.0 / 42,872 |
| 6 | barn | 0.6006 / 46,974 | 0.9526 / 58,459 |
| 7 | CLEO | 0.0 / 32,475 | 0.0 / 44,246 |
| 8 | CLEO | 0.0 / 33,088 | 0.0 / 43,617 |

### 一、C 分支被排除,2×2 的归因站住

**去掉 kickstart 之后,熵下限不再塌** —— iter 1 甚至是 0.9688 / 59,032,好过对照。
所以 `dd561a4` 判"kickstart 是塌陷的必要条件"**得到独立确认**,
而 `c410a96` 当初"熵下限使策略严格变差"的**灾难性**读数确实是混淆产物。

### 二、但 B 分支触发,而且比 B 更强:它**更差**

**cleo 阶段四个读数 31,125 / 32,689 / 32,475 / 33,088,对照是 43,483 / 42,872 /
44,246 / 43,617 —— 平均低约 11,000,而且 `opp_money` 从 ~110k 涨到 ~120k
(cleo 从我们身上多赚了)。** barnyard 阶段也从 0.9688 退到 0.6006,对照始终 0.92–0.96。

> **所以"抬 `BUY_SEED`"即使在没有 kickstart 混淆的干净条件下,也不是杠杆 —— 它是负的。**

### 三、我要否掉自己上一条判词里提出的因果链

`99a516a` 末尾我把链条写成:day 0 不买种子 → day 12 只有 17 株 → 同片地上目标稀疏 →
`productive/MOVE` 0.38 → 照料不足 → day 18–24 存量缩。并据此推断
"`productive/MOVE` 是低株数的下游症状"。**本臂直接检验了这条链的源头,而它是反的**:
把种子买起来(熵下限已证能把 `PLANT` 合法率抬到 98.9%)**并没有**换来更好的后段,
反而更差。**所以低株数与低 `productive/MOVE` 之间的箭头方向未被建立,那条链撤回。**

**可能的解释(推断,未测)**:市场头把熵花在买种子上,是从**别的采购**里挪走的预算与
动作配额 —— 每回合最多 10 个市场单、`purchase_cap` 有限,而喂养要买小麦。
所以"多买种子"在固定的市场吞吐里是**零和**的,这与清单 (a)/(c) 同形:
**解锁一个动作而不扩总吞吐,只是把配额从别处搬过来。**

### 四、这条线上"便宜的干预"至此全部试完

今天按顺序否掉:解码层 23 个候选(0 过门)、墙入池训练(+532)、教师 CE(与教师质量无关地有害)、
熵下限(去混淆后仍为负)。**加上历史记录,四类干预家族全部关闭且各有复现。**
**RL 线仍是官方引擎 0 胜 / 1,536 局。** 剩下的不是干预,是**执行吞吐本身的量变**,
而它唯一确定的表现窗口是 day 18–24(占 52.5%),唯一未解释的根量是
`productive/MOVE` 0.38 对 0.84 —— 且本臂刚刚否掉了它最直觉的那个解释。

## 2026-08-29 · 把 day 18–24 那六天逐格逐手读完:**照料吞吐不是瓶颈,作物程序才是** —— 我们整季只种一种作物,而闲置的手比赢家多干的活还多

`tools/care_gate.py`(新),`closer_cleo` 对手,8 个 seed × 719 回合,我们的席位,
`rl/out/anvil-fix/main.py` 对 `agents/champ/k01.py`。k01 按纪律作为**已知阳性**同场跑
(它对四堵墙 91–98% 胜),用来验证仪器本身。

把每个回合的**每一个** `MAX_HANDS=12` 手位唯一归桶,五桶之和恒等于 `12 × 回合数`(断言)。
day 18–24 窗口:

| | `anvil-fix` | `k01` |
|---|---:|---:|
| 在役帮手 | 8.9 | **11.0** |
| 站立作物 | 21.3 | **55.4** |
| 未浇水作物 | 12.9 | 42.2 |
| `CARE_OP` 占手位 | 12.4% | **30.9%** |
| `MOVE` 占手位 | **44.0%** | **48.6%** |
| `PASS` 占手位 | **15.0%** | **1.7%** |
| `NO_CREW`(没雇) | **25.8%** | 8.3% |

同一窗口的**存量流水**(每天,`EXP_MILKED` = 持续作物榨干后自然到期,不是损失;
`EXP_UNPICKED` = 一次性作物种了却从没收,是纯浪费):

| | planted | harvested | EXP_MILKED | EXP_UNPICKED | THIRST | net |
|---|---:|---:|---:|---:|---:|---:|
| `anvil-fix` | **0.3** | **0.0** | 1.1 | 0.0 | **0.2** | **−1.1** |
| `k01` | **8.6** | **6.3** | 0.3 | 0.0 | **0.3** | **+0.4** |

**四条结论,其中两条推翻本仓库已有的判词。**

**1. `99a516a` 的机制判词是错的。** 它写的是"作物渴死,而水/肥/收乘性互补,所以存量萎缩"。
实测**渴死是 0.2/天对 k01 的 0.3/天** —— 我们比赢家**更少**渴死,无论绝对值还是按存量比
(0.9% 对 0.5%/天,分母 21.3 对 55.4)。而**每单位照料需求的照料率我们反而更高**
(1.48/12.9 = 0.115 对 3.70/42.2 = 0.088)。存量下降的唯一来源是**不补种**:
0.3/天进、1.1/天到期出。**k01 的存量能持平不是因为它照料得好,是因为它每天补 8.6 株。**

**2. `MOVE` 不是判别量,所以 `productive/MOVE` = 0.38 对 0.84 被解释了。**
两边的 `MOVE` 手位占比几乎相同(44.0% 对 48.6%,k01 还**更高**)。同样一块地上
它有 55.4 株而我们 21.3 株,所以**每一步移动够到的活只有它的一半** ——
`productive/MOVE` 是**作物密度的下游读数**,不是一个独立的病灶,也不是走路走多了。
`0a29c02` 否掉的是"我们的作物更分散"(布局),这一条说的是"我们的作物更少"(数量),两者不冲突。

**3. 物种构成把根钉死了(4 个 seed,同窗口)。**

| | 站立构成 | 整窗口发出的 `PLANT` 指令 |
|---|---|---|
| `anvil-fix` | **100% STRAWBERRY**(21.7) | **14 条,全是 STRAWBERRY** |
| `k01` | STRAWBERRY 28.0 + **WHEAT 26.2** + CARROT 1.4 | **WHEAT 224 + CARROT 20** |

**我们的草莓床(21.7)和 k01 的(28.0)是同一个量级 —— 差的整个是它并行跑的那条小麦跑步机**
(26.2 株站立,8.6/天种、6.3/天收)。草莓是 `ongoing`(种一次持续产出),小麦/胡萝卜/甜瓜是
一次性作物,**必须按时收,否则到期作废**。所以 k01 的经济是"一次性作物高周转",
我们的是"一床持续作物榨干后停摆"。**我们在 day 18–24 一株小麦都没种过。**
这与 `f083c6e` 的支出侧判词(饲料 50,634 对 16,189,"因为它不种小麦")是同一件事的两面,
第一次给出了确切的动作计数。

**4. 决定性的一条:执行器不是产能受限的,是选择受限的。**
k01 比我们**多干**的活 = `CARE_OP` 差 18.5% + `OTHER` 差 7.7% = **3.1 个手位/回合**。
我们**当场就闲着**的是 `PASS` 15.0% = **1.8 个手位/回合**(免费、立刻可用),
再加没雇的 `NO_CREW` 25.8% = 3.1 个手位/回合(要花一次 `HIRE`,而 `_hire_cost` 是
`FARM_HAND_COST_MULT × fib(hires_today)` 且**每天重置**,一天雇一个最便宜;
同期我们均现金 13.9k–19.2k)。**闲置+可雇 = 4.9 ≥ 赢家整个额外农业程序的 3.1。**
**所以"照料吞吐不足"这个框架应当退休** —— 产能一直在那儿没用。
这也解释了为什么解码层的 `trip` / `handmul` 只值 ±1%:**它们在重新分配一个并不稀缺的资源。**

**顺带排除一个假设(我今天提出并当场否掉的):动作空间的帮手上限不绑。**
`rl/actions.py:48` 的 `MAX_HANDS = 12` 是**我们自己**的界 —— 参考引擎的 `_do_hire`
(`kaggriculture.py:702`)对帮手总数**没有任何上限**,只要付得起就 append。
但两边的历史峰值都恰好是 **12**,所以这条界从未绑住我们。
08-23 缺口定位里"唯一没测的是动作空间"这一项,就帮手轴而言现已测过且为阴。

**仪器错误(本次第一处,发布前抓住):`env.steps[t].action` 是产生
`env.steps[t].observation` 的那个动作**,即在状态 `t−1` 上做的决策 —— 不是从
`observation(t)` 出发的动作。用配对的 `observation(t)` 去归因会把一切错开一个回合,
表现为**赢家 89% 的作物消失落进一个解释不了的桶**(7.3/天的 `OTHER`)。
修正后 `OTHER` 降到 1.2/天,`harvested` 从 0.3 升到 6.3。
逼出它的正是"不许留下解释不了的桶"这条纪律,和 08-28 的已知阳性规则同源。
`care_gate.py` 因此带一道**硬对齐门**:每个新变成 `PLANT` 的格子都必须有一条
`PLANT` 指令发在那个格子上,否则整个作业作废(实测 317/317 与 1572/1572 通过)。
`tools/byday.py` 用同样的配对做**逐天动作计数**,只在日界处偏一个回合,
对日聚合无实质影响,但下次改它时要知道这件事。

**尚未解释的余项(不隐藏)**:k01 窗口里还有 1.2/天的 `OTHER` 消失(占它消失量 15%)
和 d25–29 的 0.4/天;我们的是 0.0。不影响上面四条结论,但没有归因。

**这不是"再试一个干预"的邀请。** "让网种小麦"这条已经被 `9707` 那条判词以
option 形式测过并判阴(`expand_crop:WHEAT` −57k,`farm_phase:WHEAT` 完成率 17–22/256),
结论是**种植不能外挂在 option 层**。本条判词新增的不是处方,是三件事:
存量下降的机制被更正、`productive/MOVE` 被降级为下游读数、以及**产能不稀缺**这个
把"吞吐"框架整体换掉的算术。**下一步应当先量脚本路线 `k01_route_s34_fert`
(margin −33,926)在同一窗口的作物构成** —— 它的 `wheat` 目标旋钮已被测出 28 株站立,
即它**已经**有这条跑步机。若成立,65,044 的缺口就被劈成两个有名字的一半:
路线也缺的那 ~34k,和网比路线还差的那 ~31k(疑似就是这条跑步机)。

## 2026-08-29 · 根因落到一格:**我们的网整季是单一作物的草莓单作 + 6 头畜**,而赢家是草莓 + 一条小麦跑步机 + 14 头畜 —— 窗口里它握着 5.42 颗草莓种、0 颗小麦种,面前 22 块空地

接上一条判词的同一批 episode(4–8 个 seed,`closer_cleo`,`rl/out/anvil-fix/main.py`
对 `agents/champ/k01.py`)。以下**先分两类标注证据强度**,因为本仓库已经在这上面栽过三次:

**A 类 —— 棋盘/私有状态直读,可当判词用:**

| day 18–24 | `anvil-fix` | `k01` |
|---|---|---|
| 站立作物构成 | **100% STRAWBERRY**(21.7) | STRAWBERRY 28.0 + **WHEAT 26.2** + CARROT 1.4 |
| **每回合持有的种子** | **STRAWBERRY 5.42,小麦 0** | **WHEAT 8.22 + CARROT 6.97**,草莓 0.25 |
| 每回合空闲格 | **22.0** | 5.4 |
| 窗口内 `PLANT` 指令 | **14 条(全草莓)** | **244 条(小麦 224 + 胡萝卜 20)** |

| 整季动作计数 | `anvil-fix` | `k01` |
|---|---:|---:|
| `PLANT` | **41** | **199** |
| `WATER` | 511 | 972 |
| `HARVEST` | 162 | 391 |
| `PASS` | **1,556** | **542** |
| `FERTILIZE` | 28 | 57 |
| `COLLECT_FERTILIZER` | 156 | 311 |
| 畜群(day 12 / 20 / 28) | **6.0 / 6.0 / 6.2** | **14.0 / 14.0 / 14.0** |
| 化肥上限(畜·天) | 158 | 329 |

**B 类 —— 市场动作里的数字是「下单量」不是「成交量」**(检查清单 (h),逐单位锁步撮合
可能只部分成交),所以只能读方向,不能当收入:
整季 `BUY_SEED` 下单 —— 我们 STRAWBERRY 146 / MELON 37 / **WHEAT 1**;
k01 **WHEAT 580** / STRAWBERRY 136 / MELON 80 / CARROT 64。
`BUY_PRODUCT WHEAT` 下单 —— 我们 4,082,k01 1,700。

**结论一(A 类支撑):`PLANT` 0.09× 的根不是"能种而不种",是「手里没有当季该种的那种种子」。**
窗口里我们**面前有 22 块空地、手里有 5.42 颗草莓种、0 颗小麦种**。
而草莓 `first_yield_day = 10`:day 18 种下要 day 28 才首产,day 24 之后种等于作废 ——
**所以此时不种草莓是对的**,错的是**整季从没有过小麦种子**。小麦是一次性作物、
种子 $10(最便宜)、`first_yield_day = 2`、`max_yield_day = 4`,是唯一适合填赛季后段的作物。
k01 就在这七天里把 ~26 块地按 ~4 天一轮翻了 224 次。
**这把 `9080478` 的"钱够、只是不买"精确到了物种:不是不买种子,是不买小麦种子。**

**结论二:两条结构性事实就能推出全部下游读数。**
「草莓单作」+「6 头畜对 14 头」一旦成立,`CARE_OP` 12.4% 对 30.9%、
`productive/MOVE` 0.38 对 0.84、`PASS` 1,556 对 542、饲料支出 50,634 对 16,189
**全都是这两件事的算术后果**,不是四个独立病灶。畜群减半同时把化肥上限
(158 对 329)、奶/毛/蛋三条产线一起减半。

**结论三(否掉我今天自己的一个假设):化肥不是漏掉的收入线。**
两边都已经把化肥收到接近上限 —— 我们 156/158(99%)、k01 311/329(94%)。
`SELL FERTILIZER` 的下单量看着是 6,832 对 702,但那是 B 类数字,而且
**k01 的下单量远超它自己的收集量(1,708/季 对 311/季)**,所以那只是反复挂大单部分成交。
**差距在畜群数量(6 对 14),不在收集效率。** 差点把一个下单量当成收入写进判词。

**仪器纪律(本次第二处,同样在发布前抓住)**:市场动作里的数量是**下单量**。
上一条判词的对齐错误(`env.steps[t].action` 属于状态 `t−1`)和这一条,
是同一天里第二次由"某个桶解释不了"逼出来的。**A/B 分类标注应当成为此后所有
动作计数读数的默认格式。**

**这条判词与已关闭的家族不冲突,也不产生新处方。**
"让网种小麦"以 option 形式已判阴(`9707`:`expand_crop:WHEAT` −57k,完成率 17–22/256);
"抬 `BUY_SEED`"以熵下限形式已判阴(`8ec1c96`)。**但那条熵臂从未按物种拆过** ——
它把 `BUY_SEED` 抬了 20 倍而 `PLANT` 塌了 13 倍,若抬起来的是 $100 的草莓而不是 $10 的小麦,
这个组合就有了机制解释。**这是一条可检验的假设,不是判词**,需要那条臂的 rollout 才能量。

**下一步(纯读盘,不占集群)**:量脚本路线 `k01_route_s34_fert`(margin −33,926)在同一窗口
的作物构成与持种。它的 `wheat` 目标旋钮已被测出 28 株站立,即它**已经有**这条跑步机。
若成立,65,044 就劈成两半:路线也缺的 ~34k,和**网比路线还差的 ~31k = 这条跑步机**。

## 2026-08-29 · 逐作物拆开市场头,拿到本条线上最窄的一格:**每一个资本形成动作都被压到 e⁻⁹,而交易动作全部活着** —— 网学成了商人,不是农民

`tools/head_health.py --by-crop`(新增子表),`closer_cleo` 对手,seed 10000,每 3 步一个状态,
两个**不同血统**的导出 `rl/out/anvil-fix` 与 `rl/out/chisel-fix`。

**`P(BUY_SEED_<crop> | 该作物合法)`,中位/均值/合法率:**

| 窗口 | | WHEAT | CARROT | TOMATO | STRAWBERRY | MELON |
|---|---|---|---|---|---|---|
| d0–29 | `anvil-fix` | **0.00/0.00/90%** | **0.00/0.00/87%** | 0.00/0.00/62% | 2.00/10.69/50% | 0.01/3.54/51% |
| d0–29 | `chisel-fix` | **0.00/0.00/91%** | **0.00/0.00/87%** | 0.00/0.00/60% | 0.35/8.95/50% | 0.01/4.45/51% |
| d5–11 | `anvil-fix` | 0.00/0.00/93% | 0.00/0.00/86% | 0.00/0.00/62% | 18.23/23.94/57% | 0.01/0.36/59% |
| d12–17 | `anvil-fix` | **0.00/0.00/100%** | **0.00/0.00/100%** | 0.00/0.00/100% | 3.04/8.99/100% | 0.00/0.01/100% |
| **d18–24** | `anvil-fix` | **0.00/0.00/100%** | **0.00/0.00/100%** | 0.00/0.00/57% | 0.64/1.01/29% | 0.00/0.00/29% |

**小麦种子在整季 87–100% 的状态里都合法,而中位与均值都是 0.00%** —— 按本工具自己的判据
("两者都≈0 才叫死,中位≈0 而均值有值叫稀疏但可用"),它不是稀疏,是零。
胡萝卜同。**市场头实际只有草莓+甜瓜两个种子词**,与棋盘直读完全一致
(站立 100% 草莓;`BUY_SEED` 下单 草莓 146 / 甜瓜 37 / 小麦 1)。
两个不同血统的检查点给出同一图样,所以这不是某个 checkpoint 的怪癖。

**聚合掩盖了它。** 同一次读数里 `BUY_SEED` **家族**是 0.14% 中位 / 8.00% 均值 / 90% 合法,
看起来正是"稀疏但可用"。**这与 08-23 那条根因判词是同一个失效模式下移了一层**:
那次是"求和熵掩盖一个死头",这次是"**家族聚合掩盖一个活头内部的死动作**"。
`H(market)` = 1.16 对上限 2.56,读起来只是偏低,因为草莓/甜瓜/卖出把它撑住了。

**但 logit 表把结论从"一个死格"改成了更一般的东西(这才是本条的判词)。**
day 18–24 的平均 market logit,只列该状态下合法的格:

| 活着(全部是**交易**) | | 压到 e⁻⁹(全部是**资本形成**) | |
|---|---:|---|---:|
| `NOOP` | **+0.933** | `BUY_SEED_TOMATO` | **−8.439** |
| `SELL_HALF_WHEAT` | +0.609 | `BUY_SEED_CARROT` | **−8.484** |
| `BUY_FERT` | +0.204 | `BUY_SEED_WHEAT` | **−8.743** |
| `BUY_WHEAT`(买饲料) | +0.176 | `BUY_LAND` | **−9.551** |
| `SELL_WHEAT` | −0.805 | `BUY_GOOSE / SHEEP / COW` | **−10.9 … −11.3** |
| `HIRE` | −5.228(稀疏但可用,crew 确实到 8.9) | | |

**不是一个格坏了,是一整类动作被一起压下去。** 而这一类正好是我们从别处独立观测到的
每一项缺失:从不买地(已解锁象限 **1.60/4**)、畜群 **6 对 14**、整季 1 颗小麦种子、
以及**买 4,082 单位小麦成品当饲料而不是种出来**。**网学成了商人不是农民** ——
它守着开局形成的那张草莓床,此后市场头只做买卖。

**关键的反面证据,说明这不是"未训练的索引"**:五个 `BUY_SEED` 格的 bias 全在
−0.026 ~ +0.009、`|w|` 全在 0.019–0.024(输出层 `_ortho(..., 1e-4)` 初始化即近零),
而草莓 −2.373 与小麦 −8.743 相差 6.4 个 logit。**参数量级正常、方向不同 ——
所以这是学出来的判别,不是 `adapt_legacy_hand_head` 那类加载损伤。**
市场头 31 维与 `MARKET_ACTIONS` 的 31 项逐项对齐,不存在索引错位(已核)。

**它解释了两条既有的阴性判词,而不是与它们冲突:**

1. **熵下限为什么"机制成功而策略更差"(`8ec1c96` / `e0a90f8`)**:`--mkt-entropy-floor`
   floor 的是**整个市场头**的熵,而按上表,唯一活着的种子格是 **$100 的草莓**。
   抬整头熵只会把质量推给已经活着的那些格,于是 `BUY_SEED` 涨 20 倍而 `PLANT` 塌 13 倍 ——
   **买回来的是贵而慢的草莓,不是 $10 的小麦。** 上一条判词把这写成待检验假设,
   本条的逐作物读数把它变成有直接证据的解释(仍未做干预验证)。
2. **为什么解码层四次复现只值 ±2,000**:解码层重新分配的是帮手的动作,
   而缺的是**市场头的采购决策**。两者不在同一个头上。

**机制假设(明确标为假设,未测)**:shaped reward 是 `Δnet_worth`,库存按**基准价**计入
而成交按**市场价**,所以在 1.32.7 的稀缺涨价下**卖出与低价买入本身就有即时正回报**,
而买地/买畜/买种是按成本计入的**中性**动作 —— 中性动作没有梯度推力,正回报的有。
若成立,这是"为什么 PPO 会把资本形成压掉"的答案。要测的话应当直接量
市场动作与农场动作各自贡献的 shaped reward,**不要**再排一条新的奖励项臂
(奖励项家族已关闭)。

**注意本条不提供处方。** 抬 `BUY_SEED` 的整头干预已判阴;
option 层强推种植已判阴;解码层已关闭。本条给出的是**靶子的坐标**:
`MARKET_ACTIONS` 里 5 个资本形成格,在 87–100% 合法率下位于 e⁻⁹。
任何后续干预必须**逐格**而非逐头,并且要能解释为什么它不会重复 `8ec1c96` 的结果。

## 2026-08-29 · 把整个 shaping 势函数逐动作算完:**「什么都不做」的 shaped reward 严格优于每一个资本形成动作**,而作物排序被一次性计入的 PLANT 信用**倒置**了 —— 这是上一条判词那五个 e⁻⁹ 格的机制

纯读码+算术,零集群时间。先确认前提**不是过期的**:`rl/configs/granger.yaml`(当前线的配置)
写着 `potential: future`,六个配置里五个都是。所以下面这些常量是**在役**的。

`rl/tensor_env/potential_future.py` 的设计常量:`SEED_RESIDUAL=0.5`、`PLANT_CREDIT=0.5`、
`ANIMAL_CREDIT=0.4`、`HAND_VALUE=40`、`LAND_VALUE=300`、`SHED_DISCOUNT=0.9`,
shed 轴用 `base12 = base9 + [0.0]×3` —— **即棚里的牲畜按 0 计入**。
由此每个市场动作在**它发生的那一刻**的 Δφ,与实测的 day 18–24 平均 logit 并排:

| 市场动作 | 该动作瞬间的 Δφ | 实测 logit |
|---|---:|---:|
| `NOOP` | **0** | **+0.933** |
| `SELL_*`(稀缺价 > 0.9×base) | **正** | +0.61 / −0.81 |
| `BUY_FERT` / `BUY_WHEAT`(价 < 0.9×base) | **正** | +0.20 / +0.18 |
| `HIRE`(当天第 n 个) | **+40 − fib(n)** | −5.23 |
| `BUY_SEED_WHEAT` | **−5** | −8.74 |
| `BUY_SEED_CARROT` | **−10** | −8.48 |
| `BUY_SEED_TOMATO` | **−25** | −8.44 |
| `BUY_SEED_MELON` | **−40** | −9.67 |
| `BUY_SEED_STRAWBERRY` | **−50** | −2.37 |
| `BUY_LAND` | **−700 / −1700 / −3700** | −9.55 |
| `BUY_{GOOSE,COW,SHEEP}` | **−300 / −400 / −500**(棚里记 0) | −10.93 / −11.27 / −11.14 |

**符号完全分离,零例外**:每一个 Δφ ≤ 0 的动作 logit ≤ −2.37,每一个 Δφ 可正的动作
logit ≥ −0.81。**而 `NOOP` 的 Δφ 恰好是 0,logit 是全表最高的 +0.933 ——
"什么都不做"在 shaped reward 下严格优于每一个资本购买。** 这就是上一条判词
"网学成了商人不是农民"的机制:不是探索不足,是**奖励这么写的**。

**一个独立交叉验证,把这个读法钉死。** 引擎 `FARM_HAND_COST_MULT = 1`
(`kaggriculture.py:101`),所以当天第 n 个帮手只花 `fib(n)` = 1,1,2,3,5,8,13,21,34 块,
而 φ 给每个帮手记平的 40 —— **前 8 个都是正的(第 8 个 +6),第 9 个转负(40−55 = −15)**。
实测帮手数就停在 **8.9**,`NO_CREW` 25.8%。**φ 的符号翻转点和实测的停滞点在同一个数字上。**
这个数字与 08-22 归档的 `hirer` 前提逐字一致,所以那条前提是对的、而且仍在役。

**真正的新发现:作物排序被"一次性计入"倒置了。**
`PLANT` 的信用是 `expected × crop_base × 0.5`,**整笔在下种那一刻计入,不按占用格子的天数归一**
(一次性作物更是 `expected = maxy` 常量,与日期无关):

| 作物 | `PLANT` 一次性 Δφ | 占格天数 | Δφ/格·天 | **真实 $/格·天** | 市场头 |
|---|---:|---:|---:|---:|---|
| MELON | **750** | 13 | 57.7 | 109.2 | 活(整季均值 3.54%) |
| STRAWBERRY | **240** | 16 | 15.0 | 23.8 | **活(10.69%)** |
| TOMATO | 120 | 11 | 10.9 | 17.3 | **死(0.00/0.00)** |
| WHEAT | **75** | 5 | 15.0 | **28.0** | **死(0.00/0.00)** |
| CARROT | **70** | 4 | 17.5 | **30.0** | **死(0.00/0.00)** |

**活着的两个种子恰好是一次性信用最大的两个,死掉的三个恰好是最小的三个,零例外。**
而按**真实每格每天收益**,CARROT(30.0)与 WHEAT(28.0)是第 2、第 3 名,
**都高于网唯一在种的 STRAWBERRY(23.8)**。
**势函数按"每株总价值"排序,而游戏按"每格每天价值"付钱。** 一次性形式让草莓看起来
比小麦好 3.2 倍(240 对 75),而小麦真实收益反而高 18%,并且 5 天就把格子腾出来能再种一轮。
**这是"草莓单作"和"整季 0 颗小麦种子"的精确成因,也是检查清单 (j) 的字面重演。**

**还有一层:成本记在市场头,收益记在帮手头。**
`BUY_SEED` 是市场动作、恒付 −0.5×种子价;`PLANT` 是帮手动作、独收那整笔一次性信用。
`BUY_ANIMAL` 是市场动作、棚里记 0 所以恒付 −成本;`BUILD`/`PLACE`/`FEED` 是帮手动作、
独收 `ANIMAL_CREDIT` 那一笔。**逐头独立 categorical 下,被扣钱的那个头正是要做决定的那个头。**

**这条判词不为"抬信用"背书 —— 那个处方已经判阴。** `furrow`(`--land-value 5000`)
跑过并判阴("买了地却留下更多空地,直接抬资产信用的处方被否",旧 TODO 收口表)。
而且现存的信用旋钮只剩 `--fert-credit` 与 `--land-value` 两个,
`--hand-value` / `--seed-credit` 在 08-24 清理 worktree 时随之消失。
**一次性 vs 按天归一这个缺陷根本没有旋钮**,所以它不是"再调一个信用值",
而是改一个既有项的**时间归一化** —— 与"奖励项"这个已关闭家族相邻,
因此必须靠算术论证并预登记,不能靠期望。

### 预登记:`potential networth` 单变量对照(提交前写下,不得事后改)

**不需要任何新代码。** `net_worth_t` 恰好一次性修掉上面全部五处:地按**全价**计入
(`_LAND_CUM = sum(LAND_PRICES[:k])`,买地变中性)、牲畜按**成本**计入、种子按**全价**计入
(买种变中性)、作物按 `seed_cost + yu × crop_base` 即**已实现产量逐步累积**(不再是一次性)。
所以它是"势函数到底是不是抑制资本形成的原因"的**决定性检验**,而不是又一个旋钮。

- **臂**:`--config rl/configs/granger.yaml --ks-coef 0 --potential networth`
- **对照**:已在盘上的 `zero-ks0`(同配置、`--ks-coef 0`、`potential: future`)。
  `--ks-coef 0` 两边都开,因为 `kickstart: barnyard` 已被 `dd561a4` 证明是热启动塌陷的
  **必要条件**,不关掉它这条臂会因为一个已知原因塌掉、什么也测不出。
- **lane 检查(硬门)**:iter 0 是更新前评估,只反映策略不反映奖励,所以必须逐位读到
  **40,682 / 0.1553**。读不到就作废,不解释任何后续数字。
- **主读数**:导出后 `head_health.py --by-crop 18-24` 的 `P(BUY_SEED_WHEAT|legal)`
  与 `P(BUY_LAND|legal)`,加 `care_gate.py` 的窗口站立作物构成。
- **A 分支(机制成立)**:到 iter 8,`P(BUY_SEED_WHEAT|legal)` 均值 **> 1%**(现 0.00%)
  **或** day 18–24 站立小麦 **> 5 株**(现 0)。
- **B 分支(机制被否)**:小麦种子概率仍 **< 0.1%** 且站立小麦仍 **< 2 株** →
  **势函数不是抑制资本形成的原因,本条判词的机制主张必须撤回。**
- **C 分支**:钱/胜率动了但作物构成没动 → 记录,**不得归因于本机制**。
- **明确不预测钱会涨。** `networth` 去掉了 `future` 的长程信用,可能让整体更差;
  本对照测的是**动作分布**,不是 margin。用钱来判它就是重犯"用错的尺子验收"。

## 2026-08-29 · 预登记的 B 分支触发:**换势函数没有让作物程序动一毫米** —— 所以我上一条判词的机制主张按预登记撤回

作业 `20765706`(提交 `411afad`),`granger.yaml --ks-coef 0 --potential networth`,
与已在盘的对照 `warmstart-zero-ks0` **逐字相同**、只差这一个 flag。CPU 单 link,
跑到 iter 9(在预登记的判定点 iter 8 之后)按纪律 `scancel` 释放集群,重扫无残留依赖。

**lane 硬门逐位通过**:iter 0 = **40,682 / 0.1553**,与对照逐位相同。所以这条臂有效。

**主读数(预登记的那个,不是钱):**

| | `P(BUY_SEED_WHEAT|legal)` d18–24 | d18–24 站立作物构成 | 窗口 `PLANT` 指令 | 整季 `BUY_SEED` 下单(B 类) |
|---|---|---|---|---|
| `nw-it8`(networth) | **0.00 中位 / 0.01% 均值** | **STRAWBERRY 21.4,小麦 0** | **NONE** | 草莓 127 / 甜瓜 36 / **小麦 0** |
| `anvil-fix`(future) | 0.00 / 0.00% | STRAWBERRY 21.7,小麦 0 | 草莓 13 | 草莓 146 / 甜瓜 37 / 小麦 1 |

**A 分支的两个判据都没到**(要 > 1% 或站立小麦 > 5):小麦种子概率 0.01% < 0.1%,
站立小麦 0 < 2。**B 分支按字面触发。**

### 因此撤回 `411afad` 的机制主张

把地/畜/种从"按 0.5 折或 300 计入"改成"按成本计入"(买入从负变中性)、
把作物从"一次性计入期望值"改成"按已实现产量逐步累积" —— **五处缺陷一次性全修,
而作物程序一毫米都没动。** 所以那五个 e⁻⁹ 格的成因**不是**势函数的 Δφ 符号。

**分清撤回什么、保留什么:**

- **保留(是代码事实,不受本对照影响)**:Δφ 逐动作表本身;`NOOP` 的 Δφ 恰好为 0 而它的
  logit 是全表最高;以及**一次性信用把作物排序倒置**这个缺陷确实存在
  (甜瓜一次性 750 / 草莓 240 / 小麦 75,而真实每格每天是甜瓜 109.2 / **小麦 28.0** /
  草莓 23.8 —— 势函数说草莓比小麦好 3.2 倍,实际小麦高 18%)。**这仍然是个应当修的缺陷,
  只是它不是这个症状的原因。**
- **撤回**:上述任何一项**导致**了资本形成被压制;以及"修势函数"是一个杠杆。
- **降级为可能是巧合**:那个我当作交叉验证写进去的 `HIRE` 巧合
  (`FARM_HAND_COST_MULT=1` → 第 9 个帮手 Δφ 转负 −15,而实测帮手数停在 8.9)。
  **不得再作为该机制的证据引用。**

**阴性的适用范围要说准:** 被否掉的是"**从热启动开始、换势函数能在 8–9 个迭代内
重定向作物程序**"。**没有**被否的是"从零训练时,势函数最初造成了这个单作" ——
那需要一条 from-scratch 的臂,昂贵,未测。**功效检查:这不是一条没跑动的臂** ——
它的策略确实在动(win 0.1553 → 0.2949,9 个迭代),只是动的时候完全没碰作物程序。
所以这是一个有效的阴性,不是样本不足。

**次要读数(预登记里明说不作判据,只记录):** `networth` 在每一个迭代上都比 `future`
对照差 —— iter 9 是 win **0.2949 对 0.5557**、money **44,251 对 48,601**。
所以它也不是白拿的便宜。**不归因、不外推天梯(纪律 5)。**

### 这条阴性留下的有用残渣:一个张力

按 0.01% 的密度乘每迭代 **736,256** 个市场决策,小麦种子在训练里**每迭代仍被采样约 70 次** ——
**稀薄,但不是从不。** 所以两个现成的故事都不完整:
不是"从没被探索到"(它被采样了),也不是"奖励禁止它"(奖励的符号结构刚被改过、没用)。
在 1e-4 的采样密度下,那几十个样本的梯度信号被埋在 736k 个样本里。

**下一个候选(记录,未跑)**:把干预从**逐头**改成**逐格** —— 直接抬那五个资本形成格的
采样密度,而不是 floor 整个市场头的熵(整头版已判阴且已被 `6e2b2c2` 解释:
唯一活着的种子格是 $100 的草莓,抬整头熵只会买更多草莓)。
它与已关闭的"解码层标志"家族相邻,所以必须先用算术论证并预登记;
而且本条判词给了它一个硬约束:**它必须把 1e-4 的采样密度抬高若干个数量级才可能有意义**,
否则就是又一个 ±1% 的臂。**在那个算术做出来之前不要排这条臂。**

**本节不影响今天前三条判词** —— `3dac7f5`(产能不稀缺)、`74c093a`(草莓单作 + 0 颗小麦种)、
`6e2b2c2`(五个 e⁻⁹ 格、家族聚合掩盖死动作)都是直接测量,与机制解释无关,全部照旧成立。

## 2026-08-29 · 脚本路线在同一窗口**确实跑着那条小麦跑步机**(站立小麦 25.6),所以"网缺的那一半"有了名字 —— 但缺口的两半分割**不能当实测引用**,因为三个数字来自三种仪器

纯读盘,张量侧,8 lanes、整季 720 步,player 0 = `tape:agents/bench3/closer_cleo.py`,
player 1 = `barnyard_t.BarnyardOpponent(<profile>)`。day 18–24 窗口读 player 1 的棋盘:

| d18–24 | 站立作物构成 | 持种/回合 | 帮手/回合 | 象限/回合 | 终局钱(p1 对 p0) |
|---|---|---|---|---|---|
| `k01_route_s34_fert` | STRAWBERRY 28.0 + **WHEAT 25.6** | 草莓 4.62 + **小麦 1.75** | **11.2** | **2.00** | 63,977 对 84,175 |
| `k01_route_s34` | STRAWBERRY 27.5 + **WHEAT 25.4** | 草莓 5.38 + **小麦 1.66** | 11.2 | 2.00 | 62,634 对 87,082 |
| (对比)`k01` 官方引擎 | STRAWBERRY 28.0 + **WHEAT 26.2** + CARROT 1.4 | 小麦 8.22 + 胡萝卜 6.97 | 11.0 | — | — |
| (对比)`anvil-fix` 官方引擎 | **STRAWBERRY 21.7,小麦 0** | **草莓 5.42,小麦 0** | **8.9** | **1.60** | — |

**结构性事实(稳健,不是仪器伪影)**:本仓库**已经能执行**那条跑步机 ——
脚本路线的站立小麦 25.6 与 k01 的 26.2 同量级,帮手 11.2 对 11.0,象限 2.00。
**而我们学出来的策略是 0 株小麦、8.9 个帮手、1.60 个象限。**
所以"小麦跑步机"不是一个本项目达不到的能力,它是**专门从学出来的策略里缺失**的。
`fert` 与不带 `fert` 只差 +1,343(63,977 对 62,634),方向与 `20642095` 的 +3,865 一致。

**必须说清的限制:缺口的两半分割是跨仪器推断,不得当实测引用。**
−65,044 来自官方引擎 `tools/eval.py`(四墙、1,536 配对局);−33,926 来自 `macro_audit`
张量侧;本条的 −20,198 是第三种(张量、cleo 磁带、8 lanes)。**三条不同的评估路径,
按纪律 5 与「同一评估路径才能相减」不能直接作差。** 要把"路线也缺的 ~34k / 网比路线还差的
~31k"变成实测,需要**给路线做一个官方引擎的导出**并跑同一个 `slurm/wall_eval.sh` ——
路线目前只以 `barnyard_t` profile 的形式存在,没有导出 agent。**这是一条具体的后续,
不是本条判词的结论。**

**另注**:这里的 cleo 是 `tape_t.TapeOpponent` 重放 `_TRACE`(公开 meta 的田间计划),
不含 `closer_cleo.py` 自己那层市场/SELL 调度器。它是训练池一直在用的那个张量侧 cleo,
但**不等于官方引擎里的完整 cleo**,读绝对钱数时要记得这一点。

### 预登记:`--fixed-market-profile` —— 把采购交给一个证明会买的程序,只学农场执行

**这个标志在 `rl/train.py:241` 已经存在,而整个档案里从未有任何一条 run 用过它**
(按检查清单 (k) 已 grep `docs/RUNS.md` / `rl/TODO.md` / 全部 `rl/runs/*/submission.json`)。
语义:"state-closed barnyard profile 接管学习者席位的市场队列,PPO 只学 farmer/hand 执行;
**市场头被掩成 NOOP**"。

**为什么它不属于任何已关闭家族**:不是解码层标志(不改帮手动作的解码)、不是奖励项
(奖励完全不动)、不是教师 CE(没有任何 CE 项,`--ks-coef 0`)、不是词表。
它是 **Phase 2 的"冻结一半、学另一半"模式,施加在缺陷真正所在的那个头上** ——
今天测出来的五个 e⁻⁹ 格全部在市场头,而这条臂**直接绕过它们**。

**与已做过的 farm-only / market-only scope 消融不同**:那次(`20527366` 一带)是拿**脚本
执行器**对**冻结的网**做反事实审计,结论是两个 scope 单独都不过门、只有联合整季控制为正。
**那次没有训练任何东西。** 这条臂是在市场程序被写死的前提下**训练**农场侧。

- **臂**:`--config granger.yaml --ks-coef 0 --fixed-market-profile k01_route_s34_fert`,
  其余与 `warmstart-zero-ks0` 逐字相同(`--init-from rl/runs/anvil/latest.pt`、
  `--legacy-new-bias zero`、`--multi-head`、`--hidden 1024 512`、`--v-hidden 512`、seed 280828)。
- **对照**:已在盘的 `warmstart-zero-ks0`(iter 8 = win 0.4951 / money 46,300)。
- **lane 检查换形式**:市场头从 step 0 就被掩成 NOOP,所以 iter 0 **不会**等于 40,682 ——
  用逐位相同当门在这里是错的。改用**机械有效性门**:导出后 day 18–24 的**站立小麦必须 > 10**。
  读不到就说明那个 profile 没真的在驱动采购,整条作废、不解释任何数字。
- **本条的主读数是钱和胜率,而这是有理由的**:这条干预不改奖励,而是把一个决策者换成
  一个已证明更好的程序。所以"农场侧能否用上一个能工作的采购程序"就是钱。
  (仍不外推天梯 —— 纪律 5。)
- **A 分支(市场头就是绑住的那一项)**:iter 8 money **≥ 55,000**(对照 46,300,+19%)
  **且**站立小麦 > 10。
- **B 分支(不是)**:iter 8 money **≤ 48,000**(对照的 +3.7% 以内)→
  **市场头不是绑住的那一项,农场侧拿到一个能工作的采购程序也用不上。**
  这会反过来削弱今天第三条判词的含义,必须照实记。
- **C 分支**:48,000–55,000 之间 → 未决,记录,不得归因。

### 2026-08-29 · 对上面那条预登记的**修正(读结果之前写的,只收窄结论,不放宽)**:`--fixed-market-profile` 不是单变量

读 `rl/tensor_env/trl_env.py:777-793`(检查清单 (g):压在某机制上的臂,提交后回去读那段代码)。
它把 `("m_op", "m_item", "m_rem")` **整条市场队列**交给 profile —— **包含 SELL,不只是采购**。

**这与今天的 `6e2b2c2` 撞上了**:那条判词测出我们的网**卖出那一侧是活的**
(`SELL_HALF_WHEAT` +0.609 是全表第二高,`SELL_WHEAT` −0.805,`BUY_WHEAT` +0.176),
死掉的只有资本形成那五格。**所以这条臂替换掉的东西里,既有坏的采购,也有可能是好的卖出。**

还有第三条通道:**市场干扰**。iter 0 的对手钱是 **46,314**,而对照是 **47,426** ——
换了市场队列以后**对手也少赚了 1,100**,说明我们的挂单在压同一个共享价格
(本文件「Can we interfere with the market?」那一节测过这条通道)。
所以 `win` 上升(0.1904 对 0.1553)有一部分来自**对手变差**,不是我们变好。

**因此把这条臂的判读能力按不对称收窄,现在就写死:**

- **A 分支仍然可读**:如果钱在**可能更差的卖出**之下还涨了 19%,那采购就是绑住的那一项。
  A 成立是稳健的(干扰只会让它更难成立)。
- **B 分支不再可读为"市场头不是绑住的那一项"**。B 会在两个解释之间**歧义**:
  (i) 采购确实不是约束;(ii) 路线的卖出比我们差,把采购的收益吃掉了。
  **B 只能记成"整条市场队列交给路线不划算",不得写成任何关于采购的结论。**
- **要隔离它需要一个 buy-only 的 scope,而代码里没有** ——
  `scope all|farm|market` 那个切分属于 `barnyard_prefix`(另一套机制),
  `--fixed-market-profile` 没有 scope 参数。**若 B 触发,这就是下一步的具体工作。**

**早期数字(iter 0–2,明确不是判词,判定点在 iter 8)**:钱 39,195 / 39,631 / 39,845
**低于**对照的 40,682 / 40,803 / 42,052,而 win 0.1904 / 0.2168 / 0.2021 **高于**
对照的 0.1553 / 0.1631 / 0.1924,对手钱 46,314 / 46,272 / 46,915 **低于** 47,426 / 47,261 / 47,488。
**钱和 win 的方向相反,而这正是上面第三条通道的样子。**

**为什么这算合规的修正而不是事后改预登记**:它**只收窄**能得出的结论(把 B 从一个
机制结论降级为一个成本结论),不放宽任何阈值,阈值一个字没动,而且写在读 iter 8 之前。
`79c98d4` 那次是**事后**才发现臂被混淆并降级归因;这次是事前。

## 2026-08-29 · `--fixed-market-profile` 判 **B 分支**,但它交出两件更重要的东西:**这个标志产出的检查点无法部署**,以及**保证了种子供应之后帮手反而更不种了**(第二次出现同一形状)

作业 `20767496`(5 min pilot)→ `20767497`(30 min,afterok),提交 `293a530`,跑到 iter 8。
两条都过 preflight,链尾正常结束,队列已空,无残留依赖。

**主读数(预登记):iter 8**

| | 臂 `fixmkt-route` | 对照 `warmstart-zero-ks0` |
|---|---:|---:|
| win | **0.4023** | **0.4951** |
| money | **44,410** | **46,300** |
| opp money | 46,638 | 46,106 |

`44,410 ≤ 48,000`,**B 分支按字面触发**;而且它在**两个指标上都低于对照**。
早期 iter 0–3 臂的 win 曾高于对照(0.19/0.22/0.20/0.25 对 0.16/0.16/0.19/0.21),
到 iter 8 被对照反超。

**按 `67db2e0` 那条读结果之前写下的修正,B 只能记成:「把整条市场队列交给路线不划算」** ——
不得写成任何关于采购的结论,因为该标志同时替换了 SELL(而我们的卖出侧是活的),
并且存在市场干扰通道。**这个限制是事前写的,现在照它执行。**

### 一、我那道机械有效性门**不可执行**,而查清原因比这条臂的结果更重要

我预登记的门是"导出后 day 18–24 站立小麦 > 10"。**它执行不了,而且不是操作失误,
是这个标志的结构性性质**:`--fixed-market-profile` 把市场头**整个训练期掩成 NOOP**
(`trl_env.py:777`),所以它**从头到尾没有收到任何梯度**;
而 `rl/export_agent.py` 导出时把市场决策**交还给那个从未训练过的头**。

实测这个代价(4 个 seed、官方引擎、对 cleo):

| 导出 | 站立构成 d18–24 | 窗口 `PLANT` | 整季 `BUY_SEED` 下单 | 终局钱 |
|---|---|---|---|---|
| `fm-it8`(本臂 iter 8) | STRAWBERRY 19.9,小麦 0 | **NONE** | 草莓 124 / 甜瓜 40 | **34,321** |
| `anvil-fix`(基线) | STRAWBERRY 21.7,小麦 0 | 草莓 13 | 草莓 146 / 甜瓜 37 / 小麦 1 | **51,058** |

**34,321 对 51,058,−33%,而这个损失完全由导出路径造成,不是训练造成的。**
所以**即使 A 分支成立,产物也无法交付** —— 它需要把那个脚本市场程序一起发出去,
而 agent 契约(`main.py` + `weights.npz`,`tools/package.sh` 只打 `*.py` 与 `*.npz`)
没有承载它的位置。**这与 08-28 的 `new_bias` / `kickstart` 是同一类:
一个标志的结果到不了部署。** 已写进 `rl/TODO.md`,避免有人再跑它并期待一个可部署产物。

### 二、混淆**碰不到**的那个干净子结果:保证了种子,帮手反而更不种

`P(PLANT | legal)` **逐帮手**(`head_health.py`,同 seed 同对手):

| | med / mean / legal% |
|---|---|
| `anvil-fix`(训练前) | **10.6 / 13.7 / 27%** |
| `fm-it8`(8 个迭代,采购由路线保证) | **7.0 / 9.0 / 28%** |

**帮手任务头与市场头是两个不同的头,SELL 的替换和市场干扰都到不了它** ——
所以这个读数不受 `67db2e0` 那条修正的限制。
**在一个每天都会买对种子的程序供货 8 个迭代之后,帮手选择 `PLANT` 的概率从 10.6% 掉到 7.0%。**
合法率没变(27% → 28%),所以不是掩码变了。

**这是同一形状的第二次出现,所以它不再是巧合:**

| 干预 | 对种子供应 | `PLANT` 的反应 |
|---|---|---|
| `e0a90f8` / `8ec1c96` 市场熵下限 | `BUY_SEED` **涨 20 倍** | **塌 13 倍** |
| 本臂 `--fixed-market-profile` | 采购**由已证明会买的程序接管** | **10.6% → 7.0%** |

**两次独立地保证种子供应,`PLANT` 两次都往下走。** 所以**市场头不是唯一的锁**:
**帮手头的 `PLANT` 选择也不是被种子约束的。** 由此
**「只要让它买小麦」这个计划应当退休** —— 两把锁,单独开任何一把都无效。
这也终于给 `8ec1c96` 那个当时无法解释的组合(种子涨而种植塌)配上了第二个实例。

**这留下的是一个问题,不是一个处方**:**为什么保证种子供应会让 `PLANT` 概率下降?**
不要在回答它之前排任何抬 `PLANT` 或抬 `BUY_SEED` 的臂 —— 那两条路各自都已有两次阴性。
可查的方向(纯读盘,未做):`hand_task_mask` 里 `PLANT` 与照料类任务的竞争关系,
以及 `PLANT` 在 `HAND_TASKS` 里被哪些任务抢走概率质量(逐任务读,不看求和熵 ——
求和熵掩盖死头这条本仓库已经栽过一次)。

## 2026-08-29 · **撤回我自己上一条判词的"两把锁"结论**:`PLANT` 的下降是 10→39 词表稀释,不是种子效应 —— 而正确的读法是反过来的:**只有一把锁,在上游的市场头**

`tools/head_health.py --by-task`(新增子表),逐帮手任务读概率质量,只算**在役**帮手槽位,
同 seed 同对手,day 18–24。上一条判词(`8db606f`)拿 `P(PLANT|legal)` 从 10.6% 掉到 7.0%
当作"保证种子供应反而更不种"的干净子结果。**逐任务读之后它站不住。**

| 任务 | `anvil-fix` mean% / legal% | `fm-it8` mean% / legal% | 比值 |
|---|---|---|---:|
| `AUTO` | 39.77 / 75% | 29.23 / 73% | ×0.735 |
| `IDLE` | 30.42 / 100% | 30.21 / 100% | ×0.993 |
| `WATER` | 22.42 / 71% | 15.80 / 65% | ×0.705 |
| `HARVEST` | 10.27 / 68% | 9.36 / 49% | ×0.911 |
| `CARE` | 9.62 / 45% | 6.90 / 39% | ×0.717 |
| `COLLECT_FERTILIZER` | 9.45 / 57% | 6.62 / 40% | ×0.700 |
| **`PLANT`** | **6.99 / 21%** | **5.68 / 21%** | **×0.813** |
| `DIG` | 6.74 / 54% | 4.07 / 48% | ×0.604 |
| **全部 27 个 `RAW_*` + `BUILD`** | **一律 0.00**(合法率 1–75%) | **2.29 – 6.91** | — |

**`anvil-fix` 里 39 个帮手任务有 28 个的概率质量是精确的 0.00**,包括四个
`RAW_MOVE`(合法率 65–75%)和 `BUILD`(合法率 75%)。`fm-it8` 用 `--legacy-new-bias zero`
训练,那 28 格于是**全部活了**,而每一个语义任务被按一个大致一致的乘性因子稀释掉
(×0.60 – ×0.91)。**`PLANT` 的比值 ×0.813 高于典型稀释 ×0.70–0.73 ——
也就是说,相对于词表激活,`PLANT` 其实是**涨**了。**

**所以 `8db606f` 与 `7cfce98` 里的「两把锁 / `PLANT` 不受种子约束 / 让它买小麦这个计划退休」
全部撤回。** 那不是种子效应,是 `adapt_legacy_hand_head` 把 29 个新任务打开造成的稀释。

**而 `79c98d4`(08-28)已经把这个混淆写下来过** ——「那条臂的阴性与熵下限的因果关系未建立,
因为帮手词表 10→39 的适配本身就会打坏策略」。**我没有应用它。**
连带影响另一个"实例":`e0a90f8` 那条 `BUY_SEED` 涨 20 倍而 `PLANT` 塌 13 倍,
正是 `79c98d4` 点名的同一族读数。**所以我称之为"同一形状的两次独立出现",
很可能是同一个伪影出现了两次。「两把锁」没有任何存活的证据支撑。**
(熵下限那条臂**钱**的阴性仍然成立 —— 那是同设置对照,稀释在两边等量抵消;
被混淆的只是 `PLANT` 塌 13 倍这个读数。)

### 正确的读法是反过来的:一把锁,在上游

同一次读数里的关键一行,`RAW_PLANT_<crop>` 的**合法率**(672 个在役槽位):

| | `PLANT` | `RAW_PLANT_WHEAT` | `RAW_PLANT_CARROT` | `RAW_PLANT_STRAWBERRY` |
|---|---:|---:|---:|---:|
| `anvil-fix` | 20.8% | **0.0%** | **0.0%** | 1.2% |
| `fm-it8` | 20.8% | **0.0%** | **0.0%** | 2.2% |

**`RAW_PLANT_WHEAT` 从来不合法** —— 它的合法性需要手里有小麦种子,而市场头从不买。
语义 `PLANT` 合法率 20.8%,但它只能种棚里有的东西,而棚里只有草莓。
**所以帮手侧不是"独立的第二把锁",它是被市场侧堵住的。链条是单向的:
市场头不买小麦 → 没有小麦种子 → `RAW_PLANT_WHEAT` 永不合法、语义 `PLANT` 只能种草莓 → 0 株小麦。**
**`6e2b2c2` 因此恢复为唯一的活靶子。**

**已被否的两个处方仍然被否**:`9707` 的 option 层强推种植(完成率 2–22/256)、
以及整头熵下限的**钱**的阴性(`8ec1c96`)。**恢复的是诊断,不是处方。**

### 顺带记一条基线事实(未测其危害)

**本次会话所有测量所依赖的基线 `anvil-fix`,只在 39 个帮手任务中的 11 个上运作。**
`RAW_*` 大多是语义任务的低层重复(语义版会自己选目标),所以压掉它们**可能无害**;
但 `RAW_PLANT_<crop>` **不是**重复 —— 它是唯一的逐作物播种控制,而它既被压到 0.00
又从不合法。**这条是否有害没有测过**,记在这里以免被当成已知安全。

**这是本次会话第一次「已发布后撤回」**(此前三次都在发布前抓住:
`env.steps[t].action` 错开一格、市场数量是下单量、以及那道不可执行的有效性门)。
逼出这一条的仍然是同一个动作:**不许留下一个解释不了的桶** ——
`RAW_*` 一栏整列精确的 0.00 就是那个桶。

## 2026-08-29 · 追问"市场头为什么不买小麦"得到两件事:**这个偏好随状态变化但从不反转**;以及**冻结基线的第一层在 180 个逐帮手观测维上是精确的 0**——网看不见自己帮手拿着什么

纯读盘,`rl/out/anvil-fix`,`closer_cleo`,seed 10000,每 3 步一个状态(240 个)。
市场头是 `mw @ h2 + mb` 的线性层,所以两格之差 `= (mw[i] − mw[j]) · h2 + Δb`,
可以逐状态精确算,梯度也可以解析穿过两层 ReLU。

**一、这个偏好是状态调制的,但在 240 个状态里一次都没反转。**

| | mean | std | min | max |
|---|---:|---:|---:|---:|
| `logit(BUY_SEED_WHEAT) − logit(BUY_SEED_STRAWBERRY)` | **−8.968** | 2.592 | −14.319 | **−3.226** |
| `logit(BUY_SEED_WHEAT) − logit(NOOP)` | **−10.723** | 1.976 | −19.916 | **−8.170** |

std/|mean| = 0.289,所以**不是一个常数偏置** —— 棋盘确实在调制它
(权重行差 `|Δw| = 0.838`,而 bias 差只有 −0.034,所以调制全部来自 `h2` 那一侧)。
**但最大值仍是 −3.226:小麦从未被偏好过一次;而对 `NOOP` 的差最大也只到 −8.170,
即"买 $10 的小麦种子"从来没有接近过"什么都不做"8 个 logit 以内。**
**所以这不是"在这些状态下小麦不划算"的判断,而是一个棋盘能调制、但翻不过来的常驻偏好。**
一个只在某些状态下起作用的干预因此不可能解开它。

**二、梯度按观测分块,而其中一块是精确的 0:**

| 观测块 | 维数 | mean \|d(gap)/dx\| | 占比 |
|---|---:|---:|---:|
| 棋盘前半 | 2,400 | 3.218e-02 | 43.9% |
| 棋盘后半 | 2,400 | 3.751e-02 | 51.1% |
| globals base | 67 | 1.312e-01 | 5.0% |
| **globals hands(逐帮手 180 维)** | **180** | **0.000e+00** | **0.0%** |

直接验第一层权重(不是推断):

| 导出 | `l1w[:, 逐帮手 180 维]` | globals base 67 维 | 棋盘 4,800 维 |
|---|---|---|---|
| **`anvil-fix`** | **max\|w\| 0.000e+00,非零 0 / 184,320** | max 2.99e-01 | max 1.42e-01 |
| **`chisel-fix`** | **max\|w\| 0.000e+00,非零 0 / 184,320** | max 3.15e-01 | max 1.63e-01 |
| `fm-it8`(训了 8 迭代) | max 2.15e-03,非零 134,991 / 184,320 | 3.00e-01 | 1.43e-01 |
| `nw-it8`(训了 8 迭代) | max 1.73e-03,非零 155,289 / 184,320 | 3.00e-01 | 1.42e-01 |

**两个冻结基线在那 180 维上是 184,320 个权重全部精确为 0** ——
`HAND_FEATURES = 3 + 9 个产品 + 3 个牲畜 = 15`,乘 `MAX_HANDS = 12`。
**也就是说:网看不见任何一个帮手身上带着什么。**
训练确实会把它们推离 0,但 8 个迭代后 max|w| 只有 **2.15e-03**,
对棋盘的 1.42e-01 是 **1/66**、对 globals base 的 3.00e-01 是 **1/139** —— 实质上仍然是盲的。

**这与 08-28 那条"`adapt_legacy_observation` 是 zero-pad、加载时中性"并不矛盾,但含义不同。**
zero-pad 对**加载**确实是中性的(不注入噪声),而它同时意味着**这些输入被乘以精确的 0**,
除非训练把它们推起来 —— 而按上面的速率,几十个迭代量级的臂推不起来。
**"加载时中性"不等于"有信息"。** 08-28 读了一行代码排除了"加载损伤"这个假设(正确),
随后这条线索就被放下了;本条把它接回来并量化。

**这一块正好覆盖本会话反复撞到的几个读数**:`PICKUP` 45 对 k01 的 136 次/季;
`RAW_PICKUP_WHEAT` 质量 0.00;饲料支出 50,634 对 16,189(买成品而不是搬运/自种)。
`FEED` 在引擎里从**行动者自己的库存**扣小麦(`_inv_take(inv, ...)`),
所以"喂"这件事在一个看不见手上库存的策略里是盲操作。

**但必须写下反例,它很强**:`agents/champ/k01.py` 是**开环回放,根本不看棋盘**,
却打赢四堵墙 91–98%。**所以任何观测特征都不是获胜的必要条件** ——
盲视因此**不足以**解释我们为什么输。本条给出的是一个**结构性事实加一条候选机制**,
不是一条判词式的因果结论。这次不重犯 `33cc1c9` 那个错误。

**它属于哪个家族**:不是解码层标志、不是奖励项、不是教师 CE、不是词表扩张
(那 180 维**已经在观测向量里**、已经合法,缺的只是非零权重)。
所以它是**输入层初始化**这一族,**本仓库从未测过**。
检查清单 (a)(无奖励又只解锁被掩码动作=白加)不适用:这里没有解锁任何动作。

**下一步(要先算术、再预登记,不要直接排臂)**:唯一的单变量 A/B 是把
`adapt_legacy_observation` 的新列从 zero-pad 改成与其余列同尺度的小随机初始化,
其余逐字不动。**但这正是 zero-pad 当初要防的事**(把噪声注入一个已训练的躯干),
而 `warmstart-neg` 已经演示过扰动一个成熟躯干可以是灾难性的。
所以它需要:(i) 一个 iter 0 的 lane 检查(初始化改动会立刻改变行为,所以**不能**用逐位相同,
要像 `8db606f` 那样换成机械门);(ii) 预登记的读数应当是**逐帮手观测是否被用上**
(`l1w` 那 180 列的 max|w| 是否升到棋盘量级),而不是钱 —— 钱在 8 个迭代里说明不了这件事。

## 2026-08-29 · 那道"先算术再排臂"的门**没过**:`BASE_G` 已经携带采购决策需要的一切,所以逐帮手盲视**不能**解释市场头不买小麦 —— 上一条判词的候选机制降级,输入层初始化 A/B **不排**

上一条(`3babe73`)把"第一层在 180 个逐帮手维上精确为 0"记成了"缺失小麦与饲料支出的候选机制",
并把输入层初始化 A/B 挂在一道"先做算术"的门后面。**算术做完了,门没过。**

读 `rl/obs.py:_global_features` 的 67 维 `BASE_G`(这一块的权重是**非零**的),逐项:

| 内容 | 维数 |
|---|---:|
| day/30、hour/24、我的钱 log、对手钱 log、我的帮手数、对手帮手数、`hires_today`、棚占用率 | 8 |
| 九个产品的 `price/base` | 9 |
| 九个产品的市场稀缺度 | 9 |
| **棚里九个产品的存量** | 9 |
| **棚里三种牲畜** | 3 |
| **逐作物持种数**(`min(seeds[c],20)/20`) | **5** |
| **农夫身上带的九个产品**(`priv["inventories"][0]`) | 9 |
| 我的象限 3 + 对手象限 3 | 6 |
| 八个商店 + 已解锁数 | 9 |

**所以一个采购决策需要的全部输入都在这 67 维里、而且权重非零**:
**逐作物持种数(它能看见小麦种子是 0)**、棚里有多少小麦、小麦的价格与稀缺度、钱、日期。
那 180 维额外提供的只有:**每个帮手的存活位、x、y,以及那个帮手自己身上的 9+3 库存**。
而棋盘通道 23 是 `hands here/4`,所以帮手的**位置分布**本来就可见,
缺的只是**哪个帮手在哪、身上带什么**。

**因此 `3babe73` 的机制候选降级:它不能解释市场头拒绝买小麦。**
那 180 维唯一还剩的用处是**逐帮手的分派与路线**,
而这正好落在检查清单 (i) 关闭的那一族里 ——「有余量的劳力下贪心最近近优,
调度类改动别再试(七个动作层标志六个被否,原因就是这条)」。
**所以输入层初始化 A/B 不排。** 这道门就是为这个结果准备的。

**保留的部分**:那个测量本身仍然成立(184,320 个权重精确为 0,8 迭代后只到 1/66 尺度),
而且它对"饲料"的解释**部分**保留 —— `FEED` 从**行动者自己的库存**扣小麦,
而网能看见棚和农夫身上的载荷、看不见帮手 i 的载荷。**但这仍然是分派问题,仍在 (i) 那一族里。**

### 把小麦这个问题剩下的东西写清楚,不发明新臂

`BUY_SEED_WHEAT` 这一格,已经排除的:

| 假设 | 怎么排除的 |
|---|---|
| 势函数的 Δφ 符号 | `e9407c8`,预登记 B 分支,`--potential networth` 一次修五处而作物程序不动 |
| 从未被采样 | 算术:1e-4 × 736,256 决策/迭代 ≈ 70 次/迭代,稀薄但不是从不 |
| 索引错位 | 市场头 31 维与 `MARKET_ACTIONS` 逐项对齐 |
| 加载损伤 | bias 全在 ±0.03、`\|w\|` 全在 0.02,是学出来的判别 |
| 只在某些状态下不划算 | `3babe73`:240 个状态里差值从 −14.3 到 **−3.2**,**一次都没反转** |
| **逐帮手观测盲视** | **本条:`BASE_G` 已携带采购所需的一切** |

剩下的只有第一次复盘就点명过的那一条:**一条长而精确的建设序列,它的每个前缀都是负收益,
所以逐步策略梯度永远装不起来**(买种 → 种 → 浇 → 收 → 补种,`BUY_SEED` 到 `PLANT`
的实测延迟中位 6 回合、均值 36、p90 142)。**而它已知的四种解法全部关闭:**

| 解法 | 状态 |
|---|---|
| 教师 CE / 模仿锚定 | 关闭 —— 与教师质量无关地有害(`ed4ad4f`) |
| option 层外挂 | 关闭 —— 完成率 2–22/256(`9707`) |
| 奖励整形 | 关闭 —— 势函数已测(`e9407c8`);奖励项家族(纪律 1) |
| **反向课程 / 银行态起局** | **关闭 —— `backplay-d8/d12/d16` 三段全部饱和在"磁带减 8k",补上缺掉的窗口只值 +10**(2026-08-23 判词) |

**所以我现在没有一条便宜、且不在已关闭家族里的臂可以排。** 与其发明一条,
把这个状态写下来:**问题是已知的、四条已知解法都已关闭、而下一步需要一个性质不同的干预,
那是设计决定而不是可排的实验。** `data/banks/` 目前只有 `barnyard-*.pt` 三个,
没有任何带小麦跑步机的银行态 —— 若将来要重开状态分布这条路,先得造那个银行,
而 `backplay` 的饱和判词说明单靠换起点不够。

## 2026-08-29 · 缺口的"两半"终于**同仪器实测**:路线值 **+50,206**,而其中 **41.7% 是对手从我们身上多赚的** —— 对手是开环磁带,所以那一份只能来自共享市场

上一条(`293a530`)说要把两半变成实测得"给路线做官方引擎导出"。**有更便宜的路:
把我们的网放进张量环境,而不是把路线搬到官方引擎。** `trl_env.FrozenPolicyOpponent`
能直接用检查点驱动一个席位(贪心 argmax,与导出的 numpy agent 行为一致)。
于是同一套 harness、同 8 个 seed(31000–31007)、同一个 cleo 磁带对手、同一个张量引擎:

| | 站立构成 | 持种 | 帮手 | 象限 | 我们 | 对手 | **margin** |
|---|---|---|---:|---:|---:|---:|---:|
| `k01_route_s34_fert`(脚本路线) | STRAWBERRY 28.0 + **WHEAT 25.6** | 草莓 4.62 + **小麦 1.75** | **11.2** | **2.00** | **63,977** | 84,175 | **−20,198** |
| `anvil/latest.pt`(我们的网) | **STRAWBERRY 19.8,小麦 0** | 草莓 1.66,**小麦 0** | 9.0 | **1.00** | **34,738** | **105,141** | **−70,404** |

**同仪器差值:路线比我们的网值 +50,206。** 这是此前只能作为跨仪器推断(~31k)提及的那个数,
现在它是实测,而且**比推断值大得多**。两边都是 0/8 胜。

### 而这个差值精确地劈成两半,一半根本不在我们这一侧

| 分量 | 算式 | 值 | 占比 |
|---|---|---:|---:|
| **我们少赚的** | 63,977 − 34,738 | **29,239** | 58.3% |
| **对手多赚的** | 105,141 − 84,175 | **20,966** | **41.7%** |
| 合计 | | **50,205** | = margin 差 |

（两者相加等于 margin 差,这是这个分解的内建校验。）

**关键在于对手是 `tape_t.TapeOpponent`,重放固定的 `_TRACE`,动作逐步写死、不会对我们反应。**
所以它多赚的 20,966 **不可能**来自"它打得更好",只能来自**共享市场**:
我们的农场产出少 → 卖得少 → 价格不被压下去 → cleo 那批一模一样的卖单换到更多钱。
**因为对手是开环的,这一份可以被干净地归因 —— 这正是开环对手在这里的诊断价值。**

**由此"打赢强墙"这件事有 41.7% 不是"把我们的农场做好"能覆盖的** ——
它是**市场压制**问题。本文件「Can we interfere with the market?」那一节(106,000 局)测过这条通道,
但从未把它接到当前的缺口分解上。**这是本会话第一次给那 65,044 里的一大块指出一个
不在"农场执行"框架内的成因。**

### 限制,一条不少

- **张量路径,不是官方引擎**;对手是 cleo 的 `_TRACE` 开环磁带,**不含 `closer_cleo.py`
  自己那层市场/SELL 调度器**;策略走贪心 argmax。所以**绝对数不能与官方引擎的
  −65,044 相比**;有效的只是**同仪器内的差值**。
- **8 lanes**。50,206 这个差远大于任何合理的 seed 噪声,但 **29,239 / 20,966 这个二分
  是 8 lane 上的点估计**,应当按点估计引用。
- `anvil/latest.pt` 在这里读到 **1.00 象限、1.66 颗草莓种**,而官方引擎的导出 `anvil-fix`
  读到 1.60 象限、5.42 颗 —— **seed 集与 harness 都不同(31000+ 对 10000+977i),
  所以这两组也不能互相交叉引用。** 是否存在张量/官方分歧,这条读数回答不了。
- **象限 1.00 意味着这批 lane 上我们的网一块地都没买过**,与 `BUY_LAND` 在 −9.55 一致。

**下一步(这条判词自带的,纯读盘)**:把这个二分在更多 lane 上收窄,并检查
"对手多赚"这一份是否随我们的产量单调 —— 若是,它就给出一个**不依赖我们变强**的
新读数轴:同一批 seed 上,让我们多卖会不会直接压低对手的收入。
**注意这不是"倾销压价"那条已被否的假设**(`9655`:我们的 receipts 比 cleo 还高 10,295,
那条否的是"我们的收入低是因为倾销"),这里问的是**对手的收入高是因为我们不产出**,
方向相反,而且对手开环使它可归因。

### 2026-08-29 · 对上一条的即时更正:那 41.7% **不是**"农场之外的新方向" —— 08-13 的 106,000 局早就测过,而它把两半**统一**成一件事,并给出一个 **1.7× 的杠杆**

上一条(`3507af9`)写「41.7% 不是'把我们的农场做好'能覆盖的,它是市场压制问题」。
**这句是错的,现在撤回。** 本文件「Can we interfere with the market?」那一节
(2026-08-13,两波 106,000 局)已经从另一侧测过同一件事,原话是:

> "**我们本身就是那个干扰。** 基线一季挂出 3,511 单位、把化肥和奶压到 $1,
> 而正是那种持续卖出替对手压住了价格。任何让我们卖得更少 —— 或者把自己农场搞坏
> 以致产出更少 —— 的做法,都是在**移除**我们本来正在施加的压力。"
> "**在这个环境里,退出做卖方是能送出的最大一份礼物。**"

而且那一节用**十九条臂**故意去扰动市场(倾销、囤货、换槽位),
**没有一条让对手的银行变少**。所以"把市场当一条独立轴去攻"是**已关闭**的:
唯一能压低价格的手段就是**多产多卖**,而那条路直接回到农场。

**所以正确的读法是两半被统一,不是被分开**:那 20,966 就是"我们退出做卖方"这份礼物,
它**随农场变强自动消失**。于是——

| 量 | 值 |
|---|---:|
| 我们的产出缺口(钱) | **29,239** |
| 由此带来的 margin 缺口 | **50,205** |
| **margin 对钱的杠杆** | **×1.717** |

**每多赚一块钱,margin 改善约 1.7 块**,因为它同时抬我们、压对手。
08-13 的独立读数与这个倍数一致:`C.fr_melon` 是我们 −8,132 / 对手 +9,133(合 ×2.12),
`E.fuse_d20` 是 −82,229 / +60,996(×1.74)。**三个独立测量给出 ×1.7–2.1。**

**这条更正有一个直接后果,而且是纪律层面的**:**以「钱」计价的杠杆不能直接去和以
「margin」计价的缺口相减** —— 中间差一个 ×1.7–2.1。
本仓库的量级表把"历史最大单杠杆 5,115"这类**钱**的数字与"缺口 65,044"这个 **margin**
并排相除过。**按行核对各自的量纲是待办**(有些行本身就是配对 margin,不受影响),
但这条歧义必须先记下来,因为它会**系统性低估**每一个干预的价值:
5,115 的钱若带 ×1.7 杠杆就是约 8,800 的 margin,占 50,206 的 **17.5%** 而不是 7.9%。
**这不会把任何一条已关闭的臂救活**(0/23、+532、教师 CE 塌都不受量纲影响),
但它把"需要几倍于历史最佳"这句话的倍数改小了。

**净结果**:目标从"关掉 50,206 的 margin"变成"补上 **29,239 的产出**",
而产出缺口的形状本会话已经量清:小麦跑步机(站立 25.6 对 0)、
象限 2.00 对 1.00、帮手 11.2 对 9.0。**靶子小了 42%,而且方向没变。**

## 2026-08-29 · 量级表的**量纲逐行核对完成**:五行里四行是「钱」、一行是「配对 margin」,而分母是 margin —— 最大杠杆从 7.9% 更正为 **13.5%**,排序不变但量级近乎翻倍

`a65c20d` 把"钱不能直接除以 margin"记成待办。逐行追到出处:

| 行 | 原值 | **量纲** | 出处 |
|---|---:|---|---|
| 历史最大单杠杆 `haymaker` | 5,115 | **钱** | `RUNS.md` 8002:同场 9 对手 864 局的**中位钱** 50,786 对对照 45,671 |
| 整个解码层 | ~2,000 | **钱** | `RUNS.md` 5911:与**钱**的缺口 `104,500 − 48,919 ≈ 55,600` 相除得 3.6% |
| 第 2 阶段最好候选 | 808 | **配对 margin** | `tools/stage2_read.py` 的 `--metric` 默认就是 `margin` |
| 墙入池 29 个 cleo 迭代 | 532 | **钱** | `train.csv` 的 `money` 列 |
| 强教师模仿锚定 | −12,000 | **钱** | 40,682 → 28,009,`money` 列 |

**所以那张表把四个「钱」的数字和一个「配对 margin」的数字放在同一列,再统一除以一个
**margin** 分母(65,044)。** 而 `RUNS.md` 5911 那条原始判词本身是**自洽的** ——
它用钱除钱(55,600),3.6% 那个数在它自己的语境里没错;**是我把它搬进按 margin 计价的表里
才变成了苹果除梨。**

**按 ×1.717 折算(只折"钱"那四行),两个分母都列出来:**

| 干预 | 原值 | 折成 margin | 占官方缺口 65,044 | 占同仪器路线差 50,206 |
|---|---:|---:|---:|---:|
| `haymaker`(历史最大) | 5,115 钱 | ~8,782 | **13.5%**(原记 7.9%) | **17.5%** |
| 整个解码层 | ~2,000 钱 | ~3,434 | **5.3%**(原记 3.1%) | 6.8% |
| 第 2 阶段最好候选 | **808 margin** | 808（不折） | **1.2%**(不变) | 1.6% |
| 墙入池 29 迭代 | 532 钱 | ~913 | **1.4%**(原记 0.8%) | 1.8% |
| 强教师锚定 | −12,000 钱 | ~−20,600 | 负 | 负 |

**排序一个都没变,已关闭的臂一个都没被救活**(0/23 是过门数、+532 与教师塌陷的**方向**
与量纲无关)。**变的是"需要几倍于历史最佳"这句话**:原来读作 65,044/5,115 ≈ **12.7 倍**,
按量纲更正后是 65,044/8,782 ≈ **7.4 倍**。仍然很远,但少了四成。

### 这个折算的适用边界,必须写清楚

**×1.717 的机制是"多产多卖压低共享价格,同时抬我们、压对手"**(`3507af9` + 08-13 的
106,000 局)。所以它只适用于**来自多产/多卖的钱**。
**一笔靠"买得更便宜"得来的钱不带这个倍数** —— 它不压低对手的卖价,甚至可能相反。
上表把四行都乘了 1.717,**因此那四行应当读作上界**;要变成点估计,
每一行都得单独查它的钱是从哪来的(`haymaker` 是训练臂、含产出改善,大概率带倍数;
墙入池的 +532 未查)。**这一条不要在没有逐行核查的情况下引用为精确值。**

**另一条不能混的**:65,044 是"**我们的网对四堵墙**"的官方引擎 margin;
50,206 是"**路线对我们的网**"的同仪器差。**两者问的不是同一个问题**,
分母该用哪个取决于在问什么(能否打赢墙 → 前者;路线那套程序值多少 → 后者)。
上表两列并排就是为了不让人再把它们混起来。

## 2026-08-29 · 把路线**自己消融**掉,结果**推翻我整天在建的框架**:小麦跑步机只值 **−412** margin,而**帮手那一束**值 **−16,435** —— 而且两者都几乎完全通过市场压制起作用

同一 harness、同 8 个 seed(31000–31007)、同一 cleo 磁带、同一张量引擎。
用 `barnyard_t.parse_profile` 的 `;key=value` 覆盖直接消融路线自己的程序:

| 臂 | 小麦 | 草莓 | 帮手 | 象限 | 我们 | 对手 | margin | 对基线 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `k01_route_s34_fert`(基线) | 25.6 | 28.0 | 11.2 | 2.00 | 63,977 | 84,175 | **−20,198** | +0 |
| `…;wheat=0`(**关掉小麦程序**) | **0.0** | 33.9 | 11.2 | 2.00 | **83,638** | **104,248** | **−20,610** | **−412** |
| `…;handmul=0.75`(帮手降到我们的水平) | 18.6 | 23.0 | **8.4** | 2.00 | 64,513 | **101,147** | **−36,633** | **−16,435** |
| `anvil/latest.pt`(我们的网) | 0.0 | 19.8 | 9.0 | **1.00** | 34,738 | 105,141 | **−70,404** | **−50,205** |

**旋钮机械有效性已验**:`wheat=0` 把站立小麦从 25.6 打到 **0.0**,草莓从 28.0 升到 33.9。

### 一、小麦跑步机值 −412。**我整天的框架被这一行否掉。**

本会话从 `74c093a` 起一直把"缺失的那一半"命名为小麦跑步机
(站立 25.6 对 0、窗口 `PLANT` 244 条对 14 条、整季 `BUY_SEED WHEAT` 580 对 1)。
**把它从路线里整个拿掉,margin 只动 −412。** 那个结构性差异是真的,
**但它的 margin 价值 ≈ 0(占 50,205 的 0.8%)。**

**机制是可见的,而且正是 ×1.7 杠杆反向运行**:去掉小麦后我们**多赚 19,661**
(63,977 → 83,638),而对手**也多赚 20,073**(84,175 → 104,248),两者相消剩 −412。
**所以小麦程序的功能不是挣钱,是压制对手** —— 它花掉约 20k 的钱,买回约 20k 的对手压制。
合理:小麦种下去是**喂 14 头畜**(被消耗、不卖),而同一块地本可以种基准价 $120 的草莓
(小麦成品基准价只有 $25)。

### 二、最大的可归因分量是**帮手那一束**:−16,435(占 32.7%),而且**我们自己的钱几乎没变**

`handmul=0.75` 把帮手从 11.2 降到 8.4(我们的网是 9.0),margin 掉 **16,435**。
但**我们的钱基本不动**(63,977 → 64,513),**全部损失来自对手多赚 16,972**。
**少一个帮手 → 产出少 → 卖得少 → 价格不被压低 → 对手更富。**
这是 08-13「退出做卖方是最大的礼物」的第三次独立确认。

**限制,不能忽略**:`handmul` **不是纯粹的帮手消融** ——
它同时把站立小麦压到 18.6、草莓压到 23.0。所以 −16,435 是**"帮手 + 帮手所支撑的一切"这一束**,
不是帮手槽位本身。**而且三条消融不可相加**(基线−小麦−帮手 ≠ 50,205),只能读排序。

### 三、由此更正的与新提出的

- **更正**:"小麦跑步机是缺失的那一半"**不成立**。结构差异真实,margin 价值 ≈0。
  本会话 `74c093a` / `293a530` / `3507af9` 里把它当作靶子的表述应按本条读。
  **`6e2b2c2` 的那一格(`BUY_SEED_WHEAT` 在 e⁻⁹)仍然是真的测量,
  但"打开它能拿回多少"现在有了答案:约 0。**
- **支持**:帮手轴是目前最大的单一可归因分量。监控里 `hirer` 那条臂
  (判据"每回合帮手数是否从 7.9 抬起")**瞄的变量是对的**。
  **但这不等于批准 `--hand-value 250`** —— "抬资产信用"这个处方已被 `furrow` 判阴;
  本条说的是**价值在哪**,不是**怎么拿**。
- **新假设(未测)**:我们的网整季**买 4,082 单位小麦成品**当饲料,
  而买入会**抬高**小麦价格,也就是抬高 cleo 卖小麦的成交价 —— **我们可能在直接给对手送钱**。
  路线自己种,所以不下这个单。这条可以用同一 harness 测(把我们的 `BUY_PRODUCT WHEAT` 掐掉),
  **但它是"少买"而不是"多卖",所以不带 ×1.7 那个倍数,方向也可能相反,必须实测。**

**净结果:靶子又换了一次,而这次是往帮手/产出吞吐那一侧换,不是往作物物种。**
而"产出吞吐"正是 08-28 第 2 阶段测过 23 个候选、0 个过门的那一层 ——
**但那 23 个候选是解码层旋钮(`trip`/`handmul` 等)在冻结检查点上的 A/B,
量纲是钱、按 `ea3879e` 应折 ×1.7,而且它们改的是"怎么分配现有帮手",
不是"有多少帮手"。`handmul` 在那次是 0.5 和 0.8 两个**下调**探针,**从未上调**
(旋钮在 `BY.HAND_CAP` 处被 clamp)。所以"多雇人"这个方向在本仓库**仍未被测过**。**

## 2026-08-29 · 把帮手**往上**调:曲线是**有峰的**,而峰恰好落在路线自己的 11.2 —— 所以"多雇人"这条方向**在花任何集群时间之前就被否了**,而帮手轴的价值同时被**定上界 ≤16,435**

上一条(`d02e4cb`)说"多雇人在本仓库仍未被测过",并提议为它起一条臂。
**先做了免费的那一半:`handmul` 在 `BY.HAND_CAP = 14` 处才 clamp,
而路线基线用的是 `_K01_HAND_CAP`(峰值 12),所以上调是可行的。**
同 harness、同 8 seed、同 cleo 磁带:

| `handmul` | 小麦 | 草莓 | 帮手 | 我们 | 对手 | margin | 对 1.0 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.75 | 18.6 | 23.0 | 8.4 | 64,513 | 101,147 | −36,633 | −16,435 |
| 0.90 | 26.0 | 23.9 | 10.2 | 76,653 | 103,374 | −26,721 | −6,523 |
| **1.00** | 25.6 | 28.0 | **11.2** | 63,977 | 84,175 | **−20,198** | **+0（峰）** |
| 1.15 | 25.0 | 28.5 | 13.0 | 67,260 | 92,000 | −24,740 | **−4,542** |
| 1.30 | 26.3 | 30.2 | 13.1 | 63,136 | 89,861 | −26,725 | **−6,526** |
| 1.60 | 27.4 | 26.6 | 13.1 | **47,098** | **106,111** | −59,013 | **−38,815** |

**曲线单峰,峰在 11.2,而那正是路线自己的值。** 往上每一档都更差,
`handmul 1.60` 更是把我们的钱打到 47,098、对手推到 106,111。
**所以"多雇人"是阴的,而且这个结论没花一分钟集群时间就拿到了。**
机制合理:帮手工资是 `fib(hires_today)`(见 `kaggriculture.py:698`),
而 13 个帮手在 10×10 的板上开始互相挤占格子 —— **路线已经站在最优点上。**

### 但同一条曲线给了帮手轴一个**上界**,这是它的正面价值

`d02e4cb` 的 −16,435 现在有了正确解读:**它是"跌到最优点以下"的代价,不是"最优点之上还有空间"。**
而我们的网在 **9.0**,落在这条曲线的 0.75–0.90 之间。所以:

- **帮手轴对我们的最大可能价值 ≈ 8.4→11.2 那一段 = 16,435,占 50,205 的 32.7%** ——
  **这是上界**,因为我们的网还有 1.00 象限、19.8 株作物,多出来的帮手可能无事可做。
- **而且它是路线的曲线**(靠缩放路线的 `_K01_HAND_CAP` 表得到),**不是我们网的曲线**;
  把它搬到我们的网上是**推断,不是测量**。
- 目标因此应当是 **11,而不是"更多"** —— 超过 11 已测得有害。

### 结论:这是又一个"已定上界、但每条通路都已关闭"的靶子

要让我们的网把帮手从 9.0 抬到 11,能想到的每个机制都落在已关闭家族里:

| 机制 | 状态 |
|---|---|
| 抬资产/帮手信用（`--hand-value` 一类） | 关闭 —— `furrow` 的"直接抬资产信用"判阴；且 `--hand-value` 已不在 main |
| 整头熵下限把质量推给 `HIRE` | 关闭 —— `8ec1c96`；且 `6e2b2c2` 解释了为什么（推给已活着的格） |
| 把市场队列交给脚本程序（`HIRE` 是市场动作） | 关闭 —— `8db606f`，产物无法部署 |
| 解码层标志 | 关闭 —— 四次复现 ±2,000（钱） |

**`HIRE` 本身不是不可达的**:`head_health` 读到它合法率 92%、中位 0.00% / 均值 7.41%
—— 稀疏但可用(与 φ 的符号翻转点在第 9 个帮手一致,`411afad`),
峰值确实到过 12。**所以问题不是它不能雇,是它平均停在 9.0。**
**但"怎么让它多雇"这一步,目前没有一条不在上表里的通路。**

**净结果:靶子的形状比早上清楚得多,而可排的臂比早上更少。**
今天四次移位(作物物种 → 帮手/吞吐 → 帮手有峰)之后剩下的是一句可检验的话:
**帮手轴 ≤32.7% 且目标是 11;而通往它的四条机制全部关闭。**
下一步需要的仍然是一个**性质不同**的机制,而不是又一个旋钮 —— 这是设计决定。

## 2026-08-29 · 量清 **cleo 在无人对抗时赚多少**(133,695,此前从未测过):我的"买小麦成品在给对手送钱"假设**被否**,但 `starter` 证明那个机制**真实存在**;而同一条读数把我们的网从"负资产"重估为"比不动值 +60,292、达到路线的 54.6%"

同 harness、同 8 seed(31000–31007)、同 cleo 磁带,只换 player 1:

| player 1 | p1 的钱 | **cleo 的钱** | cleo 对"无人对抗" |
|---|---:|---:|---:|
| **完全不动**(PASS/NOOP) | 3,000（=初始金，未动） | **133,695** | **+0（锚点）** |
| `starter`(内置弱基线) | 3,592 | **148,303** | **+14,608** |
| `anvil/latest.pt`(我们的网) | 34,738 | 105,141 | **−28,554** |
| `k01_route_s34_fert`(脚本路线) | 63,977 | 84,175 | **−49,520** |

### 一、我的假设被否:我们的网**不**给对手送钱,它已经在压制 28,554

`d02e4cb` 提出"我们整季买 4,082 单位小麦成品,买入抬价 = 直接给 cleo 送钱"。
**否**:相对"完全不动"这个锚,我们的网让 cleo **少赚 28,554**。
所以那 4,082 单位的买入被我们自己的卖出**净覆盖了**,我们已经在施加实质压制 ——
只是比路线少 20,966。**那 20,966 的正确说法不是"我们送出 21k",而是
"路线压制 49,520 而我们只压制 28,554,我们把 21k 的压制留在桌上没拿"。**
数值相同,**符号与因果方向被更正**。

### 二、但机制真实存在,而 `starter` 就是那个反例

**`starter` 让 cleo 比"完全不动"多赚 14,608。** 一个弱而**活跃**的 agent
比一个**完全惰性**的 agent 更让对手富有。机制候选:它买东西(抬高 cleo 卖出的成交价)
而产出不足以卖出去把价格压下来。**所以"弱而活跃"在对手收入这一侧比"什么都不做"更糟**,
而我们的网已经越过那个交叉点。**这是 08-13「退出做卖方是最大的礼物」的第四次独立确认,
而且这次量出了礼物的绝对大小(133,695 是白送的上限)。**

### 三、我们的网被重估:不是负资产,是"比不动值 +60,292、达到路线的 54.6%"

按 margin 算(p1 的钱 − cleo 的钱):

| player 1 | margin | 比"完全不动"好 | 占路线的 |
|---|---:|---:|---:|
| 完全不动 | **−130,695** | +0 | — |
| `starter` | **−144,711** | **−14,016** | **负资产** |
| 我们的网 | −70,403 | **+60,292** | **54.6%** |
| 脚本路线 | −20,198 | **+110,497** | 100% |

**`starter` 才是负资产**(比什么都不做更差 14,016);**我们的网是正资产,值 +60,292,
已经拿到路线的 54.6%。**

**这与 `57a5c0b` 的"执行器是负资产、交给它的局面越好毁得越多"不冲突,两条都成立**,
因为它们问的是不同的问题:**从零开始**,我们的网值 +60,292;
而**接手一个赢家的局面**时它把 +14,293 做成 −31,798。
**"从零可用、接手即破坏"是同一个策略的两个真实侧面** ——
前者说明它学到了实质能力,后者说明它的能力与一个强局面不兼容。
**此后引用"负资产"这个词必须带上是哪一种设定。**

### 四、这条读数给缺口一个此前没有的绝对标尺

**白送的上限是 133,695**(cleo 无人对抗时的收入),而路线只压掉 49,520(37.0%)、
我们压掉 28,554(21.4%)。**所以"压制"这条轴上,连最好的脚本路线也只用掉了 37%。**
它不构成一条新的可排干预(08-13 的十九条故意扰动市场的臂无一让对手变少,
唯一手段是多产多卖),但它把 `3507af9` 的 ×1.717 杠杆放进了一个有天花板的尺度里。

**限制**:张量路径、cleo 是不含自身市场调度器的 `_TRACE` 开环磁带、8 lanes、
策略走贪心 argmax。**绝对数不能与官方引擎的 −65,044 相比**;有效的是同仪器内的差值与排序。

## 2026-08-29 · **收口:把脚本缩到和我们完全一样的农场规模**(19.7 株、9.3 帮手、1.00 象限),它仍然赚 **79,588** 而我们赚 **34,738** —— 缺口的 **88% 是同一份资产上的执行质量**,不是物种、不是规模、不是土地、不是帮手、不是市场压制

同 harness、同 8 seed(31000–31007)、同 cleo 磁带、同张量引擎。
用 `;key=value` 把路线**缩到我们的足迹**:

| spec | 草莓 | 帮手 | 象限 | 我们 | 对手 | margin |
|---|---:|---:|---:|---:|---:|---:|
| `route`(基线) | 28.0 | 11.2 | 2.00 | 63,977 | 84,175 | −20,198 |
| `route;wheat=0` | 33.9 | 11.2 | 2.00 | 83,638 | 104,248 | −20,610 |
| `route;wheat=0;straw=28` | 27.9 | 11.2 | 2.00 | 83,912 | 105,925 | −22,013 |
| `route;wheat=0;straw=24` | 23.9 | 11.2 | 2.00 | 74,521 | 95,086 | −20,565 |
| `route;wheat=0;straw=44` | 43.5 | 11.2 | 2.00 | 75,537 | 100,424 | −24,886 |
| `route;wheat=0;straw=20` | 19.9 | 11.2 | **1.00** | 77,604 | 103,268 | −25,664 |
| **`route;wheat=0;straw=20;handmul=0.8`** | **19.7** | **9.3** | **1.00** | **79,588** | **105,785** | **−26,197** |
| `route;wheat=0;straw=20;handmul=0.7` | 19.6 | **7.6** | 1.00 | 78,638 | 105,105 | −26,468 |
| **`anvil/latest.pt`(我们的网)** | **19.8** | **9.0** | **1.00** | **34,738** | **105,141** | **−70,404** |

### 一、几乎精确的同足迹对照:差 44,207,而其中 99% 是我们自己的钱

`;straw=20;handmul=0.8` 与我们的网:草莓 **19.7 对 19.8**、帮手 **9.3 对 9.0**、
象限 **1.00 对 1.00**、同对手、同 seed、同引擎。
**margin −26,197 对 −70,404,差 44,207。**
而**对手的收入几乎相同(105,785 对 105,141,差 644)** ——
**所以那 44,207 里 98.5% 是我们自己的钱:79,588 对 34,738,倍数 2.29×。**
**在这个足迹上,市场压制的差异是零。**

### 二、由此四条结构性框架同时退场

| 框架 | 本条给出的量 |
|---|---|
| **物种**(小麦跑步机) | **−412**(`d02e4cb`) |
| **规模**(作物株数) | 19.9 → 33.9 只值 **+5,054** |
| **土地** | 两边都是 **1.00 象限**,而我们的网 19.8 株**没填满** 25 格 → 不绑 |
| **帮手** | 在这个足迹上 11.2 → 7.6 只动 **−804**;**7.6 个帮手的脚本仍然比我们的 9.0 好 43,936** |
| **市场压制** | 对手收入 105,785 对 105,141,**差 644** |

**`267017a` 那条"帮手轴 ≤16,435 / 32.7%"必须按本条收窄**:那 16,435 是在路线**全规模
(53.6 株)**下测的,帮手在那里确实绑;**在我们的 19.8 株足迹上帮手值约 0。**

### 三、分解闭合到 2.7%,这是它的内建校验

从我们的网走到路线基线:
−70,404 →(**执行质量 +44,207**)→ −26,197 →(**作物规模 +5,054**)→ ≈−21,143 →
(**小麦程序 −412**)→ ≈−21,555,对路线实测的 **−20,198** 残差 **1,357(2.7%)**。
**四项相加几乎正好等于 50,206,所以这个分解不是拆得随意,它闭合。**

### 四、所以缺口是什么,以及为什么第 2 阶段的 0/23 不与它冲突

**缺口的 88% 是"同一份资产上怎么干活、怎么交易"** ——
同样 19.8 株作物、同样 9 个帮手、同样 1 个象限,脚本把钱做到 2.29 倍。
**08-28 第 2 阶段那 23 个候选 0 过门并不与此冲突**:那些是**解码层旋钮在冻结检查点上的
微扰**(`trip`/`handmul`/收获优先级一类),而这里说的是**一个 2.29 倍的差**。
**结论不是"执行无法改进",而是"我们试过的那 23 个旋钮不是这个差"。**

**限制**:8 lanes;张量路径而非官方引擎;cleo 是不含自身市场调度器的 `_TRACE` 开环磁带;
策略走贪心 argmax。**绝对数不能与官方 −65,044 相比。**
另外**"执行质量"这一项仍然是个复合项** —— 脚本的机器同时包含农场干活(持久路线、
逐格粘性、选择性施肥)与市场交易(复合卖出队列)。**把这 44,207 拆成"农场侧 / 市场侧"
是下一个该做的读数,而 `barnyard_prefix` 的 `scope all|farm|market` 正是为此存在的。**

## 2026-08-29 · 把那 44,207 拆成农场侧/市场侧:**两个单独换都是负的(−4,381 / −20,385),而交互项是 +68,972** —— 这一个数解释了本项目全部 ±1% 结果的图样

同 harness、同 8 seed、同 cleo 磁带,同足迹脚本
`k01_route_s34_fert;wheat=0;straw=20;handmul=0.8`。用 `step_idx` 的**部分 override**
把"农场侧"(`f_*`/`h_*`/task 状态)与"市场侧"(`m_op`/`m_item`/`m_rem`)分开替换。

**两道机械门先过**:用拆分机制跑 `script+script` 得 **−26,197**(对直接跑差 **0**);
`net+net` 得 **−70,404**(差 **0**)。**所以拆分机制是保真的,下面的数不是管道产物。**

| farm | market | 我们 | 对手 | margin |
|---|---|---:|---:|---:|
| net | net | 34,738 | 105,141 | **−70,404** |
| net | **script** | 39,400 | **130,189** | **−90,788** |
| **script** | net | 34,345 | 109,130 | **−74,784** |
| script | script | **79,588** | 105,785 | **−26,197** |

| 分解 | 值 |
|---|---:|
| 只换农场侧 | **−4,381** |
| 只换市场侧 | **−20,385** |
| 两侧都换 | **+44,206** |
| **交互项** | **+68,972** |

### 一、两个子系统是**乘性互补**的,而且单独换是**负的**,不只是中性

**交互项 +68,972 压倒两个主效应之和(−24,766)。** 检查清单 (e) 记的
"浇水/施肥/收获乘性互补"在**整个子系统的层级**上同样成立。
**换掉任一半都会让结果更差** —— 这比"单独换没用"强得多,也解释力大得多。

机制在数字里可见:
- **`net farm + script market`:对手飙到 130,189**(比 `net+net` 多 25,048)。
  而"完全不动"的锚是 133,695,**所以这个嵌合体只压制了 3,506,
  比我们的网自己的 28,554 少了 88%** —— 脚本的市场队列在一个不按它计划产出的农场上,
  买进它用不上的投入(抬价)、卖出并不存在的货,于是把我们的压制几乎全部丢掉。
- **`script farm + net market`:我们的钱 34,345,基本不动。**
  脚本的农场机器拿不到它需要的采购,干活也变不出钱。

### 二、这一个数**追溯解释**了本仓库一整族结果

| 既有结果 | 本条给出的解释 |
|---|---|
| `8db606f` 的 `--fixed-market-profile`(net 农场 + script 市场,**训练**) | 那个格子**训练前就是 −20,385**;8 个迭代跨不过 +68,972 的交互项。**判 B 是可预测的** |
| 08-25 的 scope 消融「两个 scope 单独均不过门,只有联合整季控制为正」 | **同一个发现,现在被量化了**:农场侧 −4,381、市场侧 −20,385、联合 +44,206 |
| 第 2 阶段 23 个候选 0 过门 | 全是**单侧**旋钮 |
| `expand_crop` / `farm_phase` 完成率 2–22/256 | 种植被外挂在农场侧,没有配套的市场侧 |
| 整头熵下限、教师 CE、势函数 | 都是单侧或全局的标量干预 |

**自我批评**:`8db606f` 的预登记里我**提到**了 08-25 的 scope 消融,还专门写了"那次没有训练
任何东西"来区分它 —— 但**没有推出"所以那个交叉格子会从一个很负的起点开始"**。
检查清单 (k)(起臂前先 grep 同形实验)我执行了字面,没执行它的意图。

### 三、由此得到一条**可操作的设计约束**,这是今天第一条

**任何干预必须同时、且一致地改变两个子系统,否则它会测出负值。**
这不是"再找一个更好的旋钮",而是对干预**形状**的硬约束:
单侧的标量/旗标/奖励项/教师项**在结构上不可能**跨过一个 +68,972 的交互项。
**这解释了为什么"需要一个性质不同的干预"这句话是对的,并且第一次说清了"不同"指什么。**

**限制**:8 lanes;张量路径;cleo 是开环 `_TRACE`;贪心 argmax;
两个交叉格是**嵌合体**(脚本的一半在一个它没有预期的状态分布上运行),
所以 −4,381 / −20,385 应读作"**把这一半单独移植过去的代价**",
不是"这一半本身的价值"。**交互项的存在与量级不受这条限制影响**,
因为四个格子里有两个是自洽系统且都通过了逐位机械门。

## 2026-08-30 · 预登记:`granger-noks` —— 从 `granger.yaml` 移除 `kickstart: barnyard`(用户已批),验收门用**最强形式:与 `warmstart-zero-ks0` 的 train.csv 逐行字节等价**

**为什么现在删**:`dd561a4` 的 2×2 判它是热启动塌陷的**必要条件**;`f74fecd` 早已关闭
`--kickstart` 路;`ed4ad4f` 又证教师 CE 与教师质量无关地有害。配置却一直带着它,
每条臂都要靠 `--ks-coef 0` 手工中和 —— 这正是 08-28 那批臂被静默污染的入口。
用户 2026-08-30 批准移除,条件是自带 A/B。

**为什么验收门可以用字节等价(读码得出,不是假设)**:`kickstart: barnyard`(无 profile
后缀)时 `trl_env.py` 的 `self._kickstart_executor is None`,标签走
`kickstart_labels(ep, seat, None)` —— **纯状态函数,不消耗 RNG、不修改 `ep`**;
损失侧 CE 项乘 `ks_coef = 0` 精确为零(项有限,`mktfloor` 系读数 3.16)。
所以移除它唯一该变的是:吞吐(不再算教师标签)与 obs spec 里三个 teacher_* 键(策略不读)。

- **臂**:`granger-noks` = `--config granger.yaml(新) --init-from rl/runs/anvil/latest.pt
  --hidden 1024 512 --v-hidden 512 --multi-head --legacy-new-bias zero --seed 280828`
  （与 `warmstart-zero-ks0` 唯一差别:config 里没有 kickstart,于是命令行也不再需要
  `--ks-coef 0`）。CPU 单 link 30 分钟。
- **A 分支(移除干净)**:iters 0–8 的 `win`/`money`/`ent` 列与 `warmstart-zero-ks0`
  **逐行相等**(sps/sec 是计时列,不比)。顺带记录 sps 变化。
- **B 分支**:iter 0 相等但后续发散 → coef 0 时 kickstart 仍在某处消耗 RNG;
  记录在哪;**移除仍保留**(它是目的状态),但此后与旧 `--ks-coef 0` 系对照不再字节可比,
  需要重立基线。
- **C 分支**:iter 0 就不等 → 结构性问题(teacher_* 键影响了策略路径?),**回滚并查**。

## 2026-08-30 · `granger-noks` 判 **A 分支**:移除 `kickstart: barnyard` 与 `--ks-coef 0` **逐字节等价**(10 个迭代 × 7 列,0 个不同单元格) —— 顺带发现教师标签一直在吃掉**一半的采集吞吐**

作业 `20822134`(提交 `f0b809d`),CPU 单 link。与 `warmstart-zero-ks0` 的 train.csv
逐行比较 `win/money/opp_money/ent/pg/vf/steps` 七列、iters 0–9:**0 个不同单元格。**
预登记的 A 分支(移除干净)按字面成立,读码推断(纯状态函数、不耗 RNG、CE×0 精确为零)被证实。

**副产物比主结果值钱:sps 从均值 3,916 → 7,682(×1.96)。**
`kickstart: barnyard` 在 `ks_every=1`(granger 默认)下,教师标签一直占用约一半的
采集吞吐 —— **也就是说 08-28 之前每一条带 kickstart 的臂都付了 2 倍的墙钟时间,
换一个已被 `dd561a4`/`ed4ad4f` 判为有害的损失项。** 移除后同样 30 分钟的 link
能跑约两倍的迭代。

配置层面的收尾:`granger.yaml` 不再携带 kickstart/ks_coef/ks_anneal,
新臂不再需要手工 `--ks-coef 0` 中和 —— 08-28 那批臂被静默污染的入口已经关闭。
`warmstart-zero-ks0` 一系的旧对照与新 config 的臂**保持逐字节可比**(本条就是证明)。
