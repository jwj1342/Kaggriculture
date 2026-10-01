<div align="center">

# 🌾 Kaggriculture

**Kaggle 农场经营与策略博弈比赛 · 团队研究、最终方案与赛后复盘**

Strategies, experiments, and lessons from team **RL is all you need**.

[![比赛主页](https://img.shields.io/badge/Kaggle-Competition-20BEFF?style=flat-square&logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/kaggriculture)
[![赛后 Notebook](https://img.shields.io/badge/Notebook-Postmortem-2D6A4F?style=flat-square&logo=jupyter&logoColor=white)](https://www.kaggle.com/code/jwj1342/kaggriculture-final-strategy-and-lessons)
[![比赛讨论帖](https://img.shields.io/badge/Kaggle-Discussion-6B5B95?style=flat-square&logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/kaggriculture/discussion/744999)
<br>
[![笔记本源码](https://img.shields.io/badge/Notebook-Source-555555?style=flat-square&logo=jupyter&logoColor=white)](notebooks/postmortem/kaggriculture-final-strategy-and-lessons.ipynb)
[![项目档案](https://img.shields.io/badge/Docs-Index-40513B?style=flat-square&logo=readthedocs&logoColor=white)](docs/INDEX.md)
[![归档下载](https://img.shields.io/badge/Archive-Release-946B2D?style=flat-square&logo=github&logoColor=white)](https://github.com/jwj1342/Kaggriculture/releases/tag/postmortem-2026-10-01)

</div>

---

## 🧭 关于项目

**[Kaggriculture](https://www.kaggle.com/competitions/kaggriculture)** 是 Kaggle 上的一场双人农场经营模拟赛。参赛者编写智能体，安排种植、养殖、雇工和运输，在共享市场中与对手交易竞争，争取在赛季结束时获得更多现金。

本仓库是团队 **RL is all you need** 的参赛研究与赛后归档。我们一起尝试了手工策略、强化学习、公开策略研究和多轮实验，留下最终双方案、实验结论和完整复盘，也保留一路上的转向、失败与修正。

> **截至 2026-10-01：提交阶段已结束，两份最终方案均已完成提交，最终排名与奖牌待官方公布。**

## 🔬 研究路线

| 路线 | 留下的经验 |
| :--- | :--- |
| 手工策略与农场调度 | 从游戏规则出发，逐步理解生产、资源和市场之间的关系。 |
| 强化学习探索 | 围绕学习型策略反复尝试，也认识到训练目标与实际比赛表现之间的距离。 |
| 公开策略与对手研究 | 向社区学习，在真实竞争中重新检验我们的判断。 |
| 截止前的收敛 | 缩小改动范围，反复验证，最终保留两份各有侧重的方案。 |

## 🏁 最终方案

- **Mixed deferred**：围绕交易安排与补货时机改进，作为主要方案。
- **Wool priority**：优先把羊毛送回仓库，保留另一种策略选择。

两份方案建立在社区公开策略之上。完整思路、实验依据、尝试过的路线和踩过的坑，都收录在上方的 **赛后 Notebook** 中。

## 📝 复盘与收获

- **更可靠的判断方式。** 多看不同对手与不同场景，允许新的证据修正之前的结论。
- **值得保留的失败。** 没有进入最终提交的路线，同样帮助我们理解问题、减少重复尝试。
- **共同完成的研究记录。** 从早期探索到最后提交，再到代码、笔记与实验资料的整理，都成为下一次出发的积累。

---

## 🤝 致谢

感谢我的合作者们，一起参与这段比赛旅程：

**[@RicardoJLv](https://github.com/RicardoJLv)** · **[@liaodid](https://github.com/liaodid)** · **[@BPMF57](https://github.com/BPMF57)** · **[@KaltistEsperanta](https://github.com/KaltistEsperanta)**

感谢大家在 **RL 路线、其他策略探索、代码与实验、讨论和反馈** 中的投入。每条尝试过的路、每一次提出问题和共同排查，都帮助我们推进了这个项目。也感谢所有在比赛过程中参与、交流和支持我们的朋友。

感谢 Kaggriculture 社区分享代码、思路与经验的作者，尤其是 **Thomas Tschinkel、Yusuke Hayashi、aurax7、Ahmed Berat Ozer、shiiin9 和 Dmitrii Gluzdov**，以及 Kaggle 的组织者与所有参赛者。完整来源与许可说明保留在[最终方案文档](docs/FINAL_SOLUTION.md#致谢与来源)及各提交包中。
