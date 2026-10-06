"""Test pipeline idempotency."""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
SCRIPTS_DIR = ROOT_DIR / "scripts"


def test_pipeline_idempotent():
    """Running pipeline twice should produce identical output."""
    # Run pipeline first time
    result1 = subprocess.run(
        [sys.executable, "scripts/run_pipeline.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result1.returncode == 0, f"First pipeline run failed: {result1.stderr}"

    # Capture output file hashes
    sales_hash1 = _file_hash(PROCESSED_DIR / "daily_sales.parquet")
    inv_hash1 = _file_hash(PROCESSED_DIR / "daily_inventory.parquet")

    # Run pipeline second time
    result2 = subprocess.run(
        [sys.executable, "scripts/run_pipeline.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result2.returncode == 0, f"Second pipeline run failed: {result2.stderr}"

    # Capture output file hashes
    sales_hash2 = _file_hash(PROCESSED_DIR / "daily_sales.parquet")
    inv_hash2 = _file_hash(PROCESSED_DIR / "daily_inventory.parquet")

    # Hashes should match
    assert sales_hash1 == sales_hash2, "daily_sales.parquet changed on second run"
    assert inv_hash1 == inv_hash2, "daily_inventory.parquet changed on second run"


def _file_hash(path: Path) -> str:
    import hashlib

    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
