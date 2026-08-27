# CrossBorder Growth Agent

面向跨境电商公司的多 Agent 经营决策系统，覆盖广告数据治理、投放诊断、利润核算、选品、库存供应、消费者洞察、素材分析与合规审查。

## Project status

Product requirements and the delivery plan are defined. The Vue administration console is initialized from Art Design Pro and mapped to the final operating workflows. The backend now includes strict Agent contracts, async persistence, advertising CSV/XLSX preview, schema governance, quality checks, and versioned business metric services.

## Core capabilities

- Automatically ingest and normalize advertising, order, product, cost, inventory, refund, and exchange-rate data.
- Diagnose advertising anomalies with traceable metric evidence.
- Calculate contribution profit instead of relying on ROAS alone.
- Rank existing and candidate products and generate cold-start test plans.
- Analyze audience behavior, reviews, refunds, and advertising creatives.
- Enforce inventory, supply-chain, platform-policy, and compliance constraints.
- Produce human-reviewable operating decisions, alerts, and daily reports.

## Agent system

The system is organized around one supervisor and eight domain agents:

1. Supervisor Agent
2. Data Governance Agent
3. Ad Performance Agent
4. Product Intelligence Agent
5. Customer Insight Agent
6. Creative Intelligence Agent
7. Profit & Supply Agent
8. Compliance & Risk Agent
9. Business Decision Agent

See [docs/architecture.md](docs/architecture.md) for the system boundary and collaboration model.

## Repository layout

```text
.
├── apps/
│   ├── api/              FastAPI application
│   └── web/              Vue administration console
├── packages/
│   ├── analytics/        Versioned deterministic business formulas
│   ├── connectors/       Platform connector contracts and file ingestion
│   ├── domain/           Strict domain and Agent contracts
│   └── persistence/      Async SQLAlchemy infrastructure
├── migrations/           Alembic database migrations
├── tests/                Unit and integration tests
├── docs/                 Architecture and product decisions
├── .editorconfig         Shared editor conventions
├── .env.example          Environment variable contract
├── .gitignore            Local and sensitive-file exclusions
└── README.md             Project overview
```

See [docs/requirements.md](docs/requirements.md), [docs/development-plan.md](docs/development-plan.md), and [docs/third-party-notices.md](docs/third-party-notices.md).

## Backend quick start

```bash
uv sync --group dev
uv run uvicorn crossborder_api.main:app --reload
```

Development API documentation is available at `http://127.0.0.1:8000/api/docs`. Run checks with:

```bash
uv run ruff check apps/api/src packages migrations tests
uv run ruff format --check apps/api/src packages migrations tests
uv run mypy
uv run pytest
```

Preview the synthetic TikTok Ads export without importing it:

```bash
curl -F "file=@data/samples/tiktok_ads_sample.csv" \
  http://127.0.0.1:8000/api/v1/ingestion/advertising/preview
```

## Data policy

Real merchant data must be anonymized before entering development, test, evaluation, or demonstration environments. Secrets and raw exports must never be committed.
