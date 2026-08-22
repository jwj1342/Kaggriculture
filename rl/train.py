#!/usr/bin/env python
"""The unified TorchRL trainer: one entrypoint for the CPU and GPU lines.

    python rl/train.py --device cuda --B 1024 --iters 60          # A/B size
    python rl/train.py --device cpu  --B 128  --iters 12          # gate size
    python rl/train.py --algo a2c ...                             # swap loss

Supersedes rl/train_ppo.py (CPU, hand-written PPO over episode_pool) and
rl/tensor_env/train_t.py (GPU, hand-written PPO over EpisodeT): collection
is a TorchRL SyncDataCollector over trl_env.KGTensorEnv (EpisodeT is
device-agnostic, so --device is the whole CPU/GPU switch), advantages come
from torchrl.objectives.value.GAE, and the update is a swappable loss module
(--algo ppo -> ClipPPOLoss, --algo a2c -> A2CLoss). Adding an algorithm is
adding an entry to _LOSSES, not writing an update loop.

Coefficients are train_t.py's (which are rl-baseline train_ppo.py's): GAE
gamma 0.999 lambda 0.95 with zero terminal bootstrap (fixed-length episodes,
lockstep termination), whole-batch advantage normalisation, clip 0.2,
entropy 0.003, Adam(lr, eps=1e-5), grad-norm clip 0.5. The hand loops used
vf_coef * 0.5 * MSE; torchrl's "l2" distance is a plain squared error, so
the module gets critic_coeff = 0.5 * vf_coef for the same effective weight.

Checkpoints save {"model": <PolicyT-compatible state_dict>, "hidden", ...}:
rl/export_agent.py consumes them unchanged (actor submodule names match
rl/policy.py's Policy), which is the bridge into slurm/rl_eval.sh's
export -> roster h2h -> eval_summary pipeline.
"""

