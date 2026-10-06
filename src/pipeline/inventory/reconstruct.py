"""Inventory reconstruction - fully vectorized version matching standalone script."""

from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")

INV_COLUMNS = [
    "date",
    "store",
    "product_no",
    "product_description",
    "product_division",
    "product_category",
    "product_subcategory",
    "product_segment",
    "supplier",
    "qty_on_hand",
    "stock_status",
    "stock_selling_amount",
    "cost_of_stocks",
    "stock_unit_selling_price",
    "stock_unit_cost_price",
    "observed_flag",
    "gap_flag",
    "negative_qty_flag",
    "writeoff_flag",
]


def reconstruct_inventory(raw_inv: pd.DataFrame) -> pd.DataFrame:
    """Fully vectorized inventory reconstruction."""
    df = raw_inv.copy()

    # Parse dates as Timestamps (not .date)
    df["start_date"] = pd.to_datetime(df["Start Date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["End Date"], errors="coerce")
    df = df.dropna(subset=["start_date", "end_date"]).copy()

    # Cap far-future
    far_future = df["end_date"] > pd.Timestamp("2030-01-01")
    df.loc[far_future, "end_date"] = CUTOFF_DATE

    # Rename
    df = df.rename(
        columns={
            "Store": "store",
            "Product No": "product_no",
            "Product Description": "product_description",
            "Product Division": "product_division",
            "Product Category": "product_category",
            "Product Subcategory": "product_subcategory",
            "Product Segment": "product_segment",
            "Supplier": "supplier",
            "Qty on hand": "qty_on_hand",
            "Stock Status": "stock_status",
            "Stocks Selling Amount": "stock_selling_amount",
            "Cost of Stocks": "cost_of_stocks",
            "Stock Unit Selling Price": "stock_unit_selling_price",
            "Stock Unit Cost Price": "stock_unit_cost_price",
        }
    )

    # Sort
    df = df.sort_values(["store", "product_no", "start_date"]).reset_index(drop=True)

    # Duration
    df["duration"] = (df["end_date"] - df["start_date"]).dt.days + 1
    df = df[df["duration"] > 0].copy()

    # --- VECTORIZED EXPLODE ---
    df = df.loc[df.index.repeat(df["duration"])].reset_index(drop=True)

    # Day offset within each interval
    df["day_offset"] = df.groupby(["store", "product_no", "start_date", "end_date"]).cumcount()
    df["date"] = df["start_date"] + pd.to_timedelta(df["day_offset"], unit="D")

    # --- ADD GAP DAYS (VECTORIZED) ---
    # Get the min/max date per store-product
    ranges = df.groupby(["store", "product_no"])["date"].agg(["min", "max"]).reset_index()
    ranges.columns = ["store", "product_no", "min_date", "max_date"]

    # Compute number of days per store-product
    ranges["num_days"] = (ranges["max_date"] - ranges["min_date"]).dt.days + 1

    # Vectorized grid creation using numpy repeat
    stores = np.repeat(ranges["store"].values, ranges["num_days"].values)
    products = np.repeat(ranges["product_no"].values, ranges["num_days"].values)
    min_dates = np.repeat(ranges["min_date"].values, ranges["num_days"].values)

    # Generate day offsets using cumcount per group
    day_offsets = np.concatenate([np.arange(n) for n in ranges["num_days"].values])
    dates = min_dates + pd.to_timedelta(day_offsets, unit="D")

    full_grid = pd.DataFrame({"date": dates, "store": stores, "product_no": products})

    # Merge observed data onto full grid
    obs_cols = [
        "date",
        "store",
        "product_no",
        "qty_on_hand",
        "stock_status",
        "stock_selling_amount",
        "cost_of_stocks",
        "stock_unit_selling_price",
        "stock_unit_cost_price",
        "product_description",
        "product_division",
        "product_category",
        "product_subcategory",
        "product_segment",
        "supplier",
    ]

    observed = df[obs_cols].copy()
    observed = observed.drop_duplicates(subset=["date", "store", "product_no"])

    # Merge
    merged = full_grid.merge(
        observed, on=["date", "store", "product_no"], how="left", indicator=True
    )

    # Identify gap vs observed
    merged["observed_flag"] = merged["_merge"] == "both"
    merged["gap_flag"] = merged["_merge"] == "left_only"
    merged = merged.drop(columns=["_merge"])

    # For gap rows, fill metadata from nearest observed (forward fill within store-product)
    meta_cols = [
        "product_description",
        "product_division",
        "product_category",
        "product_subcategory",
        "product_segment",
        "supplier",
    ]

    # Forward fill metadata
    for col in meta_cols:
        merged[col] = merged.groupby(["store", "product_no"])[col].ffill()

    # Apply flags
    merged["negative_qty_flag"] = merged["qty_on_hand"] < 0
    merged["writeoff_flag"] = (merged["qty_on_hand"] == 0) & (merged["cost_of_stocks"] < 0)

    # Writeoff: set cost to 0
    merged.loc[merged["writeoff_flag"], "cost_of_stocks"] = 0

    # Ensure gap rows have NULL inventory values
    gap_mask = merged["gap_flag"]
    inv_cols = [
        "qty_on_hand",
        "stock_status",
        "stock_selling_amount",
        "cost_of_stocks",
        "stock_unit_selling_price",
        "stock_unit_cost_price",
    ]
    for col in inv_cols:
        merged.loc[gap_mask, col] = np.nan

    # Sort
    merged = merged.sort_values(["store", "product_no", "date"]).reset_index(drop=True)

    return merged


def save_daily_inventory(df: pd.DataFrame) -> Path:
    """Save daily inventory to parquet."""
    path = PROCESSED_DIR / "daily_inventory.parquet"
    df.to_parquet(path, index=False)
    return path


def load_daily_inventory() -> pd.DataFrame:
    """Load processed daily inventory."""
    path = PROCESSED_DIR / "daily_inventory.parquet"
    return pd.read_parquet(path)


def validate_daily_inventory(df: pd.DataFrame) -> dict:
    """Validate daily inventory output."""
    issues = []

    # Check for duplicates
    dup_count = df.duplicated(subset=["date", "store", "product_no"]).sum()
    if dup_count > 0:
        issues.append(f"Duplicate date+store+product keys: {dup_count}")

    # Check no 9999 dates
    max_date = df["date"].max()
    if max_date > CUTOFF_DATE:
        issues.append(f"Date exceeds cutoff: {max_date}")

    # Check gap days have NULL inventory values
    gap_rows = df[df["gap_flag"]]
    if len(gap_rows) > 0:
        null_checks = {
            "qty_on_hand": gap_rows["qty_on_hand"].isna().all(),
            "stock_status": gap_rows["stock_status"].isna().all(),
            "stock_selling_amount": gap_rows["stock_selling_amount"].isna().all(),
            "cost_of_stocks": gap_rows["cost_of_stocks"].isna().all(),
            "stock_unit_selling_price": gap_rows["stock_unit_selling_price"].isna().all(),
            "stock_unit_cost_price": gap_rows["stock_unit_cost_price"].isna().all(),
        }
        if not all(null_checks.values()):
            issues.append("Gap days have non-NULL inventory values")

    # Check observed days have values
    obs_rows = df[df["observed_flag"]]
    if len(obs_rows) > 0 and obs_rows["qty_on_hand"].isna().any():
        issues.append("Observed days have NULL qty_on_hand")

    # Check negative qty preserved
    neg_qty_count = (df["qty_on_hand"] < 0).sum()
    neg_qty_flagged = df["negative_qty_flag"].sum()
    if neg_qty_count != neg_qty_flagged:
        issues.append(f"Negative qty count mismatch: {neg_qty_count} vs {neg_qty_flagged}")

    # Check writeoff handling
    writeoff_rows = df[df["writeoff_flag"]]
    if len(writeoff_rows) > 0 and not (writeoff_rows["cost_of_stocks"] == 0).all():
        issues.append("Writeoff records don't have cost=0")

    # Check flags mutually exclusive
    both_flags = ((df["observed_flag"]) & (df["gap_flag"])).sum()
    if both_flags > 0:
        issues.append(f"Records with both observed and gap flags: {both_flags}")

    return {
        "row_count": len(df),
        "date_range": (str(df["date"].min()), str(df["date"].max())),
        "unique_store_product": df[["store", "product_no"]].drop_duplicates().shape[0],
        "duplicates": int(dup_count),
        "observed_days": int(df["observed_flag"].sum()),
        "gap_days": int(df["gap_flag"].sum()),
        "negative_qty_records": int((df["qty_on_hand"] < 0).sum()),
        "writeoff_records": int(df["writeoff_flag"].sum()),
        "issues": issues,
    }
