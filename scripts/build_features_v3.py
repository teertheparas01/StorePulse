"""Complete rebuild of demand forecasting features with correct calendar-day target."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
FEATURE_DIR = PROCESSED_DIR / "features"
FEATURE_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")

# ============================================================
# FEATURE METADATA (unchanged - all features already leakage-safe)
# ============================================================
FEATURE_METADATA = {
    "sales_lag_1": {
        "description": "Net qty sold on day T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_lag_7": {
        "description": "Net qty sold on day T-7",
        "available_at": "end_of_day_T_minus_7",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_lag_14": {
        "description": "Net qty sold on day T-14",
        "available_at": "end_of_day_T_minus_14",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_lag_28": {
        "description": "Net qty sold on day T-28",
        "available_at": "end_of_day_T_minus_28",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_mean_7": {
        "description": "Mean net qty over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_mean_14": {
        "description": "Mean net qty over T-14 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_mean_28": {
        "description": "Mean net qty over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_std_7": {
        "description": "Std dev of net qty over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_std_14": {
        "description": "Std dev of net qty over T-14 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_std_28": {
        "description": "Std dev of net qty over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_sum_7": {
        "description": "Total net qty over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_sum_14": {
        "description": "Total net qty over T-14 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_rolling_sum_28": {
        "description": "Total net qty over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_zero_streak": {
        "description": "Consecutive days with zero net sales up to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "sales_cv_28": {
        "description": "Coefficient of variation over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "is_promo_today": {
        "description": "Whether day T has promo (from sales_type)",
        "available_at": "start_of_day_T",
        "leakage_risk": "low - plan known in advance",
        "source": "daily_sales",
    },
    "is_markdown_today": {
        "description": "Whether day T has markdown",
        "available_at": "start_of_day_T",
        "leakage_risk": "low",
        "source": "daily_sales",
    },
    "is_clearance_today": {
        "description": "Whether day T is clearance",
        "available_at": "start_of_day_T",
        "leakage_risk": "low",
        "source": "daily_sales",
    },
    "promo_lag_7": {
        "description": "Was promo on T-7",
        "available_at": "end_of_day_T_minus_7",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "markdown_lag_7": {
        "description": "Was markdown on T-7",
        "available_at": "end_of_day_T_minus_7",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "clearance_lag_7": {
        "description": "Was clearance on T-7",
        "available_at": "end_of_day_T_minus_7",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "promo_days_last_28": {
        "description": "Count of promo days in T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "markdown_days_last_28": {
        "description": "Count of markdown days in T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "unit_price_lag_1": {
        "description": "Unit price on T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "unit_price_rolling_mean_7": {
        "description": "Mean unit price over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "price_change_pct_7": {
        "description": "Price change pct vs 7 days ago",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "inv_qty_on_hand": {
        "description": "Inventory qty at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_stock_status": {
        "description": "Stock status at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_weeks_of_supply": {
        "description": "Qty on hand / rolling 7-day avg sales (T-7 to T-1)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory + daily_sales",
    },
    "inv_days_since_receipt": {
        "description": "Days since inventory interval started",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_gap_days_since_obs": {
        "description": "Days since last observed inventory",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_negative_qty_flag": {
        "description": "Negative qty flag at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_writeoff_flag": {
        "description": "Writeoff flag at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_stock_selling_price": {
        "description": "Unit selling price from inventory",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_stock_unit_cost": {
        "description": "Unit cost price from inventory",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_cost_retail_ratio": {
        "description": "Unit cost / unit selling price",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "inv_stock_status_encoded": {
        "description": "Numeric encoding of stock status",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory",
    },
    "day_of_week": {
        "description": "Day of week (0=Mon, 6=Sun)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "day_of_month": {
        "description": "Day of month (1-31)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "week_of_year": {
        "description": "Week of year (1-52)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "month": {
        "description": "Month (1-12)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "quarter": {
        "description": "Quarter (1-4)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "is_weekend": {
        "description": "Saturday or Sunday",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "is_month_start": {
        "description": "First 3 days of month",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "is_month_end": {
        "description": "Last 3 days of month",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar",
    },
    "product_division": {
        "description": "Product division",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "product_category": {
        "description": "Product category",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "product_subcategory": {
        "description": "Product subcategory",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "product_segment": {
        "description": "Product segment",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "supplier": {
        "description": "Supplier/vendor",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "store": {
        "description": "Store identifier",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "store_avg_daily_sales_28": {
        "description": "Store avg daily sales T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
    "store_product_rank": {
        "description": "Product rank within store by 28-day sales",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales",
    },
}


# ============================================================
# TARGET DEFINITIONS
# ============================================================
TARGET_DEFINITIONS = {
    "target_demand_7d": {
        "description": "Sum of net quantity sold over 7 calendar days (T to T+6)",
        "horizon_days": 7,
        "aggregation": "sum",
        "target_type": "regression",
        "unit": "units",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "Primary demand forecasting target. Uses net_qty_sold (gross - returns). Computed on complete calendar-day grid.",
    },
    "target_demand_14d": {
        "description": "Sum of net quantity sold over 14 calendar days (T to T+13)",
        "horizon_days": 14,
        "aggregation": "sum",
        "target_type": "regression",
        "unit": "units",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_13",
        "notes": "Longer horizon for replenishment planning.",
    },
    "target_demand_28d": {
        "description": "Sum of net quantity sold over 28 calendar days (T to T+27)",
        "horizon_days": 28,
        "aggregation": "sum",
        "target_type": "regression",
        "unit": "units",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_27",
        "notes": "Monthly planning horizon.",
    },
    "target_any_demand_7d": {
        "description": "Binary: any demand in next 7 calendar days",
        "horizon_days": 7,
        "aggregation": "any",
        "target_type": "classification",
        "unit": "binary",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "For stockout prediction / zero-demand detection.",
    },
    "target_zero_demand_7d": {
        "description": "Binary: zero demand for 7 consecutive calendar days",
        "horizon_days": 7,
        "aggregation": "all_zero",
        "target_type": "classification",
        "unit": "binary",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "Dead-stock / slow-mover detection.",
    },
    "target_stockout_risk_7d": {
        "description": "Binary: 7-day calendar demand exceeds current inventory",
        "horizon_days": 7,
        "aggregation": "compare_to_inventory",
        "target_type": "classification",
        "unit": "binary",
        "leakage_safe": True,
        "available_at": "end_of_day_T_plus_6",
        "notes": "Requires inventory at day T. For stockout prediction.",
    },
}


def build_complete_calendar_grid(sales: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    """
    Create complete calendar-day grid for every Store+Product that has sales data.

    Assumption: The universe of Store+Product pairs is defined by daily_sales.
    Missing sales dates = zero observed sales (not missing data).
    """
    print("Building complete calendar-day grid...")

    sales["date"] = pd.to_datetime(sales["date"])
    inv["date"] = pd.to_datetime(inv["date"])

    # Get all Store+Product combinations from sales
    sp_combos = sales[
        [
            "store",
            "product_no",
            "product_description",
            "product_division",
            "product_category",
            "product_subcategory",
            "product_segment",
            "supplier",
        ]
    ].drop_duplicates()

    # Date range from sales data
    min_date = sales["date"].min()
    max_date = sales["date"].max()
    print(f"  Sales date range: {min_date.date()} to {max_date.date()}")

    # Create complete calendar grid
    date_range = pd.date_range(min_date, max_date, freq="D")

    grids = []
    for _, sp in sp_combos.iterrows():
        grid = pd.DataFrame(
            {"date": date_range, "store": sp["store"], "product_no": sp["product_no"]}
        )
        for col in [
            "product_description",
            "product_division",
            "product_category",
            "product_subcategory",
            "product_segment",
            "supplier",
        ]:
            grid[col] = sp[col]
        grids.append(grid)

    full_grid = pd.concat(grids, ignore_index=True)
    print(
        f"  Complete grid: {len(full_grid):,} rows ({len(sp_combos):,} store-products x {len(date_range)} days)"
    )

    # Merge daily net_qty_sold (fill missing with 0)
    sales_cols = [
        "date",
        "store",
        "product_no",
        "net_qty_sold",
        "sales_amount",
        "return_qty",
        "return_amount",
        "unit_price",
        "unit_cost",
        "is_promo",
        "is_markdown",
        "is_clearance",
        "sales_type",
        "qty_sold",
        "cogs",
        "transaction_count",
    ]

    panel = full_grid.merge(sales[sales_cols], on=["date", "store", "product_no"], how="left")

    # Fill missing sales with 0
    # ASSUMPTION: Absence of a sales record = zero observed sales that day
    panel["net_qty_sold"] = panel["net_qty_sold"].fillna(0)
    panel["sales_amount"] = panel["sales_amount"].fillna(0)
    panel["return_qty"] = panel["return_qty"].fillna(0)
    panel["return_amount"] = panel["return_amount"].fillna(0)
    panel["unit_price"] = panel["unit_price"].fillna(np.nan)
    panel["unit_cost"] = panel["unit_cost"].fillna(np.nan)
    panel["is_promo"] = panel["is_promo"].fillna(False)
    panel["is_markdown"] = panel["is_markdown"].fillna(False)
    panel["is_clearance"] = panel["is_clearance"].fillna(False)
    panel["sales_type"] = panel["sales_type"].fillna("No Sales")
    panel["qty_sold"] = panel["qty_sold"].fillna(0)
    panel["cogs"] = panel["cogs"].fillna(0)
    panel["transaction_count"] = panel["transaction_count"].fillna(0)

    # Merge observed inventory (left join - keep all calendar days)
    inv_obs = inv[inv["observed_flag"]].copy()
    inv_cols = [
        "date",
        "store",
        "product_no",
        "qty_on_hand",
        "stock_status",
        "stock_unit_selling_price",
        "stock_unit_cost_price",
        "negative_qty_flag",
        "writeoff_flag",
        "gap_flag",
    ]

    panel = panel.merge(inv_obs[inv_cols], on=["date", "store", "product_no"], how="left")

    # For days without inventory observation
    panel["gap_flag"] = panel["gap_flag"].fillna(True)
    panel["observed_flag"] = (~panel["gap_flag"]).astype(bool)
    panel["negative_qty_flag"] = panel["negative_qty_flag"].fillna(False)
    panel["writeoff_flag"] = panel["writeoff_flag"].fillna(False)

    # Sort
    panel = panel.sort_values(["store", "product_no", "date"]).reset_index(drop=True)

    print(f"  Panel shape: {panel.shape}")
    return panel


def compute_sales_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute all sales-based features using only past data (shift(1) for rolling)."""
    print("Computing sales features...")
    df = panel.copy()
    grp = df.groupby(["store", "product_no"])

    # Lags
    for lag in [1, 7, 14, 28]:
        df[f"sales_lag_{lag}"] = grp["net_qty_sold"].shift(lag)

    # Rolling on shifted series (T-1 back)
    shifted = grp["net_qty_sold"].shift(1)

    for window in [7, 14, 28]:
        df[f"sales_rolling_mean_{window}"] = shifted.groupby(grp.ngroup()).transform(
            lambda x, w=window: x.rolling(w, min_periods=1).mean()
        )
        df[f"sales_rolling_std_{window}"] = shifted.groupby(grp.ngroup()).transform(
            lambda x, w=window: x.rolling(w, min_periods=2).std()
        )
        df[f"sales_rolling_sum_{window}"] = shifted.groupby(grp.ngroup()).transform(
            lambda x, w=window: x.rolling(w, min_periods=1).sum()
        )

    # Zero streak
    df["sales_zero_streak"] = (
        grp["net_qty_sold"]
        .transform(
            lambda x: (
                (x == 0).astype(int)
                * ((x == 0).astype(int).groupby((x != 0).cumsum()).cumcount() + 1)
            )
        )
        .shift(1)
    )

    # CV
    df["sales_cv_28"] = df["sales_rolling_std_28"] / df["sales_rolling_mean_28"].replace(0, np.nan)

    # Promo/markdown features
    for col in ["is_promo", "is_markdown", "is_clearance"]:
        df[f"{col}_lag_7"] = grp[col].shift(7)
        df[f"{col}_days_last_28"] = (
            grp[col]
            .shift(1)
            .groupby(grp.ngroup())
            .transform(lambda x: x.rolling(28, min_periods=1).sum())
        )

    # Price features
    df["unit_price_lag_1"] = grp["unit_price"].shift(1)
    df["unit_price_rolling_mean_7"] = (
        grp["unit_price"]
        .shift(1)
        .groupby(grp.ngroup())
        .transform(lambda x: x.rolling(7, min_periods=1).mean())
    )
    price_lag_7 = grp["unit_price"].shift(7)
    df["price_change_pct_7"] = (df["unit_price_lag_1"] - price_lag_7) / price_lag_7.replace(
        0, np.nan
    )

    return df


