# Data Reconstruction Pipeline Report

**Date**: 2026-08-10
**Pipeline Version**: 1.0
**Status**: ✅ All Validations Passed

---

## Input Datasets

| Dataset | Source | Rows | Size |
|---------|--------|------|------|
| Sales | `data/raw/retail_sales_ml_apl.csv` | 125,751 | 39.07 MB |
| Inventory | `data/raw/retail_inventory_ml_apl.csv` | 284,755 | 99.99 MB |

---

## Output Datasets

### 1. Daily Sales: `data/processed/daily_sales.parquet`

| Metric | Value |
|--------|-------|
| Rows | 118,258 |
| Date Range | 2025-06-01 to 2026-04-24 |
| Unique Store-Product | 50,237 |
| Duplicate Keys | 0 |
| File Size | ~8.2 MB |

**Aggregation Logic**:
- Aggregated to daily + store + product level
- 1,823 duplicate keys in raw data handled by summing quantities/amounts
- Returns separated: `return_qty` (positive), `return_amount` (positive)
- Net values: `net_qty_sold = qty_sold - return_qty`, `net_sales_amount = sales_amount - return_amount`
- Unit price/cost computed where qty > 0
- Promo/markdown/clearance flags preserved

**Columns**:
```
date, store, product_no, product_description, product_division,
product_category, product_subcategory, product_segment, supplier,
qty_sold, sales_amount, cogs, transaction_count,
return_qty, return_amount, net_qty_sold, net_sales_amount,
unit_price, unit_cost, sales_type, is_promo, is_markdown, is_clearance
```

---

### 2. Daily Inventory: `data/processed/daily_inventory.parquet`

| Metric | Value |
|--------|-------|
| Rows | 9,666,655 |
| Date Range | 2025-06-01 to 2026-04-24 |
| Unique Store-Product | 60,968 |
| Duplicate Keys | 0 |
| File Size | ~1.1 GB |

**Reconstruction Logic**:
- Built complete daily grid for each store-product from min to max observed date
- Observed days: forward-filled from inventory period records (observed_flag=true, gap_flag=false)
- Gap days: NULL inventory values + gap_flag=true, observed_flag=false
- 9999-12-31 end dates capped at 2026-04-24
- No overlaps in raw data (validated)
- Negative quantities preserved with `negative_qty_flag`
- Writeoff handling: qty=0 & cost<0 → cost=0 + `writeoff_flag=true`

**Breakdown**:
- Observed days: 9,366,984 (96.9%)
- Gap days: 299,671 (3.1%)
- Negative qty records: 53,166 (0.55%)
- Writeoff records: 381,006 (3.94%)

**Columns**:
```
date, store, product_no, product_description, product_division,
product_category, product_subcategory, product_segment, supplier,
qty_on_hand, stock_status, stock_selling_amount, cost_of_stocks,
stock_unit_selling_price, stock_unit_cost_price,
observed_flag, gap_flag, negative_qty_flag, writeoff_flag
```

---

## Transformation Decisions

| Decision | Rule | Rationale |
|----------|------|-----------|
| Duplicate sales keys | Sum quantities/amounts | 1,823 duplicates represent multiple transactions same day/store/product |
| Returns | Separate columns, stored as positive | Explicit identification for modeling |
| Net sales | Gross - returns | True demand signal |
| Inventory gaps | NULL + gap_flag=true | No invented data; honest about missing periods |
| Far-future end dates | Capped at 2026-04-24 | Analysis cutoff = max sales date |
| Negative qty | Preserved + flagged | Likely return adjustments; matches sales returns |
| Writeoff (qty=0, cost<0) | Cost→0 + flag | Data quality issue; cost without stock |
| Metadata in gaps | Forward-filled | Product/store attributes don't change |

---

## Validation Results

### Raw Data Integrity
- ✅ Raw files exist and non-empty
- ✅ SHA256 hashes match baseline (`.raw_hashes.json` persisted)

### Daily Sales
- ✅ No duplicate date+store+product keys
- ✅ All expected columns present
- ✅ Net qty/amount consistency verified
- ✅ Returns stored as non-negative
- ✅ Date range within bounds

### Daily Inventory
- ✅ No duplicate date+store+product keys
- ✅ All expected columns present
- ✅ No dates beyond 2026-04-24
- ✅ Gap days have NULL inventory values
- ✅ Observed days have populated inventory values
- ✅ Observed/gap flags mutually exclusive
- ✅ Negative qty preserved and flagged correctly
- ✅ Writeoff handling: cost=0 when qty=0 and original cost<0
- ✅ Every row has either observed_flag or gap_flag = true

### Pipeline Idempotency
- ✅ Running pipeline twice produces identical output (SHA256 match)

---

## Data Quality Summary

### Sales
| Metric | Count |
|--------|-------|
| Total daily aggregates | 118,258 |
| With returns | ~7,000 |
| Net qty negative (net returns > sales) | ~500 |
| Zero sales amount | ~10 |
| Negative unit price (data issue) | ~500 |

### Inventory
| Metric | Count | % of Total |
|--------|-------|------------|
| Total daily records | 9,666,655 | 100% |
| Observed | 9,366,984 | 96.9% |
| Gap | 299,671 | 3.1% |
| Negative qty_on_hand | 53,166 | 0.55% |
| Writeoff (qty=0, cost<0) | 381,006 | 3.94% |
| Same-day snapshots (expanded) | Included in observed | - |

---

## Reproducibility

- **Idempotent**: Yes (verified)
- **Deterministic**: Yes (no random operations)
- **Raw data immutable**: Yes (validated via hashes)
- **Configuration**: Hardcoded cutoff date (2026-04-24)
- **Dependencies**: pandas, pyarrow, numpy

---

## Directory Structure After Pipeline

```
retail-decision-intelligence/
├── data/
│   ├── raw/
│   │   ├── retail_sales_ml_apl.csv (unchanged)
│   │   └── retail_inventory_ml_apl.csv (unchanged)
│   └── processed/
│       ├── daily_sales.parquet (118,258 rows)
│       ├── daily_inventory.parquet (9,666,655 rows)
│       └── .raw_hashes.json (baseline hashes)
├── docs/
│   ├── AGENTS.md
│   ├── README.md
│   ├── data-audit.md
│   ├── inventory-data-investigation.md
│   └── data-reconstruction-report.md (this file)
├── notebooks/
│   ├── 01_data_audit.ipynb
│   └── 02_inventory_investigation.ipynb
├── src/
│   └── pipeline/
│       ├── __init__.py
│       ├── run_pipeline.py
│       ├── ingestion/__init__.py
│       ├── sales/transform.py
│       ├── inventory/reconstruct.py
│       └── validation/validate.py
├── scripts/
│   └── run_pipeline.py (standalone entry point)
└── tests/
    ├── test_raw_integrity.py
    ├── test_daily_sales.py
    ├── test_daily_inventory.py
    └── test_idempotent.py
```

---

## Current Next Steps

The reconstruction pipeline is complete. The following downstream capabilities
are now implemented in `src/pipeline/`:

1. **Feature Engineering** - Rolling statistics, lag features, seasonal indicators
2. **Train/Val/Test Split** - Time-based splits for ML
3. **Model Training** - Quantile and hurdle demand forecasting
4. **Model Operations** - Registry, serving, monitoring, and backtesting
5. **Recommendations** - Inventory actions and web-based product alternatives

The remaining product-level item is a dashboard/UI for these API outputs.

---

**Pipeline Status**: ✅ COMPLETE AND VALIDATED
**Ready for Review**: YES
