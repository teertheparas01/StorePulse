import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("../data/raw")
inv_path = RAW_DIR / "retail_inventory_ml_apl.csv"
sales_path = RAW_DIR / "retail_sales_ml_apl.csv"

inv = pd.read_csv(inv_path, low_memory=False)
sales = pd.read_csv(sales_path, low_memory=False)

inv["Start Date"] = pd.to_datetime(inv["Start Date"])
inv["End Date"] = pd.to_datetime(inv["End Date"])
inv["Duration Days"] = (inv["End Date"] - inv["Start Date"]).dt.days
sales["Transaction Date"] = pd.to_datetime(sales["Transaction Date"])

print("=== BASIC INFO ===")
print(f"Total inventory records: {len(inv)}")
print(f"Unique Store-Product pairs: {inv[['Store', 'Product No']].drop_duplicates().shape[0]}")

# ============ 1. OVERLAP ANALYSIS ============
print("\n=== 1. OVERLAP ANALYSIS ===")


def check_overlaps(group):
    group = group.sort_values("Start Date").reset_index(drop=True)
    overlaps = 0
    overlap_details = []
    for i in range(len(group) - 1):
        curr_end = group.loc[i, "End Date"]
        next_start = group.loc[i + 1, "Start Date"]
        if next_start <= curr_end:
            overlaps += 1
            overlap_days = (curr_end - next_start).days + 1
            overlap_details.append(
                {
                    "record_1_idx": group.index[i],
                    "record_2_idx": group.index[i + 1],
                    "overlap_days": overlap_days,
                    "record_1_status": group.loc[i, "Stock Status"],
                    "record_2_status": group.loc[i + 1, "Stock Status"],
                    "record_1_qty": group.loc[i, "Qty on hand"],
                    "record_2_qty": group.loc[i + 1, "Qty on hand"],
                }
            )
    return pd.Series({"overlap_count": overlaps, "overlap_details": overlap_details})


overlap_results = (
    inv.groupby(["Store", "Product No"]).apply(check_overlaps, include_groups=False).reset_index()
)
total_pairs = len(overlap_results)
pairs_with_overlaps = (overlap_results["overlap_count"] > 0).sum()
total_overlaps = overlap_results["overlap_count"].sum()

print(f"Store-Product pairs: {total_pairs}")
print(f"Pairs with overlaps: {pairs_with_overlaps} ({pairs_with_overlaps/total_pairs*100:.1f}%)")
print(f"Total overlap instances: {total_overlaps}")

all_overlaps = []
for _, row in overlap_results[overlap_results["overlap_count"] > 0].iterrows():
    for detail in row["overlap_details"]:
        all_overlaps.append(detail)

if all_overlaps:
    overlap_df = pd.DataFrame(all_overlaps)
    print(f"\nOverlap days distribution:")
    print(overlap_df["overlap_days"].describe())
    print(f"\nOverlap status combinations:")
    print(overlap_df.groupby(["record_1_status", "record_2_status"]).size())
    print(f"\nSample overlaps:")
    print(overlap_df.head(20).to_string())

# ============ 2. GAP ANALYSIS ============
print("\n=== 2. GAP ANALYSIS ===")


def check_gaps(group):
    group = group.sort_values("Start Date").reset_index(drop=True)
    gaps = []
    for i in range(len(group) - 1):
        curr_end = group.loc[i, "End Date"]
        next_start = group.loc[i + 1, "Start Date"]
        gap_days = (next_start - curr_end).days - 1
        if gap_days > 0:
            gaps.append(
                {
                    "gap_days": gap_days,
                    "record_1_idx": group.index[i],
                    "record_2_idx": group.index[i + 1],
                    "record_1_status": group.loc[i, "Stock Status"],
                    "record_2_status": group.loc[i + 1, "Stock Status"],
                }
            )
    return pd.Series(
        {
            "gap_count": len(gaps),
            "gap_details": gaps,
            "total_gap_days": sum(g["gap_days"] for g in gaps),
        }
    )


