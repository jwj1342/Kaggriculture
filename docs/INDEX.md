# 文档状态索引

**最后清点：2026-09-29（冲刺前的精简）。** 本页是文档入口，不承载实验结论。

> **当前站位（一句话）**：**RL 线已归档**（`data/releases/rl-line-archive-2026-09-29.tar.gz`
> 与该 commit 之前的 git 历史），连同 `RUNS.md`、`CEILING.md`、`ROADMAP.md`、`INFRA.md`、
> `GAP-2000.md`、两份晨间战报与全部实验脚手架。留下的是会得分的那条线：
> **挖来的计划 + 自适应包装层**（`agents/newlines/`、`tools/wrap.py`）。
> **不要用「每局多赚 X → 翻转 Y 场败局 → 胜率 Z → 分数」这条推理** —— 10 条已定型提交上
> margin 对分数的 Spearman 是 **−0.285**、败率 **+0.273**，都不过临界；我方钱中位 +0.891
> 也不是因果尺子（`56081484` 我方钱 91,316 高于 `56013382` 的 83,691，分数却 662 对 1695）。

## 当前执行文档

> **⚠️ 2026-09-29：截止前 28 小时。先读 [`ENDGAME.md`](ENDGAME.md)** —— 冲刺计划、
> 决策表、以及会让计划报废的操作陷阱。它是这段时间唯一的执行入口。


| 文档 | 作用 | 更新规则 |
|---|---|---|
| [`VALIDATING.md`](VALIDATING.md) | 本地评估、统计判词与 RL 产物验收 | 测量协议变化时更新 |
| [`SUBMISSION_POLICY.md`](SUBMISSION_POLICY.md) | Kaggle 提交额度、活跃槽位与读分纪律 | 竞赛规则或提交流程变化时更新 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 工具、数据流、集群操作与交付规范 | 工具接口变化时更新 |
| [`ONBOARDING.md`](ONBOARDING.md) | 新协作者从零跑通项目 | 安装或主入口变化时更新 |

最短阅读顺序：`ONBOARDING.md` -> `SUBMISSION_POLICY.md` -> `VALIDATING.md`。


## 证据与架构

| 文档 | 状态 |
|---|---|
| [`ANALYSIS.md`](ANALYSIS.md) | 2026-08-13 市场/胜负机制研究；**含最终评分规则**（截止时锁定 active 两个 → 再跑约两周 → 一次 Bradley-Terry 整体拟合，host 确认） |
| [`LADDER_STATE.md`](LADDER_STATE.md) | 08-14 快照及 08-23 复读更正；**不是实时榜单**，实时用 `python tools/ladder.py stats` |
| [`DISCUSSIONS.md`](DISCUSSIONS.md) | **2026-09-29 拉取的竞赛讨论区情报**（166 帖 / 446 条发言）：评分机制与路径依赖、别人成功与失败的路径、两条指向动物经济的外部证据。**全部是他人自述，未经我们复现** |

## 历史快照

已归档的文档（`data/releases/rl-line-archive-2026-09-29.tar.gz`，或 `git show 7a5e91e^:<路径>`）：
`RUNS.md`（18,920 行实验台账）、`CEILING.md`、`ROADMAP.md`、`INFRA.md`、`GAP-2000.md`、
`ACCEPTANCE-2026-08-21.md`、`MORNING-2026-08-21/22.md`、`TODO.md`，以及 `rl/` 全部内容。

## 自动生成

[`LEADERBOARD.md`](LEADERBOARD.md) 是 `tools/leaderboard.py` 生成的历史 run 快照，
不要手改，也不要把它当 Kaggle 实时榜单。要刷新就重跑生成器并连同来源 run 一起记录。

实时外部状态不应硬编码进“当前”文档。天梯用 `python tools/ladder.py stats` 刷新，集群用
`squeue -u "$USER"` / `sacct` 查看；形成可引用结论后写进提交说明或 `LADDER_STATE.md`。
