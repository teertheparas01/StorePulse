"""Model Serving API for Hurdle Demand Forecasting."""

import json
import os
import warnings
from datetime import UTC, datetime
from pathlib import Path

import lightgbm as lgb
import pandas as pd
import yaml
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from pipeline.recommendations import ProductAlternativeResearcher, generate_recommendation

warnings.filterwarnings("ignore")


CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "ml.yaml"
REGISTRY_DIR = Path(__file__).parent.parent.parent.parent / "models" / "registry"
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FEATURE_METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "feature_metadata.json"
MONITORING_DIR = PROJECT_ROOT / "monitoring"
BACKTEST_DIR = PROJECT_ROOT / "backtest_results"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _read_json(path: Path) -> dict:
    """Read a JSON artifact, returning an empty object when unavailable."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _latest_json(directory: Path, pattern: str) -> dict:
    """Load the newest JSON artifact matching a pattern."""
    files = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return _read_json(files[0]) if files else {}


def dashboard_data() -> dict:
    """Build the dashboard summary from local pipeline artifacts."""
    metadata = _read_json(FEATURE_METADATA_PATH)
    dataset = metadata.get("dataset_info", {})
    monitoring = _latest_json(MONITORING_DIR, "monitoring_report_*.json")
    backtest = _latest_json(BACKTEST_DIR, "policy_comparison_*.json")
    drift = monitoring.get("feature_drift", {})
    drifted_features = [name for name, result in drift.items() if result.get("drift_detected")]
    policy_metrics = [
        {"name": name, **metrics}
        for name, metrics in backtest.items()
        if isinstance(metrics, dict) and "total_cost" in metrics
    ]
    policy_metrics.sort(key=lambda item: item["total_cost"])
    operational_policies = [
        policy for policy in policy_metrics if policy["name"] != "oracle_perfect"
    ]

    config = server.config if server is not None else load_config()
    web_config = config.get("recommendations", {}).get("web_search", {})
    api_key_env = web_config.get("api_key_env", "BRAVE_SEARCH_API_KEY")
    return {
        "dataset": {
            "rows": dataset.get("rows", 0),
            "columns": dataset.get("columns", 0),
            "store_products": dataset.get("unique_store_product", 0),
            "date_range": dataset.get("date_range", []),
        },
        "model": {
            "name": config.get("mlflow", {}).get("model_name", "demand_forecaster"),
            "loaded": server is not None,
            "features": len(server.feature_cols) if server is not None else 0,
        },
        "web_search": {
            "provider": web_config.get("provider", "brave"),
            "configured": bool(os.getenv(api_key_env)),
        },
        "monitoring": {
            "timestamp": monitoring.get("timestamp"),
            "drifted_features": drifted_features,
            "drift_count": len(drifted_features),
        },
        "backtest": {
            "policies": policy_metrics[:6],
            "best_policy": operational_policies[0] if operational_policies else None,
        },
    }


class HurdleModelServer:
    def __init__(self, config):
        self.config = config
        self.model_name = config["mlflow"]["model_name"]
        self.quantiles = config["model"].get("quantiles", [0.1, 0.5, 0.9])
        self.feature_cols = None
        self.cat_features = None
        self.binary_threshold = None
        self._load_models()

    def _load_models(self):
        """Load latest hurdle model components from registry."""
        model_dir = REGISTRY_DIR / f"{self.model_name}_hurdle"
        if not model_dir.exists():
            raise FileNotFoundError(f"Hurdle model directory not found: {model_dir}")

        versions = [d for d in model_dir.iterdir() if d.is_dir()]
        if not versions:
            raise FileNotFoundError(f"No model versions found in {model_dir}")

        latest = max(versions, key=lambda d: d.stat().st_mtime)
        print(f"Loading hurdle model from {latest}")

        # Load binary model
        binary_model_file = latest / "binary_model.txt"
        self.binary_model = lgb.Booster(model_file=str(binary_model_file))

        # Load conditional models
        self.conditional_models = {}
        for q in self.quantiles:
            cond_file = latest / f"cond_model_q{int(q*100)}.txt"
            if cond_file.exists():
                self.conditional_models[q] = lgb.Booster(model_file=str(cond_file))
            else:
                raise FileNotFoundError(f"Conditional model not found: {cond_file}")

        # Load metadata
        meta_file = latest / "metadata.json"
        with open(meta_file) as f:
            metadata = json.load(f)

        self.feature_cols = metadata["feature_cols"]
        self.cat_features = metadata["cat_features"]
        self.binary_threshold = metadata["binary"]["metrics"]["best_threshold"]

        print(f"Loaded hurdle model: binary_threshold={self.binary_threshold:.4f}")
        print(f"Features: {len(self.feature_cols)}, Categorical: {len(self.cat_features)}")

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for prediction."""
        X = df[self.feature_cols].copy()
        X = X.fillna(-999)
        for col in self.cat_features:
            if col in X.columns:
                X[col] = X[col].astype("category")
        return X

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate hurdle model predictions.

        Returns DataFrame with columns:
        - demand_probability: P(demand > 0)
        - demand_binary: 1 if P(demand > 0) >= threshold else 0
        - quantile_10, quantile_50, quantile_90: conditional quantiles
        - hurdle_10, hurdle_50, hurdle_90: hurdle predictions (binary * conditional)
        """
        X = self._prepare_features(df)

        # Binary prediction
        binary_pred = self.binary_model.predict(X, num_iteration=self.binary_model.best_iteration)
        demand_binary = (binary_pred >= self.binary_threshold).astype(int)

        # Conditional predictions
        cond_preds = {}
        for q in self.quantiles:
            if q in self.conditional_models:
                cond_preds[q] = self.conditional_models[q].predict(
                    X, num_iteration=self.conditional_models[q].best_iteration
                )

        # Hurdle predictions
        result = (
            df[["date", "store", "product_no"]].copy()
            if all(c in df.columns for c in ["date", "store", "product_no"])
            else pd.DataFrame(index=df.index)
        )

        result["demand_probability"] = binary_pred
        result["demand_binary"] = demand_binary

        for q in self.quantiles:
            if q in cond_preds:
                result[f"quantile_{int(q*100)}"] = cond_preds[q]
                result[f"hurdle_{int(q*100)}"] = demand_binary * cond_preds[q]

        return result

    def predict_single(self, features: dict) -> dict:
        """Predict for a single store-product-date."""
        df = pd.DataFrame([features])
        result = self.predict(df)
        return result.iloc[0].to_dict()


# Flask API
app = Flask(__name__)
# Enable CORS for Vite dev server
CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*"], supports_credentials=True)
server = None


def init_server():
    global server
    config = load_config()
    server = HurdleModelServer(config)


@app.route("/health", methods=["GET"])
def health():
    config = server.config if server is not None else load_config()
    web_config = config.get("recommendations", {}).get("web_search", {})
    api_key_env = web_config.get("api_key_env", "BRAVE_SEARCH_API_KEY")
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "web_search_configured": bool(os.getenv(api_key_env)),
        }
    )


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Render the browser dashboard."""
    return render_template("dashboard.html")