gap_results = (
    inv.groupby(["Store", "Product No"]).apply(check_gaps, include_groups=False).reset_index()
)
pairs_with_gaps = (gap_results["gap_count"] > 0).sum()
total_gaps = gap_results["gap_count"].sum()
total_gap_days = gap_results["total_gap_days"].sum()

print(f"Store-Product pairs: {total_pairs}")
print(f"Pairs with gaps: {pairs_with_gaps} ({pairs_with_gaps/total_pairs*100:.1f}%)")
print(f"Total gap instances: {total_gaps}")
print(f"Total gap days: {total_gap_days}")

all_gaps = []
for _, row in gap_results[gap_results["gap_count"] > 0].iterrows():
    for detail in row["gap_details"]:
        all_gaps.append(detail)

if all_gaps:
    gap_df = pd.DataFrame(all_gaps)
    print(f"\nGap days distribution:")
    print(gap_df["gap_days"].describe())
    print(f"\nGap status transitions:")
    print(gap_df.groupby(["record_1_status", "record_2_status"]).size())
    print(f"\nTop 20 largest gaps:")
    print(gap_df.nlargest(20, "gap_days")[["gap_days", "record_1_status", "record_2_status"]])

# ============ 3. MULTI-COVERAGE (same date covered by multiple records) ============
print("\n=== 3. MULTI-COVERAGE ANALYSIS ===")


def check_multi_coverage(group):
    group = group.sort_values("Start Date").reset_index(drop=True)
    multi_covered = 0
    for i in range(len(group)):
        start = group.loc[i, "Start Date"]
        end = group.loc[i, "End Date"]
        covering = group[
            (group["Start Date"] <= start) & (group["End Date"] >= start) & (group.index != i)
        ]
        if len(covering) > 0:
            multi_covered += 1
    return pd.Series({"multi_covered_count": multi_covered})


multi_results = (
    inv.groupby(["Store", "Product No"])
    .apply(check_multi_coverage, include_groups=False)
    .reset_index()
)
pairs_multi = (multi_results["multi_covered_count"] > 0).sum()
total_multi = multi_results["multi_covered_count"].sum()

print(f"Pairs with multi-covered dates: {pairs_multi} ({pairs_multi/total_pairs*100:.1f}%)")
print(f"Total multi-covered date instances: {total_multi}")

# ============ 4. STOCK STATUS ANALYSIS ============
print("\n=== 4. STOCK STATUS DISTRIBUTION ===")
print(inv["Stock Status"].value_counts())
print(f"\nStock Status by Division:")
print(inv.groupby(["Product Division", "Stock Status"]).size().unstack(fill_value=0))


# Status transitions
def get_status_sequence(group):
    group = group.sort_values("Start Date")
    statuses = group["Stock Status"].tolist()
    transitions = []
    for i in range(len(statuses) - 1):
        if statuses[i] != statuses[i + 1]:
            transitions.append(f"{statuses[i]} -> {statuses[i+1]}")
    return pd.Series({"transitions": transitions, "status_sequence": " -> ".join(statuses)})


status_results = (
    inv.groupby(["Store", "Product No"])
    .apply(get_status_sequence, include_groups=False)
    .reset_index()
)
all_transitions = []
for _, row in status_results.iterrows():
    all_transitions.extend(row["transitions"])

print(
    f"\nTotal Store-Product pairs with status changes: {(status_results['transitions'].apply(len) > 0).sum()}"
)
print(f"\nMost common status transitions:")
transition_counts = pd.Series(all_transitions).value_counts()
print(transition_counts.head(20))

# ============ 5. DAILY RECONSTRUCTION FEASIBILITY (sample) ============
print("\n=== 5. DAILY RECONSTRUCTION FEASIBILITY (SAMPLE) ===")

sample_pairs = inv.groupby(["Store", "Product No"]).size().nlargest(10).index.tolist()

