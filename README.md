# Kaggriculture

Kaggle **Kaggriculture** 仿真比赛的工作仓库
（<https://www.kaggle.com/competitions/kaggriculture>）。

你提交的是一个**程序**，不是预测结果。它在实时天梯上和别人的程序一对一打 720 回合的
农场季。排名只看胜负 —— 金额差距完全不计入。

- **奖金** $50,000 分成十个等额的 $5,000 名额，所以目标是**前 10**。
- **时间线** 2026-07-29 开赛 · 2026-09-23 报名与组队截止 · 2026-09-30 最终提交 ·
  排行榜约 2026-10-15 收敛。
- **规模** 截至 2026-08-07 有 2,903 支队伍、5,376 次提交。
- **状态** 排行榜最高 **1363.7**（我们自己引擎的最好成绩是 857.6）。本地累计
  **1,297,916 局**，另有真实天梯回放摘要。

### → 新来的？读 [`docs/ONBOARDING.md`](docs/ONBOARDING.md)，一小时，读完你会跑过一次真实锦标赛。

### → 离开了几天？读 [`docs/ROADMAP.md`](docs/ROADMAP.md)，它开头就讲哪些结论被推翻了。

---

## 环境搭建

**一台普通笔记本就够了** —— 唯一的硬性要求是 Python 3.9+。

```bash
bash tools/bootstrap.sh          # 建立 venv/，用一局真实对局验证
# 把你自己的 Kaggle 凭据放进 .kaggle/  （见 ONBOARDING §1）
source setup_env.sh              # 每次会话，任意目录下都能用
```

`setup_env.sh` 激活 `venv/` 并把**所有**凭据和缓存路径重定向到这个目录，所以这里的
任何操作都不会碰你的主目录。

依赖放在 `requirements/`，按**安装语义**而不是按用途拆分，因为一个扁平文件表达不了：

| 文件 | 安装方式 | 为什么 |
|---|---|---|
| `base.txt` | 普通 `pip install -r` | numpy、pandas、kaggle、kagglehub、jupytext |
| `nodeps.txt` | `pip install --no-deps -r` | `kaggle-environments` 声明了 19 个依赖，包括编译失败的 `open_spiel`；Kaggriculture 实际只需要其中三个 |
| `lock.txt` | 不安装 —— 生成物 | 一个已知可用的集群环境的审计快照 |

用 `bash tools/bootstrap.sh --freeze` 重新生成 lock。

> `data/arena.sqlite` 是唯一不可替代的文件，而且是 git-ignored 的 —— 用
> `tools/sync.py` 分享，不要重跑。
>
> 有 Vulcan 集群账号的人另见 [`docs/CLUSTER.md`](docs/CLUSTER.md)；**其余文档都不
> 假设你有集群**。

## 日常命令

```bash
python tools/trace.py agents/barnyard.py starter        # 逐日追踪一局
python tools/stress.py agents/barnyard.py -j 8          # 28 个病态配置
python tools/registry.py list                           # 原子空间
python tools/registry.py gen --plan all --out agents/lib
python tools/db.py stats                                # 有史以来跑过什么
python tools/sync.py export --full                      # 可分享的压缩快照

# 锦标赛：-j 给多少核就用多少（集群上走 Slurm，见 docs/CLUSTER.md）
export KG_FAST_ENV=1                                    # 结果相同，快 17%
python tools/tournament.py roundrobin --agents a.py b.py --seeds 96 -j 8
python tools/tournament.py panel --lib agents/lib --panel agents/bench3/*.py --seeds 8 -j 8

python tools/leaderboard.py --run latest                # 重新生成排行榜
```

`slurm/` 只在 Vulcan 上有意义；那里的每个脚本都是薄封装，调用上面同一批工具。

---

## 核心思路

每个策略是**七个正交原子**各取一个选项的组合，所以它的名字**就是**它的定义，
而策略库是一个笛卡尔积，不是一堆文件：

```
land - labour - produce - market - intel - muck - adapt

smallhold-crew-mgtightgrain-flood-blind-compost-shopwise
```

