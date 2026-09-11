# Validation status

Recorded during implementation on 2026-09-11. All exchange-order tests use an in-memory SDK double; **no real orders or funded-account checks were performed**.

Final local result: **39 tests passed, 2 skipped** (the two need the optional `live` extra). The execution tests are STONKFLY's, ported unchanged apart from names; passing them is what shows the money layer survived the port.

| Check | Observed result | What it does not establish |
| --- | --- | --- |
| Download + verify the public subset | 257 files, 8,192 cells × 7,879 frames plus centroids, every SHA-256 matches `sources.lock.json` | Completeness of ZAPBench or the accuracy of the segmentation |
| Fit | 2,048 cells, 7,182 training pairs, median one-step R² 0.925; browser refit on 545 cells R² 0.939 | Multi-step forecasting skill (ZAPBench's actual benchmark) |
| Population assignment | 256 light, 128 + 128 readout, 16 gate, 15 + 2 reinforcement; minimum light ratio 4.7 | That these cells are retinal, motor or dopaminergic |
| Sensory → reinforcement → checkpoint test | Reward pulse raises reward-cell activity and moves plastic edges; different inputs give different states; restore is exact; frozen weights stay unchanged | Useful credit assignment through the fixed decoder |
| Six accelerated observations on the offline fixture | SELL proposed every tick (right − left ≈ −0.07 to −0.38), all vetoed for lack of inventory | Any strategy |
| Two observations of actual Coinbase public BTC-USDC data | Bid 77,303.22; SELL proposed and vetoed; 56,909 of 64,748 plastic edges had moved | A realistic trading return |

## The browser tasks

Measured headlessly with a per-step trace of ball position versus paddle position.

- With the ball held still on one side, the readout answers clearly and repeatably (left ≈ −0.1σ, right ≈ +3.8σ) and the paddle goes to the correct side. The sensory path works.
- In live play the fish returns about **one ball in three** (typical minute: 6–11 returns, 15–22 misses). The ball-to-paddle correlation near the paddle varies between −0.2 and 0.6 from run to run.
- A/B over one-minute games, two each: **frozen weights versus learning made no measurable difference**; neither did physics sub-stepping nor the tracking ball machine. The limit is the model's response time to a moving stimulus, not the mapping.
- Bike: about 100 m per 30 s at 12 km/h with training wheels, a handful of kerb or parked-car hits, no falls. Dog: on the path roughly half the time, leash frequently taut.

## Reproduce

```sh
python -m pytest -q
python -m zebralink verify
python -m zebralink run --fixture --fast --steps 6 --out runs/check-fixture
python -m zebralink run --fast --steps 2 --out runs/check-public
```

Browser: serve `site/`, open `tasks.html?task=tabletennis`, and read `window.__trace` (ball x, paddle x, ball z, control, gate per model step) or call `window.__ZEBRA.W.hold(x)` to park the ball. `window.__ZEBRA.P.frozen = true` freezes the rule.

Before claiming learned performance, implement the held-out replay and controls described in [the model](model.md). This repository provides a functioning experimental loop and a scoreboard, not that empirical result.
