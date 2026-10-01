#!/usr/bin/env python3
"""Build the portable final-strategy notebook from frozen artifacts and lessons.

Run from any directory. Only the Python standard library is needed to build.
The notebook itself needs requirements/notebook.txt; it never submits an agent.
"""
import base64
import hashlib
import json
import lzma
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notebooks/postmortem'
NAME = 'kaggriculture-final-strategy-and-lessons'
REPO = 'https://github.com/jwj1342/Kaggriculture'


def main():
    evidence = json.loads((OUT / 'evidence.json').read_text())
    payload = {}
    for item in evidence['final_active']:
        folder = ROOT / item['directory']
        for name, expected in item['files'].items():
            actual = hashlib.sha256((folder / name).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f'Frozen artifact changed: {folder / name}')
        payload[item['name']] = {
            'files': {name: (folder / name).read_bytes().decode('utf-8')
                      for name in ('main.py', 'LICENSE.txt', 'NOTICE.txt', 'REVIEW.md')},
        }
    cells = []

    def md(source):
        cells.append({'cell_type': 'markdown', 'metadata': {},
                      'id': f'cell-{len(cells):02d}',
                      'source': textwrap.dedent(source).strip() + '\n'})

    def code(source, hidden=False):
        cells.append({'cell_type': 'code', 'execution_count': None,
                      'metadata': {'jupyter': {'source_hidden': True}} if hidden else {},
                      'id': f'cell-{len(cells):02d}', 'outputs': [],
                      'source': textwrap.dedent(source).strip() + '\n'})

    md('''
    # 🌾 Kaggriculture — Final Strategy and Lessons
    ### 从实验路线、失败与修正，到最后的两份提交

    **Team: RL is all you need · Archive date: 2026-10-01 · Final result pending**

    **[🌾 GitHub 项目主页与团队致谢](https://github.com/jwj1342/Kaggriculture#readme)** ·
    [仓库中的本 Notebook](https://github.com/jwj1342/Kaggriculture/blob/main/notebooks/postmortem/kaggriculture-final-strategy-and-lessons.ipynb)

    这是提交截止后的研究复盘。最终排名和奖牌尚未公布。我们保留结论的时间背景，
    不用局部胜率、早期天梯分或包检查通过来代替最终比赛结果。

    **English abstract.** We describe our progression from hand-written farm scheduling,
    replay-based policies and reinforcement learning to a public reactive controller with
    bounded local changes. The final pair combines market-order permutation and deferred
    restocking in one agent, with wool-delivery priority in the other. Fresh-world paired
    confirmation supports a local improvement over the mixed-order parent. It does not
    establish a medal result, universal dominance, or superiority over the wool backup.
    We include negative results, production costs, validation limits, and the exact final
    submission source with original licenses and attribution. The original archives are linked from GitHub Release.

    **Run All** 会重画冻结结果、演示计分口径、核验并导出最终源码，并链接原始提交包。
    无需联网、GPU、Kaggle 密钥或游戏引擎。原始大规模锦标赛不会在这里重跑。

    **阅读顺序**：比赛问题 → 最终方案 → 尝试过的路线 → 确认实验 → 反例与工程 → 双槽选择 → 下载与复现。

    [GitHub 仓库](https://github.com/jwj1342/Kaggriculture) ·
    [比赛](https://www.kaggle.com/competitions/kaggriculture) ·
    [官方评分说明](https://www.kaggle.com/competitions/kaggriculture/overview/evaluation)
    ''')
    md('''
    ## 1 · 问题：共享市场中的农场经营

    双方各经营一座农场，一季 720 回合。我们要同时决定雇工、路线、种植、喂养、采集、
    交仓、采购和销售。对手会改变共享市场的库存与价格；我们的动作也会改变对手随后的选择。

    现金只在单局内决定胜负。跨对局计分采用胜负结果，平局各计半分；最终赛事用
    Bradley–Terry 整体拟合，队伍取两个最终 agent **整体评分中的较高者**。
    这要求每份 agent 自己完成整个赛事；没有逐局选择赢家的机会。
    [官方解释](https://www.kaggle.com/competitions/kaggriculture/discussion/739410)。

    提交截止为 **2026-09-30 23:59 UTC**。我们在截止后 00:00:56 UTC 回读官方队伍状态，
    两份最终提交均为 COMPLETE。继续比赛和最终排名由主办方产生。
    [官方时间线](https://www.kaggle.com/competitions/kaggriculture/overview/timeline)。
    ''')
    code('''
    from pathlib import Path
    import base64
    import hashlib
    import io
    import json
    import lzma
    import tarfile
    import zipfile
    import pandas as pd
    import matplotlib.pyplot as plt
    from IPython.display import display, FileLink

    OUT = Path('postmortem_artifacts')
    OUT.mkdir(exist_ok=True)
    ''')
    code('EVIDENCE = json.loads(' + repr(json.dumps(evidence, ensure_ascii=False)) + ')\n'
         + "display(pd.DataFrame([{\n"
         + "    'agent': x['name'], 'submission_id': x['submission_id'],\n"
         + "    'uploaded_utc': x['uploaded_utc'], 'entry_point': x['entry_point']\n"
         + "} for x in EVIDENCE['final_active']]))")
    md('''
    ## 2 · 最终方案：保留继承策略，单独验证新增控制层

    最终生产与路线策略大量继承自社区公开的响应式控制器。我们没有重新训练这些上游路线，
    也不把公开策略的能力归为本地新增层的成果。完整作者与变化说明随下载文件保留。

    | 层 | 作用 | 约束与边界 |
    | :--- | :--- | :--- |
    | 继承的路线、生产与市场策略 | 根据观测执行原有开局、动物/作物、运输与交易计划 | 含既有适配、估值与回退逻辑 |
    | Guarded sales | 在保守条件下重排纯 SELL 队列 | 保留原数量与物理动作；对不可靠投影退出 |
    | Funded mixed | 排列 2–6 条完全融资、完全成交的混合买卖，最多 720 种 | 保留这一层的数量、物理动作和投影终仓 |
    | Deferred restock | 延后符合条件的夜间资源采购，并按后续观察确认的额度恢复 | 外层可以改变资源数量；需核对债务、保护库存和生产后果 |
    | Wool priority | 目标工人携毛时暂时屏蔽可选采肥标记，让交仓优先 | 调用父策略一次；减少采肥可能影响后续施肥 |

    **主要方案**：继承策略 → guarded → funded mixed → deferred。
    顺序固定，没有在看到确认结果后交换层次或重新调参。

    **第二方案**：继承策略 → guarded，并加羊毛交仓优先。
    它不包含 funded mixed / deferred 两层，因此保留不同的市场和资源响应。

    局部不改物理动作，也仍会通过现金、价格和库存改变未来物理行为。
    审查必须覆盖完整对局，不能只检查当前回合是否满足约束。
    ''')
    lessons = ROOT / 'docs/RESEARCH_LESSONS.md'
    if not lessons.exists():
        raise FileNotFoundError('Complete docs/RESEARCH_LESSONS.md before building the notebook')
    history = lessons.read_text().partition('\n')[2]
    # Resolve local repository links for the standalone Kaggle copy.
    def absolute_link(match):
        label, target = match.groups()
        if target.startswith(('http:', 'https:', '#', 'mailto:')):
            return match.group(0)
        resolved = (lessons.parent / target.split('#')[0]).resolve()
        try:
            relative = resolved.relative_to(ROOT).as_posix()
        except ValueError:
            return match.group(0)
        fragment = '#' + target.split('#', 1)[1] if '#' in target else ''
        return f'[{label}]({REPO}/blob/main/{relative}{fragment})'
    history = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', absolute_link, history)
    # Keep the research document's original hierarchy under one notebook chapter.
    history = re.sub(r'^(#{1,4}) ', lambda m: '#' + m.group(1) + ' ', history, flags=re.M)
    md('## 3 · 尝试过的路线与踩过的坑\n\n' + history)
    md('''
    ## 4 · 评测设计：先冻结假设，再看全新世界

    最终确认使用 **kaggle-environments 1.32.7 / Python 3.11**。

    1. 冻结候选源码、对手集合、种子、门槛和诊断选择规则。
    2. 用会响应的策略对打，每个世界交换座位，保留完整胜平负与资金、动作摘要。
    3. 组合使用全新世界 `3000000..3001023`，羊毛使用 `2300000..2301023`。
    4. 分别运行 `PYTHONHASHSEED=0` 与 `4`；各自判断通过，不合并为双倍独立样本。
    5. bootstrap 以世界为单位聚类，保留同一世界里的座位和对手相关性。
    6. 独立审查从原始分片重算日程、缺失项、配对结果、区间和门槛。

    组合确认共 **419,840 局**，1,024 个独立世界，两个 hash 块各 209,920 局；
    每块有 51 项预先固定的数值门。羊毛确认共 **77,824 局**，两个 hash 块各 38,912 局，
    同样只有 1,024 个独立世界。游戏数反映计算工作量，不能当作统计独立样本数。

    七组现代对手先在簇内平均，再按簇等权汇总；它们是实现簇，不是七个互不相关的策略家族。
    相同种子也不能完全固定外部环境：
    农田状态会影响共享随机数的消耗，后续杂草和商店因而可能变化。

    **下面的区间来自冻结审查。这个 Notebook 重现表格与图形，不从汇总数据重新估计区间。**
    ''')
    code('''
    effects = pd.DataFrame(EVIDENCE['effects'])
    display(effects)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'svg.fonttype': 'none', 'svg.hashsalt': 'kaggriculture-postmortem'})
    fig, axes = plt.subplots(2, 1, figsize=(11.8, 4.6),
                             gridspec_kw={'height_ratios': [3, 1.2]}, layout='constrained')
    for ax, rows, color, title in [
        (axes[0], effects.iloc[:3], '#2D6A4F', 'Combination confirmation | seven implementation clusters | 97.5% CI'),
        (axes[1], effects.iloc[3:], '#B57728', 'Wool confirmation | three other modern opponents | 95% CI')]:
        for y, (_, row) in enumerate(rows.iterrows()):
            ax.errorbar(row.mean_pp, y,
                        xerr=[[row.mean_pp-row.low_pp], [row.high_pp-row.mean_pp]],
                        fmt='o', color=color, capsize=5, markersize=7, linewidth=2)
            ax.text(1.02, y, f'{row.mean_pp:+.3f} [{row.low_pp:+.3f}, {row.high_pp:+.3f}]',
                    transform=ax.get_yaxis_transform(), va='center', ha='left', fontsize=9)
        ax.set_yticks(range(len(rows)), rows.comparison)
        ax.invert_yaxis()
        ax.axvline(0, color='#9AA0A6', linewidth=1, linestyle='--')
        ax.set_xlim(-0.3, 4.2)
        ax.set_title(title, loc='left', fontsize=11, pad=12)
        ax.grid(axis='x', alpha=0.15)
        ax.spines[['top', 'right']].set_visible(False)
    axes[1].set_xlabel('Paired score change (percentage points)')
    fig.suptitle('Local gains, with their uncertainty', fontsize=17, fontweight='bold')
    fig.savefig(OUT / 'confirmation-effects.svg', metadata={'Date': None})
    fig.savefig(OUT / 'confirmation-effects.png', dpi=160)
    effects.to_csv(OUT / 'confirmation-effects.csv', index=False)
    display(fig)
    plt.close(fig)
    ''')
    md('''
    **解读**：组合相对 mixed 的七组均值提高 2.65067 pp，区间下界为正；
    相对 wool 的区间跨过 0，不能声称显著优于 wool。
    羊毛实验的对手组与区间水平不同，不能把两行增益当作同一把尺子。

    大量近亲对局是平局。下面区分原始胜率与平局计半分的得分率，避免把 62.06% 写成胜率。
    ''')
    code('''
    direct = pd.DataFrame(EVIDENCE['direct_matches'])
    direct['games'] = direct[['wins', 'ties', 'losses']].sum(axis=1)
    direct['win_rate_percent'] = 100 * direct.wins / direct.games
    direct['score_rate_percent'] = 100 * (direct.wins + 0.5 * direct.ties) / direct.games
    assert direct.games.eq(2048).all()
    display(direct.round(5))
    direct.to_csv(OUT / 'direct-match-score-rates.csv', index=False)
    ''')
    md('''
    ## 5 · 负例、真实代价与工程检查

    ### 组合方案

    资源观察覆盖 **20,224 个不同完整对局 / 20,480 个视图 / 10,240 个配对格**。
    3,670 个延期夜晚的 24,692 单位资源债全部恢复；样本中没有残债、过期或保护库存不足。
    另对正式确认中的 126 个尾部配对、252 个完整对局追查现金与资源。

    但探索中 **565 个配对格某种产量下降**，羊毛净少 1,082、小麦净少 181，
    51 对有某夜溢出增加。新增未喂动物夜晚 1,325、减少 660；新增事件均追到继承的
    `_r85_feed` 在携麦时因估值返回 PASS。这些经济选择仍然有真实生产代价。
    正式确认中最差己方现金变化 **−1,241**，最差双方差额变化 **−935**。

    ### 羊毛方案

    9,216 个完整资源观察局中，18 个配对新增供肥失败，来自 7 个世界。
    肥料收集净少 4,017，羊毛收获净少 408，羊毛销售收入净增 305,693。
    这些是整批对局的合计，不能读作每局收益，更不能当作单一机制的因果分解。
    缺麦 FEED 无效动作和动物逃逸没有增加，但主动不喂的动物夜次数净增 196。
    所有 20 个近亲确认回归格均保留并复演，未从统计中剔除。

    ### 真正上传的包也要检查

    两份 tar 都通过 28 个压力配置，根目录只含 `main.py`、`LICENSE.txt`、`NOTICE.txt`。
    检查官方 loader 最后绑定的 callable，分别运行 schema 开关配对，并补充会实际触发新增层的场景。
    仅仅运行一局没有触发 helper 的游戏，不能证明 helper 安全。

    组合的 1,222 个选定慢局、羊毛的 214 个慢局都用原 hash、单 CPU 完整复验。
    候选隔离峰值分别为 0.416425 / 0.300854 秒。原并行运行中，组合候选峰值为 14.689405 秒，
    组合确认全场最大值 17.5766 秒属于对手 shop0913；羊毛候选峰值为 7.657571 秒。
    原始慢峰仍留在证据里。
    这解释了观察到的慢峰，不保证其他硬件的普遍时间上界。

    继承代码仍有 S839 回退；新层无错误不能写成整个控制器从无内部错误。
    两个 hash 块的组合得分相同，但有 350 / 209,920 对局的完整动作/现金/状态指纹不同；
    它们也没有因得分相同而被隐去。

    **反方审查的作用**：要求追查尾部、重算结果、确认真实包身份和机制，而不只是阅读均值。
    最终批准接受这些有证据的经济取舍，不等于证明全局无损。
    ''')
    md('''
    ## 6 · 为什么最后是 combo + wool

    最后一天按顺序提交 guarded sales、funded mixed、mixed deferred、wool priority，共用 **4 / 5 次**。
    最终两个活跃提交是 `56720412` 与 `56721680`。

    我们先保留 combo + mixed，随后针对“两个整体 BT 取较高值”的官方规则重新审查第二槽。
    frozen panel 上 mixed 比 combo 得分更好的配对格为 0；wool 有 **284 格 / 61 个世界**。
    wool 相对 combo 在 cha22 上的均值为 +2.05078 pp，名义 97.5% 区间为 [0.34180, 3.80920] pp。

    **这是事后描述性证据**，不是经过多重比较调整的新优效结论。
    wool 的七组现代均值仍低约 0.7394 pp，在部分近亲与 Harvest 上也更差。
    最终场地权重未知，那种差异可能没有实际价值；替换 mixed 也会失去它在未测场景下的保障。

    更换第二槽是一项不确定性下的选择。不能把 284 格相加为额外胜场，
    也不能把两个 agent 在每个对手上的最好表现拼成一个实际不存在的策略。
    我们保留已完成线上健康检查的 combo，并上传原封不动、此前已通过审查的 wool 包。

    第四次上传后只剩一次额度，无法靠再发两份彻底挤掉最新故障版本。
    上传后的验证局、首两场公开局和首败均完成记录复验；检查正常只说明这些已查对局正常。
    ''')
    md('''
    ## 7 · 下载原始最终包与复核摘要

    Kaggle 对源文件有 1 MB 上限，因此下方折叠单元嵌入经过联合压缩的两份源码与原独立审查。
    解码后逐个核对 SHA-256 并导出；不会运行 agent。
    原审查记录中的“待提交”或旧槽位建议属于当时状态，实际最终身份以上方提交表为准。

    运行得到的 `kaggriculture-final-source.zip` 包含两份源码、许可证、NOTICE、REVIEW 与 `evidence.json`。
    源文件与比赛上传文件保持一致。两份原始 tar 位于
    [Release 的最终包合集](https://github.com/jwj1342/Kaggriculture/releases/download/postmortem-2026-10-01/kaggriculture-final-artifacts.zip)，
    原始归档哈希也保留在摘要中。这里不包含全部原始锦标赛分片。
    ''')
    encoded = base64.b64encode(lzma.compress(json.dumps(payload, ensure_ascii=False).encode('utf-8'))).decode('ascii')
    code('PAYLOAD = json.loads(lzma.decompress(base64.b64decode(' + repr(encoded) + ')))', hidden=True)
    code('''
    checks = []
    for item in EVIDENCE['final_active']:
        name = item['name']
        folder = OUT / name
        folder.mkdir(exist_ok=True)
        source_files = PAYLOAD[name]['files']
        assert set(source_files) == {'main.py', 'LICENSE.txt', 'NOTICE.txt', 'REVIEW.md'}
        for filename, text in source_files.items():
            contents = text.encode('utf-8')
            assert hashlib.sha256(contents).hexdigest() == item['files'][filename]
            (folder / filename).write_bytes(contents)
        (folder / 'SHA256SUMS').write_text(''.join(
            f'{item["files"][filename]}  {filename}\\n' for filename in source_files))
        checks.append({'agent': name, 'submission_id': item['submission_id'],
                       'original_archive_sha256_reference': item['files']['submission.tar.gz'],
                       'all_source_files_verified': True})
    (OUT / 'evidence.json').write_text(json.dumps(EVIDENCE, ensure_ascii=False, indent=2) + '\\n')
    (OUT / 'artifact-checks.json').write_text(json.dumps(checks, indent=2) + '\\n')
    archive_path = Path('kaggriculture-final-source.zip')
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        paths = [OUT / name for name in ('evidence.json', 'artifact-checks.json',
                 'confirmation-effects.csv', 'confirmation-effects.svg',
                 'confirmation-effects.png', 'direct-match-score-rates.csv')]
        paths += [OUT / item['name'] / name for item in EVIDENCE['final_active']
                  for name in ('main.py', 'LICENSE.txt', 'NOTICE.txt', 'REVIEW.md', 'SHA256SUMS')]
        for path in paths:
            archive.write(path, path.as_posix())
    display(pd.DataFrame(checks))
    display(FileLink(str(archive_path)))
    for item in EVIDENCE['final_active']:
        display(FileLink(str(OUT / item['name'] / 'main.py')))
    ''')
    md('''
    ## 8 · 复现边界与后续研究

    | 层次 | 这里能复现什么 | 额外需要什么 |
    | :--- | :--- | :--- |
    | 本 Notebook | 表格、冻结 CI 图、胜平负计分、最终包身份与下载 | 常规 CPU Python 环境 |
    | 单局策略行为 | 冻结源码在指定引擎上的完整对局 | kaggle-environments 1.32.7、Python 3.11、指定种子/对手/hash |
    | 原正式确认 | 全日程、逐世界统计、置信区间与审查门 | 原 manifest、全部对手、原始分片、统计脚本与足够 CPU |
    | 最终赛事 | 主办方的最终评分 | 平台继续比赛及发布结果 |

    仓库 `tools/` 提供生成、评测、追踪和数据库工具；`slurm/` 提供作业入口；
    `submissions/` 保存按日期冻结的策略；`docs/` 保存协议、执行记录与历史修正。
    详细机制与实验见 [最终方案文档](https://github.com/jwj1342/Kaggriculture/blob/main/docs/FINAL_SOLUTION.md)，
    安装、复现步骤和工具导航见 [复现与使用](https://github.com/jwj1342/Kaggriculture/blob/main/docs/REPRODUCING.md)。
    大型数据库及历史 D1 快照的归档与恢复见 [数据归档](https://github.com/jwj1342/Kaggriculture/blob/main/docs/ARCHIVE.md)。

    若继续研究，最有价值的工作是：扩大独立策略家族的对手覆盖；把供肥、喂养、运输和仓容
    联合起来优化；在早期先校准本地指标与线上读数；保留未来数据做最终确认。
    这些是后续假设，目前没有新的实验结果支持它们。

    ### 来源与致谢

    感谢合作者 [@RicardoJLv](https://github.com/RicardoJLv)、
    [@liaodid](https://github.com/liaodid)、[@BPMF57](https://github.com/BPMF57)
    和 [@KaltistEsperanta](https://github.com/KaltistEsperanta)。感谢大家在 RL 路线、
    其他策略探索、代码与实验、讨论和反馈中的投入，也感谢所有在比赛过程中参与和支持我们的朋友。

    最终控制器继承了 Thomas Tschinkel、Yusuke Hayashi、aurax7、Ahmed Berat Ozer、
    shiiin9、Dmitrii Gluzdov 等社区作者的公开代码与路线。
    两份包的 Apache-2.0 文本、源码注释和 NOTICE 完整保留；NOTICE 也保留上游路线数据的溯源限制。
    我们的本地工作是新增控制层、实验与审查，没有补造上游路线的训练或采集经历。

    - [直接父控制器来源](https://www.kaggle.com/code/shiiin9/your-market-list-is-an-order-book)
    - [V56 输入预算](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v56-smarter-seeds-and-fertilizer)
    - [公共 State Router](https://www.kaggle.com/code/thomastschinkel/kaggriculture-93-8-win-rate-public-state-router)
    - [官方引擎](https://github.com/Kaggle/kaggle-environments)
    - [仓库与完整复盘](https://github.com/jwj1342/Kaggriculture)

    **Final result pending.** 提交完成、运行检查通过、本地实验改善，分别回答不同的问题。
    最终名次与奖牌留待官方结果。
    ''')
    notebook = {'cells': cells, 'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': '3.11'},
    }, 'nbformat': 4, 'nbformat_minor': 5}
    target = OUT / f'{NAME}.ipynb'
    target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n')
    metadata = {'id': f'jwj1342/{NAME}', 'title': 'Kaggriculture Final Strategy and Lessons',
                'code_file': target.name, 'language': 'python', 'kernel_type': 'notebook',
                'is_private': False, 'enable_gpu': False, 'enable_tpu': False,
                'enable_internet': False, 'dataset_sources': [], 'competition_sources': [],
                'kernel_sources': []}
    (OUT / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Built {target.relative_to(ROOT)}: {len(cells)} cells, {target.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
