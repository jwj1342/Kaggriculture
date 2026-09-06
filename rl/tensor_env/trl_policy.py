"""TorchRL policy modules over the PolicyT structure (the unification layer).

ActorNet / CriticNet are rl/tensor_env/policy_t.py's PolicyT split in two,
with the SAME submodule names (l1/l2/farmer/market and v1/v2/vout) and the
same construction order, so:

  * {**actor.state_dict(), **critic.state_dict()} == PolicyT().state_dict()
    -- train_t.py checkpoints load here and vice versa;
  * the actor half matches rl/policy.py's Policy actor names, so a checkpoint
    saved as {"model": ...} feeds rl/export_agent.py unchanged;
  * ActorNet.state_np()/export_npz() keep the 8-array weights.npz contract
    (l1w,l1b,l2w,l2b,fw,fb,mw,mb) the numpy submission agent reads.

TwoHeadMasked is the joint (farmer, market) distribution as a
torch.distributions.Distribution: the same masked_fill(-1e9) + log_softmax +
gather-sum math as PolicyT.act/evaluate, expression for expression, so
log_prob and entropy are bit-identical to the hand-written path given the
same logits (the gate is test_trl.py). Action = int64 (..., 2) stacked
(farmer, market), which is what ClipPPOLoss/A2CLoss consume without any
composite-distribution machinery.

build_actor_critic() wires both into TorchRL: a TensorDictModule MLP head
producing flogits/mlogits, a ProbabilisticActor sampling "action" with
"sample_log_prob", and a ValueOperator writing "state_value".
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributions as D

NEG = -1e9


def _n_hand_task():
    # the hand-task head width tracks actions.HAND_TASKS (grew 7 -> 8 when
    # FEED landed); resolved lazily so this module stays importable without
    # the rl/ sys.path dance until a multi-head net is actually built
    import actions as A
    return A.N_HAND_TASK


def _ortho(layer, gain):
    nn.init.orthogonal_(layer.weight, gain)
    nn.init.constant_(layer.bias, 0.0)
    return layer


class ActorNet(nn.Module):
    """PolicyT's actor half; forward returns raw (flogits, mlogits)."""

    def __init__(self, obs_dim, n_farmer, n_market, hidden1=512, hidden2=256):
        super().__init__()
        self.obs_dim, self.n_farmer, self.n_market = obs_dim, n_farmer, n_market
        self.l1 = _ortho(nn.Linear(obs_dim, hidden1), math.sqrt(2))
        self.l2 = _ortho(nn.Linear(hidden1, hidden2), math.sqrt(2))
        self.farmer = _ortho(nn.Linear(hidden2, n_farmer), 1e-4)
        self.market = _ortho(nn.Linear(hidden2, n_market), 1e-4)

    def forward(self, x):
        h = torch.relu(self.l1(x))
        h = torch.relu(self.l2(h))
        return self.farmer(h), self.market(h)

    # -- export (rl-baseline export_agent contract: policy side only) ------
    def state_np(self):
        w = {
            "l1w": self.l1.weight, "l1b": self.l1.bias,
            "l2w": self.l2.weight, "l2b": self.l2.bias,
            "fw": self.farmer.weight, "fb": self.farmer.bias,
            "mw": self.market.weight, "mb": self.market.bias,
        }
        return {k: v.detach().cpu().float().numpy() for k, v in w.items()}

    def export_npz(self, path):
        import numpy as np
        np.savez(path, **self.state_np())


# The actor-half array contract (weights.npz <-> state dict). Every reader
# and writer of exported weights goes through these two helpers -- the
# export template, the CLI, frozen opponents and residual priors all speak
# the same eight mandatory arrays plus the optional hand head.
ACTOR_ARRAYS = {"l1w": "l1.weight", "l1b": "l1.bias",
                "l2w": "l2.weight", "l2b": "l2.bias",
                "fw": "farmer.weight", "fb": "farmer.bias",
                "mw": "market.weight", "mb": "market.bias"}
HANDS_ARRAYS = {"hw": "hands.weight", "hb": "hands.bias"}
# Head coupling (2026-08-30, docs/RUNS.md 28da6ef): the farm x market
# interaction measured +68,972 while either side swapped alone measured
# negative, so a policy whose heads are independent given the state cannot
# represent the coordination the gap consists of. cfw/chw condition the
# market head on the SAME TURN's sampled farmer action and hand tasks.
# No bias array on purpose: a coupling bias would be state-independent and
# the market head already has one -- and all-zero cfw/chw must reproduce
# the factored policy exactly (that identity is the load/lane contract,
# gated by test_couple.py).
COUPLE_ARRAYS = {"cfw": "couple_f", "chw": "couple_h"}
# Multi-order head (MultiOrderMultiHead). Both arrays ship or none does:
# an npz carrying only the eight mandatory arrays plays SLOT 0 ALONE, a
# one-order agent that banks money and passes every existing check.
# export_agent.py asserts msb is present whenever the checkpoint says
# --market-orders > 1, and asserts it AFTER building the arrays -- the
# first version of that guard read the checkpoint instead and passed
# while actor_arrays silently dropped both tables (measured: the export
# emitted one order on all 719 turns).
MORDER_ARRAYS = {"msb": "slot_bias", "cmw": "couple_m"}


