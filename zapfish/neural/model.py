"""Linear whole-brain activity model fitted to one real zebrafish (ZAPBench).

x[t+1] = A [x[t], x[t-1], x[t-2]] + b + drive. A is ridge-fitted on the recorded
dF/F traces of M cells spread across the brain (ZAPBench "linear" baseline
family). Chart luminance enters as drive on light-responsive cells; P&L pulses
enter as drive on reward/aversive cells; a fixed left/right readout decodes.

This is a statistical forecaster of recorded activity, not a connectome, not a
spiking model, and not a claim that the fish sees or wants anything.
"""

import hashlib
import json

import numpy as np

from . import rule
from .common import CONDITIONS_HOLDOUT, CONDITION_OFFSETS, CONDITION_PADDING, MODEL, digest

LAGS = 3


def _windows(T):
    """Training (t, t+1) pairs inside non-holdout conditions, respecting padding."""
    idx = []
    for i in range(len(CONDITION_OFFSETS) - 1):
        if i in CONDITIONS_HOLDOUT:
            continue
        a = CONDITION_OFFSETS[i] + CONDITION_PADDING + LAGS - 1
        b = CONDITION_OFFSETS[i + 1] - CONDITION_PADDING - 1
        idx.extend(range(a, b))
    return np.asarray([t for t in idx if 0 <= t < T - 1], dtype=np.int64)


def fit(X, pops, uv, gidx, labels, ridge=3.0, out=MODEL):
    T, M = X.shape
    t = _windows(T)
    F = np.concatenate([X[t - k] for k in range(LAGS)] + [np.ones((len(t), 1), np.float32)], 1)
    Y = X[t + 1]
    G = F.T.astype(np.float64) @ F.astype(np.float64)
    G[np.diag_indices(LAGS * M)] += ridge
    W = np.linalg.solve(G, F.T.astype(np.float64) @ Y.astype(np.float64))  # (LAGS*M+1) x M
    A = W[:-1].T.astype(np.float32)  # M x LAGS*M
    b = W[-1].astype(np.float32)
    pred = F @ W.astype(np.float32)
    resid = Y - pred
    r2 = 1 - resid.var(axis=0) / (Y.var(axis=0) + 1e-9)
    lo = X.min(axis=0) - 0.25
    hi = X.max(axis=0) + 0.25
    # Plastic edges: lag-0 weights from light cells into readout cells that exist
    # in the fit (nonzero above a small magnitude). Reward compartment = edges into
    # the right group, aversive compartment = edges into the left group.
    rows = np.concatenate([pops["right"], pops["left"]])
    comp = np.concatenate([np.zeros(len(pops["right"]), np.int64), np.ones(len(pops["left"]), np.int64)])
    R, C = np.meshgrid(rows, pops["visual"], indexing="ij")
    base = A[R, C]
    keep = np.abs(base) > 1e-4
    edges_r, edges_c = R[keep], C[keep]
    edge_comp = np.repeat(comp[:, None], len(pops["visual"]), 1)[keep]
    edge_pre = np.repeat(np.arange(len(pops["visual"]))[None, :], len(rows), 0)[keep]
    np.savez(
        out, A=A, b=b, lo=lo, hi=hi, r2=r2.astype(np.float32), gidx=gidx, labels=labels, uv=uv,
        edges_r=edges_r, edges_c=edges_c, edge_comp=edge_comp, edge_pre=edge_pre, edge_base=base[keep],
        **{f"pop_{k}": v for k, v in pops.items()},
    )
    return {
        "cells": int(M), "lags": LAGS, "train_pairs": int(len(t)), "ridge": ridge,
        "r2_median_one_step": float(np.median(r2)), "plastic_edges": int(keep.sum()),
        "holdout_conditions": list(CONDITIONS_HOLDOUT),
    }