@app.route("/dashboard-data", methods=["GET"])
def dashboard_summary():
    """Return dashboard KPIs and recent pipeline artifacts."""
    return jsonify(dashboard_data())


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Handle single prediction or batch
        if isinstance(data, dict):
            # Single prediction
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            # Batch prediction
            df = pd.DataFrame(data)
        else:
            return jsonify({"error": "Invalid data format"}), 400

        # Validate required columns
        missing = set(server.feature_cols) - set(df.columns)
        if missing:
            return jsonify({"error": f"Missing features: {missing}"}), 400

        result = server.predict(df)
        return jsonify(result.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    """Batch prediction with file upload."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.filename.endswith(".parquet"):
            df = pd.read_parquet(file)
        else:
            return jsonify({"error": "Unsupported file format"}), 400

        result = server.predict(df)
        return jsonify(result.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recommendations", methods=["POST"])
def recommendations():
    """Return explainable inventory actions for one or more feature rows."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            return jsonify({"error": "Invalid data format"}), 400

        missing = set(server.feature_cols) - set(df.columns)
        if missing:
            return jsonify({"error": f"Missing features: {missing}"}), 400

        predictions = server.predict(df)
        result = [
            generate_recommendation(
                row.to_dict(), prediction.to_dict(), server.config.get("recommendations")
            ).to_dict()
            for (_, row), (_, prediction) in zip(df.iterrows(), predictions.iterrows(), strict=True)
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/product-alternatives", methods=["POST"])
def product_alternatives():
    """Search the web for better comparable products."""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({"error": "A product object is required"}), 400

        config = server.config if server is not None else load_config()
        web_config = config.get("recommendations", {}).get("web_search", {})
        researcher = ProductAlternativeResearcher.from_config(web_config)
        limit = int(data.get("limit", web_config.get("default_limit", 5)))
        return jsonify(researcher.find_alternatives(data, limit=max(1, min(limit, 10))))
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/model/info", methods=["GET"])
def model_info():
    return jsonify(
        {
            "model_name": server.model_name,
            "quantiles": server.quantiles,
            "binary_threshold": server.binary_threshold,
            "n_features": len(server.feature_cols),
            "features": server.feature_cols,
            "categorical_features": server.cat_features,
        }
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode: load model and run sample prediction
        config = load_config()
        server = HurdleModelServer(config)

        # Test with sample data
        test_df = pd.read_parquet("data/processed/features/test_sample_1pct.parquet")
        test_df = test_df.head(5)
        result = server.predict(test_df)
        print("Test predictions:")
        print(result.to_string())
    else:
        # Server mode
        init_server()
        app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
