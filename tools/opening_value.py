"""开局值多少：把 n04 的前 cut 步换成别人的，后段保持 n04 不变。

档案里的副产品（判词续三十四）说「meta line 的价值高度集中在开局」——
`n07` 单独打 `n09` 是 −5,067，而 `n04@25 + n07` 是 +21,146，
所以 `n04` 的开局 25 步比 `n07` 的开局值约 +26,000。那是一个对单一对手、
单一方向的读数。本脚本把它做成双向的、分层的、配对的测量：

    变体 = X[:cut] + n04[cut:]      对照 = 纯 n04

如果价值真的集中在开局，换掉开局应该显著变差，而且差值随 cut 增大而增大。

已知阳性（必须过，否则整次测量作废）：n04[:cut] + n04[cut:] 解码后的动作表必须与
n04 逐回合相同，且整局逐回合发出的动作相同。**不是字节相同** —— 重编码时 zlib 的
压缩结果与引号字符都会变（实测文件长 881 字节），所以字节判据不可能通过；
归档的 splice.py 写的是「逐位复现」，那个判据是错的。

纪律（docs/VALIDATING.md）：
  * 配对 —— 同 seed、同对手、双席位，差之中位数而不是中位数之差
  * 分层 —— 对手按同槽位争夺率分低/中/高三档报告，不给混合数
  * 唯一统计量 —— 配对 Δmargin 中位 + seed 簇 bootstrap 95% CI
"""
import base64
import importlib.util
import json
import os
import random
import re
import statistics as st
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOB = re.compile(r"(_TRACE\s*=\s*json\.loads\(\s*zlib\.decompress\(\s*base64\.b85decode\(\s*)"
                  r"((?:['\"](?:[^'\"\\]|\\.)*['\"]\s*)+)")


def load_trace(path):
    """带子的 720 回合动作表。tape_t.load_trace 的自足版本（该模块已归档）。"""
    name = "tape_src_" + os.path.basename(path).replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._TRACE


def write_spliced(head_path, tail_path, cut, out):
    """head 的前 cut 步 + tail 的后段，重编码成一条新带子。

    载体用 tail 的源文件，所以除了 _TRACE 之外的一切（市场层、终局控制器）
    都跟着 tail 走 —— 这正是「只换开局」的意思。
    """
    H, T = load_trace(head_path), load_trace(tail_path)
    merged = [dict(e) for e in H[:cut]] + [dict(e) for e in T[cut:]]
    src = open(tail_path).read()
    m = BLOB.search(src)
    if not m:
        raise SystemExit(f"{tail_path} 里找不到 _TRACE blob")
    blob = base64.b85encode(zlib.compress(
        json.dumps(merged, separators=(",", ":")).encode(), 9)).decode()
    lit = "\n    ".join('"%s"' % blob[i:i + 76] for i in range(0, len(blob), 76))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(src[:m.start(2)] + lit + src[m.end(2):])
    return out


def _one(job):
    """一局。seat=0 表示我方坐 0 号位。返回 (margin, 我方钱)。"""
    agent, opp, seed, seat = job
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    pair = [agent, opp] if seat == 0 else [opp, agent]
    env.run(pair)
    f = env.state[0].observation.farms
    me, them = f[seat]["money"], f[1 - seat]["money"]
    return me - them, me


