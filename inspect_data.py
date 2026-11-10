import pandas as pd

# Daily Sales
df = pd.read_parquet("D:/storepulse/data/processed/daily_sales.parquet")
print("=== DAILY SALES ===")
print(f"Rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Unique stores: {df["store"].nunique()}')
print(f'Unique products: {df["product_no"].nunique()}')
print(f'Unique store-products: {df[["store","product_no"]].drop_duplicates().shape[0]:,}')
print()
print("Sample:")
print(df.head(3).to_string())
print()

# Daily Inventory
df = pd.read_parquet("D:/storepulse/data/processed/daily_inventory.parquet")
print("=== DAILY INVENTORY ===")
print(f"Rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Unique stores: {df["store"].nunique()}')
print(f'Unique products: {df["product_no"].nunique()}')
print(f'Unique store-products: {df[["store","product_no"]].drop_duplicates().shape[0]:,}')
print(f'Observed days: {df["observed_flag"].sum():,} ({df["observed_flag"].mean()*100:.1f}%)')
print(f'Gap days: {df["gap_flag"].sum():,} ({df["gap_flag"].mean()*100:.1f}%)')
print(f'Negative qty: {(df["qty_on_hand"] < 0).sum():,}')
print(f'Writeoff: {df["writeoff_flag"].sum():,}')
print()
print("Sample:")
print(df.head(3).to_string())
print()

# Features
df = pd.read_parquet("D:/storepulse/data/processed/features/demand_forecasting_features.parquet")
print("=== FEATURES ===")
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Unique store-products: {df[["store","product_no"]].drop_duplicates().shape[0]:,}')
target_cols = [c for c in df.columns if c.startswith("target_")]
print(f"Target columns ({len(target_cols)}): {target_cols}")
print()
print("Feature categories:")
cats = {
    "Sales lags/rolling": [
        c
        for c in df.columns
        if "sales_lag" in c or "sales_rolling" in c or "sales_zero" in c or "sales_cv" in c
    ],
    "Promo/markdown": [
        c
        for c in df.columns
        if "promo" in c.lower() or "markdown" in c.lower() or "clearance" in c.lower()
    ],
    "Price": [c for c in df.columns if "price" in c.lower()],
    "Inventory": [c for c in df.columns if c.startswith("inv_")],
    "Temporal": [
        c
        for c in df.columns
        if c
        in [
            "day_of_week",
            "day_of_month",
            "week_of_year",
            "month",
            "quarter",
            "is_weekend",
            "is_month_start",
            "is_month_end",
        ]
    ],
    "Static": [
        c
        for c in df.columns
        if c
        in [
            "product_division",
            "product_category",
            "product_subcategory",
            "product_segment",
            "supplier",
            "store",
        ]
    ],
    "Store agg": [c for c in df.columns if "store_" in c],
}
for cat, cols in cats.items():
    print(f"  {cat}: {len(cols)}")
print()

# Raw data quick stats
raw_sales = pd.read_csv("D:/storepulse/data/raw/retail_sales_ml_apl.csv", low_memory=False)
raw_inv = pd.read_csv("D:/storepulse/data/raw/retail_inventory_ml_apl.csv", low_memory=False)
print("=== RAW SALES ===")
print(f"Rows: {len(raw_sales):,}")
print(f'Date range: {raw_sales["Transaction Date"].min()} to {raw_sales["Transaction Date"].max()}')
print(f'Sales Types: {raw_sales["Sales Type"].value_counts().to_dict()}')
print(
    f'Returns: {(raw_sales["Is Return"] == 1).sum():,} ({(raw_sales["Is Return"] == 1).mean()*100:.1f}%)'
)
print()

print("=== RAW INVENTORY ===")
print(f"Rows: {len(raw_inv):,}")
print(f'Start date range: {raw_inv["Start Date"].min()} to {raw_inv["Start Date"].max()}')
print(f'End date range: {raw_inv["End Date"].min()} to {raw_inv["End Date"].max()}')
print(f'Stock Status: {raw_inv["Stock Status"].value_counts().to_dict()}')
print(
    f'Far future ends (9999): {(pd.to_datetime(raw_inv["End Date"], errors="coerce") > "2030-01-01").sum():,}'
)
print(f'Negative qty: {(raw_inv["Qty on hand"] < 0).sum():,}')
print(f'Zero qty: {(raw_inv["Qty on hand"] == 0).sum():,}')
print(f'Negative cost: {(raw_inv["Cost of Stocks"] < 0).sum():,}')
