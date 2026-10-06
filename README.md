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

*Setup instructions will be added as the project evolves.*

## Principles

See [AGENTS.md](AGENTS.md) for engineering rules and project principles.