def compute_inventory_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inventory features."""
    print("Computing inventory features...")
    grp = df.groupby(["store", "product_no"])

    # Weeks of supply
    df["inv_weeks_of_supply"] = df["qty_on_hand"] / (df["sales_rolling_mean_7"] * 7).replace(
        0, np.nan
    )

    # Days since receipt (for observed inventory days)
    df["inv_days_since_receipt"] = np.nan
    obs_mask = df["observed_flag"]
    if obs_mask.any():
        for (store, product), group in df[obs_mask].groupby(["store", "product_no"]):
            group = group.sort_values("date")
            period_id = (group["date"].diff() > pd.Timedelta(days=1)).cumsum()
            days_since = group.groupby(period_id).cumcount()
            df.loc[group.index, "inv_days_since_receipt"] = days_since.values

    # Gap days since last observation
    df["inv_gap_days_since_obs"] = np.nan
    for (store, product), group in df.groupby(["store", "product_no"]):
        group = group.sort_values("date")
        last_obs = group.loc[group["observed_flag"], "date"]
        if len(last_obs) > 0:
            ffill_dates = group["date"].where(group["observed_flag"]).ffill()
            gap_since = group["date"] - ffill_dates
            df.loc[group.index, "inv_gap_days_since_obs"] = gap_since.dt.days

    # Cost/retail ratio
    df["inv_cost_retail_ratio"] = df["stock_unit_cost_price"] / df[
        "stock_unit_selling_price"
    ].replace(0, np.nan)

    # Stock status encoding
    status_map = {
        "Full Price": 0,
        "Promo": 1,
        "Markdown Tier 1": 2,
        "Markdown Tier 2": 3,
        "Clearance": 4,
    }
    df["inv_stock_status_encoded"] = df["stock_status"].map(status_map)

    return df


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features."""
    print("Computing temporal features...")
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["week_of_year"] = df["date"].dt.isocalendar().week
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_month_start"] = (df["day_of_month"] <= 3).astype(int)
    df["is_month_end"] = (df["day_of_month"] >= 28).astype(int)
    return df