第七条轴 `adapt` 是唯一关于**城镇**而不是农场或对手的：商店是**有放回**抽样的，
所以单个产品的需求在不同对局间会摆动 **49 倍**。

**这个仓库里没有任何版本号。**

一切在接近排行榜之前都先在本地测量。`tools/tournament.py` 跑面板筛选（`O(n)`）和
循环赛（`O(n²)`），把每一局持久化到 SQLite，并拟合 **Bradley-Terry** 强度 ——
和 Kaggle 用于最终排行榜的是同一个估计量。

每一局都落进 `data/arena.sqlite`，并镜像到 **Cloudflare D1**，所以协作者不需要
下载文件就能查询全部证据。同步是单向的，本地到远端；见 `docs/CONTRIBUTING.md`
的 "The sync contract"。

---

## 各部分怎么组合

四层。每层只依赖它上面那层，`tools/` 以下的一切都是重新生成而不是手编辑的。

```
  定义层        tools/registry.py          七张原子表 + 组合方案
                agents/_engine.py          唯一的执行路径，CONFIG 块由生成器写入
                        │
                        │  registry.py gen --plan all
                        ▼
  策略层        agents/lib/*.py            独立的、可直接提交的 agent
                agents/spar/*.py           从真实天梯回放重建的对手 —— 每个场地都要带上
                agents/lib/manifest.json   名字、原子、源码哈希
                        │
                        │  tools/tournament.py  (集群上分片跑)
                        ▼
  证据层        data/arena.sqlite          有史以来的每一局
                  agents    名字、原子、源码哈希
                  runs      每场锦标赛一行
                  episodes  结果、商店抽样、终局价格、约 1.6 KB 摘要 x2
                  ratings   每次跑数的 Bradley-Terry 快照
                        │
            ┌───────────┼────────────────────┐
            │           │                    │
            ▼           ▼                    ▼
  输出层   db.py      leaderboard.py      人工分析 -> docs/
           查询       docs/LEADERBOARD.md
                      site/leaderboard.html -> 发布的页面
```

**为什么是这个形状。** 策略从不手写，所以两个人不可能用不同名字造出同一个策略，
而名字永远描述这个 agent 在做什么。每一个被引用过的数字都能追回到同一个数据库里的
行，所以一条主张可以用一次查询复核，而不用重跑。发布页面是那个数据库的纯函数，
刷新它是一条命令，而且 URL 永远不变。

从这条主线旁伸出去的，是回答更窄问题的工具：`tools/trace.py`（这局为什么这样走）、
`tools/stress.py`（扛不扛得住折腾）、`tools/eval.py`（A 是否优于 B，带置信区间）、
`tools/hybrid.py`（开局值多少钱）、`tools/lines.py`（天梯实际在跑哪几条线）。

## 目录结构

```
agents/
  _engine.py       策略：唯一的执行路径；它的 CONFIG 块是生成的
  kg_rules.py      规则：作物表、价格模型、商店图 —— 无策略，引擎再平衡时只改这里
  lib/             生成的策略 + manifest.json  (git-ignored)
  spar/            从天梯回放重建的陪练场地  (git-ignored)
  ref/             第三方参考 agent (MIT，见其 NOTICE)  (git-ignored)
  ghosts/          回放真实榜首轨迹的开环对手  (git-ignored)
  lines/           天梯上每条不同剧本的一个代表  (git-ignored)
  bench3/          标准参考场地  (git-ignored)
  barnyard.py      手工调优的最初版本
  legacy/          被取代的临时 agent，因为文档引用而保留
tools/
  bootstrap.sh     从零建立 venv/
  registry.py      原子定义、组合方案、代码生成
  tournament.py    面板 / 循环赛，持久化到 SQLite
  leaderboard.py   从数据库渲染 docs/LEADERBOARD.md + site/leaderboard.html
  db.py            所有对局的 schema 和查询
  eval.py          带 Wilson 区间和配对 bootstrap 的 A/B
  stress.py        28 个病态环境配置
  trace.py         一局的逐日追踪
  ladder.py        拉取我们自己的天梯对局，19 MB 回放压成 1.4 KB 摘要
  topeps.py        消化 Kaggle 每日的榜首对局数据集
  ghost.py         把榜首轨迹变成本地对手
  lines.py         把那些轨迹聚类成它们实际在跑的"线"
  hybrid.py        把录制的开局拼接到我们的引擎上，测量开局的价值
  fetch_fields.sh  重建新克隆没有的全部对手场地
  package.sh       把 agent 打成 Kaggle 要的 tar.gz（策略 + 规则平铺在归档根）
  stats.py         Bradley-Terry 和 Wilson —— 仓库里唯一的纯模块，有单元测试
docs/              全部知识与结果 —— 见下方表格
data/arena.sqlite  证据层  (git-ignored；用 tools/sync.py 分享)
reference/
  engine/          kaggriculture.py 的副本 —— 实际运行的规则
  docs/            比赛数据集里的官方 README.md 和 AGENTS.md
requirements/      base.txt、nodeps.txt、lock.txt —— 按安装语义拆分
submissions/       每一份发给 Kaggle 的文件的精确快照
slurm/             Vulcan 专用封装（可选，见 docs/CLUSTER.md）
site/              生成的排行榜页面
```

