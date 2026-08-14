# 在 Vulcan 集群上跑（可选）

**这份文档只对能访问 Vulcan 的人有用。其他所有文档都不假设你有集群。**

这个项目在普通笔记本上功能完整 —— 同样的工具、同样的数据库、同样的结论。集群唯一
带来的是**吞吐量**：一次全库筛选在笔记本上要几小时，在这里是几分钟。如果你没有集群
账号，跳过这份文档，按 `docs/VALIDATING.md` 里给出的局数在本地跑，只是慢一些。

一个换算，方便你判断需不需要：**每核每秒约 0.375 局**（带 `KG_FAST_ENV=1`）。

| 你想跑 | 8 核笔记本 | 512 核集群 |
|---|---|---|
| 一次 A/B（每臂 384 局） | 约 4 分钟 | 4 秒 |
| 一次形状扫描（约 7 万局） | 约 6.5 小时 | 3 分钟 |
| 一次引擎消融（约 14 万局） | 约 13 小时 | 6 分钟 |

**前两行在笔记本上是完全可行的。** 只有第三行真正需要集群。

---

## 基本规则

- **永远不要在登录节点跑重活。** 一局（约 2.7 秒）可以，锦标赛不行。
- **这个负载是纯 CPU 的 —— 永远不要申请 GPU。** 它是单线程 Python，其中 42% 的时间
  花在框架内部的 `deepcopy` 上。
- **短任务立刻开跑，长任务排队。** 同样的工作量在 `--time=03:00:00` 加每任务 64 核下
  排了 78 分钟；在 `--time=00:30:00` 加 32 核下，十六个节点上立即开始。
- **`$SCRATCH` 不备份**，60 天不活动会被清理（年龄取 `min(atime, ctime)`）。
  仓库放在 `$SCRATCH` 下，但把 `data/arena.sqlite` 拷一份到 `~/projects/`。

## 分片跑大规模锦标赛

```bash
sbatch --array=0-15 --cpus-per-task=32 --mem=40G --time=00:30:00 \
    slurm/tournament_array.sh panel \
    --agents agents/mine/*.py --panel agents/bench3/*.py \
    --seeds 96 --jobs 32 --label mylabel

squeue -u $USER
python tools/tournament.py ingest --shards data/shards/mylabel
```

每个 array 任务跑作业列表的一个**跨步切片**（`jobs[k::N]`，不是分块 —— 相邻的作业是
同一对手在相邻种子上，分块会把所有慢的对局塞给同一个任务），并写一个只追加的 JSONL
分片。

**array 任务绝对不能打开 `data/arena.sqlite`。** 48 个任务并发注册 manifest 曾经把它
写坏过一次（全量恢复了，见 `docs/RUNS.md` 的数据完整性事故）。分片写 JSONL，由**一个**
`ingest` 进程做全部写入。`--shard` 和 `--from-run` 同时出现是硬错误。

`KG_FAST_ENV=1` 跳过 jsonschema 校验，实测结果逐字节相同，快 17%。`slurm/` 下的脚本
已经帮你设好了。

## 交互式调试

```bash
salloc --account=aip-zhouyang --time=02:00:00 --cpus-per-task=16 --mem=32G
```

拿到节点后可以直接跑代码。长时间的交互式会话建议配合 `tmux`，SSH 断线会杀掉 `salloc`。

## 环境

`bash tools/bootstrap.sh` 会自己检测集群并 `module load python/3.11.5`，`numpy`/`pandas`
从 Compute Canada 的 wheelhouse 取。在笔记本上同一个脚本走 PyPI。**两边环境等价**，
所以在笔记本上验证过的东西在集群上跑出来是一样的。

## 给没有集群的协作者

你缺的只是速度，不是能力。三条实用建议：

1. **用 `tools/eval.py h2h` 而不是全场地面板。** 96 个种子的两两对比在 8 核上约一分钟，
   足以分辨 10 分的差距。
2. **拿别人跑好的数据库，不要自己重挣。**
   `python tools/sync.py import dist/arena-meta.sqlite.xz` —— 那是几小时的算力压成
   几 MB。或者用 `tools/d1.py` 直接查远端镜像，连文件都不用下。
3. **分片格式是通用的。** 如果有人在集群上帮你跑了一批，你拿到 `data/shards/<label>/`
   下的 JSONL 就能自己分析，`docs/VALIDATING.md` §5 有现成的代码。
