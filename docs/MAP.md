# 什么写在哪里

给定一个问题该打开哪个文件、由哪份文档解释。文档里的每一条主张都能追溯到
`data/arena.sqlite` 里的一次跑数；每一个行为都能追溯到 `agents/_engine.py` 里的一行。

从 `README.md` 开始，然后 `docs/ONBOARDING.md`。这一页是之后所有东西的索引。

---

## 按问题查

| 你想知道… | 读 | 由什么产生 |
|---|---|---|
| 这个项目走到哪、为什么 | `docs/ROADMAP.md` | `tools/hybrid.py`、`tools/lines.py` |
| **我的改动是真的吗** | `docs/VALIDATING.md` | `tools/fetch_fields.sh` |
| 这个游戏实际奖励什么 | `docs/GAME_ECONOMICS.md` | `reference/engine/kaggriculture.py` |
| 真实对手在做什么，我们自己的场地为什么误导了我们 | `docs/LADDER_FIELD.md` | `tools/ladder.py` → `ladder_episodes` |
| 怎么在本地对着天梯**顶端**测量 | `docs/GHOSTS.md` | `tools/topeps.py`、`tools/ghost.py` |
| **天梯实际在跑哪几条不同的剧本** | `docs/ROADMAP.md` §3 | `tools/lines.py` |
| **开局决定了这一季的多少** | `docs/ROADMAP.md` §2 | `tools/hybrid.py` → `data/shards/handover*` |
| **分数为什么从 838 跳到 1364** | `docs/ROADMAP.md` §5 | 同上 |
| 对 agent 的每一次改动，以及它测出了什么 | `docs/ENGINE_CHANGES.md` | `data/shards/` 下的分片 JSONL |
| 怎么产出一个经得起追问的数字 | `docs/EVALUATION.md` | — |
| 每个原子选项值多少 | `docs/ATOM_EFFECTS.md` *(部分已被取代)* | 跑数 #1–#2 |
| 原子分类法和边界情况 | `docs/STRATEGY_LIBRARY.md` | `tools/registry.py` |
| 任意单个数字的溯源 | `docs/RUNS.md` | `runs` 表 |
| 每个脚本做什么 | `docs/TOOLS.md` | — |
| 约定，以及怎么提交 | `docs/CONTRIBUTING.md` | — |
| 什么时候提交、提交什么 | `docs/SUBMISSION_POLICY.md` | — |
| **在 Vulcan 集群上跑**（可选，没账号可跳过） | `docs/CLUSTER.md` | `slurm/*.sh` |
| 当前排名 | `docs/LEADERBOARD.md` *(生成物)* | `tools/leaderboard.py` |

---

## 按源文件查

### `agents/_engine.py` —— 唯一的执行路径

每个生成的策略都是这个文件配上不同的 `CONFIG` 块，所以改这里会一次移动整个库。
值得知道的行为，以及各自的依据：

| 区域 | 行为 | 依据在 |
|---|---|---|
| `CONFIG` 块 | 由生成器替换；永不手编辑 | `docs/STRATEGY_LIBRARY.md` |
| `_TO_FLOOR` | 把每个产品压到 $1 地板价所需的单位数，只算一次 | `docs/GAME_ECONOMICS.md` §market |
| `_town_drain` | 给定商店抽样，城镇每步移走多少 | `docs/LADDER_FIELD.md` §2 |
| `shopwise` 畜群再加权 | 畜群跟着商店抽样走，不跟计划走 | `docs/ENGINE_CHANGES.md` §5 |
| `feed_reserve` / `feed_solvent` | 买方、门禁、卖方共用一个数 | `docs/ENGINE_CHANGES.md` §1 |
| 雇工 `want_hands` | 按活儿雇人，不按计划雇人 | `docs/ENGINE_CHANGES.md` §5 |
| **雇工不受 `endgame` 限制** | 雇工是按天租的；清仓日照常雇 | `docs/ENGINE_CHANGES.md` §6 |
| the here-pass | 先干你脚下这一格的活 | `docs/ENGINE_CHANGES.md` §3 |
| `held_tiles` | 把一格剩下的活留给站在上面的那个单位 | `docs/ENGINE_CHANGES.md` §4 |
| ongoing 作物浇水 | 隔日浇，产出结算日例外 | `docs/ENGINE_CHANGES.md` §2 |
| `FERTILIZE` 调度 | 只施在已浇水、且在产出结算三天覆盖内的地块 | `docs/ENGINE_CHANGES.md` §2–3 |
| 肥料价格门禁 | 低于 $30 就不收 | `docs/ENGINE_CHANGES.md` §4 |
| `LIQUIDATE_DAY = 29` | 一季的最后一天 | `docs/ENGINE_CHANGES.md` |
| 派工循环 | 贪心，任务挑单位 —— **十一个替代方案全输** | `docs/ENGINE_CHANGES.md` §拒绝 |

### `tools/registry.py` —— 一个「策略」是什么

七条正交轴；名字就是定义。组合方案：

| 方案 | 生成什么 | 用于 |
|---|---|---|
| `all` | 去重后的全集 | 常备策略库 |
| `bench` | **标准参考场地** | 筛选时的 `--panel`，消融实验的固定对手 |
| `ladder` | 从真实回放重建的对手 | 保持场地诚实 |
| `factorial` | produce × land × muck × market，平衡设计 | 不被混杂的主效应 |
| `crop`、`refine`、`labour`、`recheck` | 围绕在位者的单轴扫描 | 引擎改动后重新测量 |

**候选打到 90% 以上就重建 `bench`。** 它已经饱和过两次；一个什么都输的参考排不了任何序。
**而且现在两端都可能饱和** —— 见 `docs/VALIDATING.md` §1。

