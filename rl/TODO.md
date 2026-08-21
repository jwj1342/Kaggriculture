# rl/ TODO — 已议定但未动工的事项

规则：这里的每一项都**不许**打断或修改当前正在跑的训练管线。动工时新开目录，
旧管线保持原样直到新东西通过验证。

## 1. 张量化脚本对手（barnyard ✅ 2026-08-19；ghosts/spar 未动）

**barnyard 已张量化**：`tensor_env/barnyard_t.py`（决策直接产出引擎内部
编码，经 `step_idx(..., override=)` 接缝上席位——它的全单位统一调度超出
宏动作空间，所以走原始动作级而非宏投影）。门 `test_barn.py`：对真
`agents/barnyard.py` **逐动作 + 逐步全状态**双重判等，5 lanes × 719 步
全绿，终局金钱 63–85k（强度无损）。训练对手写法：`--opponents ...,barnyard`。

剩余：**ghosts/spar**（录音重放型）。两条路：录音的原始动作 → 内部编码的
离线转换（一次性预计算 (T, ops) 表，override 逐步喂——比 barnyard 简单
得多，但录音不还手、可被退化利用）；或维持它们只做评估对手。`enhanced`
（另一个手写强 agent）如需张量化，走 barnyard_t 同样的样板。

## 2. 推理期市场精确优化器（讨论于 2026-08-14，ghost 里程碑后）

对 market 头做一步穷举精确评估（kg_rules.market_price 是引擎价格模型的
镜像，卖单收益可逐单位精确算）+ value 网络评估后继状态。收敛于路线 C 的
外包装机制。在 1 秒/回合预算内数毫秒可完成。

## 3. 离线 N×N 联赛 Bradley-Terry 重排

tools/stats.py 有现成 bradley_terry。注意：联赛成员全叫 main.py，
**必须按目录键控读 shard JSONL**，绝不能走 ingest+ratings 表
（basename 合并陷阱，run #22 实录）。

## 4. 榜单轨迹 BC（储备加速器）

dist/ 里 3MB、371 条真实榜首剧本。原始动作 → 宏意图需要一层反向映射，
做之前先量映射覆盖率（README §8）。

**op 级覆盖率已测（2026-08-20，全库 371 条 × 719 回合）**：hand 工作动作
897,751 个，**88.8% 落在 FEED 落地后的词表内**；缺口 = 雇工 PLANT 6.1%、
FERTILIZE 2.9%、PLACE/BUILD ~1.5%（→ 下两个便宜的词表扩展）。榜首 meta
的雇工喂食 97k 次、取麦 40k 次——动物引擎在顶端同样是雇工劳动。市场：
16.5% 的活跃回合发多单（含 17k 个 5+ 单爆发回合），单槽 market 头表达
不了；单数是 HIRE 105k / SELL 83k / BUY_PRODUCT 66k。**状态级保真度**
（贪心执行器是否选中同一目标格）需要重建状态：库里只有单席动作带，得按
episode id 从 Kaggle 日数据集重拉 replay（管线在 tracelib.py pull，每局
29MB；这次保留 replay 而非即拉即删）。

## 5. 容量实验（m5）前置条件 — 2026-08-15 负结果归档

1024/512 与 512/256 的新鲜 BC 克隆在当前代码下都出现种子双峰塌陷
（部分种子 ~25k、部分 $0；旧的 512/256 检查点 bc_init.pt 无此病）。
BC 数据（rl/runs/bc/data）采集于 PLANT_DEADLINE 掩码与复合市场指令之前,
标签/掩码与部署语义已漂移。重试容量实验前必须：用当前语义重采教师数据
（`rl/bc/collect_bc.py` 重跑即可），再训 BC，先过 8-seed 部署 sanity。

## 6. 反事实信用分配（CCA，2026-08-19 议定）

德扑式的问题："这一手如果不这么打，价值差多少"。720 步链条上普通 GAE 的
信号被折扣与方差吃掉。两条可行落地，都靠张量引擎才变得便宜：

