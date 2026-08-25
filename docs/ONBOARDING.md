# 上手指南 —— 你的第一个小时

> 本指南维护安装与第一次本地运行。项目当前结论和文档新旧关系先看
> [`INDEX.md`](INDEX.md)；RL 实验不要从本文拼 Slurm 命令，统一按
> [`INFRA.md`](INFRA.md) 与 [`../rl/TODO.md`](../rl/TODO.md) 执行。

写给零基础加入这个仓库的人。从上到下照做，大约一小时，读完你会跑过一次真实的锦标赛，
并读懂一个真实的结果。

---

## 0. 这个项目是什么，五句话

Kaggriculture 是一个 Kaggle **仿真类**比赛：你提交的是一个**程序**，不是预测结果，
它会和别人的程序一对一打 720 回合的农场季。奖金是十个等额的 $5,000 名额，所以目标是
**前 10**，不是第一。排名只看胜负 —— 金额差距完全不计入 —— 最终排行榜是对最后两周
所有对局做一次 Bradley-Terry 拟合。

这个仓库包含一个**可组合的策略库**（七个正交原子生成的 agent）、一个已经把
**340 万局**写进 SQLite 的**本地锦标赛系统**、一条**RL 训练主线**（与竞赛引擎
逐字节一致的批量张量引擎 + TorchRL，`rl/README.md`——2026-08-18 起的主要工作面），
以及由此得出的全部分析。本指南先教会你锦标赛系统（所有测量的地基）；RL 线上手
在读完本文后转 `rl/README.md`。

---

## 1. 环境搭建（10 分钟）

**一台普通笔记本就够了。** 这份指南全程假设你在笔记本上，不需要任何集群账号。
唯一的硬性要求是 Python 3.9+（3.11 与 Kaggle 自身运行时一致），加上你**自己的**
Kaggle API 凭据。

```bash
git clone <repo> Kaggriculture
cd Kaggriculture

bash tools/bootstrap.sh             # 建立 venv/，并用一局真实对局验证
```

它使用 `PATH` 里的 `python3`（可用 `PYTHON=/path/to/python3.11` 覆盖），
从 PyPI 安装全部依赖。

> 如果你**确实**有 Vulcan 集群账号，同一个脚本会自动检测并改走 `module load` 和
> Compute Canada 的 wheelhouse，两边环境等价。集群相关的一切都收在
> `docs/CONTRIBUTING.md`《在 Vulcan 集群上跑》 里，其余文档都不假设你有集群。

然后把**你自己的** Kaggle 凭据放进 `.kaggle/`：

```bash
# 两种任选其一；从 https://www.kaggle.com/settings/api 获取
printf '{"username":"YOU","key":"..."}' > .kaggle/kaggle.json
echo 'KGAT_...'                             > .kaggle/access_token
chmod 600 .kaggle/*
```

它们只留在这个目录里 —— `setup_env.sh` 把 `KAGGLE_CONFIG_DIR` 指向这里，所以
`$HOME` 下的副本**永远不会被使用**，这是有意为之（一台机器上可以放多个账号）。

```bash
source setup_env.sh                         # 每次会话，任意目录下
kaggle competitions list -s kaggriculture   # 确认认证可用

python tools/registry.py gen --plan all --out agents/lib   # 生成策略库
```

`agents/lib/` 是**生成的、且 git-ignored** —— 由 `agents/_engine.py` 加
`tools/registry.py` 派生。要改就重新生成，不要手编辑；改动任一源文件后也要重新生成。

`data/arena.sqlite` 同样 git-ignored，因为它对 git 来说太大而且可重建。请**拷贝**
而不是重跑 —— 它代表几十小时的算力：

```bash
# 有它的人导出：元数据快照（runs/agents/ratings，几百 KB，进 git）
python tools/sync.py export               # -> dist/arena-meta.sqlite.xz

# 你来安装
python tools/sync.py import dist/arena-meta.sqlite.xz

# 完整库（含全部 episodes，几百 MB）走本地传输，不进 git
python tools/sync.py export --full
```

集群上跑完任何锦标赛之后，先做数据对账再相信 `data/` 是完整的
（分片是手工 ingest 的，忘掉它是这里的默认失败模式）：

```bash
python tools/datalake.py status        # 数据库 vs 分片 vs dist/，一屏
python tools/datalake.py sync --prune  # 补入库，然后清分片
```

没有它所有工具照样能用；`tools/db.py` 会建一个空库，你从零开始积累自己的跑数。