import argparse
import csv
import inspect
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_TENSOR = os.path.join(_HERE, "tensor_env")
for _p in (_TENSOR, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch

import actions as A
import obs as O
from trl_env import KGTensorEnv
from trl_policy import (build_actor_critic, load_merged_state_dict,
                        merged_state_dict)

try:  # torchrl >= 0.12 name; SyncDataCollector is deprecated for removal in 0.13
    from torchrl.collectors import Collector as SyncDataCollector
except ImportError:
    from torchrl.collectors import SyncDataCollector
from torchrl.data import LazyTensorStorage, ReplayBuffer
from torchrl.data.replay_buffers.samplers import SamplerWithoutReplacement
from torchrl.objectives import A2CLoss, ClipPPOLoss
from torchrl.objectives.value import GAE

_LOSSES = {"ppo": ClipPPOLoss, "a2c": A2CLoss}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--algo", choices=sorted(_LOSSES), default="ppo")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--B", type=int, default=128, help="episodes per iteration")
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--hidden", type=int, nargs=2, default=[512, 256],
                    metavar=("H1", "H2"), help="actor trunk widths")
    ap.add_argument("--v-hidden", type=int, default=256, help="critic width")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0,
                    help="policy init + sampling seed; episode seeds derive from it")
    ap.add_argument("--gamma", type=float, default=0.999)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--minibatches", type=int, default=8)
    ap.add_argument("--ent-coef", type=float, default=0.003)
    ap.add_argument("--vf-coef", type=float, default=0.5)
    ap.add_argument("--win-bonus", type=float, default=3.0)
    ap.add_argument("--seat", choices=("0", "1", "alt"), default="0",
                    help="learner seat: fixed 0 / 1, or alternating per episode batch")
    ap.add_argument("--opponent", default="starter",
                    help='"starter", or a checkpoint .pt / weights .npz played greedily')
    # -- the old line's hooks, ported (rl/README.md "TorchRL 统一层") ---------
    ap.add_argument("--config", default="",
                    help="YAML of defaults (keys = flag names); CLI still overrides")
    ap.add_argument("--init-from", default="",
                    help="load model weights before training (BC init / warm start)")
    ap.add_argument("--resume", default="",
                    help="checkpoint to continue from: model + optimizer + seed "
                         "stream + curriculum/pool state (chained slurm jobs)")
    ap.add_argument("--freeze-policy-until", type=int, default=0,
                    help="critic-only updates for the first N lane-steps "
                         "(protects a BC-cloned policy during value warm-up)")
    ap.add_argument("--opponents", default="",
                    help="comma-separated curriculum stages (starter and/or "
                         "npz//pt paths); takes precedence over --opponent")
    ap.add_argument("--advance-at", type=float, default=0.85,
                    help="rolling-win gate to advance the curriculum stage")
    ap.add_argument("--league", action="store_true",
                    help="mix self-snapshots into the opponent pool (0.25 mass)")
    ap.add_argument("--pfsp", type=float, default=0.0,
                    help="within each pool category, weight opponents by "
                         "(1 - ema_win)^pfsp with a 0.1 uniform floor "
                         "(AlphaStar f_hard): dominated members drain out "
                         "of the sampling mass; 0 = uniform (legacy)")
    # -- kickstarting (Schmitt et al. 2018; the Lux-S1 winner's teacher-KL) --
    ap.add_argument("--kickstart", default="", choices=("", "barnyard"),
                    help="teacher whose mapped decision labels every "
                         "learner state; adds an annealed CE pull on the "
                         "action heads ON TOP of the RL loss (never plain "
                         "BC -- the RL term is on from step one)")
    ap.add_argument("--ks-coef", type=float, default=0.5,
                    help="initial weight of the teacher CE term")
    ap.add_argument("--ks-anneal", type=float, default=80e6,
                    help="lane-steps over which ks-coef decays linearly "
                         "to zero (0 = constant)")
    ap.add_argument("--fert-credit", type=float, default=0.0,
                    help="per-animal fertilizer-stream credit folded into "
                         "the potential: w x base x remaining days (the top "
                         "meta's #1 income line was unpriced; 0 = off)")
    ap.add_argument("--land-value", type=float, default=0.0,
                    help="override the potential's per-quadrant land value "
                         "(Kilo's flat 300; the iter-160 census found the "
                         "economy land-gated because a quadrant unlocks "
                         "~5k of downstream crop credit. 0 = keep 300)")
    ap.add_argument("--ks-every", type=int, default=1,
                    help="teacher labels every Nth step (profiler: the "
                         "teacher is 41%% of step time; 4 buys ~1.7x "
                         "collection throughput, CE skips the gaps)")
    ap.add_argument("--build-bonus", type=float, default=0.0,
                    help="weight of the curve-capped build credit folded "
                         "into the potential (targets measured from the "
                         "231k-season anatomy; 0 = off)")
    ap.add_argument("--bank", default="",
                    help="comma-separated make_bank.py files: banked resets "
                         "start episodes from mid-game states (backplay)")
    ap.add_argument("--bank-frac", type=float, default=0.5,
                    help="fraction of resets that start from the bank")
    ap.add_argument("--snapshot-every", type=int, default=5,
                    help="league: snapshot the actor every N iterations")
    # -- adversarial-gradient smoothing (docs: rl/README.md, RUNS 2026-08-19) --
    ap.add_argument("--margin-bonus", type=float, default=0.0,
                    help="terminal reward += w * tanh(money margin / scale): "
                         "grades losses so a 0%%-win frontier still carries "
                         "gradient (bounded on purpose -- per-step full "
                         "zero-sum was a documented negative result)")
    ap.add_argument("--margin-scale", type=float, default=30000.0)
    ap.add_argument("--opp-noise", type=float, default=0.0,
                    help="per lane, replace the opponent's action with a "
                         "random legal one at this rate (dominance smoothing)")
    ap.add_argument("--handicap", type=int, default=0,
                    help="extra starting money for the learner seat; with "
                         "--opponents the pool halves it at each win gate "
                         "and only advances the stage at zero")
    ap.add_argument("--residual-base", default="",
                    help="frozen prior (npz / checkpoint): the actor learns "
                         "logit corrections over it instead of a policy "
                         "from scratch")
    ap.add_argument("--multi-head", action="store_true",
                    help="per-hand task heads (rl/TODO.md #0): action = "
                         "[farmer, market, hand x12]; hand heads start "
                         "AUTO-biased, so iteration 0 plays the classic "
                         "scheduler and learns deviations")
    ap.add_argument("--potential",
                    choices=("networth", "future", "future-mkt"),
                    default="networth",
                    help='shaping potential: "networth" (holdings at base '
                         'price) or "future" (Kilo\'s future-credit formula: '
                         'planting credits expected harvest immediately) or '
                         '"future-mkt" (future with shed stock at '
                         "min(market, base) -- removes the hoarding subsidy)")
    ap.add_argument("--shape-gamma", type=float, default=0.0,
                    help="Ng-correct shaping: r = g*phi(s') - phi(s); the "
                         "plain difference (0 = legacy) leaks (1-g)*phi per "
                         "step, an annuity for holding high-phi assets. Set "
                         "to --gamma to close the leak.")
    ap.add_argument("--shape-scale", type=float, default=3000.0,
                    help="divisor of the per-step potential delta")
    ap.add_argument("--opp-lambda", type=float, default=0.0,
                    help="subtract lambda * opponent potential delta "
                         "(relative shaping; 1.0 is the archived "
                         "mutual-destruction result -- A/B graded values)")
    # -- deterministic probes + early stop (rl/probe.py) ---------------------
    ap.add_argument("--probe-every", type=int, default=0,
                    help="every N iterations, play a fixed seed set with the "
                         "argmax policy vs the current stage anchor (0 = off); "
                         "feeds the early stopper and the best.pt ratchet")
    ap.add_argument("--probe-lanes", type=int, default=128)
    ap.add_argument("--stop-patience", type=int, default=6,
                    help="stop after this many consecutive probes improving "
                         "neither win nor margin at an unchanged frontier")
    ap.add_argument("--stop-delta-win", type=float, default=0.01)
    ap.add_argument("--stop-delta-margin", type=float, default=500.0)
    ap.add_argument("--steps", type=int, default=720, help="episode length")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = leave)")
    ap.add_argument("--max-minutes", type=float, default=0.0,
                    help="stop after this wall time (0 = only --iters)")
    ap.add_argument("--log", default="", help="CSV of per-iteration records")
    ap.add_argument("--save", default="", help="checkpoint path after each iteration")
    ap.add_argument("--quiet", action="store_true")
    return ap


