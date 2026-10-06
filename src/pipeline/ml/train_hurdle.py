"""Hurdle Model Training: Binary Classifier + Conditional Quantile Regressor."""

import yaml
import pandas as pd
import numpy as np
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_curve
import json
import warnings
warnings.filterwarnings("ignore")


CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "ml.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_data(config):
    """Load and prepare training data."""
    df = pd.read_parquet(config["data"]["features_path"])
    
    # Filter sentinel targets
    if config["data"].get("filter_target_ge") is not None:
        df = df[df[config["data"]["target_col"]] >= config["data"]["filter_target_ge"]].copy()
    
    # Time-based split
    test_start = pd.Timestamp(config["split"]["test_start_date"])
    val_start = pd.Timestamp(config["split"]["val_start_date"])
    
    train = df[df["date"] < val_start].copy()
    val = df[(df["date"] >= val_start) & (df["date"] < test_start)].copy()
    test = df[df["date"] >= test_start].copy()
    
    print(f"Train: {len(train):,} rows ({train['date'].min()} to {train['date'].max()})")
    print(f"Val:   {len(val):,} rows ({val['date'].min()} to {val['date'].max()})")
    print(f"Test:  {len(test):,} rows ({test['date'].min()} to {test['date'].max()})")
    
    # Sample for faster iteration
    sample_frac = config["training"].get("sample_frac", 1.0)
    if sample_frac < 1.0:
        train = train.sample(frac=sample_frac, random_state=config["training"]["sample_random_state"])
        val = val.sample(frac=sample_frac, random_state=config["training"]["sample_random_state"])
        test = test.sample(frac=sample_frac, random_state=config["training"]["sample_random_state"])
        print(f"Sampled: train={len(train):,}, val={len(val):,}, test={len(test):,}")
    
    # Create binary target for hurdle
    target_col = config["data"]["target_col"]
    for split in [train, val, test]:
        split["demand_binary"] = (split[target_col] > 0).astype(int)
    
    # Prepare features
    exclude = config["data"]["exclude_cols"]
    feature_cols = [c for c in df.columns if c not in exclude]
    
    # Fill nulls FIRST (before categorical conversion)
    for split in [train, val, test]:
        split[feature_cols] = split[feature_cols].fillna(-999)
    
    # Handle categoricals
    cat_features = config["model"].get("categorical_features", [])
    for col in cat_features:
        if col in train.columns:
            all_cats = pd.concat([train[col], val[col], test[col]]).unique()
            train[col] = pd.Categorical(train[col], categories=all_cats)
            val[col] = pd.Categorical(val[col], categories=all_cats)
            test[col] = pd.Categorical(test[col], categories=all_cats)
    
    X_train, y_train_bin = train[feature_cols], train["demand_binary"]
    X_val, y_val_bin = val[feature_cols], val["demand_binary"]
    X_test, y_test_bin = test[feature_cols], test["demand_binary"]
    
    # Conditional data (only positive demand)
    train_pos = train[train[target_col] > 0].copy()
    val_pos = val[val[target_col] > 0].copy()
    test_pos = test[test[target_col] > 0].copy()
    
    print(f"Positive demand: train={len(train_pos):,}, val={len(val_pos):,}, test={len(test_pos):,}")
    
    X_train_pos = train_pos[feature_cols]
    y_train_pos = train_pos[target_col]
    X_val_pos = val_pos[feature_cols]
    y_val_pos = val_pos[target_col]
    X_test_pos = test_pos[feature_cols]
    y_test_pos = test_pos[target_col]
    
    return {
        "binary": {
            "train": (X_train, y_train_bin),
            "val": (X_val, y_val_bin),
            "test": (X_test, y_test_bin),
        },
        "conditional": {
            "train": (X_train_pos, y_train_pos),
            "val": (X_val_pos, y_val_pos),
            "test": (X_test_pos, y_test_pos),
        },
        "feature_cols": feature_cols,
        "cat_features": [c for c in cat_features if c in train.columns],
        "full_test": test,
    }


def asymmetric_loss(y_true, y_pred, stockout_cost=20.0, holding_cost=0.5):
    """Asymmetric loss: under-prediction (stockout) costs more than over-prediction."""
    err = y_true - y_pred
    return np.mean(np.where(err > 0, stockout_cost * err, holding_cost * -err))


