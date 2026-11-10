"""Tests for calendar-day demand targets."""

import pandas as pd
from pipeline.targets.demand_targets import add_targets


def test_demand_target_uses_calendar_days_and_full_windows():
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "store": "S1",
            "product_no": "P1",
            "net_qty_sold": [2, 0, 3, 0, 0, 0, 0, 1, 0, 0],
            "qty_on_hand": 10,
        }
    )

    result = add_targets(df, horizons=[7])

    assert result.loc[0, "target_demand_7d"] == 5
    assert result.loc[2, "target_demand_7d"] == 4
    assert result.loc[4:, "target_demand_7d"].isna().all()
    assert result.loc[4:, "target_any_demand_7d"].isna().all()


def test_zero_demand_target_is_calendar_window_aware():
    dates = pd.date_range("2026-01-01", periods=8, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "store": "S1",
            "product_no": "P1",
            "net_qty_sold": 0,
            "qty_on_hand": 10,
        }
    )

    result = add_targets(df, horizons=[7])

    assert result.loc[0, "target_demand_7d"] == 0
    assert result.loc[0, "target_any_demand_7d"] == 0
    assert result.loc[0, "target_zero_demand_7d"] == 1
    assert pd.isna(result.loc[2, "target_demand_7d"])
