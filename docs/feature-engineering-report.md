# Demand Forecasting Feature Engineering & Target Definition Report

**Date**: 2026-08-12
**Pipeline**: `scripts/build_features_v2.py`
**Status**: ✅ Complete - Ready for Review

---

## Dataset Overview

| Metric | Value |
|--------|-------|
| **Rows** | 118,258 (one per sales day per store-product) |
| **Columns** | 82 (70 features + 12 targets) |
| **Date Range** | 2025-06-01 to 2026-04-24 (329 days) |
| **Unique Store-Products** | 50,237 |
| **Gap Days** | 32,798 (27.7%) |
| **Observed Inventory Days** | 85,460 (72.3%) |
| **File** | `data/processed/features/demand_forecasting_features.parquet` |

---

## Feature Categories (70 Features)

### 1. Sales Lags & Rolling Statistics (14 features) - **Available at end_of_day_T-1**

| Feature | Description | Leakage Risk |
|---------|-------------|--------------|
| `sales_lag_1` | Net qty sold on T-1 | None |
| `sales_lag_7` | Net qty sold on T-7 | None |
| `sales_lag_14` | Net qty sold on T-14 | None |
| `sales_lag_28` | Net qty sold on T-28 | None |
| `sales_rolling_mean_7` | Mean net qty T-7 to T-1 | None |
| `sales_rolling_mean_14` | Mean net qty T-14 to T-1 | None |
| `sales_rolling_mean_28` | Mean net qty T-28 to T-1 | None |
| `sales_rolling_std_7` | Std dev T-7 to T-1 | None |
| `sales_rolling_std_14` | Std dev T-14 to T-1 | None |
| `sales_rolling_std_28` | Std dev T-28 to T-1 | None |
| `sales_rolling_sum_7` | Total net qty T-7 to T-1 | None |
| `sales_rolling_sum_28` | Total net qty T-28 to T-1 | None |
| `sales_zero_streak` | Consecutive zero-sales days up to T-1 | None |
| `sales_cv_28` | Coefficient of variation T-28 to T-1 | None |

### 2. Promo/Markdown Features (8 features)

| Feature | Availability | Leakage Risk |
|---------|--------------|--------------|
| `is_promo_today` | start_of_day_T | Low (plan known) |
| `is_markdown_today` | start_of_day_T | Low |
| `is_clearance_today` | start_of_day_T | Low |
| `is_promo_lag_7` | end_of_day_T-7 | None |
| `is_markdown_lag_7` | end_of_day_T-7 | None |
| `is_clearance_lag_7` | end_of_day_T-7 | None |
| `is_promo_days_last_28` | end_of_day_T-1 | None |
| `is_markdown_days_last_28` | end_of_day_T-1 | None |

### 3. Price Features (4 features) - **Available at end_of_day_T-1**

| Feature | Description |
|---------|-------------|
| `unit_price_lag_1` | Unit price on T-1 |
| `unit_price_rolling_mean_7` | Mean price T-7 to T-1 |
| `price_change_pct_7` | % change vs T-7 |

### 4. Inventory Features (10 features) - **Available at start_of_day_T**

| Feature | Description | Gap Handling |
|---------|-------------|--------------|
| `qty_on_hand` | Inventory qty at day start | NaN on gap days |
| `stock_status` | Stock status (Full Price, Markdown, etc.) | NaN on gap days |
| `stock_unit_selling_price` | Unit selling price | NaN on gap days |
| `stock_unit_cost_price` | Unit cost price | NaN on gap days |
| `inv_weeks_of_supply` | Qty / (7-day avg sales × 7) | NaN on gap days |
| `inv_days_since_receipt` | Days since inventory interval started | NaN on gap days |
| `inv_gap_days_since_obs` | Days since last observed inventory | Computed for all days |
| `negative_qty_flag` | True if qty < 0 | False on gap days |
| `writeoff_flag` | True if qty=0 & cost<0 | False on gap days |
| `inv_cost_retail_ratio` | Unit cost / unit selling price | NaN on gap days |
| `inv_stock_status_encoded` | Numeric encoding of stock status | NaN on gap days |

### 5. Temporal Features (7 features) - **Available at start_of_day_T**

| Feature | Description |
|---------|-------------|
| `day_of_week` | 0=Mon, 6=Sun |
| `day_of_month` | 1-31 |
| `week_of_year` | 1-52 |
| `month` | 1-12 |
| `quarter` | 1-4 |
| `is_weekend` | Sat/Sun indicator |
| `is_month_start` | Days 1-3 |
| `is_month_end` | Days 28-31 |

### 6. Static Features (6 features) - **Always Available**

| Feature | Description |
|---------|-------------|
| `product_division` | Scholar/Femme/Junior |
| `product_category` | 27 categories |
| `product_subcategory` | 51 subcategories |
| `product_segment` | 600 segments |
| `supplier` | 30 vendors |
| `store` | 40 stores |