- **因子化头的反事实基线**（COMA 式，先做这个）：我们的动作本来就是
  farmer×market 双头因子化，对单头 a_f 的优势可以用"固定另一头、按策略
  边际化本头"的基线替代全局 V——需要一个 Q(s, a_f, a_m) 头或对 23×22
  联合枚举 value 网（4867→506 输出，一次前向）。改动集中在 GAE 之后的
  优势替换，loss 不动。
- **日尺度反事实 rollout**：在选定决策点 fork 批状态（EpisodeT 状态全是
  张量，fork = clone），把某头动作换成策略次优解，冻结策略滚 24 步
  （一个游戏日），两条线的势能差 = 该动作的日尺度反事实优势。B=1024 上
  fork+24 步 ≈ 0.5 秒（228k lane-steps/s 实测推算），每迭代抽样几个
  决策点完全可负担。

## 7. RL 当序列生成：Decision Transformer（2026-08-19 议定，分三期）

720 帧当序列，self-attention 直连第 50 步与第 600 步。分期：

- **(a) 离线 DT**：数据来自张量引擎自博弈（league 快照互打，多样性够）；
  obs 4867 → 线性嵌入 256，每步 (RTG, s, a) 三 token，上下文 719×3 ≈
  2157 token，H100 单卡毫无压力。RTG 用终局 money（或 margin）。
- **(b) 部署路径**：导出契约是纯 numpy——小 transformer 的前向就是矩阵乘,
  带 KV cache 的逐步推理在 1 秒/回合预算里绰绰有余（现 agent 用 0.25ms,
  预算用了 0.02%）。main.py 模板需要新变体，仿 residual 的做法。
- **(c) 在线微调**：DT 采样接入现有 collector（动作头复用 TwoHeadMasked）。
  风险登记：DT 的上限受数据分布钳制（"轨迹引导搜索"的老问题），所以 (a)
  的数据必须包含 league 的多样对局而非单一剧本；先用 (a) 复现 pitchfork
  水平作为门，再谈超越。

（背景注记：势能奖励重塑**已是现行基线**——`potential_t.net_worth_t` 的
势能差就是每步奖励；边际奖励做成了**终局有界 tanh** 而非逐步零和,
因为 λ=1.0 逐步零和是已归档的负结果"同归于尽"。平滑三件套 margin/
handicap/opp-noise 已实现，`rl/configs/foothold.yaml` 是首个组合 run。）

---

## 已完成 / 已被取代（记录）

- **逐单位多头动作空间**（原 #0，复盘 §13 出路②，想法出自 Kilo
  `new-branch b53739f`，机械用我们已验证的）：2026-08-19 完成。hand 任务
  词表 {AUTO, IDLE, HARVEST, WATER, CARE, COLLECT_FERTILIZER, DIG}，AUTO =
  经典级联且**全 AUTO 逐位等价于旧宏空间**；market 保留 22 动作（Kilo 的
  4 模式内嵌 barnyard 经济表，未采）。落地五层各有门（`test_multi.py`
  M1–M4）：`actions.decode_multi` → `step_idx(h_idx=)` 设备解码（mfk 最低
  家族键换成指定家族键，认领机械复用）→ `MultiHeadMasked`/`MultiActorNet`
  （hand 头 AUTO 偏置 +2.5 起步）→ env (B, 14) 动作 + 设备端
  `hand_task_mask_t` → 导出模板/CLI/FrozenPolicyOpponent 全组合支持。
  入口 `rl/train.py --multi-head`；首个 run 见 `rl/configs/breach.yaml`。

- **分布式收集 + 中心学习器**（原 #1，目标单节点 800–1,300 步/秒的 ~4 倍）：
  被张量路径整体取代——单卡 H100 上 TorchRL collector 46k 步/秒（35–57 倍于
  原目标基线），单设备采集+更新同驻，分布式失去动机。原方案细节在 git 历史。
- **张量化引擎**（原 #2）：完成即 `rl/tensor_env/`（tensorize 分支，
  2026-08-18 并入 main），逐字节验证链、单卡 22.8 万 lane-steps/s；
  其上是 TorchRL 统一层。当时登记的三处易错点（市场 lockstep、原子 PLANT、
  每日 RNG）全部有独立门覆盖。

