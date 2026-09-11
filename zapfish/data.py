"""Fetch the public ZAPBench trace subset and verify it against a lock file."""

import concurrent.futures as cf
import json
import os
import urllib.request
from pathlib import Path

import numpy as np

from .neural.common import (
    BUCKET, CHUNK, DATA, FRAMES, NEURON_BLOCKS, NEURONS_TOTAL, TIME_CHUNKS, sha,
)

PACKAGE = Path(__file__).with_name("neural")
LOCK = PACKAGE / "sources.lock.json"


def chunk_files():
    return {
        f"traces/c_{t}_{n}.bin": f"{BUCKET}/traces/c/{t}/{n}"
        for t in range(TIME_CHUNKS)
        for n in NEURON_BLOCKS
    } | {"centroids.json": f"{BUCKET}/segmentation/dataframe_centroids.json"}


def _fetch(item):
    name, url = item
    path = DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return name, False
    tmp = path.with_suffix(path.suffix + ".partial")
    with urllib.request.urlopen(url, timeout=120) as r, tmp.open("wb") as o:
        o.write(r.read())
    os.replace(tmp, path)
    return name, True


def prepare():
    files = chunk_files()
    with cf.ThreadPoolExecutor(8) as ex:
        fetched = sum(new for _, new in ex.map(_fetch, files.items()))
    print(json.dumps({"downloaded": fetched, "files": len(files)}), flush=True)
    if not LOCK.exists():
        # First preparation on this checkout pins what was downloaded. Commit it.
        lock = {name: {"url": url, "sha256": sha(DATA / name)} for name, url in files.items()}
        LOCK.write_text(json.dumps(lock, indent=2) + "\n")
        print("Wrote", LOCK, flush=True)
    print(json.dumps(verify()), flush=True)


def verify():
    if not LOCK.exists():
        raise RuntimeError("Run prepare first; no source lock present")
    lock = json.loads(LOCK.read_text())
    if set(lock) != set(chunk_files()):
        raise RuntimeError("Lock file does not match the configured subset")
    for name, info in lock.items():
        path = DATA / name
        if not path.exists():
            raise RuntimeError("Missing source: " + name)
        if sha(path) != info["sha256"]:
            raise RuntimeError("Source checksum mismatch: " + name)
    return {
        "release": "ZAPBench 20240930 traces (public)",
        "neurons_total": NEURONS_TOTAL,
        "neurons_downloaded": CHUNK * len(NEURON_BLOCKS),
        "frames": FRAMES,
        "sources_verified": True,
    }


def load_traces():
    """Return (X, global_index): X is frames x M float32, dF/F traces."""
    M = CHUNK * len(NEURON_BLOCKS)
    X = np.empty((TIME_CHUNKS * CHUNK, M), dtype=np.float32)
    for t in range(TIME_CHUNKS):
        for j, n in enumerate(NEURON_BLOCKS):
            a = np.fromfile(DATA / f"traces/c_{t}_{n}.bin", dtype="<f4").reshape(CHUNK, CHUNK)
            X[t * CHUNK:(t + 1) * CHUNK, j * CHUNK:(j + 1) * CHUNK] = a
    X = X[:FRAMES]
    if not np.isfinite(X).all():
        raise RuntimeError("Nonfinite trace values")
    gidx = np.concatenate([np.arange(n * CHUNK, (n + 1) * CHUNK) for n in NEURON_BLOCKS])
    return X, gidx


def load_centroids(gidx):
    d = json.loads((DATA / "centroids.json").read_text())
    keys = [str(int(i)) for i in gidx]
    label = np.array([d["label"][k] for k in keys], dtype=np.int64)
    if not np.array_equal(label, gidx + 1):
        raise RuntimeError("Centroid rows are not aligned with trace columns")
    xyz = np.stack(
        [np.array([d[f"centroid_{ax}"][k] for k in keys], dtype=np.float32) for ax in "xyz"], 1
    )
    return label, xyz
