# 市场与胜负机制分析

> **范围说明：** 这是 2026-08-13 的机制研究，不是 2026-08-24 的 RL 路线图。
> 引擎与市场事实继续有效；“为什么反复训练没有进步”的当前归纳见
> [`RUNS.md`](RUNS.md) 顶部，执行路线见 [`../rl/TODO.md`](../rl/TODO.md)，文档状态见
> [`INDEX.md`](INDEX.md)。

这份文档记录 2026-08-13 做的一轮系统分析：**这个比赛里，到底是什么决定输赢。**

面向没跟进过程的协作者。每一节开头一句话说明**分析了什么**和**用什么路线分析的**，
然后才是数字。所有结论都有局数和区间，推翻掉的东西也留在里面 —— 被推翻的过程
往往比结论更有用。

原始记录在 `docs/RUNS.md`，工具在 `tools/perturb.py`、`tools/factorial.py`、
`tools/tracefeat.py`，实验设计在 `designs/mkt-wave*.json`。

---

## 0. 总量与可信度

**分析了什么**：这轮总共跑了多少、结论建立在什么样本上。
**路线**：五波受控实验 + 两份观测数据。

```
波次 1    31,744 局    29 个市场旋钮，先筛哪个有效
波次 2    74,240 局    有效的那个做笛卡尔积，并检验是否只对「自己」有效
波次 3    56,320 局    包装层的三个阈值：终局控制器、终局清仓、买地
波次 4    94,720 局    卖单排序层，4 因子 72 个单元
波次 5    56,320 局    修正需求模型后的商铺响应复检（本文 §11）
──────────────────────────────────────────
         312,320 局
观测数据   664 局真实天梯对局（带按天资金轨迹）
          371 条挖来的天梯录音（完整 720 回合动作日志）
```

**每一波都带两个控制组**：一个是被测 agent 的逐字节副本，一个是加了实验覆盖层但
所有旋钮清空的副本。**八个控制组全部落在 50%**（50.0 / 50.0 / 49.6 / 50.0），
配对边际 $0 ± 500。这是读任何实验臂之前的准入条件。

> **为什么必须有控制组**：这轮抓到 **4 个静默无操作** —— 代码跑了、有分数、
> 看起来完全正常，实际上什么都没做。三个是这轮新写的，一个是仓库里早就存在的。
> 没有控制组，其中至少两个会被当成真结果写进结论。

---

## 1. 实验方法：怎么做到「只改一个变量」

**分析了什么**：如何在一个 720 回合的复杂对局里做干净的因果实验。
**路线**：只改模块级常量，田间计划一个字节都不动，然后让它打一个逐字节相同的自己。

我们提交的 agent（`agents/champ/k01.py`）是两半拼起来的：

| 部分 | 是什么 | 来源 |
|---|---|---|
| `_TRACE` 那个大 base85 块 | カワシギ 第 92125421 局的 720 回合动作录音 | 从公开录像挖的 |
| 其余全部代码 | 市场层、调度器、终局控制器 | Rayk Kretzschmar 的 MIT 代码 |
| `tools/wrap.py` | 把两半粘起来 | 我们的 |

关键在于**市场层是参数化的** —— 十几个模块级常量决定什么时候卖、卖单排第几格、
持有多久。所以一条实验臂 = 一个和基线**逐字节相同、只差一个数字**的文件。
`_TRACE` 不变意味着种什么、收什么、雇几个人完全一样，**任何结果差异只能来自市场行为**。

工具是 `tools/perturb.py`。它做三重验证，因为这个环境里**非法动作是静默无操作**：

1. 常量的赋值行在源文件里必须**恰好出现一次**，否则报错退出
2. 写完之后按比赛框架的方式加载（`get_last_callable`），必须解析到 `agent`
3. 读**加载后模块里的活值**，不是看源码文本，必须等于要求的值

---

## 2. 「干扰市场」这条路：走不通，而且方向是反的

**分析了什么**：如果对手是固定剧本，能不能通过操纵市场价格打败他。
**路线**：19 条干扰臂（倾销、囤积、抢占槽位、低价扫货），每条打一个相同的自己，
看**对手的钱**有没有掉 —— 对手没掉钱就等于没干扰到。

**19 条干扰臂，对手的钱无一下降。全部让对手变富。**

```
倾销草莓     我方 -$8,706    对手 +$9,608
倾销西瓜     我方 -$8,132    对手 +$9,133
囤积后引爆   我方 -$82,229   对手 +$60,996
```

原因是反直觉的：**我们本来就是那个市场破坏者。** 基线一季卖 3,511 个单位，
把化肥和牛奶都砸到 $1 —— 这种持续倾销正是压住对手价格的东西。任何让我们少卖的
改动，都等于**撤掉了我们原本一直在施加的压力**。

囤羊毛那一局，牛奶价格从基线的 **$1 涨到 $183** —— 我们一停手，对手照单全收。

### 引擎层面：两个农场之间只有两条通路

读 `reference/engine/kaggriculture.py` 确认的：

1. **共享的市场库存** —— 唯一可以主动使用的
2. **日终 RNG** —— `random.Random((seed * 1_000_003) ^ day)` 一条流服务两个农场，
   而 `_spawn_weeds` 只在空地上抽（Python 短路求值），所以**抽取次数 = 空地数**。
   两个农场的空地数因此决定了当天解锁哪家商铺。这条通路真实存在，但要知道 seed
   才能定向，实际不可用。

### 摧毁一个市场的成本（从引擎算出来的）

