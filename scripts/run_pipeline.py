"""Standalone pipeline script - fully vectorized."""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date, timedelta
import hashlib
import json


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")


def load_raw_sales():
    return pd.read_csv(RAW_DIR / "retail_sales_ml_apl.csv", low_memory=False)


def load_raw_inventory():
    return pd.read_csv(RAW_DIR / "retail_inventory_ml_apl.csv", low_memory=False)


def validate_raw_unchanged():
    hashes = {}
    for name in ["retail_sales_ml_apl.csv", "retail_inventory_ml_apl.csv"]:
        path = RAW_DIR / name
        with open(path, "rb") as f:
            hashes[name] = hashlib.sha256(f.read()).hexdigest()
    
    hash_file = PROCESSED_DIR / ".raw_hashes.json"
    if hash_file.exists():
        with open(hash_file) as f:
            expected = json.load(f)
    else:
        expected = hashes
        with open(hash_file, "w") as f:
            json.dump(expected, f)
    
    return all(hashes[k] == expected[k] for k in hashes)


def transform_sales(raw_sales):
    df = raw_sales.copy()
    df["date"] = pd.to_datetime(df["Transaction Date"]).dt.date
    
    df = df.rename(columns={
        "Store": "store", "Product No": "product_no",
        "Product Description": "product_description",
        "Product Division": "product_division",
        "Product Category": "product_category",
        "Product Subcategory": "product_subcategory",
        "Product Segment": "product_segment",
        "Supplier": "supplier",
        "Qty Sold": "qty_sold", "Sales Amount": "sales_amount",
        "Cogs": "cogs", "Number of Transactions": "transaction_count",
        "Sales Type": "sales_type", "Is Return": "is_return"
    })
    
    df["is_promo"] = df["sales_type"] == "Promo"
    df["is_markdown"] = df["sales_type"].isin(["Markdown Tier 1", "Markdown Tier 2"])
    df["is_clearance"] = df["sales_type"] == "Clearance"
    
    returns = df[df["is_return"] == 1].copy()
    sales = df[df["is_return"] == 0].copy()
    
    sales_agg = sales.groupby([
        "date", "store", "product_no", "product_description",
        "product_division", "product_category", "product_subcategory", "product_segment",
        "supplier"
    ], as_index=False).agg(
        qty_sold=("qty_sold", "sum"),
        sales_amount=("sales_amount", "sum"),
        cogs=("cogs", "sum"),
        transaction_count=("transaction_count", "sum"),
        sales_type=("sales_type", lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "Mixed"),
        is_promo=("is_promo", "any"),
        is_markdown=("is_markdown", "any"),
        is_clearance=("is_clearance", "any"),
    )
    
    if len(returns) > 0:
        returns_agg = returns.groupby(["date", "store", "product_no"], as_index=False).agg(
            return_qty=("qty_sold", "sum"),
            return_amount=("sales_amount", "sum"),
        )
        returns_agg["return_qty"] = returns_agg["return_qty"].abs()
        returns_agg["return_amount"] = returns_agg["return_amount"].abs()
    else:
        returns_agg = pd.DataFrame(columns=["date", "store", "product_no", "return_qty", "return_amount"])
    
    result = sales_agg.merge(returns_agg, on=["date", "store", "product_no"], how="left")
    result["return_qty"] = result["return_qty"].fillna(0)
    result["return_amount"] = result["return_amount"].fillna(0)
    
    result["net_qty_sold"] = result["qty_sold"] - result["return_qty"]
    result["net_sales_amount"] = result["sales_amount"] - result["return_amount"]
    
    result["unit_price"] = np.where(result["qty_sold"] != 0, result["sales_amount"] / result["qty_sold"], np.nan)
    result["unit_cost"] = np.where(result["qty_sold"] != 0, result["cogs"] / result["qty_sold"], np.nan)
    
    cols = [
        "date", "store", "product_no", "product_description",
        "product_division", "product_category", "product_subcategory", "product_segment",
        "supplier",
        "qty_sold", "sales_amount", "cogs", "transaction_count",
        "return_qty", "return_amount", "net_qty_sold", "net_sales_amount",
        "unit_price", "unit_cost", "sales_type", "is_promo", "is_markdown", "is_clearance"
    ]
    return result[cols]


