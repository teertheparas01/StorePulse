"""Test daily sales output."""

from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def load_daily_sales():
    """Load daily sales."""
    path = PROCESSED_DIR / "daily_sales.parquet"
    assert path.exists(), "daily_sales.parquet not found - run pipeline first"
    return pd.read_parquet(path)


def test_daily_sales_exists():
    """Daily sales file should exist."""
    assert (PROCESSED_DIR / "daily_sales.parquet").exists()


def test_daily_sales_no_duplicates():
    """No duplicate date+store+product keys."""
    df = load_daily_sales()
    dupes = df.duplicated(subset=["date", "store", "product_no"]).sum()
    assert dupes == 0, f"Found {dupes} duplicate keys"


def test_daily_sales_columns():
    """Daily sales should have expected columns."""
    df = load_daily_sales()
    expected_cols = {
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
    }
    assert set(df.columns) == expected_cols


def test_daily_sales_net_consistency():
    """Net values should equal gross minus returns."""
    df = load_daily_sales()
    assert (df["net_qty_sold"] == df["qty_sold"] - df["return_qty"]).all()
    assert (df["net_sales_amount"] == df["sales_amount"] - df["return_amount"]).all()


def test_daily_sales_returns_nonnegative():
    """Return quantities/amounts should be non-negative (stored as positive)."""
    df = load_daily_sales()
    assert (df["return_qty"] >= 0).all()
    assert (df["return_amount"] >= 0).all()


def test_daily_sales_date_range():
    """Date range should be reasonable."""
    df = load_daily_sales()
    assert df["date"].min() >= pd.Timestamp("2025-06-01").date()
    assert df["date"].max() <= pd.Timestamp("2026-04-24").date()


def test_daily_sales_row_count():
    """Should have reasonable row count."""
    df = load_daily_sales()
    assert len(df) > 10000  # At least 10k daily aggregates
    assert len(df) < 200000  # Sanity upper bound