| 商品 | 砸到 $1 需卖 | 砸的人自己收到 | 整季自然回血 |
|---|---:|---:|---:|
| WOOL | 59 | $7,928 | 30（无 YARN_STORE 时）|
| STRAWBERRY | 62 | $3,809 | 30 |
| MILK | 76 | $6,181 | 30 |
| MELON | 158 | $26,485 | 30（**没有任何商铺消耗西瓜**）|
| FERTILIZER | 493 | $25,045 | **0** |
| WHEAT / EGG | 打不穿 | — | 地板 $17 / $33 |

**砸市场是收钱的，不是花钱的** —— 沿途价格的积分归砸的人。所以门槛很低。
但上面的实验说明：即使便宜，也没用。

---

## 3. 「抢先卖」这个机制：只对「自己」有效

**分析了什么**：赶在对手抛售之前把高价品卖掉，能不能赢。
**路线**：先在镜像对局里测（自己打自己），发现大胜；再拿同一批 agent 去打
**四条真实天梯录音**，看还在不在。

引擎的市场结算是**逐格对齐**的 —— 我方第 0 格和对方第 0 格用同一个提交前库存报价，
第 1 格对第 1 格，依此类推。所以**槽位就是先后手**。原作者也知道，他写了一个
克隆检测抢跑：识别出对面是镜像后，赶在对方预期抛售之前卖掉一条高价线。

**镜像里效果惊人**：把抢跑窗口从 1 回合放宽到 3 回合，胜率 **78.7% [75.0, 82.0]**；
关掉它掉到 22.9%。

**但对真实录音完全无效**：56 个单元 × 4 条真实录音，每一个的成绩都是
**(901 胜 / 992 局)** —— 不是「差异不显著」，是**逐局产生了完全相同的对局**。

机制清楚：抢跑要求「对方农场公开特征与我方距离 ≤ 1」。自己打自己按构造距离为 0，
真实对手永远进不了这个门。

> ### 这一节最重要的一条规律
> **镜像里大的效应，对不是自己的对手几乎一律归零。** 这个模式在四波里出现了三次
> （克隆抢跑、提前清仓、卖单前置）。**自己打自己测出来的任何优势，必须再对
> 非镜像对手验一遍，否则默认为零。**

---

## 4. 包装层到底值多少钱

**分析了什么**：录音外面那层「适配代码」贡献了多少战力。
**路线**：把它的每个组件逐个关掉或改掉，在真实录音场上测。

| 组件 | 实场价值 |
|---|---|
| **卖单排序 `_SORT_KEY='impact'`** | **+4.1 点**（区间不相交） |
| `_terminal_action`（唯一读棋盘的部分） | **$4** on $83,465 |
| `_terminal_liquidation`（终局清仓） | **0** |
| `_RACE_WEIGHT` / `_SELLS_FIRST` / `_PROMOTE` | **0** |
| `_PROMOTE_IF_OPP_MONEY`（唯一读对手余额的规则） | +0.3 点，在区间内 |
| `_RESERVE` / `_RAMP_*` / `_SHED_PRESSURE` | **死代码，且 `_RESERVE` 是坏的** |

### 唯一有效的：卖单排序

```
_SORT_KEY   实场胜率        95%区间
impact       91.0%   [89.1, 92.6]   ← 原作者选的，四个里最好
gross        87.5%   [85.3, 89.4]
off          86.9%   [84.7, 88.8]   ← 关掉排序
unit         81.2%   [78.6, 83.4]
```

`impact` 的排序依据是「后手会损失多少收入」= 数量 × 自身价格冲击。**它是整个文件里
唯一显式假设「对手也在卖」的规则**，也是唯一一个在非镜像对手上活下来的效应。

**市场竞争是真实的，值大约 4 个点，而且原作者已经找到了正确的形式。**

### 一个反常识的结果：读棋盘的部分没用

`_terminal_action` 是这个 agent 里唯一读棋盘的组件（它扫描地块、给每只手分配
收割/搬运任务）。默认它接管最后 6 个回合。

```
seed 777:   开着 $83,465    关掉 $83,461
实场胜率:   开着 91.0%      关掉 91.3%
```

而且**跑得越久越差**：91.2%（12回合）→ 88.0%（1天）→ 69.3%（2天）→ 31.5%（4天）。
因为它只收割搬运，**不种、不浇、不喂**。

### 唯一的巨大效应：买地是必需的

抑制录音里的 `BUY_LAND` 单（k01 买 2 块共 $3,000）：
**镜像 0 胜 / 5,376 局，实场 0 胜 / 21,504 局。26,880 局零胜。**

> **注意**：`docs/RUNS.md` 里「两个象限比一个差、32/50 格闲置」说的是**我们自己的
> 引擎**，对录音完全不适用。真实天梯 643 局的对手画像是**中位数 3 个象限、
> 闲置 40 格**。闲置格子不是它看起来的那种成本。

---

## 5. 两个相同的 agent 打，谁赢？

**分析了什么**：如果场上所有人都跑同一条录音配同一层包装，胜负由什么决定。
**路线**：把杂草生成概率设成 0，看镜像对局会不会变成精确平局。

**会。每一个种子都变成分文不差的平局。** 恢复杂草，差距就回来。

```
逐字节相同的两个 agent，2,048 局:   精确平局 804 局 = 39.3%
                                   非平局的中位差 $717
真实天梯 664 局:                    精确平局 0 局
                                   中位差 $10,392
```

**所以在真正的镜像对局里，赢家由杂草掉在谁家决定，跟策略完全无关。**

这有两个推论：

1. **场上不是单一栽培。** 如果大家真的都在跑同一条线，我们会看到近四成精确平局。
   真实天梯一个都没有。**策略差异是真实存在的，而且大到中位数差一万块。**