**或者干脆不要这个文件。** 每一层都镜像到了 Cloudflare D1，带上 `*.secret` 凭据就能
直接查询全部对局：

```bash
python tools/d1.py check
python tools/d1.py top -n 20
python tools/d1.py query "SELECT json_extract(a.atoms,'\$.labour') labour,
    COUNT(*) n, ROUND(AVG(r.winrate)*100,1) winpct
  FROM ratings r JOIN agents a ON a.name=r.agent
  WHERE r.run_id=1 GROUP BY labour ORDER BY winpct DESC"
python tools/d1.py mirror local.sqlite    # 或者把它拉成一个本地文件
```

**为什么需要 bootstrap 而不是直接 `pip install -r`：** `kaggle-environments` 声明了
19 个依赖，其中 `open_spiel` 要从源码编译、在多数机器上会失败，而 Kaggriculture 实际
只用到三个。所以它是**故意**用 `--no-deps` 安装的。**其他**环境（`lux_ai_s3`、
`halite`、`open_spiel_env`）的导入错误会打到 stderr，这是预期内的。

---

## 2. 跑一局并看看它（10 分钟）

```bash
python tools/trace.py agents/barnyard.py starter
```

你会得到一张逐日的表：现金、雇工、地块、地块构成、棚内库存、市场价格。
**这是这个仓库里最重要的工具。** 这个引擎里的非法动作是**静默空操作** —— 不报错、
不扣钱 —— 所以 bug 看起来和"策略差"一模一样。这里找到的每一个五位数级别的缺陷，
都是靠读 trace 找到的，**从来不是**靠盯着最终分数。

然后确认 agent 扛得住折腾：

```bash
python tools/stress.py agents/barnyard.py -j 8
```

28 个病态配置（零现金、4×4 棋盘、只能放一件东西的棚子、一天只有一回合、免费雇工）。
一次崩溃会让整局作废，所以这一步在所有事情之前跑。

---

## 3. 理解命名（5 分钟）

一个策略的名字**就是**它的定义 —— 七个原子，顺序固定：

```
land - labour - produce - market - intel - muck - adapt

estate-crew-mixedfarm-metered-blind-muck-shopwise
  │      │        │        │       │      │      └ 畜群随商店抽样调整
  │      │        │        │       │      └ 收集每日免费肥料
  │      │        │        │       └ 忽略对手
  │      │        │        └ 价格低于下限时压住不卖
  │      │        └ 西瓜 + 草莓 + 小麦 + 牛 + 羊 + 鹅
  │      └ 每天最多 11 个雇工，工资不超过现金的 6%
  └ 四个 5×5 象限里的三个
```

**永远不要版本号。** 两个相同的配置不可能得到不同的名字，而看名字就知道这个 agent
在做什么，不用打开文件。

```bash
python tools/registry.py list          # 整个原子空间
ls agents/lib | head                   # 生成的库
```

`agents/barnyard.py` 是唯一手写的例外：最初那个 agent。`agents/legacy/` 存放被取代的
临时 agent，保留是因为已发布的结果引用了它们；它的 README 把旧名字映射到原子上。

---

## 4. 跑一次锦标赛（20 分钟）

```bash
export KG_FAST_ENV=1               # 跳过 schema 校验，结果相同，快 17%

python tools/tournament.py roundrobin \
    --agents agents/barnyard.py agents/lib/homestead-crew-orchardherd-flood-blind-muck.py starter \
    --seeds 8 --label "my-first-run" -j $(python -c 'import os;print(os.cpu_count())')
```

**现实地估算预算**：每核每秒约 0.375 局。八个核约 3 局/秒：

| 你想跑 | 8 核笔记本 |
|---|---|
| 上面这个三 agent 的跑数（48 局） | 十几秒 |
| 一次有统计效力的 A/B（每臂 384 局） | 约 4 分钟 |
| 对整个 `bench3` 场地筛一个 agent（约 3 千局） | 约 15 分钟 |
| 整个策略库的全量筛选（数万局） | 几小时 |

**前三行在笔记本上完全可行**，只有最后一行值得动用集群（`docs/CONTRIBUTING.md`《在 Vulcan 集群上跑》）。
另一个办法是直接拿别人跑好的证据：`python tools/sync.py import dist/arena-meta.sqlite.xz`。
这份快照带 `runs` / `agents` / `ratings`（每一次实验的形状和排名，0.42 MB），**不带 episodes**
—— 那是 3.4M 行、几个 GB，git 装不下，而且重跑就能复现。要完整的找有集群的人直接拷。