**生成物，永不手编辑：** `agents/lib/`、`agents/spar/`、`docs/LEADERBOARD.md`、
`site/leaderboard.html`、`notebooks/baseline.ipynb`。**git-ignored：** 以上加
`venv/`、`.cache/`、`.kaggle/`、`data/`、以及 `agents/` 下所有生成的对手场地。

**新克隆一个对手都没有** —— 先跑 `bash tools/fetch_fields.sh`。

## 常见问题

三个每个人第一周都会问的问题。更长的答案在链接后面；这里的内容够你动起来。

### 1. 我该怎么提交到 Kaggle？

**先配凭据。** `setup_env.sh` 把 `KAGGLE_CONFIG_DIR` 指向项目自己的 `.kaggle/`，
所以这里不碰 `~/.kaggle`，你可以在一台机器上放多个账号：

```bash
mkdir -p .kaggle && chmod 700 .kaggle
printf '{"username":"YOU","key":"..."}' > .kaggle/kaggle.json   # kaggle.com/settings/api
chmod 600 .kaggle/*
source setup_env.sh
kaggle competitions submission-limits kaggriculture     # 验证可用
```

**然后提交。** 单文件 agent 直接作为 `main.py` 上传；多文件的必须打成 tar.gz，
且每个模块都在**归档根目录**，因为 Kaggle 解包到 `/kaggle_simulations/agent/`，
嵌套目录会让 import 失败。

```bash
python tools/stress.py agents/mine/main.py -j 14        # 必须 28/28
mkdir -p submissions/$(date +%F)-mine && cp agents/mine/main.py submissions/$(date +%F)-mine/
kaggle competitions submit -c kaggriculture \
    -f submissions/$(date +%F)-mine/main.py -m "一句话 + 本地证据"

# 多文件：打包、解包、检查 get_last_callable、跑一整局
bash tools/package.sh agents/mine mine
```

**三条已经各自让我们损失过槽位的规则** —— 完整清单在
[`docs/SUBMISSION_POLICY.md`](docs/SUBMISSION_POLICY.md)：

* **每天 5 次，只有最新两个活跃，而失活是按*时间顺序*不是按分数。** 第三次提交会
  挤掉较早的那个活跃者，即使它是你最好的。
* **一个 agent 需要 40 局以上分数才有意义** —— 大约四小时。在这个窗口内再次提交，
  等于把你正在等的测量扔掉。
* **永远快照**到 `submissions/<日期>-<名字>/`，并在
  [`docs/RUNS.md`](docs/RUNS.md) 里记下本地证据。一条天梯记录必须几个月后仍可追溯。

### 2. 我怎么先在本地把策略跑通？

```bash
source setup_env.sh                  # 任意目录，任意机器
bash tools/bootstrap.sh              # 只在 venv/ 缺失时需要
bash tools/fetch_fields.sh           # 对手 —— 新克隆一个都没有
```

然后，从便宜到贵：

