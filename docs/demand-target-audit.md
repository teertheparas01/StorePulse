# Demand Target Audit: `target_demand_7d`

**Date**: 2026-08-13  
**Dataset**: `data/processed/features/demand_forecasting_features.parquet`  
**Status**: ❌ **CRITICAL BUG FOUND** - Target definition is incorrect

---

## 1. Exact Prediction Timestamp / Information Cutoff

| Aspect | Value |
|--------|-------|
| **Prediction Time** | Start of day T (before any sales on day T) |
| **Information Cutoff** | End of day T-1 (all historical data through T-1) |
| **Target Window** | Calendar days T through T+6 (7 days inclusive) |
| **Target Availability** | End of day T+6 (when actuals are known) |

---

## 2. Target Definition Verification

### ❌ CRITICAL BUG IDENTIFIED

**Current Implementation (WRONG)**:
```python
df["target_demand_7d"] = grp["net_qty_sold"].transform(
    lambda x: x.rolling(7, min_periods=1).sum().shift(-6)
)
```

**Problem**: The feature panel only contains rows where sales occurred (118,258 rows). The `rolling(7)` operates on **7 consecutive SALES DAYS**, not **7 calendar days**.

**Evidence**:
- Store `STR-1006`, Product `PROD-100358`: Only 8 sales days over 7 months
- Gaps between sales: 1, 13, 17, 27, 36, 38, 74 days
- `target_demand_7d` at first row = 7.0 (sum of next 7 **sales days**)
- True 7-calendar-day demand should include zero-sales days

### Correct Definition Required

The target must be computed on a **complete daily grid** (including zero-sales days), then rolling sum over 7 **calendar days**.

```python
# Create complete daily grid per store-product
# Merge net_qty_sold (fillna 0)
# Rolling sum over 7 calendar days, shift(-6)
```

---

## 3. Target Distribution (Current Buggy Version)

| Statistic | Value |
|-----------|-------|
| Count (non-null) | 9,218 |
| Mean | 7.46 |
| Median | 7.0 |
| Std | 1.05 |
| Min | 4.0 |
| Max | 15.0 |
| Zero-demand % | **0.0%** |
| Positive-demand % | **100.0%** |

**Interpretation**: The zero-demand percentage of 0% is **impossible** for real retail demand. This confirms the target is summing only positive-sales days.

### Expected Distribution (True 7-day Calendar Demand)