2. **镜像对局的基准边际字面意义上是零**，所以几百块的稳定优势就能翻掉大量对局。
   这解释了波次 1 一个怪现象：某个旋钮让钱只多了 $176（统计上是零），
   胜率却涨了 28.7 个点。

> **由此得到的度量原则**：**比赛只记输赢，所以验收必须用胜率，不能用钱。**
> 已量到的反例有两个方向 ——
> （a）钱一分没多、胜率涨 28.7 点；
> （b）对手 w48 我们抽走的钱最多（$21,012）却胜率最低（86.3%），
> 而对 w68 抽走最少（$7,156）胜率最高（98.4%）。
> **按「多赚钱」优化，会把策略推向高方差的对局，而天梯只数你赢了几次。**

---

## 6. 我们在天梯上输的那些局，输在哪

**分析了什么**：已提交的 `topline` 在真实天梯上 59 局输了 13 局，是怎么输的。
**路线**：对局摘要里存了按天的资金轨迹，直接看领先量什么时候开始逆转。

我方的对局摘要在胜局和败局里**逐字节相同**（开环重放，本来就不会变），
所以**所有差异都是对手造成的**。

```
我方领先中位数    d5      d10     d15      d20     d25     d29
赢的局          -407   +1,490  +9,602  +8,994  +8,572 +11,284
输的局           +80     +537  +7,200  +3,981    +837    -632

输的局里我们仍领先:  d15 92%  →  d20 77%  →  d25 54%  →  d29 31%
```

**十三局败仗里有十二局，我们在第 15 天还领先。** 之后单调失血；赢的局里领先是扩大的。
所以问题不是「什么时候落后」，而是 **「第 15 天之后我们不再增长」**。

### 领先量的增量曲线，对不同对手

把领先量的逐窗口变化画出来（正 = 我们在拉开，负 = 被追）：

```
对手       终局胜率    d0-5   d5-10  d10-15  d15-20  d20-25  d25-29
w39        96.1%    -396   1,662   8,368  -1,618  -2,228     386
w48        86.3%    -407   2,522   8,789    +795  +3,654  +5,658
w16        94.9%    -220   1,617   5,690    -617  +1,075  +1,646
w68        98.4%    -407   1,982   8,507  -1,416  -3,171   1,661
                                      ↑
                          对每一个对手，峰值都在 d10-15
```

**分割很清楚：**

- **d10–15 的峰值是我们这条线自身的性质** —— 对四个对手全部成立，幅度相近
- **d15 之后发生什么完全由对手决定** —— 对 w39/w68 是负的，对 w48 却在加速

所以不是「我们在 d15 露了破绽被抓」。是**我们的增长在 d15 用完了，之后拼谁的
后半段更强，而我们的后半段是一段录音，不会变**。

### 打赢我们的对手做了什么不一样的事

```
                 我方   对手(我赢)   对手(我输)
牛                10        8           8
卖出牛奶         279      241         320
卖出化肥       1,708      235         300
卖出小麦       1,037      455         479
残留杂草          13        5           5
```

**我们 10 头牛产 279 桶奶（28/头），打赢我们的对手 8 头牛产 320 桶（40/头）——
每头牛差 43%。**

我们雇更多人（277 vs 266）、养更多牲畜、总成交量是他们两倍多，然后输。
因为 3,511 个单位里 **2,745 个是化肥和小麦** —— 一个被砸到 3.5 倍深度收在 $1，
一个地板价 $17。

---

## 7. 最大的发现：商铺抽取

**分析了什么**：棋盘上哪些变量会同时影响双方，决定我们和对手的相对关系。
**路线**：每局记录里都存了解锁的商铺组合，拿 4,096 局对真实录音的对局做分组比较。

城镇每 3 天解锁一家商铺，**8 家有放回地抽 8 个实例**，每家每 4 步消耗固定商品。
**这个抽取决定了哪些市场能维持在地板价以上。**

```
消耗牛奶的商铺实例数  局数   胜率            我方钱     对手钱   终局奶价
      0            100   64.0%          58,964    61,066      $1
      1            392   88.8%          73,578    67,866      $1
      2           1036   84.9%          76,804    71,487      $1
      3           1024   92.6%          92,108    80,446      $1
      4           1048   95.4%         105,930    94,344     $47
      5            420   98.1%         111,990    99,652    $197
```

**胜率跨度 64% → 98%，我方收入跨度接近两倍。** 而这是一个**两个玩家都控制不了**
的变量。

最右边那列是机制：**≤3 家时牛奶市场饱和、收在 $1；4 家时城镇消耗刚好越过供给，
价格活过来；5 家时接近基准价。**

8 个商铺名额是零和的，所以多一家胡萝卜店（我们一季只卖 20 个胡萝卜）就少一家
有用的 —— 胡萝卜商铺 ≥3 家时我们掉 6.4 个点。

### 两条比标题更重要的细节

**（a）它是对手特异的**

```
w48:  78.1% [75,81] → 98.0% [96,99]   +20.0 点   区间不相交
w16:  84.1% [81,87] → 94.6% [91,97]   +10.5 点   区间不相交
w39:  +2.0 点     w68:  +0.6 点        —— 无效应
```

**商铺抽取只在两个计划的产品结构不同时才决定胜负。** 把双方联系起来的不是市场
库存本身，而是**城镇恰好想要谁的产品**。

**（b）越早解锁越好，单调**

```
第一家牛奶商铺出现在  d3: 96.4%  d6: 90.4%  d9: 89.6%  d12: 83.0%  d15: 79.2%  从不: 64.0%
```

