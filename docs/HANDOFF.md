# 交接：笔记本 PPO 对 barnyard（2026-08-21）

> 这不是项目总路线图。总入口仍是 [`README.md`](../README.md) →
> [`ONBOARDING.md`](ONBOARDING.md) → [`rl/README.md`](../rl/README.md)。
> 本文只覆盖 **2026-08-20～21 这条笔记本工作线**：官方参考引擎上的逐单位
> PPO，对手永远是真 `agents/barnyard.py`。集群 TorchRL（siege / breach /
> `rl/train.py`）是另一套管线，检查点不能混用。

接手前先读 [`VALIDATING.md`](VALIDATING.md)。数字怎么采、怎么算数，那份说了算。

---

## 0. 一分钟

我们在让 **会看棋盘的 RL agent** 在官方引擎上少输给 `barnyard`。天梯只计胜负，
所以考试主量是 W–L，金钱分差只说明「少输了多少」。

当前最好的考试产物是 **Transformer 80 轮从零训**（贪心导出）：对 barnyard
**6–26**，己方中位 **$33,734**，平均分差 **−$3,943**。仍明显弱于对手，但已经
超过这条线上所有 MLP 检查点，也超过无网络的 idle-restock（同分 6–26，但少赚
约 $3k、多分差约 $3k）。**CNN 同预算从零训失败。不要提交。**

---

## 1. 在做什么任务

比赛是 Kaggle 仿真：720 步农场季，一对一，排名只看胜负。本地手写调度器
（`barnyard`）在这条线上当墙：它能养到约 22 头牲畜、终局约 $40k–$55k；MLP
策略养到约 6–12 头、考试中位约 $27k–$31k，32 局对打常常 0 胜。

这条工作线的选择（相对集群 TorchRL）：

| | 集群 TorchRL | 本机这条线 |
|---|---|---|
| 入口 | `python rl/train.py` | `python -m rl.train_ppo` |
| 引擎 | 张量引擎（GPU 批量） | 官方 `kaggle-environments` |
| 对手 | starter / pitchfork / 张量化 barnyard | **真** `agents/barnyard.py` |
| 动作 | 宏动作或 `--multi-head` | 已是逐单位：farmer + 12 hand + market |
| 验收 | `slurm/rl_eval.sh` 十对手花名册 | `tools/eval.py h2h … --seeds 16 -j 8` |

本机不跑集群那套的原因：GPU/张量上的 `win=` 不是考试；对 starter 微调过的网
导出后考试更差；真 barnyard 还没接到 `rl/gpu` 这条采集环。

目标不是「把 ep_reward 拉正」，而是：**官方引擎、换座、对 barnyard，出现稳定胜场。**
16 种子 × 2 座位 = 32 局只是探针；96 局才能分辨约 10 个点的胜率差。

---

## 2. 完成了什么

代码在 git 分支 `new-branch` 上，**多数还没 commit**（检查点和 `logs/` 本来
就不进 git）。下面按时间，每条都附考试数字。

### 2.1 训练信号（保留）

- **畜群势函数**（`rl/potential.py`，镜像 `rl/gpu/obs.py`、
  `rl/tensor_env/potential_future.py`）：`PLANT_CREDIT=0.25`，
  `ANIMAL_CREDIT=0.9`，`SHED_ANIMAL_CREDIT=0.85`，`HERD_ASSET=200`，
  `HOUSING_VALUE=80`。selfcheck：番茄株约 +$60，瓜约 +$375，棚里的牛约 +$340，
  已放置且喂过的牛约 +$1928。改信用只改 `potential.py` 的命名常量。
- **对手**：`train_ppo` 默认只打 `agents/barnyard.py`，`mix-prev=0`，
  `switch-after` 极大。starter 混进训练会占住奖励山，考试用不上。
- **阶段软 logit 偏置**（不是掩码）：天 0–8 BUILD +2.0；天 9–27 WATER/HARVEST/FEED/CARE
  +1.5；天 28–29 HARVEST +2.0、DUMP +2.0。从 `feats[4]=clamp(step/720)` 反推日历日。
  `act` 和 PPO 更新都要加（`rl/ppo.py`、`rl/gpu/policy.py`、`rl/spatial_policy.py`、
  `rl/export_multihead.py` 生成的 `_forward`）。学到的先验没动：IDLE +2.5，RESTOCK +1.5。
- **日志**：`train_ppo` 写 `log.csv`（iter / opp / ep_reward / win / money /
  omoney / pol / val / ent）。工人返回双方终局金钱。循环变量曾叫 `ep_opp`，
  把金钱列表盖掉了，已改名为 `ep_omoney`。

### 2.2 解码器补丁（已回退，不要恢复）

