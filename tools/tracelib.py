#!/usr/bin/env python
"""Build a local library of the *distinct* plans the top of the ladder plays.

    python tools/tracelib.py pull --dates 2026-08-07,2026-08-08 --per-date 200 -j 12
    python tools/tracelib.py stats
    python tools/tracelib.py emit --out agents/traces --top 20

Kaggle publishes one dataset per day holding that day's highest-scoring
episodes -- games between players rated ~3,100 that we are never matched into.
Each is ~29 MB of JSON in and one 720-turn action sequence per seat out.

**Deduplication is the entire job.** In the first 156 trajectories pulled, 97
were the same plan; a naive corpus is one line copied a hundred times. Two farms
running the same plan one turn apart agree on *nothing* compared index to index,
so every comparison sweeps shifts of +-8 turns first -- without that, 156
recordings look like 156 strategies (`docs/ROADMAP.md` §3).

Only episodes from **after the 1.32.6 rebalance (2026-08-06/07)** are worth
holding: town demand halved and shop draws became with-replacement, so a plan
tuned before it is playing a different game.

The replay is deleted as soon as it is digested. 29 MB in, ~11 KB out, and disk
never holds more than `-j` replays at once.
"""

import argparse
import base64
import collections
import gzip
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kaggle_cli import dataset_file, dataset_files      # noqa: E402

WORK = "data/tracelib/work"
LIB = "data/tracelib"
INDEX = os.path.join(LIB, "index.json")
REBALANCE = "2026-08-07"          # first fully post-1.32.6 day
ALIGN = 8                         # turns of shift allowed when comparing plans
SAME = 0.85                       # agreement above this is the same plan


# --------------------------------------------------------------------------- io

def _load():
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            return json.load(f)
    return {"lines": {}, "seen": []}


def _save(idx):
    os.makedirs(LIB, exist_ok=True)
    tmp = INDEX + ".part"
    with open(tmp, "w") as f:
        json.dump(idx, f, indent=1, sort_keys=True)
    os.replace(tmp, INDEX)


def _pack(turns):
    return base64.b64encode(gzip.compress(json.dumps(turns).encode())).decode()


def _unpack(blob):
    return json.loads(gzip.decompress(base64.b64decode(blob)).decode())


# ------------------------------------------------------------------- comparison

def signature(turns):
    """What identifies a plan: the farm actions, turn by turn.

    Market orders are excluded on purpose -- they are the part a wrapper
    rewrites, so two agents running the same plan behind different market layers
    should count as the same plan.
    """
    return [json.dumps([t.get("farmer"), t.get("hands")], sort_keys=True)
            for t in turns]


def agreement(a, b, span=ALIGN):
    """Best turn-by-turn agreement over shifts of +-`span`."""
    n = min(len(a), len(b)) - span
    if n <= span:
        return 0.0
    best = 0
    for s in range(-span, span + 1):
        best = max(best, sum(1 for i in range(span, n) if a[i] == b[i + s]))
    return best / (n - span)


