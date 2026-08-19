#!/usr/bin/env python
"""Per-run training charts, written to rl/runs/<run>/plots/.

    python rl/plot_run.py --run <name>              # everything under rl/runs/<name>
    python rl/plot_run.py --ckpt <file.pt> --out <dir>

For every checkpoint in the run dir that carries training records
(latest.pt, trl.pt, ...) a six-panel summary lands in plots/ -- win rate,
learner-vs-opponent money, policy loss, value loss, entropy, throughput --
plus one roster bar chart (win % with 95% CI whiskers) when eval/*.json
exists. CSV logs are the fallback for runs without a checkpoint.
rl/train.py calls plot_summary() itself after training when --save is set,
so the standard flow needs no extra step; this CLI re-renders after the
fact (and slurm/rl_eval.sh runs it to fold in fresh roster results).

Style follows the repo's chart conventions (dataviz reference palette):
series blue #2a78d6 / orange #eb6834 in fixed order, ink-not-series-color
for text, hairline grid, one axis per panel, no dual axes.
"""

import argparse
import csv
import glob
import json
import os
import sys

_RL = os.path.dirname(os.path.abspath(__file__))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# reference palette (validated; see dataviz references/palette.md)
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
S1, S2 = "#2a78d6", "#eb6834"  # categorical slots 1-2, fixed order


def _style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=6)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8, length=3)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_color(MUTED)


def _endlabel(ax, x, y, text, color=INK2):
    ax.annotate(text, (x, y), xytext=(4, 0), textcoords="offset points",
                fontsize=8, color=color, va="center")


def _stage_marks(ax, records):
    """Vertical hairlines where the curriculum advanced a stage."""
    prev = None
    for r in records:
        s = r.get("stage")
        if s is None:
            return
        if prev is not None and s != prev:
            ax.axvline(r["iter"], color=BASELINE, linewidth=0.8,
                       linestyle=(0, (4, 3)))
        prev = s


def plot_summary(records, out_png, title=""):
    records = [r for r in records if "iter" in r]
    if not records:
        return None
    it = [r["iter"] for r in records]

    fig, axes = plt.subplots(2, 3, figsize=(12.5, 7), dpi=150)
    fig.patch.set_facecolor(PAGE)
    fig.suptitle(title, fontsize=12, color=INK, x=0.02, ha="left")

    ax = axes[0][0]
    _style(ax, "win rate vs opponent")
    win = [r["win"] for r in records]
    ax.plot(it, win, color=S1, linewidth=1.6)
    ax.set_ylim(-0.03, 1.06)
    ax.axhline(0.5, color=BASELINE, linewidth=0.8, linestyle=(0, (4, 3)))
    _stage_marks(ax, records)
    _endlabel(ax, it[-1], win[-1], f"{win[-1]:.2f}")

    ax = axes[0][1]
    _style(ax, "final money per episode batch")
    money = [r["money"] for r in records]
    omoney = [r["opp_money"] for r in records]
    ax.plot(it, money, color=S1, linewidth=1.6, label="learner")
    ax.plot(it, omoney, color=S2, linewidth=1.6, label="opponent")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper left")
    _stage_marks(ax, records)
    _endlabel(ax, it[-1], money[-1], f"{money[-1]:,.0f}")

    ax = axes[0][2]
    _style(ax, "throughput (lane-steps / s)")
    ax.plot(it, [r["sps"] for r in records], color=S1, linewidth=1.6)
    ax.set_ylim(bottom=0)

    ax = axes[1][0]
    _style(ax, "policy loss (clip objective)")
    ax.plot(it, [r["pg"] for r in records], color=S1, linewidth=1.6)
    ax.axhline(0.0, color=BASELINE, linewidth=0.8)

    ax = axes[1][1]
    _style(ax, "value loss")
    ax.plot(it, [r["vf"] for r in records], color=S1, linewidth=1.6)
    ax.set_ylim(bottom=0)

    ax = axes[1][2]
    _style(ax, "policy entropy (nats, both heads)")
    ax.plot(it, [r["ent"] for r in records], color=S1, linewidth=1.6)
    ax.set_ylim(bottom=0)

    for row in axes:
        for ax in row:
            ax.set_xlabel("iteration", fontsize=8, color=MUTED, labelpad=2)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_png