然后：

```bash
python tools/db.py stats                    # 有史以来跑过什么
python tools/db.py top --run latest         # 排名
python tools/leaderboard.py --run latest    # 重新生成 docs/LEADERBOARD.md + site/
```

---

## 5. 按这个顺序读知识（25 分钟）

如果你离开超过几天，先读 `docs/INDEX.md` 判断哪些文件仍是当前合同，再看当前主线。

1. `docs/INDEX.md` —— 当前合同、证据档案、历史快照和生成物怎么区分
2. `rl/TODO.md` + `docs/RUNS.md` 顶部 —— 当前诊断、执行阶段和已有判词
3. `docs/VALIDATING.md` —— 怎么判断你的改动是真的。出任何数字之前读
4. `docs/ANALYSIS.md` —— 这个游戏实际奖励什么
5. `docs/ROADMAP.md` §11 —— 停掉的路线：引擎改动的 A/B 记录（9 落地 / 7 被否）、
   为什么我们自己写的场地误导了我们一周
6. `rl/README.md` —— 张量引擎、TorchRL 训练与历代复盘
7. `docs/INFRA.md` / `docs/SUBMISSION_POLICY.md` —— 跑集群或碰排行榜之前分别必读

根目录 `README.md` 的《文档》一节按问题索引，`docs/INDEX.md` 维护状态和时间边界。

## 6. 会咬你的五件事

这些都不是假设；每一条都已经在这里造成过实际损失。

**非法动作静默失败。** 没有异常、没有日志、没有代价。错的地块、空的库存、满的棚子 ——
全都只是空操作。永远要 trace。

**`FEED` 从执行单位的库存里取小麦，不是从棚子里取。** 而 `PICKUP` 只在棚子旁边那四格
才有效。不显式安排雇工回去取饲料，所有单位就会一直忙着浇水，整个畜群饿死。
这一个 bug 值约 4.5 万。

**种子间的方差大于大多数调参效果。** 这个仓库早期 3–4 个种子的扫描，**重复跑会得出
互相矛盾的排序**。一个可信结果的下限是几百局；表格见 `VALIDATING.md` §5。

**共同随机数在这个环境里不成立。** `_end_of_day` 用同一个 RNG 抽杂草和商店解锁，而
杂草抽取次数正比于**双方**农场的空地数 —— 所以改你的 agent 会改变哪些商店解锁。
按种子配对有帮助，但抵消不了任何东西。

**策略空间是非传递的。** 存在实测到的石头剪刀布环：flood 胜 metered 胜 spite 胜 flood。
任何排名都是**相对于它的场地**的排名，换个场地就重排。这个仓库里有两次诚实的锦标赛
结论相反，原因正是这个。

---

## 7. 目前的状况

**这一节故意不写具体数字** —— 上一版（截至 08-12）在一周内全部过时。
现状的单点真相只有三处，按需要查：

- **天梯历史**：`docs/LADDER_STATE.md`（08-14 快照与 08-23 更正）；实时读数跑
  `python tools/ladder.py stats`。
- **主线进展**：`docs/RUNS.md` 顶部总览 + `rl/TODO.md`（下一步）。
- **两条线的分工与待办**：`docs/TODO.md` 开头；文档状态统一看 `docs/INDEX.md`。

三条不随快照过时的事实：天梯顶端是「剧本 + 市场外包装」而我们的原子库是在线调度器
（差 40 个百分点，不是调参能补的）；价值在外包装不在剧本（裸录音对带包装的 agent
是 0/3072）；5 次提交/天、只有最新两个活跃、**失活按时间顺序不按分数**——这条
让我们一夜损失过当时最好的两个提交。

---

## 8. 保住证据

`data/arena.sqlite` 是这里唯一不可替代的文件 —— 它是 **340 万局**的记录（约 7.5 GB），
所有文档里的数字都追溯到它。它是 git-ignored 的（对 git 来说太大），所以**它只存在于跑过它的那台
机器上**。

拿到它 / 分享它：

```bash
python tools/sync.py export --full      # 有它的人导出，几 MB
python tools/sync.py import <文件>       # 你安装
python tools/d1.py top -n 20            # 或者不下载，直接查远端镜像
```

如果你在 Vulcan 集群上工作，还有几条集群专属的注意事项 —— 全都收在
`docs/CONTRIBUTING.md`《在 Vulcan 集群上跑》，其余文档都不假设你有集群。