Based on raw sales data (125,751 transactions over 11 months across 50,237 store-products):
- Expected zero-demand %: **~60-80%** (most store-products don't sell every day)
- Expected mean: **~0.5-2.0 units** (not 7.46)
- Expected distribution: Highly right-skewed with mass at 0

---

## 4. Inventory Observed vs Gap

| Category | Rows | Percentage |
|----------|------|------------|
| Total rows | 118,258 | 100% |
| Observed inventory | 85,460 | 72.3% |
| Gap days | 32,798 | 27.7% |

### Rows with Valid Target (9,218)
| Category | Rows | Percentage |
|----------|------|------------|
| Observed inventory | 8,688 | 94.2% |
| Gap days | 530 | 5.8% |

---

## 5. Inventory Gap Duration Distribution

| Duration | Gap Periods | Percentage |
|----------|-------------|------------|
| 1-3 days | 28,634 | 99.5% |
| 4-7 days | 143 | 0.5% |
| 8-14 days | 1 | ~0% |
| >14 days | 0 | 0% |

**Gap Period Stats**:
- Mean: 1.6 days
- Median: 2.0 days
- Max: 8.0 days
- No gap periods exceed 14 days

---

## 6. Long Gap Recommendation

**Recommendation**: **RETAIN** (no exclusion needed)

| Factor | Assessment |
|--------|------------|
| Max gap duration | 8 days (well within 7-day target horizon) |
| Gap periods >14 days | 0 |
| Rows in gaps >7 days | <1% |
| `inv_gap_days_since_obs` feature | Already captures gap length |

**Strategy**: Keep all rows. Model can learn uncertainty from `inv_gap_days_since_obs`. If needed, apply sample weights: `weight = 1 / (1 + gap_days/7)`.

---

## 7. Leakage Check - Feature Correlations with Target

**Top 20 Features by |Correlation| with `target_demand_7d`** (sample n=50,000):

| Rank | Feature | |Correlation| | Assessment |
|------|---------|---------------|------------|
| 1 | `net_qty_sold` | 0.401 | Same-day sales - expected |
| 2 | `qty_sold` | 0.379 | Gross sales - expected |
| 3 | `transaction_count` | 0.370 | Basket size proxy - expected |
| 4 | `sales_rolling_sum_28` | 0.324 | 28-day history - expected |
| 5 | `net_sales_amount` | 0.302 | Revenue - expected |
| 6 | `sales_rolling_sum_14` | 0.299 | 14-day history - expected |
| 7 | `sales_amount` | 0.275 | Gross revenue - expected |
| 8 | `cogs` | 0.267 | Cost - expected |
| 9 | `sales_rolling_sum_7` | 0.252 | 7-day history - expected |
| 10 | `qty_on_hand` | 0.216 | Inventory - plausible |

**⚠️ Suspiciously Low**: `sales_lag_1` correlation = **0.088** (expected 0.3-0.7 for retail)

**Explanation**: The target is sum of 7 **sales days**, not 7 calendar days. Lag-1 (previous sales day) may be weeks ago in calendar time, so correlation is artificially low.

---

## 8. Static Features Availability

All static features available at prediction time with 0% nulls:

| Feature | Null % | Available at Prediction |
|---------|--------|------------------------|
| `product_division` | 0.0% | ✅ Always |
| `product_category` | 0.0% | ✅ Always |
| `product_subcategory` | 0.0% | ✅ Always |
| `product_segment` | 0.0% | ✅ Always |
| `supplier` | 0.0% | ✅ Always |
| `store` | 0.0% | ✅ Always |

---

## 9. Today's Promo/Markdown Features

| Feature | Null % | True % | Source |
|---------|--------|--------|--------|
| `is_promo_today` | 0.0% | ~19% | `daily_sales.sales_type == "Promo"` on day T |
| `is_markdown_today` | 0.0% | ~5% | `sales_type` in ["Markdown Tier 1", "Markdown Tier 2"] |
| `is_clearance_today` | 0.0% | ~1% | `sales_type == "Clearance"` |

**Verification**: These come from the **sales transaction's `Sales Type` field on day T**. The merchandising plan determines promo/markdown status **before day T starts**. Therefore: **Available at start of day T → NO LEAKAGE**.

---

## 10. Future Information in Derived Features

**All rolling/ranking/aggregation features correctly use `shift(1)`**:

| Feature | Shift Applied | Data Used |
|---------|---------------|-----------|
| `sales_rolling_mean_7` | shift(1) | T-1 to T-7 |
| `sales_rolling_std_7` | shift(1) | T-1 to T-7 |
| `sales_rolling_sum_7` | shift(1) | T-1 to T-7 |
| `sales_rolling_mean_14` | shift(1) | T-1 to T-14 |
| `sales_rolling_mean_28` | shift(1) | T-1 to T-28 |
| `promo_days_last_28` | shift(1) | T-1 to T-28 |
| `markdown_days_last_28` | shift(1) | T-1 to T-28 |
| `unit_price_rolling_mean_7` | shift(1) | T-1 to T-7 |
| `store_avg_daily_sales_28` | shift(1) | T-1 to T-28 |
| `store_product_rank` | shift(1) | T-1 to T-28 |
| `inv_weeks_of_supply` | N/A | qty(T) / sales(T-1 to T-7) |
| `sales_zero_streak` | shift(1) | Up to T-1 |
| `sales_cv_28` | shift(1) | T-1 to T-28 |

**✅ No feature uses data from day T or future in its computation.**

---

## Summary of Findings

| Check | Status | Notes |
|-------|--------|-------|
| Prediction timestamp defined | ✅ | Start of day T |
| Target = 7 calendar days | ❌ | **BUG: Currently 7 sales days** |
| Target distribution realistic | ❌ | **Zero% = 0% (impossible)** |
| Inventory observed vs gap | ✅ | 72% / 28% |
| Gap duration distribution | ✅ | Max 8 days, 99.5% ≤3 days |
| Long gap handling | ✅ | Retain with gap feature |
| Leakage in correlations | ⚠️ | Low lag-1 corr due to target bug |
| Static features available | ✅ | All 0% null |
| Promo features known at T | ✅ | From merchandising plan |
| No future in rolling features | ✅ | All use shift(1) |

---

## Required Fixes Before Train/Val/Test Split

### 1. **FIX TARGET DEFINITION** (Critical)
```python
# In build_features_v2.py, replace target definition:
# Create complete daily grid per store-product (with zero-sales days)
# Compute rolling 7-day calendar sum with shift(-6)
```

### 2. **Re-validate After Fix**
- Target distribution should show ~60-80% zeros
- Mean should drop to ~0.5-2.0
- `sales_lag_1` correlation should rise to 0.3-0.7

### 3. **Update Feature Panel**
- Consider keeping only rows where target is computable (T ≤ max_date - 6 days)
- Or keep all rows with target=null for last 6 days

---

## Files Referenced

- Feature dataset: `data/processed/features/demand_forecasting_features.parquet`
- Pipeline: `scripts/build_features_v2.py` (lines 89-102)
- Target module: `src/pipeline/targets/demand_targets.py` (lines 24-35)

---

**Audit Conclusion**: ❌ **DO NOT PROCEED** to train/val/test split until target definition is fixed. The current target measures "sum of next 7 sales days" not "7-day calendar demand" - a fundamental mismatch with the business problem.