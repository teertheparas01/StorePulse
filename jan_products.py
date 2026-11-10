import pandas as pd

df = pd.read_parquet("D:/storepulse/data/processed/daily_sales.parquet")
df["date"] = pd.to_datetime(df["date"])
jan = df[(df["date"] >= "2026-01-01") & (df["date"] <= "2026-01-31")]

# All products sold in January with details
prod = (
    jan.groupby(
        [
            "product_no",
            "product_description",
            "product_division",
            "product_category",
            "product_subcategory",
            "product_segment",
        ]
    )
    .agg(
        total_qty=("net_qty_sold", "sum"),
        total_revenue=("net_sales_amount", "sum"),
        avg_price=("unit_price", "mean"),
        selling_days=("net_qty_sold", lambda x: (x > 0).sum()),
        stores_selling=("store", "nunique"),
        total_txns=("transaction_count", "sum"),
        promo_days=("is_promo", "sum"),
        markdown_days=("is_markdown", "sum"),
        clearance_days=("is_clearance", "sum"),
    )
    .sort_values("total_qty", ascending=False)
    .reset_index()
)

print(f"=== ALL {len(prod)} PRODUCTS SOLD IN JANUARY 2026 ===\n")
pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 200)
print(prod.to_string(index=False))