def actor_arrays(sd, prefix="", numpy=False):
    """State dict (keys under `prefix`) -> weights.npz array dict."""
    out = {}
    for ak, pk in {**ACTOR_ARRAYS, **HANDS_ARRAYS, **COUPLE_ARRAYS,
                   **MORDER_ARRAYS}.items():
        k = prefix + pk
        if k in sd:
            v = sd[k]
            if numpy and torch.is_tensor(v):
                v = v.detach().cpu().float().numpy()
            out[ak] = v
        elif ak in ACTOR_ARRAYS:
            raise KeyError(f"actor state dict is missing {k}")
    return out


def arrays_to_sd(arrays, prefix=""):
    """weights.npz arrays (optionally d_-prefixed) -> actor state dict."""
    sd = {}
    for ak, pk in {**ACTOR_ARRAYS, **HANDS_ARRAYS, **COUPLE_ARRAYS,
                   **MORDER_ARRAYS}.items():
        k = prefix + ak
        if k in arrays:
            sd[pk] = torch.as_tensor(arrays[k])
        elif ak in ACTOR_ARRAYS:
            raise KeyError(f"weights arrays are missing {k}")
    return sd


def load_actor_state(path):
    """Two-head actor state dict from an exported weights.npz or a
    checkpoint (residual priors are two-head; hand heads are ignored)."""
    import numpy as np
    if path.endswith(".npz"):
        sd = arrays_to_sd(dict(np.load(path)))
        sd.pop("hands.weight", None)
        sd.pop("hands.bias", None)
        return sd
    ck = torch.load(path, map_location="cpu", weights_only=False)
    full = ck.get("model") or ck.get("state_dict") or ck
    return {k: v for k, v in full.items()
            if k.split(".")[0] in ("l1", "l2", "farmer", "market")}


class ResidualActor(nn.Module):
    """logits = frozen base prior + trainable delta (residual learning).

    The delta net keeps ActorNet's 1e-4 head init, so at step 0 the combined
    policy IS the prior up to noise -- training learns per-step corrections
    instead of a policy from scratch. state_np()/export_npz() carry BOTH
    nets (l1w.. for the base, d_l1w.. for the delta); the export template
    and FrozenPolicyOpponent sum the two forwards, so the deployment and
    league-snapshot contracts both hold.
    """

    def __init__(self, base_path, obs_dim, n_farmer, n_market,
                 hidden1=512, hidden2=256):
        super().__init__()
        sd = load_actor_state(base_path)
        h1 = sd["l1.weight"].shape[0]
        h2 = sd["l2.weight"].shape[0]
        self.base = ActorNet(obs_dim, n_farmer, n_market, h1, h2)
        self.base.load_state_dict(sd)
        self.base.requires_grad_(False)
        self.base.eval()
        self.delta = ActorNet(obs_dim, n_farmer, n_market, hidden1, hidden2)

    def forward(self, x):
        with torch.no_grad():
            bf, bm = self.base(x)
        df, dm = self.delta(x)
        return bf + df, bm + dm

    def state_np(self):
        base = self.base.state_np()
        return {**base, **{f"d_{k}": v for k, v in self.delta.state_np().items()}}

    def export_npz(self, path):
        import numpy as np
        np.savez(path, **self.state_np())


class CriticNet(nn.Module):
    """PolicyT's critic half; forward returns (..., 1) values (ValueOperator
    expects a trailing singleton)."""

    def __init__(self, obs_dim, v_hidden=256):
        super().__init__()
        self.v1 = _ortho(nn.Linear(obs_dim, v_hidden), math.sqrt(2))
        self.v2 = _ortho(nn.Linear(v_hidden, v_hidden), math.sqrt(2))
        self.vout = _ortho(nn.Linear(v_hidden, 1), 1.0)

    def forward(self, x):
        h = torch.relu(self.v1(x))
        h = torch.relu(self.v2(h))
        return self.vout(h)