def parse_args(argv=None):
    """--config YAML becomes parser defaults, so the precedence is
    built-in < config file < command line (the sota-implementations
    convention, without the hydra dependency)."""
    ap = build_parser()
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", default="")
    known, _ = pre.parse_known_args(argv)
    if known.config:
        import yaml
        with open(known.config) as f:
            cfg = yaml.safe_load(f) or {}
        cfg = {str(k).replace("-", "_"): v for k, v in cfg.items()}
        unknown = sorted(set(cfg) - {a.dest for a in ap._actions})
        if unknown:
            ap.error(f"unknown keys in {known.config}: {unknown}")
        ap.set_defaults(**cfg)
    return ap.parse_args(argv)


def _filtered(cls, **kw):
    """Instantiate cls with only the kwargs its signature accepts (absorbs
    torchrl arg renames such as critic_coef -> critic_coeff across versions)."""
    sig = inspect.signature(cls.__init__).parameters
    return cls(**{k: v for k, v in kw.items() if k in sig})


def _kickstart_ce(actor_net, mb, multi):
    """Masked cross-entropy pulling the action heads toward the teacher's
    labels on the learner's OWN states (kickstarting, never plain BC: the
    RL loss stays on and the coefficient anneals). Entries whose label is
    illegal under the mask are skipped -- the intent mapping is lossy by
    design -- as are dead hand slots (label -1)."""
    NEG = -1e9
    outs = actor_net(mb["observation"])
    fl, ml = outs[0], outs[1]
    total = None
    denom = None

    def acc(loss, cnt):
        nonlocal total, denom
        total = loss if total is None else total + loss
        denom = cnt if denom is None else denom + cnt

    for logits, mask, lab in ((fl, mb["farmer_mask"], mb["teacher_f"]),
                              (ml, mb["market_mask"], mb["teacher_m"])):
        live = lab >= 0                       # -1 = unlabelled step (ks-every)
        lab_c = lab.clamp(min=0)
        lp = torch.log_softmax(logits.masked_fill(~mask, NEG), -1)
        legal = mask.gather(-1, lab_c.unsqueeze(-1)).squeeze(-1) & live
        pick = lp.gather(-1, lab_c.unsqueeze(-1)).squeeze(-1)
        acc(-(pick * legal.float()).sum(), legal.sum())
    if multi:
        hl = outs[2]                                     # (B, H, T)
        hm, lab = mb["hand_mask"], mb["teacher_h"]       # (B, H, T), (B, H)
        live = lab >= 0
        lab_c = lab.clamp(min=0)
        lp = torch.log_softmax(hl.masked_fill(~hm, NEG), -1)
        legal = hm.gather(-1, lab_c.unsqueeze(-1)).squeeze(-1) & live
        pick = lp.gather(-1, lab_c.unsqueeze(-1)).squeeze(-1)
        acc(-(pick * legal.float()).sum(), legal.sum())
    return total / denom.clamp(min=1)


