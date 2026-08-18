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
  **3,397,241 局**（87 个 run），另有真实天梯回放摘要。

### → 新来的？读 [`docs/ONBOARDING.md`](docs/ONBOARDING.md)，一小时，读完你会跑过一次真实锦标赛。

### → 离开了几天？读 [`docs/ROADMAP.md`](docs/ROADMAP.md)，它开头就讲哪些结论被推翻了。

### → 想跑几万倍速的批量对局、或在 GPU 上训练？读 [`rl/tensor_env/README.md`](rl/tensor_env/README.md)（`tensorize` 分支）—— 与竞赛引擎逐字节一致的张量引擎，单卡 22.8 万步/秒，PPO 18 分钟学会打赢基线；RL 线的复盘在 `rl-baseline` 分支的 `rl/README.md`。

### → 只想知道榜上跑的是什么？读 [`docs/LADDER_STATE.md`](docs/LADDER_STATE.md) —— 场上两个提交对应本地哪两个、怎么一模一样地重建、以及为什么现在不要提交。

---

## 环境搭建

**一台普通笔记本就够了** —— 唯一的硬性要求是 Python 3.9+。

```bash
bash tools/bootstrap.sh          # 建立 venv/，用一局真实对局验证
source setup_env.sh              # 每次会话，任意目录下都能用
```

### 你需要自己的 Kaggle API 密钥

**仓库里没有、也不会有任何人的密钥。** 每个人用自己的，从
<https://www.kaggle.com/settings/api> 点 "Create New Token" 拿到：

```bash
mkdir -p .kaggle && chmod 700 .kaggle
printf '{"username":"你的用户名","key":"你的key"}' > .kaggle/kaggle.json
chmod 600 .kaggle/*
source setup_env.sh
kaggle competitions list -s kaggriculture     # 验证可用
```

`setup_env.sh` 把 `KAGGLE_CONFIG_DIR` 指向**项目自己的 `.kaggle/`**，所以这里不碰
`~/.kaggle`，一台机器上可以放多个账号，而且 `.kaggle/` 是 git-ignored 的。

**三件事需要它**，缺了任何一件都会卡住：

| 你要做 | 用到的命令 | 没有密钥的后果 |
|---|---|---|
| 拿到对手场地 | `bash tools/fetch_fields.sh` | 一个对手都没有 —— 新克隆的 `agents/` 是空的 |
| 拉对局数据分析 | `tools/ladder.py pull`、`tools/topeps.py pull`、`tools/ghost.py make` | 拉不到任何回放 |
| 提交到排行榜 | `kaggle competitions submit` | 交不上去 |

**只跑本地锦标赛不需要密钥** —— 前提是有人已经把 `agents/` 下的场地给了你。

`setup_env.sh` 还把**所有**缓存路径重定向到这个目录，所以这里的任何操作都不会碰
你的主目录。

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
> 有 Vulcan 集群账号的人另见 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)「在 Vulcan 集群上跑」；**其余文档都不
> 假设你有集群**。

## 日常命令

```bash
python tools/trace.py agents/barnyard.py starter        # 逐日追踪一局
python tools/stress.py agents/barnyard.py -j 8          # 28 个病态配置
python tools/registry.py list                           # 原子空间
python tools/registry.py gen --plan all --out agents/lib
python tools/db.py stats                                # 有史以来跑过什么
python tools/sync.py export --full                      # 可分享的压缩快照

# 锦标赛：-j 给多少核就用多少（集群上走 Slurm，见 docs/CONTRIBUTING.md（集群））
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

### 但这套库不是分数最高的那个结构

**必须先知道这件事，否则你会往一条已经量到头的路上投入时间。**

这个原子库是一个**在线调度器**：每回合扫描棋盘、生成任务清单、把任务派给最近的空闲
单位。十一个落地的引擎改动把它从 623 推到 **857**，然后停住了。

天梯顶端跑的是另一套结构 —— **剧本 + 软包装**：

```
   剧本 (trace)        一条离线算好的 720 回合动作序列，按回合号查表，不看棋盘
        │
        ▼
   软包装 (wrapper)     一层薄的自适应逻辑，只重写市场动作：
                        供给表、对克隆对手抢先卖出、终局收割清仓
