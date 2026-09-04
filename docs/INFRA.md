# RL 训练基础设施与提交纪律

本页是当前训练线的操作合同。实验结论仍写入 `docs/RUNS.md`，研究路线写入
`rl/TODO.md`；这里仅规定怎样申请资源、记录证据和避免无效消耗。

## 已测瓶颈（数据截至 2026-08-24）

| 项目 | 实测 | 结论 |
|---|---:|---|
| H100，B=1024 | 10,469 lane-steps/s | 单卡参考值 |
| 每轮采集 / 总训练阶段 | 约 68 / 69.5 秒 | 约 98% 时间在 rollout，PPO 更新不是主瓶颈 |
| GPU util，472 个 2 秒样本 | 中位 98%，均值 73.9% | 有短间隙，但不是长时间等 Python |
| GPU util <10% / >=90% | 8.3% / 55.9% | “显卡大量空转”不成立 |
| H100 B=1024 峰值 | 47.34 GiB（`--rb-free`） | 单卡单进程；不要共卡 |
| H100 B=1536 | 首轮 15,166 sps，随后 OOM | 不可作为稳定配置 |
| CPU 16 核，B=1024 | 6,304–10,939 sps，依节点而变 | 拥堵时默认路径 |
| CPU B=1024 RSS | 约 76.5 GiB（有效训练链） | 申请 96G；140G 是过量预留 |
| 宏观反事实审计，8 核 | 1.01–1.48 GiB RSS | 默认 4G，不再沿用 24G |
| 官方引擎配对评估，8 worker | 1.44 GiB RSS | 8 worker 用 4G；32 worker 默认 12G |

GPU sweep 的零利用率样本主要来自进程启动、不同 probe 之间和 OOM 后清理。
`nvidia-smi` 的 utilization 只说明采样窗口内是否有 kernel 执行，不能等同于 SM
occupancy；因此它能否定“整段空转”，不能证明 kernel 已经高效。当前最有价值的性能
工作仍是缩短 rollout 内的 719 次环境/策略小算子循环，或在通过行为 A/B 后压缩
observation，而不是增加 PPO epochs、CPU 核数或同卡进程。

## 正式提交入口

```bash
source setup_env.sh
python tools/submit_rl.py --run option-cf-v1 --links 3 \
  --hypothesis "persistent option raises completed build sequences" \
  --acceptance "paired 3-seed build completion +20%, no roster regression" -- \
  --config rl/configs/granger.yaml --seed 11
```

默认使用 CPU：16 核、96G、每 link 25 分钟。首个 link 是 5 分钟 pilot；后续仅以
`afterok` 运行，父任务失败时不会烧后续资源。本集群不会自动移除
`DependencyNeverSatisfied`，发现失败后应用 `scancel` 清理剩余 job。先用 `--dry-run`
检查展开后的命令。续跑必须加 `--resume`，新实验必须使用空 run 名。最多一次提交 8 个
link，更多预算要先读取中期曲线并重新预登记。pilot 还会执行吞吐硬门：CPU 默认
5,000 sps、GPU 默认 8,000 sps，
可用提交器的 `--min-sps` 为新架构预登记不同阈值；NaN/Inf 会直接使 job 非零退出。

GPU 只有在短 pilot 已证明吞吐或功能必须依赖 CUDA 时使用：

```bash
python tools/submit_rl.py --run option-cf-gpu-v1 --backend gpu --links 2 \
  --gpu-justification "counterfactual branch batching measured >1.5x CPU" \
  --hypothesis "..." --acceptance "..." -- \
  --config rl/configs/granger.yaml --seed 11
```

提交器拒绝覆盖 `--device`、checkpoint、计时、线程和 walltime 参数；拒绝 tracked
改动以及未跟踪的代码/配置文件（普通导出产物不阻塞）；要求 GPU 理由；记录
`submission.json`（commit、完整 argv、假设、阈值、job IDs）。`--allow-dirty` 只用于
故障诊断，不用于可比较实验。配置、初始化 checkpoint、residual prior、bank 与 tape
等文件也记录 SHA-256。计算节点启动时会复核源码和这些输入；排队期间若内容变化，job
会在训练前以退出码 42 停止，避免 manifest 与实际执行内容错位。

不训练模型的 Phase 0/1 宏观审计使用独立但同样受控的入口：

```bash
python tools/submit_macro_audit.py --run macro-phase0 \
  --hypothesis "frozen candidates differ on one fixed field" \
  --acceptance "select by registered full-field terminal margin" -- \
  baseline --checkpoint rl/runs/chisel/latest.pt --opponent starter
```

它固定 CPU 资源（默认 8 核、4G）、管理输出路径，并把 checkpoint、tape 对手、完整审计参数、假设、
阈值和 job ID 写入 `submission.json`。`slurm/rl_macro_audit.sh` 拒绝没有 manifest 的
手工提交，避免评测作业绕过训练线已经执行的源码与输入哈希门。

Phase 2 的 option-lite PPO 使用独立入口。它冻结 turn-level checkpoint，只训练每季约
7 次决策的高层 categorical controller：