class TwoHeadMasked(D.Distribution):
    """Joint masked categorical over (farmer, market); action (..., 2) int64."""

    arg_constraints = {}
    has_enumerate_support = False

    def __init__(self, flogits, mlogits, fmask, mmask):
        self.flp = F.log_softmax(flogits.masked_fill(~fmask, NEG), -1)
        self.mlp = F.log_softmax(mlogits.masked_fill(~mmask, NEG), -1)
        super().__init__(batch_shape=self.flp.shape[:-1],
                         event_shape=torch.Size([2]), validate_args=False)

    def sample(self, sample_shape=torch.Size()):
        if sample_shape != torch.Size():
            # MC fallbacks only (entropy estimates); collection never lands here
            fa = D.Categorical(logits=self.flp).sample(sample_shape)
            ma = D.Categorical(logits=self.mlp).sample(sample_shape)
            return torch.stack([fa, ma], -1)
        flp2 = self.flp.reshape(-1, self.flp.shape[-1])
        mlp2 = self.mlp.reshape(-1, self.mlp.shape[-1])
        fa = torch.multinomial(flp2.exp(), 1).squeeze(-1)
        ma = torch.multinomial(mlp2.exp(), 1).squeeze(-1)
        return torch.stack([fa.reshape(self.batch_shape),
                            ma.reshape(self.batch_shape)], -1)

    def log_prob(self, action):
        fa, ma = action[..., 0], action[..., 1]
        return (self.flp.gather(-1, fa.unsqueeze(-1)).squeeze(-1)
                + self.mlp.gather(-1, ma.unsqueeze(-1)).squeeze(-1))

    def entropy(self):
        # masked entries: p = exp(-1e9 - lse) == 0 exactly, so p*logp == -0.0
        return (-(self.flp.exp() * self.flp).sum(-1)
                - (self.mlp.exp() * self.mlp).sum(-1))

    @property
    def mode(self):
        return torch.stack([self.flp.argmax(-1), self.mlp.argmax(-1)], -1)

    def deterministic_sample(self):
        return self.mode


class MultiHeadMasked(D.Distribution):
    """farmer + market + per-hand task heads (rl/TODO.md #0); action is
    (..., 2 + H) int64 laid out [farmer, market, hand_1..hand_H]. Same
    masked_fill(-1e9) + log_softmax + gather-sum math as TwoHeadMasked,
    with the hand heads carried as one (..., H, T) block."""

    arg_constraints = {}
    has_enumerate_support = False

    def __init__(self, flogits, mlogits, hlogits, fmask, mmask, hmask):
        self.flp = F.log_softmax(flogits.masked_fill(~fmask, NEG), -1)
        self.mlp = F.log_softmax(mlogits.masked_fill(~mmask, NEG), -1)
        self.hlp = F.log_softmax(hlogits.masked_fill(~hmask, NEG), -1)
        H = self.hlp.shape[-2]
        super().__init__(batch_shape=self.flp.shape[:-1],
                         event_shape=torch.Size([2 + H]), validate_args=False)

    def sample(self, sample_shape=torch.Size()):
        if sample_shape != torch.Size():
            fa = D.Categorical(logits=self.flp).sample(sample_shape)
            ma = D.Categorical(logits=self.mlp).sample(sample_shape)
            ha = D.Categorical(logits=self.hlp).sample(sample_shape)
            return torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)
        flp2 = self.flp.reshape(-1, self.flp.shape[-1])
        mlp2 = self.mlp.reshape(-1, self.mlp.shape[-1])
        hlp2 = self.hlp.reshape(-1, self.hlp.shape[-1])
        fa = torch.multinomial(flp2.exp(), 1).squeeze(-1).reshape(self.batch_shape)
        ma = torch.multinomial(mlp2.exp(), 1).squeeze(-1).reshape(self.batch_shape)
        ha = torch.multinomial(hlp2.exp(), 1).squeeze(-1).reshape(
            self.hlp.shape[:-1])
        return torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)

    def log_prob(self, action):
        fa, ma, ha = action[..., 0], action[..., 1], action[..., 2:]
        return (self.flp.gather(-1, fa.unsqueeze(-1)).squeeze(-1)
                + self.mlp.gather(-1, ma.unsqueeze(-1)).squeeze(-1)
                + self.hlp.gather(-1, ha.unsqueeze(-1)).squeeze(-1).sum(-1))

    def entropy(self):
        return (-(self.flp.exp() * self.flp).sum(-1)
                - (self.mlp.exp() * self.mlp).sum(-1)
                - (self.hlp.exp() * self.hlp).sum((-1, -2)))

    @property
    def mode(self):
        return torch.cat([self.flp.argmax(-1, keepdim=True),
                          self.mlp.argmax(-1, keepdim=True),
                          self.hlp.argmax(-1)], -1)

    def deterministic_sample(self):
        return self.mode


class MarketOnlyMultiHead(MultiHeadMasked):
    """MultiHeadMasked whose ratio and entropy count the MARKET head only.

    For `--fixed-farm-tape`: the farm program comes from a recorded tape and
    the learner's farmer/hand actions are overridden at the raw-op level
    (`trl_env` step_overrides), exactly as `--fixed-market-profile` does in
    the other direction. Those two heads therefore cannot influence the
    reward, and leaving their log-probs in the PPO ratio would add pure noise
    to it -- the importance weight would fluctuate with draws that changed
    nothing. Dropping them makes the effective action space the market head,
    which is what the run is about.

    Why not do this with masks instead: a point-mass mask on the tape's own
    action would give log_prob 0 and entropy 0 with no policy change at all,
    but the tape lives in RAW op space (f_op/f_arg/f_qty) while the farmer
    head is a MACRO index, and the macro decode cannot express every raw op --
    which is precisely why `tape_t.TapeOpponent` bypasses the decode via
    step_idx overrides rather than emitting macro actions.

    Sampling is inherited unchanged: the farmer/hand draws still happen and
    are then discarded by the override. That keeps the action tensor's shape,
    the buffer layout and every downstream consumer identical, and costs one
    multinomial per head per step.
    """

    def log_prob(self, action):
        ma = action[..., 1]
        return self.mlp.gather(-1, ma.unsqueeze(-1)).squeeze(-1)

    def entropy(self):
        return -(self.mlp.exp() * self.mlp).sum(-1)


