# 上手指南 —— 你的第一个小时

写给零基础加入这个仓库的人。从上到下照做，大约一小时，读完你会跑过一次真实的锦标赛，
并读懂一个真实的结果。

---

## 0. 这个项目是什么，五句话

Kaggriculture 是一个 Kaggle **仿真类**比赛：你提交的是一个**程序**，不是预测结果，
它会和别人的程序一对一打 720 回合的农场季。奖金是十个等额的 $5,000 名额，所以目标是
**前 10**，不是第一。排名只看胜负 —— 金额差距完全不计入 —— 最终排行榜是对最后两周
所有对局做一次 Bradley-Terry 拟合。

这个仓库包含一个**可组合的策略库**（七个正交原子生成的 agent）、一个已经把
130 万局写进 SQLite 的**本地锦标赛系统**，以及由此得出的全部分析。

---

## 1. 环境搭建（10 分钟）

**这个项目在 Vulcan 集群和普通笔记本上都能跑。** 除了 Slurm 以外一切行为一致；
`bootstrap.sh` 和 `setup_env.sh` 会自动检测所处环境。

你需要 Python 3.9+（3.11 与集群和 Kaggle 自身运行时一致），以及你**自己的**
Kaggle API 凭据。

```bash
git clone <repo> Kaggriculture      # 在集群上请放到 $SCRATCH 下面
cd Kaggriculture

bash tools/bootstrap.sh             # 建立 venv/，并用一局真实对局验证
```

在集群上它会 `module python/3.11.5`，并从 Compute Canada 的 wheelhouse 取
`numpy`/`pandas`。在笔记本上它使用 `PATH` 里的 `python3`（可用
`PYTHON=/path/to/python3.11` 覆盖），全部从 PyPI 安装。两边环境一致。

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
而不是重跑 —— 它代表数小时的 32 核算力：

```bash
# 有它的人导出一份快照
python tools/sync.py export --full        # -> dist/arena-full.sqlite.xz

# 你来安装
python tools/sync.py import dist/arena-full.sqlite.xz

# 或者只要排名，几十 KB，如果你只想读结果
python tools/sync.py export               # -> dist/arena-meta.sqlite.xz
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

**为什么需要 bootstrap 而不是直接 `pip install -r`：** `kaggle-environments` 声明依赖
`open_spiel`，那个包要从源码编译，在这个集群上会失败。所以它是**故意**用 `--no-deps`
安装的，`numpy`/`pandas` 从 Compute Canada wheelhouse 取。**其他**环境
（`lux_ai_s3`、`halite`、`open_spiel_env`）的导入错误会打到 stderr，这是预期内的。

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

**在集群上** —— 永远不要在登录节点跑。一局（约 2.7 秒）没问题，一场锦标赛不行。

```bash
sbatch slurm/tournament.sh roundrobin \
    --agents agents/barnyard.py agents/lib/homestead-crew-orchardherd-flood-blind-muck.py starter \
    --seeds 24 --label "my-first-run"

squeue -u $USER                    # 等它
tail -f logs/tourney-<jobid>.out
```

**在笔记本上** —— 同一个 runner，直接调用，按你的核数调整：

```bash
python tools/tournament.py roundrobin \
    --agents agents/barnyard.py agents/lib/homestead-crew-orchardherd-flood-blind-muck.py starter \
    --seeds 8 --label "my-first-run" -j $(python -c 'import os;print(os.cpu_count())')
