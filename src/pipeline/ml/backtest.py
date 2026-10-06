"""Backtest Simulator - Simulate replenishment decisions using quantile forecasts (7-day horizon)."""

import yaml
import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings("ignore")


CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "ml.yaml"
REGISTRY_DIR = Path(__file__).parent.parent.parent.parent / "models" / "registry"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_latest_models(config):
    """Load latest quantile models from registry."""
    model_name = config["mlflow"]["model_name"]
    quantiles = config["model"].get("quantiles", [0.1, 0.5, 0.9])
    
    models = {}
    for q in quantiles:
        model_dir = REGISTRY_DIR / f"{model_name}_q{int(q*100)}"
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        
        versions = [d for d in model_dir.iterdir() if d.is_dir()]
        if not versions:
            raise FileNotFoundError(f"No model versions found in {model_dir}")
        
        latest = max(versions, key=lambda d: d.stat().st_mtime)
        model_file = latest / "model.txt"
        meta_file = latest / "metadata.json"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        model = lgb.Booster(model_file=str(model_file))
        with open(meta_file) as f:
            metadata = json.load(f)
        
        models[q] = {
            "model": model,
            "metadata": metadata,
            "version": latest.name
        }
        print(f"Loaded q{int(q*100)}: version {latest.name}, best_iter={model.best_iteration}")
    
    return models


def load_test_data(config):
    """Load test data for backtesting."""
    sample_path = Path("data/processed/features/test_sample_1pct.parquet")
    if sample_path.exists():
        df = pd.read_parquet(sample_path)
        print(f"Using sampled test data: {len(df):,} rows")
    else:
        df = pd.read_parquet(config["data"]["features_path"])
        if config["data"].get("filter_target_ge") is not None:
            df = df[df[config["data"]["target_col"]] >= config["data"]["filter_target_ge"]].copy()
        
        test_start = pd.Timestamp(config["split"]["test_start_date"])
        df = df[df["date"] >= test_start].copy()
        
        df = df.sample(frac=0.01, random_state=42)
        print(f"Created sample: {len(df):,} rows")
        df.to_parquet(sample_path, index=False)
    
    # CRITICAL: Sort by store, product, date for correct inventory carryover
    df = df.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    
    exclude = config["data"]["exclude_cols"]
    feature_cols = [c for c in df.columns if c not in exclude]
    target_col = config["data"]["target_col"]
    
    df[feature_cols] = df[feature_cols].fillna(-999)
    
    cat_features = config["model"].get("categorical_features", [])
    for col in cat_features:
        if col in df.columns:
            df[col] = df[col].astype("category")
    
    X_test = df[feature_cols]
    y_test = df[target_col]
    
    return df, X_test, y_test, feature_cols


def prepare_features(df, feature_cols, cat_features):
    """Prepare features for prediction."""
    X = df[feature_cols].copy()
    X = X.fillna(-999)
    for col in cat_features:
        if col in X.columns:
            X[col] = X[col].astype("category")
    return X


def predict_quantiles(models, X_test):
    """Generate quantile predictions for test set."""
    preds = {}
    for q, m in models.items():
        best_iter = m["model"].best_iteration if m["model"].best_iteration > 0 else m["metadata"].get("best_iteration", -1)
        preds[q] = m["model"].predict(X_test, num_iteration=best_iter)
    return preds


def enforce_monotonicity(preds, quantiles):
    """Ensure P10 <= P50 <= P90."""
    for i in range(len(quantiles) - 1):
        q_low = quantiles[i]
        q_high = quantiles[i + 1]
        preds[q_high] = np.maximum(preds[q_high], preds[q_low])
    return preds