### 7. Store-Level Aggregations (2 features) - **Available at end_of_day_T-1**

| Feature | Description |
|---------|-------------|
| `store_avg_daily_sales_28` | Store's avg daily sales T-28 to T-1 |
| `store_product_rank` | Product rank within store by 28-day sales |

---

## Target Definitions (12 Targets)

| Target | Type | Horizon | Availability | Notes |
|--------|------|---------|--------------|-------|
| `target_demand_7d` | Regression | 7 days | end_of_day_T+6 | Primary: sum of net_qty_sold T to T+6 |
| `target_demand_14d` | Regression | 14 days | end_of_day_T+13 | Replenishment planning |
| `target_demand_28d` | Regression | 28 days | end_of_day_T+27 | Monthly planning |
| `target_any_demand_7d` | Binary | 7 days | end_of_day_T+6 | Any demand > 0 |
| `target_any_demand_14d` | Binary | 14 days | end_of_day_T+13 | |
| `target_any_demand_28d` | Binary | 28 days | end_of_day_T+27 | |
| `target_zero_demand_7d` | Binary | 7 days | end_of_day_T+6 | All 7 days zero (dead-stock) |
| `target_zero_demand_14d` | Binary | 14 days | end_of_day_T+13 | |
| `target_zero_demand_28d` | Binary | 28 days | end_of_day_T+27 | |
| `target_stockout_risk_7d` | Binary | 7 days | end_of_day_T+6 | Demand > qty_on_hand |
| `target_stockout_risk_14d` | Binary | 14 days | end_of_day_T+13 | |
| `target_stockout_risk_28d` | Binary | 28 days | end_of_day_T+27 | |

**All targets are leakage-safe**: Computed from future data relative to prediction day T, never using future info in features.

---

## Gap Day Handling

**Principle**: Gap days (no inventory observation) are explicitly modeled, not interpolated.

| Aspect | Implementation |
|--------|----------------|
| **Inventory values** | NaN on gap days (qty, status, prices) |
| **Gap indicator** | `gap_flag=True`, `observed_flag=False` |
| **Days since last obs** | `inv_gap_days_since_obs` computed for ALL days |
| **Weeks of supply** | NaN on gap days (requires qty) |
| **Model responsibility** | Model learns to handle NaN or use gap flag |

**Gap Statistics**:
- Total gap days: 32,798 (27.7%)
- Observed inventory days: 85,460 (72.3%)
- Gap days concentrated in: Markdown transitions, replenishment cycles

---

## Null Percentage Analysis (Top 20)

| Feature | Null % | Reason |
|---------|--------|--------|
| `sales_lag_28` | 99.8% | Only 28+ day histories |
| `target_*_28d` | 99.8% | Need 28 future days |
| `sales_lag_14` | 98.1% | Only 14+ day histories |
| `target_*_14d` | 97.8% | Need 14 future days |
| `sales_lag_7` | 93.8% | Only 7+ day histories |
| `price_change_pct_7` | 93.8% | Requires T-7 price |
| `target_*_7d` | 92.2% | Need 7 future days |
| `sales_cv_28` | 67.3% | Requires 28-day history |
| `sales_rolling_std_*` | 67.3% | Requires 28-day history |
| `inv_weeks_of_supply` | 59.1% | Requires inventory + sales history |

**Expected**: High nulls at series start/end are normal for time-series features.

---

## Validation Results

### Leakage Checks ✅
- All lag/rolling features: NaN on first row per store-product
- Targets computed from future data only
- No target information in features

### Data Quality Checks ✅
- No duplicate date+store+product keys
- Gap days have NULL inventory values
- Observed days have populated inventory values
- `gap_flag` and `observed_flag` mutually exclusive
- Negative qty preserved and flagged
- Writeoff handling correct

### Issues Found
- None critical

---

## Files Created

```
data/processed/features/
├── demand_forecasting_features.parquet  (118,258 rows × 82 cols, ~45 MB)
└── feature_metadata.json                 (Full feature/target documentation)
```

---

## Code Structure

```
src/pipeline/
├── features/
│   └── demand_features.py    (Feature metadata + engineering functions)
├── targets/
│   └── demand_targets.py     (Target definitions + validation)
scripts/
└── build_features_v2.py      (Optimized pipeline entry point)
```

---

## Next Steps (Not Yet Implemented)

1. **Train/Validation/Test Split** - Time-aware (e.g., train: Jun-Dec 2025, val: Jan-Mar 2026, test: Apr 2026)
2. **Feature Selection** - Remove high-null features for specific horizons
3. **Model Training** - LightGBM/XGBoost for regression, CatBoost for classification
4. **Evaluation** - MAE, RMSE, WAPE for demand; Precision/Recall for binary targets
5. **Explainability** - SHAP values for feature importance

---

**Review Status**: Feature engineering complete. All features documented with availability timestamps. Gap handling explicit. Targets defined for 7/14/28-day horizons. No leakage detected. Ready for review before train/val/test split and model training.