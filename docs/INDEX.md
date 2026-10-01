# 文档索引

**整理时间：2026-10-01。提交阶段已结束，最终排名与奖牌待公布。**

先读 [README](../README.md)，再按问题进入下面的文档。最终两个活跃提交是
**56720412 mixed-deferred** 与 **56721680 wool-priority**，截止后官方读回均为 COMPLETE。

## 赛后交付

| 文档 | 内容 |
| :--- | :--- |
| [赛后 Notebook](../notebooks/postmortem/kaggriculture-final-strategy-and-lessons.ipynb) | 思路、路线、失败、确认实验、最终包下载与复现边界 |
| [研究路线与教训](RESEARCH_LESSONS.md) | 手工调度、轨迹、RL、测量和工程的得失，含历史更正 |
| [数据归档与恢复](ARCHIVE.md) | 数据库、D1、RL 历史和 Release 资产的范围与恢复方式 |
| [冻结结果摘要](../notebooks/postmortem/evidence.json) | 最终提交身份、哈希、实验规模和统计区间 |
| [组合原审查](../submissions/2026-09-30-mixed-deferred/REVIEW.md) | 组合正式确认、资源成本、真实包与慢局复验 |
| [羊毛原审查](../submissions/2026-09-30-wool-priority/REVIEW.md) | 羊毛正式确认、供肥失败、回归格与运行复验 |

原审查文件冻结在各自审批时点，可能仍写“待上传”或当时的旧槽位建议；
实际提交和最终槽位以 [RUNS.md](RUNS.md) 的最终截止核对为准。

## 截止前执行与来源

| 文档 | 用途与时间背景 |
| :--- | :--- |
| [ENDGAME_EXECUTION.md](ENDGAME_EXECUTION.md) | 09-29 至截止后的执行、证据、审查与决策过程 |
| [RUNS.md](RUNS.md) | 本轮提交台账、Kaggle ID、真实上传时间与健康检查 |
| [ENDGAME_PUBLIC.md](ENDGAME_PUBLIC.md) | 公开代码来源、候选与许可检查 |
| [ENDGAME.md](ENDGAME.md) | 09-29 冲刺前计划；其中历史资产推断随后被实际复评修正 |

## 方法与协作

| 文档 | 用途与限制 |
| :--- | :--- |
| [VALIDATING.md](VALIDATING.md) | 评测协议的演变；部分 RL 和旧面板章节描述历史。最终实验按冻结审查解释 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 工具、数据流与集群规范；长期计算走 Slurm，网络操作在登录节点 |
| [ONBOARDING.md](ONBOARDING.md) | 历史完整上手流程；最短赛后复现路径见 README |
| [SUBMISSION_POLICY.md](SUBMISSION_POLICY.md) | 历史提交、额度和读分纪律；截止后不再执行提交示例 |

## 历史研究与快照

| 文档 | 时间背景 |
| :--- | :--- |
| [ANALYSIS.md](ANALYSIS.md) | 08-13 市场与胜负机制，含官方最终评分讨论 |
| [LADDER_STATE.md](LADDER_STATE.md) | 08-14 快照及 08-23 复读；不能用作当前榜单 |
| [DISCUSSIONS.md](DISCUSSIONS.md) | 09-29 抓取的 166 帖、446 条发言；外部自述不等于我们已复现 |
| [LEADERBOARD.md](LEADERBOARD.md) | `tools/leaderboard.py` 生成的历史本地 run 快照 |

RL 线和较长实验台账于 09-29 归档。本地包为
`data/releases/rl-line-archive-2026-09-29.tar.gz`；历史 Git 可按路径恢复：

```bash
git show 7a5e91e^:docs/RUNS.md
```

同批归档包含 `CEILING.md`、`ROADMAP.md`、`INFRA.md`、`GAP-2000.md`、晨间战报和 `rl/`。
当前 `docs/RUNS.md` 是截止前新增台账，和旧的 18,920 行实验台账不是同一份内容。
归档资产与恢复方法见 README 的“数据归档”。

## 如何阅读这些证据

- 先看日期、引擎版本、对手范围和独立种子数，再解释一个数字。
- 本地提升、线上早期分数、最终 BT 和奖牌是不同层面的结论。
- 保留历史错误与后续更正；不把事后观察改写成预先验证。
- 原始分片、数据库和回放通常不随 Git 克隆；摘要不能代替它们重算完整统计。
