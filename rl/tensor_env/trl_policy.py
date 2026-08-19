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


def load_actor_state(path):
    """Actor-half state dict from an exported weights.npz or a checkpoint."""
    import numpy as np
    if path.endswith(".npz"):
        w = dict(np.load(path))
        sd = {"l1.weight": w["l1w"], "l1.bias": w["l1b"],
              "l2.weight": w["l2w"], "l2.bias": w["l2b"],
              "farmer.weight": w["fw"], "farmer.bias": w["fb"],
              "market.weight": w["mw"], "market.bias": w["mb"]}
        return {k: torch.as_tensor(v) for k, v in sd.items()}
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


class MultiActorNet(ActorNet):
    """ActorNet + one task head per hand slot. The hand-head bias starts at
    +auto_bias on AUTO, so the untrained policy behaves like the classic
    scheduler and learns deviations (the action-space analog of the
    residual start; Kilo used the same trick with IDLE -- AUTO is a
    competent default where IDLE is a strike)."""

    def __init__(self, obs_dim, n_farmer, n_market, hidden1=512, hidden2=256,
                 n_hands=12, n_hand_task=7, auto_bias=2.5):
        super().__init__(obs_dim, n_farmer, n_market, hidden1, hidden2)
        self.n_hands, self.n_hand_task = n_hands, n_hand_task
        self.hands = _ortho(nn.Linear(hidden2, n_hands * n_hand_task), 1e-4)
        with torch.no_grad():
            self.hands.bias.view(n_hands, n_hand_task)[:, 0] = auto_bias

    def forward(self, x):
        h = torch.relu(self.l1(x))
        h = torch.relu(self.l2(h))
        hl = self.hands(h).view(*x.shape[:-1], self.n_hands, self.n_hand_task)
        return self.farmer(h), self.market(h), hl

    def state_np(self):
        out = super().state_np()
        out["hw"] = self.hands.weight.detach().cpu().float().numpy()
        out["hb"] = self.hands.bias.detach().cpu().float().numpy()
        return out


class MultiResidualActor(nn.Module):
    """Frozen two-head prior + trainable multi-head delta: farmer/market
    logits are prior + correction, hand logits come from the delta alone
    (the prior never had hands -- they start at the AUTO bias)."""

    def __init__(self, base_path, obs_dim, n_farmer, n_market,
                 hidden1=512, hidden2=256, n_hands=12, n_hand_task=7):
        super().__init__()
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
except ImportError:  # torchrl absent: the raw nets are still importable
    pass


def build_actor_critic(obs_dim, n_farmer, n_market, hidden1=512, hidden2=256,
                       v_hidden=256, device="cpu", residual_base="",
                       multi=False, n_hands=12, n_hand_task=7):
    """(actor, critic, actor_net, critic_net): TorchRL modules + raw nets.

    Construction order (actor layers, then critic layers) matches PolicyT's
    __init__, so under the same torch seed the initial weights are the same
    draws train_t.py would have made. residual_base wraps a frozen prior;
    multi=True adds the per-hand task heads (MultiHeadMasked, action
    (B, 2 + n_hands)).
    """
    from tensordict.nn import TensorDictModule, InteractionType
    from torchrl.modules import ProbabilisticActor, ValueOperator

    if multi:
        if residual_base:
            actor_net = MultiResidualActor(
                residual_base, obs_dim, n_farmer, n_market, hidden1, hidden2,
                n_hands, n_hand_task).to(device)
        else:
            actor_net = MultiActorNet(obs_dim, n_farmer, n_market, hidden1,
                                      hidden2, n_hands, n_hand_task).to(device)
        logits_mod = TensorDictModule(
            actor_net, in_keys=["observation"],
            out_keys=["flogits", "mlogits", "hlogits"])
        dist_keys = {"flogits": "flogits", "mlogits": "mlogits",
                     "hlogits": "hlogits", "fmask": "farmer_mask",
                     "mmask": "market_mask", "hmask": "hand_mask"}
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
