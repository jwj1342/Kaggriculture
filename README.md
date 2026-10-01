<div align="center">

# 🌾 Kaggriculture

**从农场经营到策略博弈，记录我们一起走过的比赛旅程。**

[![Competition](https://img.shields.io/badge/Kaggle-Kaggriculture-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/kaggriculture)
[![Notebook](https://img.shields.io/badge/赛后复盘-Notebook-2D6A4F)](https://www.kaggle.com/code/jwj1342/kaggriculture-final-strategy-and-lessons)

**[📓 阅读赛后 Notebook](https://www.kaggle.com/code/jwj1342/kaggriculture-final-strategy-and-lessons)** · [比赛讨论帖](https://www.kaggle.com/competitions/kaggriculture/discussion/744999) · [仓库中的 .ipynb](notebooks/postmortem/kaggriculture-final-strategy-and-lessons.ipynb) · [项目档案](docs/INDEX.md)

</div>

---

## 关于项目

Kaggriculture 是一场双人农场经营模拟赛：双方安排生产、养殖和运输，在共享市场中交易，争取在赛季结束时赚到更多现金。

我们以 **RL is all you need** 的队名参赛，一起尝试了手工策略、强化学习、公开策略研究和多轮实验。这个仓库记录最终方案，也保留一路上的转向、失败与修正。

> **截至 2026-10-01：提交阶段已结束，两份最终方案均已完成提交，最终排名与奖牌待官方公布。**

## 我们走过的路

| 路线 | 留下的经验 |
| :--- | :--- |
| 手工策略与农场调度 | 从游戏规则出发，逐步理解生产、资源和市场之间的关系。 |
| 强化学习探索 | 围绕学习型策略反复尝试，也认识到训练目标与实际比赛表现之间的距离。 |
| 公开策略与对手研究 | 向社区学习，在真实竞争中重新检验我们的判断。 |
| 截止前的收敛 | 缩小改动范围，反复验证，最终保留两份各有侧重的方案。 |

## 最终方案

- **Mixed deferred**：围绕交易安排与补货时机改进，作为主要方案。
- **Wool priority**：优先把羊毛送回仓库，保留另一种策略选择。

两份方案建立在社区公开策略之上。完整思路、实验依据、尝试过的路线和踩过的坑，都收录在上方的 **赛后 Notebook** 中。

## 这次比赛留下了什么

- **更可靠的判断方式。** 多看不同对手与不同场景，允许新的证据修正之前的结论。
- **值得保留的失败。** 没有进入最终提交的路线，同样帮助我们理解问题、减少重复尝试。
- **共同完成的研究记录。** 从早期探索到最后提交，再到代码、笔记与实验资料的整理，都成为下一次出发的积累。

---

## 致谢

感谢我的合作者们，一起参与这段比赛旅程：

**[@RicardoJLv](https://github.com/RicardoJLv)** · **[@liaodid](https://github.com/liaodid)** · **[@BPMF57](https://github.com/BPMF57)** · **[@KaltistEsperanta](https://github.com/KaltistEsperanta)**

感谢大家在 **RL 路线、其他策略探索、代码与实验、讨论和反馈** 中的投入。每条尝试过的路、每一次提出问题和共同排查，都帮助我们推进了这个项目。也感谢所有在比赛过程中参与、交流和支持我们的朋友。

感谢 Kaggriculture 社区分享代码、思路与经验的作者，尤其是 **Thomas Tschinkel、Yusuke Hayashi、aurax7、Ahmed Berat Ozer、shiiin9 和 Dmitrii Gluzdov**，以及 Kaggle 的组织者与所有参赛者。完整来源与许可说明保留在[最终方案文档](docs/FINAL_SOLUTION.md#致谢与来源)及各提交包中。
