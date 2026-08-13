# 文档

这个项目知道的一切都在这里。没有任何东西只存在于某个人的脑子里或聊天记录里。

**不知道该读哪份就看 [`MAP.md`](MAP.md)** —— 它按*问题*索引，而不是按文件名，
还标出每个行为对应 `agents/_engine.py` 的哪一行。

---

## 按阅读顺序

前四份是新人的第一小时，读完就能独立工作。

| 文档 | 内容 |
|---|---|
| [`ONBOARDING.md`](ONBOARDING.md) | **从这里开始** —— 搭建、第一次锦标赛、会咬你的五件事 |
| [`ROADMAP.md`](ROADMAP.md) | **这个项目走到哪、为什么** —— 离开过几天就先读这个，它开头就讲哪些结论被推翻了 |
| [`VALIDATING.md`](VALIDATING.md) | **我的改动是真的吗？** 两个场地对应两个层级，以及两种自信地得出错误答案的方式 |
| [`SUBMISSION_POLICY.md`](SUBMISSION_POLICY.md) | 什么时候提交、提交什么，以及额度机制 |

## 这个游戏与这个场地

| 文档 | 内容 |
|---|---|
| [`GAME_ECONOMICS.md`](GAME_ECONOMICS.md) | 引擎实际奖励什么；官方页面写错的三处 |
| [`LADDER_FIELD.md`](LADDER_FIELD.md) | 真实对手在做什么，以及本地排名为什么没预测到 |
| [`GHOSTS.md`](GHOSTS.md) | 怎么在本地对着天梯**顶端**测量 |
| [`EVALUATION.md`](EVALUATION.md) | `VALIDATING` 的完整版：要跑多少局，随机性到底在做什么 |

## 做过什么，测出了什么

| 文档 | 内容 |
|---|---|
| [`ENGINE_CHANGES.md`](ENGINE_CHANGES.md) | 对 agent 的每一次改动、它测出了什么、以及被否决和仅是确认的那些 |
| [`RUNS.md`](RUNS.md) | 溯源：每次实验和它支撑的那条主张 |
| [`ADVERSARIAL.md`](ADVERSARIAL.md) | 能靠压制对手取胜吗？（部分能，但不是你想的那样） |
| [`ATOM_EFFECTS.md`](ATOM_EFFECTS.md) | 每个原子选项值多少 —— **部分已被取代**，见开头提示 |
| [`ENHANCED_BASELINE.md`](ENHANCED_BASELINE.md) | **历史** —— 一个被取代两次的 agent，留作多文件打包的范例 |

## 怎么动这个仓库

| 文档 | 内容 |
|---|---|
| [`TOOLS.md`](TOOLS.md) | 每个脚本：做什么、读写什么、已知局限 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 约定、同步契约、加原子、生成物是一对文件、测试写在哪 |
| [`STRATEGY_LIBRARY.md`](STRATEGY_LIBRARY.md) | 原子分类法和边界情况 |
| [`CLUSTER.md`](CLUSTER.md) | Vulcan 集群专用 —— **没有账号可以完全跳过** |
| [`MAP.md`](MAP.md) | 哪份文档回答哪个问题，每个行为在代码的哪一行 |
| [`LEADERBOARD.md`](LEADERBOARD.md) | 由数据库生成 —— **不要手编辑** |

---

## 本地对手在哪

`bash tools/fetch_fields.sh` 建起三层场地：

| 场地 | 是什么 | 什么时候用 |
|---|---|---|
| `agents/bench3/` | 我们自己的引擎家族 + 参考 agent | 你的 agent 赢它 50–70% 时 |
| **`agents/wrapped/`** | **100 条从天梯挖出的剧本，同一层适配层** | **赢 bench3 95% 以上时 —— 这是真正的对手** |
| `benchmarks/strongest.py` | 那 100 条里最强的（95.4%），已进 git | 想知道离顶端还有多远 |

**我们提交上天梯的 agent 在 `agents/wrapped/` 里排 64/101、胜率 36.5%**（477,225 局），
而 `bench3` 给它 90%+。**在 bench3 上赢 95%，完全可能在真实前沿排倒数。**

不需要 Kaggle key —— 371 条剧本的快照 `dist/tracelib.json.xz`（3 MB）已提交进 git。
用法见 [`VALIDATING.md`](VALIDATING.md) §1。

---

## 语言

前八份是中文的（新人第一小时 + 判断数字是否可信所需的全部）。其余是英文的参考资料，
内容已逐条对照代码库审计过，但没有翻译。

`CLAUDE.md` 保持英文是有意的 —— 它由 AI 工具自动加载，英文指令的遵循度更稳定。

## 一条约定

**每一条主张都要附样本量。** 这个仓库里看似合理的推理大约五次里有四次输给十万局实测，
所以一个没有 n 的数字在这里不算证据 —— 它只是一个观点。