for store, product in sample_pairs[:5]:
    subset = inv[(inv["Store"] == store) & (inv["Product No"] == product)].sort_values("Start Date")
    print(f"\n=== {store} - {product} ===")
    print(f"Records: {len(subset)}")
    print(
        subset[
            [
                "Start Date",
                "End Date",
                "Duration Days",
                "Qty on hand",
                "Stock Status",
                "Stock Unit Selling Price",
            ]
        ].to_string()
    )

    min_date = subset["Start Date"].min()
    max_date = subset["End Date"].max()
    max_date_capped = min(max_date, pd.Timestamp("2026-04-24"))
    total_days = (max_date_capped - min_date).days + 1

    covered = 0
    for _, r in subset.iterrows():
        s = max(r["Start Date"], min_date)
        e = min(r["End Date"], max_date_capped)
        if r["End Date"].year > 2030:
            e = max_date_capped
        covered += (e - s).days + 1

    print(f"Date range: {min_date} to {max_date_capped} ({total_days} days)")
    print(f"Covered days: {covered} ({covered/total_days*100:.1f}%)")

# ============ 6. NEGATIVE QTY ON HAND ============
print("\n=== 6. NEGATIVE QTY ON HAND (1,380 records) ===")
neg_qty = inv[inv["Qty on hand"] < 0]
print(f"Negative Qty on hand records: {len(neg_qty)}")
print(f"Unique Store-Product pairs: {neg_qty[['Store', 'Product No']].drop_duplicates().shape[0]}")
print(f"\nQty on hand distribution:")
print(neg_qty["Qty on hand"].value_counts().sort_index())
print(f"\nStock Status:")
print(neg_qty["Stock Status"].value_counts())
print(f"\nProduct Division:")
print(neg_qty["Product Division"].value_counts())
print(f"\nAssociated negative fields:")
print(f"  Negative Stocks Selling Amount: {(neg_qty['Stocks Selling Amount'] < 0).sum()}")
print(f"  Negative Cost of Stocks: {(neg_qty['Cost of Stocks'] < 0).sum()}")
print(f"  Negative Stock Unit Selling Price: {(neg_qty['Stock Unit Selling Price'] < 0).sum()}")
print(f"  Negative Stock Unit Cost Price: {(neg_qty['Stock Unit Cost Price'] < 0).sum()}")

# Check alignment with returns
returns = sales[sales["Is Return"] == 1]
print(f"\n=== Negative Qty vs Returns Alignment (sample) ===")
sample_neg = neg_qty.head(20)
for _, inv_row in sample_neg.iterrows():
    store = inv_row["Store"]
    product = inv_row["Product No"]
    start = inv_row["Start Date"]
    end = inv_row["End Date"]

    period_returns = returns[
        (returns["Store"] == store)
        & (returns["Product No"] == product)
        & (returns["Transaction Date"] >= start)
        & (returns["Transaction Date"] <= end)
    ]

    before_returns = returns[
        (returns["Store"] == store)
        & (returns["Product No"] == product)
        & (returns["Transaction Date"] < start)
        & (returns["Transaction Date"] >= start - pd.Timedelta(days=30))
    ]

    print(
        f"\n{store}-{product} | Inv: {start.date()} to {end.date()} | Qty: {inv_row['Qty on hand']} | Status: {inv_row['Stock Status']}"
    )
    print(
        f"  Returns during period: {len(period_returns)}, Qty: {period_returns['Qty Sold'].sum()}"
    )
    print(f"  Returns 30d before: {len(before_returns)}, Qty: {before_returns['Qty Sold'].sum()}")

