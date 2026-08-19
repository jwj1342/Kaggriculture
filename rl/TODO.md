# rl/ TODO — 已议定但未动工的事项

规则：这里的每一项都**不许**打断或修改当前正在跑的训练管线。动工时新开目录，
旧管线保持原样直到新东西通过验证。

## 1. 张量化脚本对手（统一层的已知边界）

设备端课程/league（`tensor_env/trl_pool.py`）只能吃张量可表示的对手：
starter 与任何导出权重（npz/checkpoint）。**barnyard、ghosts、spar 这些
脚本对手还不能当训练对手**——它们只活在 kaggle-env 评估世界
（`slurm/rl_eval.sh`、`rl/league.py`）。要把课程推到 ghost/barnyard 档，
要么按 `opponents_t.py` 的样板逐个张量化（starter 用了 ~150 行 + 逐动作
一致门 `test_b4a.py`），要么先把它们 BC 成权重再当冻结对手（有保真度损耗，
barnyard 神谕克隆两轮均部署即塌的教训在 README §11）。

## 2. 推理期市场精确优化器（讨论于 2026-08-14，ghost 里程碑后）

对 market 头做一步穷举精确评估（kg_rules.market_price 是引擎价格模型的
镜像，卖单收益可逐单位精确算）+ value 网络评估后继状态。收敛于路线 C 的
外包装机制。在 1 秒/回合预算内数毫秒可完成。

## 3. 离线 N×N 联赛 Bradley-Terry 重排

tools/stats.py 有现成 bradley_terry。注意：联赛成员全叫 main.py，
**必须按目录键控读 shard JSONL**，绝不能走 ingest+ratings 表
（basename 合并陷阱，run #22 实录）。

## 4. 榜单轨迹 BC（储备加速器）

dist/ 里 3MB、156 条真实榜首剧本。原始动作 → 宏意图需要一层反向映射，
做之前先量映射覆盖率（README §8）。

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

- **分布式收集 + 中心学习器**（原 #1，目标单节点 800–1,300 步/秒的 ~4 倍）：
  被张量路径整体取代——单卡 H100 上 TorchRL collector 46k 步/秒（35–57 倍于
  原目标基线），单设备采集+更新同驻，分布式失去动机。原方案细节在 git 历史。
- **张量化引擎**（原 #2）：完成即 `rl/tensor_env/`（tensorize 分支，
  2026-08-18 并入 main），逐字节验证链、单卡 22.8 万 lane-steps/s；
  其上是 TorchRL 统一层。当时登记的三处易错点（市场 lockstep、原子 PLANT、
  每日 RNG）全部有独立门覆盖。
