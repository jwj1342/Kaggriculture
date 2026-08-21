# 验收证据包 — draught-samp(2026-08-21 晨)

**结论:RL 线首个通过本地验收线(≥5/10 且含至少一条录音)的产物。**
提交决定按约定归用户;本文只汇集证据。

## 产物

- checkpoint:`rl/runs/draught/latest.pt`(280 迭代,4×宽网 1024/512 + 512 critic,~12M 参数)
- 交付形态:**采样导出** `rl/out/draught-samp/`(`export_agent.py --sample 1.0`;
  argmax 模式确认失真:墙 0%、ghost 34-41%——不要用 argmax 交付)
- 配方:granger 系(教师 CE 退火 + 231k 解剖建设曲线势能 + 无瓜锚 +
  对手动作丢弃噪声阶梯 0.40→0)+ 两个 reward 修复(future-mkt / shape-gamma)
  + ks-every 4;容量是最后一块拼图(3M 对照同配方零噪声只到 0.208)。

## 花名册(96 局/对手,参考引擎,采样导出)

| 对手 | 胜率 | margin | 判定 |
|---|---|---|---|
| random | 100.0% | +41,860 | BEATEN |
| starter | 100.0% | +32,989 | BEATEN |
| ghost-89825016(录音) | 75.0% [65.5, 82.6] | +20,150 | **BEATEN** |
| ghost-89830307(录音) | 82.3% [73.5, 88.6] | +24,520 | **BEATEN** |
| **barnyard** | 96 局 55.2% → **坐实局 384 局 56.8% [51.8, 61.6]** | +504 / +157 | **BEATEN(区间整体 >50%)** |
| enhanced/main | 0% | −36,816 | LOST |
| spar grazier / berrybaron | 0% | −25,285 / −27,286 | LOST |
| ledger_lena | 0% | −107,513 | LOST |
| w49 | 0% | −102,656 | LOST |

**= 5/10,含两条录音。** 坐实局:`rl/runs/draught-samp/eval/barnyard-resolve.json`
(384 局 218W-166L,eval 判词 "A is better")。

## 镜像与稳健性

- 镜像局(48 seeds × 双席):margin **+0** [−1,728, +1,729] —— 无席位偏置;
  镜像收入中位 24,353(sd 15,923,采样策略方差大,属预期)。
- 打包链已干跑验证(tar → get_last_callable → 整局,2026-08-20)。
- 已知弱点(如实):k01/k06 档 −136k(20 倍收入差);lena/w49 档 −100k;
  argmax 模式不可用;对市场强压对手的鲁棒性未证。

## 天梯定位的诚实估计

本地锚点:barnyard/enhanced ≈ 天梯 857 档;已胜 barnyard(56.8%)但未胜
enhanced/main(0%)→ **估计 ~800–950 分段(排名 ~1700–2100/4356)**。
真实天梯对手中位收入 68–71k(tools/ladder.py stats,737 局),median 对手
= 3 块地 + 13 只动物 + 小麦/化肥/草莓流——我们 42k 的收入仍低于场地中位,
天梯分主要来自打赢底部集群。**2000 分还需跨过 lena/w49(≈1364 档)那座山。**

## 用户决断点

1. **提交与否**:验收线已过,但按 SUBMISSION_POLICY(每日 5 次、仅最新 2 个
   生效、半天一发),提交它的价值主要是**拿到 RL 线的第一个真实天梯读数**
   (校准本地 → 天梯的映射),分数预期 ~800–950,不是 2000。
2. **不提交、继续攀登**:draught 配方 + 容量还有明显余量(280 迭代仍在爬、
   CNN 干未动、critic 可再放大、混池防 k 档市场压力未加)——gen-4 可从
   draught 续链/分叉直攻 enhanced/main(−36.8k)与 spar(−25k)。
3. 折中:提交拿读数的同时 gen-4 照跑(两者不冲突,只花一个提交名额)。

---

## 追记(2026-08-21 深夜):验收头名易主 —— cropper-samp

