"""Test raw data integrity."""

import pandas as pd
from pathlib import Path
import hashlib


ROOT_DIR = Path(__file__).parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def test_raw_files_exist():
    """Raw files should exist."""
    assert (RAW_DIR / "retail_sales_ml_apl.csv").exists()
    assert (RAW_DIR / "retail_inventory_ml_apl.csv").exists()


def test_raw_files_not_empty():
    """Raw files should not be empty."""
    assert (RAW_DIR / "retail_sales_ml_apl.csv").stat().st_size > 0
    assert (RAW_DIR / "retail_inventory_ml_apl.csv").stat().st_size > 0


def test_raw_hashes_persisted():
    """Hash file should exist after first pipeline run."""
    hash_file = PROCESSED_DIR / ".raw_hashes.json"
    assert hash_file.exists(), "Hash file not found - run pipeline first"


def test_raw_unchanged():
    """Raw files should match stored hashes."""
    hash_file = PROCESSED_DIR / ".raw_hashes.json"
    if not hash_file.exists():
        # First run - skip
        return
    
    import json
    with open(hash_file) as f:
        expected = json.load(f)
    
    for name in ["retail_sales_ml_apl.csv", "retail_inventory_ml_apl.csv"]:
        path = RAW_DIR / name
        with open(path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert actual == expected[name], f"{name} has been modified!"