```

三个场地一致的实测：

| | 对 `bench3`+参考 | 对 156 条真实榜首轨迹 | 五方对打 |
|---|---|---|---|
| 剧本 + 软包装 | **99.2%** | **99.4%** | **92.7%** |
| 只有剧本（原始录音） | 66.6% | 70.5% | **0.0%** |
| 我们的在线调度器 | 60.9% | 57.7% | — |

两个反直觉的地方，都是量出来的：

- **原始录音换个种子就塌**（最好的那簇只剩 11.8%，另一簇 0.9%）—— 开环动作遇到不同的
  杂草会大量变成静默空操作。跑的人最多的那条线是**最耐操**的，不是最强的。
- **值钱的是软包装，不是剧本。** 原始录音对每一个带软包装的 agent 都是 **0/3072**。
  而那层包装**只重写 `action["market"]`** —— 农场动作原封不动来自剧本。

### 这两层是怎么接的

**接口只有一个：`action` 这个 dict。** 剧本产出它，包装原地改写它，然后返回给框架。

```
每回合 agent(obs) 被调用一次
        │
        ├─ step >= 714 ?  ──是──▶  _terminal_action(obs)          ← 完全接管，读盘面
        │                          收割 / 搬运 / 抛售调度器
        │                          （最后 6 回合，其余层全部跳过）
        否
        ▼
   action = deepcopy(_TRACE[step])        ← 剧本：按回合号查表，不看棋盘
        │                                    产出 {farmer, hands, market}
        ▼
   ┌────────────────────────────────────────────────────────┐
   │  软包装：三层，全部只改 action["market"]                 │
   │  farmer 和 hands 原封不动 —— 农场动作 100% 来自剧本      │
   ├────────────────────────────────────────────────────────┤
   │ ① _front_run       检测到克隆 → 抢在它抛售前一回合卖出   │
   │                    条件 _CLONE_CONFIDENCE >= 2          │
   │ ② _terminal_liquidation  step >= 680 → 把棚内存货挂单    │
   │ ③ 市场控制器 _plan_sells  按储备价决定卖多少             │
   │                    储备价 = 基价 × 系数 × 供需比          │
   │                    只接管 _RESERVE 里列出的品类           │
   └────────────────────────────────────────────────────────┘
        │
        ▼
   return action
```

**两层之间唯一共享的状态**是 `_TRACE` 本身 —— 包装会**读未来几回合的剧本**，
知道自己接下来要卖什么，这就是"抢跑"的信息来源。除此之外包装不改变剧本的任何意图。

**两层各自的失效模式完全不同**，这是分层的代价：

| 层 | 怎么失效 | 现状 |
|---|---|---|
| 剧本 | 换个种子杂草不同 → 动作变成静默空操作 | 无法修，只能重搜 |
| ① 抢跑 | 要求棚里有货，而策略是进棚就卖 → **永远读到空棚子** | 实测 0/714 回合触发 |
| ③ 市场控制器 | `_RESERVE` 为空 → **一个品类都不接管** | 整套机制在空转 |

前两条是实测的：镜像对局里克隆检测完美（信心值 step 192 就满 8）、闸门开了 666 次、
**实际下单 0 次**，每次都读到空棚子。

完整证据和它推翻的三个旧结论在 [`docs/ROADMAP.md`](docs/ROADMAP.md)；
唯一还有前 10 天花板的路线是 §7 C：**自己搜一条剧本 + 自己写市场包装**，两样都要。

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
slurm/             Vulcan 专用封装（可选，见 docs/CONTRIBUTING.md（集群））
site/              生成的排行榜页面
```

**生成物，永不手编辑：** `agents/lib/`、`agents/spar/`、`docs/LEADERBOARD.md`、
`site/leaderboard.html`、`notebooks/baseline.ipynb`。**git-ignored：** 以上加
`venv/`、`.cache/`、`.kaggle/`、`data/`、以及 `agents/` 下所有生成的对手场地。

**新克隆一个对手都没有** —— 先跑 `bash tools/fetch_fields.sh`。

## 对手一览

`bash tools/fetch_fields.sh` 建起全部场地。**除 `benchmarks/` 外都是 git-ignored 的生成物** ——
它们由脚本重建，不进版本库。

> **怎么判断一条线或一个 agent 好不好：只看「面板胜率」。**
> 固定十个对手（`w39 w48 w16 w68 w56 w25 w12 w28 w05 w02`）× 96 个种子 × 双方座位
> = **1,920 局**，赢的比例就是它。固定，是为了让不同候选用同一把尺子量。
> 比赛只看输赢不看钱，所以胜率就是比赛真正评的那个量；任何以「钱」为单位的指标
> 都只是代理，而代理指标背叛过我们一次。
> 定义、跑法、以及它自己还没解决的两个问题，写在
> [`docs/VALIDATING.md`](docs/VALIDATING.md) 开头。