### 这留下的口子

`obs["town"]["unlocked_shops"]` 是**公开字段**，每 3 天填进一个，
到第 12 天已经看到 8 家里的 4 家。

**「哪些市场会保持流动」在赛季中期就是可知的，而且值最多 20 个点。**
会读盘的 agent 可以把产量往抽到的商铺上调；**录音做不到 —— 它种什么就是什么。**

这是四波以来唯一一个**不是自博弈假象**的方向，而且它是**单人问题**：
不需要对手模型，只需要对着棋盘方差做优化。

---

## 8. 一个没跑通的方向：从录音里找行为规律

**分析了什么**：排行榜前列的队伍，录音里有没有已经在用某种市场技巧。
**路线**：从 371 条录音提取 14 个市场行为特征，用它们各自的**真实天梯胜负记录**
（`wins/plays`，不是我们模拟的）当标签做相关。

**空结果。** 最好的 |spearman| ≤ 0.28，而且**门槛一变排第一的特征就换**
（wheat → prem → mean_sell_idx），有一个特征在两个子集里**符号相反**。
这是噪声的签名。

**但过程中量到一个更有用的结构数字**。全部 266,749 个录制回合：

```
53.61% 的回合   一个市场单都不下
29.87%          只下 1 个
82.26% 的回合   一个 SELL 都没有
```

**10 个槽位，83.5% 的回合只用到 0–1 个。** 大多数回合里根本没有可排序的东西。
而 371 条线里有 306 条整季至少用满过一次 10 格 —— 他们**会**用，
只是集中在极少数回合（终局清仓、集中雇工）。

**所以没有人在做槽位策略，结构上也没多少空间做。**

---

## 9. 抓到的四个静默无操作

**分析了什么**：这轮实验自己出过什么错。
**路线**：全部由控制组发现 —— 实验臂的结果和对照组一模一样，就是信号。

这个环境里**非法动作是静默无操作** —— 没有报错、没有代价，bug 看起来和坏策略
一模一样。这轮的实例：

1. **`_RESERVE` 整条路径是坏的**（仓库原有）。它从**回合开始时**的仓库重新规划
   卖单，而录音是当回合把货落库后才卖 —— 控制器看不见那批货，不下单，货烂在仓里。
   实测：羊毛挂单从 136 个掉到 63 个，我方 $63,550 → $43,073。
   **这条路径在这个仓库从来没有被执行过**，连带 `_RAMP_START` / `_RAMP_END` /
   `_SHED_PRESSURE` 三个死旋钮。
2. **替代单被 10 格上限丢弃**：先删掉录音的卖单，再挂替代单，队列满时替代单被丢，
   结果那个商品整季没卖。单局代价 $19,000。
3. **`_X_NO_LAND` 被提前返回跳过**：`_x_market` 开头的 guard 漏写了一个旋钮名，
   整条臂和对照组一分不差。
4. **`_FRONT_RUN_ITEMS` 扩集会抛异常逃逸**：`_GLUT_WEIGHT` 只有四个高价品的键，
   扩集会 KeyError，而且抛在 `try` 外面 —— 比无操作更糟。设计文件里预先处理了。

> **纪律**：每一波都必须带一个「逐字节相同的副本」和一个「实验框架在位但旋钮全空」
> 的副本。两个都必须回到 50%。回不到就先修仪器，一条实验臂都不许读。

---

## 10. 这轮之后，方向清单

**分析了什么**：上面所有结论合起来指向哪里。

| 方向 | 判决 | 依据 |
|---|---|---|
| 干扰对手的市场 | **死路** | 19 条臂，对手的钱无一下降 |
| 调包装层的参数 | **已到底** | 全部组件加起来 4 个点，且已在最优设置 |
| 找一条更好的固定录音 | **有限** | 再好也不看棋盘，64%–98% 的方差还在 |
| **让产量响应商铺抽取** | **活的** | 值最多 20 点，公开可知，且是单人问题 |
| 真正的对手建模 | **未被否定** | 只否定了 19 种手写规则，不等于否定这一类 |

（后记更新至 2026-08-24：会读棋盘的 agent 已经建成；后续容量、词表、课程、奖励和
长信用实验把剩余瓶颈定位到稀有长期战略决策的信用分配，不再只是“目标函数与对手池”。
证据见 `docs/RUNS.md` 顶部总览，下一步见 `rl/TODO.md`。）

**最重要的一条背景事实**：照抄录音的天花板是量过的 —— 榜首队伍的录音重放后
只保留 **80.5%** 的评分（差 630.8 点，2026-08-14 用 k06 重测；k01 是 73% / 877 点）。
前 10 名门槛 3,061.4，而完美复制榜首是 3,235.7 —— **天花板在奖金区内，卡住的是保留率**。

包装层现在被证明只值 4 个点，所以那 630 点**不在包装层里**。
它在剧本，以及**剧本不会看棋盘**这件事上。

---

## 11. 商铺响应：市场层这条路也关了

**分析了什么**：能不能在不重写 agent 的前提下，让它对商铺抽取做出反应。
**路线**：先查产量能不能改（不能），再修好文件里唯一的商铺感知模型，重测唯一用到它的旋钮。

### 产量被录音锁死

`PLANT` 的动作是 `["PLANT", "CARROT"]` —— **作物名写在动作里**。而且引擎有一条原子
校验：某作物的播种请求超过种子存量时，**当回合该作物的全部播种请求一起作废**。
所以改市场队列里的买种单不但重定向不了产量，还可能把一整回合的播种打掉。

**真正的产量响应必须重写 agent。**

