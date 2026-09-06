"""装袋树的关键假设:A 的前缀 + B 的后缀能不能接上?

带子是开环定序的,B 的后半段预设 B 自己的棋盘/库存/位置。若接不上,
非法动作会静默 no-op(CLAUDE.md 的老陷阱),农场会安静地烂掉。
对照组 A+A 必须逐位复现 A 本身 —— 那是这个测量的已知阳性。
"""
import sys, os, json, base64, zlib, re, statistics as st
ROOT = "/scratch/jwj/Kaggriculture"
sys.path.insert(0, ROOT + "/rl/tensor_env")
from tape_t import load_trace
from kaggle_environments import make

BLOB = re.compile(r"(_TRACE\s*=\s*json\.loads\(\s*zlib\.decompress\(\s*base64\.b85decode\(\s*)"
                  r"((?:['\"](?:[^'\"\\]|\\.)*['\"]\s*)+)")

def write_spliced(a_path, b_path, cut, out):
    A, B = load_trace(a_path), load_trace(b_path)
    T = [dict(e) for e in A[:cut]] + [dict(e) for e in B[cut:]]
    src = open(a_path).read()
    m = BLOB.search(src)
    blob = base64.b85encode(zlib.compress(
        json.dumps(T, separators=(",", ":")).encode(), 9)).decode()
    lit = "\n    ".join('"%s"' % blob[i:i+76] for i in range(0, len(blob), 76))
    open(out, "w").write(src[:m.start(2)] + lit + src[m.end(2):])
    return out

def money(agent, opp, seed):
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([agent, opp])
    f = env.state[0].observation.farms
    return f[0]["money"], f[0]["money"] - f[1]["money"]

if __name__ == "__main__":
    A = ROOT + "/agents/newlines/n04.py"
    OPP = ROOT + "/agents/newlines/n09.py"
    seeds = [123, 555]
    cuts = [int(x) for x in sys.argv[1].split(",")]
    others = sys.argv[2].split(",")
    base = {s: money(A, OPP, s) for s in seeds}
    print(f"基线 n04 vs n09：" + "  ".join(f"seed{s} 钱 {base[s][0]:,.0f} margin {base[s][1]:+,.0f}" for s in seeds))
    print(f"\n{'切点':>6}{'后缀':>7}{'我方钱 中位':>13}{'margin 中位':>13}{'对基线 Δ':>12}")
    for cut in cuts:
        # 已知阳性:A+A 必须复现基线
        p = write_spliced(A, A, cut, f"/tmp/spl_self_{cut}.py")
        r = [money(p, OPP, s) for s in seeds]
        ok = all(abs(r[i][0] - base[s][0]) < 1e-6 for i, s in enumerate(seeds))
        print(f"{cut:>6}{'n04(自身)':>10}{st.median(x[0] for x in r):>10,.0f}"
              f"{st.median(x[1] for x in r):>13,.0f}"
              f"{'  已知阳性 ' + ('通过' if ok else '失败!'):>12}")
        for b in others:
            bp = f"{ROOT}/agents/newlines/{b}.py"
            p = write_spliced(A, bp, cut, f"/tmp/spl_{b}_{cut}.py")
            r = [money(p, OPP, s) for s in seeds]
            mm = st.median(x[0] for x in r); mg = st.median(x[1] for x in r)
            print(f"{cut:>6}{b:>7}{mm:>13,.0f}{mg:>13,.0f}"
                  f"{mm - st.median(base[s][0] for s in seeds):>+12,.0f}")