def reconstruct_inventory(raw_inv):
    """Fully vectorized inventory reconstruction."""
    df = raw_inv.copy()
    
    # Parse dates
    df["start_date"] = pd.to_datetime(df["Start Date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["End Date"], errors="coerce")
    df = df.dropna(subset=["start_date", "end_date"]).copy()
    
    # Cap far-future
    far_future = df["end_date"] > pd.Timestamp("2030-01-01")
    df.loc[far_future, "end_date"] = CUTOFF_DATE
    
    # Rename
    df = df.rename(columns={
        "Store": "store", "Product No": "product_no",
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
    })
    
    # Sort
    df = df.sort_values(["store", "product_no", "start_date"]).reset_index(drop=True)
    
    # Duration
    df["duration"] = (df["end_date"] - df["start_date"]).dt.days + 1
    df = df[df["duration"] > 0].copy()
    
    # --- VECTORIZED EXPLODE ---
    # Repeat rows by duration
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
    
    full_grid = pd.DataFrame({
        "date": dates,
        "store": stores,
        "product_no": products
    })
    
    # Merge observed data onto full grid
    # Select only needed columns from observed
    obs_cols = ["date", "store", "product_no", "qty_on_hand", "stock_status",
                "stock_selling_amount", "cost_of_stocks", "stock_unit_selling_price",
                "stock_unit_cost_price", "product_description", "product_division",
                "product_category", "product_subcategory", "product_segment", "supplier"]
    
    observed = df[obs_cols].copy()
    observed = observed.drop_duplicates(subset=["date", "store", "product_no"])
    
    # Merge
    merged = full_grid.merge(observed, on=["date", "store", "product_no"], how="left", indicator=True)
    
    # Identify gap vs observed
    merged["observed_flag"] = merged["_merge"] == "both"
    merged["gap_flag"] = merged["_merge"] == "left_only"
    merged = merged.drop(columns=["_merge"])
    
    # For gap rows, fill metadata from nearest observed (forward fill within store-product)
    meta_cols = ["product_description", "product_division", "product_category",
                 "product_subcategory", "product_segment", "supplier"]
    
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
    inv_cols = ["qty_on_hand", "stock_status", "stock_selling_amount", 
                "cost_of_stocks", "stock_unit_selling_price", "stock_unit_cost_price"]
    for col in inv_cols:
        merged.loc[gap_mask, col] = np.nan
    
    # Sort
    merged = merged.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    
    return merged


def validate_sales(df):
    issues = []
    dupes = df.duplicated(subset=["date", "store", "product_no"]).sum()
    if dupes > 0: issues.append(f"Duplicates: {dupes}")
    net_qty = (df["net_qty_sold"] == df["qty_sold"] - df["return_qty"]).all()
    net_amt = (df["net_sales_amount"] == df["sales_amount"] - df["return_amount"]).all()
    if not net_qty: issues.append("Net qty inconsistent")
    if not net_amt: issues.append("Net amount inconsistent")
    return {"rows": len(df), "date_range": (str(df["date"].min()), str(df["date"].max())), 
            "unique_sp": df[["store", "product_no"]].drop_duplicates().shape[0],
            "duplicates": int(dupes), "issues": issues}


def validate_inventory(df):
    issues = []
    dupes = df.duplicated(subset=["date", "store", "product_no"]).sum()
    if dupes > 0: issues.append(f"Duplicates: {dupes}")
    if df["date"].max() > CUTOFF_DATE: issues.append(f"Date exceeds cutoff: {df['date'].max()}")
    
    gap = df[df["gap_flag"]]
    if len(gap) > 0:
        if not gap["qty_on_hand"].isna().all(): issues.append("Gap has non-NULL qty")
    
    obs = df[df["observed_flag"]]
    if len(obs) > 0:
        if obs["qty_on_hand"].isna().any(): issues.append("Obs has NULL qty")
    
    neg = (df["qty_on_hand"] < 0).sum()
    flagged = df["negative_qty_flag"].sum()
    if neg != flagged: issues.append(f"Neg qty mismatch: {neg} vs {flagged}")
    
    woff = df[df["writeoff_flag"]]
    if len(woff) > 0 and not (woff["cost_of_stocks"] == 0).all():
        issues.append("Writeoff cost not zero")
    
    both = ((df["observed_flag"]) & (df["gap_flag"])).sum()
    if both > 0: issues.append(f"Both flags: {both}")
    
    return {"rows": len(df), "date_range": (str(df["date"].min()), str(df["date"].max())),
            "unique_sp": df[["store", "product_no"]].drop_duplicates().shape[0],
            "duplicates": int(dupes), "observed": int(df["observed_flag"].sum()),
            "gaps": int(df["gap_flag"].sum()), "neg_qty": int(neg),
            "writeoff": int(df["writeoff_flag"].sum()), "issues": issues}


def main():
    print("=" * 60)
    print("RETAIL DECISION INTELLIGENCE - DATA RECONSTRUCTION")
    print("=" * 60)
    
    print("\n[1/5] Validating raw data...")
    assert validate_raw_unchanged(), "Raw data modified!"
    print("    OK")
    
    print("\n[2/5] Loading raw data...")
    raw_sales = load_raw_sales()
    raw_inv = load_raw_inventory()
    print(f"    Sales: {len(raw_sales):,} rows")
    print(f"    Inventory: {len(raw_inv):,} rows")
    
    print("\n[3/5] Transforming sales...")
    daily_sales = transform_sales(raw_sales)
    print(f"    Daily sales: {len(daily_sales):,} rows")
    
    print("\n[4/5] Reconstructing inventory...")
    daily_inv = reconstruct_inventory(raw_inv)
    print(f"    Daily inventory: {len(daily_inv):,} rows")
    
    print("\n[5/5] Validating outputs...")
    sales_val = validate_sales(daily_sales)
    inv_val = validate_inventory(daily_inv)
    
    print("\nSales validation:")
    for k, v in sales_val.items():
        print(f"  {k}: {v}")
    
    print("\nInventory validation:")
    for k, v in inv_val.items():
        print(f"  {k}: {v}")
    
    all_ok = (len(sales_val["issues"]) == 0 and len(inv_val["issues"]) == 0)
    
    if not all_ok:
        print("\nVALIDATION FAILED!")
        return 1
    
    print("\nSaving...")
    daily_sales.to_parquet(PROCESSED_DIR / "daily_sales.parquet", index=False)
    daily_inv.to_parquet(PROCESSED_DIR / "daily_inventory.parquet", index=False)
    print("Done!")
    
    return 0


if __name__ == "__main__":
    exit(main())