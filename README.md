# Retail Decision Intelligence System

ML-powered system for retail decision-making.

## Pipeline Overview

```
Sales + Inventory Data → Data Engineering → Analytics → ML/Forecasting → Decision Engine → Actionable Recommendations → Dashboard
```

## Project Structure

```
retail-decision-intelligence/
├── data/
│   ├── raw/           # Immutable source data (never modified)
│   └── processed/     # Derived datasets from pipelines
├── docs/              # Architecture, API specs, runbooks, ADRs
├── src/               # Production source code (packages/modules)
├── models/            # Trained model artifacts, configs, registries
├── notebooks/         # Exploratory analysis, prototyping (not production)
├── tests/             # Unit, integration, contract tests
├── scripts/           # One-off operational scripts, migrations
├── config/            # Environment configs, pipeline params, feature flags
├── AGENTS.md          # Engineering rules & project principles
└── README.md          # This file
```

## Getting Started

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Run the data pipeline and model API:

```bash
python scripts/run_pipeline.py
python scripts/build_features.py
python -m pipeline.ml.serve
```

The feature build creates a complete store-product calendar grid. The demand
targets use only complete future windows, so the last six days are null for the
7-day target rather than being treated as shortened forecasts.

## Principles

See [AGENTS.md](AGENTS.md) for engineering rules and project principles.

## Smart Recommendations

The model-serving layer can turn demand forecasts and current inventory into
explainable actions (`reorder`, `monitor`, `hold`, or `markdown`). After starting
the serving API, send feature rows to `POST /recommendations`. Each response
includes the action, priority, suggested order quantity, confidence, and rationale
for human approval.

For product replacement research, send a product to `POST /product-alternatives`.
The endpoint searches the public web and ranks comparable results using product
similarity, reported quality, price, and availability evidence. Set
`BRAVE_SEARCH_API_KEY` before starting the API; returned alternatives always include
their source URLs for verification.

`GET /health` reports whether the configured web-search key is available. If it
is not configured, the product-alternatives endpoint returns HTTP 503 rather than
silently producing an unverified recommendation.