def calibrate_predictions(preds, actual, target_coverage=0.95):
    """Scale predictions to achieve target coverage AND match conditional mean."""
    p90 = preds[0.9]
    coverage = (actual <= p90).mean()
    scale_coverage = target_coverage / max(coverage, 0.01)
    
    # Also scale to match mean of positive actuals
    actual_pos = actual[actual > 0]
    p90_pos = p90[p90 > 0]
    if len(p90_pos) > 0 and len(actual_pos) > 0:
        scale_mean = actual_pos.mean() / p90_pos.mean()
    else:
        scale_mean = 1.0
    
    # Use geometric mean of both scales
    scale = (scale_coverage * scale_mean) ** 0.5
    
    cal_p90 = p90 * scale
    
    p50 = preds[0.5]
    coverage50 = (actual <= p50).mean()
    scale50 = 0.5 / max(coverage50, 0.01)
    cal_p50 = p50 * scale50
    
    print(f"  Coverage scale: {scale_coverage:.3f}, Mean scale: {scale_mean:.3f}, Combined: {scale:.3f}")
    
    return {
        0.9: cal_p90,
        0.5: cal_p50,
        0.1: preds[0.1]
    }


def get_demand_probability(p90_preds, threshold=0.5):
    """
    Use P90 forecast as demand probability signal.
    Higher P90 -> higher probability of demand > 0.
    Returns binary flag: 1 if P90 > threshold else 0.
    """
    return (p90_preds > threshold).astype(float)


def simulate_policy_hurdle(test_df, cal_preds, demand_prob, policy_params):
    """
    Simulate hurdle model: only order if predicted probability > threshold.
    demand_prob is binary: 1 if P90 > threshold else 0.
    """
    stockout_cost_per_unit = policy_params.get("stockout_cost_per_unit", 20.0)
    holding_cost_per_unit_per_period = policy_params.get("holding_cost_per_unit_per_period", 0.5)
    ordering_cost = policy_params.get("ordering_cost", 50.0)
    min_order_qty = policy_params.get("min_order_qty", 1)
    
    forecast_p90 = cal_preds[0.9]
    forecast_p50 = cal_preds[0.5]
    forecast_p10 = cal_preds[0.1]
    actual = test_df["target_demand_7d"].values
    
    # FIX: Clip initial inventory to >= 0 (qty_on_hand may have -999 from fillna)
    initial_inv = test_df.groupby(["store", "product_no"])["qty_on_hand"].first().clip(lower=0).fillna(0)
    
    results = []
    
    for idx, row in test_df.iterrows():
        store = row["store"]
        product = row["product_no"]
        date = row["date"]
        actual_demand_7d = row["target_demand_7d"]
        
        row_idx = test_df.index.get_loc(idx)
        if isinstance(row_idx, np.ndarray):
            row_idx = row_idx[0]
        
        p90 = forecast_p90[row_idx] if row_idx < len(forecast_p90) else 0
        p50 = forecast_p50[row_idx] if row_idx < len(forecast_p50) else 0
        p10 = forecast_p10[row_idx] if row_idx < len(forecast_p10) else 0
        prob = demand_prob[row_idx] if row_idx < len(demand_prob) else 0
        
        key = (store, product)
        current_inv = initial_inv.get(key, 0)
        
        # Hurdle: only order if demand probability > 0 (i.e., P90 > threshold)
        if prob > 0:
            target_inv = p90
            order_qty = max(0, target_inv - current_inv)
            
            if order_qty >= min_order_qty:
                current_inv += order_qty
                ordering_cost_incurred = ordering_cost
            else:
                ordering_cost_incurred = 0
        else:
            ordering_cost_incurred = 0
            order_qty = 0
        
        sales = min(current_inv, actual_demand_7d)
        stockout_qty = max(0, actual_demand_7d - current_inv)
        ending_inv = current_inv - sales
        
        stockout_cost = stockout_qty * stockout_cost_per_unit
        holding_cost = max(0, ending_inv) * holding_cost_per_unit_per_period
        total_cost = stockout_cost + holding_cost + ordering_cost_incurred
        
        results.append({
            "date": date,
            "store": store,
            "product_no": product,
            "actual_demand_7d": actual_demand_7d,
            "demand_prob": prob,
            "forecast_p10": p10,
            "forecast_p50": p50,
            "forecast_p90": p90,
            "starting_inv": current_inv,
            "ending_inv": ending_inv,
            "sales": sales,
            "stockout_qty": stockout_qty,
            "stockout_cost": stockout_cost,
            "holding_cost": holding_cost,
            "ordering_cost": ordering_cost_incurred,
            "total_cost": total_cost,
            "ordered": prob > 0,
            "order_qty": order_qty,
        })
        
        initial_inv[key] = ending_inv
    
    return pd.DataFrame(results)


