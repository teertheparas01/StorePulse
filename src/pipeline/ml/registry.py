"""Model Registry - Versioned models with metadata."""

import json
import mlflow
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import yaml


REGISTRY_DIR = Path(__file__).parent.parent.parent.parent / "models" / "registry"
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "ml.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class ModelRegistry:
    def __init__(self, registry_dir: Path = REGISTRY_DIR):
        self.registry_dir = registry_dir
        self.registry_dir.mkdir(parents=True, exist_ok=True)
    
    def list_models(self) -> list:
        """List all registered model names."""
        return [d.name for d in self.registry_dir.iterdir() if d.is_dir()]
    
    def list_versions(self, model_name: str) -> list:
        """List all versions for a model."""
        model_dir = self.registry_dir / model_name
        if not model_dir.exists():
            return []
        versions = []
        for v in model_dir.iterdir():
            if v.is_dir():
                meta_file = v / "metadata.json"
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)
                    versions.append({
                        "version": v.name,
                        "run_id": meta.get("run_id"),
                        "timestamp": meta.get("timestamp"),
                        "val_rmse": meta.get("val_metrics", {}).get("val_rmse"),
                        "test_rmse": meta.get("test_metrics", {}).get("test_rmse"),
                    })
        return sorted(versions, key=lambda x: x["timestamp"], reverse=True)
    
    def get_model(self, model_name: str, version: str) -> Dict[str, Any]:
        """Load model and metadata."""
        model_dir = self.registry_dir / model_name / version
        meta_file = model_dir / "metadata.json"
        model_file = model_dir / "model.txt"
        
        if not meta_file.exists() or not model_file.exists():
            raise FileNotFoundError(f"Model {model_name} version {version} not found")
        
        with open(meta_file) as f:
            metadata = json.load(f)
        
        return {
            "metadata": metadata,
            "model_path": str(model_file),
            "version": version
        }
    
    def promote(self, model_name: str, version: str, stage: str = "Production") -> bool:
        """Promote a model version to a stage."""
        model_dir = self.registry_dir / model_name
        stage_file = model_dir / f".stage_{stage.lower()}"
        
        # Verify version exists
        if not (model_dir / version / "metadata.json").exists():
            raise ValueError(f"Version {version} not found")
        
        # Write stage pointer
        with open(stage_file, "w") as f:
            json.dump({
                "version": version,
                "promoted_at": datetime.utcnow().isoformat(),
                "stage": stage
            }, f, indent=2)
        
        print(f"Promoted {model_name} v{version} to {stage}")
        return True
    
    def get_production_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get current production model."""
        model_dir = self.registry_dir / model_name
        stage_file = model_dir / ".stage_production"
        
        if not stage_file.exists():
            return None
        
        with open(stage_file) as f:
            stage_info = json.load(f)
        
        return self.get_model(model_name, stage_info["version"])
    
    def compare_versions(self, model_name: str, version_a: str, version_b: str) -> Dict[str, Any]:
        """Compare two model versions."""
        v_a = self.get_model(model_name, version_a)
        v_b = self.get_model(model_name, version_b)
        
        metrics_a = v_a["metadata"].get("test_metrics", {})
        metrics_b = v_b["metadata"].get("test_metrics", {})
        
        comparison = {}
        for metric in ["test_rmse", "test_mae", "test_r2", "test_poisson_deviance"]:
            if metric in metrics_a and metric in metrics_b:
                diff = metrics_b[metric] - metrics_a[metric]
                better = "B" if diff < 0 else "A" if diff > 0 else "equal"
                comparison[metric] = {
                    "version_a": metrics_a[metric],
                    "version_b": metrics_b[metric],
                    "diff": diff,
                    "better": better
                }
        
        return comparison


def main():
    import sys
    
    registry = ModelRegistry()
    config = load_config()
    model_name = config["mlflow"]["model_name"]
    
    if len(sys.argv) < 2:
        print("Usage: python registry.py <command> [args]")
        print("Commands: list, versions, promote, production, compare")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        models = registry.list_models()
        for m in models:
            prod = registry.get_production_model(m)
            prod_tag = " [PRODUCTION]" if prod else ""
            print(f"  {m}{prod_tag}")
    
    elif cmd == "versions":
        if len(sys.argv) < 3:
            print("Usage: versions <model_name>")
            return
        versions = registry.list_versions(sys.argv[2])
        for v in versions:
            print(f"  {v['version']}: val_rmse={v['val_rmse']:.4f}, test_rmse={v['test_rmse']:.4f} ({v['timestamp']})")
    
    elif cmd == "promote":
        if len(sys.argv) < 4:
            print("Usage: promote <model_name> <version> [stage]")
            return
        stage = sys.argv[4] if len(sys.argv) > 4 else "Production"
        registry.promote(sys.argv[2], sys.argv[3], stage)
    
    elif cmd == "production":
        if len(sys.argv) < 3:
            print("Usage: production <model_name>")
            return
        prod = registry.get_production_model(sys.argv[2])
        if prod:
            print(f"Production: {prod['version']} (run_id: {prod['metadata']['run_id']})")
        else:
            print("No production model set")
    
    elif cmd == "compare":
        if len(sys.argv) < 4:
            print("Usage: compare <model_name> <version_a> <version_b>")
            return
        comp = registry.compare_versions(sys.argv[2], sys.argv[3], sys.argv[4])
        for metric, vals in comp.items():
            print(f"  {metric}: A={vals['version_a']:.4f}, B={vals['version_b']:.4f}, diff={vals['diff']:.4f}, better={vals['better']}")
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()