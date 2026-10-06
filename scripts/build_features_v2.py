"""Optimized demand feature engineering - vectorized, chunked processing."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
FEATURE_DIR = PROCESSED_DIR / "features"
FEATURE_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")
MAX_LOOKBACK = 90


def build_feature_dataset_optimized() -> pd.DataFrame:
    """Build features using efficient vectorized operations."""
    print("Loading data...")
    sales = pd.read_parquet(PROCESSED_DIR / "daily_sales.parquet")
    inv = pd.read_parquet(PROCESSED_DIR / "daily_inventory.parquet")

    # Convert dates
    sales["date"] = pd.to_datetime(sales["date"])
    inv["date"] = pd.to_datetime(inv["date"])

    # Filter inventory to only observed days (gap days don't add features)
    inv_obs = inv[inv["observed_flag"]].copy()
    print(f"Observed inventory days: {len(inv_obs):,}")

    # Create a unified panel only for store-product-date combinations that have SALES
    # This is much smaller than the full grid
    print("Merging sales with observed inventory...")

    # Select inventory features
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
    inv_obs = inv_obs[inv_cols].copy()

    # Merge sales with observed inventory (left join on sales)
    # This keeps all sales records, adds inventory where available
    panel = sales.merge(inv_obs, on=["date", "store", "product_no"], how="left")

    # For sales days without inventory observation, mark as gap
    panel["gap_flag"] = panel["gap_flag"].fillna(True)
    panel["observed_flag"] = (~panel["gap_flag"]).astype(bool)
    panel["negative_qty_flag"] = panel["negative_qty_flag"].fillna(False)
    panel["writeoff_flag"] = panel["writeoff_flag"].fillna(False)

    # Sort for time-series operations
    panel = panel.sort_values(["store", "product_no", "date"]).reset_index(drop=True)

    print(f"Panel shape: {panel.shape}")

    # ========== SALES FEATURES (vectorized, no leakage) ==========
    print("Computing sales features...")
    grp = panel.groupby(["store", "product_no"])

    # Lags
    for lag in [1, 7, 14, 28]:
        panel[f"sales_lag_{lag}"] = grp["net_qty_sold"].shift(lag)

    # Rolling on shifted series (T-1 back)
    shifted = grp["net_qty_sold"].shift(1)

    for window in [7, 14, 28]:
        panel[f"sales_rolling_mean_{window}"] = shifted.groupby(grp.ngroup()).transform(
            lambda x, w=window: x.rolling(w, min_periods=1).mean()
        )
        panel[f"sales_rolling_std_{window}"] = shifted.groupby(grp.ngroup()).transform(
            lambda x, w=window: x.rolling(w, min_periods=2).std()
        )
        panel[f"sales_rolling_sum_{window}"] = shifted.groupby(grp.ngroup()).transform(
            lambda x, w=window: x.rolling(w, min_periods=1).sum()
        )

    # Zero streak
    panel["sales_zero_streak"] = (
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
    panel["sales_cv_28"] = panel["sales_rolling_std_28"] / panel["sales_rolling_mean_28"].replace(
        0, np.nan
    )

    # Promo/markdown features
    for col in ["is_promo", "is_markdown", "is_clearance"]:
        panel[f"{col}_lag_7"] = grp[col].shift(7)
        panel[f"{col}_days_last_28"] = (
            grp[col]
            .shift(1)
            .groupby(grp.ngroup())
            .transform(lambda x: x.rolling(28, min_periods=1).sum())
        )

    # Price features
    panel["unit_price_lag_1"] = grp["unit_price"].shift(1)
    panel["unit_price_rolling_mean_7"] = (
        grp["unit_price"]
        .shift(1)
        .groupby(grp.ngroup())
        .transform(lambda x: x.rolling(7, min_periods=1).mean())
    )
    price_lag_7 = grp["unit_price"].shift(7)
    panel["price_change_pct_7"] = (panel["unit_price_lag_1"] - price_lag_7) / price_lag_7.replace(
        0, np.nan
    )

    # ========== INVENTORY FEATURES ==========
    print("Computing inventory features...")

    # Weeks of supply
    panel["inv_weeks_of_supply"] = panel["qty_on_hand"] / (
        panel["sales_rolling_mean_7"] * 7
    ).replace(0, np.nan)

    # Days since receipt (for observed inventory days)
    panel["inv_days_since_receipt"] = np.nan
    obs_mask = panel["observed_flag"]
    if obs_mask.any():
        obs_idx = panel[obs_mask].index
        for (store, product), group in panel[obs_mask].groupby(["store", "product_no"]):
            group = group.sort_values("date")
            period_id = (group["date"].diff() > pd.Timedelta(days=1)).cumsum()
            days_since = group.groupby(period_id).cumcount()
            panel.loc[group.index, "inv_days_since_receipt"] = days_since.values

    # Gap days since last observation
    panel["inv_gap_days_since_obs"] = np.nan
    for (store, product), group in panel.groupby(["store", "product_no"]):
        group = group.sort_values("date")
        last_obs = group.loc[group["observed_flag"], "date"]
        if len(last_obs) > 0:
            ffill_dates = group["date"].where(group["observed_flag"]).ffill()
            gap_since = group["date"] - ffill_dates
            panel.loc[group.index, "inv_gap_days_since_obs"] = gap_since.dt.days

    # Cost/retail ratio
    panel["inv_cost_retail_ratio"] = panel["stock_unit_cost_price"] / panel[
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
    panel["inv_stock_status_encoded"] = panel["stock_status"].map(status_map)

    # ========== TEMPORAL FEATURES ==========
    print("Computing temporal features...")
    panel["day_of_week"] = panel["date"].dt.dayofweek
    panel["day_of_month"] = panel["date"].dt.day
    panel["week_of_year"] = panel["date"].dt.isocalendar().week
    panel["month"] = panel["date"].dt.month
    panel["quarter"] = panel["date"].dt.quarter
    panel["is_weekend"] = (panel["day_of_week"] >= 5).astype(int)
    panel["is_month_start"] = (panel["day_of_month"] <= 3).astype(int)
    panel["is_month_end"] = (panel["day_of_month"] >= 28).astype(int)

    # ========== STORE FEATURES ==========
    print("Computing store features...")
    # Store avg daily sales (28-day rolling)
    store_daily = panel.groupby(["store", "date"])["net_qty_sold"].sum().reset_index()
    store_daily["store_avg_28"] = store_daily.groupby("store")["net_qty_sold"].transform(
        lambda x: x.rolling(28, min_periods=1).mean().shift(1)
    )
    panel = panel.merge(
        store_daily[["store", "date", "store_avg_28"]], on=["store", "date"], how="left"
    )
    panel = panel.rename(columns={"store_avg_28": "store_avg_daily_sales_28"})

    # Product rank within store
    sp_daily = panel.groupby(["store", "product_no", "date"])["net_qty_sold"].sum().reset_index()
    sp_daily["sales_28"] = sp_daily.groupby(["store", "product_no"])["net_qty_sold"].transform(
        lambda x: x.rolling(28, min_periods=1).sum().shift(1)
    )
    sp_daily["store_product_rank"] = sp_daily.groupby(["store", "date"])["sales_28"].rank(
        ascending=False, method="min"
    )
    panel = panel.merge(
        sp_daily[["store", "product_no", "date", "store_product_rank"]],
        on=["store", "product_no", "date"],
        how="left",
    )

    return panel


def main():
    print("=" * 60)
    print("DEMAND FORECASTING - OPTIMIZED FEATURE ENGINEERING")
    print("=" * 60)

    df = build_feature_dataset_optimized()
    print(f"\nFeature panel: {df.shape}")

    # Add targets
    print("\nAdding targets...")
    grp = df.groupby(["store", "product_no"])

    for h in [7, 14, 28]:
        df[f"target_demand_{h}d"] = grp["net_qty_sold"].transform(
            lambda x, h=h: x.rolling(h, min_periods=1).sum().shift(-h + 1)
        )
        df[f"target_any_demand_{h}d"] = (df[f"target_demand_{h}d"] > 0).astype(int)
        df[f"target_zero_demand_{h}d"] = grp["net_qty_sold"].transform(
            lambda x, h=h: (x.rolling(h, min_periods=h).max() == 0).astype(int).shift(-h + 1)
        )
        if "qty_on_hand" in df.columns:
            df[f"target_stockout_risk_{h}d"] = (
                (df[f"target_demand_{h}d"] > df["qty_on_hand"])
                .astype(int)
                .where(df["qty_on_hand"].notna(), np.nan)
            )

    # Validation
    print("\nValidating...")
    target_cols = [c for c in df.columns if c.startswith("target_")]

    # Check for leakage
    issues = []
    for lag in [1, 7, 14, 28]:
        col = f"sales_lag_{lag}"
        if col in df.columns:
            first_rows = df.groupby(["store", "product_no"]).head(1)
            if first_rows[col].notna().any():
                issues.append(f"Leakage in {col}: non-NaN on first row")

    # Null stats
    null_pct = df.isnull().mean().sort_values(ascending=False)

    print(f"\nRows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Unique store-products: {df[['store', 'product_no']].drop_duplicates().shape[0]:,}")
    print(f"Target columns: {len(target_cols)}")
    print(f"Gap days: {df['gap_flag'].sum():,}")
    print(f"Observed inv days: {(~df['gap_flag']).sum():,}")
    print(f"Issues: {issues}")

    print("\nTop 20 null features:")
    print(null_pct.head(20))

    # Save
    print("\nSaving...")
    df.to_parquet(FEATURE_DIR / "demand_forecasting_features.parquet", index=False)

    # Save metadata
    metadata = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "date_range": [str(df["date"].min()), str(df["date"].max())],
        "unique_store_product": int(df[["store", "product_no"]].drop_duplicates().shape[0]),
        "target_columns": target_cols,
        "gap_days": int(df["gap_flag"].sum()),
        "observed_inv_days": int((~df["gap_flag"]).sum()),
        "issues": issues,
        "null_pct": null_pct.to_dict(),
    }
    with open(FEATURE_DIR / "feature_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"Saved to {FEATURE_DIR / 'demand_forecasting_features.parquet'}")
    return df


if __name__ == "__main__":
    main()