class MultiOrderMultiHead(D.Distribution):
    """farmer + K autoregressive market slots + per-hand task heads.

    Action is (..., 1 + K + H) int64 laid out
    [farmer, market_0..market_{K-1}, hand_1..hand_H].

    Why K > 1 (docs/RUNS.md verdict 33): the engine takes up to ten market
    orders a turn and the shared meta plan uses them; capping closer_cleo at
    one order a turn measures -89,479 and leaves the farm on 1,765 dollars.
    Every head in this repo emitted exactly one, so the policy class could not
    represent the plan it was being scored against -- that is the P ~ 1e-7
    representation gap in dollars.

    Slot k's logits are mbase + slot_bias[k] + couple_m[:, a_{k-1}] (slot 0
    takes slot_bias[0] only). Contracts, each load-bearing:
      * ZERO slot_bias and couple_m make slot 0 bit-identical to
        MultiHeadMasked's market head, and every later slot an i.i.d. draw
        from it -- warm starts and the K == 1 gate both rest on this;
      * sample() draws f, then h, then m_0..m_{K-1} in order, so the global
        RNG consumption differs from MultiHeadMasked; compare deterministic
        lanes, not sampled trajectories;
      * entropy() is H(f) + H(h) + sum_k H(m_k | argmax prefix): the exact
        term needs an expectation over prefixes, and conditioning on the mode
        keeps it deterministic and exact whenever the tables are zero.
    """

    arg_constraints = {}
    has_enumerate_support = False
    slot_bias = None   # (K, n_market), bound by build_actor_critic
    couple_m = None    # (n_market, n_market)

    def __init__(self, flogits, mlogits, hlogits, fmask, mmask, hmask):
        self.flp = F.log_softmax(flogits.masked_fill(~fmask, NEG), -1)
        self.hlp = F.log_softmax(hlogits.masked_fill(~hmask, NEG), -1)
        self._mraw = mlogits
        self._mmask = mmask
        self.K = self.slot_bias.shape[0]
        H = self.hlp.shape[-2]
        super().__init__(batch_shape=self.flp.shape[:-1],
                         event_shape=torch.Size([1 + self.K + H]),
                         validate_args=False)

    def _slot_lp(self, k, prev):
        """log-probs for market slot k given the previous slot's action."""
        logits = self._mraw + self.slot_bias[k]
        if prev is not None:
            logits = logits + self.couple_m.t()[prev]
        return F.log_softmax(logits.masked_fill(~self._mmask, NEG), -1)

    def _draw_slots(self, greedy=False):
        acts, prev = [], None
        for k in range(self.K):
            lp = self._slot_lp(k, prev)
            if greedy:
                a = lp.argmax(-1)
            else:
                a = torch.multinomial(
                    lp.reshape(-1, lp.shape[-1]).exp(), 1
                ).squeeze(-1).reshape(self.batch_shape)
            acts.append(a); prev = a
        return acts

    def sample(self, sample_shape=torch.Size()):
        flp2 = self.flp.reshape(-1, self.flp.shape[-1])
        hlp2 = self.hlp.reshape(-1, self.hlp.shape[-1])
        fa = torch.multinomial(flp2.exp(), 1).squeeze(-1).reshape(self.batch_shape)
        ha = torch.multinomial(hlp2.exp(), 1).squeeze(-1).reshape(
            self.hlp.shape[:-1])
        ma = self._draw_slots()
        return torch.cat([fa.unsqueeze(-1)]
                         + [a.unsqueeze(-1) for a in ma] + [ha], -1)

    def log_prob(self, action):
        K = self.K
        fa, ha = action[..., 0], action[..., 1 + K:]
        lp = (self.flp.gather(-1, fa.unsqueeze(-1)).squeeze(-1)
              + self.hlp.gather(-1, ha.unsqueeze(-1)).squeeze(-1).sum(-1))
        prev = None
        for k in range(K):
            a = action[..., 1 + k]
            lp = lp + self._slot_lp(k, prev).gather(
                -1, a.unsqueeze(-1)).squeeze(-1)
            prev = a
        return lp

    def entropy(self):
        ent = (-(self.flp.exp() * self.flp).sum(-1)
               - (self.hlp.exp() * self.hlp).sum((-1, -2)))
        prev = None
        for k in range(self.K):
            lp = self._slot_lp(k, prev)
            ent = ent - (lp.exp() * lp).sum(-1)
            prev = lp.argmax(-1)
        return ent

    @property
    def mode(self):
        ma = self._draw_slots(greedy=True)
        return torch.cat([self.flp.argmax(-1, keepdim=True)]
                         + [a.unsqueeze(-1) for a in ma]
                         + [self.hlp.argmax(-1)], -1)

    def deterministic_sample(self):
        return self.mode


