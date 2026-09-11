"""Only chart pixels and engineered reinforcement enter the model. No market policy."""

import hashlib

import numpy as np

from .model import FishBrain
from .sensory import retinal_samples


class Decoder:
    def __init__(self, brain, threshold, gate_level):
        self.left = brain.pops["left"]
        self.right = brain.pops["right"]
        self.gate = brain.pops["gate"]
        self.threshold = threshold
        self.gate_level = gate_level
        self.identities = {
            k: [int(brain.labels[i]) for i in getattr(self, k)] for k in ["left", "right", "gate"]
        }

    def decode(self, window):
        """window: frames x n dF/F. Mean rates avoid population-size bias."""
        left = float(window[:, self.left].mean())
        right = float(window[:, self.right].mean())
        difference = right - left
        gate = float(window[:, self.gate].max())
        side = (
            "HOLD"
            if gate < self.gate_level or abs(difference) < self.threshold
            else "BUY"
            if difference > 0
            else "SELL"
        )
        return {
            "side": side,
            "left_dff": left,
            "right_dff": right,
            "difference_dff": difference,
            "gate_peak_dff": gate,
            "cell_ids": self.identities,
        }


class FishController:
    def __init__(self, settings, model_path=None):
        self.s = settings
        self.brain = FishBrain(settings) if model_path is None else FishBrain(settings, model_path)
        self.brain.weights_frozen = not settings.learning
        self.decoder = Decoder(self.brain, settings.decoder_threshold, settings.gate_level)

    def observe(self, rgb, reinforcement):
        if reinforcement not in ("none", "reward", "aversive"):
            raise ValueError("Unknown reinforcement")
        b = self.brain
        lum = retinal_samples(rgb, b.uv)
        window = np.zeros((self.s.neural_frames, b.n), np.float32)
        delivered = 0
        for f in range(self.s.neural_frames):
            drive = np.zeros(b.n, np.float32)
            drive[b.pops["visual"]] = self.s.input_gain * (lum - 0.5)
            if reinforcement != "none" and f < self.s.pulse_frames:
                drive[b.pops[reinforcement]] += self.s.pulse_amplitude
                delivered += 1
            window[f] = b.step(drive, learning=self.s.learning)
        pos = np.maximum(window, 0)
        return {
            **self.decoder.decode(window),
            "frames": int(self.s.neural_frames),
            "brain_frames": int(b.frames),
            "stimulus": reinforcement,
            "stimulus_frames": delivered,
            "reward_dff": float(window[:, b.pops["reward"]].mean()),
            "aversive_dff": float(window[:, b.pops["aversive"]].mean()),
            "visual_dff": float(window[:, b.pops["visual"]].mean()),
            "active_fraction": float((window[-1] > 0.1).mean()),
            "total_activity": float(pos.sum()),
            "state_sha256": hashlib.sha256(window.tobytes()).hexdigest(),
            "input_sha256": hashlib.sha256(np.asarray(rgb).tobytes()).hexdigest(),
            "memory": b.memory(),
        }

    def save(self, path):
        self.brain.checkpoint(path)

    def restore(self, path):
        self.brain.restore(path)
