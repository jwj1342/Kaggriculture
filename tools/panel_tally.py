#!/usr/bin/env python
"""Full-field win rate per candidate, read from shard JSONL keyed on full path.

    python tools/panel_tally.py --shards data/shards/newplan-v1 --families

Nothing is ingested. `tournament.py`'s `short(path)` takes a basename and that
basename is the rating key, so a field of candidates that are all called
`main.py` -- or twelve emissions of one wrapper -- collapses into a single row
without erroring (run #100 measured it: one `main` row of 1,440 games = 4 x 360).
Every large ablation here reads the JSONL directly for that reason.

`--families` merges candidates whose *farm actions* agree above the threshold.
Farm-action agreement is the right key because hand-assignment differences
provably do not reach the environment: n04 and n06 differ on 41 turns and return
identical money to the dollar on three seeds (docs/RUNS.md, 2026-09-04).
"""
import argparse, collections, glob, json, os, sys

def load(shard_dir):
    rows, files = [], sorted(glob.glob(os.path.join(shard_dir, "shard-*.jsonl")))
    if not files:
        sys.exit(f"no shards under {shard_dir}")
    for f in files:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows, files

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", required=True)
    ap.add_argument("--candidates", nargs="*", default=None,
                    help="restrict the table to these full paths")
    ap.add_argument("--families", action="store_true")
    ap.add_argument("--thresh", type=float, default=0.85)
    args = ap.parse_args()

    rows, files = load(args.shards)
    print(f"  {len(rows):,} episodes from {len(files)} shards")

    wins = collections.Counter(); games = collections.Counter()
    money = collections.defaultdict(list)
    for r in rows:
        L, R = r["left"], r["right"]
        mL, mR = r["money"]
        if L == R:
            continue
        for who, mine, theirs in ((L, mL, mR), (R, mR, mL)):
            games[who] += 1
            money[who].append(mine)
            if mine > theirs:
                wins[who] += 1
            elif mine == theirs:
                wins[who] += 0.5

    import statistics as st
    names = args.candidates or sorted(games)
    names = [n for n in names if games[n]]
    names.sort(key=lambda n: -wins[n] / games[n])
    print(f"\n  {'agent':<58}{'局数':>7}{'胜率':>8}{'中位钱':>10}")
    for n in names:
        print(f"  {n:<58}{games[n]:>7}{100*wins[n]/games[n]:>7.2f}%"
              f"{st.median(money[n]):>10,.0f}")

    if args.families:
        # cluster the candidates on farm-action agreement
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import ast, base64, zlib
        from tracelib import agreement
        def tape(path):
            for nd in ast.walk(ast.parse(open(path).read())):
                if isinstance(nd, ast.Assign) and any(
                        getattr(t, "id", None) == "_TRACE" for t in nd.targets):
                    for s in ast.walk(nd):
                        if isinstance(s, ast.Constant) and isinstance(s.value, str) \
                                and len(s.value) > 500:
                            return json.loads(zlib.decompress(
                                base64.b85decode(s.value)).decode())
            return None
        def farmsig(t):
            return [json.dumps((x or {}).get("farmer"), sort_keys=True) for x in t]
        cands = [n for n in names if os.path.exists(n)]
        sig = {}
        for c in cands:
            t = tape(c)
            if t: sig[c] = farmsig(t)
        fam, seen = [], set()
        for c in sig:
            if c in seen: continue
            grp = [c]; seen.add(c)
            for d in sig:
                if d not in seen and agreement(sig[c], sig[d]) >= args.thresh:
                    grp.append(d); seen.add(d)
            fam.append(grp)
        print(f"\n  按农场动作一致率 >={args.thresh} 合并的家族（手的差异不到达环境）:")
        fam.sort(key=lambda g: -sum(wins[x] for x in g) / max(1, sum(games[x] for x in g)))
        for g in fam:
            W = sum(wins[x] for x in g); G = sum(games[x] for x in g)
            print(f"    {100*W/G:>6.2f}%  {G:>6} 局  " +
                  ", ".join(os.path.basename(x) for x in sorted(g)))

main()
