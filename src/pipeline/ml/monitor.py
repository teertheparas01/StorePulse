"""Model Monitoring: Drift Detection & Performance Tracking."""

import yaml
import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from datetime import datetime, timedelta
import json
import warnings
from typing import Dict, List
warnings.filterwarnings("ignore")

from scipy.stats import entropy, ks_2samp
import mlflow
import sys


CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "ml.yaml"
REGISTRY_DIR = Path(__file__).parent.parent.parent.parent / "models" / "registry"
MONITORING_DIR = Path(__file__).parent.parent.parent.parent / "monitoring"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class ModelMonitor:
    def __init__(self, config):
        self.config = config
        self.model_name = config["mlflow"]["model_name"]
        self.quantiles = config["model"].get("quantiles", [0.1, 0.5, 0.9])
        self.psi_threshold = config["monitoring"].get("psi_threshold", 0.2)
        self.performance_threshold = config["monitoring"].get("performance_threshold_rmse", 1.0)
        
        MONITORING_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load training reference distributions
        self._load_reference_distributions()
    
    def _load_reference_distributions(self):
        """Load feature distributions from training data."""
        train_path = Path("data/processed/features/demand_forecasting_features.parquet")
        if train_path.exists():
            df = pd.read_parquet(train_path)
            
            # Time-based split to get training data
            test_start = pd.Timestamp(self.config["split"]["test_start_date"])
            val_start = pd.Timestamp(self.config["split"]["val_start_date"])
            train = df[df["date"] < val_start].copy()
            
            exclude = self.config["data"]["exclude_cols"]
            feature_cols = [c for c in df.columns if c not in exclude]
            
            # Store reference distributions
            self.reference_features = {}
            for col in feature_cols:
                if train[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                    # Numeric: store histogram bins
                    hist, bins = np.histogram(train[col].dropna(), bins=20, density=True)
                    self.reference_features[col] = {
                        "type": "numeric",
                        "hist": hist,
                        "bins": bins,
                        "mean": float(train[col].mean()),
                        "std": float(train[col].std()),
                        "min": float(train[col].min()),
                        "max": float(train[col].max()),
                    }
                else:
                    # Categorical: store value counts
                    vc = train[col].value_counts(normalize=True)
                    self.reference_features[col] = {
                        "type": "categorical",
                        "value_counts": vc.to_dict(),
                    }
            
            # Store target distribution
            target_col = self.config["data"]["target_col"]
            self.reference_target = {
                "mean": float(train[target_col].mean()),
                "std": float(train[target_col].std()),
                "zero_rate": float((train[target_col] == 0).mean()),
            }
            
            print(f"Loaded reference distributions for {len(self.reference_features)} features")
    
    def compute_psi(self, reference, current, bins=20):
        """Compute Population Stability Index (PSI)."""
        if reference["type"] == "numeric":
            ref_hist = reference["hist"]
            ref_bins = reference["bins"]
            
            # Use same bins for current
            curr_hist, _ = np.histogram(current.dropna(), bins=ref_bins, density=True)
            
            # Avoid zeros
            ref_hist = np.maximum(ref_hist, 1e-6)
            curr_hist = np.maximum(curr_hist, 1e-6)
            
            psi = np.sum((curr_hist - ref_hist) * np.log(curr_hist / ref_hist))
            return float(psi)
        
        else:
            # Categorical PSI
            ref_vc = reference["value_counts"]
            curr_vc = current.value_counts(normalize=True).to_dict()
            
            all_cats = set(ref_vc.keys()) | set(curr_vc.keys())
            psi = 0.0
            for cat in all_cats:
                ref_p = ref_vc.get(cat, 1e-6)
                curr_p = curr_vc.get(cat, 1e-6)
                psi += (curr_p - ref_p) * np.log(curr_p / ref_p)
            return float(psi)
    
    def check_feature_drift(self, current_df: pd.DataFrame) -> Dict:
        """Check feature drift using PSI."""
        exclude = self.config["data"]["exclude_cols"]
        feature_cols = [c for c in current_df.columns if c not in exclude]
        
        drift_results = {}
        alerts = []
        
        for col in feature_cols:
            if col in self.reference_features and col in current_df.columns:
                psi = self.compute_psi(self.reference_features[col], current_df[col])
                drift_results[col] = {
                    "psi": psi,
                    "drift_detected": psi > self.psi_threshold,
                }
                if psi > self.psi_threshold:
                    alerts.append(f"Feature drift: {col} (PSI={psi:.4f})")
        
        # Overall drift score
        max_psi = max([r["psi"] for r in drift_results.values()]) if drift_results else 0
        drift_results["_summary"] = {
            "max_psi": max_psi,
            "features_above_threshold": sum(1 for r in drift_results.values() if isinstance(r, dict) and r.get("drift_detected", False)),
            "total_features": len(drift_results),
            "alerts": alerts,
        }
        
        return drift_results
    
    def check_prediction_drift(self, predictions: pd.DataFrame) -> Dict:
        """Check prediction distribution drift."""
        drift_results = {}
        
        for q in self.quantiles:
            col = f"hurdle_{int(q*100)}"
            if col in predictions.columns:
                pred = predictions[col].dropna()
                
                # KS test against reference target
                ref_mean = self.reference_target["mean"]
                ref_std = self.reference_target["std"]
                
                # Generate reference sample from training
                np.random.seed(42)
                ref_sample = np.random.normal(ref_mean, ref_std, 10000)
                ref_sample = np.maximum(ref_sample, 0)
                
                ks_stat, p_value = ks_2samp(pred, ref_sample)
                
                drift_results[f"hurdle_{int(q*100)}"] = {
                    "mean": float(pred.mean()),
                    "std": float(pred.std()),
                    "ks_statistic": float(ks_stat),
                    "p_value": float(p_value),
                    "drift_detected": p_value < 0.05,
                }
        
        return drift_results
    
    def check_performance(self, actual: pd.Series, predictions: pd.DataFrame) -> Dict:
        """Check model performance on new data."""
        metrics = {}
        
        for q in self.quantiles:
            col = f"hurdle_{int(q*100)}"
            if col in predictions.columns:
                pred = predictions[col].values
                y_true = actual.values
                
                rmse = np.sqrt(np.mean((y_true - pred) ** 2))
                mae = np.mean(np.abs(y_true - pred))
                
                # Asymmetric cost
                stockout_cost = self.config["loss"].get("stockout_cost_per_unit", 20.0)
                holding_cost = self.config["loss"].get("holding_cost_per_unit_per_period", 0.5)
                err = y_true - pred
                asymmetric = np.mean(np.where(err > 0, stockout_cost * err, holding_cost * -err))
                
                metrics[f"hurdle_{int(q*100)}"] = {
                    "rmse": float(rmse),
                    "mae": float(mae),
                    "asymmetric_cost": float(asymmetric),
                    "performance_ok": rmse < self.performance_threshold,
                }
        
        return metrics
    
    def run_monitoring(self, features_df: pd.DataFrame, predictions_df: pd.DataFrame, actual_df: pd.Series = None) -> Dict:
        """Run full monitoring pipeline."""
        timestamp = datetime.utcnow().isoformat()
        
        print(f"Running monitoring at {timestamp}")
        
        # Feature drift
        feature_drift = self.check_feature_drift(features_df)
        
        # Prediction drift
        pred_drift = self.check_prediction_drift(predictions_df)
        
        # Performance (if actuals available)
        performance = {}
        if actual_df is not None:
            performance = self.check_performance(actual_df, predictions_df)
        
# Compile report
        report = {
            "timestamp": timestamp,
            "feature_drift": feature_drift,
            "prediction_drift": pred_drift,
            "performance": performance,
            "summary": {
                "feature_drift_detected": feature_drift["_summary"]["features_above_threshold"] > 0,
                "max_feature_psi": feature_drift["_summary"]["max_psi"],
                "prediction_drift_detected": any(r.get("drift_detected", False) for r in pred_drift.values()),
                "performance_degraded": any(not r.get("performance_ok", True) for r in performance.values()) if performance else False,
            }
        }
        
        # Save report
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = MONITORING_DIR / f"monitoring_report_{timestamp_str}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"MONITORING REPORT - {timestamp}")
        print(f"{'='*60}")
        print(f"Feature drift: {report['summary']['max_feature_psi']:.4f} max PSI, {report['summary']['feature_drift_detected']}")
        print(f"Prediction drift: {report['summary']['prediction_drift_detected']}")
        print(f"Performance degraded: {report['summary']['performance_degraded']}")
        
        if feature_drift["_summary"]["alerts"]:
            print("ALERTS:")
            for alert in feature_drift["_summary"]["alerts"]:
                print(f"  - {alert}")
        
        return report, report_path


def main():
    config = load_config()
    
    # Set up MLflow
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["experiment"]["name"] + "_monitoring")
    
    # Load recent predictions for monitoring (simulate with test data)
    test_df = pd.read_parquet("data/processed/features/test_sample_1pct.parquet")
    test_df = test_df.sort_values(["store", "product_no", "date"]).reset_index(drop=True)
    
    # Use first 1000 rows as "today's batch"
    batch_df = test_df.head(1000).copy()
    
    # Load model server for predictions
    sys.path.insert(0, str(Path(__file__).parent))
    from serve import HurdleModelServer
    
    server_config = load_config()
    server = HurdleModelServer(server_config)
    
    # Generate predictions
    print("Generating predictions for monitoring...")
    predictions = server.predict(batch_df)
    
    # Get actuals
    actual = batch_df[config["data"]["target_col"]]
    
    # Run monitoring
    monitor = ModelMonitor(config)
    report, report_path = monitor.run_monitoring(batch_df, predictions, actual)
    
    # Log to MLflow
    with mlflow.start_run(run_name=f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        mlflow.log_metrics({
            "max_feature_psi": report["summary"]["max_feature_psi"],
            "feature_drift_alerts": report["summary"]["feature_drift_detected"],
            "prediction_drift_alerts": report["summary"]["prediction_drift_detected"],
        })
        
        if report["performance"]:
            for k, v in report["performance"].items():
                mlflow.log_metric(f"perf_{k}_rmse", v["rmse"])
                mlflow.log_metric(f"perf_{k}_mae", v["mae"])
        
        mlflow.log_artifact(str(report_path))
    
    print("Monitoring complete!")


if __name__ == "__main__":
    import sys
    main()