| 路径 | 数量 | 是什么 | 怎么来 |
|---|---|---|---|
| **`agents/wrapped/`** | **100** | **真正的对手** —— 从天梯挖出的剧本，全部套同一层适配层 | `tools/wrap.py --top 100` |
| `benchmarks/strongest.py` | 1 | 要打过的那条（= `d08`，源队伍天梯 **#1**），**已提交进 git**，`agents/CHAMPION` 指向它 | `wrap.py` |
| `agents/darkhorse/` | 40 | 未进 `wrapped` 的 247 条里另选的 40 条，**18 条越过旧场地第十名** | `tools/wrap.py` |
| `agents/champ/` | 17 | **天梯 #1 那支队伍的全部录音**，同一层适配层 | `wrap.py --team` |
| `agents/lines/` | 35 | 每条不同剧本的一个代表，**裸录音**（无适配层，会塌） | `tracelib emit` |
| `agents/bench3/` | 28 | 引擎级场地：我们自己的形状 + 参考 agent | `registry.py gen --plan bench` |
| `agents/ref/` | 10 | 第三方教学梯队 tier 0–9（MIT，见其 NOTICE） | Kaggle 数据集 |
| `agents/ghosts/` | 156 | 早期拉的开环轨迹（**08-04～08-07，跨在再平衡线上**） | `ghost.py make` |
| `agents/spar/` | 30 | 从天梯回放重建的对手形状 | `registry.py gen --plan ladder` |
| `agents/lib/` | 2,366 | 全量策略库（七个原子的笛卡尔积） | `registry.py gen --plan all` |

### `agents/wrapped/` 里的名次（477,225 局实测）—— 以及它为什么不能当强弱看

| 对手 | 本地名次 | 本地胜率 | 跑它的队伍 | **源队伍天梯名次** |
|---|---|---|---|---|
| `w39` | **1** | 95.4% | 1 | #358 |
| `w48` | 2 | 95.1% | 1 | #711 |
| `w16` | 3 | 93.9% | 2 | #596 |
| `w05` | 9 | 86.3% | 11 | **#13** |
| `w02` | 10 | 84.5% | 39 | **#34** |
| `w03` | 11 | 84.0% | 38 | **#3** |
| `w01` | 45 | 47.4% | **96** ← 最流行 | **#6** |
| `cleo` = 我们提交过的那个 | 64 | 36.5% | — | — |

**最右一列和左边两列没有关系** —— 全部 100 条上 `spearman -0.05`（n=100）。
同一支队伍的不同对局，本地胜率能从 14% 跨到 93%（THUNDER THUNDER，#364，16 条线）。
**本地胜率测的是「这段录音换个棋盘还能不能用」，不是策略强弱。**
完整证据在 [`docs/ROADMAP.md`](docs/ROADMAP.md) §10.5。所以上表里 `cleo` 的 64 名
**不能**读成「我们中下游」—— 它两个方向都不说明问题。

`benchmarks/strongest.py` 现在指向 `d08`：本地对上表前十拿 92.4%（1,920 局，
上表最强的 `w48` 同一面板只有 79.9%），**且源队伍是天梯 #1**。两个信号一致的唯一一条。

### 提交过的 agent 与天梯分数

| 日期 | 提交号 | agent | 天梯分 | 快照 |
|---|---|---|---|---|
| 08-13 | `55489160` | `kawashigi-k06` —— 同一支队的另一局录音，**按面板胜率选出** | 等待中²  | `submissions/2026-08-13-kawashigi-k06/` |
| 08-13 | `55484175` | `topline` —— 榜首 カワシギ 的剧本 + MIT 市场层 | **2402.8**（#556 附近¹） | `submissions/2026-08-13-topline/` |
| 08-12 | `55458466` | `closer_cleo` + terminal@714（重发） | 1218.6 | `submissions/2026-08-11-closercleo-term714/` |
| 08-11 | `55442784` | 同上，首次 | **1363.7** | 同上 |
| 08-11 | `55439740` | `closer_cleo` 原样 | 1287.2 | `submissions/2026-08-11-closercleo/` |
| 08-11 | `55404837` | `mgtight` + liq29 | 836.8 | `submissions/2026-08-10-mgtight-liq29/` |
| 08-11 | `55431972` | `mgtight` + here-pass | 818.4 | `submissions/2026-08-11-mgtight-here/` |
| 08-11 | `55418588` | `mgtightgrain` | 767.4 | `submissions/2026-08-11-mgtightgrain/` |
| 08-10 | `55400803` | `bigberry` + compost | 763.3 | — |
| 08-10 | `55402695` | `mgtight` | 759.9 | — |
| 08-08 | `55358912` | `enhanced`（多文件） | 623.6 | `submissions/2026-08-08-enhanced/` |
| 08-07 | `55332339` | `barnyard`（最初版本） | 621.4 | `submissions/2026-08-07-barnyard/` |

