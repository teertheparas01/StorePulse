import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("../data/raw")
inv = pd.read_csv(RAW_DIR / "retail_inventory_ml_apl.csv", low_memory=False)
inv["Start Date"] = pd.to_datetime(inv["Start Date"])
inv["End Date"] = pd.to_datetime(inv["End Date"])

# Systematic overlap/gap check using vectorized operations
inv_sorted = inv.sort_values(["Store", "Product No", "Start Date"]).reset_index(drop=True)

# Get next record's start date for each group
inv_sorted["next_start"] = inv_sorted.groupby(["Store", "Product No"])["Start Date"].shift(-1)
inv_sorted["curr_end"] = inv_sorted["End Date"]

# Check overlaps: next_start <= curr_end
inv_sorted["overlap"] = inv_sorted["next_start"] <= inv_sorted["curr_end"]
inv_sorted["gap_days"] = (inv_sorted["next_start"] - inv_sorted["curr_end"]).dt.days - 1

overlaps = inv_sorted[inv_sorted["overlap"] == True]
gaps = inv_sorted[inv_sorted["gap_days"] > 0]

print("=== SYSTEMATIC OVERLAP/GAP CHECK ===")
total_pairs = inv_sorted["next_start"].notna().sum()
print("Total consecutive record pairs checked:", total_pairs)
print("Overlaps found:", len(overlaps))
print("Gaps found:", len(gaps))

if len(gaps) > 0:
    print("Gap days stats:")
    print(gaps["gap_days"].describe())
    gaps["next_status"] = gaps.groupby(["Store", "Product No"])["Stock Status"].shift(-1)
    print("Gap status transitions:")
    print(gaps.groupby(["Stock Status", "next_status"]).size())

# Check same-day records
same_day = inv[inv["Start Date"] == inv["End Date"]]
print("\nSame-day records (Start=End):", len(same_day))
print("Same-day Stock Status:")
print(same_day["Stock Status"].value_counts())

# Check records per store-product
records_per_pair = inv.groupby(["Store", "Product No"]).size()
print("\nRecords per Store-Product pair:")
print(records_per_pair.describe())

# Check negative qty
neg_qty = inv[inv["Qty on hand"] < 0]
print("\n=== NEGATIVE QTY ON HAND ===")
print("Count:", len(neg_qty))
print("Qty distribution:")
print(neg_qty["Qty on hand"].value_counts().sort_index())
print("Stock Status:")
print(neg_qty["Stock Status"].value_counts())
print("Product Division:")
print(neg_qty["Product Division"].value_counts())

# Check negative cost
neg_cost = inv[inv["Cost of Stocks"] < 0]
print("\n=== NEGATIVE COST OF STOCKS ===")
print("Count:", len(neg_cost))
print("Cost distribution:")
print(neg_cost["Cost of Stocks"].describe())
print("Stock Status:")
print(neg_cost["Stock Status"].value_counts())
print("Product Division:")
print(neg_cost["Product Division"].value_counts())
print("Associated:")
print("  Neg Qty:", (neg_cost["Qty on hand"] < 0).sum())
print("  Zero Qty:", (neg_cost["Qty on hand"] == 0).sum())
print("  Neg Unit Cost:", (neg_cost["Stock Unit Cost Price"] < 0).sum())

# Negative cost only (non-negative qty)
neg_cost_only = neg_cost[neg_cost["Qty on hand"] >= 0]
print("\nNegative cost with non-negative qty:", len(neg_cost_only))
if len(neg_cost_only) > 0:
    print(
        neg_cost_only[
            [
                "Store",
                "Product No",
                "Start Date",
                "End Date",
                "Qty on hand",
                "Cost of Stocks",
                "Stock Unit Cost Price",
                "Stock Status",
            ]
        ]
        .head(20)
        .to_string()
    )

# Negative unit cost price
neg_unit_cost = inv[inv["Stock Unit Cost Price"] < 0]
print("\n=== NEGATIVE STOCK UNIT COST PRICE ===")
print("Count:", len(neg_unit_cost))
print(
    neg_unit_cost[
        [
            "Store",
            "Product No",
            "Start Date",
            "End Date",
            "Qty on hand",
            "Cost of Stocks",
            "Stock Unit Cost Price",
            "Stock Status",
        ]
    ].to_string()
)

# Zero qty
zero_qty = inv[inv["Qty on hand"] == 0]
print("\n=== ZERO QTY ON HAND ===")
print("Count:", len(zero_qty))
print("Stock Status:")
print(zero_qty["Stock Status"].value_counts())
print("Duration days:")
print(
    zero_qty.assign(dur=(zero_qty["End Date"] - zero_qty["Start Date"]).dt.days)["dur"].describe()
)
print("Same-day zero qty:", (zero_qty["Start Date"] == zero_qty["End Date"]).sum())

# Far future end dates
far_future = inv[inv["End Date"] > pd.Timestamp("2030-01-01")]
print("\n=== FAR FUTURE END DATES (9999-12-31) ===")
print("Count:", len(far_future))
print("Stock Status:")
print(far_future["Stock Status"].value_counts())
print("Product Division:")
print(far_future["Product Division"].value_counts())
ff_per_pair = far_future.groupby(["Store", "Product No"]).size()
print("Pairs with far-future:", len(ff_per_pair))
print("Max per pair:", ff_per_pair.max())
print("Pairs with >1:", (ff_per_pair > 1).sum())

# Stock Status distribution
print("\n=== STOCK STATUS DISTRIBUTION ===")
print(inv["Stock Status"].value_counts())

# Stock Status transitions
inv_sorted["next_status"] = inv_sorted.groupby(["Store", "Product No"])["Stock Status"].shift(-1)
transitions = inv_sorted[inv_sorted["Stock Status"] != inv_sorted["next_status"]]
print("\n=== STOCK STATUS TRANSITIONS ===")
print("Pairs with transitions:", transitions[["Store", "Product No"]].drop_duplicates().shape[0])
print("Transition counts:")
trans_counts = (transitions["Stock Status"] + " -> " + transitions["next_status"]).value_counts()
print(trans_counts.head(20))

# Records per store-product per month
inv["YearMonth"] = inv["Start Date"].dt.to_period("M")
monthly = inv.groupby(["Store", "Product No", "YearMonth"]).size().reset_index(name="count")
print("\n=== RECORDS PER STORE-PRODUCT-MONTH ===")
print("Combinations:", len(monthly))
print("Count distribution:")
print(monthly["count"].value_counts().sort_index())
multi = monthly[monthly["count"] > 1]
print("Multi-record months:", len(multi), "(", len(multi) / len(monthly) * 100, "%)")
