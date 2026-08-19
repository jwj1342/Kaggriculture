"""GPU-batched PPO: vectorized env + PyTorch policy.

    pip install -r requirements/gpu.txt
    python -m rl.gpu.train --device cpu --batch 256 --iters 200 \\
        --init-weights rl/ckpt_official/ppo_it0300.npz --ckpt-dir rl/ckpt_gpu

`--device auto` picks CUDA when present. On a laptop GPU (measured RTX 4060)
that is slower: one 256×720 iter is ~246s on CUDA vs ~132s on CPU, because
`step` is kernel-launch bound, not compute bound. Prefer `--device cpu` unless
you have measured the other way on that machine.

Opponent `starter` is the official carrot loop; `scripted` is all-IDLE + RESTOCK
(the default farm scheduler). Log `win=` is against those vectorized opponents,
not the ladder — exam is `tools/eval.py h2h` on the official interpreter.

Weights save in the same npz layout as CPU PPO so
`python -m rl.export_multihead --arch multi` still works.
The torchrl exporter stays at `rl/export_agent.py`.
"""

import argparse
import os
import time

import torch

from .env import KaggGpuEnv
from .policy import MultiHeadActor, compute_gae, ppo_update


def _device(name):
    if name == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument(
        "--device", default="auto",
        help="cpu|cuda|mps|auto. auto→CUDA if available; CPU is faster on "
             "launch-bound laptop GPUs (see module docstring).",
    )
    ap.add_argument("--opponent", choices=["starter", "scripted"], default="starter")
    ap.add_argument("--switch-after", type=int, default=80,
                    help="after this many iters, opponent becomes scripted")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--gamma", type=float, default=0.997)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=2048)
    ap.add_argument("--entropy", type=float, default=0.003)
    ap.add_argument("--value-coef", type=float, default=0.5)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--init-weights", default="rl/ckpt_official/ppo_it0300.npz")
    ap.add_argument("--ckpt-dir", default="rl/ckpt_gpu")
    ap.add_argument("--save-every", type=int, default=5)
    args = ap.parse_args()

    device = _device(args.device)
    print(f"device={device}  batch={args.batch}  opponent={args.opponent}")
    torch.manual_seed(args.seed)
    if device == "cuda":
        torch.cuda.manual_seed_all(args.seed)

    model = MultiHeadActor().to(device)
    init = args.init_weights
    if init and init.lower() not in ("none", "null", "-") and os.path.exists(init):
        try:
            model.load(init, allow_partial=True)
            print(f"loaded init weights from {init}")
        except Exception as e:
            print(f"init weights load failed: {e}")
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)

    env = KaggGpuEnv(batch=args.batch, device=device, opponent=args.opponent)
    os.makedirs(args.ckpt_dir, exist_ok=True)
    t0_all = time.time()

    for it in range(1, args.iters + 1):
        if it == args.switch_after + 1 and args.opponent == "starter":
            env.opponent = "scripted"
            print("  switched opponent to scripted")
        seeds = torch.randint(0, 2**30, (args.batch,), device="cpu").tolist()
        obs, n_hands = env.reset(seeds=seeds)
        t0 = time.time()

        obs_l, act_l, logp_l, rew_l, val_l, done_l, nh_l = [], [], [], [], [], [], []
        ep_r = torch.zeros(args.batch, device=device)
        for _ in range(720):
            tasks, logp, val = model.act(obs, n_hands, sample=True)
            nxt, rew, done, info = env.step(tasks)
            obs_l.append(obs)
            act_l.append(tasks)
            logp_l.append(logp)
            rew_l.append(rew)
            val_l.append(val.detach())
            done_l.append(done)
            nh_l.append(n_hands)
            ep_r = ep_r + rew
            obs, n_hands = nxt, info["n_hands"]
            if bool(done.all()):
                break

        obs_t = torch.stack(obs_l)       # [T,B,75]
        act_t = torch.stack(act_l)
        logp_t = torch.stack(logp_l)
        rew_t = torch.stack(rew_l)
        val_t = torch.stack(val_l)
        done_t = torch.stack(done_l)
        nh_t = torch.stack(nh_l)
        boot = torch.zeros(args.batch, device=device)
        val_cat = torch.cat([val_t, boot.unsqueeze(0)], dim=0)
        adv, ret = compute_gae(rew_t, val_cat, done_t, gamma=args.gamma, lam=args.lam)
        stats = ppo_update(
            model, opt, obs_t, act_t, logp_t.detach(), adv.detach(), ret.detach(), nh_t,
            clip=args.clip, entropy_coef=args.entropy, value_coef=args.value_coef,
            epochs=args.epochs, minibatch=args.minibatch, max_grad_norm=args.max_grad_norm,
        )
        money = env.st.money
        win = (money[:, 0] > money[:, 1]).float().mean()
        elapsed = time.time() - t0
        print(
            f"iter {it:4d}/{args.iters}  opp={env.opponent}  "
            f"ep_reward={float(ep_r.mean()):.3f}  win={float(win):.2f}  "
            f"money={float(money[:, 0].mean()):.0f}/{float(money[:, 1].mean()):.0f}  "
            f"pol={stats['policy_loss']:.4f} val={stats['value_loss']:.4f} "
            f"ent={stats['entropy']:.4f}  time={elapsed:.1f}s"
        )
        if it % args.save_every == 0 or it == args.iters:
            path = os.path.join(args.ckpt_dir, f"ppo_it{it:04d}.npz")
            model.save(path)
            print(f"  saved {path}  total_time={time.time() - t0_all:.1f}s")


if __name__ == "__main__":
    main()