class CoupledMultiHeadMasked(D.Distribution):
    """MultiHeadMasked with the market head CONDITIONED on the same turn's
    farmer action and hand tasks (autoregressive order f, h -> m).

    Why (docs/RUNS.md 28da6ef): the farm x market interaction measured
    +68,972 with either side alone negative, so heads that are independent
    given the state cannot represent the coordination the gap consists of.
    The conditional is one linear map on intent counts:

        mlogits(fa, ha) = mbase + couple_f[:, fa] + mean_i couple_h[:, ha_i]

    couple_f/couple_h are bound as CLASS attributes by build_actor_critic
    (a per-build subclass), because ProbabilisticActor instantiates the
    distribution from tensordict tensors only, and shipping the (n_market x
    n_farmer+n_task) tables through the replay buffer per step would cost
    gigabytes. Gradients flow: the loss re-runs the actor forward, and the
    parameters participate in log_prob's graph regardless of how the
    reference arrived.

    Contracts, each load-bearing:
      * all-zero coupling == MultiHeadMasked exactly -- log_prob, entropy
        and mode are bit-identical (test_couple.py G1), which is what makes
        legacy warm starts and the iter-0 deterministic lane gate valid;
      * sample() draws f, then h, then m -- a DIFFERENT global-RNG
        consumption order from MultiHeadMasked's f, m, h, so sampled
        trajectories are not byte-comparable to factored runs even at zero
        coupling (deterministic evaluation is; use that for lane gates);
      * entropy() is H(f) + H(h) + H(m | argmax f, argmax h): the exact
        market term needs an expectation over (f, h); conditioning on the
        mode keeps it deterministic (no extra RNG draws that would shift
        the stream) and exact whenever the coupling is zero;
      * hand means run over ALL MAX_HANDS slots, dead slots included --
        dead rows are IDLE-only, so their contribution is a constant the
        linear map absorbs; masking to live hands would need crew state
        the distribution does not have.
    """

    arg_constraints = {}
    has_enumerate_support = False
    couple_f = None   # (n_market, n_farmer), bound by build_actor_critic
    couple_h = None   # (n_market, n_hand_task)

    def __init__(self, flogits, mlogits, hlogits, fmask, mmask, hmask):
        self.flp = F.log_softmax(flogits.masked_fill(~fmask, NEG), -1)
        self.hlp = F.log_softmax(hlogits.masked_fill(~hmask, NEG), -1)
        self._mraw = mlogits
        self._mmask = mmask
        H = self.hlp.shape[-2]
        super().__init__(batch_shape=self.flp.shape[:-1],
                         event_shape=torch.Size([2 + H]), validate_args=False)

    def _mlp(self, fa, ha):
        """Conditioned market log-probs for one (fa, ha) per batch element."""
        delta = (self.couple_f.t()[fa]
                 + self.couple_h.t()[ha].mean(-2))
        return F.log_softmax(
            (self._mraw + delta).masked_fill(~self._mmask, NEG), -1)

    def sample(self, sample_shape=torch.Size()):
        if sample_shape != torch.Size():
            # MC fallback only (A2C entropy estimates); collection and PPO
            # never land here. Conditions each draw correctly.
            fa = D.Categorical(logits=self.flp).sample(sample_shape)
            ha = D.Categorical(logits=self.hlp).sample(sample_shape)
            ma = D.Categorical(logits=self._mlp(fa, ha)).sample()
            return torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)
        flp2 = self.flp.reshape(-1, self.flp.shape[-1])
        hlp2 = self.hlp.reshape(-1, self.hlp.shape[-1])
        fa = torch.multinomial(flp2.exp(), 1).squeeze(-1).reshape(self.batch_shape)
        ha = torch.multinomial(hlp2.exp(), 1).squeeze(-1).reshape(
            self.hlp.shape[:-1])
        mlp = self._mlp(fa, ha)
        ma = torch.multinomial(
            mlp.reshape(-1, mlp.shape[-1]).exp(), 1
        ).squeeze(-1).reshape(self.batch_shape)
        return torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)

    def log_prob(self, action):
        fa, ma, ha = action[..., 0], action[..., 1], action[..., 2:]
        mlp = self._mlp(fa, ha)
        return (self.flp.gather(-1, fa.unsqueeze(-1)).squeeze(-1)
                + mlp.gather(-1, ma.unsqueeze(-1)).squeeze(-1)
                + self.hlp.gather(-1, ha.unsqueeze(-1)).squeeze(-1).sum(-1))

    def entropy(self):
        fa = self.flp.argmax(-1)
        ha = self.hlp.argmax(-1)
        mlp = self._mlp(fa, ha)
        return (-(self.flp.exp() * self.flp).sum(-1)
                - (mlp.exp() * mlp).sum(-1)
                - (self.hlp.exp() * self.hlp).sum((-1, -2)))

    @property
    def mode(self):
        fa = self.flp.argmax(-1)
        ha = self.hlp.argmax(-1)
        ma = self._mlp(fa, ha).argmax(-1)
        return torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)

    def deterministic_sample(self):
        return self.mode


