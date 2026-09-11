"""Local verified ZAPBench subset and the trained model location."""

import hashlib
import json
import os
from pathlib import Path

DATA = Path(os.environ.get("ZEBRALINK_DATA", "data")).resolve() / "zapbench"
MODEL = DATA / "model.npz"

BUCKET = "https://storage.googleapis.com/zapbench-release/volumes/20240930"
TIME_CHUNKS = 16  # 7879 frames / 512
NEURON_BLOCKS = (0, 9, 18, 27, 36, 45, 54, 63, 72, 81, 90, 99, 108, 117, 126, 135)
CHUNK = 512
FRAMES = 7879
NEURONS_TOTAL = 71721

# ZAPBench condition boundaries (google-research/zapbench constants.py, Apache-2.0).
CONDITION_OFFSETS = (0, 649, 2422, 3078, 3735, 5047, 5638, 6623, 7279, 7879)
CONDITION_NAMES = (
    "gain", "dots", "flash", "taxis", "turning", "position", "open loop", "rotation", "dark",
)
CONDITIONS_HOLDOUT = (3,)
CONDITION_PADDING = 1


def digest(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def condition_slices():
    out = {}
    for i, name in enumerate(CONDITION_NAMES):
        a, b = CONDITION_OFFSETS[i] + CONDITION_PADDING, CONDITION_OFFSETS[i + 1] - CONDITION_PADDING
        out[name] = slice(a, b)
    return out
