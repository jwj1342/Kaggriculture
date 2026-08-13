#!/usr/bin/env python
"""Regenerate the three opponent tables in README.md.

They go stale: fields get rebuilt, plans get re-mined, submissions accumulate.
This prints them in the README's own markdown so the fix is a paste, not an
edit -- which is the difference between a table that stays true and one that
quietly becomes fiction.

    python tools/fieldtable.py
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHAT = [
    ("agents/wrapped/", "**真正的对手** —— 从天梯挖出的剧本，全部套同一层适配层",
     "`tools/wrap.py --top 100`"),
    ("agents/darkhorse/", "未进 `wrapped` 的 247 条里另选的 40 条，"
     "18 条越过旧场地第十名", "`tools/wrap.py`"),
    ("agents/champ/", "天梯 **#1** 那支队伍的全部录音，同一层适配层",
     "`wrap.py --team`"),
    ("agents/lines/", "每条不同剧本的一个代表，**裸录音**（无适配层，会塌）",
     "`tracelib emit`"),
    ("agents/bench3/", "引擎级场地：我们自己的形状 + 参考 agent",
     "`registry.py gen --plan bench`"),
    ("agents/ref/", "第三方教学梯队 tier 0–9（MIT，见其 NOTICE）", "Kaggle 数据集"),
    ("agents/ghosts/", "早期拉的开环轨迹", "`ghost.py make`"),
    ("agents/spar/", "从天梯回放重建的对手形状", "`registry.py gen --plan ladder`"),
    ("agents/lib/", "全量策略库（七个原子的笛卡尔积）", "`registry.py gen --plan all`"),
]


def fields():
    print("| 路径 | 数量 | 是什么 | 怎么来 |")
    print("|---|---|---|---|")
    for path, what, how in WHAT:
        n = len(glob.glob(os.path.join(ROOT, path, "*.py")))
        if n:
            print(f"| `{path}` | {n:,} | {what} | {how} |")
    if os.path.exists(os.path.join(ROOT, "benchmarks/strongest.py")):
        print("| `benchmarks/strongest.py` | 1 | 要打过的那条（源队伍天梯 **#1**），"
              "**已提交进 git**，`agents/CHAMPION` 指向它 | `wrap.py` |")


def submissions():
    out = subprocess.run(["kaggle", "competitions", "submissions", "kaggriculture"],
                         capture_output=True, text=True).stdout
    print("\n| 日期 | 提交号 | 天梯分 | 描述 |")
    print("|---|---|---|---|")
    for ln in out.split("\n")[2:]:
        m = re.search(r"(SubmissionStatus\.\w+)\s+([\d.]+)?\s*$", ln)
        d = re.search(r"(2026-\d\d-\d\d)", ln)
        if not (m and m.group(2)):
            continue
        desc = ln[45:ln.find("SubmissionStatus")].strip() if "SubmissionStatus" in ln else ""
        desc = re.sub(r"^[\d:.]+\s*", "", desc)[:60] or "*(无描述)*"
        print(f"| {d.group(1)[5:] if d else '?'} | `{ln[:9].strip()}` | "
              f"{float(m.group(2)):.1f} | {desc} |")


if __name__ == "__main__":
    fields()
    submissions()
    sys.exit(0)
