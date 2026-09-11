import numpy as np
import pytest

from zebralink.config import Settings
from zebralink.neural import model
from zebralink.neural.controller import Decoder, FishController
from zebralink.neural.rule import advance
from zebralink.reinforcement import reinforcement


class FakeBrain:
    def __init__(self):
        self.pops = {"left": np.array([0]), "right": np.array([1]), "gate": np.array([2])}
        self.labels = np.array([10, 20, 30])


def test_fixed_readout_decoder():
    d = Decoder(FakeBrain(), 0.02, 0.15)
    w = np.zeros((4, 3), np.float32)
    assert d.decode(w)["side"] == "HOLD"
    w[:, 1] = 0.5; w[:, 2] = 0.3
    assert d.decode(w)["side"] == "BUY"
    w[:, 1] = 0; w[:, 0] = 0.5
    assert d.decode(w)["side"] == "SELL"
    w[:, 2] = 0.0  # gate silent -> hold even with a large difference
    assert d.decode(w)["side"] == "HOLD"


@pytest.mark.parametrize("equity,expected", [("100.03", "reward"), ("99.97", "aversive"), ("100.001", "none")])
def test_explicit_feedback(equity, expected):
    assert reinforcement(equity, "100", ".01")[0] == expected


def trace_protocol(order, frozen=False):
    k = np.zeros(2); d = np.zeros(1); u = np.zeros(2); w = np.zeros(2); gain = np.ones((1, 2))
    for phase in order:
        for _ in range(3):
            kh = np.array([20.0, 0.0]) if phase == "cue" else np.zeros(2)
            dh = np.array([30.0]) if phase == "reinforce" else np.zeros(1)
            advance(k, d, u, w, kh, dh, gain, 0.9, 0.001, frozen=frozen)
    return w


def test_memory_rule_temporal_specificity_at_frame_resolution():
    paired = trace_protocol(["cue", "reinforce"])
    reverse = trace_protocol(["reinforce", "cue"])
    assert paired[0] < 0 and reverse[0] > 0
    assert paired[1] == 0 and reverse[1] == 0
    assert np.array_equal(trace_protocol(["cue", "reinforce"], True), np.zeros(2))


def synthetic_model(tmp_path, M=160, T=800, seed=1):
    rng = np.random.default_rng(seed)
    A = rng.normal(0, 0.05, (M, M)); A[np.diag_indices(M)] += 0.7
    X = np.zeros((T, M), np.float32); X[0] = rng.normal(0, 0.2, M)
    for t in range(1, T):
        X[t] = np.clip(A @ X[t - 1] + rng.normal(0, 0.05, M), -0.5, 2.0)
    xyz = rng.normal(0, 100, (M, 3)).astype(np.float32)
    # small fake conditions so anatomy.assign has something to split on
    import zebralink.neural.common as c
    old = (c.CONDITION_OFFSETS, model.CONDITION_OFFSETS)
    offs = tuple(int(x) for x in np.linspace(0, T, 10))
    c.CONDITION_OFFSETS = offs; model.CONDITION_OFFSETS = offs
    try:
        from zebralink.neural import anatomy
        pops, uv, _ = anatomy.assign(X, xyz, n_visual=8, n_motor_side=4, n_gate=2, n_reward=3, n_aversive=1)
        out = tmp_path / "model.npz"
        rep = model.fit(X, pops, uv, np.arange(M), np.arange(M) + 1, ridge=1.0, out=out)
    finally:
        c.CONDITION_OFFSETS, model.CONDITION_OFFSETS = old
    return out, rep


def test_sensory_reinforcement_checkpoint_roundtrip(tmp_path):
    path, rep = synthetic_model(tmp_path)
    assert rep["plastic_edges"] > 0
    s = Settings(neural_frames=4, pulse_frames=2)
    c = FishController(s, model_path=path)
    white = np.full((180, 320, 3), 255, np.uint8)
    black = np.zeros((180, 320, 3), np.uint8)
    for _ in range(3):
        c.observe(white, "none")
    c.save(tmp_path / "before.npz")
    w_before = c.brain.w.copy()
    reward = c.observe(white, "reward")
    assert reward["stimulus_frames"] == 2 and reward["memory"]["changed_edges"] > 0
    assert reward["reward_dff"] > 0
    w_reward = c.brain.w.copy()
    assert not np.array_equal(w_before, w_reward)
    # different input -> different state
    assert c.observe(black, "none")["state_sha256"] != c.observe(white, "none")["state_sha256"]
    # restore returns the exact pre-reward memory; frozen leaves it unchanged
    c.restore(tmp_path / "before.npz")
    assert np.array_equal(c.brain.w, w_before)
    c.brain.weights_frozen = True
    c.observe(white, "aversive")
    assert np.array_equal(c.brain.w, w_before)
    assert np.isfinite(c.brain.h).all()
