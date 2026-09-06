"""开局搜索的上界:换掉前 cut 步,后面全部保持 n04。

之前的扫描是 n04@cut + X 后缀(换后段);这里是 X@cut + n04 后缀(换开局)。
依据:n07 单独打 n09 是 -5,067,而 n04@25 + n07 是 +21,146
⇒ 光换前 25 步就差 +26,213,比今天量到的任何杠杆大一个量级,而开局从没被搜索过。
"""
import sys, os, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splice import write_spliced, money
ROOT="/scratch/jwj/Kaggriculture"; T=ROOT+"/agents/newlines/"
BASE=T+"n04.py"
OPENERS=["n01","n02","n03","n05","n06","n07","n08","n09","n10","n11","n12"]
OPP=sys.argv[2] if len(sys.argv)>2 else T+"n09.py"
CUTS=[int(x) for x in sys.argv[1].split(",")]
seeds=[123,555,777]
base={s: money(BASE,OPP,s)[1] for s in seeds}
print(f"对手 {os.path.basename(OPP)}  n04 基线 margin 中位 {st.median(base.values()):+,.0f}"
      f"  逐seed {[f'{base[s]:+,.0f}' for s in seeds]}", flush=True)
print(f"\n{'开局来自':>8}" + "".join(f"{c:>10}" for c in CUTS), flush=True)
best=(None,None,-10**9)
for o in OPENERS:
    row=f"{o:>8}"
    for c in CUTS:
        p=write_spliced(T+o+".py", BASE, c, f"/tmp/op_{o}_{c}.py")
        v=st.median(money(p,OPP,s)[1]-base[s] for s in seeds)
        row+=f"{v:>+10,.0f}"
        if v>best[2]: best=(o,c,v)
    print(row, flush=True)
print(f"\n**最好的替代开局：{best[0]}@{best[1]} = {best[2]:+,.0f}**")
print(f"（对照：换后段的最好是 n04@25 + n07 = +5,385）")
