# AGENTS.md - Engineering Rules & Project Principles

## Project Overview
Retail Decision Intelligence System: ML-powered system for retail decision-making
Sales + Inventory Data → Data Engineering → Analytics → ML/Forecasting → Decision Engine → Actionable Recommendations → Dashboard

---

## Engineering Rules

### Code Quality
- **Type Safety**: Use strict typing (TypeScript/Python type hints) everywhere
- **Linting**: Code must pass lint checks before merge (configure per language)
- **Testing**: Minimum 80% coverage for business logic; 100% for critical paths
- **Documentation**: Docstrings for all public functions/classes; README per module

### Architecture Principles
- **Separation of Concerns**: Data, ML, API, UI layers strictly separated
- **Reproducibility**: All experiments tracked; models versioned with data lineage
- **Config over Code**: Environment-specific config in `config/`, not hardcoded
- **Immutability**: Raw data never modified; processed data derived via pipelines

### Data Engineering
- **Pipeline Idempotency**: Re-running pipelines produces same results
- **Schema Validation**: Enforce schemas at ingestion and transformation boundaries
- **Data Contracts**: Explicit contracts between pipeline stages
- **Observability**: Logging, metrics, and alerting on all data flows

### ML Practices
- **Experiment Tracking**: Every training run logged with params, metrics, artifacts
- **Model Registry**: Versioned models with metadata (training data, metrics, purpose)
- **Feature Store**: Centralized feature definitions; reuse over reinvention
- **Monitoring**: Drift detection, performance monitoring in production

### Git Workflow
- **Branch Strategy**: `main` (protected), feature branches, release tags
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
- **PR Reviews**: Required; minimum 1 approval; CI must pass
- **No Direct Pushes** to `main`

### Security
- **Secrets**: Never commit secrets; use `.env` (gitignored) or secret managers
- **Dependencies**: Regular vulnerability scanning; pin versions
- **Data Privacy**: PII anonymization; compliance with data regulations

---

## Project Principles

1. **Decisions Over Predictions**: ML serves business decisions, not just accuracy metrics
2. **Actionable Outputs**: Every model output maps to a concrete business action
3. **Explainability First**: Stakeholders must understand *why* a recommendation was made
4. **Iterative Delivery**: Ship working slices; improve incrementally
5. **Domain Expertise > Algorithms**: Retail knowledge drives feature engineering
6. **Cost-Aware**: Optimize for business ROI, not just model performance
7. **Human-in-the-Loop**: Critical decisions require human validation

---

## Directory Conventions

| Directory | Purpose |
|-----------|---------|
| `data/raw/` | Immutable source data (never modified) |
| `data/processed/` | Derived datasets from pipelines |
| `docs/` | Architecture, API specs, runbooks, ADRs |
| `src/` | Production source code (packages/modules) |
| `models/` | Trained model artifacts, configs, registries |
| `notebooks/` | Exploratory analysis, prototyping (not production) |
| `tests/` | Unit, integration, contract tests |
| `scripts/` | One-off operational scripts, migrations |
| `config/` | Environment configs, pipeline params, feature flags |

---

## Tooling Standards (to be configured)
- **Language**: Python 3.11+ (primary), TypeScript (dashboard)
- **Package Manager**: uv (Python), pnpm (Node)
- **ML Framework**: TBD (PyTorch/LightGBM/Prophet/etc.)
- **Orchestration**: TBD (Airflow/Dagster/Prefect)
- **Tracking**: MLflow or Weights & Biases
- **Testing**: pytest, vitest
- **Linting**: ruff, eslint
- **Formatting**: black, prettier