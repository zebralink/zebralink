"""Action provider for Coinbase Advanced (an exchange, not a CDP wallet).

Mirrors STONKFLY's AgentKit ActionProvider. If `coinbase-agentkit` is installed
the real base classes are used; otherwise a minimal local shim with the same
interface keeps paper mode dependency-light. No LLM, wallet tools, transfers or
analytics decorators in either case.
"""

import time
from typing import Literal

from pydantic import BaseModel, ConfigDict

try:  # pragma: no cover - depends on optional install
    from coinbase_agentkit import ActionProvider
    from coinbase_agentkit.action_providers.action_provider import Action
except ImportError:  # local shim, identical call surface

    class ActionProvider:
        def __init__(self, name, providers):
            self.name = name
            self.action_providers = providers

    class Action:
        def __init__(self, name, description, args_schema, invoke):
            self.name = name
            self.description = description
            self.args_schema = args_schema
            self.invoke = invoke


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product: str
    side: Literal["BUY", "SELL"]


class ZebralinkActions(ActionProvider):
    def __init__(self, guard, broker):
        self.guard = guard
        self.broker = broker
        self.quotes = {}
        super().__init__("zebralink", [])

    def supports_network(self, network):
        return getattr(network, "network_id", None) == "coinbase-advanced"

    def get_actions(self, wallet_provider=None):
        return [
            Action(
                name="zebralink_spot_order",
                description="Submit a budget-checked, price-bounded Coinbase Advanced spot FOK order from a neural proposal.",
                args_schema=Proposal,
                invoke=self.invoke,
            )
        ]

    def invoke(self, args):
        p = Proposal.model_validate(args)
        plan = self.guard.plan(p.product, p.side, self.quotes)
        plan["neural_observation"] = self.guard.l.get("observation")
        plan["checkpoint"] = self.guard.l.get("checkpoint")
        plan = self.guard.l.reserve(plan, time.time())
        return self.broker.execute(plan, self.guard.before_submit)