```bash
python tools/submit_macro_rl.py --run macro-ppo-v1 --links 2 \
  --hypothesis "milestone-conditioned selector beats either fixed route" \
  --acceptance "held-out paired margin CI > 0 and cleo has a win" -- \
  --checkpoint rl/runs/anvil/latest.pt --B 32 --iters 1000 \
  --eval-before --eval-every 5 --eval-lanes 16
```

该路径当前固定 CPU（默认 8 核、16G）：route 执行器包含逐任务分派与 Python 标量分支，
尚无 GPU 加速证据。`train.jsonl` 记录每季高层决策数、逐 Option 选择数/持续时间/熵贡献、
终止原因和 terminal margin；probe 在相同 seed 上同时运行 controller、固定 route 和固定
`route_s34`，直接报告配对 margin 差。checkpoint、对手 tape、argv、假设和门槛同样写入 manifest，
后续 link 只通过 `afterok` 恢复。

## 不可重建的文件放在哪（2026-09-04）

组织规则明确禁止把唯一副本留在 `/scratch`（不备份、会被定期清理）。
以下几份都曾**只**存在于 scratch 上，现已复制到有备份的 project 空间：

    /home/jwj/projects/def-zhouyang/kaggriculture-artifacts/

| 文件 | 为什么不可重建 |
|---|---|
| `kg-opponent-fields-2026-08-18.tar.gz` | **`agents/spar/` 的唯一恢复源。** `CLAUDE.md` 要求 spar 进每一个场且**绝不重新生成**，所以这个 tarball 坏掉等于那条纪律无法执行 |
| `kg-rl-agent-deliverable-guarded.tar.gz` | RL 交付物快照 |
| `tracerecords-2026-09-04.jsonl.xz` | 逐局回放记录（27 MB 原始）。重建 = 约 69 分钟的限流退避，见下 |
| `tracelib-2026-09-04.json.xz` | 计划库索引（889 计划）。也在 `dist/` 里被 git 跟踪 |

`data/releases/` 与 `data/tracelib/` 仍留在 scratch 作为工作副本；project 那份是备份，
不是工作路径。**复制后用 md5 校验过。**

**Kaggle 拉取的限流现状（09-04 实测，比 8 月紧得多）**：
`tools/tracelib.py` 的 docstring 记的"16 workers 安全"是 8 月的标定。09-04 两次实测：
1,000 局在 `-j 6` 下 **23 次 429**；900 局在 `-j 4` 下 **207 次 429**
（后者日期列表是缓存命中，请求全花在下载上，且当天已累计拉了约 2,100 局）。
每次退避 20 秒，207 次 ≈ **69 分钟纯等待**，两次都跑完 100% 没丢数据。
默认已降到 `-j 6`。**规划挖掘时按"一天约 2,000 局"估容量，不要按吞吐估。**

## 每个 job 自动留下什么

- stdout 的 `RUN-META`：commit、host、backend、CPU 数、run ID。
- `rl/runs/<run>/timing.csv`：startup、collect、GAE、prepare、update、metrics、probe、
  checkpoint、总墙钟和两种吞吐。
- 所有 GPU job 的 `logs/profiles/<run>/<job>-gpu.csv`：每 2 秒的利用率、显存和功率。
- `PROFILE` 日志行：即使 CSV 搬走，阶段计时仍能从 stdout 恢复。

训练阶段吞吐 `train_sps` 不含 metrics/probe/checkpoint；`wall_sps` 包含整轮所有开销。
启用 `--profile-timing` 时 CUDA 会在阶段边界同步，数字可归因，但会带来轻微开销。

## 复盘命令

```bash
python tools/slurm_audit.py --job 20360593 \
  --timing rl/runs/<run>/timing.csv \
  --gpu logs/profiles/<run>/20360593-gpu.csv
```

报告同时给出排队时间、运行时间、CPU efficiency、各训练阶段占比、GPU 忙/闲样本和
峰值显存。比较 CPU/GPU 时必须同时报告吞吐与 `submit -> end` 总周转时间；只报运行中
sps 会在当前拥堵集群上得出错误决策。

## 提交前后检查表

1. 先在 `rl/TODO.md` 指定路线，再写单一变量、假设、随机种子和验收阈值。
2. 提交前用 `sbatch slurm/rl_test.sh` 跑 RL 门，并执行
   `python tools/submit_rl.py ... --dry-run`；正式实验使用已提交的代码。
3. 新 batch/模型先跑 pilot。OOM、checkpoint 权限错误、NaN、吞吐低于基线 20% 均停止链。
4. 不在一张 H100 上启动多个训练进程；不使用 `afterany`；不手工复制长 `sbatch` 命令。
5. 评测继续走 CPU array/shard，worker 不写 SQLite，由单一 ingest 进程合并。
6. 跑完用 `tools/slurm_audit.py` 复盘，把统计证据和判词写进 `docs/RUNS.md`。
7. Kaggle 提交仍遵守最多半天一次、至少输掉三分之一对局后才采信分数的规则。
