"""Money and neural parameters. Execution bounds are copied from STONKFLY (MIT);
the neural block is the zebrafish model's declared choices."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal


def D(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not money")
    x = Decimal(str(value))
    if not x.is_finite():
        raise ValueError("Nonfinite quantity")
    return x


def down(value, step):
    return (D(value) / D(step)).to_integral_value(rounding=ROUND_DOWN) * D(step)


def up(value, step):
    return (D(value) / D(step)).to_integral_value(rounding=ROUND_UP) * D(step)


@dataclass(frozen=True)
class Settings:
    products: tuple[str, ...] = ("BTC-USDC",)
    capital: str = "100"
    order_limit: str = "10"
    loss_stop: str = "20"
    fee_reserve: str = "0.02"
    slippage: str = "0.005"
    spread_limit: str = "0.005"
    daily_orders: int = 24
    interval_seconds: float = 60
    max_quote_age: float = 15
    reward_deadband: str = "0.01"
    paper_fee: str = "0.006"
    learning: bool = True
    # --- zebrafish model (declared choices, not measured physiology) ---
    neural_frames: int = 8  # imaging frames of fish time per market observation
    frame_seconds: float = 0.9  # approximate ZAPBench volume period, for traces only
    input_gain: float = 0.35  # dF/F drive per unit of chart luminance contrast
    pulse_frames: int = 2  # reinforcement pulse length in frames
    pulse_amplitude: float = 0.5  # dF/F-equivalent drive into reward/aversive cells
    decoder_threshold: float = 0.02  # mean right minus left dF/F
    gate_level: float = 0.15  # any gate cell above this dF/F enables a proposal
    plasticity_gain: float = 0.001

    def __post_init__(self):
        if (
            not self.products
            or len(set(self.products)) != len(self.products)
            or not set(self.products) <= set(("BTC-USDC", "ETH-USDC", "SOL-USDC"))
        ):
            raise ValueError("Only allowlisted USDC spot pairs")
        if not 0 < D(self.capital) <= 100 or not 0 < D(self.order_limit) <= min(
            D(self.capital), D(10)
        ):
            raise ValueError("Maximum capital $100; maximum order $10")
        if not 0 < D(self.loss_stop) <= D(self.capital):
            raise ValueError("Invalid loss stop")
        if (
            not D(0) < D(self.fee_reserve) <= D(".05")
            or not 0 <= D(self.slippage) <= D(".01")
            or not 0 < D(self.spread_limit) <= D(".01")
        ):
            raise ValueError("Invalid fee/spread/slippage bounds")
        if not 0 <= D(self.paper_fee) <= D(self.fee_reserve):
            raise ValueError("Invalid paper fee")
        if (
            type(self.daily_orders) is not int
            or not 1 <= self.daily_orders <= 100
            or not math.isfinite(self.interval_seconds)
            or self.interval_seconds < 60
        ):
            raise ValueError("Rate limit: >=60 s between orders, <=100 orders/day")
        if D(self.reward_deadband) <= 0:
            raise ValueError("Positive reinforcement deadband required")
        for x in [
            self.max_quote_age,
            self.frame_seconds,
            self.input_gain,
            self.pulse_amplitude,
            self.decoder_threshold,
            self.gate_level,
            self.plasticity_gain,
        ]:
            if not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0:
                raise ValueError("Positive finite parameter required")
        if (
            type(self.neural_frames) is not int
            or type(self.pulse_frames) is not int
            or not 1 <= self.neural_frames <= 64
            or not 1 <= self.pulse_frames <= self.neural_frames
        ):
            raise ValueError("1-64 frames per observation; pulse must fit inside")

    def signature(self):
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()
        ).hexdigest()
