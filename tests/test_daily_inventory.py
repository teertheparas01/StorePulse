"""Test daily inventory output."""

import pandas as pd
import numpy as np
from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CUTOFF_DATE = pd.Timestamp("2026-04-24").date()


def load_daily_inventory():
    """Load daily inventory."""
    path = PROCESSED_DIR / "daily_inventory.parquet"
    assert path.exists(), "daily_inventory.parquet not found - run pipeline first"
    return pd.read_parquet(path)


def test_daily_inventory_exists():
    """Daily inventory file should exist."""
    assert (PROCESSED_DIR / "daily_inventory.parquet").exists()


def test_daily_inventory_no_duplicates():
    """No duplicate date+store+product keys."""
    df = load_daily_inventory()
    dupes = df.duplicated(subset=["date", "store", "product_no"]).sum()
    assert dupes == 0, f"Found {dupes} duplicate keys"


def test_daily_inventory_columns():
    """Daily inventory should have expected columns."""
    df = load_daily_inventory()
    expected_cols = {
        "date", "store", "product_no", "product_description",
        "product_division", "product_category", "product_subcategory", "product_segment",
        "supplier",
        "qty_on_hand", "stock_status",
        "stock_selling_amount", "cost_of_stocks",
        "stock_unit_selling_price", "stock_unit_cost_price",
        "observed_flag", "gap_flag", "negative_qty_flag", "writeoff_flag"
    }
    assert set(df.columns) == expected_cols


def test_daily_inventory_no_far_future():
    """No dates beyond cutoff."""
    df = load_daily_inventory()
    max_date = df["date"].max()
    if hasattr(max_date, 'date'):
        max_date = max_date.date()
    assert max_date <= CUTOFF_DATE, f"Max date {max_date} exceeds cutoff {CUTOFF_DATE}"


def test_daily_inventory_gap_days_null():
    """Gap days should have NULL inventory values."""
    df = load_daily_inventory()
    gap_rows = df[df["gap_flag"] == True]
    
    if len(gap_rows) > 0:
        assert gap_rows["qty_on_hand"].isna().all(), "Gap days have non-NULL qty"
        assert gap_rows["stock_status"].isna().all(), "Gap days have non-NULL status"
        assert gap_rows["stock_selling_amount"].isna().all(), "Gap days have non-NULL selling amount"
        assert gap_rows["cost_of_stocks"].isna().all(), "Gap days have non-NULL cost"
        assert gap_rows["stock_unit_selling_price"].isna().all(), "Gap days have non-NULL unit price"
        assert gap_rows["stock_unit_cost_price"].isna().all(), "Gap days have non-NULL unit cost"


def test_daily_inventory_observed_days_populated():
    """Observed days should have inventory values."""
    df = load_daily_inventory()
    obs_rows = df[df["observed_flag"] == True]
    
    if len(obs_rows) > 0:
        assert obs_rows["qty_on_hand"].notna().all(), "Observed days have NULL qty"
        assert obs_rows["stock_status"].notna().all(), "Observed days have NULL status"


def test_daily_inventory_flags_mutually_exclusive():
    """Observed and gap flags should be mutually exclusive."""
    df = load_daily_inventory()
    both = ((df["observed_flag"] == True) & (df["gap_flag"] == True)).sum()
    assert both == 0, f"Found {both} rows with both flags"


def test_daily_inventory_negative_qty_preserved():
    """Negative quantities should be preserved and flagged."""
    df = load_daily_inventory()
    neg_count = (df["qty_on_hand"] < 0).sum()
    flagged = df["negative_qty_flag"].sum()
    assert neg_count == flagged, f"Negative qty count mismatch: {neg_count} vs {flagged}"
    
    # Flagged records should actually have negative qty
    if flagged > 0:
        assert (df[df["negative_qty_flag"] == True]["qty_on_hand"] < 0).all()


def test_daily_inventory_writeoff_handling():
    """Zero qty + negative cost should have cost=0 and writeoff_flag."""
    df = load_daily_inventory()
    writeoff_rows = df[df["writeoff_flag"] == True]
    
    if len(writeoff_rows) > 0:
        assert (writeoff_rows["cost_of_stocks"] == 0).all(), "Writeoff records don't have cost=0"
        assert (writeoff_rows["qty_on_hand"] == 0).all(), "Writeoff records don't have qty=0"
        assert (writeoff_rows["negative_qty_flag"] == False).all(), "Writeoff records incorrectly flagged as negative qty"


def test_daily_inventory_gap_flag_consistency():
    """Gap flag should be true only for gap days."""
    df = load_daily_inventory()
    # Every row should be either observed or gap
    assert ((df["observed_flag"] == True) | (df["gap_flag"] == True)).all()


def test_daily_inventory_date_range():
    """Date range should be reasonable."""
    df = load_daily_inventory()
    min_date = df["date"].min()
    max_date = df["date"].max()
    if hasattr(min_date, 'date'):
        min_date = min_date.date()
    if hasattr(max_date, 'date'):
        max_date = max_date.date()
    assert min_date >= pd.Timestamp("2025-06-01").date()
    assert max_date <= CUTOFF_DATE


def test_daily_inventory_row_count():
    """Should have reasonable row count."""
    df = load_daily_inventory()
    assert len(df) > 100000  # At least 100k daily records
    assert len(df) < 15000000  # Sanity upper bound (9.6M observed)