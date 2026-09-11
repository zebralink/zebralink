"""Population assignment from data and centroids. Engineered, disclosed, fixed.

Nothing here is an atlas registration. Axes follow the ZAPBench centroid frame:
x spans ~500 um (left/right), y spans ~820 um (long, rostro-caudal), z ~250 um.
Which end of y is rostral is assumed from the release figures (head at low y);
the decoder is symmetric in x, so a wrong rostral guess changes which cells
are read, not the buy/sell bias.
"""

import numpy as np

from .common import condition_slices


def _top(score, k, exclude=()):
    order = np.argsort(-score)
    mask = np.ones(len(score), bool)
    mask[list(exclude)] = False
    return order[mask[order]][:k]


def assign(X, xyz, n_visual=256, n_motor_side=128, n_gate=16, n_reward=15, n_aversive=2, seed=20240930):
    """X: frames x M dF/F. Returns index arrays into the M columns plus a report."""
    c = condition_slices()
    var = {k: X[s].var(axis=0) for k, s in c.items()}
    eps = 1e-6
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    midline = float(np.median(x))
    caudal = y >= np.quantile(y, 2 / 3)
    middle = (y > np.quantile(y, 1 / 3)) & ~caudal

    # Light-responsive cells: variance during full-field flashes relative to darkness.
    light = (var["flash"] + eps) / (var["dark"] + eps)
    visual = _top(light, n_visual)

    # Turning-responsive caudal cells, split by side of the midline.
    turn = var["turning"] * caudal
    left_pool = np.flatnonzero(caudal & (x < midline))
    right_pool = np.flatnonzero(caudal & (x >= midline))
    left = left_pool[_top(turn[left_pool], n_motor_side, exclude=[i for i, g in enumerate(left_pool) if g in set(visual)])]
    right = right_pool[_top(turn[right_pool], n_motor_side, exclude=[i for i, g in enumerate(right_pool) if g in set(visual)])]
    used = set(visual) | set(left) | set(right)
    gate_pool = np.array([i for i in np.flatnonzero(caudal) if i not in used])
    gate = gate_pool[_top(X[:, gate_pool].mean(axis=0), n_gate)]
    used |= set(gate)

    # Reinforcement targets: fixed seeded picks from the middle third. Engineered.
    rng = np.random.default_rng(seed)
    pool = np.array([i for i in np.flatnonzero(middle) if i not in used])
    pick = rng.choice(pool, n_reward + n_aversive, replace=False)
    reward, aversive = pick[:n_reward], pick[n_reward:]

    for name, arr, need in [("left", left, min(8, n_motor_side)), ("right", right, min(8, n_motor_side)), ("gate", gate, 1), ("visual", visual, min(16, n_visual))]:
        if len(arr) < need:
            raise RuntimeError(f"Population too small: {name}")

    # Display adapter: rank positions of light cells inside the population -> chart UV.
    def ranks(v):
        r = np.empty(len(v)); r[np.argsort(v)] = np.arange(len(v)); return r / max(1, len(v) - 1)
    uv = np.stack([ranks(x[visual]), ranks(y[visual])], 1).astype(np.float32)

    pops = {"visual": visual, "left": left, "right": right, "gate": gate, "reward": reward, "aversive": aversive}
    pops = {k: np.asarray(v, dtype=np.int64) for k, v in pops.items()}
    report = {
        "method": "flash/dark variance ratio -> light cells; caudal-third turning variance split at the x midline -> left/right readout; caudal mean activity -> gate; seeded middle-third picks -> reward/aversive. Fixed before any trading; not atlas-registered.",
        "midline_x_um": midline,
        "sizes": {k: int(len(v)) for k, v in pops.items()},
        "light_ratio_min_selected": float(light[visual].min()),
        "assumed_rostral": "low y",
    }
    return pops, uv, report