# ============ 7. NEGATIVE COST OF STOCKS ============
print("\n=== 7. NEGATIVE COST OF STOCKS (8,022 records) ===")
neg_cost = inv[inv["Cost of Stocks"] < 0]
print(f"Negative Cost of Stocks records: {len(neg_cost)}")
print(f"Unique Store-Product pairs: {neg_cost[['Store', 'Product No']].drop_duplicates().shape[0]}")
print(f"\nCost of Stocks distribution:")
print(neg_cost["Cost of Stocks"].describe())
print(f"\nStock Status:")
print(neg_cost["Stock Status"].value_counts())
print(f"\nProduct Division:")
print(neg_cost["Product Division"].value_counts())
print(f"\nAssociated fields:")
print(f"  Negative Qty on hand: {(neg_cost['Qty on hand'] < 0).sum()}")
print(f"  Negative Stocks Selling Amount: {(neg_cost['Stocks Selling Amount'] < 0).sum()}")
print(f"  Negative Stock Unit Cost Price: {(neg_cost['Stock Unit Cost Price'] < 0).sum()}")
print(f"  Zero Qty on hand: {(neg_cost['Qty on hand'] == 0).sum()}")
print(f"  Zero Stock Unit Cost Price: {(neg_cost['Stock Unit Cost Price'] == 0).sum()}")

both_neg = neg_cost[neg_cost["Qty on hand"] < 0]
print(f"\nRecords with both negative Qty and negative Cost: {len(both_neg)}")
neg_cost_only = neg_cost[neg_cost["Qty on hand"] >= 0]
print(f"Records with negative Cost but non-negative Qty: {len(neg_cost_only)}")

if len(neg_cost_only) > 0:
    print(f"\nSample of negative Cost with non-negative Qty:")
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

# ============ 8. NEGATIVE STOCK UNIT COST PRICE ============
print("\n=== 8. NEGATIVE STOCK UNIT COST PRICE (25 records) ===")
neg_unit_cost = inv[inv["Stock Unit Cost Price"] < 0]
print(f"Negative Stock Unit Cost Price records: {len(neg_unit_cost)}")
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

# ============ 9. ZERO QTY ON HAND ============
print("\n=== 9. ZERO QTY ON HAND (13,869 records) ===")
zero_qty = inv[inv["Qty on hand"] == 0]
print(f"Zero Qty on hand records: {len(zero_qty)}")
print(f"Unique Store-Product pairs: {zero_qty[['Store', 'Product No']].drop_duplicates().shape[0]}")
print(f"\nStock Status:")
print(zero_qty["Stock Status"].value_counts())
print(f"\nDuration days:")
print(zero_qty["Duration Days"].describe())
print(f"Same-day (0 duration): {(zero_qty['Duration Days'] == 0).sum()}")

# ============ 10. RECORDS PER STORE-PRODUCT PER MONTH ============
print("\n=== 10. RECORDS PER STORE-PRODUCT PER MONTH ===")
inv["YearMonth"] = inv["Start Date"].dt.to_period("M")
monthly_counts = (
    inv.groupby(["Store", "Product No", "YearMonth"]).size().reset_index(name="record_count")
)
print(f"Store-Product-Month combinations: {len(monthly_counts)}")
print(f"\nRecord count per Store-Product-Month:")
print(monthly_counts["record_count"].value_counts().sort_index())

multi_record_months = monthly_counts[monthly_counts["record_count"] > 1]
print(
    f"\nStore-Product-Months with multiple records: {len(multi_record_months)} ({len(multi_record_months)/len(monthly_counts)*100:.1f}%)"
)

# ============ 11. END DATE = 9999-12-31 ============
print("\n=== 11. FAR-FUTURE END DATES ===")
far_future = inv[inv["End Date"] > pd.Timestamp("2030-01-01")]
print(
    f"Records with far-future end date (>2030): {len(far_future)} ({len(far_future)/len(inv)*100:.1f}%)"
)
print(f"\nStock Status:")
print(far_future["Stock Status"].value_counts())
print(f"\nProduct Division:")
print(far_future["Product Division"].value_counts())

ff_per_pair = far_future.groupby(["Store", "Product No"]).size().reset_index(name="ff_count")
print(f"\nStore-Product pairs with far-future records: {len(ff_per_pair)}")
print(f"Max far-future records per pair: {ff_per_pair['ff_count'].max()}")
print(f"Pairs with >1 far-future record: {(ff_per_pair['ff_count'] > 1).sum()}")

