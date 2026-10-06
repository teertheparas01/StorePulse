# Inventory Data Deep Investigation Report

**Date**: 2026-08-10
**Dataset**: `retail_inventory_ml_apl.csv` (284,755 records)

---

## 1. Interval Structure Overview

### Key Findings
- **No overlapping intervals**: 0 overlaps found across 223,787 consecutive record pairs
- **Gaps are pervasive**: 8,607 gaps (3.8% of consecutive pairs) with median 19 days, max 298 days
- **Same-day records**: 34,998 records (12.3%) have Start Date = End Date
- **Far-future end dates**: 22,701 records (8.0%) have End Date = 9999-12-31
- **Records per Store-Product**: Mean 4.67, max 86 (heavily right-skewed)
- **Multi-record months**: 50.8% of Store-Product-Months have >1 inventory record

### Interpretation
The inventory data represents **period-based snapshots**, not continuous daily records. Each record = a period where stock status/quantity was stable. Gaps between periods are normal (replenishment cycles, status changes). Same-day records appear to be daily snapshots (likely stockout checks or replenishment events).

---

## 2. Overlap Analysis

**Result: NO OVERLAPS** (0 instances)

- Consecutive records for the same Store+Product never overlap
- Next record's Start Date is always > current record's End Date (or exactly +1 day)
- This means: **at most one inventory record covers any given date** for a Store+Product

**Implication**: Daily reconstruction via forward-fill is unambiguous — no conflicts to resolve.

---

## 3. Gap Analysis

| Metric | Value |
|--------|-------|
| Gap instances | 8,607 (3.8% of consecutive pairs) |
| Mean gap | 34.8 days |
| Median gap | 19 days |
| Max gap | 298 days |

### Gap Status Transitions
| From Status | To Status | Count |
|-------------|-----------|-------|
| Full Price | Full Price | 1,345 |
| Full Price | Markdown Tier 1 | 15 |
| Markdown Tier 1 | Markdown Tier 1 | 20 |
| Markdown Tier 1 | Clearance | 5 |
| Clearance | Markdown Tier 1 | 1 |
| ... | ... | ... |

**Key insight**: Most gaps occur within same status (Full Price → Full Price), suggesting gaps represent **replenishment cycles** where stock was not tracked, not status changes.

---

## 4. Same-Day Records (Start = End)

- **Count**: 34,998 (12.3% of all records)
- **Status breakdown**:
  - Full Price: 32,607 (93.2%)
  - Markdown Tier 1: 889
  - Clearance: 845
  - Markdown Tier 2: 649
  - Promo: 8

**Interpretation**: These are likely **daily inventory snapshots** taken during active selling periods (especially for fast-moving SKUs). They capture day-level stock positions.

---

## 5. Far-Future End Dates (9999-12-31)

- **Count**: 22,701 (8.0%)
- **Max 1 per Store-Product pair** — each product-store has at most one "current" record
- **Status**: Mostly Full Price (19,981), some in markdown/clearance
- **Meaning**: "Currently active" inventory period extending to present/unknown end

**Handling for reconstruction**: Treat as open-ended; cap at analysis date (2026-04-24).

---

## 6. Stock Status Transitions

**Total pairs with transitions**: 60,968 (all pairs have at least one record; many have transitions)

| Transition | Count | Interpretation |
|------------|-------|----------------|
| Full Price → Markdown Tier 1 | 3,584 | First markdown |
| Markdown Tier 1 → Clearance | 1,866 | Deep markdown |
| Full Price → Markdown Tier 2 | 1,707 | Second markdown tier |
| Clearance → Markdown Tier 1 | 868 | Status reversal (replenishment?) |
| Markdown Tier 1 → Full Price | 756 | Return to full price (replenishment?) |
| Markdown Tier 2 → Full Price | 537 | Return to full price |
| Clearance → Full Price | 504 | Return to full price |

**Pattern**: Clear lifecycle (Full Price → Markdown → Clearance) with occasional reversions (likely new stock receipts at full price).

---

## 7. Negative Qty on Hand (1,380 records, 0.48%)

| Qty | Count |
|-----|-------|
| -1 | 1,129 |
| -2 | 166 |
| -3 | 55 |
| -4 | 20 |
| -5 | 6 |
| -6 | 1 |
| -7 | 1 |
| -9 | 2 |

- **Status**: Mostly Full Price (1,078), some in markdown tiers
- **Divisions**: Scholar Footwear (567), Junior Apparel (520), Femme Footwear (293)

**Hypothesis**: Negative qty = **returns exceeding on-hand** or **data entry for return adjustments**. The -1 dominates (82%), matching return qty of -1 in sales data.

**Sales alignment check needed**: Cross-reference with return transactions.

---

## 8. Negative Cost of Stocks (8,022 records, 2.8%)

### Breakdown
- **With negative qty**: 1,376 (17.1%) — aligns with negative qty records
- **With zero qty**: 6,625 (82.6%) — **zero stock but negative cost**
- **With positive qty**: 21 (0.3%)

