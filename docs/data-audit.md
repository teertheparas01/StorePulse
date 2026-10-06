# Data Audit Report

**Project**: Retail Decision Intelligence System
**Date**: 2026-08-10
**Datasets Audited**:
- `retail_sales_ml_apl.csv` (39.07 MB, 125,751 rows × 17 cols)
- `retail_inventory_ml_apl.csv` (99.99 MB, 284,755 rows × 18 cols)

---

## A. Confirmed Facts About the Datasets

### File Overview
| Metric | Sales | Inventory |
|--------|-------|-----------|
| File Size | 39.07 MB | 99.99 MB |
| Rows | 125,751 | 284,755 |
| Columns | 17 | 18 |
| Date Range | 2025-06-01 to 2026-04-24 | Start: 2025-06-01 to 2026-04-24, End: up to 9999-12-31 |

### Schema

**Sales Columns**: Transaction Date, Sales Type, Is Return, Reason of Return, Supplier, Product No, Product Description, Product Division, Product Category, Product Subcategory, Product Segment, Store, Sales Channel, Qty Sold, Sales Amount, Cogs, Number of Transactions

**Inventory Columns**: Start Date, End Date, Stock Status, Supplier, Product No, Product Description, Product Division, Product Category, Product Subcategory, Product Segment, Store, Store Type, Sales Channel, Qty on hand, Stocks Selling Amount, Cost of Stocks, Stock Unit Selling Price, Stock Unit Cost Price

### Key Dimensions
- **Stores**: 40 (identical in both datasets)
- **Products/SKUs**: 2,326 (identical in both datasets)
- **Suppliers**: 30 (identical in both datasets)
- **Product Hierarchy**: 3 Divisions → 27 Categories → 51 Subcategories → 600 Segments
- **Sales Channels**: 1 (Channel Alpha)
- **Store Types**: 1 (Retail Storefront)

### Product Divisions
| Division | Transactions | Categories |
|----------|-------------|------------|
| Scholar Footwear | 76,907 | 10 |
| Femme Footwear | 29,848 | 6 |
| Junior Apparel | 18,996 | 11 |

### Sales Types
| Type | Count | % |
|------|-------|---|
| Full Price | 93,929 | 74.7% |
| Promo | 23,651 | 18.8% |
| Markdown Tier 1 | 4,384 | 3.5% |
| Markdown Tier 2 | 2,434 | 1.9% |
| Clearance | 1,353 | 1.1% |

### Returns
- **Return transactions**: 7,491 (5.96% of sales)
- All returns have `Qty Sold = -1`, negative `Sales Amount` (avg -$97.93), negative `Cogs`
- **Reason of Return**: 100% missing (0 non-null values)

### Temporal Coverage
- **Sales**: 11 months (Jun 2025 - Apr 2026), all 40 stores active every month
- **Inventory**: 11 months of start dates, records span varying durations (median 9 days, max ~7,977 days / 21.8 years due to 9999-12-31 end dates)
- **Same-day inventory records**: 34,998 (12.3%) - likely snapshot/stockout indicators

---

## B. Data-Quality Issues

### 1. Negative Values in Numerical Fields
| Field | Negatives | % of Rows |
|-------|-----------|-----------|
| Sales: Qty Sold | 7,491 | 5.96% (all returns) |
| Sales: Sales Amount | 7,491 | 5.96% (all returns) |
| Sales: Cogs | 7,491 | 5.96% (all returns) |
| Inventory: Qty on hand | 1,380 | 0.48% |
| Inventory: Stocks Selling Amount | 1,380 | 0.48% |
| Inventory: Cost of Stocks | 8,022 | 2.82% |
| Inventory: Stock Unit Cost Price | 25 | 0.01% |

### 2. Zero Values
| Field | Zeros | % of Rows |
|-------|-------|-----------|
| Sales: Qty Sold | 2 | 0.002% |
| Sales: Sales Amount | 9 | 0.007% |
| Sales: Cogs | 2 | 0.002% |
| Inventory: Qty on hand | 13,869 | 4.87% |
| Inventory: Stocks Selling Amount | 13,869 | 4.87% |
| Inventory: Cost of Stocks | 362 | 0.13% |
| Inventory: Stock Unit Selling Price | 13,869 | 4.87% |
| Inventory: Stock Unit Cost Price | 13,869 | 4.87% |