def make_loss(algo, actor, critic, args):
    common = dict(
        actor_network=actor, critic_network=critic,
        entropy_bonus=True,
        entropy_coeff=args.ent_coef, entropy_coef=args.ent_coef,
        # hand loops: vf_coef * 0.5 * (v - ret)^2; torchrl l2 has no 0.5
        critic_coeff=0.5 * args.vf_coef, critic_coef=0.5 * args.vf_coef,
        loss_critic_type="l2",
        normalize_advantage=False,  # normalised whole-batch below, hand-loop style
    )
    if algo == "ppo":
        loss = _filtered(ClipPPOLoss, clip_epsilon=args.clip, **common)
    else:
        loss = _filtered(_LOSSES[algo], **common)
    loss.set_keys(action="action", sample_log_prob="sample_log_prob",
                  advantage="advantage", value_target="value_target",
                  value="state_value")
    return loss


def train(args, log_fn=None):
    if log_fn is None:
        log_fn = lambda s: print(s, flush=True)
    if args.threads > 0:
        torch.set_num_threads(args.threads)
    dev = torch.device(args.device)
    torch.manual_seed(args.seed)

    env = KGTensorEnv(
        args.B, device=dev,
        seat=0 if args.seat == "alt" else int(args.seat),
        alternate_seat=args.seat == "alt",
        episode_steps=args.steps, base_seed=args.seed,
        opponent=args.opponent, win_bonus=args.win_bonus,
        margin_bonus=args.margin_bonus, margin_scale=args.margin_scale,
        opp_noise=args.opp_noise, handicap=args.handicap,
        potential=args.potential, shape_scale=args.shape_scale,
        opp_lambda=args.opp_lambda, multi_head=args.multi_head,
        kickstart=args.kickstart, build_bonus=args.build_bonus,
        bank=args.bank, bank_frac=args.bank_frac,
        shape_gamma=args.shape_gamma, ks_every=args.ks_every,
        fert_credit=args.fert_credit, land_value=args.land_value)
    actor, critic, actor_net, critic_net = build_actor_critic(
        O.OBS_DIM, A.N_FARMER, A.N_MARKET,
        hidden1=args.hidden[0], hidden2=args.hidden[1],
        v_hidden=args.v_hidden, device=dev,
        residual_base=args.residual_base, multi=args.multi_head)
    if args.init_from:
        ck = torch.load(args.init_from, map_location="cpu", weights_only=False)
        load_merged_state_dict(actor_net, critic_net,
                               ck.get("model") or ck.get("state_dict") or ck)
        log_fn(f"initialised from {args.init_from}")

    pool = None
    if args.opponents:
        from trl_pool import OpponentPool
        snap_dir = (os.path.join(os.path.dirname(os.path.abspath(args.save)),
                                 "snapshots") if args.save else "")
        pool = OpponentPool(
            [s.strip() for s in args.opponents.split(",") if s.strip()],
            dev, advance_at=args.advance_at, league=args.league,
            snapshot_dir=snap_dir, seed=args.seed, handicap=args.handicap,
            pfsp=args.pfsp)
        env.opponent_sampler = pool.sample
    # shifted=True: value of obs and next-obs in ONE forward over T+1 steps
    # instead of torch.stack-ing two full copies of the batch (a 26.7 GiB
    # allocation at B=1024 that OOMed an 80 GB H100); valid because a batch
    # is whole episodes -- obs[t+1] == next.obs[t] except at the terminal,
    # where the value is masked by `terminated` anyway.
    adv_mod = GAE(gamma=args.gamma, lmbda=args.lam, value_network=critic,
                  average_gae=False, shifted=True)
    loss_mod = make_loss(args.algo, actor, critic, args).to(dev)
    optim = torch.optim.Adam(loss_mod.parameters(), lr=args.lr, eps=1e-5)

    if args.save:
        os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
    stopper = None
    if args.probe_every > 0:
        from probe import EarlyStopper
        stopper = EarlyStopper(
            len(pool.anchors) if pool is not None else 1, args.advance_at,
            patience=args.stop_patience, delta_win=args.stop_delta_win,
            delta_margin=args.stop_delta_margin)

    start_it, total_steps, best_win = 0, 0, -1.0
    best_probe = -float("inf")
    prev_records = []
    if args.resume and os.path.exists(args.resume):
        ck = torch.load(args.resume, map_location=dev, weights_only=False)
        if ck.get("stopped"):
            log_fn(f"run already stopped ({ck['stopped']}) -- "
                   "nothing to resume; exiting cleanly")
            return (actor_net, critic_net), list(ck.get("records", []))
        load_merged_state_dict(actor_net, critic_net, ck["model"])
        if ck.get("optim"):
            optim.load_state_dict(ck["optim"])
        env._episode_index = int(ck.get("episode_index", 0))
        start_it = int(ck.get("iter", -1)) + 1
        total_steps = int(ck.get("total_steps", 0))
        best_win = float(ck.get("best_win", -1.0))
        if pool is not None and ck.get("pool"):
            pool.load_state(ck["pool"])
        if stopper is not None and ck.get("stopper"):
            stopper.load_state(ck["stopper"])
        best_probe = float(ck.get("best_probe", best_probe))
        prev_records = list(ck.get("records", []))
        log_fn(f"resumed {args.resume}: iter {start_it}, "
               f"episode_index {env._episode_index}"
               + (f", {pool.describe()}" if pool else ""))

    # the engine flags done while executing action index episode_steps - 2
    # (kaggle DONE semantics), so a complete episode is episode_steps - 1
    # actions and one collector batch == one batch of complete episodes
    # (asserted bit-exactly in rl/tensor_env/test_trl.py gate (ii))
    ep_len = args.steps - 1
    frames = args.B * ep_len
    col_kw = dict(frames_per_batch=frames,
                  total_frames=frames * max(0, args.iters - start_it),
                  device=dev)
    if "return_same_td" in inspect.signature(SyncDataCollector.__init__).parameters:
        # hand back the internal buffer instead of a clone (halves on-device
        # residency); safe because each batch is fully consumed -- the replay
        # buffer copies the keys it keeps -- before the next collect overwrites it
        col_kw["return_same_td"] = True
    collector = SyncDataCollector(env, actor, **col_kw)
    rb = ReplayBuffer(storage=LazyTensorStorage(frames, device=dev),
                      sampler=SamplerWithoutReplacement(),
                      batch_size=frames // args.minibatches)

    records = list(prev_records)
    writer = fh = None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        append = start_it > 0 and os.path.exists(args.log)
        fh = open(args.log, "a" if append else "w", newline="")
        writer = csv.writer(fh)
        if not append:
            writer.writerow(["iter", "steps", "sps", "win", "money", "opp_money",
                             "pg", "vf", "ent", "sec"])
    t_start = time.time()
    for i, td in enumerate(collector):
        it = start_it + i
        t0 = time.time()
        t_col = t0 - (records[-1].get("_t_end", t_start) if records else t_start)
        frozen = total_steps < args.freeze_policy_until
        with torch.no_grad():
            adv_mod(td)
        adv = td["advantage"]
        td["advantage"] = (adv - adv.mean()) / (adv.std() + 1e-8)

        # only what the loss reads: dropping next.observation / logits halves
        # the replay copy (at B=1024 the full batch is ~29 GB of float32 obs)
        keep = ["observation", "farmer_mask", "market_mask", "action",
                "sample_log_prob", "advantage", "value_target"]
        if args.multi_head:
            keep.append("hand_mask")  # the loss rebuilds the distribution
        if args.kickstart:
            keep += ["teacher_f", "teacher_m", "teacher_h"]
        flat = td.reshape(-1).select(*keep)
        ks_coef = 0.0
        if args.kickstart and not frozen:
            ks_coef = args.ks_coef * (
                max(0.0, 1.0 - total_steps / args.ks_anneal)
                if args.ks_anneal > 0 else 1.0)
        stats = {"pg": 0.0, "vf": 0.0, "ent": 0.0, "ks": 0.0}
        n_mb = 0
        for _ in range(args.epochs):
            rb.empty()
            rb.extend(flat)
            for _ in range(args.minibatches):
                mb = rb.sample()
                loss_td = loss_mod(mb)
                if frozen:  # value warm-up: the policy must not move
                    loss = loss_td["loss_critic"]
                else:
                    loss = sum(v for k, v in loss_td.items()
                               if k.startswith("loss_"))
                if ks_coef > 0.0:
                    ks = _kickstart_ce(actor_net, mb, args.multi_head)
                    loss = loss + ks_coef * ks
                    stats["ks"] += ks.item()
                optim.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(loss_mod.parameters(), 0.5)
                optim.step()
                with torch.no_grad():
                    stats["pg"] += loss_td["loss_objective"].item()
                    stats["vf"] += loss_td["loss_critic"].item()
                    stats["ent"] += -loss_td.get(
                        "loss_entropy", torch.zeros(())).item() / max(args.ent_coef, 1e-12)
                n_mb += 1
        for k in stats:
            stats[k] /= max(1, n_mb)

        if dev.type == "cuda":
            torch.cuda.synchronize()
        t_end = time.time()
        # terminal money via the done mask: identical to [:, -1] while a
        # batch is whole fixed-length episodes, and still correct once
        # bank-started (variable-length) episodes land in a batch
        dm = td["next", "done"].reshape(td.shape)
        if bool(dm.any()):
            last = (dm.to(torch.int64)
                    * torch.arange(td.shape[1], device=dm.device)).amax(1)
        else:
            last = torch.full((td.shape[0],), td.shape[1] - 1,
                              dtype=torch.int64, device=td.device)
        money = td["next", "money"].gather(1, last.unsqueeze(1)).squeeze(1)
        omoney = td["next", "opp_money"].gather(1, last.unsqueeze(1)).squeeze(1)
        win = ((money > omoney).float().mean()
               + 0.5 * (money == omoney).float().mean()).item()
        n_steps = td.numel()
        total_steps += n_steps
        sec = t_end - (records[-1].get("_t_end", t_start) if records else t_start)
        rec = {"iter": it, "steps": total_steps, "n_steps": n_steps,
               "sps": n_steps / sec, "win": win,
               "money": money.mean().item(), "opp_money": omoney.mean().item(),
               "stage": (pool.stage if pool is not None else None),
               "sec": sec, "t_collect": t_col, "_t_end": t_end, **stats}
        records.append(rec)
        ks_s = f"ks {stats['ks']:.3f}@{ks_coef:.2f}  " if args.kickstart else ""
        log_fn(f"it {it:3d}  steps {total_steps:>9,}  sps {rec['sps']:>8,.0f}  "
               f"win {win:5.3f}  money {rec['money']:>9,.0f}  opp {rec['opp_money']:>8,.0f}  "
               f"pg {stats['pg']:+.4f}  vf {stats['vf']:.4f}  ent {stats['ent']:.3f}  "
               f"{ks_s}{sec:5.1f}s (collect {t_col:4.1f}s)")
        if pool is not None:
            ev = pool.record(win)
            env.handicap = pool.handicap  # ladder takes effect at next reset
            if ev:
                log_fn(f"      curriculum {ev}: {pool.describe()}")
            elif it % 10 == 0:
                log_fn(f"      pool: {pool.describe()}")
            if (args.league and args.snapshot_every > 0
                    and it % args.snapshot_every == 0):
                pool.add_snapshot(actor_net, f"snap-{it:04d}")

        stop_reason = None
        if stopper is not None and (it + 1) % args.probe_every == 0:
            from probe import run_probe
            pw, pm = run_probe(actor_net, pool, args, dev)
            stage = pool.stage if pool is not None else 0
            hc = pool.handicap if pool is not None else int(env.handicap)
            rec["probe_win"], rec["probe_margin"] = pw, pm
            stop_reason = stopper.update(stage, hc, pw, pm)
            log_fn(f"      probe: win {pw:.3f}  margin {pm:+,.0f}  "
                   f"vs stage {stage + 1} @handicap {hc}"
                   + (f"  -> STOP ({stop_reason})" if stop_reason else ""))
        if writer:
            writer.writerow([it, total_steps, round(rec["sps"]), round(win, 4),
                             round(rec["money"]), round(rec["opp_money"]),
                             round(stats["pg"], 5), round(stats["vf"], 5),
                             round(stats["ent"], 4), round(sec, 2)])
            fh.flush()
        if args.save:
            ckpt = {"model": merged_state_dict(actor_net, critic_net),
                    "optim": optim.state_dict(),
                    "hidden": list(args.hidden), "v_hidden": args.v_hidden,
                    "algo": args.algo, "args": vars(args), "iter": it,
                    "episode_index": env._episode_index,
                    "total_steps": total_steps, "best_win": best_win,
                    "best_probe": best_probe, "stopped": stop_reason,
                    "stopper": stopper.state() if stopper is not None else None,
                    "pool": pool.state() if pool is not None else None,
                    "records": [{k: v for k, v in r.items() if k != "_t_end"}
                                for r in records]}
            _atomic_save(ckpt, args.save)
            # peak ratchet (the old line's best.pt): a policy can regress
            # after its peak; the best checkpoint is what eval/export wants.
            # With probes on, the ratchet reads the deterministic fixed-field
            # probe instead of the noisy, opponent-mix-dependent batch win.
            best_path = os.path.join(
                os.path.dirname(os.path.abspath(args.save)), "best.pt")
            if stopper is not None:
                # ratchet only on FINAL-stage probes: scores from different
                # frontiers are not comparable (a 0.97-win probe vs stage 2
                # outranks every 0-win probe vs the last-stage wall and
                # freezes best.pt in the past -- observed on breach)
                final_stage = (pool is None
                               or pool.stage == len(pool.anchors) - 1)
                if rec.get("probe_win") is not None and final_stage:
                    pscore = rec["probe_win"] * 1e9 + rec["probe_margin"]
                    if pscore > best_probe:
                        best_probe = pscore
                        ckpt["best_probe"] = best_probe
                        _atomic_save(ckpt, best_path)
            elif win > best_win:
                best_win = win
                ckpt["best_win"] = best_win
                _atomic_save(ckpt, best_path)
        if stop_reason:
            log_fn(f"early stop: {stop_reason} (iter {it})")
            break
        if args.max_minutes > 0 and (t_end - t_start) / 60.0 >= args.max_minutes:
            break
    collector.shutdown()
    if fh:
        fh.close()
    if args.save and records:
        try:  # charts must never fail a training run
            import plot_run
            run_dir = os.path.dirname(os.path.abspath(args.save))
            stem = os.path.splitext(os.path.basename(args.save))[0]
            name = "summary.png" if stem == "latest" else f"{stem}-summary.png"
            out = plot_run.plot_summary(
                [{k: v for k, v in r.items() if k != "_t_end"} for r in records],
                os.path.join(run_dir, "plots", name),
                title=f"{os.path.basename(run_dir)} / {stem}")
            if out:
                log_fn(f"plots: {out}")
        except Exception as e:
            log_fn(f"plots skipped: {type(e).__name__}: {e}")
    return (actor_net, critic_net), records



def _atomic_save(obj, path):
    """torch.save through a temp file plus os.replace.

    Chains run as ~30-minute links against --max-minutes 50, so a link normally
    ENDS by walltime kill. The save is about one second of each ~37-second
    iteration, so a kill lands inside it a few percent of the time -- and across
    a night of two dozen links that is closer to a coin flip than a corner case.
    A truncated latest.pt breaks --resume for the rest of the chain and silently
    poisons whatever the roster exports. os.replace is atomic within a
    filesystem, so the file a reader sees is always a complete checkpoint.
    Behaviour-neutral: same object, same path, only the write ordering changes.
    """
    tmp = path + ".tmp"
    torch.save(obj, tmp)
    os.replace(tmp, path)

def main(argv=None):
    args = parse_args(argv)
    _, records = train(args, log_fn=(lambda *a, **k: None) if args.quiet else None)
    if records:
        r = records[-1]
        print(f"done: {len(records)} iters, {r['steps']:,} learner lane-steps, "
              f"final win {r['win']:.3f}, mean sps "
              f"{sum(x['sps'] for x in records)/len(records):,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
