"""ML Training Pipeline with MLflow Tracking - Quantile Regression."""

import json
import warnings
from datetime import datetime
from pathlib import Path

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

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
        train = train.sample(
            frac=sample_frac, random_state=config["training"]["sample_random_state"]
        )
        val = val.sample(frac=sample_frac, random_state=config["training"]["sample_random_state"])
        test = test.sample(frac=sample_frac, random_state=config["training"]["sample_random_state"])
        print(f"Sampled: train={len(train):,}, val={len(val):,}, test={len(test):,}")

    # Prepare features
    exclude = config["data"]["exclude_cols"]
    feature_cols = [c for c in df.columns if c not in exclude]
    target_col = config["data"]["target_col"]

    # Fill nulls FIRST (before categorical conversion)
    for split in [train, val, test]:
        split[feature_cols] = split[feature_cols].fillna(-999)

    # Handle categoricals
    cat_features = config["model"].get("categorical_features", [])
    for col in cat_features:
        if col in train.columns:
            # Combine all categories across splits
            all_cats = pd.concat([train[col], val[col], test[col]]).unique()
            train[col] = pd.Categorical(train[col], categories=all_cats)
            val[col] = pd.Categorical(val[col], categories=all_cats)
            test[col] = pd.Categorical(test[col], categories=all_cats)

    X_train, y_train = train[feature_cols], train[target_col]
    X_val, y_val = val[feature_cols], val[target_col]
    X_test, y_test = test[feature_cols], test[target_col]

    return (X_train, y_train), (X_val, y_val), (X_test, y_test), feature_cols, cat_features


def quantile_loss(y_true, y_pred, alpha):
    """Pinball loss for quantile regression."""
    err = y_true - y_pred
    return np.mean(np.where(err >= 0, alpha * err, (alpha - 1) * err))


