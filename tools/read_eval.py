#!/usr/bin/env python
"""One reader for eval.py's JSON, so no script has to guess the schema again.

eval.py writes {"summary": {n,wins,winrate,ci,margin,median_money},
"episodes": [{tag: "A0"|"A1", money: [p0, p1]}]}. Our money is money[0] on
an A0 episode and money[1] on an A1 one. Three roster scripts I submitted
today read a "rows"/"score_0" schema that does not exist -- they would have
printed nothing after hours of GPU time.

    python read_eval.py <dir-with-json> [label] [--split trained=a,b heldout=c,d]
"""
import json, glob, os, sys


def load(path):
    d = json.load(open(path))
    s = d.get("summary") or {}
    ours = [(e["money"][0] if e["tag"].endswith("0") else e["money"][1])
            for e in d.get("episodes", [])]
    theirs = [(e["money"][1] if e["tag"].endswith("0") else e["money"][0])
              for e in d.get("episodes", [])]
    return s, ours, theirs


def report(d, label="", trained=()):
    fs = sorted(glob.glob(os.path.join(d, "*.json")))
    if not fs:
        print(f"  (no eval json under {d})")
        return
    print(f"\n== {label or d} ==")
    print(f"  {'opponent':<44}{'win':>7}{'95% CI':>17}{'margin':>10}"
          f"{'ours med':>10}{'  pool'}")
    allours = []
    beaten = {"TRAINED": 0, "HELDOUT": 0}
    total = {"TRAINED": 0, "HELDOUT": 0}
    for f in fs:
        name = os.path.basename(f)[:-5]
        s, ours, theirs = load(f)
        if not s or not ours:
            print(f"  {name[:43]:<44}  (empty)")
            continue
        pool = "TRAINED" if any(t in name for t in trained) else "HELDOUT"
        total[pool] += 1
        lo = s["ci"][0]
        if lo > 50:
            beaten[pool] += 1
        med = sorted(ours)[len(ours) // 2]
        print(f"  {name[:43]:<44}{100*s['winrate']:>6.1f}%"
              f"{'[%.1f,%.1f]' % tuple(s['ci']):>17}{s['margin']:>+10,.0f}"
              f"{med:>10,.0f}   {pool}")
        allours += ours
    if allours:
        allours.sort()
        n = len(allours)
        print(f"  --- BEATEN heldout {beaten['HELDOUT']}/{total['HELDOUT']}"
              f"   trained {beaten['TRAINED']}/{total['TRAINED']}"
              f" | p05 {allours[int(.05*n)]:,.0f}"
              f"  median {allours[n//2]:,.0f}"
              f"  <20k {100*sum(1 for m in allours if m < 20000)/n:.0f}%"
              f"  ({n} episodes)")


if __name__ == "__main__":
    d = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    trained = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else (
        "closer_cleo", "ledger_lena", "k06")
    report(d, label, trained)