试过：空目标改走调度器、HOLD→RESTOCK、禁种番茄、`HAND_CAP` 12→14。
官方考试全部更差。已 `git checkout -- rl/action_space.py`。
策略头继续 **12 只手**。非法动作在引擎里是静默空操作，解码器「看起来更合法」
不等于会赢。

### 2.3 训练过的检查点

| 目录 | 是什么 | 墙钟 | 训练采样末段 |
|---|---|---|---|
| `rl/ckpt_official/ppo_it0300.npz` | 官方 300 轮 MLP（课程含 starter） | （更早） | — |
| `rl/ckpt_herd/ppo_it0080.npz` | 从 0300 续训，畜群势，对 barnyard 80 轮 | ~536 s | 己方 ~$18k，0 胜 |
| `rl/ckpt_phase/ppo_it0300.npz` | 从 herd 0080 再 300 轮 + 阶段偏置 | 2752 s | 末 10 轮 ~$25.4k / 对方 ~$47.4k，ep_reward −45→−33，0 胜 |
| `rl/ckpt_cnn/ppo_it0080.pt` | CNN 从零 80 轮 | 2105 s | 末 10 轮 ~$7.7k，熵 15→11 |
| `rl/ckpt_transformer/ppo_it0080.pt` | Transformer 从零 80 轮 | 7466 s | 末 10 轮 ~$11.6k，熵维持 ~17 |

CNN / Transformer **不能**加载 75→256 的 MLP npz。空间读出零初始化，主干是随机的
`(75+64)→256`。这是架构从零对比，不是在 380 轮 MLP 上加一层。

### 2.4 官方考试（同一把尺子）

命令形态：

```bash
PYTHONPATH=. KG_FAST_ENV=1 ./venv/Scripts/python.exe tools/eval.py h2h \
    <agent.py> agents/barnyard.py --seeds 16 -j 8 -o logs/h2h_<name>_vs_barnyard.json
```

`seed0` 默认 10000，16 种子换座 = 32 局。下面五行是同一组种子。

| Agent | W–L | 己方中位 | 对方中位 | 平均分差 | 产物 |
|---|---|---|---|---|---|
| **Transformer 80** | **6–26** | **$33,734** | **$36,180** | **−$3,943** | `logs/labour-heads-transformer.py` |
| idle-restock（无网络） | 6–26 | $27,659 | $37,764 | −$7,197 | `logs/idle-restock.py` |
| 阶段偏置 MLP 300 | 0–32 | $30,675 | $42,968 | −$11,692 | `logs/labour-heads-phase.py` |
| 官方 MLP 300 | 0–32 | $27,389 | $42,222 | −$12,927 | `logs/labour-heads-official.py` |
| CNN 80 | 0–32 | $16,606 | $52,464 | −$33,313 | `logs/labour-heads-cnn.py` |
| 张量引擎 +3 轮对 starter | 0–32 | $24,919 | $41,180 | −$15,790 | （更早，已弃） |

Transformer 的 6 场胜利里，有 4 场是 idle 在**同一种子座位**输掉的
（10002/seat1、10012/seat1、10013/seat0、10015/seat1）。不完全是商店抽签碰巧。
对方中位从 ~$43k 降到 ~$36k，说明我们的空格改变了杂草/商店 RNG；分差仍以己方金钱为主。

训练时 `win=` 是**采样**策略，考试是**贪心**。Transformer 训练金钱 ~$12k、考试中位
$34k，就是这个差别：熵 ~17 时采样把局打散了。不要拿训练 `money=` 和考试中位比。

Wilson 区间不要看：`tools/stats.py` 的 `wilson()` 已经返回百分数，
`tools/eval.py` 又用 `{lo:.1%}` 乘了一次，会打出 `1071%`。看 W/L 和金钱。

---

## 3. 开在哪里

### 代码（改了、要用的）

| 路径 | 职责 |
|---|---|
| `rl/train_ppo.py` | 本机训练入口。`--net mlp\|cnn\|transformer` |
| `rl/ppo.py` | 75→256→256 多头 MLP + 阶段偏置 |
| `rl/action_space.py` | 解码器 + 阶段偏置常量。`HAND_CAP=12` |
| `rl/potential.py` | 势函数唯一信用源 |
| `rl/features.py` | 75 维全局特征。`STEP_FEATURE_INDEX=4` |
| `rl/board_obs.py` | 每农场 22 通道 × 10×10；打包观测 = 75 + 4400 |
| `rl/spatial_policy.py` | CNN / Transformer 主干 + 同一套 13×(1+12)+4 头 |
| `rl/export_spatial.py` | 空间网 → 本地考试 agent（依赖 torch，不能交 Kaggle） |
| `rl/export_multihead.py` | MLP npz → 单文件纯 Python（可交 Kaggle 的那条） |
| `rl/rollout.py` | 多进程采集；空间网 Windows 上 worker 封顶 4 |
| `rl/gpu/` | 批量张量环境。观测默认仍是 75 维；`encode_packed` 已写好但训练环还没用 |
| `rl/selfcheck.py` | 含 `test_spatial_forward` |