### 3. COGS > Sales Amount (Loss-Making Transactions)
- **14,194 transactions (11.29%)** have COGS > Sales Amount
- Includes all returns (negative revenue) plus some regular transactions

### 4. Future Dates in Sales
- **38,621 sales records (30.7%)** have Transaction Date > 2025-12-31 (into 2026)
- This appears to be legitimate forward-looking data (Jan-Apr 2026), not an error

### 5. Inventory End Date = 9999-12-31
- Many inventory records have far-future end dates, indicating "current/ongoing" stock
- Median duration: 9 days; Mean: ~636 days (skewed by 9999 end dates)
- 12.3% are same-day start/end (snapshots)

### 6. Missing Reason of Return
- 100% missing - no return reason codes available

### 7. Sales Key Duplicates
- 1,823 duplicate (Transaction Date, Store, Product No) combinations in sales
- No full-row duplicates in either dataset

### 8. Negative Inventory Qty/Cost
- 1,380 records with negative Qty on hand (likely returns/adjustments in inventory)
- 8,022 records with negative Cost of Stocks
- 25 records with negative Stock Unit Cost Price

---

## C. Features We Can Use

### Sales Features
- **Transaction Date** (daily granularity)
- **Sales Type** (Full Price, Promo, Markdown Tier 1/2, Clearance) - strong promo/markdown signal
- **Is Return** flag (binary)
- **Supplier** (30 vendors)
- **Product hierarchy** (Division → Category → Subcategory → Segment → SKU)
- **Store** (40 locations)
- **Qty Sold** (units, includes negative for returns)
- **Sales Amount** (revenue, includes negative for returns)
- **Cogs** (cost of goods sold)
- **Number of Transactions** (basket size proxy, mostly 1)
- **Derived**: Unit Price, Unit Cost, Margin, Margin %

### Inventory Features
- **Start Date, End Date** (period-based, not daily snapshots)
- **Stock Status** (Full Price, Markdown Tier 1/2, Clearance, Promo) - aligns with sales types
- **Supplier** (same 30 vendors)
- **Product hierarchy** (same as sales)
- **Store** (same 40 stores)
- **Qty on hand** (current stock level, includes negative)
- **Stocks Selling Amount** (total value at selling price)
- **Cost of Stocks** (total value at cost)
- **Stock Unit Selling Price, Stock Unit Cost Price** (per-unit prices)

### Temporal Features (Derivable)
- Day of week, week of year, month, quarter
- Seasonal indicators
- Days since product launch / days until markdown
- Inventory age (days since Start Date)

### Cross-Dataset Features
- Perfect product/store overlap (2,326 products × 40 stores in both)
- Supplier alignment
- Stock Status ↔ Sales Type alignment for markdown/promo modeling

---

## D. ML Problems Genuinely Supported

### 1. Demand Forecasting ✅
- **Support**: Strong. 11 months of daily sales per product-store (40 stores × 2,326 SKUs)
- **Features**: Price, promo type, seasonality, product hierarchy, store, supplier
- **Target**: Daily Qty Sold (or weekly/monthly aggregated)
- **Caveat**: Returns mixed in; need to separate or model net demand

### 2. Stockout Prediction ✅
- **Support**: Moderate. Inventory has Qty on hand with 4.9% zero-stock records
- **Features**: Current stock, sales velocity, stock status, replenishment lead time (inferred from inventory duration)
- **Target**: Binary stockout within N days / time-to-stockout
- **Caveat**: Inventory is period-based snapshots, not daily. Same-day records (12.3%) may indicate stockout checks.

### 3. Dead/Slow-Stock Detection ✅
- **Support**: Strong. Inventory shows aging (Start Date), stock status progression (Full Price → Markdown → Clearance), sales velocity
- **Features**: Inventory age, weeks of supply, sell-through rate, markdown depth, zero-sales periods
- **Target**: Binary dead-stock flag / aging bucket / recommended action (markdown, transfer, donate)

### 4. Product Replacement Intelligence ⚠️ Partial
- **Support**: Partial. Product hierarchy (Segment → Subcategory → Category) enables substitution modeling
- **Features**: Co-purchase patterns (limited - no basket data), category/subcategory affinity, price proximity
- **Caveat**: No explicit substitution/cannibalization data. No basket/transaction-level co-occurrence.