| 你想知道 | 命令 |
|---|---|
| 会不会崩 | `python tools/stress.py <agent>.py -j 8` |
| 一局，逐日 | `python tools/trace.py <agent>.py starter` |
| A 是否优于 B | `python tools/eval.py h2h a.py b.py --seeds 96 -j 32` |
| 对整个场地 | `python tools/tournament.py panel --agents <agent>.py --panel agents/bench3/*.py --seeds 96 -j 8 --label mine` |

八核笔记本上，最后一行约 15 分钟。更大的跑数见 [`docs/CLUSTER.md`](docs/CLUSTER.md)，
或者直接拿别人跑好的数据库。

**不要手写策略文件。** 在 `tools/registry.py` 里加一个原子选项然后重新生成 ——
名字就是定义，而且所有生成的策略共用一条执行路径，比较才公平。

**然后在相信那个数字之前读 [`docs/VALIDATING.md`](docs/VALIDATING.md)。**
它很短，它的存在是因为这个项目在量表两端都产出过自信的胡话：一个什么都打得过的
参考场地，和一个什么都以同样幅度打得过的参考场地。四个种子分辨不出任何东西 ——
三个改动在四种子下读数为正，在每臂 2,304 局下落后 21 到 44 分。

### 3. 我该怎么分析一局对战？

**你自己的天梯对局。** Kaggle 保存回放；`ladder.py` 拉下来，留一份约 1.4 KB 的
摘要，删掉 19 MB 的原件：

```bash
python tools/ladder.py pull --limit 40      # 你最近的天梯对局
python tools/ladder.py stats                # 胜率、对手形状、卖了什么
```

**天梯顶端**，你永远不会被匹配到的那些：

```bash
python tools/topeps.py index                # 列出 Kaggle 每日的榜首对局数据集
python tools/topeps.py pull                 # 消化进数据库
python tools/ghost.py make --limit 60 --per-team 2 --bands
python tools/lines.py                       # 他们实际在跑哪几条不同的剧本
```

**幽灵**就是把那样一条轨迹变成本地对手 —— 11 KB，录制的动作序列逐回合重放，
没有任何拟合成分。[`docs/GHOSTS.md`](docs/GHOSTS.md) 有采样设计和它的局限。

**一局的细节。** `tools/trace.py` 逐日打印农场 —— 地块、棚子、价格、现金。
**这个引擎里非法动作是静默空操作**，所以 bug 看起来和"策略差"完全一样，而最终分数
永远不会告诉你是哪一种。这个仓库里每一个五位数级别的缺陷都是靠读 trace 找到的，
不是靠盯分数。

---

## 文档

这个项目知道的一切都在 `docs/` 里。没有任何东西只存在于某个人的脑子里或聊天记录里。

| 文档 | 内容 |
|---|---|
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md) | **从这里开始** —— 搭建、第一次锦标赛、会咬你的五件事 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | **这个项目走到哪、为什么** —— 离开过几天就先读这个 |
| [`docs/VALIDATING.md`](docs/VALIDATING.md) | **我的改动是真的吗？** 两个场地对应两个层级，以及两种自信地得出错误答案的方式 |
| [`docs/GAME_ECONOMICS.md`](docs/GAME_ECONOMICS.md) | 引擎实际奖励什么；官方页面写错的三处 |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | 完整版：要跑多少局，以及随机性到底在做什么 |
| [`docs/MAP.md`](docs/MAP.md) | **哪份文档回答哪个问题，每个行为在代码的哪一行** |
| [`docs/LADDER_FIELD.md`](docs/LADDER_FIELD.md) | 真实对手在做什么，以及本地排名为什么没预测到 |
| [`docs/ENGINE_CHANGES.md`](docs/ENGINE_CHANGES.md) | 对 agent 的每一次改动、它测出了什么、以及被否决的那些 |
| [`docs/GHOSTS.md`](docs/GHOSTS.md) | 怎么在本地对着天梯**顶端**测量 |
| [`docs/CLUSTER.md`](docs/CLUSTER.md) | Vulcan 集群专用 —— 没有账号可以完全跳过 |
| [`docs/SUBMISSION_POLICY.md`](docs/SUBMISSION_POLICY.md) | 什么时候提交、提交什么，以及额度机制 |
| [`docs/ATOM_EFFECTS.md`](docs/ATOM_EFFECTS.md) | 每个原子选项值多少 —— 部分已被取代，见开头提示 |
| [`docs/STRATEGY_LIBRARY.md`](docs/STRATEGY_LIBRARY.md) | 原子分类法和边界情况 |
| [`docs/ADVERSARIAL.md`](docs/ADVERSARIAL.md) | 能靠压制对手取胜吗？（部分能，但不是你想的那样） |
| [`docs/ENHANCED_BASELINE.md`](docs/ENHANCED_BASELINE.md) | 那个基线 agent：每个选择都追溯到一次测量，外加一处更正 |
| [`docs/TOOLS.md`](docs/TOOLS.md) | 每个脚本：做什么、读写什么、已知局限 |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | 约定、同步契约、加原子、提交 |
| [`docs/RUNS.md`](docs/RUNS.md) | 溯源：每次实验和它支撑的那条主张 |
| [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md) | 由数据库生成 —— 不要手编辑 |

