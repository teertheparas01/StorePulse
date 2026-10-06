"""Clean verification: unique flagged days outside ANY raw writeoff interval."""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
CUTOFF_DATE = pd.Timestamp("2026-04-24")

# Load raw writeoff intervals
raw_inv = pd.read_csv(RAW_DIR / "retail_inventory_ml_apl.csv", 
                      usecols=["Store", "Product No", "Start Date", "End Date", "Qty on hand", "Cost of Stocks"],
                      low_memory=False)
raw_inv["start_date"] = pd.to_datetime(raw_inv["Start Date"], errors="coerce")
raw_inv["end_date"] = pd.to_datetime(raw_inv["End Date"], errors="coerce")
raw_inv = raw_inv.dropna(subset=["start_date", "end_date"]).copy()
far_future = raw_inv["end_date"] > pd.Timestamp("2030-01-01")
raw_inv.loc[far_future, "end_date"] = CUTOFF_DATE

raw_inv = raw_inv.rename(columns={
    "Store": "store", "Product No": "product_no",
    "Qty on hand": "qty_on_hand",
    "Cost of Stocks": "cost_of_stocks",
})

writeoff_raw = raw_inv[
    (raw_inv["qty_on_hand"] == 0) & 
    (raw_inv["cost_of_stocks"] < 0)
][["store", "product_no", "start_date", "end_date"]].copy()

print(f"Raw writeoff intervals: {len(writeoff_raw)}")
print(f"Raw writeoff unique store-products: {writeoff_raw[['store', 'product_no']].drop_duplicates().shape[0]}")

# Load processed writeoff flags
proc_inv = pd.read_parquet(PROCESSED_DIR / "daily_inventory.parquet",
                           columns=["date", "store", "product_no", "writeoff_flag"])

proc_flagged = proc_inv[proc_inv["writeoff_flag"] == True][["date", "store", "product_no"]].copy()
proc_flagged["date"] = pd.to_datetime(proc_flagged["date"])
proc_flagged = proc_flagged.drop_duplicates()

print(f"Processed writeoff unique flagged days: {len(proc_flagged)}")
print(f"Processed writeoff unique store-products: {proc_flagged[['store', 'product_no']].drop_duplicates().shape[0]}")

# For each unique flagged day, check if it falls in ANY raw writeoff interval for that store-product
# Use interval tree approach: sort intervals and use searchsorted, or just merge and check
merged = proc_flagged.merge(writeoff_raw, on=["store", "product_no"], how="left")

# A flagged day is "in interval" if date >= start_date AND date <= end_date for ANY matching interval
merged["in_some_interval"] = (merged["date"] >= merged["start_date"]) & (merged["date"] <= merged["end_date"])

# Group by the flagged day to see if ANY interval matches
flagged_coverage = merged.groupby(["store", "product_no", "date"])["in_some_interval"].any().reset_index()

in_any = flagged_coverage["in_some_interval"].sum()
out_any = (~flagged_coverage["in_some_interval"]).sum()

print(f"\n=== UNIQUE FLAGGED DAYS COVERAGE ===")
print(f"In at least one raw writeoff interval: {in_any}")
print(f"Outside ALL raw writeoff intervals: {out_any}")

if out_any > 0:
    outside = flagged_coverage[~flagged_coverage["in_some_interval"]]
    print(f"\nOutside store-products: {outside[['store', 'product_no']].drop_duplicates().shape[0]}")
    print(f"\nSample outside days:")
    print(outside.head(20).to_string())
    
    # For these outside days, what are the raw intervals for that store-product?
    sample_out = outside.head(5)
    for _, row in sample_out.iterrows():
        store = row["store"]
        product = row["product_no"]
        date = row["date"]
        raw_intervals = writeoff_raw[(writeoff_raw["store"] == store) & (writeoff_raw["product_no"] == product)]
        print(f"\n  {store}-{product} on {date.date()}:")
        for _, iv in raw_intervals.iterrows():
            print(f"    Raw writeoff: {iv['start_date'].date()} to {iv['end_date'].date()}")

# Also check: are there raw writeoff intervals that got ZERO flags in processed?
print(f"\n=== RAW INTERVALS WITH ZERO PROCESSED FLAGS ===")
# For each raw interval, count how many processed flagged days fall in it
merged_all = proc_flagged.merge(writeoff_raw, on=["store", "product_no"], how="inner")
merged_all["in_interval"] = (merged_all["date"] >= merged_all["start_date"]) & (merged_all["date"] <= merged_all["end_date"])
in_interval = merged_all[merged_all["in_interval"]]

counts_per_raw = in_interval.groupby(["store", "product_no", "start_date", "end_date"]).size().reset_index(name="flagged_days")
writeoff_with_counts = writeoff_raw.merge(counts_per_raw, on=["store", "product_no", "start_date", "end_date"], how="left")
writeoff_with_counts["flagged_days"] = writeoff_with_counts["flagged_days"].fillna(0).astype(int)
writeoff_with_counts["expected_days"] = (writeoff_with_counts["end_date"] - writeoff_with_counts["start_date"]).dt.days + 1

zero_coverage = writeoff_with_counts[writeoff_with_counts["flagged_days"] == 0]
print(f"Raw writeoff intervals with zero processed flags: {len(zero_coverage)}")

if len(zero_coverage) > 0:
    print(zero_coverage.head(10).to_string())

# Full coverage stats
print(f"\n=== COVERAGE STATS ===")
print(f"Raw intervals total: {len(writeoff_with_counts)}")
print(f"With full coverage (flagged == expected): {(writeoff_with_counts['flagged_days'] == writeoff_with_counts['expected_days']).sum()}")
print(f"With partial coverage: {((writeoff_with_counts['flagged_days'] > 0) & (writeoff_with_counts['flagged_days'] < writeoff_with_counts['expected_days'])).sum()}")
print(f"With zero coverage: {len(zero_coverage)}")
print(f"With extra coverage (flagged > expected): {(writeoff_with_counts['flagged_days'] > writeoff_with_counts['expected_days']).sum()}")