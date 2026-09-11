"""Baseline-centered anti-Hebbian eligibility model.

Adaptation of Huang, Luo et al. 2024, Appendix equations 3.2--3.5, as used in
STONKFLY (MIT), with one change: rate bins are imaging frames (about one second)
instead of 10 ms spike bins, so the bin guard admits up to 2 s. Rates are
dF/F-derived proxies, not spikes. u/w are deviations from each fitted edge's
baseline weight. Bounds and trace constants are declared model choices.
"""

import math

import numpy as np

PARAMETERS = {
    "trace_pre_seconds": 1.0,
    "trace_dan_seconds": 1.0,
    "memory_decay_seconds": 1800.0,
    "weight_filter_seconds": 0.05,
    "minimum_fraction": 0.1,
    "maximum_fraction": 2.0,
    "maximum_rate_bin_seconds": 2.0,
    "source": "https://doi.org/10.1038/s41586-024-07819-w",
    "interpretation": "Centered rate-rule adaptation on fitted light->readout edges of a linear zebrafish activity model. Rates are dF/F proxies at imaging-frame resolution. Unvalidated extension.",
}


def advance(y_pre, y_dan, u, w, pre_hz, dan_hz, gain, dt_seconds, eta, learning=True, frozen=False):
    """Mutate traces and efficacy deviations with constant rates for one bin."""
    if not math.isfinite(dt_seconds) or dt_seconds <= 0 or dt_seconds > PARAMETERS["maximum_rate_bin_seconds"]:
        raise ValueError("Rate bins must be 0--2 s")
    h = dt_seconds
    p = PARAMETERS
    ak = math.exp(-h / p["trace_pre_seconds"])
    ad = math.exp(-h / p["trace_dan_seconds"])
    kmid = y_pre * math.sqrt(ak) + pre_hz * (1 - math.sqrt(ak))
    dmid = y_dan * math.sqrt(ad) + dan_hz * (1 - math.sqrt(ad))
    y_pre[:] = y_pre * ak + pre_hz * (1 - ak)
    y_dan[:] = y_dan * ad + dan_hz * (1 - ad)
    if frozen:
        return
    drive = (
        eta * (pre_hz * (gain.T @ dmid) - (gain.T @ dan_hz) * kmid)
        if learning
        else np.zeros_like(u)
    )
    tu = p["memory_decay_seconds"]
    tw = p["weight_filter_seconds"]
    eu = math.exp(-h / tu)
    ew = math.exp(-h / tw)
    c = tu / (tu - tw) * (eu - ew)
    old_u = u.copy()
    u[:] = old_u * eu + drive * tu * (-math.expm1(-h / tu))
    w[:] = w * ew + old_u * c + drive * tu * (-math.expm1(-h / tw) - c)
    lo = p["minimum_fraction"] - 1
    hi = p["maximum_fraction"] - 1
    np.clip(u, lo, hi, out=u)
    np.clip(w, lo, hi, out=w)