夜间四臂判词更新了交付物排序:

| 产物 | barnyard | ghosts | main | 备注 |
|---|---|---|---|---|
| draught-samp(晨间验收版) | 56.8% [51.8,61.6]@384 | 75.0/82.3% | 0% (−36.8k) | 原验收线产物 |
| **cropper-samp(信用臂)** | **69.8% [60.0,78.1]@96,margin +1,875** | **96.9/91.7%** | 0% (−38.7k) | **新头名;区间整体>50%** |
| carter-samp(league/pfsp) | 8.3% | 93.8/94.8% | **10.4% (−10.1k)** | 墙滑落换泛化;首个对 main 非零 |

- cropper = draught 配方 + 作物建设曲线 + 化肥流信用(gen-5 项),
  单变量 +13pp;检查点 `Kaggriculture-gen5 worktree rl/runs/cropper/latest.pt`,
  采样导出 `rl/out/cropper-samp`(worktree 内)。
- 若晨间决定提交,**建议提交 cropper-samp**(打包与镜像检查待做——
  按包装链 SOP:tools/package.sh + get_last_callable 验证 + 整局)。
- 深夜还在跑:wrangler(磁带混池)与 sower-v3(gen-8 全篮:
  PLANT+FERTILIZE+10 人日工+原子物理+信用);两者判词晨间可见,
  可能进一步改写此表。夜间两大机制发现(帮手=日工;原子 PLANT)
  见 docs/RUNS.md 同日条目。

### cropper-samp 证据补全(深夜,job 20223956)

- **镜像公平**:margin **+0** [−1,490, +1,443](48 seeds × 双席),
  席位无偏;镜像中位收入 23,600(采样方差大,与 draught 同性质)。
- **打包链干跑通过**:tar 解包 → get_last_callable 解析 → 完整 720 步
  对局($57,130 收官)。产物:
  `submissions/2026-08-21-cropper-samp/submission.tar.gz`(20.2 MB)。
- 提交命令(**决断归用户**):
  `kaggle competitions submit kaggriculture -f submissions/2026-08-21-cropper-samp/submission.tar.gz -m "..."`

---

## 头名再易主(2026-08-21 拂晓后):sower-it228

| 产物 | barnyard | ghosts | main | spar | 二梯队墙 |
|---|---|---|---|---|---|
| draught-samp | 56.8%@384 | 75/82% | 0% | 0% | cleo −103k / w49 −100k |
| cropper-samp | 69.8% +1,875 | 96.9/91.7% | 0% | 0% | cleo −102.6k / w49 −96.0k |
| **sower-it228** | **92.7% +11,336** | **100/100%** | **19.8%** | **6.2%(首非零)** | **cleo −82.2k / w49 −84.5k** |

- 产物 = gen-8 全篮(PLANT+FERTILIZE 词表 × 10 人日工连发 × 作物/化肥
  信用 × 原子 PLANT 物理)在 draught 树干上的 it-228 **链中**检查点,
  采样导出。行为:42 株/局、帮手浇水 1,205 次、草莓为主作物(顶端第一
  收入线,自主发现)、闲置工时腰斩。
- **镜像 margin +0** [−1,515, +1,521](48 seeds × 双席),席位公平。
- **打包链验证通过**:解包 → get_last_callable → 整局 $60,365。
  tar:`submissions/2026-08-21-sower-it228/submission.tar.gz`(20.3 MB)。
- 提交命令(决断归用户):
  `kaggle competitions submit kaggriculture -f submissions/2026-08-21-sower-it228/submission.tar.gz -m "..."`
- 天梯预期 **~1000–1300**(barnyard 档 92.7% + main 19.8% + 二梯队收窄
  20k;真实天梯中位对手 68–71k 收入,我们已到 52k 批次均值)。
- 注意:链还有 ~170 迭代,链尾检查点大概率更强(花名册 20226407 会自动
  出);若你晨间看到更高的数,用更新的那个。