def boot_ci(pairs, n=4000, seed=7):
    """seed 簇 bootstrap：按 seed 重采样，而不是按单局。"""
    if not pairs:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    by = {}
    for s, d in pairs:
        by.setdefault(s, []).append(d)
    keys = list(by)
    meds = []
    for _ in range(n):
        samp = [d for k in (rng.choice(keys) for _ in keys) for d in by[k]]
        meds.append(st.median(samp))
    meds.sort()
    return meds[int(0.025 * n)], meds[int(0.975 * n)]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", default=f"{ROOT}/agents/newlines/n04.py")
    ap.add_argument("--cuts", default="25,50,100")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=32)
    ap.add_argument("--out", default=f"{ROOT}/logs/opening_value.json")
    a = ap.parse_args()

    cuts = [int(x) for x in a.cuts.split(",")]
    seeds = [1000 + 7 * i for i in range(a.seeds)]
    donors = sorted(f"{ROOT}/agents/newlines/{n}" for n in
                    os.listdir(f"{ROOT}/agents/newlines") if re.fullmatch(r"n\d+\.py", n))
    # 分层对手池：同槽位争夺率 低 / 中 / 高（docs/VALIDATING.md 0.5）
    opps = [("低 ~3%", f"{ROOT}/agents/champ/k01.py"),
            ("中 ~15%", f"{ROOT}/agents/newlines/n02.py"),
            ("高 ~35%", f"{ROOT}/agents/newlines/n06.py")]
    work = f"{ROOT}/agents/_opening"
    os.makedirs(work, exist_ok=True)

    # --- 已知阳性：同带子拼接必须语义复现（不是字节，见模块 docstring）---
    probe = write_spliced(a.tail, a.tail, cuts[0], f"{work}/_selfcheck.py")
    if load_trace(probe) != load_trace(a.tail):
        raise SystemExit("已知阳性失败：X[:cut]+X[cut:] 的动作表与 X 不同，测量作废")
    # 两者分别对同一个固定对手、同一个 seed 各跑一局,再逐回合比动作流。
    # 不能把两者放进同一局对打 —— 它们会坐不同席位、面对不同局面,而 n04 自带的
    # 自适应市场层按棋盘状态反应,分歧会来自席位不对称而不是拼接(实测 4 个回合)。
    from kaggle_environments import make as _make

    def _stream(agent_path):
        e = _make("kaggriculture", configuration={"seed": 424242}, debug=False)
        e.run([agent_path, f"{ROOT}/agents/newlines/n09.py"])
        return [json.dumps(st_[0].get("action"), sort_keys=True) for st_ in e.steps]

    _sa, _sb = _stream(probe), _stream(a.tail)
    _diff = sum(1 for x, y in zip(_sa, _sb) if x != y) + abs(len(_sa) - len(_sb))
    if _diff:
        raise SystemExit(f"已知阳性失败：自拼接体与原带子对同一对手在 {_diff} 个回合"
                         f"动作不同，测量作废")
    print(f"已知阳性 ok：{os.path.basename(a.tail)}@{cuts[0]} 自拼接的动作表逐回合相同，"
          f"且对同一对手整局动作流完全一致（{len(_sa)} 回合）\n")

    variants = [("(纯 n04 基线)", 0, a.tail)]
    for d in donors:
        if os.path.abspath(d) == os.path.abspath(a.tail):
            continue
        for c in cuts:
            tag = os.path.basename(d)[:-3]
            variants.append((tag, c, write_spliced(
                d, a.tail, c, f"{work}/{tag}_at{c}.py")))
    print(f"{len(variants)} 个变体 × {len(opps)} 对手 × {len(seeds)} seeds × 2 席位 "
          f"= {len(variants)*len(opps)*len(seeds)*2} 局")

    jobs, index = [], []
    for name, cut, path in variants:
        for olab, opath in opps:
            for s in seeds:
                for seat in (0, 1):
                    jobs.append((path, opath, s, seat))
                    index.append((name, cut, olab, s))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(_one, jobs, chunksize=4))

    cell = {}
    for (name, cut, olab, s), (margin, me) in zip(index, res):
        cell.setdefault((name, cut, olab, s), []).append((margin, me))
    base = {k[2:]: v for k, v in cell.items() if k[0] == "(纯 n04 基线)"}

    print(f"\n{'开局来源':<10}{'cut':>5}  {'低 ~3%':>22}{'中 ~15%':>22}{'高 ~35%':>22}")
    print("-" * 82)
    rows = {}
    for name, cut, path in variants:
        if name == "(纯 n04 基线)":
            continue
        line = f"{name:<10}{cut:>5}  "
        for olab, _ in opps:
            pairs = []
            for s in seeds:
                v = cell.get((name, cut, olab, s), [])
                b = base.get((olab, s), [])
                for (vm, _), (bm, _) in zip(sorted(v), sorted(b)):
                    pairs.append((s, vm - bm))
            if not pairs:
                line += f"{'—':>22}"
                continue
            med = st.median(d for _, d in pairs)
            lo, hi = boot_ci(pairs)
            rows[(name, cut, olab)] = (med, lo, hi, len(pairs))
            line += f"{f'{med:+,.0f} [{lo:+,.0f},{hi:+,.0f}]':>22}"
        print(line)
    json.dump({f"{k[0]}@{k[1]}|{k[2]}": v for k, v in rows.items()},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"\n写入 {a.out}")
    print("\n读法：负值 = 换掉 n04 的开局之后更差 = n04 的开局有价值。")
    print("      若 |值| 随 cut 增大而增大，说明价值确实集中在越来越长的开局里。")


if __name__ == "__main__":
    main()
