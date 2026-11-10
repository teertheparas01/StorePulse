"""Tests for model-driven inventory recommendations."""

from pipeline.recommendations import generate_recommendation


def test_recommends_reorder_when_inventory_is_below_forecast():
    recommendation = generate_recommendation(
        {"store": "S1", "product_no": "P1", "qty_on_hand": 2},
        {"demand_probability": 0.9, "hurdle_50": 5, "hurdle_90": 8},
    )

    assert recommendation.action == "reorder"
    assert recommendation.priority == "high"
    assert recommendation.order_qty == 6
    assert recommendation.confidence == 0.9


def test_recommends_markdown_for_excess_clearance_inventory():
    recommendation = generate_recommendation(
        {"qty_on_hand": 30, "stock_status": "Clearance"},
        {"demand_probability": 0.1, "hurdle_50": 4, "hurdle_90": 8},
    )

    assert recommendation.action == "markdown"
    assert recommendation.order_qty == 0


def test_recommends_hold_when_signal_is_weak_without_excess_inventory():
    recommendation = generate_recommendation(
        {"qty_on_hand": 5, "stock_status": "Full Price"},
        {"demand_probability": 0.1, "hurdle_50": 2, "hurdle_90": 4},
    )

    assert recommendation.action == "hold"
    assert recommendation.priority == "low"
