"""Sales transformation - aggregate to daily store-product level."""

from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


SALES_COLUMNS = [
    "date",
    "store",
    "product_no",
    "product_description",
    "product_division",
    "product_category",
    "product_subcategory",
    "product_segment",
    "supplier",
    "qty_sold",
    "sales_amount",
    "cogs",
    "transaction_count",
    "return_qty",
    "return_amount",
    "net_qty_sold",
    "net_sales_amount",
    "unit_price",
    "unit_cost",
    "sales_type",
    "is_promo",
    "is_markdown",
    "is_clearance",
]


def transform_sales(raw_sales: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate sales to daily store-product level.

    Handles 1,823 duplicate (date, store, product) keys by summing.
    Keeps returns explicitly identifiable.
    """
    df = raw_sales.copy()

    # Parse dates
    df["date"] = pd.to_datetime(df["Transaction Date"]).dt.date

    # Rename columns
    df = df.rename(
        columns={
            "Store": "store",
            "Product No": "product_no",
            "Product Description": "product_description",
            "Product Division": "product_division",
            "Product Category": "product_category",
            "Product Subcategory": "product_subcategory",
            "Product Segment": "product_segment",
            "Supplier": "supplier",
            "Qty Sold": "qty_sold",
            "Sales Amount": "sales_amount",
            "Cogs": "cogs",
            "Number of Transactions": "transaction_count",
            "Sales Type": "sales_type",
            "Is Return": "is_return",
        }
    )

    # Flag promo/markdown/clearance
    df["is_promo"] = df["sales_type"] == "Promo"
    df["is_markdown"] = df["sales_type"].isin(["Markdown Tier 1", "Markdown Tier 2"])
    df["is_clearance"] = df["sales_type"] == "Clearance"

    # Separate returns
    returns = df[df["is_return"] == 1].copy()
    sales = df[df["is_return"] == 0].copy()

    # Aggregate non-returns
    sales_agg = sales.groupby(
        [
            "date",
            "store",
            "product_no",
            "product_description",
            "product_division",
            "product_category",
            "product_subcategory",
            "product_segment",
            "supplier",
        ],
        as_index=False,
    ).agg(
        qty_sold=("qty_sold", "sum"),
        sales_amount=("sales_amount", "sum"),
        cogs=("cogs", "sum"),
        transaction_count=("transaction_count", "sum"),
        # Sales type: take the most frequent (mode)
        sales_type=("sales_type", lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "Mixed"),
        is_promo=("is_promo", "any"),
        is_markdown=("is_markdown", "any"),
        is_clearance=("is_clearance", "any"),
    )

    # Aggregate returns
    if len(returns) > 0:
        returns_agg = returns.groupby(["date", "store", "product_no"], as_index=False).agg(
            return_qty=("qty_sold", "sum"),  # negative values
            return_amount=("sales_amount", "sum"),  # negative values
        )
        returns_agg["return_qty"] = returns_agg["return_qty"].abs()  # store as positive for clarity
        returns_agg["return_amount"] = returns_agg["return_amount"].abs()
    else:
        returns_agg = pd.DataFrame(
            columns=["date", "store", "product_no", "return_qty", "return_amount"]
        )

    # Merge
    result = sales_agg.merge(returns_agg, on=["date", "store", "product_no"], how="left")
    result["return_qty"] = result["return_qty"].fillna(0)
    result["return_amount"] = result["return_amount"].fillna(0)

    # Net values
    result["net_qty_sold"] = result["qty_sold"] - result["return_qty"]
    result["net_sales_amount"] = result["sales_amount"] - result["return_amount"]

    # Unit price/cost (handle division by zero)
    result["unit_price"] = np.where(
        result["qty_sold"] != 0, result["sales_amount"] / result["qty_sold"], np.nan
    )
    result["unit_cost"] = np.where(
        result["qty_sold"] != 0, result["cogs"] / result["qty_sold"], np.nan
    )

    # Ensure column order
    result = result[SALES_COLUMNS]

    return result


def save_daily_sales(df: pd.DataFrame) -> Path:
    """Save daily sales to parquet."""
    path = PROCESSED_DIR / "daily_sales.parquet"
    df.to_parquet(path, index=False)
    return path


def load_daily_sales() -> pd.DataFrame:
    """Load processed daily sales."""
    path = PROCESSED_DIR / "daily_sales.parquet"
    return pd.read_parquet(path)


def validate_daily_sales(df: pd.DataFrame) -> dict:
    """Validate daily sales output."""
    issues = []

    # Check for duplicates
    dup_count = df.duplicated(subset=["date", "store", "product_no"]).sum()
    if dup_count > 0:
        issues.append(f"Duplicate date+store+product keys: {dup_count}")

    # Check date range
    min_date = df["date"].min()
    max_date = df["date"].max()

    # Check nulls
    null_counts = df.isnull().sum().to_dict()

    # Check net values consistency
    net_qty_check = (df["net_qty_sold"] == df["qty_sold"] - df["return_qty"]).all()
    net_amt_check = (df["net_sales_amount"] == df["sales_amount"] - df["return_amount"]).all()

    return {
        "row_count": len(df),
        "date_range": (str(min_date), str(max_date)),
        "unique_store_product": df[["store", "product_no"]].drop_duplicates().shape[0],
        "duplicates": int(dup_count),
        "null_counts": null_counts,
        "net_qty_consistent": bool(net_qty_check),
        "net_amt_consistent": bool(net_amt_check),
        "issues": issues,
    }
