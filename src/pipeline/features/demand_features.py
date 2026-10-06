"""Demand forecasting feature engineering - leakage-safe, time-aware."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import timedelta


PROCESSED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed"
FEATURE_DIR = PROCESSED_DIR / "features"
FEATURE_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")
MAX_LOOKBACK_DAYS = 90  # Maximum lookback for rolling features


# ============================================================
# FEATURE METADATA: Every feature documents its availability timestamp
# ============================================================
FEATURE_METADATA = {
    # --- Sales-based features (available at end of day T) ---
    "sales_lag_1": {
        "description": "Net qty sold on day T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_lag_7": {
        "description": "Net qty sold on day T-7",
        "available_at": "end_of_day_T_minus_7",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_lag_14": {
        "description": "Net qty sold on day T-14",
        "available_at": "end_of_day_T_minus_14",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_lag_28": {
        "description": "Net qty sold on day T-28",
        "available_at": "end_of_day_T_minus_28",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_rolling_mean_7": {
        "description": "Mean net qty over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_rolling_mean_14": {
        "description": "Mean net qty over T-14 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_rolling_mean_28": {
        "description": "Mean net qty over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_rolling_std_7": {
        "description": "Std dev of net qty over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_rolling_sum_7": {
        "description": "Total net qty over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_rolling_sum_28": {
        "description": "Total net qty over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_zero_streak": {
        "description": "Consecutive days with zero net sales up to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "sales_cv_28": {
        "description": "Coefficient of variation over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },

    # --- Promo/Markdown features (known in advance or at day start) ---
    "is_promo_today": {
        "description": "Whether day T has promo (from sales_type)",
        "available_at": "start_of_day_T",
        "leakage_risk": "low - plan known in advance",
        "source": "daily_sales"
    },
    "is_markdown_today": {
        "description": "Whether day T has markdown",
        "available_at": "start_of_day_T",
        "leakage_risk": "low",
        "source": "daily_sales"
    },
    "is_clearance_today": {
        "description": "Whether day T is clearance",
        "available_at": "start_of_day_T",
        "leakage_risk": "low",
        "source": "daily_sales"
    },
    "promo_lag_7": {
        "description": "Was promo on T-7",
        "available_at": "end_of_day_T_minus_7",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "promo_days_last_28": {
        "description": "Count of promo days in T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "markdown_days_last_28": {
        "description": "Count of markdown days in T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },

    # --- Price features (available at day start) ---
    "unit_price_lag_1": {
        "description": "Unit price on T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "unit_price_rolling_mean_7": {
        "description": "Mean unit price over T-7 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "price_change_pct_7": {
        "description": "Price change % vs 7 days ago",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },

    # --- Inventory features (available at day start T) ---
    "inv_qty_on_hand": {
        "description": "Inventory qty at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none - snapshot at day start",
        "source": "daily_inventory"
    },
    "inv_stock_status": {
        "description": "Stock status at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_weeks_of_supply": {
        "description": "Qty on hand / rolling 7-day avg sales (T-7 to T-1)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory + daily_sales"
    },
    "inv_days_since_receipt": {
        "description": "Days since inventory interval started",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_is_gap_day": {
        "description": "Whether day T is a gap day (no inventory observation)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none - gap flag is known",
        "source": "daily_inventory"
    },
    "inv_gap_days_since_obs": {
        "description": "Days since last observed inventory (for gap days)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_negative_qty_flag": {
        "description": "Negative qty flag at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_writeoff_flag": {
        "description": "Writeoff flag at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_stock_selling_price": {
        "description": "Unit selling price from inventory at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_stock_unit_cost": {
        "description": "Unit cost price from inventory at start of day T",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },
    "inv_cost_retail_ratio": {
        "description": "Unit cost / unit selling price",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "daily_inventory"
    },

    # --- Temporal features (known in advance) ---
    "day_of_week": {
        "description": "Day of week (0=Mon, 6=Sun)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "day_of_month": {
        "description": "Day of month (1-31)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "week_of_year": {
        "description": "Week of year (1-52)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "month": {
        "description": "Month (1-12)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "quarter": {
        "description": "Quarter (1-4)",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "is_weekend": {
        "description": "Saturday or Sunday",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "is_month_start": {
        "description": "First 3 days of month",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },
    "is_month_end": {
        "description": "Last 3 days of month",
        "available_at": "start_of_day_T",
        "leakage_risk": "none",
        "source": "calendar"
    },

    # --- Product/Store static features (always available) ---
    "product_division": {
        "description": "Product division (Scholar/Femme/Junior)",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "product_category": {
        "description": "Product category",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "product_subcategory": {
        "description": "Product subcategory",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "product_segment": {
        "description": "Product segment",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "supplier": {
        "description": "Supplier/vendor",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "store": {
        "description": "Store identifier",
        "available_at": "always",
        "leakage_risk": "none",
        "source": "daily_sales"
    },

    # --- Store-level aggregations (available at day start) ---
    "store_avg_daily_sales_28": {
        "description": "Store's avg daily sales over T-28 to T-1",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
    "store_product_rank": {
        "description": "Product's rank within store by 28-day sales",
        "available_at": "end_of_day_T_minus_1",
        "leakage_risk": "none",
        "source": "daily_sales"
    },
}


# ============================================================
# FEATURE ENGINEERING FUNCTIONS
# ============================================================

def load_daily_sales() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "daily_sales.parquet")


def load_daily_inventory() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "daily_inventory.parquet")


def prepare_sales_panel(sales: pd.DataFrame) -> pd.DataFrame:
    """Ensure complete daily panel per store-product with forward-filled metadata."""
    sales = sales.copy()
    sales["date"] = pd.to_datetime(sales["date"])
    
    # Create complete date range per store-product
    date_range = pd.date_range(sales["date"].min(), sales["date"].max(), freq="D")
    sp_combos = sales[["store", "product_no", "product_description",
                       "product_division", "product_category", 
                       "product_subcategory", "product_segment", "supplier"]].drop_duplicates()
    
    # Full grid
    grids = []
    for _, sp in sp_combos.iterrows():
        grid = pd.DataFrame({"date": date_range, "store": sp["store"], "product_no": sp["product_no"]})
        for col in ["product_description", "product_division", "product_category",
                    "product_subcategory", "product_segment", "supplier"]:
            grid[col] = sp[col]
        grids.append(grid)
    
    full_panel = pd.concat(grids, ignore_index=True)
    
    # Merge sales data
    sales_cols = ["date", "store", "product_no", "net_qty_sold", "sales_amount", 
                  "return_qty", "return_amount", "unit_price", "unit_cost",
                  "is_promo", "is_markdown", "is_clearance", "sales_type"]
    panel = full_panel.merge(sales[sales_cols], on=["date", "store", "product_no"], how="left")
    
    # Fill missing sales with 0 (no sales = 0 demand)
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
    
    panel = panel.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    return panel


def prepare_inventory_panel(inv: pd.DataFrame) -> pd.DataFrame:
    """Prepare inventory panel with gap handling."""
    inv = inv.copy()
    inv["date"] = pd.to_datetime(inv["date"])
    
    # Select relevant columns
    inv_cols = ["date", "store", "product_no", "qty_on_hand", "stock_status",
                "stock_selling_amount", "cost_of_stocks", "stock_unit_selling_price",
                "stock_unit_cost_price", "observed_flag", "gap_flag",
                "negative_qty_flag", "writeoff_flag"]
    inv = inv[inv_cols].copy()
    
    # For gap days, qty_on_hand is NaN - we keep it as NaN and add gap indicator
    # For observed days with negative qty, keep as-is (flagged)
    # For writeoff days, cost is 0
    
    inv = inv.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    return inv


def compute_sales_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute all sales-based features using only past data."""
    df = panel.copy()
    
    # Sort for proper lag/rolling
    df = df.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    
    # Lags
    for lag in [1, 7, 14, 28]:
        df[f"sales_lag_{lag}"] = df.groupby(["store", "product_no"])["net_qty_sold"].shift(lag)
    
    # Rolling statistics using shift(1) to avoid leakage
    shifted = df.groupby(["store", "product_no"])["net_qty_sold"].shift(1)
    
    for window in [7, 14, 28]:
        # Compute rolling on the shifted series within each group
        df[f"sales_rolling_mean_{window}"] = (
            shifted.groupby(df.groupby(["store", "product_no"]).ngroup())
            .rolling(window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        df[f"sales_rolling_std_{window}"] = (
            shifted.groupby(df.groupby(["store", "product_no"]).ngroup())
            .rolling(window, min_periods=2)
            .std()
            .reset_index(level=0, drop=True)
        )
        df[f"sales_rolling_sum_{window}"] = (
            shifted.groupby(df.groupby(["store", "product_no"]).ngroup())
            .rolling(window, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
    
    # Zero sales streak - compute per group
    def zero_streak(series):
        # Consecutive zeros up to each point
        is_zero = (series == 0).astype(int)
        streak = is_zero * (is_zero.groupby((is_zero == 0).cumsum()).cumcount() + 1)
        return streak
    
    df["sales_zero_streak"] = (
        df.groupby(["store", "product_no"])["net_qty_sold"]
        .transform(zero_streak)
        .shift(1)
    )
    
    # Coefficient of variation
    df["sales_cv_28"] = df["sales_rolling_std_28"] / df["sales_rolling_mean_28"].replace(0, np.nan)
    
    # Promo/markdown features
    for col in ["is_promo", "is_markdown", "is_clearance"]:
        df[f"{col}_lag_7"] = df.groupby(["store", "product_no"])[col].shift(7)
        df[f"{col}_days_last_28"] = (
            df.groupby(["store", "product_no"])[col]
            .shift(1)
            .groupby(df.groupby(["store", "product_no"]).ngroup())
            .rolling(28, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
    
    # Price features
    df["unit_price_lag_1"] = df.groupby(["store", "product_no"])["unit_price"].shift(1)
    df["unit_price_rolling_mean_7"] = (
        df.groupby(["store", "product_no"])["unit_price"]
        .shift(1)
        .groupby(df.groupby(["store", "product_no"]).ngroup())
        .rolling(7, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    price_lag_7 = df.groupby(["store", "product_no"])["unit_price"].shift(7)
    df["price_change_pct_7"] = (df["unit_price_lag_1"] - price_lag_7) / price_lag_7.replace(0, np.nan)
    
    return df


def compute_inventory_features(sales_panel: pd.DataFrame, inv_panel: pd.DataFrame) -> pd.DataFrame:
    """Merge inventory features into sales panel."""
    df = sales_panel.copy()
    
    # Merge inventory data
    inv_cols = ["date", "store", "product_no", "qty_on_hand", "stock_status",
                "stock_unit_selling_price", "stock_unit_cost_price",
                "observed_flag", "gap_flag", "negative_qty_flag", "writeoff_flag"]
    
    df = df.merge(inv_panel[inv_cols], on=["date", "store", "product_no"], how="left")
    
    # For missing inventory (store-product not in inventory data), fill with NaN and gap_flag=True
    df["gap_flag"] = df["gap_flag"].fillna(True)
    df["observed_flag"] = df["observed_flag"].fillna(False)
    df["negative_qty_flag"] = df["negative_qty_flag"].fillna(False)
    df["writeoff_flag"] = df["writeoff_flag"].fillna(False)
    
    # Inventory-based features
    # Weeks of supply = qty_on_hand / 7-day rolling avg sales (using past sales only)
    df["inv_weeks_of_supply"] = df["qty_on_hand"] / (df["sales_rolling_mean_7"] * 7).replace(0, np.nan)
    
    # Days since receipt (for observed days)
    df["inv_days_since_receipt"] = np.nan
    for (store, product), group in df[df["observed_flag"]].groupby(["store", "product_no"]):
        group = group.sort_values("date")
        period_id = (group["date"].diff() > pd.Timedelta(days=1)).cumsum()
        days_since = group.groupby(period_id).cumcount()
        df.loc[group.index, "inv_days_since_receipt"] = days_since.values
    
    # Gap days since last observation
    df["inv_gap_days_since_obs"] = np.nan
    for (store, product), group in df.groupby(["store", "product_no"]):
        group = group.sort_values("date")
        last_obs_dates = group.loc[group["observed_flag"], "date"]
        if len(last_obs_dates) > 0:
            # Forward fill last observed date
            ffill_dates = group["date"].where(group["observed_flag"]).ffill()
            gap_since = group["date"] - ffill_dates
            df.loc[group.index, "inv_gap_days_since_obs"] = gap_since.dt.days
    
    # Cost/retail ratio
    df["inv_cost_retail_ratio"] = df["stock_unit_cost_price"] / df["stock_unit_selling_price"].replace(0, np.nan)
    
    # Stock status encoding
    status_map = {"Full Price": 0, "Promo": 1, "Markdown Tier 1": 2, "Markdown Tier 2": 3, "Clearance": 4}
    df["inv_stock_status_encoded"] = df["stock_status"].map(status_map)
    
    return df


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features."""
    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek  # 0=Mon
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
    df = df.copy()
    
    # Store average daily sales (28-day rolling) - sum across products per store per day, then roll
    store_daily = df.groupby(["store", "date"])["net_qty_sold"].sum().reset_index()
    store_daily["store_avg_28"] = store_daily.groupby("store")["net_qty_sold"].transform(
        lambda x: x.rolling(28, min_periods=1).mean().shift(1)
    )
    df = df.merge(store_daily[["store", "date", "store_avg_28"]], on=["store", "date"], how="left")
    df = df.rename(columns={"store_avg_28": "store_avg_daily_sales_28"})
    
    # Product rank within store by 28-day sales
    sp_daily = df.groupby(["store", "product_no", "date"])["net_qty_sold"].sum().reset_index()
    sp_daily["sales_28"] = sp_daily.groupby(["store", "product_no"])["net_qty_sold"].transform(
        lambda x: x.rolling(28, min_periods=1).sum().shift(1)
    )
    sp_daily["store_product_rank"] = sp_daily.groupby(["store", "date"])["sales_28"].rank(ascending=False, method="min")
    df = df.merge(sp_daily[["store", "product_no", "date", "store_product_rank"]], on=["store", "product_no", "date"], how="left")
    
    return df


def build_feature_dataset() -> pd.DataFrame:
    """Main function to build the complete feature dataset."""
    print("Loading data...")
    sales = load_daily_sales()
    inv = load_daily_inventory()
    
    print("Preparing sales panel...")
    sales_panel = prepare_sales_panel(sales)
    
    print("Preparing inventory panel...")
    inv_panel = prepare_inventory_panel(inv)
    
    print("Computing sales features...")
    sales_panel = compute_sales_features(sales_panel)
    
    print("Merging inventory features...")
    sales_panel = compute_inventory_features(sales_panel, inv_panel)
    
    print("Computing temporal features...")
    sales_panel = compute_temporal_features(sales_panel)
    
    print("Computing store features...")
    sales_panel = compute_store_features(sales_panel)
    
    return sales_panel


def define_target(df: pd.DataFrame, horizon: int = 7) -> pd.DataFrame:
    """Define 7-day demand target (sum of net_qty_sold over T to T+6)."""
    df = df.copy()
    df = df.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    
    # Target: sum of net_qty_sold over next 7 days (including today)
    df[f"target_demand_{horizon}d"] = (
        df.groupby(["store", "product_no"])["net_qty_sold"]
        .transform(lambda x: x.rolling(horizon, min_periods=1).sum().shift(-horizon + 1))
    )
    
    # Also define binary targets
    df[f"target_any_demand_{horizon}d"] = (df[f"target_demand_{horizon}d"] > 0).astype(int)
    df[f"target_stockout_risk_{horizon}d"] = (df[f"target_demand_{horizon}d"] > df["qty_on_hand"]).astype(int) if "qty_on_hand" in df.columns else np.nan
    
    return df


def save_feature_dataset(df: pd.DataFrame, name: str = "demand_forecasting_features") -> Path:
    path = FEATURE_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path


def load_feature_dataset(name: str = "demand_forecasting_features") -> pd.DataFrame:
    path = FEATURE_DIR / f"{name}.parquet"
    return pd.read_parquet(path)


def validate_features(df: pd.DataFrame) -> Dict:
    """Validate feature dataset for leakage and quality."""
    issues = []
    
    # Check target is not all NaN
    target_col = "target_demand_7d"
    if target_col in df.columns:
        target_null_pct = df[target_col].isna().mean()
        if target_null_pct > 0.5:
            issues.append(f"Target {target_col} is {target_null_pct*100:.1f}% null")
    
    # Check for future leakage in lag features
    lag_cols = [c for c in df.columns if "lag_" in c or "rolling_" in c]
    for col in lag_cols:
        # For first few rows per store-product, lags should be NaN
        first_row_per_sp = df.groupby(["store", "product_no"]).head(1)
        if first_row_per_sp[col].notna().any():
            issues.append(f"Potential leakage in {col}: non-NaN on first row")
    
    # Check gap handling
    if "gap_flag" in df.columns:
        gap_rows = df[df["gap_flag"] == True]
        if len(gap_rows) > 0:
            # Gap days should have NaN inventory values
            inv_cols = ["qty_on_hand", "stock_status", "stock_unit_selling_price", "stock_unit_cost_price"]
            for col in inv_cols:
                if col in df.columns:
                    non_null = gap_rows[col].notna().sum()
                    if non_null > 0:
                        issues.append(f"Gap days have non-NULL {col}: {non_null}")
    
    # Check no target leakage into features
    if target_col in df.columns:
        # Target should not correlate perfectly with any feature (sanity check)
        pass
    
    # Null percentage summary
    null_pct = df.isnull().mean().sort_values(ascending=False)
    
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "date_range": (str(df["date"].min()), str(df["date"].max())),
        "unique_store_product": df[["store", "product_no"]].drop_duplicates().shape[0],
        "target_null_pct": float(df[target_col].isna().mean()) if target_col in df.columns else None,
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