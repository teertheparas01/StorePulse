"""Data ingestion module - reads raw data without modification."""

import pandas as pd
from pathlib import Path
from typing import Tuple


RAW_DIR = Path(__file__).parent.parent.parent.parent / "data" / "raw"


def load_raw_sales() -> pd.DataFrame:
    """Load raw sales data with original dtypes preserved."""
    path = RAW_DIR / "retail_sales_ml_apl.csv"
    df = pd.read_csv(path, low_memory=False)
    return df


def load_raw_inventory() -> pd.DataFrame:
    """Load raw inventory data with original dtypes preserved."""
    path = RAW_DIR / "retail_inventory_ml_apl.csv"
    df = pd.read_csv(path, low_memory=False)
    return df


def get_raw_file_hashes() -> dict:
    """Get file hashes for validation that raw data hasn't changed."""
    import hashlib
    hashes = {}
    for name in ["retail_sales_ml_apl.csv", "retail_inventory_ml_apl.csv"]:
        path = RAW_DIR / name
        with open(path, "rb") as f:
            hashes[name] = hashlib.sha256(f.read()).hexdigest()
    return hashes


EXPECTED_SALES_HASH = None
EXPECTED_INV_HASH = None

def validate_raw_unchanged() -> bool:
    """Verify raw files haven't been modified."""
    hashes = get_raw_file_hashes()
    global EXPECTED_SALES_HASH, EXPECTED_INV_HASH
    
    if EXPECTED_SALES_HASH is None:
        EXPECTED_SALES_HASH = hashes["retail_sales_ml_apl.csv"]
        EXPECTED_INV_HASH = hashes["retail_inventory_ml_apl.csv"]
        return True
    
    return (hashes["retail_sales_ml_apl.csv"] == EXPECTED_SALES_HASH and 
            hashes["retail_inventory_ml_apl.csv"] == EXPECTED_INV_HASH)


# Export
__all__ = ["load_raw_sales", "load_raw_inventory", "validate_raw_unchanged", "get_raw_file_hashes"]