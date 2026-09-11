# What is actually modeled

This is a statistical whole-brain activity model driving fixed readouts. It is not a connectome, not a spiking simulation, not a calibrated retina, and not a trading strategy. No LLM selects actions. No price rule overrides the neural proposal.

## Data

[ZAPBench](https://google-research.github.io/zapbench/) release 20240930: one larval zebrafish, whole-brain light-sheet calcium imaging, **71,721 segmented neurons × 7,879 frames** at roughly one volume per second, with nine labelled stimulus conditions (gain, dots, flash, taxis, turning, position, open loop, rotation, dark; boundaries from the ZAPBench `constants.py`). We download 16 spatial blocks of 512 neurons (8,192 cells) for all frames, plus the segmentation centroids, as raw zarr chunks over HTTPS. `zapfish/neural/sources.lock.json` pins every file's SHA-256; `prepare` and `verify` check them.

## Cell selection and populations

From the 8,192 downloaded cells, `train` keeps the 128 highest-variance cells in each block (2,048). Populations are then assigned from the data and the centroids, before any trading (`zapfish/neural/anatomy.py`):

| Population | Rule | Size |
| --- | --- | --- |
| light | highest variance ratio of the *flash* condition over the *dark* condition | 256 |
| left / right readout | caudal third by centroid; highest variance during *turning*; split at the x midline | 128 + 128 |
| gate | caudal, highest mean activity, disjoint from the above | 16 |
| reward / aversive | seeded picks from the middle third | 15 + 2 |

The centroid frame's long axis is taken as rostro-caudal with the head at low y, from the release figures; it is not an atlas registration. The reward/aversive sets mirror the fly's 15 PAM11 and 2 PPL101 cells in count only. They are engineered assignments.

## Dynamics

`x[t+1] = A · [x[t], x[t−1], x[t−2]] + b + drive`, with `A` (2,048 × 6,144) fitted by ridge regression (λ = 3) on 7,182 frame pairs inside the eight training conditions; the *taxis* condition is held out as ZAPBench does. Median one-step R² is 0.92. States are clipped to each cell's recorded range plus a margin. The browser build refits the same model on the 545 population cells only (R² 0.94, float16, 1.8 MB).

## What the fish sees

A 320 × 180 RGB chart of past prices (locally rendered; no balances or P&L) is sampled at the light cells' screen positions and converted to linear luminance; `drive = 0.35 · (luminance − 0.5)` per cell. In the engine the positions are anatomical ranks. In the browser tasks each light cell is placed by the side of the readout its fitted weights drive (u) and its anatomical rank (v), and sees a 9 × 9 patch. Both are declared display adapters, the way the fly's inferred retina projection was, not zebrafish vision.

Each market observation advances 8 model frames (about 7 s of fish time) regardless of wall time. The browser tasks step at 16 Hz. This is a compressed clock, not real-time physiology.

## How activity becomes an order

Over the observation window: mean ΔF/F of the right readout group minus the left. In the browser both groups are first z-scored against their recorded mean and spread (the left group is twice as variable as the right) and the difference is centred on its own 30-second running average, otherwise the recording's resting left bias pins the controls.

| Measurement | Proposal |
| --- | --- |
| difference ≥ 0.02 with any gate cell above 0.10 | Buy |
| difference ≤ −0.02 with any gate cell above 0.10 | Sell |
| otherwise | Hold |

The guard can reject a proposal for price, budget, inventory, timing or account-state reasons. It cannot replace it. Persistent network bias becomes persistent one-sided proposals; in every run so far the engine has proposed SELL, which the guard vetoes for lack of inventory. Do not read that as market insight.

## Reinforcement and plasticity

Equity change of at least +0.01 USDC per observation schedules a 2-frame, 0.5 ΔF/F-equivalent drive into the 15 reward cells; −0.01 or less into the 2 aversive cells. The rule is STONKFLY's baseline-centred anti-Hebbian eligibility model (adapted from [Huang, Luo et al., 2024](https://doi.org/10.1038/s41586-024-07819-w)), run at imaging-frame resolution instead of 10 ms bins, on the 64,748 non-trivial lag-0 weights from light cells into readout cells. Reward cells modulate edges into the right group, aversive cells edges into the left group: a declared compartment choice, not anatomy. Efficacy stays within 0.1–2× the fitted weight.

## What would count as learning

Held-out chronological market replay, independent starts, frozen-weight and shuffled-reinforcement controls, fees and slippage, equal budgets, retention, and loss of benefit after resetting learned weights, compared against cash and simple exposure baselines. In the browser tasks we ran the frozen-weight control: over one-minute games it made no measurable difference. **No profitable learning, strategy improvement, biological replication or live-funded performance has been demonstrated.**
