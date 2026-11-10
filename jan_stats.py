import pandas as pd

df = pd.read_parquet("D:/storepulse/data/processed/daily_sales.parquet")
df["date"] = pd.to_datetime(df["date"])
jan = df[(df["date"] >= "2026-01-01") & (df["date"] <= "2026-01-31")]

print("=== JANUARY 2026 DAILY SALES ===")
print(f"Rows: {len(jan):,}")
print(f'Unique stores: {jan["store"].nunique()}')
print(f'Unique products: {jan["product_no"].nunique()}')
print(f'Unique store-products: {jan[["store","product_no"]].drop_duplicates().shape[0]:,}')

print("\nTOTALS:")
print(f'  Total qty_sold: {jan["qty_sold"].sum():,.0f}')
print(f'  Total net_qty_sold: {jan["net_qty_sold"].sum():,.0f}')
print(f'  Total sales_amount: ${jan["sales_amount"].sum():,.2f}')
print(f'  Total net_sales_amount: ${jan["net_sales_amount"].sum():,.2f}')
print(f'  Total COGS: ${jan["cogs"].sum():,.2f}')
print(f'  Total transactions: {jan["transaction_count"].sum():,.0f}')
print(f'  Total returns qty: {jan["return_qty"].sum():,.0f}')
print(f'  Total returns amount: ${jan["return_amount"].sum():,.2f}')

print("\nBY SALES TYPE:")
for st, g in jan.groupby("sales_type"):
    print(
        f'  {st}: rows={len(g):,}, qty={g["net_qty_sold"].sum():,.0f}, revenue=${g["net_sales_amount"].sum():,.2f}'
    )

print("\nTOP 10 PRODUCTS BY NET QTY:")
top = (
    jan.groupby(["product_no", "product_description"])["net_qty_sold"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)
print(top.to_string())

print("\nTOP 10 STORES BY NET QTY:")
top = jan.groupby("store")["net_qty_sold"].sum().sort_values(ascending=False).head(10)
print(top.to_string())

print("\nDAILY BREAKDOWN:")
daily = (
    jan.groupby("date")
    .agg(
        qty=("net_qty_sold", "sum"),
        revenue=("net_sales_amount", "sum"),
        txns=("transaction_count", "sum"),
        active_sp=("product_no", "nunique"),
    )
    .round(2)
)
print(daily.to_string())

print("\nBY DIVISION:")
for div, g in jan.groupby("product_division"):
    print(
        f'  {div}: qty={g["net_qty_sold"].sum():,.0f}, revenue=${g["net_sales_amount"].sum():,.2f}, products={g["product_no"].nunique()}'
    )

print("\nZERO vs NON-ZERO DAYS:")
zero_days = (jan["net_qty_sold"] == 0).sum()
non_zero = (jan["net_qty_sold"] > 0).sum()
print(f"  Zero qty rows: {zero_days:,} ({zero_days/len(jan)*100:.1f}%)")
print(f"  Non-zero qty rows: {non_zero:,} ({non_zero/len(jan)*100:.1f}%)")