def coarse(sig):
    """A cheap key that identical plans share, to skip most full comparisons."""
    return hashlib.md5("|".join(sig[100:140]).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------- digest

def _digest_one(args):
    """Download one episode, return one record per seat. Deletes the replay."""
    date, name = args
    slug = f"kaggle/kaggriculture-episodes-{date}"
    path = dataset_file(slug, name, WORK)
    if not path:
        # Kaggle refuses downloads above some concurrency and the CLI exits 0
        # with no file, so this has to be counted rather than ignored -- a
        # silent 80% failure rate looks exactly like "that day had few episodes".
        return [{"error": "download refused (rate limit?)", "episode": int(name[:-5])}]
    try:
        with open(path) as f:
            data = json.load(f)
        steps = data["steps"]
        info = data.get("info") or {}
        # `TeamNames` is a list of plain strings; `Agents` carries dicts. Both
        # appear in the wild, so accept either.
        raw = info.get("TeamNames") or info.get("Agents") or []
        names = [t if isinstance(t, str) else (t or {}).get("Name") or "?" for t in raw]
        final = steps[-1]
        out = []
        for seat in (0, 1):
    # `steps[i]["action"]` is the action that PRODUCED `steps[i]["observation"]`,
    # not the one taken from it. So an agent asked at step i must return
    # `_TURNS[i + 1]`. Getting this wrong shifts the whole plan one turn late,
    # which for an open-loop plan means every decision is made against the
    # previous turn's board -- and it is invisible, because a shifted replay
    # still produces a plausible season. Verified against a real episode:
    # offset +1 reproduces 85,511 / 86,278 and the shop sequence exactly;
    # offset 0 gives 91,206 / 90,033 and a different town.
            turns = [(s[seat].get("action") or {}) for s in steps[1:]]
            if len(turns) < 700:
                continue
            out.append({
                "episode": int(name[:-5]), "seat": seat, "date": date,
                "team": names[seat] if seat < len(names) else "?",
                "score": float(final[seat].get("reward") or 0),
                "opponent_score": float(final[1 - seat].get("reward") or 0),
                "won": float(final[seat].get("reward") or 0)
                       > float(final[1 - seat].get("reward") or 0),
                # The seed lives in `info`, not in the first observation --
                # reading it from the wrong place gives None for every episode,
                # and an open-loop trace without its seed cannot be replayed on
                # the board it was recorded on, which is most of its value.
                "seed": info.get("seed"),
                "turns": _pack(turns),
            })
        return out
    except Exception as e:                          # noqa: BLE001
        return [{"error": f"{type(e).__name__}: {e}", "episode": int(name[:-5])}]
    finally:
        for p in (path, path + ".zip"):
            if p and os.path.exists(p):
                os.remove(p)


# ------------------------------------------------------------------------ pull

def cmd_pull(args):
    idx = _load()
    seen = set(idx["seen"])
    lines = idx["lines"]
    # coarse key -> line ids, so a new trace only compares against plausible ones
    buckets = collections.defaultdict(list)
    sigs = {}
    for lid, rec in lines.items():
        sigs[lid] = signature(_unpack(rec["turns"]))
        buckets[coarse(sigs[lid])].append(lid)

    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    stale = [d for d in dates if d < REBALANCE]
    if stale:
        print(f"  refusing {', '.join(stale)}: before the 1.32.6 rebalance "
              f"({REBALANCE}); those plans play a different game")
        dates = [d for d in dates if d >= REBALANCE]

    jobs = []
    for d in dates:
        # Cache the listing. It is four paged calls per date and it does not
        # change once a day is closed, but it is the first thing to hit a 429 --
        # and being rate-limited on the *listing* means the run stalls before
        # downloading anything at all.
        cache = os.path.join(LIB, f"files-{d}.json")
        if os.path.exists(cache):
            with open(cache) as f:
                all_names = json.load(f)
        else:
            all_names = dataset_files(f"kaggle/kaggriculture-episodes-{d}")
            if all_names:
                os.makedirs(LIB, exist_ok=True)
                with open(cache, "w") as f:
                    json.dump(all_names, f)
        names = [n for n in all_names if int(n[:-5]) not in seen]
        if args.per_date and len(names) > args.per_date:
            # even stride across the day, not the first N -- the listing is
            # chronological and one hour is one slice of the population
            step = len(names) / args.per_date
            names = [names[int(i * step)] for i in range(args.per_date)]
        jobs += [(d, n) for n in names]
        print(f"  {d}: {len(names)} episodes queued")
    if not jobs:
        print("  nothing new to pull")
        return 0

    t0 = time.time()
    new_lines = dupes = errors = kept_seats = 0
    os.makedirs(WORK, exist_ok=True)
    with ProcessPoolExecutor(args.jobs) as ex:
        futs = {ex.submit(_digest_one, j): j for j in jobs}
        for k, fut in enumerate(as_completed(futs), 1):
            for rec in fut.result():
                if "error" in rec:
                    errors += 1
                    continue
                seen.add(rec["episode"])
                kept_seats += 1
                sig = signature(_unpack(rec["turns"]))
                key = coarse(sig)
                hit = None
                for lid in buckets[key]:
                    if agreement(sig, sigs[lid]) > SAME:
                        hit = lid
                        break
                if hit is None:                     # nothing cheap matched: sweep all
                    for lid, s in sigs.items():
                        if agreement(sig, s) > SAME:
                            hit = lid
                            break
                if hit is not None:
                    ln = lines[hit]
                    ln["count"] += 1
                    ln["teams"] = sorted(set(ln["teams"] + [rec["team"]]))
                    ln["wins"] = ln.get("wins", 0) + int(rec["won"])
                    ln["plays"] = ln.get("plays", 0) + 1
                    if rec["score"] > ln["best_score"]:
                        ln.update(best_score=rec["score"], turns=rec["turns"],
                                  episode=rec["episode"], seat=rec["seat"],
                                  seed=rec["seed"], date=rec["date"],
                                  opponent_score=rec["opponent_score"])
                        sigs[hit] = sig
                    dupes += 1
                else:
                    lid = hashlib.md5(("|".join(sig)).encode()).hexdigest()[:12]
                    lines[lid] = {"turns": rec["turns"], "count": 1,
                                  "teams": [rec["team"]], "best_score": rec["score"],
                                  "episode": rec["episode"], "seat": rec["seat"],
                                  "seed": rec["seed"], "date": rec["date"],
                                  "opponent_score": rec["opponent_score"],
                                  "wins": int(rec["won"]), "plays": 1}
                    sigs[lid] = sig
                    buckets[key].append(lid)
                    new_lines += 1
            if k % 20 == 0 or k == len(jobs):
                el = time.time() - t0
                print(f"    {k}/{len(jobs)} episodes  {el/max(k,1):.1f}s each  "
                      f"{new_lines} lines / {dupes} dupes  eta "
                      f"{(len(jobs)-k)*el/max(k,1)/60:.0f} min", flush=True)
                idx["seen"] = sorted(seen)
                _save(idx)                          # incremental: safe to interrupt
    idx["seen"] = sorted(seen)
    _save(idx)
    ok = kept_seats // 2
    rate = 100 * ok / max(1, len(jobs))
    print(f"\n  {ok}/{len(jobs)} episodes downloaded ({rate:.0f}%)"
          f"{f', {errors} refused or malformed' if errors else ''}")
    if rate < 90:
        print(f"  !! {100-rate:.0f}% did not arrive -- lower -j and rerun; "
              f"the index is incremental so nothing is lost")
    print(f"  {kept_seats} trajectories -> {new_lines} new lines, {dupes} duplicates")
    print(f"  library now holds {len(lines)} distinct plans")
    return 0


# ----------------------------------------------------------------------- stats

def cmd_stats(args):
    idx = _load()
    lines = idx["lines"]
    if not lines:
        print("  empty -- run `pull` first")
        return 0
    rows = sorted(lines.items(), key=lambda kv: -kv[1]["count"])
    tot = sum(v["count"] for _, v in rows)
    print(f"{len(idx['seen']):,} episodes digested -> {tot:,} trajectories "
          f"-> {len(rows)} distinct plans\n")
    print(f"{'line':<14}{'seen':>6}{'teams':>7}{'best $':>11}{'date':>12}  代表队伍")
    for lid, v in rows[:args.top]:
        print(f"  {lid:<12}{v['count']:>6}{len(v['teams']):>7}"
              f"{v['best_score']:>11,.0f}{v['date']:>12}  {v['teams'][0][:26]}")
    head = sum(v["count"] for _, v in rows[:3])
    print(f"\n  top 3 plans cover {head}/{tot} = {100*head/tot:.0f}% of trajectories")
    print(f"  plans seen once only: {sum(1 for _, v in rows if v['count'] == 1)}")
    return 0


# ------------------------------------------------------------------------ emit

TEMPLATE = '''"""Ghost of {team} -- episode {episode}, seat {seat}, scored ${score:,.0f}.

Not a strategy. One top-of-ladder player's recorded 720-turn action sequence,
replayed turn by turn. Generated by tools/tracelib.py; do not edit.

This plan was seen {count} time(s) across {nteams} team(s). Open-loop: it cannot
react, and off its recorded seed ({seed}) its actions become silent no-ops --
which is a feature in an opponent and a trap in anything else.
"""

import base64
import gzip
import json

_SEED = {seed}
_TURNS = json.loads(gzip.decompress(base64.b64decode(
    "{blob}")).decode())
_PASS = {{"farmer": ["PASS"], "hands": [], "market": []}}


def agent(obs):
    try:
        i = int(obs.get("step", 0) or 0)
        return _TURNS[i] if 0 <= i < len(_TURNS) else _PASS
    except Exception:
        return _PASS
'''


def keep(v, args):
    """Is this line worth holding as an opponent?

    Money alone is a bad filter -- it depends on the opponent, and two strong
    lines sharing one market both score low. So the gates are: it has to have
    won at least sometimes, and it has to clear a floor that only excludes
    obviously broken seasons.
    """
    if v["best_score"] < args.min_score:
        return False
    plays = v.get("plays", v["count"])
    if args.won_only and plays and v.get("wins", 0) == 0:
        return False
    if v["count"] < args.min_seen:
        return False
    return True


def cmd_emit(args):
    idx = _load()
    rows = [(k, v) for k, v in idx["lines"].items() if keep(v, args)]
    dropped = len(idx["lines"]) - len(rows)
    if dropped:
        print(f"  filtered out {dropped} of {len(idx['lines'])} lines "
              f"(min_score={args.min_score:,}, min_seen={args.min_seen}"
              f"{', wins>0' if args.won_only else ''})")
    rows = sorted(rows, key=lambda kv: -kv[1]["count"])[:args.top]
    os.makedirs(args.out, exist_ok=True)
    man = {}
    for i, (lid, v) in enumerate(rows, 1):
        path = os.path.join(args.out, f"line{i:02d}-{lid}.py")
        src = TEMPLATE.format(team=v["teams"][0], episode=v["episode"], seat=v["seat"],
                              score=v["best_score"], count=v["count"],
                              nteams=len(v["teams"]), seed=v["seed"], blob=v["turns"])
        compile(src, path, "exec")
        with open(path, "w") as f:
            f.write(src)
        man[os.path.basename(path)] = {k: v[k] for k in
                                       ("count", "teams", "best_score", "episode",
                                        "seat", "seed", "date")}
        print(f"  {path}  seen {v['count']}x across {len(v['teams'])} teams  "
              f"${v['best_score']:,.0f}")
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    return 0



def cmd_verify(args):
    """Replay whole recorded episodes and require them to reproduce, exactly.

    The bar is *both sides of a real episode, to the dollar, plus the shop
    sequence* -- not "the ghost reaches a plausible score". The old check
    reported a ghost hitting 114% of its original and that was read as success;
    it was a one-turn offset producing a different, luckier season. An
    open-loop plan replayed a turn late makes every decision against the
    previous turn's board, and nothing about the result looks wrong.
    """
    import gzip as _gz
    from kaggle_environments import make
    tmp = os.path.join(WORK, "_verify")
    os.makedirs(tmp, exist_ok=True)
    tpl = ('import json,gzip,base64\n'
           '_T=json.loads(gzip.decompress(base64.b64decode("{b}")).decode())\n'
           '_P={{"farmer":["PASS"],"hands":[],"market":[]}}\n'
           'def agent(obs):\n'
           '    try:\n'
           '        i=int(obs.get("step",0) or 0)\n'
           '        return _T[i] if 0<=i<len(_T) else _P\n'
           '    except Exception: return _P\n')
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    ok = bad = 0
    for d in dates:
        cache = os.path.join(LIB, f"files-{d}.json")
        names = json.load(open(cache)) if os.path.exists(cache) else \
            dataset_files(f"kaggle/kaggriculture-episodes-{d}")
        step = max(1, len(names) // args.limit)
        for name in names[::step][:args.limit]:
            path = dataset_file(f"kaggle/kaggriculture-episodes-{d}", name, WORK)
            if not path:
                continue
            try:
                data = json.load(open(path))
                steps, seed = data["steps"], (data.get("info") or {}).get("seed")
                want, want_shops = data["rewards"], \
                    steps[-1][0]["observation"]["town"]["unlocked_shops"]
                for seat in (0, 1):
                    turns = [(s[seat].get("action") or {}) for s in steps[1:]]
                    blob = base64.b64encode(_gz.compress(
                        json.dumps(turns).encode())).decode()
                    open(os.path.join(tmp, f"s{seat}.py"), "w").write(
                        tpl.format(b=blob))
                env = make("kaggriculture",
                           configuration={"episodeSteps": 720, "seed": seed})
                env.run([os.path.join(tmp, "s0.py"), os.path.join(tmp, "s1.py")])
                got = [float(x.reward or 0) for x in env.steps[-1]]
                shops = env.steps[-1][0].observation["town"]["unlocked_shops"]
                exact = got == want and shops == want_shops
                ok, bad = ok + exact, bad + (not exact)
                mark = "ok  " if exact else "FAIL"
                print(f"  {mark} {name[:-5]}  {got} vs {want}"
                      f"{'' if shops == want_shops else '  shops differ'}")
            finally:
                for q in (path, path + ".zip"):
                    if q and os.path.exists(q):
                        os.remove(q)
    print(f"\n  {ok} exact, {bad} not")
    return 1 if bad else 0



def cmd_export(args):
    """Compress the library for sharing. It is not in the database.

    `data/arena.sqlite` holds episodes and ratings; the trace library is a JSON
    index of *plans*, which is a different kind of object and does not fit that
    schema. It is also the expensive part to rebuild -- roughly an hour of
    rate-limited pulling -- so it travels as a file, the same way the database
    does via `tools/sync.py`.
    """
    import lzma
    idx = _load()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with lzma.open(args.out, "wt") as f:
        json.dump(idx, f)
    print(f"  {args.out}  {os.path.getsize(args.out)/1048576:.1f} MB  "
          f"({len(idx['lines'])} plans from {len(idx['seen'])} episodes)")
    return 0


def cmd_import(args):
    """Merge a shared library in. Plans already held keep their best season."""
    import lzma
    opener = lzma.open if args.path.endswith(".xz") else open
    with opener(args.path, "rt") as f:
        other = json.load(f)
    idx = _load()
    before = len(idx["lines"])
    for lid, v in other["lines"].items():
        cur = idx["lines"].get(lid)
        if cur is None or v["best_score"] > cur["best_score"]:
            idx["lines"][lid] = v
        elif cur is not None:
            cur["count"] += v.get("count", 0)
            cur["teams"] = sorted(set(cur["teams"] + v.get("teams", [])))
    idx["seen"] = sorted(set(idx["seen"]) | set(other.get("seen", [])))
    _save(idx)
    print(f"  {before} -> {len(idx['lines'])} plans, {len(idx['seen'])} episodes seen")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pull")
    p.add_argument("--dates", required=True)
    p.add_argument("--per-date", type=int, default=200)
    # 16 is measured: at 48 the download failure rate was 80% and at 64 the
    # account was 429'd for minutes. The bottleneck is Kaggle's request rate,
    # not our cores, so more workers buy nothing and cost the whole pull.
    p.add_argument("-j", "--jobs", type=int, default=16)
    p.set_defaults(fn=cmd_pull)
    p = sub.add_parser("stats")
    p.add_argument("--top", type=int, default=25)
    p.set_defaults(fn=cmd_stats)
    p = sub.add_parser("export")
    p.add_argument("--out", default="dist/tracelib.json.xz")
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("import")
    p.add_argument("path")
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser("verify")
    p.add_argument("--dates", required=True)
    p.add_argument("--limit", type=int, default=4)
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("emit")
    p.add_argument("--out", default="agents/traces")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--min-score", type=float, default=50000,
                   help="drop lines whose best season is below this")
    p.add_argument("--min-seen", type=int, default=1,
                   help="drop lines seen fewer than this many times")
    p.add_argument("--won-only", action="store_true",
                   help="drop lines that never won an episode")
    p.set_defaults(fn=cmd_emit)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