def simulate_baseline_historical(test_df, policy_params):
    """Baseline: historical average per store-product with reorder point."""
    stockout_cost_per_unit = policy_params.get("stockout_cost_per_unit", 20.0)
    holding_cost_per_unit_per_period = policy_params.get("holding_cost_per_unit_per_period", 0.5)
    ordering_cost = policy_params.get("ordering_cost", 50.0)
    min_order_qty = policy_params.get("min_order_qty", 1)
    
    hist_avg = test_df.groupby(["store", "product_no"])["target_demand_7d"].mean().fillna(0)
    
    initial_inv = test_df.groupby(["store", "product_no"])["qty_on_hand"].first().fillna(0)
    
    results = []
    
    for idx, row in test_df.iterrows():
        store = row["store"]
        product = row["product_no"]
        actual_demand_7d = row["target_demand_7d"]
        avg_demand = hist_avg.get((store, product), 0)
        
        key = (store, product)
        current_inv = initial_inv.get(key, 0)
        
        reorder_point = avg_demand * 2
        target_inv = avg_demand * 4
        
        order_qty = 0
        ordering_cost_incurred = 0
        if current_inv <= reorder_point:
            order_qty = max(0, target_inv - current_inv)
            if order_qty >= min_order_qty:
                current_inv += order_qty
                ordering_cost_incurred = ordering_cost
        
        sales = min(current_inv, actual_demand_7d)
        stockout_qty = max(0, actual_demand_7d - current_inv)
        ending_inv = current_inv - sales
        
        stockout_cost = stockout_qty * stockout_cost_per_unit
        holding_cost = max(0, ending_inv) * holding_cost_per_unit_per_period
        total_cost = stockout_cost + holding_cost + ordering_cost_incurred
        
        results.append({
            "date": row["date"],
            "store": store,
            "product_no": product,
            "actual_demand_7d": actual_demand_7d,
            "forecast_p10": avg_demand * 0.5,
            "forecast_p50": avg_demand,
            "forecast_p90": avg_demand * 1.5,
            "demand_prob": avg_demand > 0,
            "starting_inv": current_inv,
            "ending_inv": ending_inv,
            "sales": sales,
            "stockout_qty": stockout_qty,
            "stockout_cost": stockout_cost,
            "holding_cost": holding_cost,
            "ordering_cost": ordering_cost_incurred,
            "total_cost": total_cost,
            "ordered": order_qty > 0,
            "order_qty": order_qty,
        })
        
        initial_inv[key] = ending_inv
    
    return pd.DataFrame(results)


def simulate_oracle(test_df, policy_params):
    """Oracle: perfect forecast - order exactly actual demand."""
    stockout_cost_per_unit = policy_params.get("stockout_cost_per_unit", 20.0)
    holding_cost_per_unit_per_period = policy_params.get("holding_cost_per_unit_per_period", 0.5)
    ordering_cost = policy_params.get("ordering_cost", 50.0)
    
    actual = test_df["target_demand_7d"].values
    
    results = []
    for idx, row in test_df.iterrows():
        actual_demand = row["target_demand_7d"]
        
        order_qty = actual_demand
        ordering_cost_incurred = ordering_cost if order_qty > 0 else 0
        
        sales = actual_demand
        stockout_qty = 0
        ending_inv = 0
        
        stockout_cost = 0
        holding_cost = 0
        total_cost = ordering_cost_incurred
        
        results.append({
            "date": row["date"],
            "store": row["store"],
            "product_no": row["product_no"],
            "actual_demand_7d": actual_demand,
            "forecast_p10": actual_demand,
            "forecast_p50": actual_demand,
            "forecast_p90": actual_demand,
            "demand_prob": 1.0 if actual_demand > 0 else 0.0,
            "starting_inv": actual_demand,
            "ending_inv": 0,
            "sales": sales,
            "stockout_qty": 0,
            "stockout_cost": 0,
            "holding_cost": 0,
            "ordering_cost": ordering_cost_incurred,
            "total_cost": total_cost,
            "ordered": order_qty > 0,
            "order_qty": order_qty,
        })
    
    return pd.DataFrame(results)


