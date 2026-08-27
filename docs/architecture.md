# System Architecture

## Product boundary

CrossBorder Growth Agent is an internal decision-support system for a cross-border e-commerce company. It connects operating data with specialized AI agents, deterministic analytical tools, risk controls, and human approval.

The system may recommend actions but must not publish products, modify advertising budgets, or perform other high-impact account operations without explicit human approval.

## Agent responsibilities

| Agent | Responsibility |
| --- | --- |
| Supervisor Agent | Interpret requests, build execution plans, route work, manage state, and resolve missing information. |
| Data Governance Agent | Map changing source schemas, assess data quality, identify ambiguity, and request clarification. |
| Ad Performance Agent | Diagnose advertising anomalies, compare periods, analyze attribution, and simulate budget changes. |
| Product Intelligence Agent | Discover high-potential products, evaluate candidates, rank opportunities, and design cold-start tests. |
| Customer Insight Agent | Analyze segments, reviews, refunds, demand signals, and product-market fit. |
| Creative Intelligence Agent | Analyze video, image, and copy performance; detect fatigue; and produce evidence-based creative briefs. |
| Profit & Supply Agent | Calculate contribution profit and evaluate inventory, logistics, replenishment, currency, and supply risk. |
| Compliance & Risk Agent | Check platform policy, claims, intellectual-property risk, evidence quality, and decision risk. |
| Business Decision Agent | Reconcile specialist outputs and produce prioritized, evidence-linked actions for human review. |

## Non-agent services

These capabilities are deterministic infrastructure and must not be presented as agents:

- Platform connectors and scheduled synchronization
- File parsing, OCR, schema storage, and data warehousing
- Metric formulas, currency conversion, and read-only SQL execution
- Feature windows and anomaly algorithms
- Knowledge retrieval and policy indexing
- Authentication, authorization, audit logging, and secret management
- Evaluation datasets, backtesting, tracing, and runtime monitoring
- Report rendering and export

## Main decision flows

### Advertising diagnosis

```text
Data sync -> quality validation -> advertising diagnosis
          -> profit and supply checks -> customer/creative investigation
          -> compliance review -> decision synthesis -> human approval
```

### Product selection

```text
Candidate intake -> data validation -> opportunity ranking
                 -> customer fit -> profit and supply checks
                 -> creative test plan -> compliance review
                 -> decision synthesis -> human approval -> outcome feedback
```

### Daily operating review

```text
Scheduled refresh -> supervisor plan -> parallel specialist analysis
                  -> evidence aggregation -> risk review
                  -> prioritized daily actions -> human approval
```

## Reliability principles

- Structured inputs and outputs at every agent boundary
- Read-only, allow-listed analytical queries
- Explicit timeouts, retries, circuit breaking, and deterministic fallbacks
- Evidence references attached to every material conclusion
- Checkpointed workflow state and resumable human-review steps
- Separate evaluation for routing, tool selection, calculations, diagnosis, and product-ranking backtests
