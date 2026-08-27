# CrossBorder Growth Agent

面向跨境电商公司的多 Agent 经营决策系统，覆盖广告数据治理、投放诊断、利润核算、选品、库存供应、消费者洞察、素材分析与合规审查。

## Project status

Repository initialized. The current milestone is architecture and domain design; application code has not been implemented yet.

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
├── docs/                 Architecture and product decisions
├── .editorconfig         Shared editor conventions
├── .env.example          Environment variable contract
├── .gitignore            Local and sensitive-file exclusions
└── README.md             Project overview
```

## Data policy

Real merchant data must be anonymized before entering development, test, evaluation, or demonstration environments. Secrets and raw exports must never be committed.