def evaluate_policy(results_df):
    """Evaluate replenishment policy performance."""
    total_cost = results_df["total_cost"].sum()
    total_stockout_cost = results_df["stockout_cost"].sum()
    total_holding_cost = results_df["holding_cost"].sum()
    total_ordering_cost = results_df["ordering_cost"].sum()
    
    total_demand = results_df["actual_demand_7d"].sum()
    total_sales = results_df["sales"].sum()
    total_stockout_qty = results_df["stockout_qty"].sum()
    total_orders = results_df["ordered"].sum()
    
    service_level = 1 - (total_stockout_qty / total_demand) if total_demand > 0 else 1
    fill_rate = total_sales / total_demand if total_demand > 0 else 1
    stockout_rate = (results_df["stockout_qty"] > 0).mean()
    order_rate = total_orders / len(results_df)
    
    metrics = {
        "total_cost": float(total_cost),
        "stockout_cost": float(total_stockout_cost),
        "holding_cost": float(total_holding_cost),
        "ordering_cost": float(total_ordering_cost),
        "service_level": float(service_level),
        "fill_rate": float(fill_rate),
        "stockout_rate": float(stockout_rate),
        "order_rate": float(order_rate),
        "avg_cost_per_period": float(total_cost / len(results_df)),
        "total_demand": float(total_demand),
        "total_stockout_qty": float(total_stockout_qty),
        "total_orders": int(total_orders),
        "avg_ending_inv": float(results_df["ending_inv"].mean()),
    }
    
    return metrics


def compare_policies(config, test_df, preds, quantiles):
    """Compare different replenishment policies."""
    
    actual = test_df["target_demand_7d"].values
    cal_preds = calibrate_predictions(preds, actual, target_coverage=0.95)
    p90_raw = preds[0.9]  # Use raw P90 for hurdle thresholding
    
    print(f"Calibration: P90 scale factor = {cal_preds[0.9].mean() / preds[0.9].mean():.3f}")
    print(f"Calibrated P90 coverage: {(actual <= cal_preds[0.9]).mean():.2%}")
    
    policies = {
        "oracle_perfect": {"simulator": "oracle"},
        "hurdle_p90_0.05": {
            "simulator": "hurdle",
            "p90_threshold": 0.05,
            "stockout_cost_per_unit": 20.0,
            "holding_cost_per_unit_per_period": 0.5,
            "ordering_cost": 50.0,
            "min_order_qty": 1,
        },
        "hurdle_p90_0.1": {
            "simulator": "hurdle",
            "p90_threshold": 0.1,
            "stockout_cost_per_unit": 20.0,
            "holding_cost_per_unit_per_period": 0.5,
            "ordering_cost": 50.0,
            "min_order_qty": 1,
        },
        "hurdle_p90_0.2": {
            "simulator": "hurdle",
            "p90_threshold": 0.2,
            "stockout_cost_per_unit": 20.0,
            "holding_cost_per_unit_per_period": 0.5,
            "ordering_cost": 50.0,
            "min_order_qty": 1,
        },
        "hurdle_p90_0.5": {
            "simulator": "hurdle",
            "p90_threshold": 0.5,
            "stockout_cost_per_unit": 20.0,
            "holding_cost_per_unit_per_period": 0.5,
            "ordering_cost": 50.0,
            "min_order_qty": 1,
        },
        "forecast_always": {
            "simulator": "hurdle",
            "p90_threshold": 0.0,  # Always order
            "stockout_cost_per_unit": 20.0,
            "holding_cost_per_unit_per_period": 0.5,
            "ordering_cost": 50.0,
            "min_order_qty": 1,
        },
        "baseline_historical": {
            "simulator": "baseline",
            "stockout_cost_per_unit": 20.0,
            "holding_cost_per_unit_per_period": 0.5,
            "ordering_cost": 50.0,
            "min_order_qty": 1,
        },
    }
    
    comparison = {}
    
    for name, params in policies.items():
        print(f"\nSimulating policy: {name}")
        simulator = params.pop("simulator")
        
        if simulator == "oracle":
            results = simulate_oracle(test_df, params)
        elif simulator == "hurdle":
            p90_threshold = params.pop("p90_threshold", 0.1)
            demand_prob = get_demand_probability(p90_raw, p90_threshold)
            results = simulate_policy_hurdle(test_df, cal_preds, demand_prob, params)
        elif simulator == "baseline":
            results = simulate_baseline_historical(test_df, params)
        else:
            raise ValueError(f"Unknown simulator: {simulator}")
        
        metrics = evaluate_policy(results)
        comparison[name] = metrics
        print(f"  Total cost: {metrics['total_cost']:,.2f}")
        print(f"  Service level: {metrics['service_level']:.2%}")
        print(f"  Fill rate: {metrics['fill_rate']:.2%}")
        print(f"  Stockout rate: {metrics['stockout_rate']:.2%}")
        print(f"  Order rate: {metrics['order_rate']:.2%}")
        print(f"  Avg cost/period: {metrics['avg_cost_per_period']:.2f}")
        print(f"  Cost breakdown: stockout={metrics['stockout_cost']:,.0f}, holding={metrics['holding_cost']:,.0f}, ordering={metrics['ordering_cost']:,.0f}")
    
    return comparison