---

## 目前知道的事

简版；证据在 `docs/ROADMAP.md`，任何关于真实场地的事在 `docs/LADDER_FIELD.md`。

**差距不在开局，在全程。** 把一条录制的开局拼接到我们的引擎前面并扫描交接日，
胜率从 54.0%（纯我们）单调升到 98.6%（纯剧本），**曲线不见顶**。不存在一个"我们的
引擎开始产生价值"的转折点，所以"前半剧本 + 后半自适应"这条路没有可拼的东西。

**榜首跑的不是我们一直对标的那条线。** 156 条真实榜首轨迹里，只有 8 条与
`agents/ref/closer_cleo.py` 内嵌的剧本重合超过 30%。它们彼此中位重合 75.4%，聚成
25 条线，最大一条 97 份、跨 38 个队伍。之前没发现，是因为**同一套剧本错开一个回合，
逐格比对就是 0% 重合** —— 要先做 ±8 回合对齐。

**价值在外包装，不在剧本。** 原始录音换个种子就塌（原始分最高的那簇只剩 11.8%，
另一簇 0.9%），因为开环动作遇到不同的杂草会大量变成静默空操作。而在 3,072 局的循环赛里，
原始录音对四个带外包装的 agent 是 **0.0%**。那层外包装**只重写市场动作** ——
农场动作原封不动来自剧本。

**引擎里正确的行为常常没有注释。** 一个探针显示农场十天买不了种子、现金只有
$109–$435，看起来像死锁。"修好"它在 137,664 局下损失 8–14 分：现金流向了牲畜，
而牲畜更值钱。**判定引擎坏掉之前，先查它把资源花到哪去了。**

**最值钱的单次测量来自动作直方图。** 榜首每个有效动作只花 1.09 步移动，我们是 1.85，
因为他们 50% 的工作不需要移动 —— 一头牲畜在同一格上支撑 FEED、CARE、
COLLECT_FERTILIZER、HARVEST 四个动作。从同一份回放读出的三个**形状**想法则全部测负。

**雇工这条轴支配其他所有轴，而且失败模式是反的。** `crew`（11 个雇工、≤6% 现金）
赢 55%；`swarm`（30 个雇工、无工资上限）赢 **10%** —— 比完全不雇人还差。
第 n 个雇工的成本是 `fib(n)`。

**引擎在 2026-08-06/07 被重新平衡过**（`kaggle-environments` 1.32.6）：城镇需求减半，
商店改为**有放回**抽样。所有日期在 08-06 或更早的公开 meta 分析，描述的是一个已经
不存在的游戏。

**策略空间是非传递的。** flood > metered > spite > flood，全部实测。任何排名都是
相对于它的场地的排名。

**两个参考场地都已经在顶端饱和。** 八个 `closer_cleo` 量级的变体在幽灵场地上并列
99.4%，分不出高下。在这个层级唯一还有分辨率的，是**带外包装的 agent 互相打** ——
92.7 / 73.8 / 54.1 / 29.3，间距干净。