### 唯一的商铺感知模型算错了

`_remaining_drain(item, step, shops)` 是文件里唯一读 `town.unlocked_shops` 的代码。
拿 200 个真实天梯商铺抽取比对引擎实际消耗：

```
              agent 估计   引擎实际
MILK   step0      491        336     1.5x
WOOL              374        210     1.8x
MELON             140         30     4.7x
       step360    100         15     6.7x
```

它把 town center 写成**每 12 步触发、带 1/2/4 的倍率递增**；引擎是**每 24 步、
倍率恒为 1、无递增**（看起来是 1.32.6「城镇需求减半」之前的余留）。西瓜最严重，
因为没有任何商铺消耗西瓜，它的估计里全是那个错的项。

### 修好之后重测，还是没用

这个模型只喂给 `_race_factor` —— 给「注定过剩」的品类加槽位优先级。
20 个单元、56,320 局：

```
合并全部 race>0 的单元（实场，各 16,384 局）
  坏模型   86.27%  [85.73, 86.79]
  修正后   86.62%  [86.09, 87.13]     +0.35 点，区间大幅重叠，不显著

race 权重本身（合并两种模型，各 8,192 局）
  r0(关)  87.67%  [86.94, 88.37]     ← 最优
  r05     87.21%
  r1      86.63%
  r2      86.24%
  r4      85.69%  [84.92, 86.43]     ← 与 r0 区间不相交
```

**在两种模型下，抢跑权重都单调有害，最优值都是 0。**

> **一次被证伪的事前预测**：设计文件里预先写了「修正后的模型报告更少的剩余需求，
> 会让 `_race_factor` 触发得更频繁更用力，所以应该**更差**」。实际是**略好**
> （+0.35 点，不显著）。所以那个机制解释方向就是错的。诚实的读法是：
> **修正模型几乎没改变「抢哪些品类」，因为这个机制本来就没用。**

### 结论

**商铺响应在市场层这条路关了。** 那 34 个点的空间只能在**产量侧**拿，
而产量侧被录音锁死 —— 只能靠重写 agent（这项工作现由 `rl/` 线承担；
剧本线的对应路线是 C）。

这也是五波实验最终的收敛点：**包装层已经被榨干（总共 4 个点，且已在最优设置），
剩下的全部价值在剧本本身，以及让剧本会看棋盘。**

---

# 附：能不能靠压制对手取胜（2026-08-10 的研究，与上文对账）

> 原 `docs/ANALYSIS.md`，2026-08-14 并入。当时用的是**手写的闭环 agent**
> （`agents/adv/*`、`agents/probes/*`，从未提交，`agents/` 是 git-ignored，已不在磁盘上），
> 证据在 `data/arena.sqlite` 里。原文在 git 历史里。

## 它测到了什么

**倾销打败惜售，而且是大幅打败。** `dump_all`（照常生产，但见货就卖，不保护自己的价格）
对 `barnyard`（惜售）在 384 局满功率下：

```
胜率 71.4%  [66.6, 75.6]     边际 +$4,444  [+3,770, +5,146]
自己的钱中位 35,776          惜售那边通常是 47,880
座位 0: 72%   座位 1: 70%    —— 不是座位假象
```

**71.4% 的胜率，靠的是自己少赚 25%。** 它把两边的分都往下拖，而把对手拖得更狠。

机制在于池子是**有限且共享**的：把一个池子砸到 $1 需要卖掉有限个单位，而**沿途的钱
归砸的人**（羊毛 59 个收 $7,928，西瓜 158 个收 $26,485）。所以**「先占住池子」和
「让对手拿不到」是同一个动作**，不是取舍。

## 它和上文 §2 的关系 —— 不矛盾，是同一条规律的两面

上文 §2 说：19 条干扰臂全败，且**对手的钱无一下降**。字面上像是反对「倾销有效」。
实际是这样：

- `dump_all` 是**为倾销而设计的闭环 agent**，它照常生产、只是不保护价格
- 我的 19 条臂是**给一段固定录音强加干扰**，而这段录音（k01）**本来就是倾销者** ——
  一季卖 3,511 个单位，把化肥和牛奶都收在 $1

**所以 §2 里每一条「让它少卖 / 囤起来 / 换个卖法」的臂，都是在把倾销者改成惜售者。**
按这里的结论，那正是变弱的方向 —— 而实测也确实如此：我们一停手，对手照单全收
（囤羊毛那局牛奶从 $1 涨到 $183，对手净赚 +$60,996）。

**两份测量指向同一件事：这个游戏奖励先把池子占掉，而我们已经在这么做了。**

## 一处需要修正的措辞

原文 §1 写「**只有一条通路**：市场」。引擎层面更准确的说法是**两条** —— 另一条是
日终 RNG（见上文 §2「引擎层面」和 §5）。但那一条要知道 seed 才能定向，
**作为攻击手段确实只有市场一条**，原文的结论成立。

## 还成立的两条

- **纯封锁在机制上不可能** —— 你够不到对方的地块、牲畜、仓库、种子、人手，
  没有攻击动作、没有破坏、没有偷窃
- **策略空间非传递** —— flood > metered > spite > flood，全部实测。任何排名都是
  相对它的场地而言

---

# 附：这个游戏的经济学 —— 引擎实际奖励什么

> 原 `docs/ANALYSIS.md`，2026-08-14 并入。这一节**不是历史** ——
> 它是当前引擎的事实清单，改动 agent 之前应该先在这里查一遍。

Everything here is derived from `reference/engine/kaggriculture.py` — a copy of
the file the episodes import — not from the competition's prose, which is stale
in several places (§2). Re-diff that copy against the installed package after
every `kaggle-environments` upgrade; the balance has already changed once
mid-competition.