def binary_asymmetric_loss(y_true, y_pred_proba, fn_cost=20.0, fp_cost=1.0, threshold=0.5):
    """Asymmetric loss for binary classification."""
    y_pred = (y_pred_proba >= threshold).astype(int)
    fn = ((y_true == 1) & (y_pred == 0)).sum()  # False negatives
    fp = ((y_true == 0) & (y_pred == 1)).sum()  # False positives
    tn = ((y_true == 0) & (y_pred == 0)).sum()
    tp = ((y_true == 1) & (y_pred == 1)).sum()
    return fn * fn_cost + fp * fp_cost, fn, fp, tp, tn


def quantile_loss(y_true, y_pred, alpha):
    """Pinball loss for quantile regression."""
    err = y_true - y_pred
    return np.mean(np.where(err >= 0, alpha * err, (alpha - 1) * err))


def train_binary_classifier(config, X_train, y_train, X_val, y_val, cat_features):
    """Train binary classifier for P(demand > 0)."""
    pos_weight = (len(y_train) - y_train.sum()) / y_train.sum()
    params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 63,
        "max_depth": 6,
        "learning_rate": 0.05,
        "n_estimators": 1000,
        "min_child_samples": 100,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "random_state": 42,
        "verbosity": -1,
        "n_jobs": -1,
        "scale_pos_weight": pos_weight,
    }
    params["categorical_feature"] = [c for c in cat_features if c in X_train.columns]
    
    train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=params.pop("categorical_feature", []))
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, categorical_feature=params.pop("categorical_feature", []))
    
    model = lgb.train(
        params,
        train_data,
        valid_sets=[train_data, val_data],
        valid_names=["train", "val"],
        num_boost_round=params["n_estimators"],
        callbacks=[
            lgb.early_stopping(50),
            lgb.log_evaluation(period=50)
        ]
    )
    
    return model


def train_conditional_quantile(config, X_train, y_train, X_val, y_val, cat_features, alpha):
    """Train conditional quantile regressor for quantity | demand > 0."""
    params = {
        "objective": "quantile",
        "alpha": alpha,
        "metric": "quantile",
        "boosting_type": "gbdt",
        "num_leaves": 63,
        "max_depth": 6,
        "learning_rate": 0.05,
        "n_estimators": 1000,
        "min_child_samples": 50,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "random_state": 42,
        "verbosity": -1,
        "n_jobs": -1,
    }
    params["categorical_feature"] = [c for c in cat_features if c in X_train.columns]
    
    train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=params.pop("categorical_feature", []))
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, categorical_feature=params.pop("categorical_feature", []))
    
    model = lgb.train(
        params,
        train_data,
        valid_sets=[train_data, val_data],
        valid_names=["train", "val"],
        num_boost_round=params["n_estimators"],
        callbacks=[
            lgb.early_stopping(50),
            lgb.log_evaluation(period=50)
        ]
    )
    
    return model


def evaluate_binary(model, X_test, y_test):
    """Evaluate binary classifier."""
    y_pred = model.predict(X_test, num_iteration=model.best_iteration)
    auc = roc_auc_score(y_test, y_pred)
    ap = average_precision_score(y_test, y_pred)
    
    # Find optimal threshold for F1
    precision, recall, thresholds = precision_recall_curve(y_test, y_pred)
    f1 = 2 * precision * recall / (precision + recall + 1e-10)
    best_idx = np.argmax(f1)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
    
    y_pred_bin = (y_pred >= best_threshold).astype(int)
    precision_at_best = precision[best_idx]
    recall_at_best = recall[best_idx]
    f1_at_best = f1[best_idx]
    
    return {
        "auc": float(auc),
        "avg_precision": float(ap),
        "best_threshold": float(best_threshold),
        "precision_at_best": float(precision_at_best),
        "recall_at_best": float(recall_at_best),
        "f1_at_best": float(f1_at_best),
    }


def evaluate_conditional(model, X_test, y_test, alpha):
    """Evaluate conditional quantile model."""
    y_pred = model.predict(X_test, num_iteration=model.best_iteration)
    
    metrics = {}
    metrics["mae"] = float(np.mean(np.abs(y_test - y_pred)))
    metrics["rmse"] = float(np.sqrt(np.mean((y_test - y_pred) ** 2)))
    metrics["pinball"] = float(quantile_loss(y_test, y_pred, alpha))
    metrics["asymmetric"] = float(asymmetric_loss(y_test, y_pred))
    
    # Coverage
    coverage = (y_test <= y_pred).mean()
    metrics[f"coverage_q{int(alpha*100)}"] = float(coverage)
    
    return metrics


