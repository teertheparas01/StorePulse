"""Verify writeoff_flag logic - optimized version."""

from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
CUTOFF_DATE = pd.Timestamp("2026-04-24")

# Load raw inventory - only needed columns
raw_inv = pd.read_csv(
    RAW_DIR / "retail_inventory_ml_apl.csv",
    usecols=["Store", "Product No", "Start Date", "End Date", "Qty on hand", "Cost of Stocks"],
    low_memory=False,
)
raw_inv["start_date"] = pd.to_datetime(raw_inv["Start Date"], errors="coerce")
raw_inv["end_date"] = pd.to_datetime(raw_inv["End Date"], errors="coerce")
raw_inv = raw_inv.dropna(subset=["start_date", "end_date"]).copy()

far_future = raw_inv["end_date"] > pd.Timestamp("2030-01-01")
raw_inv.loc[far_future, "end_date"] = CUTOFF_DATE

raw_inv = raw_inv.rename(
    columns={
        "Store": "store",
        "Product No": "product_no",
        "Qty on hand": "qty_on_hand",
        "Cost of Stocks": "cost_of_stocks",
    }
)

# Original writeoff records
writeoff_raw = raw_inv[(raw_inv["qty_on_hand"] == 0) & (raw_inv["cost_of_stocks"] < 0)].copy()

print("=== ORIGINAL WRITEOFF RECORDS ===")
print(f"Count: {len(writeoff_raw)}")
print(f"Unique Store-Product: {writeoff_raw[['store', 'product_no']].drop_duplicates().shape[0]}")

# Load processed - only needed columns
proc_inv = pd.read_parquet(
    PROCESSED_DIR / "daily_inventory.parquet",
    columns=["date", "store", "product_no", "writeoff_flag", "observed_flag", "gap_flag"],
)

writeoff_proc = proc_inv[proc_inv["writeoff_flag"]]
print("\n=== PROCESSED WRITEOFF FLAGS ===")
print(f"Count: {len(writeoff_proc)}")
print(f"Unique Store-Product: {writeoff_proc[['store', 'product_no']].drop_duplicates().shape[0]}")

# Vectorized check: for each raw writeoff, count flagged days in interval
# Create interval key for raw
writeoff_raw["interval_key"] = list(
    zip(
        writeoff_raw["store"],
        writeoff_raw["product_no"],
        writeoff_raw["start_date"],
        writeoff_raw["end_date"],
        strict=False,
    )
)

# For processed, we need to check which interval each flagged day belongs to
# Merge flagged dates with raw intervals
proc_flagged = writeoff_proc[["date", "store", "product_no"]].copy()
proc_flagged["date"] = pd.to_datetime(proc_flagged["date"])

# Merge on store+product
merged = proc_flagged.merge(
    writeoff_raw[["store", "product_no", "start_date", "end_date"]],
    on=["store", "product_no"],
    how="left",
)

# Check if flagged date falls within any raw writeoff interval for that store-product
merged["in_interval"] = (merged["date"] >= merged["start_date"]) & (
    merged["date"] <= merged["end_date"]
)

# For each raw writeoff record, how many flagged days in its interval?
in_interval = merged[merged["in_interval"]]
flagged_per_raw = (
    in_interval.groupby(["store", "product_no", "start_date", "end_date"])
    .size()
    .reset_index(name="flagged_count")
)

# Expected days per raw writeoff
writeoff_raw["expected_days"] = (writeoff_raw["end_date"] - writeoff_raw["start_date"]).dt.days + 1

# Compare
check = writeoff_raw[["store", "product_no", "start_date", "end_date", "expected_days"]].merge(
    flagged_per_raw, on=["store", "product_no", "start_date", "end_date"], how="left"
)
check["flagged_count"] = check["flagged_count"].fillna(0).astype(int)
check["match"] = check["flagged_count"] == check["expected_days"]

print("\n=== PER INTERVAL MATCH ===")
print(f"Total raw writeoff intervals: {len(check)}")
print(f"Perfect match: {check['match'].sum()}")
print(f"Mismatch: {(~check['match']).sum()}")

mismatches = check[~check["match"]]
if len(mismatches) > 0:
    print("\nMismatches:")
    for _, m in mismatches.head(20).iterrows():
        print(
            f"  {m['store']}-{m['product']} | {m['start_date'].date()} to {m['end_date'].date()} | expected {m['expected_days']}, got {m['flagged_count']}"
        )

# Check for writeoff flags OUTSIDE any raw writeoff interval
outside = merged[not merged["in_interval"]]
print("\n=== FLAGGED DAYS OUTSIDE RAW INTERVALS ===")
print(f"Count: {len(outside)}")
if len(outside) > 0:
    print(outside.groupby(["store", "product_no"]).size().reset_index(name="count").to_string())

# Check writeoff on gap days
gap_writeoff = proc_inv[(proc_inv["gap_flag"]) & (proc_inv["writeoff_flag"])]
print("\n=== WRITEOFF ON GAP DAYS ===")
print(f"Count: {len(gap_writeoff)}")

# Concrete examples - first 10 raw writeoff records
print("\n=== CONCRETE EXAMPLES (first 10 raw writeoff records) ===")
for _, w in writeoff_raw.head(10).iterrows():
    store = w["store"]
    product = w["product_no"]
    start = w["start_date"]
    end = w["end_date"]
    expected = w["expected_days"]

    proc_subset = proc_inv[
        (proc_inv["store"] == store)
        & (proc_inv["product_no"] == product)
        & (proc_inv["date"] >= start)
        & (proc_inv["date"] <= end)
    ]

    flagged = proc_subset["writeoff_flag"].sum()
    gaps = proc_subset["gap_flag"].sum()
    obs = proc_subset["observed_flag"].sum()

    # Get actual flagged dates
    flagged_dates = proc_subset[proc_subset["writeoff_flag"]]["date"].dt.date.tolist()

    print(f"\n{store} - {product}")
    print(f"  Raw interval: {start.date()} to {end.date()} ({expected} days)")
    print(f"  Raw: Qty={w['qty_on_hand']}, Cost={w['cost_of_stocks']:.2f}")
    print(f"  Processed in interval: {len(proc_subset)} rows (obs={int(obs)}, gap={int(gaps)})")
    print(f"  Writeoff flagged: {int(flagged)} days")
    if len(flagged_dates) <= 15:
        print(f"  Dates: {flagged_dates}")
    else:
        print(f"  Dates: {flagged_dates[:5]} ... {flagged_dates[-5:]}")

# Summary counts
print("\n=== SUMMARY COUNTS ===")
print(f"Raw writeoff records: {len(writeoff_raw)}")
print(f"Processed writeoff flags: {len(writeoff_proc)}")
print(f"Expansion ratio: {len(writeoff_proc) / len(writeoff_raw):.1f}x")
print(
    f"Raw unique store-products: {writeoff_raw[['store', 'product_no']].drop_duplicates().shape[0]}"
)
print(
    f"Proc unique store-products: {writeoff_proc[['store', 'product_no']].drop_duplicates().shape[0]}"
)
