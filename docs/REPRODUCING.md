# 复现、使用与仓库导航

本页汇集从 README 移出的运行步骤、工具导航和归档说明。项目概览见 [README](../README.md)，文档全貌见 [文档索引](INDEX.md)。

## Notebook 入口

**[在 Kaggle 阅读与运行](https://www.kaggle.com/code/jwj1342/kaggriculture-final-strategy-and-lessons)** · [仓库中的 .ipynb](../notebooks/postmortem/kaggriculture-final-strategy-and-lessons.ipynb)

Notebook 包含中文复盘、英文摘要、确认实验图表，以及两份与实际上传字节一致的最终源码。运行全部单元格会生成可下载源码、许可证、原审查记录和校验清单；原始提交包另附 Release 下载链接。无需 API 密钥、GPU 或联网，也不会发起比赛提交。

## 复现与使用

### 1 · 先阅读，再决定复现范围

Notebook 的 **Run All** 只需要常规 Python、pandas、matplotlib 和 IPython：它校验并导出最终源码、展示冻结统计摘要和图表。**它不会重新计算原始逐世界 bootstrap，也不重跑几十万局锦标赛。** 完整实验还需要对应对手源码、manifest、原始分片及指定引擎。

### 2 · 建立游戏运行环境

```bash
git clone https://github.com/jwj1342/Kaggriculture.git
cd Kaggriculture

# 仅新环境执行：此脚本会重建现有 venv
bash tools/bootstrap.sh
source setup_env.sh

# 冻结赛后复现使用的引擎；普通安装脚本默认跟随更新
python -m pip install --no-deps kaggle-environments==1.32.7
```

最终确认使用 Python 3.11。`requirements/lock.txt` 是历史集群环境快照，含平台专属依赖；不要把它当成跨平台的一键安装清单。联网下载与 Kaggle 操作放在登录节点；评测、训练和大规模诊断放到 Slurm。

### 3 · 校验最终文件

```bash
(cd submissions/2026-09-30-mixed-deferred && sha256sum -c SHA256SUMS)
(cd submissions/2026-09-30-wool-priority && sha256sum -c SHA256SUMS)
```

### 4 · 做一次本地比较

```bash
# 集群：先检查 slurm/eval.sh 内的账户、项目路径和资源设置
sbatch slurm/eval.sh h2h \
  submissions/2026-09-30-mixed-deferred/main.py \
  submissions/2026-09-30-wool-priority/main.py --seeds 32

# 普通工作站：相同入口可直接运行，小样本仅用于复现流程
python tools/eval.py h2h \
  submissions/2026-09-30-mixed-deferred/main.py \
  submissions/2026-09-30-wool-priority/main.py --seeds 4 -j 2
```

两份最终版本的直接对打不能替代原多对手确认实验。旧 `eval.py` 输出中的 `win rate` 实际含平局半分，其区间按对局计算，没有保留世界簇；上述命令只用于跑通比较流程，不复现[最终方案与实验记录](FINAL_SOLUTION.md)中的正式区间或验收门。统计协议及历史变化见 [VALIDATING.md](VALIDATING.md)；最终审查记录中的协议优先用于解释该记录中的数字。

## 仓库地图

```text
Kaggriculture/
├── README.md                 项目总览与最终交付入口
├── notebooks/postmortem/     赛后 Notebook、冻结摘要、Kaggle 发布配置
├── submissions/              按日期冻结的源码、原始包、许可证与审查
├── agents/                   手工引擎、规则表、早期模块化策略和历史探针
├── benchmarks/               固定历史回归对手
├── tools/                    生成、测量、诊断、打包、数据与发布工具
├── slurm/                    集群作业入口；长任务在计算节点运行
├── docs/                     协议、机制分析、执行记录及历史快照
├── reference/                引擎、官方说明与公开参考 Notebook
├── requirements/             基础依赖、引擎安装策略和旧环境快照
├── tests/                    统计工具测试
├── dist/                     可重建产物；保留轨迹库等已跟踪快照
└── data/                     本地数据库、评测分片、回放和归档（通常忽略）
```

生成的 `agents/lib/`、`agents/wrapped/`、`agents/newlines/` 等目录通常不在 Git 中。最终可交付策略以 `submissions/2026-09-30-*/` 的冻结文件为准。RL 线于 09-29 归档，可从归档包及历史提交恢复。

<details>
<summary><strong>工具导航：按要完成的事情查找</strong></summary>

| 任务 | 入口 |
| :--- | :--- |
| 安装环境 / 生成 Notebook | `bootstrap.sh`、`build_notebook.py`、`build_postmortem.py` |
| 策略与对手生成 | `registry.py`、`wrap.py`、`hybrid.py`、`ghost.py`、`lines.py`、`make_probes.py`、`fetch_fields.sh` |
| 对战评测与统计 | `eval.py`、`tournament.py`、`stats.py`、`ruler_calib.py`、`opening_value.py` |
| 看一局发生了什么 | `trace.py`、`board.py`、`tracelib.py`、`stress.py` |
| 截止前专项工作流 | `endgame_eval.py`、`endgame_diagnostics.py`、`endgame_preflight.py`、`endgame_ingest.py`、`endgame_watch.py` |
| 数据库与同步 | `db.py`、`datalake.py`、`sync.py`、`d1.py` |
| 线上记录与报告 | `ladder.py`、`topeps.py`、`leaderboard.py`、`fieldtable.py` |
| 历史打包与发布 | `package.sh`、`kaggle_cli.py`、`publish.sh` |

所有入口位于 [tools/](../tools/)。部分历史脚本需要本地数据或项目专属配置；使用前查看 `--help` 和 [协作说明](CONTRIBUTING.md)。

</details>

## 数据归档

Git 保存代码、结论、提交身份和 Notebook；大型 SQLite、原始回放及实验分片单独归档。归档入口为 [赛后 Release](https://github.com/jwj1342/Kaggriculture/releases/tag/postmortem-2026-10-01)，包含本地约 497 万局数据库、独立 D1 SQL/SQLite、RL 历史包和最终提交。所有归档已回下载校验，D1 两种格式均恢复成功；对应 Cloudflare D1 已删除，本地原件保留。范围、证据与恢复命令见 [ARCHIVE.md](ARCHIVE.md)。
