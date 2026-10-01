# Our Kaggriculture Journey: RL Experiments, Final Agents & Lessons Learned

Hi everyone! We are **RL is all you need**, and we have published a write-up of our Kaggriculture experiments, final agents, and the mistakes that changed our approach. **As of October 1, final rankings and medals are still pending.**

- **[Postmortem Notebook](https://www.kaggle.com/code/jwj1342/kaggriculture-final-strategy-and-lessons)** — the research story, frozen experiment charts, and verified final source files.
- **[Public GitHub repository](https://github.com/jwj1342/Kaggriculture)** — code, research notes, experiment records, and acknowledgments.
- **[Archive and final submission packages](https://github.com/jwj1342/Kaggriculture/releases/tag/postmortem-2026-10-01)** — downloadable artifacts and data snapshots.

The Notebook is mainly in Chinese, with an English abstract. Here is an English overview of what we learned.

## What we tried

We explored hand-written farm scheduling, policies built around recorded action sequences, reactive market adaptations, and reinforcement learning. The RL work included PPO, behavior cloning, curricula, self-play, and market residual policies. We also made actual RL and hybrid submissions during development.

Our tested RL setups did not reach the strength we wanted against strong opponents. That result led us to change direction before the deadline; it does not establish a limit on what RL could achieve in this game. We have kept the failed experiments and later corrections alongside the successful changes.

## Our final two agents

Both final agents build on community public reactive controllers:

- **Mixed deferred:** guarded sales ordering, funded mixed-order reordering, and selective deferred restocking.
- **Wool priority:** a separate branch that prioritizes wool delivery over some optional manure collection.

Our contribution was the additional control logic, experiments, diagnostics, and final selection. The inherited production and route policies remain credited to their original authors.

Fresh-world confirmation supported a local improvement of the combination over its mixed-order parent. It did not establish a significant advantage over the wool agent on the seven-cluster comparison, or predict a medal. We also recorded regressions and resource costs instead of reporting only the average gain.

## Five lessons we would take into another simulation competition

1. **Calibrate the evaluation before scaling the experiments.** Beating opponents we wrote ourselves did not reliably predict performance against the wider field. More episodes did not fix a poorly chosen comparison.
2. **Check replay alignment against the original game.** An off-by-one action replay could still make money, so a plausible final cash total was a weak correctness check.
3. **Match the training objective to the actual score.** Rewarding inventory that would not become terminal cash created incentives different from winning the game.
4. **Verify the exact exported agent.** Module caches, entry-point selection, and engine-version drift could make an experiment evaluate a different policy or economy from the one intended.
5. **Count independent worlds carefully, and validate combinations separately.** Seats, opponents, and hash settings share dependencies. Two individually useful changes can also interact through prices, production, and storage.

The Notebook preserves the evidence and limits behind these points. Running it reproduces the frozen charts and verifies and exports the final source files. Re-running the full tournaments requires the original inputs and a matching engine; the Notebook alone does not repeat that computation.

## Thanks

Thank you to our collaborators **[RicardoJLv](https://github.com/RicardoJLv), [liaodid](https://github.com/liaodid), [BPMF57](https://github.com/BPMF57), and [KaltistEsperanta](https://github.com/KaltistEsperanta)** for the work across RL, other strategy approaches, experiments, discussions, and feedback. We also appreciate everyone who participated and supported the project.

Thank you to **Thomas Tschinkel, Yusuke Hayashi, aurax7, Ahmed Berat Ozer, shiiin9, and Dmitrii Gluzdov**, and to the broader Kaggriculture community for sharing code and ideas. The original licenses and attribution remain with the final packages; [source acknowledgments](https://github.com/jwj1342/Kaggriculture/blob/main/docs/FINAL_SOLUTION.md#致谢与来源) provide more detail.

We would be interested to hear how others handled long-term credit assignment and chose opponents for local evaluation. What helped your local results transfer to the competition?