### 产物（git-ignored / 本地）

`.gitignore` 忽略 `logs/`、`rl/ckpt*/`、`rl/*.npz`。换机器要把检查点拷走，否则只剩代码。

| 路径 | 内容 |
|---|---|
| `rl/ckpt_phase/ppo_it0300.npz` + `log.csv` | 最好的 MLP |
| `rl/ckpt_transformer/ppo_it0080.pt` + `log.csv` | 最好的考试网 |
| `rl/ckpt_cnn/ppo_it0080.pt` + `log.csv` | 对照，弱 |
| `logs/h2h_*_vs_barnyard.json` | 32 局原始对局 |
| `logs/*_train.log` | 训练 stdout |

曲线看板不在 git 里，在 Cursor 本机 canvases 目录，聊天旁打开：

- `C:\Users\Lenovo\.cursor\projects\c-Users-Lenovo-Desktop-Kaggriculture\canvases\rl-training-curves.canvas.tsx`（阶段偏置 300 轮）
- `C:\Users\Lenovo\.cursor\projects\c-Users-Lenovo-Desktop-Kaggriculture\canvases\spatial-arch-vs-barnyard.canvas.tsx`（CNN / Transformer 考试）

### 环境

Windows 笔记本。`setup_env.sh` 找的是 `venv/bin/activate`，这里没有，**不要 source**。

```bash
cd /c/Users/Lenovo/Desktop/Kaggriculture
export PYTHONPATH=. KG_FAST_ENV=1 KG_ROOT="$(pwd)"
./venv/Scripts/python.exe -m rl.selfcheck
```

`open_spiel_env` 打到 stderr 是预期的（`kaggle-environments` 用了 `--no-deps`）。

---

## 4. 常用命令

验收（唯一算数的尺子）：

```bash
PYTHONPATH=. KG_FAST_ENV=1 ./venv/Scripts/python.exe tools/eval.py h2h \
    logs/labour-heads-transformer.py agents/barnyard.py \
    --seeds 16 -j 4 -o logs/h2h_transformer80_vs_barnyard.json
```

导出：

```bash
# MLP（Kaggle 单文件）
./venv/Scripts/python.exe -m rl.export_multihead --arch multi \
    --weights rl/ckpt_phase/ppo_it0300.npz --out logs/labour-heads-phase.py

# 空间网（本地考试，硬编码了本机绝对路径）
./venv/Scripts/python.exe -m rl.export_spatial \
    --weights rl/ckpt_transformer/ppo_it0080.pt \
    --out logs/labour-heads-transformer.py
```

续训 Transformer（从 0080，不要 `--init-weights none`）：

```bash
PYTHONPATH=. KG_FAST_ENV=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
./venv/Scripts/python.exe -m rl.train_ppo --arch multi --net transformer \
    --iters 80 --episodes 8 --workers 4 --save-every 10 \
    --opponents agents/barnyard.py --pga-frac 0.3 \
    --init-weights rl/ckpt_transformer/ppo_it0080.pt \
    --ckpt-dir rl/ckpt_transformer
```

注意：`log.csv` 是 append 的。续训前把旧 `log.csv` 拷走，否则曲线会接在 80 行后面、iter 号从 1 重计。

CNN / Transformer 在 Windows 上 worker 被代码封顶为 4（torch + spawn）。
Transformer 一轮约 50–100 s，80 轮约 2 小时；CNN 一轮约 17–30 s。

---

## 5. 下一步（按「值不值得做」排）

1. **Transformer 的采样/贪心鸿沟。** 训练熵 ~17、采样金钱 ~$12k，贪心考试 $34k。
   同一套权重，采集时过噪。先试更低 `--entropy`，或采集用较小温度 / 部分贪心，
   再从 `ppo_it0080.pt` 续训。这是最便宜、最对准已有证据的一步。
2. **从 0080 再训，不要从零。** 80 轮远短于 MLP 的 380。预期是「少输」而不是过半胜。
   续训后考试仍用 16 种子探针；若要对 idle 下结论，升到 96 局。
3. **不要再从零训 CNN。** 若还想试卷积：把 MLP 的 W1/W2/头装进
   `fc1[:, :75]`，空间列保持 0，让第一步前向等于现成 MLP。没做这个之前，
   CNN 数字不能拿来否定「棋盘卷积」本身。
4. **不要为了交榜改解码器。** 已经量过，更差。`HAND_CAP` 保持 12。
5. **不要把 GPU `win=` 当考试。** `rl/gpu/train.py` 默认对手是 scripted（全 IDLE + RESTOCK），
   不是 barnyard。对 starter 微调过的网，考试金钱下降。
