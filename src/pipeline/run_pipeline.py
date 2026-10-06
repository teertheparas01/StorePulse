"""Main pipeline orchestrator."""

import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.ingestion import load_raw_sales, load_raw_inventory, validate_raw_unchanged
from pipeline.sales.transform import transform_sales, save_daily_sales, validate_daily_sales
from pipeline.inventory.reconstruct import reconstruct_inventory, save_daily_inventory, validate_daily_inventory
from pipeline.validation.validate import validate_pipeline, print_validation_report


def run_pipeline() -> dict:
    """Run the full data reconstruction pipeline."""
    print("=" * 60)
    print("RETAIL DECISION INTELLIGENCE - DATA RECONSTRUCTION PIPELINE")
    print("=" * 60)
    
    # Step 1: Validate raw data unchanged
    print("\n[1/6] Validating raw data integrity...")
    if not validate_raw_unchanged():
        raise RuntimeError("Raw data has been modified! Pipeline aborted.")
    print("    Raw data verified unchanged.")
    
    # Step 2: Load raw data
    print("\n[2/6] Loading raw data...")
    raw_sales = load_raw_sales()
    raw_inv = load_raw_inventory()
    print(f"    Sales: {len(raw_sales):,} rows")
    print(f"    Inventory: {len(raw_inv):,} rows")
    
    # Step 3: Transform sales
    print("\n[3/6] Transforming sales to daily level...")
    daily_sales = transform_sales(raw_sales)
    print(f"    Daily sales: {len(daily_sales):,} rows")
    
    # Step 4: Reconstruct inventory
    print("\n[4/6] Reconstructing daily inventory...")
    daily_inv = reconstruct_inventory(raw_inv)
    print(f"    Daily inventory: {len(daily_inv):,} rows")
    
    # Step 5: Save processed data
    print("\n[5/6] Saving processed datasets...")
    sales_path = save_daily_sales(daily_sales)
    inv_path = save_daily_inventory(daily_inv)
    print(f"    Saved: {sales_path}")
    print(f"    Saved: {inv_path}")
    
    # Step 6: Validate
    print("\n[6/6] Running validation checks...")
    validation_results = validate_pipeline()
    print_validation_report(validation_results)
    
    # Check all passed
    all_passed = all(
        validation_results[k].get("passed", False) 
        for k in ["raw_unchanged", "sales_no_duplicates", "inv_no_duplicates", 
                  "no_raw_overlaps", "gap_days_null", "no_far_future",
                  "neg_qty_preserved", "writeoff_correct", "idempotent"]
    )
    
    if not all_passed:
        raise RuntimeError("Validation failed! See report above.")
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    
    return {
        "daily_sales_rows": len(daily_sales),
        "daily_inventory_rows": len(daily_inv),
        "validation": validation_results
    }


if __name__ == "__main__":
    run_pipeline()