# ============ 12. COMPREHENSIVE DAILY RECONSTRUCTION TEST ============
print("\n=== 12. DAILY RECONSTRUCTION TEST (Dec 2025) ===")


def build_daily_inventory(store, product, target_month):
    subset = inv[
        (inv["Store"] == store)
        & (inv["Product No"] == product)
        & (inv["Start Date"] <= target_month.to_timestamp() + pd.offsets.MonthEnd(0))
        & (inv["End Date"] >= target_month.to_timestamp())
    ].sort_values("Start Date")

    if len(subset) == 0:
        return None

    days = pd.date_range(
        target_month.to_timestamp(), target_month.to_timestamp() + pd.offsets.MonthEnd(0), freq="D"
    )
    daily = pd.DataFrame({"Date": days})
    daily["Qty on hand"] = np.nan
    daily["Stock Status"] = None
    daily["Stock Unit Selling Price"] = np.nan
    daily["Stock Unit Cost Price"] = np.nan
    daily["Source Record"] = None

    for _, rec in subset.iterrows():
        start = max(rec["Start Date"], days[0])
        end = min(rec["End Date"], days[-1])
        if rec["End Date"].year > 2030:
            end = days[-1]
        mask = (daily["Date"] >= start) & (daily["Date"] <= end)
        conflict = mask & daily["Qty on hand"].notna()
        if conflict.any():
            daily.loc[conflict, "Source Record"] = "CONFLICT"
        daily.loc[mask & ~conflict, "Qty on hand"] = rec["Qty on hand"]
        daily.loc[mask & ~conflict, "Stock Status"] = rec["Stock Status"]
        daily.loc[mask & ~conflict, "Stock Unit Selling Price"] = rec["Stock Unit Selling Price"]
        daily.loc[mask & ~conflict, "Stock Unit Cost Price"] = rec["Stock Unit Cost Price"]
        daily.loc[mask & ~conflict, "Source Record"] = rec.name

    coverage = daily["Qty on hand"].notna().sum()
    conflicts = (daily["Source Record"] == "CONFLICT").sum()
    gaps = daily["Qty on hand"].isna().sum()

    return {
        "daily": daily,
        "coverage": coverage,
        "conflicts": conflicts,
        "gaps": gaps,
        "total_days": len(days),
        "records_used": len(subset),
    }


test_pairs = inv.groupby(["Store", "Product No"]).size().nlargest(20).index.tolist()
test_month = pd.Period("2025-12", freq="M")

results = []
for store, product in test_pairs[:10]:
    result = build_daily_inventory(store, product, test_month)
    if result:
        result["store"] = store
        result["product"] = product
        results.append(result)
        print(
            f"{store}-{product}: Coverage={result['coverage']}/{result['total_days']} ({result['coverage']/result['total_days']*100:.1f}%), Conflicts={result['conflicts']}, Gaps={result['gaps']}, Records={result['records_used']}"
        )

# ============ 13. DETAILED CONFLICT ANALYSIS ============
print("\n=== 13. DETAILED OVERLAP/CONFLICT ANALYSIS ===")

overlap_pairs = []
for (store, product), group in inv.groupby(["Store", "Product No"]):
    group = group.sort_values("Start Date").reset_index(drop=True)
    for i in range(len(group) - 1):
        curr_end = group.loc[i, "End Date"]
        next_start = group.loc[i + 1, "Start Date"]
        if next_start <= curr_end:
            overlap_pairs.append(
                {
                    "Store": store,
                    "Product No": product,
                    "Record 1 Index": group.index[i],
                    "Record 2 Index": group.index[i + 1],
                    "Record 1 Start": group.loc[i, "Start Date"],
                    "Record 1 End": group.loc[i, "End Date"],
                    "Record 2 Start": group.loc[i + 1, "Start Date"],
                    "Record 2 End": group.loc[i + 1, "End Date"],
                    "Overlap Days": (curr_end - next_start).days + 1,
                    "Record 1 Status": group.loc[i, "Stock Status"],
                    "Record 2 Status": group.loc[i + 1, "Stock Status"],
                    "Record 1 Qty": group.loc[i, "Qty on hand"],
                    "Record 2 Qty": group.loc[i + 1, "Qty on hand"],
                }
            )