def poisson_deviance(y_true, y_pred):
    """Poisson deviance for count data."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    y_pred = np.maximum(y_pred, 1e-10)
    return 2 * np.mean(y_pred - y_true + y_true * np.log(y_true / y_pred + 1e-10))


def evaluate_model(y_true, y_pred, prefix=""):
    """Compute evaluation metrics."""
    metrics = {}
    metrics[f"{prefix}rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    metrics[f"{prefix}mae"] = float(mean_absolute_error(y_true, y_pred))
    metrics[f"{prefix}r2"] = float(r2_score(y_true, y_pred))
    metrics[f"{prefix}poisson_deviance"] = float(poisson_deviance(y_true, y_pred))

    # MAPE (handle zeros)
    mask = y_true != 0
    if mask.any():
        metrics[f"{prefix}mape"] = float(
            np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        )
    else:
        metrics[f"{prefix}mape"] = 0.0

    return metrics


def train_quantile_model(config, X_train, y_train, X_val, y_val, cat_features, alpha):
    """Train LightGBM quantile model with early stopping."""
    params = config["model"]["params"].copy()
    params["objective"] = "quantile"
    params["alpha"] = alpha
    params["metric"] = "quantile"
    params["categorical_feature"] = [c for c in cat_features if c in X_train.columns]

    train_data = lgb.Dataset(
        X_train, label=y_train, categorical_feature=params.pop("categorical_feature", [])
    )
    val_data = lgb.Dataset(
        X_val,
        label=y_val,
        reference=train_data,
        categorical_feature=params.pop("categorical_feature", []),
    )

    model = lgb.train(
        params,
        train_data,
        valid_sets=[train_data, val_data],
        valid_names=["train", "val"],
        num_boost_round=params.pop("n_estimators", 2000),
        callbacks=[
            lgb.early_stopping(config["model"]["early_stopping_rounds"]),
            lgb.log_evaluation(period=100),
        ],
    )

    return model


def log_feature_importance(model, feature_cols, quantile):
    """Log feature importance as artifact."""
    importance = pd.DataFrame(
        {"feature": feature_cols, "importance": model.feature_importance(importance_type="gain")}
    ).sort_values("importance", ascending=False)

    importance_path = f"feature_importance_q{int(quantile*100)}.csv"
    importance.to_csv(importance_path, index=False)
    mlflow.log_artifact(importance_path)
    Path(importance_path).unlink()

    return importance


def main():
    config = load_config()

    # Setup MLflow
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["experiment"]["name"])

    quantiles = config["model"].get("quantiles", [0.5])

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"MLflow Run ID: {run_id}")

        # Log config
        mlflow.log_params(
            {f"config.{k}": v for k, v in config.items() if isinstance(v, (str, int, float, bool))}
        )
        mlflow.log_dict(config, "config.yaml")

        # Load data
        (X_train, y_train), (X_val, y_val), (X_test, y_test), feature_cols, cat_features = (
            load_data(config)
        )

        # Log data stats
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_param("n_val", len(X_val))
        mlflow.log_param("n_test", len(X_test))
        mlflow.log_param("target_mean", float(y_train.mean()))
        mlflow.log_param("target_std", float(y_train.std()))
        mlflow.log_param("zero_frac_train", float((y_train == 0).mean()))
        mlflow.log_param("quantiles", str(quantiles))

        all_models = {}
        all_metrics = {}

        # Train one model per quantile
        for alpha in quantiles:
            print(f"\n{'='*60}")
            print(f"Training quantile q{int(alpha*100)} (alpha={alpha})")
            print(f"{'='*60}")

            model = train_quantile_model(
                config, X_train, y_train, X_val, y_val, cat_features, alpha
            )
            all_models[alpha] = model

            # Evaluate
            val_pred = model.predict(X_val, num_iteration=model.best_iteration)
            test_pred = model.predict(X_test, num_iteration=model.best_iteration)

            val_metrics = evaluate_model(y_val, val_pred, f"val_q{int(alpha*100)}_")
            test_metrics = evaluate_model(y_test, test_pred, f"test_q{int(alpha*100)}_")

            # Add quantile-specific metrics
            val_metrics[f"val_q{int(alpha*100)}_pinball"] = float(
                quantile_loss(y_val, val_pred, alpha)
            )
            test_metrics[f"test_q{int(alpha*100)}_pinball"] = float(
                quantile_loss(y_test, test_pred, alpha)
            )

            print(
                f"Validation: RMSE={val_metrics[f'val_q{int(alpha*100)}_rmse']:.4f}, Pinball={val_metrics[f'val_q{int(alpha*100)}_pinball']:.4f}"
            )
            print(
                f"Test:       RMSE={test_metrics[f'test_q{int(alpha*100)}_rmse']:.4f}, Pinball={test_metrics[f'test_q{int(alpha*100)}_pinball']:.4f}"
            )

            # Log metrics
            mlflow.log_metrics(val_metrics)
            mlflow.log_metrics(test_metrics)
            all_metrics[alpha] = {"val": val_metrics, "test": test_metrics}

            # Log feature importance
            importance = log_feature_importance(model, feature_cols, alpha)
            print(f"Top 10 features for q{int(alpha*100)}:")
            print(importance.head(10))

        # Cross-quantile validation: check monotonicity
        print(f"\n{'='*60}")
        print("Cross-quantile validation (monotonicity check)")
        print(f"{'='*60}")

        test_preds = {}
        for alpha in quantiles:
            test_preds[alpha] = all_models[alpha].predict(
                X_test, num_iteration=all_models[alpha].best_iteration
            )

        # Check P10 <= P50 <= P90
        for i in range(len(quantiles) - 1):
            q_low = quantiles[i]
            q_high = quantiles[i + 1]
            violations = (test_preds[q_low] > test_preds[q_high]).sum()
            total = len(test_preds[q_low])
            pct = violations / total * 100
            print(
                f"  q{int(q_low*100)} <= q{int(q_high*100)}: {violations}/{total} violations ({pct:.2f}%)"
            )
            mlflow.log_metric(
                f"monotonicity_violations_q{int(q_low*100)}_q{int(q_high*100)}", violations
            )
            mlflow.log_metric(f"monotonicity_pct_q{int(q_low*100)}_q{int(q_high*100)}", pct)

        # Log all models
        if config["mlflow"]["log_models"]:
            for alpha in quantiles:
                input_example = X_test.iloc[:5]
                mlflow.lightgbm.log_model(
                    all_models[alpha],
                    artifact_path=f"model_q{int(alpha*100)}",
                    input_example=input_example,
                    registered_model_name=f"{config['mlflow']['model_name']}_q{int(alpha*100)}",
                )

        # Log model metadata
        model_meta = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "config": config,
            "feature_cols": feature_cols,
            "cat_features": cat_features,
            "quantiles": quantiles,
            "best_iterations": {str(a): m.best_iteration for a, m in all_models.items()},
            "metrics": all_metrics,
            "data_stats": {
                "n_stores": int(X_train["store"].nunique()) if "store" in X_train.columns else None,
                "n_products": (
                    int(X_train["product_no"].nunique())
                    if "product_no" in X_train.columns
                    else None
                ),
            },
        }

        meta_path = "model_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(model_meta, f, indent=2, default=str)
        mlflow.log_artifact(meta_path)
        Path(meta_path).unlink()

        # Save models locally for registry
        for alpha in quantiles:
            model_dir = (
                Path("models")
                / "registry"
                / f"{config['mlflow']['model_name']}_q{int(alpha*100)}"
                / run_id
            )
            model_dir.mkdir(parents=True, exist_ok=True)
            all_models[alpha].save_model(str(model_dir / "model.txt"))
            with open(model_dir / "metadata.json", "w") as f:
                meta = model_meta.copy()
                meta["quantile"] = alpha
                meta["best_iteration"] = all_models[alpha].best_iteration
                json.dump(meta, f, indent=2, default=str)

        print(f"\nAll {len(quantiles)} quantile models saved!")
        print("Done!")


if __name__ == "__main__":
    main()