## 8. market 头的分批卖出(2026-08-20 测量完毕,待 parrot v1 判词后实施)

55 局当前平衡 replay、13,183 个榜首 SELL 单:47.3% 清仓卖(现 SELL_p 已
覆盖),其余为小批量(众数 7 单位,多数 ≤ 深度 T 的 5–10%);按品类
WHEAT 6,627 / FERTILIZER 2,649 / MILK 1,375——顶端在用小麦+化肥做持续
现金流,甜瓜只有 225 单。方案:`SELL_HALF_<p>`×9(头 22→31,新 run 才
兼容,与 FEED 的 7→8 同一验收模式);几轮可组合出任意比例。预期把
market 头状态级保真度 57% → ~75%+(见 rl/bc/build_dataset.py 台账),
然后重建 BC 数据集重训 parrot。

**#8 追记(2026-08-20 晚)**:SELL_HALF 落地后重建 BC 数据集,market 状态级
保真度 57.0%→**57.7%,基本没动**——榜首的分批卖是小额定量(众数 7 单位),
"半仓"在大库存下对不上(40 存货的一半是 20)。教训:精确量匹配是 BC 标签
的错误标尺;RL 侧 SELL_HALF 仍成立(可跨回合组合任意比例,granger 在用)。
BC 若重启,用区间匹配(qty ∈ [0.25,0.75]×held → SELL_HALF)或定量动作
(SELL_N,N∈{4,8})。

## 9. 容量路线图(2026-08-20 夜,调研判词 + draught 探针)

调研核心(全文见会话,来源含 Hilton/Schulman 2301.13442、Neumann&Gros
2210.00849、BRO/SimBa、Net2Net、OpenAI Five surgery):游戏 RL 历史上
**普遍尺寸不足**;更大网络在**等环境步数**下就更强(判定性实验);我们
2.7M actor 的 93% 耗在 4867 维输入投影,主干仅 ~170k;critic(1.3M)
比 actor 小——与"value 网应更宽"的证据相反。行动序:
1. **draught 探针在跑**(4× 宽 + 2× critic,granger 配方,等步对照)——
   赢了即证容量是绑定约束;
2. 先决条件(下一代前):trunk 加 LayerNorm + weight decay(可塑性
   前提;注意会破 8 数组导出契约,与 CNN 线一并动);
3. **critic 4–8×**(部署零成本,长视野 value 欠拟合最可疑)+ PPG 式
   value 多 epoch;诊断项:分段 explained variance / srank / 死神经元率;
4. 结构大招:棋盘 CNN 干(4–8 个 SE 残差块 @64–128ch,标量池化后注入,
   12×8 hand 头映射到逐格头)——kickstart 从最强 MLP checkpoint 蒸馏,
   平行线不热切;推理预算允许 ~60×(现用 0.02%);
5. 增长机制:Net2Net 加宽 / 手术式函数保持扩容 / 可塑性注入(也可当
   诊断:平台期注入容量,曲线复活=容量绑定)。

## 10. 磁带课程与两个定价观察(2026-08-21)

- **tape:k06 已可用**(k6tape 分支 91e36bb 待合并):idx 路径补上 PLACE
  的第二语义(邻棚定量存货)后 k06 磁带逐元判等(100,032)。gen-6 课程
  阶梯:barnyard(47k)→ tape:w49(84k)→ tape:k06(100k)。
- **单一产品经济的价格脆弱性(实测)**:cropper 对局中双方倾销把奶价砸到
  3–7,同种子收入 24.5k(draught 早先 58.6k)——顶端的 5 线收入结构是
  价格风险保险;作物曲线信用 30/株在既有奶业盆地面前可能太弱,等 cropper
  链尾判词再调。
- **蛋价生态位**:hinge 平衡下 EG 尾盘冲到 107–149(3× base)而无人养鹅;
  future 势给动物产品按 base 定价,鹅被 3× 低估——候选:动物未来产出按
  max(base, 当前价) 定价(注意别复活市值 mark-to-market 的旧病,只对
  above-base 方向开口)。
