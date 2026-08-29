# 文档状态索引

**最后清点：2026-08-29。** 本页是文档入口，不承载实验结论。看到其他文件里的
“当前”“最新”“在跑”时，先用这里的状态和日期判断它是不是历史语境。

## 当前执行文档

| 文档 | 作用 | 更新规则 |
|---|---|---|
| [`rl/TODO.md`](../rl/TODO.md) | 当前 RL 诊断、Phase 0–4 与验收门 | 路线变化时更新；唯一 RL 待办队列。**先读顶部「当前站位总表」**：这个项目的"步骤"有四套层级（Phase 0–4 / G1–G3 门 / G1 六步战术计划 / 四层分工），总表是唯一的对齐入口 |
| [`INFRA.md`](INFRA.md) | Slurm、Python 环境、profiling、资源与提交纪律 | 集群实测或脚本变化时更新 |
| [`VALIDATING.md`](VALIDATING.md) | 本地评估、统计判词与 RL 产物验收 | 测量协议变化时更新 |
| [`SUBMISSION_POLICY.md`](SUBMISSION_POLICY.md) | Kaggle 提交额度、活跃槽位与读分纪律 | 竞赛规则或提交流程变化时更新 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 工具、数据流、集群操作与交付规范 | 工具接口变化时更新 |
| [`ONBOARDING.md`](ONBOARDING.md) | 新协作者从零跑通项目 | 安装或主入口变化时更新 |
| [`TODO.md`](TODO.md) | 两条工作线分流与挂起的剧本线事项 | RL 细项不在这里重复 |

当前路线的最短阅读顺序是：`rl/TODO.md` -> `INFRA.md` -> `RUNS.md` 顶部总览；
准备验收或提交时再读 `VALIDATING.md` 与 `SUBMISSION_POLICY.md`。

## 证据与架构

| 文档 | 状态 |
|---|---|
| [`RUNS.md`](RUNS.md) | 只增不删的实验台账；顶部总览是截至 2026-08-28 的当前判词，后文按发生时间**正序**阅读（最新判词在文件末尾，不在顶部） |
| [`ANALYSIS.md`](ANALYSIS.md) | 2026-08-13 市场/胜负机制研究；引擎事实仍有用，但不是当前 RL 路线图 |
| [`ROADMAP.md`](ROADMAP.md) | 覆盖到 2026-08-14 的剧本线证据档案；当前路线已转到 `rl/TODO.md` |
| [`../rl/README.md`](../rl/README.md) | RL 架构、资产和历代复盘；“终局判词”以下含第一代历史说明 |
| [`../rl/tensor_env/README.md`](../rl/tensor_env/README.md) | 当前张量引擎接口与正确性门 |
| [`../rl/tensor_env/DESIGN.md`](../rl/tensor_env/DESIGN.md) | 2026-08-16 至 08-18 的张量化设计与实测修订；不是当前资源申请规则 |

## 历史快照

以下文件保留当时的判断、路径和队列，**不能据此恢复 job、寻找已删除 worktree 或决定
今天要跑什么**：

- [`GAP-2000.md`](GAP-2000.md)：截至 2026-08-23 的差距诊断；已被 08-24 的信用分配
  总结与新 Phase 路线接续。
- [`LADDER_STATE.md`](LADDER_STATE.md)：08-14 快照及 08-23 复读更正；不是实时榜单。
- [`MORNING-2026-08-21.md`](MORNING-2026-08-21.md)、
  [`MORNING-2026-08-22.md`](MORNING-2026-08-22.md)：交班快照。
- [`ACCEPTANCE-2026-08-21.md`](ACCEPTANCE-2026-08-21.md)：当日候选验收包；部分 worktree
  产物已在 08-24 清理。

## 自动生成

[`LEADERBOARD.md`](LEADERBOARD.md) 是 `tools/leaderboard.py` 生成的历史 run 快照，
不要手改，也不要把它当 Kaggle 实时榜单。要刷新就重跑生成器并连同来源 run 一起记录。

实时外部状态不应硬编码进“当前”文档。天梯用 `python tools/ladder.py stats` 刷新，集群用
`squeue -u "$USER"` / `sacct` 查看；形成可引用结论后再写入 `RUNS.md`。