**天梯最高 1363.7，而榜首 3,240.2、第 10 名约 3,080（08-13 实测，4,259 支队伍）。**

¹ **输掉三分之一之前，天梯分不算数。** 新提交从低分起步、靠打赢弱对手往上爬，
爬完之前那个数是地板而且一直在动。`55484175` 第 11 局读 1695.2（11 战全胜），
四十分钟后第 22 局读 2144.1，54 局收在 **2359.5** —— 同一个文件，三小时涨 664 点。
判据是**滑动窗口的败率，不是局数**（累计口径会永远滞后）：最近 18 局输 <1/3 还在爬，
≈1/2 才收敛。见 [`SUBMISSION_POLICY.md`](docs/SUBMISSION_POLICY.md) 规则 7。

**这次提交测出的东西**：カワシギ 本人 3,236.5，我们重放它 2,359.5 ——
**开环重放税 = 630.8 点**，一段录音能保住原 agent **80.5%** 的评分
（2026-08-14 用 `k06` 重测；用 `k01` 测是 877 点 / 73%，换一段更好的录音就找回约 246 点）。
第 10 名要 3,089.0，所以**照抄录音这条路到不了奖金区**，现在这是量出来的，不是猜的。

² **这一次是对「面板胜率」这把尺子本身的前瞻性检验。** 和 `55484175` 相比，
源队伍、市场层、打包方式**全部相同，只换了录自哪一局**：面板胜率 98.5% vs 92.4%，
直接对决 60.8%（768 局，区间不含 50%）。天梯若跟着涨，说明面板胜率在同队条件下
有预测力；若不动，说明它只是个过滤器、不能当优化目标。
判据在结果出来**之前**写好了，见 [`docs/RUNS.md`](docs/RUNS.md)。

**另外，`55442784` 和 `55458466` 是同一个文件**：一字未改，相隔一天，分别拿到
**1363.7 和 1218.6**。合并 130 局后胜率正好 50.0%（已收敛）。
**同一个 agent 的天梯分能差 145 点** —— 这张表里任何小于该幅度的差距
（包括归给 liq29 的 +69）都在噪声带内。完整清单见 [`docs/RUNS.md`](docs/RUNS.md)。

> **这三张表会过时。** 重新生成用：
>
> ```bash
> python tools/fieldtable.py          # 打印当前的三张表，可直接粘回这里
> ```
>
> 提交一个新 agent 后，把它加进最后一张表并在 `docs/RUNS.md` 记一行 ——
> 一条天梯记录必须几个月后仍能追溯到产生它的代码。

---

## 常见问题

三个每个人第一周都会问的问题。更长的答案在链接后面；这里的内容够你动起来。

### 1. 我该怎么提交到 Kaggle？

**先配好你自己的密钥**（见上面「你需要自己的 Kaggle API 密钥」），然后确认额度：

```bash
kaggle competitions submission-limits kaggriculture
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
bash tools/fetch_fields.sh           # 对手 —— 新克隆一个都没有，这一步要 Kaggle 密钥
```

**每次开工前都跑一遍 `fetch_fields.sh`。** 它会建起三个场地，其中
`agents/wrapped/` 是**真正该打的那个** —— 100 条从天梯挖出的真实剧本，全部套同一层
适配层，所以胜负只反映剧本本身。

**我们放上天梯的那个 agent 在这里排 64/101、胜率 36.5%**（477,225 局），而 `bench3`
给它的读数是 90%+。**在 `bench3` 上赢 95%，完全可能在真实前沿排倒数。**

它还会把 `agents/CHAMPION` 指向的那条拷成 `champion.py`。**你的对手里必须有它。**