### `tools/tournament.py` —— 一个数字是怎么产生的

`panel` 是 `O(n)` 筛选，`roundrobin` 是 `O(n²)` 确认，`ingest` 把分片 JSONL 折进一次跑数。
分片任务永不碰 SQLite。

**消融实验直接读分片 JSONL 并按目录分组**，因为 `short(path)` 取的是文件名，
两个来自不同目录的同名构建会静默合并成一行。

### `tools/topeps.py`、`tools/ghost.py`、`tools/lines.py` —— 天梯顶端，在本地

`topeps.py` 消化 Kaggle 每日发布的最高分对局 —— 评分约 3,100 的选手之间的对局，
我们永远不会被匹配进去。它的摘要带**动作直方图**，因为差别就在那里。

`ghost.py` 把那些轨迹变成对手。一个幽灵是 11 KB —— 一个选手录下来的动作序列，
在它打过的种子和座位上重放。没有任何拟合成分。

`lines.py` 把那些轨迹聚类成它们实际在跑的**线**。关键在于**先做 ±8 回合对齐**：
同一套剧本错开一个回合，逐格比对就毫无重合；没有对齐的话，156 条录音看起来像
156 种不同策略。

### `tools/hybrid.py` —— 开局值多少钱

把录制的开局拼接到我们的引擎前面，交接日可调，于是"开局决定了多少"变成可测量的。
产出的是**测量仪器，不是提交物** —— 见 `docs/ROADMAP.md` §9.3。

### `tools/ladder.py` —— 匹配到**我们这个评分**的对手

拉取我们自己的天梯对局，留约 1.4 KB 摘要，删掉 19 MB 回放。座位是靠对手日志返回 403
**确定**的，从不靠猜。

它找到了两件别的工具找不到的事：西瓜陷阱（`docs/LADDER_FIELD.md` §2），以及那个
产生了项目里最大单次改动的动作直方图（`docs/ENGINE_CHANGES.md` §3）。

---

## 新克隆没有的东西

**`agents/` 目录整个是 git-ignored 的**，所以新克隆下来一个对手都没有。
一个没有参考 agent 的场地，测的是我们自己家族内部互殴 —— 这个错误让项目损失了一周。

```bash
bash tools/fetch_fields.sh            # 全部
bash tools/fetch_fields.sh ghosts 60  # 只要幽灵，60 个
```

| 目录 | 是什么 | 为什么不提交 |
|---|---|---|
| `agents/ref/` | 公开的教学梯队，tier 0–9；tier 6–9 重放共享的 meta 线 | 第三方（MIT + 一份有实质范围豁免的 NOTICE）；一条命令就能取 |
| `agents/ghosts/` | 11 KB 的对手，重放榜首选手的轨迹 | 可从公开回放数据重建；每个约 90 秒 |
| `agents/lines/` | 天梯上每条不同剧本的一个代表 | 由 `tools/lines.py` 从幽灵聚类得出 |
| `agents/bench3/` | 标准参考场地 | 生成：`registry.py gen --plan bench`，再加上 tier 4–9 和 `line1` |
| `agents/lib/` | 全量策略库 | 生成：`registry.py gen --plan all` |

## 测量链条

```
reference/engine/kaggriculture.py     真值，每次升级后重新 diff
            │
            ▼
tools/registry.py  +  agents/_engine.py
            │  gen --plan <名字> --out agents/<目录>
            ▼
agents/<目录>/*.py                    每个策略一个文件，可直接提交
            │  tools/tournament.py  （大规模时分片跑）
            ▼
data/shards/<label>/shard-NNN.jsonl   只追加，每个分片任务一个文件
            │  tournament.py ingest              （单一写入者）
            ▼
data/arena.sqlite                     全部对局
            │
            ├── tools/leaderboard.py  → docs/LEADERBOARD.md, site/
            └── 临时查询               → docs/ENGINE_CHANGES.md, docs/RUNS.md
```

天梯循环在旁边同时跑，它才是纠正本地循环的那一环：

```
kaggle submit  →  约 10 局/小时  →  tools/ladder.py pull
                                              │
                                              ▼
                                     ladder_episodes（摘要）
                                              │
                     ┌────────────────────────┴─────────────────┐
                     ▼                                          ▼
        把对手重建进 registry.py                  从一份完整回放读
        的 `ladder` 方案                          动作直方图
                     │                                          │
                     └──────────────► docs/LADDER_FIELD.md ◄────┘
```

---

## 这个仓库掉进去过的四个坑

每一个都记录在它会咬人的地方，每一个都造成过实际损失：

1. **饱和的参考场地排不了序。** 当每个候选都以 97–100% 打败锚点时，99.2% 和 100.0%
   是同一个测量。**两端都会饱和**：`dairy` 被十个候选于 7,296 局中每一局打败，
   而八个高水平变体在幽灵场地上并列 99.4%。→ `docs/VALIDATING.md`
2. **四个种子会指错方向。** 四个独立改动在四种子下读数为正，在每臂 2,304 局下落后
   21–44 分。冒烟测试是语法检查。→ `docs/EVALUATION.md`
3. **agent 是按文件名索引的。** 两个来自不同目录的同名构建会合并成一行、一个
   Bradley-Terry 节点。→ `docs/TOOLS.md`
4. **框架会静默地跑另一份代码。** `get_last_callable` 取模块字典里最后一个 callable；
   包装一个 agent 会让框架加载**未包装**的那个，于是每个臂分数相同、而结论看起来很干净。
   → `docs/VALIDATING.md` §4

以及那个塑造了其余一切的：**一个针对我们自己写的场地做出的排名，不是关于天梯的证据。**
→ `docs/LADDER_FIELD.md`