class MultiActorNet(ActorNet):
    """ActorNet + one task head per hand slot. The hand-head bias starts at
    +auto_bias on AUTO, so the untrained policy behaves like the classic
    scheduler and learns deviations (the action-space analog of the
    residual start; Kilo used the same trick with IDLE -- AUTO is a
    competent default where IDLE is a strike)."""

    def __init__(self, obs_dim, n_farmer, n_market, hidden1=512, hidden2=256,
                 n_hands=12, n_hand_task=None, auto_bias=2.5, couple=False,
                 market_orders=1):
        super().__init__(obs_dim, n_farmer, n_market, hidden1, hidden2)
        self.market_orders = max(1, int(market_orders))
        n_hand_task = n_hand_task or _n_hand_task()
        self.n_hands, self.n_hand_task = n_hands, n_hand_task
        self.hands = _ortho(nn.Linear(hidden2, n_hands * n_hand_task), 1e-4)
        with torch.no_grad():
            self.hands.bias.view(n_hands, n_hand_task)[:, 0] = auto_bias
        if couple:
            # Market-head coupling tables (CoupledMultiHeadMasked). ZERO init
            # is the contract, not a convenience: at zero the coupled policy
            # is bit-identical to the factored one, so legacy checkpoints
            # warm-start unchanged and the iter-0 deterministic lane gate
            # stays valid. torch.zeros draws no RNG, so adding these does
            # not shift the init stream of the shared layers either.
            self.couple_f = nn.Parameter(torch.zeros(n_market, n_farmer))
            self.couple_h = nn.Parameter(torch.zeros(n_market, n_hand_task))
        if self.market_orders > 1:
            # Multi-order market head (rl/TODO.md 20). The gap it closes is
            # measured, not assumed: capping closer_cleo at ONE market order a
            # turn costs it -89,479 margin and bankrupts the farm (money 80,647
            # -> 1,765, docs/RUNS.md verdict 33), and one order a turn is
            # exactly what every head in this repo could emit.
            #
            # Slot 0 keeps the existing head verbatim. Slot k adds a per-slot
            # bias and one linear map on the PREVIOUS slot's sampled action --
            # the autoregressive order m_0 -> m_1 -> ... -> m_{K-1}. Both
            # tables are ZERO-init, which is the contract: at zero, slot 0 is
            # bit-identical to the one-order policy and every later slot is an
            # i.i.d. draw from it, so a legacy checkpoint warm-starts unchanged
            # and the K == 1 lane gate stays valid. torch.zeros draws no RNG,
            # so the init stream of the shared layers is untouched.
            self.slot_bias = nn.Parameter(
                torch.zeros(self.market_orders, n_market))
            self.couple_m = nn.Parameter(torch.zeros(n_market, n_market))

    def forward(self, x):
        h = torch.relu(self.l1(x))
        h = torch.relu(self.l2(h))
        hl = self.hands(h).view(*x.shape[:-1], self.n_hands, self.n_hand_task)
        return self.farmer(h), self.market(h), hl

    def state_np(self):
        out = super().state_np()
        out["hw"] = self.hands.weight.detach().cpu().float().numpy()
        out["hb"] = self.hands.bias.detach().cpu().float().numpy()
        if hasattr(self, "couple_f"):
            out["cfw"] = self.couple_f.detach().cpu().float().numpy()
            out["chw"] = self.couple_h.detach().cpu().float().numpy()
        if hasattr(self, "slot_bias"):
            # Multi-order head. Both arrays MUST ship: an export that drops
            # them plays slot 0 only, which is a different agent that scores
            # silently -- the same shape as the wrapped-agent trap, one layer
            # down. export_agent.py refuses a multi-order checkpoint whose npz
            # lacks msb.
            out["msb"] = self.slot_bias.detach().cpu().float().numpy()
            out["cmw"] = self.couple_m.detach().cpu().float().numpy()
        return out


class MultiResidualActor(nn.Module):
    """Frozen two-head prior + trainable multi-head delta: farmer/market
    logits are prior + correction, hand logits come from the delta alone
    (the prior never had hands -- they start at the AUTO bias)."""

    def __init__(self, base_path, obs_dim, n_farmer, n_market,
                 hidden1=512, hidden2=256, n_hands=12, n_hand_task=None):
        super().__init__()
        n_hand_task = n_hand_task or _n_hand_task()
        sd = load_actor_state(base_path)
        h1, h2 = sd["l1.weight"].shape[0], sd["l2.weight"].shape[0]
        self.base = ActorNet(obs_dim, n_farmer, n_market, h1, h2)
        self.base.load_state_dict(sd)
        self.base.requires_grad_(False)
        self.base.eval()
        self.delta = MultiActorNet(obs_dim, n_farmer, n_market,
                                   hidden1, hidden2, n_hands, n_hand_task)

    def forward(self, x):
        with torch.no_grad():
            bf, bm = self.base(x)
        df, dm, dh = self.delta(x)
        return bf + df, bm + dm, dh

    def state_np(self):
        base = self.base.state_np()
        return {**base,
                **{f"d_{k}": v for k, v in self.delta.state_np().items()}}

    def export_npz(self, path):
        import numpy as np
        np.savez(path, **self.state_np())