def main():
    config = load_config()
    
    print("Loading models...")
    models = load_latest_models(config)
    
    print("\nLoading test data...")
    test_df, X_test, y_test, feature_cols = load_test_data(config)
    print(f"Test set: {len(test_df):,} rows, {test_df['date'].nunique()} days")
    print(f"Date range: {test_df['date'].min()} to {test_df['date'].max()}")
    print(f"Unique store-products: {test_df[['store','product_no']].drop_duplicates().shape[0]}")
    
    cat_features = config["model"].get("categorical_features", [])
    X_test = prepare_features(test_df, feature_cols, cat_features)
    
    print("\nGenerating predictions...")
    preds = predict_quantiles(models, X_test)
    
    quantiles = config["model"].get("quantiles", [0.1, 0.5, 0.9])
    preds = enforce_monotonicity(preds, quantiles)
    
    for i in range(len(quantiles) - 1):
        q_low = quantiles[i]
        q_high = quantiles[i + 1]
        violations = (preds[q_low] > preds[q_high]).sum()
        print(f"  q{int(q_low*100)} <= q{int(q_high*100)}: {violations} violations after enforcement")
    
    print("\nRunning backtest comparison...")
    comparison = compare_policies(config, test_df, preds, quantiles)
    
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    comparison_path = output_dir / f"policy_comparison_{timestamp}.json"
    with open(comparison_path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)
    
    best_policy = min(comparison.items(), key=lambda x: x[1]["total_cost"])[0]
    print(f"\nBest policy: {best_policy} (cost: {comparison[best_policy]['total_cost']:,.2f})")
    
    print("\n" + "="*80)
    print("BACKTEST SUMMARY")
    print("="*80)
    for name, m in comparison.items():
        print(f"{name:25s} | Cost: {m['total_cost']:>10,.0f} | Service: {m['service_level']:>6.1%} | Fill: {m['fill_rate']:>6.1%} | Stockout%: {m['stockout_rate']:>5.1%} | Orders: {m['total_orders']:>6} | Cost/period: {m['avg_cost_per_period']:>6.2f}")


if __name__ == "__main__":
    main()