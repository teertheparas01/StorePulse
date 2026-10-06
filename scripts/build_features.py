"""Build and validate demand forecasting feature dataset."""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipeline.features.demand_features import (
    build_feature_dataset, save_feature_dataset, validate_features, 
    print_feature_metadata, FEATURE_METADATA
)
from pipeline.targets.demand_targets import add_targets, validate_targets, TARGET_DEFINITIONS


PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
FEATURE_DIR = PROCESSED_DIR / "features"
FEATURE_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2026-04-24")


def main():
    print("=" * 80)
    print("DEMAND FORECASTING - FEATURE ENGINEERING & TARGET DEFINITION")
    print("=" * 80)
    
    # Print feature metadata for review
    print_feature_metadata()
    
    # Print target definitions
    print("\n" + "=" * 80)
    print("TARGET DEFINITIONS")
    print("=" * 80)
    for name, meta in TARGET_DEFINITIONS.items():
        print(f"\n{name}:")
        for k, v in meta.items():
            print(f"  {k}: {v}")
    
    # Build features
    print("\n" + "=" * 80)
    print("BUILDING FEATURE DATASET")
    print("=" * 80)
    
    df = build_feature_dataset()
    print(f"Base features shape: {df.shape}")
    
    # Add targets
    print("\nAdding targets...")
    df = add_targets(df, horizons=[7, 14, 28])
    print(f"With targets shape: {df.shape}")
    
    # Validate
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    feat_val = validate_features(df)
    print("\nFeature validation:")
    for k, v in feat_val.items():
        print(f"  {k}: {v}")
    
    target_cols = [c for c in df.columns if c.startswith("target_")]
    target_val = validate_targets(df, target_cols)
    print("\nTarget validation:")
    for col, stats in target_val["stats"].items():
        print(f"  {col}: null={stats['null_pct']*100:.1f}%, mean={stats.get('mean')}, "
              f"pos_rate={stats.get('positive_rate', 'N/A')}")
    if target_val["issues"]:
        print("  Issues:")
        for issue in target_val["issues"]:
            print(f"    - {issue}")
    
    # Combined issues
    all_issues = feat_val["issues"] + target_val["issues"]
    if all_issues:
        print("\n⚠️  VALUATION ISSUES:")
        for issue in all_issues:
            print(f"  - {issue}")
    else:
        print("\n✅ ALL VALIDATIONS PASSED")
    
    # Save
    print("\nSaving feature dataset...")
    path = save_feature_dataset(df, "demand_forecasting_features")
    print(f"Saved to: {path}")
    
    # Save metadata
    metadata = {
        "feature_metadata": FEATURE_METADATA,
        "target_definitions": TARGET_DEFINITIONS,
        "validation": {
            "features": feat_val,
            "targets": target_val
        },
        "dataset_info": {
            "rows": len(df),
            "columns": len(df.columns),
            "date_range": [str(df["date"].min()), str(df["date"].max())],
            "unique_store_product": int(df[["store", "product_no"]].drop_duplicates().shape[0]),
            "target_columns": target_cols
        }
    }
    
    meta_path = FEATURE_DIR / "feature_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"Metadata saved to: {meta_path}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("FEATURE DATASET SUMMARY")
    print("=" * 80)
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Unique store-products: {df[['store', 'product_no']].drop_duplicates().shape[0]:,}")
    print(f"Target columns: {len(target_cols)}")
    print(f"Gap days: {feat_val.get('gap_days', 0):,}")
    print(f"Observed inventory days: {feat_val.get('observed_inv_days', 0):,}")
    
    # Feature categories
    feature_cats = {
        "Sales lags/rolling": [c for c in df.columns if "sales_lag" in c or "sales_rolling" in c or "sales_zero" in c or "sales_cv" in c],
        "Promo/markdown": [c for c in df.columns if "promo" in c.lower() or "markdown" in c.lower() or "clearance" in c.lower()],
        "Price": [c for c in df.columns if "price" in c.lower()],
        "Inventory": [c for c in df.columns if c.startswith("inv_")],
        "Temporal": [c for c in df.columns if c in ["day_of_week", "day_of_month", "week_of_year", "month", "quarter", "is_weekend", "is_month_start", "is_month_end"]],
        "Static": [c for c in df.columns if c in ["product_division", "product_category", "product_subcategory", "product_segment", "supplier", "store"]],
        "Store agg": [c for c in df.columns if "store_" in c],
        "Targets": target_cols,
    }
    
    print("\nFeature categories:")
    for cat, cols in feature_cats.items():
        print(f"  {cat}: {len(cols)} features")
    
    return df


if __name__ == "__main__":
    main()