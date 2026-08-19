"""Smoke tests for the GPU-batched engine (CPU is enough)."""

import os
import sys


def main():
    try:
        import torch
    except ImportError:
        print("torch not installed; pip install -r requirements/gpu.txt")
        sys.exit(1)

    from rl.gpu.env import KaggGpuEnv
    from rl.gpu.obs import encode
    from rl.gpu.policy import MultiHeadActor, ppo_update, compute_gae
    from rl.gpu import constants as C
    from rl.features import FEATURE_DIM

    device = "cpu"
    B = 4
    env = KaggGpuEnv(batch=B, device=device, opponent="starter")
    obs, n_hands = env.reset(seeds=list(range(B)))
    assert obs.shape == (B, FEATURE_DIM), obs.shape
    assert obs.shape[-1] == C.FEATURE_DIM

    # starter vs starter should plant carrots within a few days
    env2 = KaggGpuEnv(batch=B, device=device, opponent="starter")
    env2.reset(seeds=list(range(B)))
    from rl.gpu.decode import decode_starter, merge_actions
    from rl.gpu.engine import step
    for _ in range(48):
        a0 = decode_starter(env2.st, 0, env2.T)
        a1 = decode_starter(env2.st, 1, env2.T)
        act = merge_actions(a0, a1)
        step(env2.st, act, env2.T)
    planted = (env2.st.kind == C.K_PLANT).any()
    print("starter loop 48 steps  planted_any=", bool(planted),
          "money=", env2.st.money.mean(0).tolist(),
          "day=", int(env2.st.day[0]))
    assert not torch.isnan(env2.st.money).any()
    assert (env2.st.money >= 0).all()

    model = MultiHeadActor()
    opt = torch.optim.Adam(model.parameters(), lr=3e-4)
    obs, n_hands = env.reset(seeds=list(range(B)))
    obs_l, act_l, logp_l, rew_l, val_l, done_l, nh_l = [], [], [], [], [], [], []
    for _ in range(8):
        tasks, logp, val = model.act(obs, n_hands, sample=True)
        nxt, rew, done, info = env.step(tasks)
        obs_l.append(obs)
        act_l.append(tasks)
        logp_l.append(logp)
        rew_l.append(rew)
        val_l.append(val.detach())
        done_l.append(done)
        nh_l.append(n_hands)
        obs, n_hands = nxt, info["n_hands"]
    obs_t = torch.stack(obs_l)
    act_t = torch.stack(act_l)
    logp_t = torch.stack(logp_l)
    rew_t = torch.stack(rew_l)
    val_t = torch.stack(val_l)
    done_t = torch.stack(done_l)
    nh_t = torch.stack(nh_l)
    boot = torch.zeros(B)
    val_cat = torch.cat([val_t, boot.unsqueeze(0)], 0)
    adv, ret = compute_gae(rew_t, val_cat, done_t)
    stats = ppo_update(model, opt, obs_t, act_t, logp_t.detach(), adv.detach(), ret.detach(), nh_t,
                       epochs=1, minibatch=16)
    print("ppo_update ok", stats)

    path = os.path.join("rl", "gpu", "_selfcheck.npz")
    model.save(path)
    model2 = MultiHeadActor()
    model2.load(path)
    os.remove(path)
    print("save/load ok")

    env3 = KaggGpuEnv(batch=2, device=device, opponent="scripted")
    obs, nh = env3.reset(seeds=[1, 2])
    for _ in range(24):
        tasks, _, _ = model.act(obs, nh, sample=True)
        obs, r, d, info = env3.step(tasks)
        nh = info["n_hands"]
    print("scripted 24 steps  n_hands=", env3.st.n_hands.tolist(),
          "money=", env3.st.money.mean(0).tolist())
    print("gpu selfcheck ok")
    print("engine regression: python -m rl.gpu.verify --left starter --right starter")


if __name__ == "__main__":
    main()