overlap_df = pd.DataFrame(overlap_pairs)
print(f"Total overlapping interval pairs: {len(overlap_df)}")
print(
    f"Unique Store-Product pairs with overlaps: {overlap_df[['Store', 'Product No']].drop_duplicates().shape[0]}"
)

if len(overlap_df) > 0:
    print(f"\nOverlap days distribution:")
    print(overlap_df["Overlap Days"].describe())
    print(f"\nStatus combinations in overlaps:")
    print(overlap_df.groupby(["Record 1 Status", "Record 2 Status"]).size())
    print(f"\nSample overlaps:")
    print(overlap_df.head(20).to_string())

# ============ 14. SALES-INVENTORY ALIGNMENT IN OVERLAPS ============
print("\n=== 14. SALES IN OVERLAP PERIODS ===")

sample_overlaps = overlap_df.head(10)
for _, ov in sample_overlaps.iterrows():
    store = ov["Store"]
    product = ov["Product No"]
    overlap_start = ov["Record 2 Start"]
    overlap_end = ov["Record 1 End"]

    sales_in_overlap = sales[
        (sales["Store"] == store)
        & (sales["Product No"] == product)
        & (sales["Transaction Date"] >= overlap_start)
        & (sales["Transaction Date"] <= overlap_end)
    ]

    print(
        f"\n{store}-{product} | Overlap: {overlap_start.date()} to {overlap_end.date()} ({ov['Overlap Days']} days)"
    )
    print(
        f"  Rec1: {ov['Record 1 Status']}, Qty={ov['Record 1 Qty']} | Rec2: {ov['Record 2 Status']}, Qty={ov['Record 2 Qty']}"
    )
    print(
        f"  Sales in overlap: {len(sales_in_overlap)} transactions, {sales_in_overlap['Qty Sold'].sum()} units"
    )

# ============ 15. SUMMARY ============
print("\n=== 15. INVENTORY STRUCTURE SUMMARY ===")
print(f"Total records: {len(inv)}")
print(f"Unique Store-Product pairs: {total_pairs}")
print(f"Date range: {inv['Start Date'].min()} to {inv['End Date'].max()}")
print(
    f"Records with End Date = 9999-12-31: {len(far_future)} ({len(far_future)/len(inv)*100:.1f}%)"
)
print(f"\nPairs with overlaps: {pairs_with_overlaps} ({pairs_with_overlaps/total_pairs*100:.1f}%)")
print(f"Total overlap instances: {total_overlaps}")
print(f"\nPairs with gaps: {pairs_with_gaps} ({pairs_with_gaps/total_pairs*100:.1f}%)")
print(f"Total gap instances: {total_gaps}")
print(f"Total gap days: {total_gap_days}")
print(f"\nPairs with multi-covered dates: {pairs_multi} ({pairs_multi/total_pairs*100:.1f}%)")
print(f"\nNegative Qty on hand: {len(neg_qty)} ({len(neg_qty)/len(inv)*100:.2f}%)")
print(f"Negative Cost of Stocks: {len(neg_cost)} ({len(neg_cost)/len(inv)*100:.2f}%)")
print(
    f"Negative Stock Unit Cost Price: {len(neg_unit_cost)} ({len(neg_unit_cost)/len(inv)*100:.3f}%)"
)
print(f"Zero Qty on hand: {len(zero_qty)} ({len(zero_qty)/len(inv)*100:.1f}%)")
print(
    f"\nSame-day records (Duration=0): {(inv['Duration Days'] == 0).sum()} ({(inv['Duration Days'] == 0).sum()/len(inv)*100:.1f}%)"
)
