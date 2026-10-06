"""Demand forecasting target definitions."""

from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed"
FEATURE_DIR = PROCESSED_DIR / "features"
FEATURE_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")


TARGET_DEFINITIONS = {
    "target_demand_7d": {
        "description": "Sum of net quantity sold over 7 days (T to T+6)",
        "horizon_days": 7,
        "aggregation": "sum",
        "target_type": "regression",
        "unit": "units",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "Primary demand forecasting target. Uses net_qty_sold (gross - returns).",
    },
    "target_demand_14d": {
        "description": "Sum of net quantity sold over 14 days (T to T+13)",
        "horizon_days": 14,
        "aggregation": "sum",
        "target_type": "regression",
        "unit": "units",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_13",
        "notes": "Longer horizon for replenishment planning.",
    },
    "target_demand_28d": {
        "description": "Sum of net quantity sold over 28 days (T to T+27)",
        "horizon_days": 28,
        "aggregation": "sum",
        "target_type": "regression",
        "unit": "units",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_27",
        "notes": "Monthly planning horizon.",
    },
    "target_any_demand_7d": {
        "description": "Binary: any demand in next 7 days",
        "horizon_days": 7,
        "aggregation": "any",
        "target_type": "classification",
        "unit": "binary",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "For stockout prediction / zero-demand detection.",
    },
    "target_zero_demand_7d": {
        "description": "Binary: zero demand for 7 consecutive days",
        "horizon_days": 7,
        "aggregation": "all_zero",
        "target_type": "classification",
        "unit": "binary",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "Dead-stock / slow-mover detection.",
    },
    "target_stockout_risk_7d": {
        "description": "Binary: 7-day demand exceeds current inventory",
        "horizon_days": 7,
        "aggregation": "compare_to_inventory",
        "target_type": "classification",
        "unit": "binary",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "Requires inventory at day T. For stockout prediction.",
    },
}


def add_targets(df: pd.DataFrame, horizons: list[int] | None = None) -> pd.DataFrame:
    if horizons is None:
        horizons = [7, 14, 28]
    """Add all target columns to feature dataframe."""
    df = df.copy()
    df = df.sort_values(["store", "product_no", "date"]).reset_index(drop=True)

    for h in horizons:
        # Regression targets
        df[f"target_demand_{h}d"] = df.groupby(["store", "product_no"])["net_qty_sold"].transform(
            lambda x, h=h: x.rolling(h, min_periods=1).sum().shift(-h + 1)
        )

        # Binary: any demand
        df[f"target_any_demand_{h}d"] = (df[f"target_demand_{h}d"] > 0).astype(int)

        # Binary: zero demand (all days zero)
        df[f"target_zero_demand_{h}d"] = df.groupby(["store", "product_no"])[
            "net_qty_sold"
        ].transform(
            lambda x, h=h: (x.rolling(h, min_periods=h).max() == 0).astype(int).shift(-h + 1)
        )

        # Binary: stockout risk (demand > inventory at day T)
        if "qty_on_hand" in df.columns:
            df[f"target_stockout_risk_{h}d"] = (
                (df[f"target_demand_{h}d"] > df["qty_on_hand"])
                .astype(int)
                .where(df["qty_on_hand"].notna(), np.nan)
            )

    return df


def get_target_info(target_name: str) -> dict:
    """Get metadata for a specific target."""
    return TARGET_DEFINITIONS.get(target_name, {})


def list_targets() -> list[str]:
    """List all available target names."""
    return list(TARGET_DEFINITIONS.keys())


def validate_targets(df: pd.DataFrame, target_cols: list[str] = None) -> dict:
    """Validate target columns for leakage and quality."""
    if target_cols is None:
        target_cols = [c for c in df.columns if c.startswith("target_")]

    issues = []
    stats = {}

    for col in target_cols:
        if col not in df.columns:
            issues.append(f"Target column {col} not found")
            continue

        null_pct = df[col].isna().mean()
        stats[col] = {
            "null_pct": float(null_pct),
            "mean": float(df[col].mean()) if df[col].dtype in ["float64", "int64"] else None,
            "std": float(df[col].std()) if df[col].dtype in ["float64", "int64"] else None,
            "min": float(df[col].min()) if df[col].dtype in ["float64", "int64"] else None,
            "max": float(df[col].max()) if df[col].dtype in ["float64", "int64"] else None,
            "unique": int(df[col].nunique()) if df[col].dtype in ["int64", "object"] else None,
        }

        # Check for high null rate (expected at end of time series)
        if null_pct > 0.3:
            issues.append(f"Target {col} has {null_pct*100:.1f}% nulls (expected at series end)")

        # For binary targets, check class balance
        if df[col].dtype in ["int64", "int32"] and df[col].nunique() <= 2:
            vals = df[col].dropna()
            if len(vals) > 0:
                pos_rate = vals.mean()
                stats[col]["positive_rate"] = float(pos_rate)
                if pos_rate < 0.01 or pos_rate > 0.99:
                    issues.append(f"Target {col} highly imbalanced: {pos_rate*100:.1f}% positive")

    return {"stats": stats, "issues": issues}