不需要 Kaggle key —— 371 条剧本的快照（`dist/tracelib.json.xz`，3 MB）已提交进 git。

然后，从便宜到贵：

| 你想知道 | 命令 |
|---|---|
| 会不会崩 | `python tools/stress.py <agent>.py -j 8` |
| 一局，逐日 | `python tools/trace.py <agent>.py starter` |
| A 是否优于 B | `python tools/eval.py h2h a.py b.py --seeds 96 -j 32` |
| 对整个场地 | `python tools/tournament.py panel --agents <agent>.py --panel agents/bench3/*.py --seeds 96 -j 8 --label mine` |

八核笔记本上，最后一行约 15 分钟。更大的跑数见 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)「在 Vulcan 集群上跑」，
或者直接拿别人跑好的数据库。

**不要手写策略文件。** 在 `tools/registry.py` 里加一个原子选项然后重新生成 ——
名字就是定义，而且所有生成的策略共用一条执行路径，比较才公平。

**然后在相信那个数字之前读 [`docs/VALIDATING.md`](docs/VALIDATING.md)。**
它很短，它的存在是因为这个项目在量表两端都产出过自信的胡话：一个什么都打得过的
参考场地，和一个什么都以同样幅度打得过的参考场地。四个种子分辨不出任何东西 ——
三个改动在四种子下读数为正，在每臂 2,304 局下落后 21 到 44 分。

### 3. 我该怎么分析一局对战？

下面每一条都要**你自己的 Kaggle 密钥**（见上面那一节）—— 它们都在向 Kaggle 拉数据。

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
没有任何拟合成分。[`docs/ROADMAP.md`](docs/ROADMAP.md) §11 有采样设计和它的局限。

**一局的细节。** `tools/trace.py` 逐日打印农场 —— 地块、棚子、价格、现金。
**这个引擎里非法动作是静默空操作**，所以 bug 看起来和"策略差"完全一样，而最终分数
永远不会告诉你是哪一种。这个仓库里每一个五位数级别的缺陷都是靠读 trace 找到的，
不是靠盯分数。

---

## 文档

这个项目知道的一切都在 [`docs/`](docs/) 里，**十份**，没有别的地方。
按你想知道什么来查：

| 你想知道… | 读 |
|---|---|
| **榜上跑的是什么，我怎么在本地复现** | [`docs/LADDER_STATE.md`](docs/LADDER_STATE.md) —— 交接先读这个 |
| **这个比赛里到底什么决定输赢** | [`docs/ANALYSIS.md`](docs/ANALYSIS.md) —— 引擎经济学 + 312,000 局受控实验 |
| 怎么把环境跑起来 | [`docs/ONBOARDING.md`](docs/ONBOARDING.md) —— 第一个小时 |
| 这个项目走到哪、哪些结论被推翻了、哪些路线停了 | [`docs/ROADMAP.md`](docs/ROADMAP.md) |
| **我的改动是真的吗** | [`docs/VALIDATING.md`](docs/VALIDATING.md) —— 出任何数字之前读 |
| 命名约定、工具用法、集群、怎么交东西 | [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) |
| 什么时候提交、提交什么、额度怎么算 | [`docs/SUBMISSION_POLICY.md`](docs/SUBMISSION_POLICY.md) |
| 接下来做什么 | [`docs/TODO.md`](docs/TODO.md) —— 按「不做会怎样」排序 |
| 某一个具体数字是哪次跑出来的 | [`docs/RUNS.md`](docs/RUNS.md) —— 台账，只增不改 |
| 当前本地排名 | [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md) —— **生成物**，别手改 |

`CLAUDE.md` 是给 AI 工具自动加载的短规则表（英文），不是给人读的入门文档。
`reference/docs/` 是比赛官方 README 和 AGENTS，原样保存，不是我们写的。

> **文档数量本身是个约束。** 2026-08-14 这里曾有 28 份、7,700 行，包括两个互相指来
> 指去的目录页、一份自称是另一份「完整版」的方法论、和四份自己在第一行就声明
> 已被取代的文档。合并到十份。**加新文档之前先问能不能并进现有的一份。**

---

## 目前知道的事

简版；证据在 `docs/ROADMAP.md`，任何关于真实场地的事在 `docs/ROADMAP.md §11`。

**最重要的一条在上面「核心思路」里**：天梯顶端是「剧本 + 软包装」，而我们这套原子库是
在线调度器，两者差 40 个百分点，而且不是调参能补的。

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