Companion documents: `docs/ROADMAP.md §11` measures which of these levers
actually pays, and `docs/ANALYSIS.md` covers what you can do *to* the
opponent.

## 1. What the competition actually is

Two agents each run a farm for one 30-day season = **720 turns** (24 turns/day).
Whoever has more **coins in the bank** at the end wins. Unsold inventory scores
zero. Rating is Elo-style: only win/loss/tie matters, never the coin margin. A
final Bradley–Terry tournament decides the leaderboard.

Each turn an agent returns:

```python
{"farmer": [op, *args], "hands": [[op, *args], ...], "market": [[op, *args], ...]}
```

The main farmer plus every hired hand each get one action; up to
`maxMarketOrdersPerTurn` (10) market orders are processed per turn.

**This is a scheduling problem wearing a farming costume.** The scarce resource
is *actions*, the scarce asset is *tiles*, and the price of everything you
produce moves against you as you sell it.

### Hard constraints worth memorising

| Constraint | Value | Why it bites |
|---|---|---|
| `actTimeout` | **1 second per turn** | No search. Heuristics only. 60 s total overage bank. |
| `shedCapacity` | 100 items | Overflow at end-of-day is **discarded**, not queued. |
| `maxMarketOrdersPerTurn` | 10 | Hires, land, buys and sells all compete for these slots. |
| Submission size | 100 MiB | Runtime: 1.6 vCPU, 6.5 GiB RAM, 8 GiB disk. |
| Daily submissions | 5 | Only the latest **2** stay active. |

---

## 2. The 1.32.6 rebalance — and why old meta data is now suspect

`reference/engine/kaggriculture.py` is the ground truth: it is the file the
episodes import. It **disagrees with the overview page**, and the reason matters.