```

**现实地估算预算**：一局约 2.7 秒单核。八个核约 3 局/秒，所以上面这个三 agent 的跑数
（48 局）不到一分钟；但整个策略库的筛选（数万局）要几个小时。全库筛选是集群任务，
其余在本地都很舒服。

大规模跑数请分片，永远不要让 array 任务碰数据库：

```bash
sbatch --array=0-15 --cpus-per-task=32 --mem=40G --time=00:30:00 \
    slurm/tournament_array.sh panel --agents agents/mine/*.py \
    --panel agents/bench3/*.py --seeds 96 --jobs 32 --label mine
python tools/tournament.py ingest --shards data/shards/mine
```

然后：

```bash
python tools/db.py stats                    # 有史以来跑过什么
python tools/db.py top --run latest         # 排名
python tools/leaderboard.py --run latest    # 重新生成 docs/LEADERBOARD.md + site/
```

吞吐参考：带 `KG_FAST_ENV=1` 时每核每秒 0.375 局，32 核约 12 局/秒。一次有统计效力的
A/B（每臂 384 局）大约花一个计算节点几十秒。

---

## 5. 按这个顺序读知识（25 分钟）

如果你离开超过几天，**先读 `docs/ROADMAP.md`** —— 它就是为这种情况写的，开头就讲
哪些结论后来被推翻了。

1. `docs/ROADMAP.md` —— 这个项目走到哪、为什么，每条主张都附样本量
2. `docs/VALIDATING.md` —— 怎么判断你的改动是真的。两个场地对应两个水平层级，用错
   这一轮就白跑
3. `docs/GAME_ECONOMICS.md` —— 这个游戏实际奖励什么
4. `docs/ENGINE_CHANGES.md` —— 七个落地、五个被否，全都附样本量
5. `docs/LADDER_FIELD.md` —— 为什么我们自己写的场地误导了我们一周
6. `docs/SUBMISSION_POLICY.md` —— 碰排行榜之前必读
7. `docs/EVALUATION.md` —— 上面第 2 条的完整版

`docs/MAP.md` 会把其他任何问题路由到回答它的那份文档。

## 6. 会咬你的五件事

这些都不是假设；每一条都已经在这里造成过实际损失。

**非法动作静默失败。** 没有异常、没有日志、没有代价。错的地块、空的库存、满的棚子 ——
全都只是空操作。永远要 trace。

**`FEED` 从执行单位的库存里取小麦，不是从棚子里取。** 而 `PICKUP` 只在棚子旁边那四格
才有效。不显式安排雇工回去取饲料，所有单位就会一直忙着浇水，整个畜群饿死。
这一个 bug 值约 4.5 万。

**种子间的方差大于大多数调参效果。** 这个仓库早期 3–4 个种子的扫描，**重复跑会得出
互相矛盾的排序**。一个可信结果的下限是几百局；表格见 `EVALUATION.md` §5。

**共同随机数在这个环境里不成立。** `_end_of_day` 用同一个 RNG 抽杂草和商店解锁，而
杂草抽取次数正比于**双方**农场的空地数 —— 所以改你的 agent 会改变哪些商店解锁。
按种子配对有帮助，但抵消不了任何东西。

**策略空间是非传递的。** 存在实测到的石头剪刀布环：flood 胜 metered 胜 spite 胜 flood。
任何排名都是**相对于它的场地**的排名，换个场地就重排。这个仓库里有两次诚实的锦标赛
结论相反，原因正是这个。

---

## 7. 目前的状况（截至 2026-08-12）

- **排行榜最高分 1363.7**，来自 `closer_cleo` 加一行改动（终局控制器从最后 3 回合
  放宽到 6 回合）。我们自己引擎的历史最好是 **857.6**。为什么会跳，见
  `docs/ROADMAP.md` §5。
- **我们自己的引擎赢参考场地 54–61%，而 `closer_cleo` 赢 99%。** 这不是调参能补的差距。
- 最重要的一条事实修正：**榜首跑的不是 `agents/ref/` 里那条线** —— 156 条真实榜首
  轨迹里只有 8 条与之重合超过 30%。它们自己聚成 25 条线，最大一条 97 份、跨 38 个队伍。
  见 `docs/ROADMAP.md` §3 和 `tools/lines.py`。
- **价值在外包装，不在剧本本身。** 原始轨迹换个种子就塌（最好的那簇只剩 11.8%），
  而对四个带外包装的 agent 是 0/3072。
- 唯一还有天花板的路线是 **C：自己搜一整季的剧本 + 市场外包装**。见 `ROADMAP.md` §7。
- 5 次提交/天，只有最新两个活跃，**失活按时间顺序不按分数** —— 这条已经让我们
  在一夜之间损失了 1363.7 和 1287.2。

---

## 8. 集群礼仪

Vulcan 的登录节点是共享的。一局没问题，比这更大的都走 Slurm。这个工作负载是纯 CPU 的
—— **永远不要申请 GPU**。

```bash
sbatch slurm/tournament.sh ...     # 32 核，正式跑数的默认值
salloc --account=aip-zhouyang --time=02:00:00 --cpus-per-task=16 --mem=32G
```

**短任务立刻开跑，长任务排队。** 同样的工作量在 `--time=03:00:00` 加每任务 64 核下
排了 78 分钟；在 `--time=00:30:00` 加 32 核下，十六个节点上立即开始。

`$SCRATCH` 有 5 TB，**不备份**，60 天不活动会被清理（年龄取 `min(atime, ctime)`）。
`data/arena.sqlite` 是这里唯一不可替代的文件 —— 如果你在意，拷一份到 `~/projects/`。
