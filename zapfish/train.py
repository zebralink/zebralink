"""Select cells, assign populations, fit the linear activity model."""

import json

import numpy as np

from .data import load_centroids, load_traces, verify
from .neural import anatomy, model
from .neural.common import DATA, MODEL, save_json


def select_cells(X, n):
    """Spread across the downloaded blocks: equal share per block, highest variance within."""
    M = X.shape[1]
    blocks = 16
    per = n // blocks
    v = X.var(axis=0)
    chosen = []
    for b in range(blocks):
        s = slice(b * (M // blocks), (b + 1) * (M // blocks))
        local = np.argsort(-v[s])[:per] + s.start
        chosen.append(local)
    return np.sort(np.concatenate(chosen))


def train(cells=2048, ridge=3.0):
    verified = verify()
    X, gidx = load_traces()
    keep = select_cells(X, cells)
    X = np.ascontiguousarray(X[:, keep])
    gidx = gidx[keep]
    labels, xyz = load_centroids(gidx)
    pops, uv, report = anatomy.assign(X, xyz)
    fit = model.fit(X, pops, uv, gidx, labels, ridge=ridge, out=MODEL)
    summary = {"dataset": verified, "cells": int(len(keep)), "populations": report, "fit": fit, "model": str(MODEL)}
    save_json(DATA / "model.report.json", summary)
    return summary