On **2026-08-06/07** the host shipped a balance change
([discussion 733431](https://www.kaggle.com/discussions/kaggriculture/733431),
[PR #1394](https://github.com/Kaggle/kaggle-environments/pull/1394)), announced as
*"rolling out and hitting the leaderboard — make sure to upgrade to >= 1.32.6"*:

| | Before (what the overview page still describes) | After (1.32.6, what runs now) |
|---|---|---|
| Town centre | buys **2×/day**, escalating to 2×/4× after days 10/20 | buys **1×/day**, flat all season |
| Shop unlocks | sampled **without** replacement | sampled **with** replacement, capped at 8 instances |

The host's stated reason: *"The large demand from the TC meant that markets were
too resistant to sell pressure later in the game."*

**Two consequences that drive everything below.**

1. **Markets are now much more fragile.** Town demand was cut by roughly half to
   three-quarters late-game. Overproducing and dumping is punished far harder
   than it was a week ago. Metered selling matters more, and large herds matter
   less.
2. **Every public meta analysis dated 2026-08-06 or earlier describes a game that
   no longer exists.** That includes the daily episode datasets and the modal
   "8 cows + 6 sheep" farm in §5 — that composition was calibrated against
   *double* the town-centre demand. Treat pre-08-07 strategy conclusions as
   historical, not as targets.

Shops drawn with replacement also means **each game is genuinely different** —
one episode may spawn four Yarn Stores and no Bakery. A fixed crop-and-herd plan
is now strictly worse than one that reads `obs["town"]["unlocked_shops"]`.

Also not on the overview page: **`actTimeout` is 1 second**. The framework
deducts only the *excess* over one second from the 60 s bank
(`overage_time_consumed = max(0, duration - actTimeout)` in `core.py`), so the
real budget is 1 s every turn *plus* 60 s of borrowing across the episode.

Re-diff `reference/engine/` against the installed package after every
`kaggle-environments` upgrade — this has already changed once mid-competition.

---

## 3. The economics

### 3.1 Price curves

```
price(inv) = base ± amp · f(|inv − I0|),     amp = target · base / f(T)
```

Every product starts at `I0 = 10,000`. Selling pushes inventory up and price
down; town consumption pulls it down and price up. Floored at $1.

The `above_func` is what decides how badly you can hurt yourself. Units you can
dump from equilibrium before hitting the $1 floor:

| Product | Base | `above_func` | Units to floor | Character |
|---|---|---|---|---|
| Wool | 200 | `sq` | **59** | Dumps instantly |
| Strawberry | 120 | `linear` | **62** | Dumps instantly |
| Milk | 160 | `linear` | **76** | Dumps instantly |
| Melon | 250 | `sq` | **158** | Cheap early, cliff later |
| Tomato | 60 | `sqrt` | ~555 | Gentle |
| Carrot | 35 | `sqrt` | ~918 | Gentle |
| Wheat | 25 | `log` | 3000+ | Effectively never crashes |
| Egg | 50 | `log` | 3000+ | Effectively never crashes |
| Fertilizer | 100 | `linear` | ~500 | Steady bleed |

Melon's quadratic curve is worth internalising: the first 10 melons cost you
$1 of price, the 158th costs you $250. Sell melon **early and wide**.

### 3.2 The town is the real customer

The 10,000-unit buffer is a one-off. What pays the bills all season is town
demand, and it is much larger than the buffer:

- Up to **8 shop instances**, unlocking one every 3 days from day 3.
- Each instance consumes one of each of its products every **4 turns** = 6×/day
  (single-product shops pull 2×).
- Plus the town centre: one of every non-fertilizer product per day.

That totals roughly **2,000 units of demand across a season**, weighted by which
shops happen to unlock. Wheat appears in 5 of the 8 shop types, strawberry in 4,
milk in 3, egg and tomato in 2, carrot and wool in 1 each (both at 2×), and
**melon in none**.

Two consequences:

- **Melon is a fixed pool, not a faucet.** Its only demand is the town centre's
  1/day. Total extractable value across the whole season is roughly **$26k**,
  and it is *shared with the opponent* — first seller wins.
- **Herd size should track town demand, not land.** ~3 shops wanting milk absorb
  ~18/day; 8 cows on daily `CARE` produce ~12/day. The public meta's "8 cows +
  6 sheep" is calibrated to exactly this, not chosen arbitrarily.

### 3.3 Fertilizer is one-way

Every surviving animal makes 1 fertilizer per day, free, fed or not
(`fertilizer_available = True` on every end-of-day refresh). It is worth ~$100
at base.

**No shop and not the town centre consumes `FERTILIZER`** — check
`TOWN_CENTER_PRODUCTS` and `SHOPS` in the engine. So its market inventory only
ever rises and its price only ever falls. Holding fertilizer for a better price
is *strictly* a losing move. Sell every unit the turn it reaches the shed.

### 3.4 Farm hands: the cheapest lever, up to a point

The n-th hire of a day costs `fib(n)` = 1, 1, 2, 3, 5, 8, 13, 21, … and each hand
buys 24 extra actions that day. Cumulative payroll:

| Hands | 5 | 8 | 10 | 12 | 14 | 16 | 17 | 18 | 20 |
|---|---|---|---|---|---|---|---|---|---|
| Cost/day | 12 | 54 | 143 | 376 | 1,596 | 2,583 | **4,180** | 6,764 | 17,710 |

The first eight hands cost less than one melon seed. The 17th hand alone costs
more than the first fifteen combined. Testing confirmed the curve: pushing
`HAND_CAP` from 14 to 16 *lost* ~10k because payroll outran the extra output.
Budget the day's payroll as a fraction of cash rather than chasing a head count.

### 3.5 `CARE` roughly triples animal output

`CARE` + `FEED` on the same day banks +1 on `pending_care_bonus`, paid out on the
animal's next scheduled production. A cow (interval 2) goes from 1 milk per
2 days to **3 milk per 2 days** — $160/day extra for one action. Note the code
checks `fed_today` *before* resetting it, and an unfed animal still produces its
base 1 unit but forfeits the whole banked bonus.

### 3.6 Yield rules worth getting exactly right

- A fresh seed starts at `consecutive_unwatered = 1`. **Plant and water the same
  day or it is a weed by nightfall.** No grace period.
- One-shot crops gain +1 unit per watered day inside `[⌈max_yield_day/2⌉,
  max_yield_day]`; fertilizer makes it +2. Watering outside the window only
  keeps the plant alive, so the cheap pattern is *alternate days, then daily
  through the window*.
- Wheat and carrot **cannot** reach their listed max yield on water alone (4 and
  3, not 6 and 4). Melon reaches its cap of 6 on water alone by day 10 —
  fertilizing melon is wasted.
- Animals survive on **alternate-day feeding** (`consecutive_unfed >= 2`
  escapes), but the `CARE` bonus needs them fed *daily*.

### 3.7 Why nobody buys the fourth quadrant

The land is bought in a fixed order — NE $1,000, SW $2,000, SE $4,000 — and the
public meta's modal farm owns exactly `NE + NW + SW`. SE is never bought. The
reason is not geometry: all four quadrants are perfectly symmetric about the
shed, each owning one of the four shed-access tiles.

It is that **the market saturates long before the land does**, and the work that
does pay saturates even sooner. Expected town demand over a season plus the
initial 10,000-unit buffer, against what a single 25-tile quadrant produces:

| Product | Season absorption | One quadrant produces | Tiles that saturate it |
|---|---|---|---|
| Melon | 188 | 346 | **14** |
| Strawberry | 488 | 167 | 73 |
| Carrot | 1,169 | 562 | 52 |
| Wheat | 4,525 | 600 | 188 |
| Milk | 403 | — | ~13 cows |
| Wool | 287 | — | ~10 sheep |

Melon — by far the best crop per action — is fully saturated by **14 tiles**.
Animals saturate at roughly 13 cows + 10 sheep. That is ~37 tiles of genuinely
high-value work, which fits inside two quadrants.

Everything past that is low-value work competing for the same hands:

| Work | Coins per action |
|---|---|
| Animal HARVEST (6 units at once) | ~$960 |
| Melon bonus-window WATER | ~$250 |
| Sheep / cow daily cycle | ~$80 |
| Strawberry | ~$30 |
| Carrot / wheat / tomato | ~$16-21 |

So extra tiles do not add income, they add *cheap* tasks that starve the
expensive ones. Measured over 8 seeds, forcing the crop plan to fill more land
makes things monotonically worse:

| Config | Median money |
|---|---|
| 3 quadrants, crop plan ×1.0 | **68,892** |
| 4 quadrants, crop plan ×1.0 | 68,892 (never actually buys SE) |
| 3 quadrants, crop plan ×1.6 | 63,724 |
| 4 quadrants, crop plan ×2.2 | 55,766 |

And on quadrant count alone: 1 → 49,078 · 2 → 68,738 · 3 → 68,892 · 4 → 68,892.
**The second quadrant is worth ~20k; the third is noise; the fourth is worth
nothing and costs $4,000** — which instead buys 10 cows.


---

## 4. The three public notebooks

Pulled into `reference/notebooks/` (`.ipynb` plus a `.py` conversion for
grepping).

### `bovard/kaggriculture-getting-started` — the official tutorial (342 votes)

Walks the observation format and ships **"Melon Maxxer"**: buy a melon seed when
out, walk to the nearest tile needing work (harvest > water > plant), sell the
whole shed when melon price ≥ $200. The notebook then lists its own flaws — never
hires, never buys land, monocrops, and dumps its entire inventory in one order,
crashing the price mid-sale. Useful as a floor and as a correct reading of the
observation schema; not competitive.

### `cjlcjlcjl/kaggriculture-what-the-top-farms-do-a-live-meta` — the meta tracker

The most valuable of the three. It re-derives the engine's economics
(profit per tile-day, yield curves, the price-cliff table) and then **streams the
official daily top-episodes dataset** to tally what high-Elo players actually
built. Its 2026-08-06 snapshot (Elo band 2700+, 683 episodes):

- **Modal farm: 8 cows + 6 sheep, 5 hands, land NE+NW+SW — 44% of players.**
  Notably *no crops* at the top.
- Ending money: **median 115,664, max 168,527**.
- Build order (median first-order day): first hire **day 0**, first cow **day 0**,
  first sheep **day 0**, first land **day 7**.
- Early seeds, days 0–4: wheat 14.0, melon 11.6 per player.
- Cash curve: d5 = 299, d10 = 2,212, d15 = 21,272, d20 = 45,689.
- Sell rhythm (first day / avg batch): fertilizer d3/4.5, wheat d2/5.6,
  wool d9/5.3, melon d10/12.8, milk d10/4.8, strawberry d18/12.2.
- Ladder Elo moved from median 670 (07-30) to 2,973 (08-06) — the bar rises
  ~100 points a day, so a fixed strategy goes stale in about a week.

Its headline advice: sell in small metered batches, and since everyone runs the
same farm, **differentiate on timing** — sell into the shared market before the
opponent's harvest lands.

> **Caveat:** every number above predates the 1.32.6 rebalance (§3). The modal
> farm was tuned against a town centre buying twice as much, and against shops
> drawn without replacement. Its *method* — stream the daily dataset, tally what
> wins — stays valid; its *conclusions* need re-deriving on post-08-07 episodes.

### `flexonafft/kaggriculture-adaptive-replay-agent` — trajectory replay

A different school entirely. It embeds **two complete pre-optimised action
sequences** (zlib + base85 blobs) and picks one at episode start based on melon
and strawberry prices, then replays it verbatim. It never mixes routes mid-game.
Runtime adaptation is deliberately minimal:

- weed recovery when the board drifts from the recording,
- `_front_run_market`, which re-ranks existing SELL orders by opponent exposure ×
  glut weight × price × `log1p(qty)` — reading the opponent's tiles to sell ahead
  of their harvest,
- `_terminal_overlay`, an endgame liquidation that `PLACE`s every unit's
  inventory into the shed and dumps it,
- a divergence counter that falls back if the board stops matching.

Worth stealing: the endgame liquidation and the front-running sell ranking. The
approach itself — offline-optimise a trajectory, replay it — is a credible route
to the top given the environment is near-deterministic apart from weed RNG, shop
draws, and the opponent.

---


---

## 5. How the leaderboard score is produced

There is no metric computed from a file. Your rating is an **outcome of playing
games**, and it moves entirely on win/loss/tie — the coin margin never enters.

### Live ladder (now until 2026-09-30)

1. **Validation episode.** Every submission first plays one game against a copy
   of itself. Crash or timeout → `Error`, and `kaggle competitions logs` gives
   you the traceback. Ours (`90791512`) passed.
2. **Join the pool at the default rating.** Observed: **600.0**. This is a
   starting placeholder, not a measurement.
3. **Continuous matchmaking.** The server pairs active submissions — the latest
   **2 per team** — against opponents of *similar* rating, forever. New
   submissions play far more often, which pulls their rating to its true level
   quickly.
4. **Update after each episode.** Win → up, loss → down, tie → the two ratings
   converge. The size of the move scales with the rating *gap*: beating someone
   far above you moves you a lot, beating someone far below barely registers.
   Kaggle does not publish the exact update rule; treat the displayed number as
   a conservative estimate of skill that rises as uncertainty shrinks.
5. **The leaderboard shows only your best active submission.** Track the others
   on the Submissions page.

Practical implication: **variance is punished**. Since only win/loss counts, an
agent that reliably banks 80k beats one that averages 100k but occasionally
collapses. Optimise the win rate against a real opponent, not the mean score in
a mirror-free sandbox.

### Final evaluation — the Bradley-Terry tournament

Confirmed by the host in [discussion
731587](https://www.kaggle.com/discussions/kaggriculture/731587): submissions
lock at the deadline, episodes keep running for ~2 weeks, and then a **single
Bradley-Terry tournament** over that match record produces the final leaderboard.

Bradley-Terry is a model for pairwise comparisons. Each agent gets one strength
parameter `p_i`, and

```
P(i beats j) = p_i / (p_i + p_j)
```

All strengths are fit **at once**, by maximum likelihood, over the entire set of
observed episodes. The contrast with the live ladder is the whole point:

| | Live ladder (Elo-style) | Bradley-Terry |
|---|---|---|
| Updates | sequential, one game at a time | one batch fit over all games |
| Order of games | changes the result | irrelevant |
| Hot streaks | inflate the rating | averaged away |

The host's stated reason is exactly this: *"this change reduces any 'hot streaks'
that may otherwise influence the final results."*

So the ladder rating you watch day to day is a **noisy progress indicator**. What
decides the prize is your aggregate head-to-head record over the final two weeks.
Consistency compounds; a lucky run does not.