def compute_store_features(df: pd.DataFrame) -> pd.DataFrame:
    """Store-level aggregations."""
    print("Computing store features...")

    # Store avg daily sales (28-day rolling)
    store_daily = df.groupby(["store", "date"])["net_qty_sold"].sum().reset_index()
    store_daily["store_avg_28"] = store_daily.groupby("store")["net_qty_sold"].transform(
        lambda x: x.rolling(28, min_periods=1).mean().shift(1)
    )
    df = df.merge(store_daily[["store", "date", "store_avg_28"]], on=["store", "date"], how="left")
    df = df.rename(columns={"store_avg_28": "store_avg_daily_sales_28"})

    # Product rank within store
    sp_daily = df.groupby(["store", "product_no", "date"])["net_qty_sold"].sum().reset_index()
    sp_daily["sales_28"] = sp_daily.groupby(["store", "product_no"])["net_qty_sold"].transform(
        lambda x: x.rolling(28, min_periods=1).sum().shift(1)
    )
    sp_daily["store_product_rank"] = sp_daily.groupby(["store", "date"])["sales_28"].rank(
        ascending=False, method="min"
    )
    df = df.merge(
        sp_daily[["store", "product_no", "date", "store_product_rank"]],
        on=["store", "product_no", "date"],
        how="left",
    )

    return df


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add target columns computed on complete calendar grid."""
    print("Adding targets (7/14/28 calendar days)...")
    grp = df.groupby(["store", "product_no"])

    for h in [7, 14, 28]:
        # Regression targets: sum over T to T+h-1 (h calendar days)
        df[f"target_demand_{h}d"] = grp["net_qty_sold"].transform(
            lambda x, h=h: x.rolling(h, min_periods=1).sum().shift(-h + 1)
        )

        # Binary: any demand
        df[f"target_any_demand_{h}d"] = (df[f"target_demand_{h}d"] > 0).astype(int)

        # Binary: zero demand (all h days zero)
        df[f"target_zero_demand_{h}d"] = grp["net_qty_sold"].transform(
            lambda x, h=h: (x.rolling(h, min_periods=h).max() == 0).astype(int).shift(-h + 1)
        )

        # Binary: stockout risk
        if "qty_on_hand" in df.columns:
            df[f"target_stockout_risk_{h}d"] = (
                (df[f"target_demand_{h}d"] > df["qty_on_hand"])
                .astype(int)
                .where(df["qty_on_hand"].notna(), np.nan)
            )

    return df


def validate_features(df: pd.DataFrame) -> dict:
    """Validate feature dataset for leakage and quality."""
    issues = []

    # Check target is defined correctly
    target_col = "target_demand_7d"
    if target_col in df.columns:
        target_null_pct = df[target_col].isna().mean()
        if target_null_pct > 0.5:
            issues.append(f"Target {target_col} is {target_null_pct*100:.1f}% null")

    # Check for future leakage in lag features
    lag_cols = [c for c in df.columns if "lag_" in c or "rolling_" in c]
    for col in lag_cols:
        first_row_per_sp = df.groupby(["store", "product_no"]).head(1)
        if first_row_per_sp[col].notna().any():
            issues.append(f"Potential leakage in {col}: non-NaN on first row")

    # Check gap handling
    if "gap_flag" in df.columns:
        gap_rows = df[df["gap_flag"]]
        if len(gap_rows) > 0:
            inv_cols = [
                "qty_on_hand",
                "stock_status",
                "stock_unit_selling_price",
                "stock_unit_cost_price",
            ]
            for col in inv_cols:
                if col in df.columns:
                    non_null = gap_rows[col].notna().sum()
                    if non_null > 0:
                        issues.append(f"Gap days have non-NULL {col}: {non_null}")

    # Verify target uses exactly 7 calendar days - use smaller sample
    if target_col in df.columns:
        valid_target = df[df[target_col].notna()]
        if len(valid_target) > 0:
            # Use head instead of sample to avoid memory issues
            sample = valid_target.head(min(100, len(valid_target)))
            mismatches = 0
            for _, row in sample.iterrows():
                store, prod, date = row["store"], row["product_no"], row["date"]
                future = df[
                    (df["store"] == store)
                    & (df["product_no"] == prod)
                    & (df["date"] >= date)
                    & (df["date"] <= date + pd.Timedelta(days=6))
                ]["net_qty_sold"].sum()
                if abs(row[target_col] - future) > 0.01:
                    mismatches += 1
            if mismatches > 0:
                issues.append(
                    f"Target verification failed: {mismatches}/{len(sample)} samples don't match 7-day calendar sum"
                )
            else:
                print(
                    f"  Target verification: {len(sample)}/{len(sample)} samples match 7-day calendar sum"
                )

    # Null percentage summary - use head to avoid memory
    null_pct = df.isnull().mean().sort_values(ascending=False)

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "date_range": (str(df["date"].min()), str(df["date"].max())),
        "unique_store_product": df[["store", "product_no"]].drop_duplicates().shape[0],
        "target_null_pct": (
            float(df[target_col].isna().mean()) if target_col in df.columns else None
        ),
        "issues": issues,
        "top_null_features": null_pct.head(20).to_dict(),
        "gap_days": int(df["gap_flag"].sum()) if "gap_flag" in df.columns else 0,
        "observed_inv_days": int((~df["gap_flag"]).sum()) if "gap_flag" in df.columns else 0,
    }


def print_feature_metadata():
    """Print feature availability timestamps for review."""
    print("=" * 80)
    print("FEATURE METADATA - AVAILABILITY TIMESTAMPS")
    print("=" * 80)
    for name, meta in FEATURE_METADATA.items():
        print(f"\n{name}:")
        print(f"  Description: {meta['description']}")
        print(f"  Available at: {meta['available_at']}")
        print(f"  Leakage risk: {meta['leakage_risk']}")
        print(f"  Source: {meta['source']}")


def print_target_definitions():
    print("\n" + "=" * 80)
    print("TARGET DEFINITIONS")
    print("=" * 80)
    for name, meta in TARGET_DEFINITIONS.items():
        print(f"\n{name}:")
        for k, v in meta.items():
            print(f"  {k}: {v}")


def main():
    print("=" * 80)
    print("DEMAND FORECASTING - COMPLETE REBUILD WITH CALENDAR-DAY TARGET")
    print("=" * 80)

    print_feature_metadata()
    print_target_definitions()

    # Load data
    print("\n" + "=" * 80)
    print("LOADING DATA")
    print("=" * 80)
    sales = pd.read_parquet(PROCESSED_DIR / "daily_sales.parquet")
    inv = pd.read_parquet(PROCESSED_DIR / "daily_inventory.parquet")
    print(f"Sales: {len(sales):,} rows")
    print(f"Inventory: {len(inv):,} rows")

    # Build complete calendar grid
    print("\n" + "=" * 80)
    print("BUILDING COMPLETE CALENDAR GRID")
    print("=" * 80)
    panel = build_complete_calendar_grid(sales, inv)

    # Compute features
    print("\n" + "=" * 80)
    print("COMPUTING FEATURES")
    print("=" * 80)
    panel = compute_sales_features(panel)
    panel = compute_inventory_features(panel)
    panel = compute_temporal_features(panel)
    panel = compute_store_features(panel)

    # Add targets
    print("\n" + "=" * 80)
    print("ADDING TARGETS")
    print("=" * 80)
    panel = add_targets(panel)

    # Filter: keep only rows with sufficient feature history (>=28 days) and computable target (<= max_date - 6 days)
    print("\n" + "=" * 80)
    print("FILTERING ROWS WITH SUFFICIENT HISTORY")
    print("=" * 80)
    print(f"Before filter: {len(panel):,} rows")

    # Keep rows where we have at least 28 days of history for rolling features
    # and target is computable (not in last 6 days for 7d target, 13 days for 14d, 27 for 28d)
    max_date = panel["date"].max()
    min_date_for_features = panel["date"].min() + pd.Timedelta(days=28)
    max_date_for_target = max_date - pd.Timedelta(days=6)  # for 7d target

    panel = panel[
        (panel["date"] >= min_date_for_features) & (panel["date"] <= max_date_for_target)
    ].reset_index(drop=True)

    print(f"After filter: {len(panel):,} rows")
    print(f"Date range: {panel['date'].min().date()} to {panel['date'].max().date()}")

    # Validate
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    feat_val = validate_features(panel)

    print(f"\nRows: {feat_val['rows']:,}")
    print(f"Columns: {feat_val['columns']}")
    print(f"Date range: {feat_val['date_range'][0]} to {feat_val['date_range'][1]}")
    print(f"Unique store-products: {feat_val['unique_store_product']:,}")
    print(f"Gap days: {feat_val['gap_days']:,}")
    print(f"Observed inv days: {feat_val['observed_inv_days']:,}")
    print(f"Target null %: {feat_val['target_null_pct']*100:.1f}%")
    print(f"Issues: {feat_val['issues']}")

    # Target distribution
    target_col = "target_demand_7d"
    t = panel[target_col].dropna()
    print(f"\nTarget {target_col} distribution:")
    print(f"  Count: {len(t):,}")
    print(f"  Mean: {t.mean():.4f}")
    print(f"  Median: {t.median():.4f}")
    print(f"  Std: {t.std():.4f}")
    print(f"  Min: {t.min():.4f}")
    print(f"  Max: {t.max():.4f}")
    print(f"  Zero %: {(t == 0).mean()*100:.2f}%")
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]:
        print(f"  {p}th: {t.quantile(p/100):.4f}")

    # Example calendar windows
    print("\nExample calendar windows (T to T+6):")
    sample = panel[panel[target_col].notna()].sample(
        min(10, panel[target_col].notna().sum()), random_state=42
    )
    for _, row in sample.iterrows():
        store, prod, date = row["store"], row["product_no"], row["date"]
        window = panel[
            (panel["store"] == store)
            & (panel["product_no"] == prod)
            & (panel["date"] >= date)
            & (panel["date"] <= date + pd.Timedelta(days=6))
        ][["date", "net_qty_sold"]]
        print(f"  {store}-{prod} @ {date.date()}: target={row[target_col]:.1f}")
        for _, w in window.iterrows():
            print(f"    {w['date'].date()}: {w['net_qty_sold']:.1f}")

    # Save
    print("\n" + "=" * 80)
    print("SAVING")
    print("=" * 80)
    panel.to_parquet(FEATURE_DIR / "demand_forecasting_features.parquet", index=False)

    metadata = {
        "feature_metadata": FEATURE_METADATA,
        "target_definitions": TARGET_DEFINITIONS,
        "validation": feat_val,
        "dataset_info": {
            "rows": int(len(panel)),
            "columns": int(len(panel.columns)),
            "date_range": [str(panel["date"].min()), str(panel["date"].max())],
            "unique_store_product": int(panel[["store", "product_no"]].drop_duplicates().shape[0]),
            "target_columns": [c for c in panel.columns if c.startswith("target_")],
            "assumptions": [
                "Calendar-day grid built from daily_sales Store+Product pairs",
                "Missing sales dates filled with 0 = zero observed sales (not missing data)",
                "target_demand_7d = sum(net_qty_sold from T to T+6 calendar days)",
                "Prediction timestamp = start of day T",
                "All rolling features use shift(1) -> data up to T-1",
                "Inventory features from observed_flag=True days only",
            ],
        },
    }
    with open(FEATURE_DIR / "feature_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"Saved to {FEATURE_DIR / 'demand_forecasting_features.parquet'}")

    if feat_val["issues"]:
        print("\n⚠️  VALIDATION ISSUES:")
        for issue in feat_val["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✅ ALL VALIDATIONS PASSED")

    return panel


if __name__ == "__main__":
    main()