class FishBrain:
    def __init__(self, settings, path=MODEL):
        a = np.load(path, allow_pickle=False)
        for k in a.files:
            setattr(self, k, a[k])
        self.s = settings
        self.n = len(self.b)
        if self.A.shape != (self.n, LAGS * self.n):
            raise ValueError("Model shape mismatch")
        self.pops = {k[4:]: getattr(self, k) for k in a.files if k.startswith("pop_")}
        self.E = len(self.edges_r)
        self.model_sha256 = hashlib.sha256(self.A.tobytes() + self.b.tobytes()).hexdigest()
        self.weights_frozen = False
        # per-compartment DAN groups: 0 reward -> right edges, 1 aversive -> left edges
        self.dan = np.concatenate([self.pops["reward"], self.pops["aversive"]])
        dan_comp = np.concatenate([np.zeros(len(self.pops["reward"]), np.int64), np.ones(len(self.pops["aversive"]), np.int64)])
        gain = np.zeros((len(self.dan), self.E), np.float32)
        for c in (0, 1):
            m = dan_comp == c
            gain[np.ix_(m, self.edge_comp == c)] = 1.0 / m.sum()
        self.gain = gain
        self.reset()

    def reset(self, keep_memory=False):
        self.h = np.zeros((LAGS, self.n), np.float32)
        if not keep_memory:
            self.u = np.zeros(self.E, np.float32)
            self.w = np.zeros(self.E, np.float32)
            self.y_pre = np.zeros(self.E, np.float32)  # per plastic edge, like the fly rule
            self.y_dan = np.zeros(len(self.dan), np.float32)
        self.frames = 0

    def step(self, drive, learning=True):
        """One imaging frame. drive: length-n additive input (dF/F units)."""
        A = self.A
        if self.E:
            A[self.edges_r, self.edges_c] = self.edge_base * (1 + self.w)
        x = A @ self.h.reshape(-1) + self.b + drive
        np.clip(x, self.lo, self.hi, out=x)
        self.h = np.roll(self.h, 1, axis=0)
        self.h[0] = x
        self.frames += 1
        pre = (np.maximum(x[self.pops["visual"]], 0) * 20.0)[self.edge_pre]
        dan = np.maximum(x[self.dan], 0) * 20.0
        rule.advance(
            self.y_pre, self.y_dan, self.u, self.w, pre, dan, self.gain,
            self.s.frame_seconds, self.s.plasticity_gain,
            learning=learning, frozen=self.weights_frozen,
        )
        return x

    def memory(self):
        changed = int(np.count_nonzero(np.abs(self.w) > 1e-9))
        return {
            "plastic_edges": int(self.E),
            "changed_edges": changed,
            "mean_abs_deviation": float(np.abs(self.w).mean()) if self.E else 0.0,
            "max_abs_deviation": float(np.abs(self.w).max()) if self.E else 0.0,
            "saturated_fraction": float(np.mean(np.abs(self.w) >= 0.9 * (rule.PARAMETERS["maximum_fraction"] - 1))) if self.E else 0.0,
            "rule": rule.PARAMETERS,
        }

    def checkpoint(self, path):
        np.savez(path, h=self.h, u=self.u, w=self.w, y_pre=self.y_pre, y_dan=self.y_dan,
                 frames=np.asarray([self.frames]), model=np.frombuffer(bytes.fromhex(self.model_sha256), np.uint8))

    def restore(self, path):
        a = np.load(path, allow_pickle=False)
        if a["model"].tobytes().hex() != self.model_sha256:
            raise RuntimeError("Checkpoint belongs to a different model")
        for k in ["h", "u", "w", "y_pre", "y_dan"]:
            v = a[k]
            if v.shape != getattr(self, k).shape:
                raise RuntimeError("Checkpoint shape mismatch: " + k)
            setattr(self, k, v.astype(np.float32).copy())
        self.frames = int(a["frames"][0])

    def report(self):
        return {
            "cells": int(self.n), "lags": LAGS, "model_sha256": self.model_sha256,
            "populations": {k: int(len(v)) for k, v in self.pops.items()},
            "plastic_edges": int(self.E),
            "r2_median_one_step": float(np.median(self.r2)),
        }