### Zero Qty + Negative Cost (6,625 records)
- Cost values: median -$0.22, max -$418.95 (mostly tiny negative amounts)
- Status: Mostly Full Price (7,075 of 8,022)
- **Pattern**: When Qty=0, Cost of Stocks should be 0. Negative cost suggests:
  - Write-offs/adjustments for damaged/expired stock
  - Accrued cost reversals
  - Data quality issue (cost recorded without qty)

---

## 9. Negative Stock Unit Cost Price (25 records, 0.009%)

All 25 have:
- Qty on hand = 1 or -1
- Cost of Stocks = negative (matching unit cost × qty)
- Specific products: PROD-161863, PROD-161864, PROD-161865, PROD-166366, PROD-176441, PROD-176442, PROD-176443, PROD-185773, PROD-165035, PROD-165036, PROD-156688
- **Likely**: Specific vendor/cost data errors for ~11 SKUs

---

## 10. Zero Qty on Hand (13,869 records, 4.9%)

| Status | Count |
|--------|-------|
| Full Price | 12,653 |
| Markdown Tier 2 | 593 |
| Markdown Tier 1 | 572 |
| Clearance | 51 |

- **Duration**: Median 64 days, heavily skewed by far-future end dates
- **Same-day zero qty**: 365 records (likely stockout snapshots)
- **Interpretation**: Genuine stockouts (mostly Full Price = active selling, stock depleted)

---

## 11. Daily Reconstruction Feasibility

### Can we build a defensible daily inventory panel?

**YES, with caveats:**

| Approach | Feasibility | Notes |
|----------|-------------|-------|
| **Forward-fill from period snapshots** | ✅ High | No overlaps = unambiguous |
| **Gap handling** | ⚠️ Medium | 3.8% of periods have gaps (median 19 days). Options: (a) carry forward last known, (b) interpolate, (c) mark as unknown |
| **Same-day records** | ✅ High | Provide daily granularity for fast movers |
| **Far-future end dates** | ✅ High | Cap at analysis date (2026-04-24) |
| **Negative qty/cost** | ⚠️ Medium | Need business logic: treat as 0? keep as signal? separate flag? |

### Recommended Reconstruction Strategy

```python
# For each Store+Product:
# 1. Sort by Start Date
# 2. For each day from min(Start) to min(max(End), 2026-04-24):
#    - If covered by a record: use that record's values
#    - If in gap:
#        * Option A: Forward-fill last known (conservative)
#        * Option B: Linear interpolate qty (risky)
#        * Option C: Mark as NaN with gap flag
# 3. Flag negative qty/cost as data quality issues
# 4. Add derived fields: days_since_receipt, stock_status, weeks_of_supply
```

### Coverage Estimate
- **Continuous periods**: ~96% of Store-Product timelines covered by records
- **Gaps**: ~4% of timeline (median 19 days) — need imputation strategy
- **Same-day snapshots**: Provide true daily data for ~12% of records

---

## 12. Multi-Record Months

- **50.8% of Store-Product-Months** have multiple inventory records
- Max 19 records in a single month for one Store-Product
- **Reason**: Status changes (markdowns), replenishments, same-day snapshots

---

## 13. Records per Store-Product

| Stat | Value |
|------|-------|
| Mean | 4.67 |
| Median | 3 |
| Max | 86 |
| Pairs with 1 record | ~15% |
| Pairs with >10 records | ~5% |

High-record pairs = fast-moving SKUs with frequent status changes + daily snapshots.

---

## 14. Conclusions & Recommendations

### Defensible Daily Reconstruction: **YES, possible**

**No invented data required** if we:
1. Forward-fill within recorded periods (no overlaps = clean)
2. Explicitly flag gap days (don't interpolate silently)
3. Cap far-future at analysis cutoff
4. Handle negatives as explicit quality flags, not imputed values

### Required Decisions Before Pipeline

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Gap days | Forward-fill / NaN / Interpolate | **NaN + gap_flag** (preserves honesty) |
| Negative qty | Set to 0 / Keep / Separate flag | **Keep + return_flag** (aligns with sales returns) |
| Negative cost (zero qty) | Set to 0 / Keep / Separate flag | **Set to 0 + writeoff_flag** |
| Far-future end | Cap at 2026-04-24 / Extend | **Cap at analysis date** |
| Same-day records | Treat as daily / Aggregate | **Use as daily snapshots** |

### ML Feature Implications

| Feature | Supported? | Notes |
|---------|------------|-------|
| Daily stock level | ✅ Yes | With gap flags |
| Stockout history | ✅ Yes | Zero qty records + gap analysis |
| Inventory age | ✅ Yes | From Start Date |
| Markdown progression | ✅ Yes | Stock Status transitions |
| Weeks of supply | ✅ Yes | Qty / daily sales velocity |
| Replenishment detection | ⚠️ Partial | Gaps + status reversions suggest it |
| True daily turns | ❌ No | Gaps prevent exact calculation |

---

## 15. Next Steps

1. **Create processed daily inventory panel** with explicit gap/quality flags
2. **Cross-reference negative qty** with sales returns for validation
3. **Document reconstruction logic** in pipeline code
4. **Validate** against known stockout events (if any external data exists)