def plot_eval(eval_dir, out_png, title="roster, 95% CI"):
    rows = []
    for path in sorted(glob.glob(os.path.join(eval_dir, "*.json"))):
        with open(path) as f:
            s = json.load(f).get("summary", {})
        if "winrate" not in s:
            continue
        lo, hi = s.get("ci", (0.0, 100.0))
        rows.append((os.path.basename(path)[:-5], 100.0 * s["winrate"],
                     lo, hi, s.get("n", 0)))
    if not rows:
        return None
    rows.sort(key=lambda r: r[1])
    names = [r[0] for r in rows]
    wins = [r[1] for r in rows]
    y = range(len(rows))

    fig, ax = plt.subplots(figsize=(8.5, 0.55 * len(rows) + 1.4), dpi=150)
    fig.patch.set_facecolor(PAGE)
    _style(ax, f"{title}  (n={rows[0][4]} per pair)")
    ax.barh(y, wins, height=0.62, color=S1)
    for i, (_, w, lo, hi, _n) in enumerate(rows):
        ax.plot([lo, hi], [i, i], color=INK2, linewidth=1.2)
        verdict = "beaten" if lo > 50 else ("lost" if hi < 50 else "unresolved")
        ax.annotate(f"{w:.1f}%  {verdict}", (max(hi, w) + 1.5, i),
                    fontsize=8, color=INK2, va="center")
    ax.axvline(50, color=BASELINE, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.set_yticks(list(y), names, fontsize=8, color=INK)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("win rate (%)", fontsize=8, color=MUTED)
    ax.grid(axis="y", visible=False)

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_png


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def records_from_ckpt(path):
    import torch
    ck = torch.load(path, map_location="cpu", weights_only=False)
    return ck.get("records") or None


def records_from_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        try:
            out.append({k: float(v) for k, v in r.items()})
        except (TypeError, ValueError):
            continue
    for r in out:
        r["iter"] = int(r["iter"])
    return out


def render_run(run_dir, quiet=False):
    plots = os.path.join(run_dir, "plots")
    made, seen = [], set()
    for ck in sorted(glob.glob(os.path.join(run_dir, "*.pt"))):
        stem = os.path.splitext(os.path.basename(ck))[0]
        if stem == "best":  # best.pt mirrors latest's records up to the peak
            continue
        recs = records_from_ckpt(ck)
        if not recs:
            continue
        name = "summary.png" if stem == "latest" else f"{stem}-summary.png"
        out = plot_summary(recs, os.path.join(plots, name),
                           title=f"{os.path.basename(run_dir)} / {stem}")
        if out:
            made.append(out)
            seen.add(stem)
    for cs in sorted(glob.glob(os.path.join(run_dir, "*.csv"))):
        stem = os.path.splitext(os.path.basename(cs))[0]
        if stem in seen:
            continue
        out = plot_summary(records_from_csv(cs),
                           os.path.join(plots, f"{stem}-summary.png"),
                           title=f"{os.path.basename(run_dir)} / {stem}")
        if out:
            made.append(out)
    if os.path.isdir(os.path.join(run_dir, "eval")):
        out = plot_eval(os.path.join(run_dir, "eval"),
                        os.path.join(plots, "eval-roster.png"),
                        title=f"{os.path.basename(run_dir)} roster, 95% CI")
        if out:
            made.append(out)
    if not quiet:
        for p in made:
            print(f"wrote {p}")
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", default="", help="run name under rl/runs/")
    ap.add_argument("--dir", default="", help="explicit run directory")
    ap.add_argument("--ckpt", default="", help="single checkpoint to plot")
    ap.add_argument("--out", default="", help="output dir (with --ckpt)")
    args = ap.parse_args(argv)

    if args.ckpt:
        recs = records_from_ckpt(args.ckpt)
        out_dir = args.out or os.path.join(os.path.dirname(args.ckpt), "plots")
        stem = os.path.splitext(os.path.basename(args.ckpt))[0]
        out = plot_summary(recs or [], os.path.join(out_dir, f"{stem}-summary.png"),
                           title=stem)
        print(f"wrote {out}" if out else "no records in checkpoint")
        return 0
    run_dir = args.dir or os.path.join(_RL, "runs", args.run)
    if not args.run and not args.dir:
        ap.error("need --run, --dir or --ckpt")
    if not os.path.isdir(run_dir):
        ap.error(f"not a directory: {run_dir}")
    render_run(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