# A2CLoss decides analytic-vs-Monte-Carlo entropy from this registry (PPO
# uses try/except instead); unregistered types would MC-estimate through
# rsample, which categoricals do not have.
try:
    from torchrl.modules.distributions import HAS_ENTROPY
    HAS_ENTROPY[TwoHeadMasked] = True
    HAS_ENTROPY[MultiHeadMasked] = True
    HAS_ENTROPY[MarketOnlyMultiHead] = True
    HAS_ENTROPY[CoupledMultiHeadMasked] = True  # bound subclasses register
    # themselves in build_actor_critic (the dict is keyed by exact class)
except ImportError:  # torchrl absent: the raw nets are still importable
    pass


def build_actor_critic(obs_dim, n_farmer, n_market, hidden1=512, hidden2=256,
                       v_hidden=256, device="cpu", residual_base="",
                       market_orders=1,
                       multi=False, n_hands=12, n_hand_task=None,
                       couple=False, market_only=False):
    """(actor, critic, actor_net, critic_net): TorchRL modules + raw nets.

    Construction order (actor layers, then critic layers) matches PolicyT's
    __init__, so under the same torch seed the initial weights are the same
    draws train_t.py would have made. residual_base wraps a frozen prior;
    multi=True adds the per-hand task heads (MultiHeadMasked, action
    (B, 2 + n_hands)); couple=True conditions the market head on the same
    turn's sampled farmer/hand intents (CoupledMultiHeadMasked).
    """
    from tensordict.nn import TensorDictModule, InteractionType
    from torchrl.modules import ProbabilisticActor, ValueOperator

    if couple and not multi:
        raise ValueError("couple=True requires multi=True: the coupling "
                         "conditions on hand-task intents")
    if market_only and not multi:
        raise ValueError("market_only=True requires multi=True: the hand "
                         "heads have to exist to be excluded")
    if market_only and couple:
        raise ValueError("market_only=True with couple=True is refused: the "
                         "coupling conditions the market head on the sampled "
                         "farmer/hand intents, and under a fixed farm tape "
                         "those intents are discarded, so it would condition "
                         "on noise")
    if couple and residual_base:
        raise ValueError("couple=True with a residual prior is not "
                         "implemented; the prior's market logits would be "
                         "conditioned inconsistently with its own training")
    if multi:
        if residual_base:
            actor_net = MultiResidualActor(
                residual_base, obs_dim, n_farmer, n_market, hidden1, hidden2,
                n_hands, n_hand_task).to(device)
        else:
            actor_net = MultiActorNet(obs_dim, n_farmer, n_market, hidden1,
                                      hidden2, n_hands, n_hand_task,
                                      couple=couple,
                                      market_orders=market_orders).to(device)
        logits_mod = TensorDictModule(
            actor_net, in_keys=["observation"],
            out_keys=["flogits", "mlogits", "hlogits"])
        dist_keys = {"flogits": "flogits", "mlogits": "mlogits",
                     "hlogits": "hlogits", "fmask": "farmer_mask",
                     "mmask": "market_mask", "hmask": "hand_mask"}
        if couple:
            # A per-build subclass binds the coupling PARAMETERS as class
            # attributes: ProbabilisticActor instantiates the distribution
            # from tensordict tensors only, and expanding the tables per
            # replay step would cost gigabytes. nn.Module.to() moves
            # parameter storage in place, so binding after .to(device) holds
            # the live tensors, and autograd tracks them through log_prob
            # regardless of how the reference arrived.
            dist_cls = type("CoupledMultiHeadMaskedBound",
                            (CoupledMultiHeadMasked,),
                            {"couple_f": actor_net.couple_f,
                             "couple_h": actor_net.couple_h})
            try:
                from torchrl.modules.distributions import HAS_ENTROPY
                HAS_ENTROPY[dist_cls] = True
            except ImportError:
                pass
        elif market_orders > 1:
            dist_cls = type("MultiOrderMultiHeadBound",
                            (MultiOrderMultiHead,),
                            {"slot_bias": actor_net.slot_bias,
                             "couple_m": actor_net.couple_m})
            try:
                from torchrl.modules.distributions import HAS_ENTROPY
                HAS_ENTROPY[dist_cls] = True
            except ImportError:
                pass
        elif market_only:
            dist_cls = MarketOnlyMultiHead
        else:
            dist_cls = MultiHeadMasked
    else:
        if residual_base:
            actor_net = ResidualActor(residual_base, obs_dim, n_farmer,
                                      n_market, hidden1, hidden2).to(device)
        else:
            actor_net = ActorNet(obs_dim, n_farmer, n_market,
                                 hidden1, hidden2).to(device)
        logits_mod = TensorDictModule(
            actor_net, in_keys=["observation"], out_keys=["flogits", "mlogits"])
        dist_keys = {"flogits": "flogits", "mlogits": "mlogits",
                     "fmask": "farmer_mask", "mmask": "market_mask"}
        dist_cls = TwoHeadMasked
    critic_net = CriticNet(obs_dim, v_hidden).to(device)

    actor = ProbabilisticActor(
        module=logits_mod,
        in_keys=dist_keys,
        out_keys=["action"],
        distribution_class=dist_cls,
        return_log_prob=True,
        log_prob_key="sample_log_prob",
        default_interaction_type=InteractionType.RANDOM,
    )
    critic = ValueOperator(critic_net, in_keys=["observation"],
                           out_keys=["state_value"])
    return actor, critic, actor_net, critic_net


