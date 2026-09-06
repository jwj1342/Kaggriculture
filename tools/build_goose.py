"""从 n04 的 meta 带子生成一条养鹅的带子（判词续三十的 ⑲ 步骤 1）。

只做**畜种置换**：BUILD_PASTURE→BUILD_COOP、BUY_ANIMAL COW/SHEEP→GOOSE、
PLACE COW/SHEEP→PLACE GOOSE。移动、WATER/HARVEST/FEED/CARE/COLLECT_FERTILIZER
一个字节不改 —— 引擎里这些 op 都是按品种泛型的，HARVEST 直接给
ANIMALS[animal]["product"]。

卖出侧：SELL MILK / SELL WOOL 原地换成 SELL EGG（同一槽位、同样的条数），
因为置换之后农场再也不产奶和毛，而蛋会把上限 100 的棚塞满后被
_drop_inventories_to_shed 丢弃。

用法：python tools/build_goose.py --out agents/goose/main.py [--keep-cows N]
"""
import argparse, base64, json, os, re, sys, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agents/newlines/n04.py")
BLOB = re.compile(
    r'(_TRACE\s*=\s*json\.loads\(\s*zlib\.decompress\(\s*base64\.b85decode\(\s*)'
    r'((?:[\'"](?:[^\'"\\]|\\.)*[\'"]\s*)+)')

def decode(src):
    m = BLOB.search(src)
    if not m:
        sys.exit("找不到 _TRACE blob")
    blob = "".join(re.findall(r'[\'"]((?:[^\'"\\]|\\.)*)[\'"]', m.group(2)))
    return m, json.loads(zlib.decompress(base64.b85decode(blob.encode())).decode())

def transform(T, keep=0, sell_egg=True, append_egg=True):
    st = {"pasture": 0, "buy": 0, "place": 0, "sell": 0, "kept": 0, "pickup": 0, "append": 0}
    for e in T:
        for key in ("farmer", "hands"):
            v = e.get(key)
            items = [v] if key == "farmer" else (v or [])
            for i, a in enumerate(items):
                if not isinstance(a, (list, tuple)) or not a:
                    continue
                a = list(a)
                if a[0] == "BUILD_PASTURE":
                    a[0] = "BUILD_COOP"; st["pasture"] += 1
                elif a[0] == "PLACE" and len(a) == 2 and a[1] in ("COW", "SHEEP"):
                    if st["kept"] < keep:
                        st["kept"] += 1; continue
                    a[1] = "GOOSE"; st["place"] += 1
                elif a[0] in ("PICKUP", "DROP") and len(a) >= 2 and a[1] in ("COW", "SHEEP"):
                    # BUY_ANIMAL 落在棚里,PLACE 从单位库存取 -> 中间必须 PICKUP。
                    # 不换这一条,鹅会永远卡在棚里(实测:棚 GOOSE 6,畜群空,钱 88)。
                    a[1] = "GOOSE"; st["pickup"] += 1
                else:
                    continue
                if key == "farmer": e["farmer"] = a
                else: v[i] = a
        mk = e.get("market") or []
        for i, o in enumerate(mk):
            if not isinstance(o, (list, tuple)) or not o:
                continue
            o = list(o)
            if o[0] == "BUY_ANIMAL" and o[1] in ("COW", "SHEEP"):
                o[1] = "GOOSE"; st["buy"] += 1
            elif sell_egg and o[0] == "SELL" and o[1] in ("MILK", "WOOL"):
                o[1] = "EGG"; o[2] = 10 ** 9; st["sell"] += 1
            else:
                continue
            mk[i] = o
        if append_egg and len(mk) < 10:
            # 追加在末尾:既有槽位索引逐位不变,而空槽位有 6,488 个,基本免费。
            # 不这样做,蛋会堆在上限 100 的棚里把带子自己的收成挤掉(实测草莓 269->49)。
            mk.append(["SELL", "EGG", 10 ** 9]); st["append"] += 1
            e["market"] = mk
    return st

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "agents/goose/main.py"))
    ap.add_argument("--keep-cows", type=int, default=0, help="保留前 N 头不换（做剂量曲线）")
    ap.add_argument("--no-sell-egg", action="store_true", help="不把 MILK/WOOL 卖单改成 EGG")
    ap.add_argument("--no-append-egg", action="store_true", help="不在空槽位追加 EGG 卖单")
    args = ap.parse_args()

    src = open(SRC).read()
    m, T = decode(src)
    st = transform(T, keep=args.keep_cows, sell_egg=not args.no_sell_egg,
                   append_egg=not args.no_append_egg)

    blob = base64.b85encode(zlib.compress(json.dumps(T, separators=(",", ":")).encode(), 9)).decode()
    chunks = [blob[i:i + 76] for i in range(0, len(blob), 76)]
    lit = "\n    ".join('"%s"' % c for c in chunks)
    out = src[:m.start(2)] + lit + src[m.end(2):]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(out)
    print(f"写出 {args.out}")
    print(f"  BUILD_PASTURE→BUILD_COOP {st['pasture']}   BUY_ANIMAL→GOOSE {st['buy']}   "
          f"PLACE→GOOSE {st['place']}（保留 {st['kept']}）   PICKUP/DROP→GOOSE {st['pickup']}   "
          f"SELL MILK/WOOL→EGG {st['sell']}   追加 SELL EGG {st['append']}")

if __name__ == "__main__":
    main()