6. **提交。** `SUBMISSION_POLICY.md`：半天最多一次；分数在输够约三分之一局之前是地板。
   RL 线还没交过。Transformer 导出依赖 torch，Kaggle 运行时没有这条依赖链，
   要交必须先写纯 numpy 前向（或把权重塞进 `export_multihead` 那套单文件契约）。
7. **集群线**（`rl/TODO.md`）仍在：ghost 张量化、CCA、Decision Transformer。
   与本机这条线独立。不要把 `trl.pt` 和 `ppo_it0080.pt` 互相 `load`。

---

## 6. 踩过的坑

**考试尺子。** 训练 `win=` / GPU 批次胜率 / 势函数 ep_reward 都不算数。只信
`tools/eval.py h2h` 打参考引擎。种子间方差大于大多数调参；3–4 个种子会排出相反顺序。

**非法动作是静默空操作。** 没有报错、没有花费。bug 长得像「策略差」。改解码器前先
`tools/trace.py`，改完必须再考试，不能用「更合法」当证据。

**解码器补丁。** 空目标→调度器、HOLD→RESTOCK、禁番茄、HAND_CAP 14，全部让考试更差。
不要从聊天记录里把它们拣回来。

**加 MLP 轮数。** 官方 300 → herd 80 → phase 300：考试金钱 $27k→$31k，胜场仍 0。
再加一轮数，多半是少输一点，不是开始赢。

**对 starter / scripted 微调。** 张量引擎 3 轮对 starter，考试分差从 −$13k 变成 −$16k。
奖励山在弱敌上，考试在 barnyard 上。

**`ep_opp` 变量名。** 循环里的对手路径字符串盖掉了对方金钱列表，日志里的 omoney
一度是垃圾。现在叫 `ep_omoney`。加日志时不要重用 `ep_*` 短名。

**Wilson CI。** `eval.py` 把已经是百分数的区间再当比例格式化。0 胜会打出
「1071%」和「interval contains 50%」的假 VERDICT。6 胜时甚至会印「A is better」。
只看 `games  6W 26L`。

**空间网加载 MLP。** `W1` 是 75×256，空间网 `fc1` 是 139×256。`allow_partial`
按键名对齐，对不上就跳过，等于随机主干。`--init-weights none` 是故意的。

**Windows 进程池 + torch。** 8 worker 会碎；代码把空间网封顶 4，并 `torch.set_num_threads(1)`。
不要为了「更快」把 worker 加回去。

**`main.py` 最后一个可调用。** Kaggle `get_last_callable` 取模块级最后一个
callable。`def` / `class` / `from x import f` 写在 `agent` 后面会交上去一个
没包住的函数，所有变体分数一模一样且不报错。空间导出文件最后必须是 `agent`。

**导出路径。** `export_spatial` 把仓库绝对路径写进生成文件。换目录或换机器要重导。
`logs/` git-ignored，协作者克隆不到这些 py。

**商店 RNG。** 杂草和商店解锁共用一个 RNG，抽取次数随双方空格变。换策略会换商店。
idle 的 6 胜有一部分是这个。用同一种子座位和 idle 对拍，不要只看胜场数。

**势函数文档过时。** `docs/RL_TRAINING.md` §2 仍写植物 0.5 / 动物 0.4。以
`rl/potential.py` 顶部常量为准。

**不要在登录节点跑重活；不要 GPU 跑参考引擎评估。** 本机这条线是 CPU。集群例外只在
`rl/` 训练作业（`CLAUDE.md`）。

**提交配额。** 一天 5 次，只激活最近 2 个。连交会让每个 agent 只打 4–12 局，无法定位。

---

## 7. 不要动的东西

- `reference/engine/kaggriculture.py` 是引擎真相。竞赛概述页是 1.32.6 之前的数值。
- 生成物：`agents/lib/`、`agents/spar/`、`docs/LEADERBOARD.md`、`site/leaderboard.html`。
- `data/arena.sqlite` 的 `episodes` 行（历史，不可改）。array 作业禁止打开它。
- 策略头 `HAND_CAP=12`（引擎手数量不封顶，但检查点形状锁在 12）。
- 已回退的解码器行为。

项目级待办仍在 [`rl/TODO.md`](../rl/TODO.md) 和 [`docs/TODO.md`](TODO.md)。
剧本线挂起，证据在 [`ROADMAP.md`](ROADMAP.md)（只写到 2026-08-14）。
集群 RL 判词在 [`RUNS.md`](RUNS.md) 末尾 foothold / siege / breach。
本机这条线的考试数字也已追加在 `RUNS.md`「laptop multi-head vs barnyard」。