def log_feature_importance(model, feature_cols, prefix=""):
    """Log feature importance as artifact."""
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importance(importance_type="gain")
    }).sort_values("importance", ascending=False)
    
    importance_path = f"{prefix}feature_importance.csv"
    importance.to_csv(importance_path, index=False)
    mlflow.log_artifact(importance_path)
    Path(importance_path).unlink()
    
    return importance


def main():
    config = load_config()
    
    # Setup MLflow
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    experiment_name = f"{config['experiment']['name']}_hurdle"
    mlflow.set_experiment(experiment_name)
    
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"MLflow Run ID: {run_id}")
        
        # Log config
        mlflow.log_dict(config, "config.yaml")
        
        # Load data
        data = load_data(config)
        feature_cols = data["feature_cols"]
        cat_features = data["cat_features"]
        
        # ============ STAGE 1: Binary Classifier ============
        print(f"\n{'='*60}")
        print("STAGE 1: Binary Classifier (P(demand > 0))")
        print(f"{'='*60}")
        
        X_train_bin, y_train_bin = data["binary"]["train"]
        X_val_bin, y_val_bin = data["binary"]["val"]
        X_test_bin, y_test_bin = data["binary"]["test"]
        
        print(f"Train positive rate: {y_train_bin.mean():.4f}")
        print(f"Val positive rate: {y_val_bin.mean():.4f}")
        print(f"Test positive rate: {y_test_bin.mean():.4f}")
        
        mlflow.log_param("binary_train_pos_rate", float(y_train_bin.mean()))
        
        binary_model = train_binary_classifier(config, X_train_bin, y_train_bin, X_val_bin, y_val_bin, cat_features)
        
        # Evaluate binary
        binary_metrics = evaluate_binary(binary_model, X_test_bin, y_test_bin)
        print(f"Binary AUC: {binary_metrics['auc']:.4f}")
        print(f"Binary AP: {binary_metrics['avg_precision']:.4f}")
        print(f"Best threshold: {binary_metrics['best_threshold']:.4f}")
        print(f"Precision@best: {binary_metrics['precision_at_best']:.4f}")
        print(f"Recall@best: {binary_metrics['recall_at_best']:.4f}")
        print(f"F1@best: {binary_metrics['f1_at_best']:.4f}")
        
        mlflow.log_metrics({f"binary_{k}": v for k, v in binary_metrics.items()})
        
        binary_importance = log_feature_importance(binary_model, feature_cols, "binary_")
        print("Top 10 binary features:")
        print(binary_importance.head(10))
        
        # ============ STAGE 2: Conditional Quantile Models ============
        print(f"\n{'='*60}")
        print("STAGE 2: Conditional Quantile Models (quantity | demand > 0)")
        print(f"{'='*60}")
        
        quantiles = config["model"].get("quantiles", [0.1, 0.5, 0.9])
        conditional_models = {}
        conditional_metrics = {}
        
        X_train_pos, y_train_pos = data["conditional"]["train"]
        X_val_pos, y_val_pos = data["conditional"]["val"]
        X_test_pos, y_test_pos = data["conditional"]["test"]
        
        for alpha in quantiles:
            print(f"\n--- Quantile q{int(alpha*100)} (alpha={alpha}) ---")
            
            model = train_conditional_quantile(
                config, X_train_pos, y_train_pos, X_val_pos, y_val_pos, cat_features, alpha
            )
            conditional_models[alpha] = model
            
            # Evaluate
            metrics = evaluate_conditional(model, X_test_pos, y_test_pos, alpha)
            print(f"  MAE: {metrics['mae']:.4f}, RMSE: {metrics['rmse']:.4f}")
            print(f"  Pinball: {metrics['pinball']:.4f}, Asymmetric: {metrics['asymmetric']:.4f}")
            print(f"  Coverage: {metrics[f'coverage_q{int(alpha*100)}']:.4f}")
            
            mlflow.log_metrics({f"cond_q{int(alpha*100)}_{k}": v for k, v in metrics.items()})
            conditional_metrics[alpha] = metrics
            
            importance = log_feature_importance(model, feature_cols, f"cond_q{int(alpha*100)}_")
            print(f"  Top 5 features: {importance.head(5)['feature'].tolist()}")
        
        # ============ STAGE 3: End-to-End Hurdle Evaluation ============
        print(f"\n{'='*60}")
        print("STAGE 3: End-to-End Hurdle Evaluation on Test Set")
        print(f"{'='*60}")
        
        full_test = data["full_test"]
        test_features = full_test[feature_cols].fillna(-999)
        for col in cat_features:
            if col in test_features.columns:
                test_features[col] = test_features[col].astype("category")
        
        # Binary predictions
        test_bin_pred = binary_model.predict(test_features, num_iteration=binary_model.best_iteration)
        test_bin_pred_bin = (test_bin_pred >= binary_metrics["best_threshold"]).astype(int)
        
        # Conditional predictions
        test_cond_preds = {}
        for alpha in quantiles:
            test_cond_preds[alpha] = conditional_models[alpha].predict(
                test_features, num_iteration=conditional_models[alpha].best_iteration
            )
        
        # Hurdle predictions: binary * conditional
        test_hurdle_preds = {}
        for alpha in quantiles:
            test_hurdle_preds[alpha] = test_bin_pred_bin * test_cond_preds[alpha]
        
        # Evaluate hurdle model
        y_true = full_test[config["data"]["target_col"]].values
        
        for alpha in quantiles:
            pred = test_hurdle_preds[alpha]
            mae = np.mean(np.abs(y_true - pred))
            rmse = np.sqrt(np.mean((y_true - pred) ** 2))
            pinball = quantile_loss(y_true, pred, alpha)
            asymmetric = asymmetric_loss(y_true, pred)
            coverage = (y_true <= pred).mean()
            
            print(f"Hurdle q{int(alpha*100)}: MAE={mae:.4f}, RMSE={rmse:.4f}, Pinball={pinball:.4f}, Asym={asymmetric:.4f}, Cov={coverage:.4f}")
            mlflow.log_metrics({
                f"hurdle_q{int(alpha*100)}_mae": float(mae),
                f"hurdle_q{int(alpha*100)}_rmse": float(rmse),
                f"hurdle_q{int(alpha*100)}_pinball": float(pinball),
                f"hurdle_q{int(alpha*100)}_asymmetric": float(asymmetric),
                f"hurdle_q{int(alpha*100)}_coverage": float(coverage),
            })
        
        # Binary metrics on full test
        test_binary_auc = roc_auc_score(full_test["demand_binary"], test_bin_pred)
        test_binary_ap = average_precision_score(full_test["demand_binary"], test_bin_pred)
        print(f"Full test Binary AUC: {test_binary_auc:.4f}, AP: {test_binary_ap:.4f}")
        mlflow.log_metric("full_binary_auc", float(test_binary_auc))
        mlflow.log_metric("full_binary_ap", float(test_binary_ap))
        
        # ============ LOG MODELS ============
        if config["mlflow"]["log_models"]:
            input_example = test_features.iloc[:5]
            
            # Log binary model
            mlflow.lightgbm.log_model(
                binary_model,
                artifact_path="binary_model",
                input_example=input_example,
                registered_model_name=f"{config['mlflow']['model_name']}_binary"
            )
            
            # Log conditional models
            for alpha in quantiles:
                mlflow.lightgbm.log_model(
                    conditional_models[alpha],
                    artifact_path=f"cond_model_q{int(alpha*100)}",
                    input_example=input_example,
                    registered_model_name=f"{config['mlflow']['model_name']}_cond_q{int(alpha*100)}"
                )
        
        # ============ SAVE METADATA ============
        model_meta = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "config": config,
            "feature_cols": feature_cols,
            "cat_features": cat_features,
            "binary": {
                "best_iteration": binary_model.best_iteration,
                "metrics": binary_metrics,
            },
            "conditional": {
                str(a): {
                    "best_iteration": m.best_iteration,
                    "metrics": conditional_metrics[a],
                }
                for a, m in conditional_models.items()
            },
            "data_stats": {
                "n_stores": int(X_train_bin["store"].nunique()) if "store" in X_train_bin.columns else None,
                "n_products": int(X_train_bin["product_no"].nunique()) if "product_no" in X_train_bin.columns else None,
            }
        }
        
        meta_path = "model_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(model_meta, f, indent=2, default=str)
        mlflow.log_artifact(meta_path)
        Path(meta_path).unlink()
        
        # Save locally
        model_dir = Path("models") / "registry" / f"{config['mlflow']['model_name']}_hurdle" / run_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        binary_model.save_model(str(model_dir / "binary_model.txt"))
        for alpha in quantiles:
            conditional_models[alpha].save_model(str(model_dir / f"cond_model_q{int(alpha*100)}.txt"))
        
        with open(model_dir / "metadata.json", "w") as f:
            json.dump(model_meta, f, indent=2, default=str)
        
        print(f"\nHurdle model saved to {model_dir}")
        print("Done!")


if __name__ == "__main__":
    main()