"""Generate explainable inventory actions from model predictions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

Action = Literal["reorder", "markdown", "monitor", "hold"]
Priority = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Recommendation:
    """A recommended retail action with the evidence behind it."""

    action: Action
    priority: Priority
    order_qty: int
    confidence: float
    rationale: list[str]
    store: Any = None
    product_no: Any = None
    date: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable recommendation payload."""
        return asdict(self)


def _number(value: Any, default: float = 0.0) -> float:
    """Convert a possibly missing model or feature value to a finite number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def generate_recommendation(
    features: Mapping[str, Any],
    prediction: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> Recommendation:
    """Turn one forecast and inventory snapshot into an inventory action.

    The recommendation uses the model's demand probability and P50/P90 forecasts,
    together with current inventory and stock status. It is deliberately
    deterministic and explainable so that a human can approve the action.
    """
    policy = policy or {}
    demand_probability = min(1.0, max(0.0, _number(prediction.get("demand_probability"))))
    p50 = max(0.0, _number(prediction.get("hurdle_50", prediction.get("quantile_50"))))
    p90 = max(p50, _number(prediction.get("hurdle_90", prediction.get("quantile_90"))))
    inventory = max(0.0, _number(features.get("qty_on_hand")))
    demand_threshold = min(1.0, max(0.0, _number(policy.get("demand_probability_threshold"), 0.5)))
    excess_multiplier = max(1.0, _number(policy.get("excess_inventory_multiplier"), 2.0))
    markdown_statuses = {
        str(status).lower() for status in policy.get("markdown_statuses", ["markdown", "clearance"])
    }
    stock_status = str(features.get("stock_status", "")).lower()

    rationale = [
        f"Predicted demand probability is {demand_probability:.0%}.",
        f"Forecast demand is {p50:.1f} units (P50) to {p90:.1f} units (P90).",
        f"Current inventory is {inventory:.1f} units.",
    ]

    if demand_probability >= demand_threshold and inventory < p50:
        target = p90
        action: Action = "reorder"
        priority: Priority = "high"
        rationale.append("Inventory is below the expected demand range; replenish toward P90.")
    elif demand_probability >= demand_threshold and inventory < p90:
        target = p90
        action = "reorder"
        priority = "medium"
        rationale.append(
            "Inventory is below the high-demand forecast; replenish before a stockout."
        )
    elif inventory > p90 * excess_multiplier and (
        stock_status in markdown_statuses or demand_probability < demand_threshold
    ):
        target = p50
        action = "markdown"
        priority = "medium"
        rationale.append("Inventory materially exceeds forecast demand; reduce excess stock.")
    elif demand_probability >= demand_threshold:
        target = inventory
        action = "monitor"
        priority = "low"
        rationale.append(
            "Demand is likely and inventory covers the forecast; monitor sell-through."
        )
    else:
        target = inventory
        action = "hold"
        priority = "low"
        rationale.append("Demand signal is weak and no immediate inventory action is indicated.")

    order_qty = max(0, math.ceil(target - inventory)) if action == "reorder" else 0
    return Recommendation(
        action=action,
        priority=priority,
        order_qty=order_qty,
        confidence=demand_probability,
        rationale=rationale,
        store=features.get("store"),
        product_no=features.get("product_no"),
        date=features.get("date"),
    )