def merged_state_dict(actor_net, critic_net):
    """PolicyT-compatible state_dict ({"model": ...} checkpoint payload)."""
    return {**actor_net.state_dict(), **critic_net.state_dict()}


def adapt_legacy_hand_head(model, new_bias=NEG):
    """Pad an append-only legacy hand vocabulary to the runtime width.

    ``new_bias=NEG`` preserves the old policy for evaluation.  Training may
    use a finite negative bias so supervised gradients can grow new tasks.
    """
    import actions as A

    if "hands.weight" not in model:
        return model, {"checkpoint_hand_tasks": None,
                       "runtime_hand_tasks": A.N_HAND_TASK,
                       "adapted": False}
    rows, hidden = model["hands.weight"].shape
    if rows % A.MAX_HANDS:
        raise ValueError(
            f"hand head has {rows} rows, not divisible by {A.MAX_HANDS} hands")
    old_tasks = rows // A.MAX_HANDS
    info = {"checkpoint_hand_tasks": old_tasks,
            "runtime_hand_tasks": A.N_HAND_TASK,
            "adapted": old_tasks != A.N_HAND_TASK}
    if old_tasks == A.N_HAND_TASK:
        return model, info
    if old_tasks > A.N_HAND_TASK:
        raise ValueError(
            f"checkpoint has {old_tasks} hand tasks but runtime has "
            f"{A.N_HAND_TASK}; shrinking is not safe")

    out = dict(model)
    weight, bias = model["hands.weight"], model["hands.bias"]
    new_weight = weight.new_zeros((A.MAX_HANDS * A.N_HAND_TASK, hidden))
    new_biases = bias.new_full(
        (A.MAX_HANDS * A.N_HAND_TASK,), float(new_bias))
    for hand in range(A.MAX_HANDS):
        old = slice(hand * old_tasks, (hand + 1) * old_tasks)
        new = slice(hand * A.N_HAND_TASK,
                    hand * A.N_HAND_TASK + old_tasks)
        new_weight[new] = weight[old]
        new_biases[new] = bias[old]
    out["hands.weight"], out["hands.bias"] = new_weight, new_biases
    info["new_task_bias"] = float(new_bias)
    return out, info


def adapt_legacy_observation(model, runtime_obs_dim):
    """Zero-pad append-only observation inputs, preserving old logits."""
    out = dict(model)
    widths = set()
    adapted = []
    for key, weight in model.items():
        if not (key.endswith("l1.weight") or key.endswith("v1.weight")):
            continue
        old_dim = weight.shape[1]
        widths.add(old_dim)
        if old_dim > runtime_obs_dim:
            raise ValueError(
                f"checkpoint {key} input {old_dim} exceeds runtime "
                f"observation width {runtime_obs_dim}")
        if old_dim == runtime_obs_dim:
            continue
        padded = weight.new_zeros((weight.shape[0], runtime_obs_dim))
        padded[:, :old_dim] = weight
        out[key] = padded
        adapted.append(key)
    return out, {"checkpoint_obs_dims": sorted(widths),
                 "runtime_obs_dim": int(runtime_obs_dim),
                 "adapted": bool(adapted), "adapted_keys": adapted}


def load_merged_state_dict(actor_net, critic_net, sd):
    """Load a PolicyT / train_t / rl-baseline Policy state_dict pair-wise.
    Tolerates rl/policy.py's `value` name for the critic output layer."""
    sd = dict(sd)
    if "value.weight" in sd and "vout.weight" not in sd:
        sd["vout.weight"], sd["vout.bias"] = sd.pop("value.weight"), sd.pop("value.bias")
    actor_keys = {k for k, _ in actor_net.named_parameters()}
    actor_sd = {k: v for k, v in sd.items() if k in actor_keys}
    if not actor_sd:
        raise ValueError(
            "checkpoint shares no actor keys with this network -- plain "
            "checkpoints do not load into a ResidualActor (or vice versa)")
    actor_net.load_state_dict(actor_sd, strict=len(actor_sd) == len(actor_keys))
    critic_keys = {k for k, _ in critic_net.named_parameters()}
    critic_sd = {k: v for k, v in sd.items() if k in critic_keys}
    critic_net.load_state_dict(critic_sd, strict=len(critic_sd) == len(critic_keys))