### 5. Branch/Category Health Analysis ✅
- **Support**: Strong. 40 stores × 27 categories × 11 months
- **Features**: Revenue, units, margin, sell-through, inventory turnover, stockout rate, promo reliance
- **Target**: Store/category performance scoring, anomaly detection, peer benchmarking

### 6. Markdown/Promo Optimization ✅
- **Support**: Strong. 5 sales types with clear pricing tiers, 25.3% of transactions are non-full-price
- **Features**: Sales Type, unit price discount depth, inventory stock status, seasonality
- **Target**: Lift estimation, optimal markdown timing/depth, sell-through projection

---

## E. ML Problems NOT Supported

| Problem | Reason |
|---------|--------|
| **Customer-level modeling (CLV, segmentation, personalization)** | No customer ID, no loyalty data, no demographics |
| **Basket analysis / cross-sell / bundling** | Number of Transactions ≈ 1 always; no transaction/basket ID linking multiple products |
| **Price elasticity at SKU level** | Price changes confounded with Sales Type (promo/markdown); no controlled price experiments |
| **Supplier performance / lead time prediction** | No purchase order / receipt dates; inventory Start Date ≠ receipt date |
| **Lost sales estimation during stockouts** | No daily inventory snapshots; no traffic/footfall data |
| **New product launch forecasting** | No product launch dates; all products appear with history |
| **Omnichannel / e-commerce analysis** | Single sales channel (Channel Alpha) |
| **Store format / size effects** | Single store type (Retail Storefront) |
| **Return reason analysis** | 100% missing Reason of Return |
| **Causal inference for promotions** | No control group; promo assignment not randomized |

---

## F. Important Limitations

1. **Inventory is period-based, not daily snapshots** - Cannot reconstruct true daily stock levels without interpolation/assumptions. Gaps between inventory records (2-73 days in sample).

2. **Returns embedded in sales** - 5.96% of transactions are returns (negative qty/amount). Must separate for demand forecasting.

3. **Future sales dates (30.7%)** - Data includes Jan-Apr 2026. If this is "actuals", fine. If forecast/plan data, must exclude from training.

4. **No customer or basket data** - Pure product-store-time series. No personalization, no cross-sell.

5. **Single channel, single store type** - No channel/store format variation for modeling.

6. **Reason of Return 100% missing** - Cannot analyze return drivers.

7. **Negative inventory quantities** - 1,380 records (0.48%) have negative Qty on hand - data quality issue or adjustment coding.

8. **COGS > Sales in 11.3% of transactions** - Beyond returns, suggests data quality issues or markdowns below cost.

9. **Inventory end dates = 9999-12-31** - Requires handling for "current" records; duration calculations skewed.

10. **Sales key duplicates (1,823)** - Multiple rows per (date, store, SKU). Need aggregation strategy.

---

## G. Recommended Next Step

### Immediate (Before Any Modeling)

1. **Create cleaned analysis-ready datasets** (in `data/processed/`, not modifying raw):
   - Separate returns from sales (Is Return flag)
   - Aggregate sales to daily product-store level (handle 1,823 duplicates)
   - Filter future dates if they represent plans not actuals
   - Create daily inventory panel via forward-fill from period snapshots (with gap flags)
   - Handle negative inventory qty/cost (investigate: adjustments? data errors?)

2. **Define ML targets explicitly**:
   - Demand: Net daily units sold (excl returns) per product-store
   - Stockout: Binary - will Qty on hand reach 0 within 7/14/30 days?
   - Dead-stock: Inventory age > 90 days + sell-through < 20% + in markdown/clearance

3. **Build feature store** with:
   - Product hierarchy embeddings
   - Store profiles (size, revenue tier)
   - Temporal features (seasonality, holidays)
   - Price/promo history
   - Inventory position (weeks of supply, stock status)

4. **Establish validation strategy**: Time-series split (train on Jun-Dec 2025, validate Jan-Mar 2026, test Apr 2026)

### Notebook Created
- `notebooks/01_data_audit.ipynb` - Full exploratory audit (executed)

---

**Audit Complete**. Ready for review before pipeline development.