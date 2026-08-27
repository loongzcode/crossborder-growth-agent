# CrossBorder Growth Agent 开发计划书

## 1. 计划原则

本计划以完整产品范围为目标。实施阶段仅用于安排依赖和验证顺序，所有在 PRD 中定义的数据、九个 Agent、业务模块、审批、评测、管理端和部署能力都属于最终交付，不使用“先做简版、以后再说”的范围划分。

每个阶段都必须形成可运行、可测试、可提交的增量；任何简历成果描述都以代码、测试、评测报告或授权环境运行记录为依据。

## 2. 技术架构

### 2.1 技术栈

| 层级 | 选型 | 用途 |
| --- | --- | --- |
| 后端 API | Python 3.12、FastAPI、Pydantic v2 | API、配置、校验、OpenAPI |
| Agent 编排 | LangGraph | 状态图、动态路由、检查点、人工审批中断与恢复 |
| 数据访问 | SQLAlchemy 2.0 async、Alembic、PostgreSQL | 事务数据、审计、配置、工作流元数据 |
| 缓存/队列 | Redis | 缓存、任务协调、限流与短期状态 |
| 分析计算 | Polars、DuckDB | 文件导入、批量指标、回测与本地分析 |
| 前端 | Vue 3、TypeScript、Vite、Element Plus、Tailwind CSS | 基于 Art Design Pro 的管理端和分析工作台 |
| 状态与请求 | Pinia、Axios | 认证、组织上下文、服务端请求和少量本地 UI 状态 |
| 图表 | ECharts | 广告、利润、库存和评测可视化 |
| 测试 | pytest、pytest-asyncio、Ruff、mypy；Vue TSC、Vitest、Playwright | 单元、集成、契约和端到端测试 |
| 部署 | Docker Compose、GitHub Actions | 本地复现、CI 和演示环境 |

LLM 供应商通过统一接口适配，领域代码不直接依赖某一模型。没有 LLM 密钥时，确定性流程、模拟模型和大部分测试仍应可运行。

### 2.2 架构边界

```text
Vue Admin (Art Design Pro)
    -> FastAPI application API
        -> Auth / RBAC / Organization isolation
        -> Ingestion & metric services
        -> LangGraph workflow runtime
             -> Supervisor
             -> 8 domain agents
             -> deterministic tools
             -> checkpoint / approval
        -> PostgreSQL / Redis / object storage abstraction
        -> evaluation & backtest runner
```

Agent 不直接持有数据库连接或平台密钥。工具层负责权限、参数校验、只读查询、幂等和审计；Agent 只能通过注册工具访问业务能力。

### 2.3 代码仓库结构

```text
.
├── apps/
│   ├── api/                    FastAPI 入口、路由、中间件
│   └── web/                    Vue 管理端（Art Design Pro 基座）
├── packages/
│   ├── agent_core/             Agent 协议、Supervisor、状态图、检查点
│   ├── domain/                 领域实体、值对象、业务规则
│   ├── analytics/              指标、异常检测、利润和回测
│   ├── connectors/             平台 API、文件导入、模拟连接器
│   ├── persistence/            SQLAlchemy 模型、仓储、迁移
│   └── evaluation/             数据集、评分器、回归报告
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
├── data/
│   ├── samples/                可提交的合成/脱敏样例
│   └── evals/                  版本化评测案例
├── docs/
├── docker-compose.yml
└── pyproject.toml
```

## 3. 实施阶段

### 阶段 A：需求基线与工程基础

目标：形成可持续扩展的单仓工程和质量门槛。

任务：

- 固化 PRD、架构边界、指标口径、风险和验收标准。
- 建立 Python 包、FastAPI 应用、统一配置、日志、错误模型和健康检查。
- 建立 Pydantic 领域协议、SQLAlchemy 基础设施、Alembic 和测试数据库策略。
- 建立 Ruff、mypy、pytest、pre-commit/CI 基线。
- 引入 Art Design Pro 管理端基座，保留 MIT 许可声明，完成项目品牌、路由和 API 客户端边界调整。
- 建立 Docker Compose 的 PostgreSQL、Redis、API 和 Web 服务定义。

交付门：健康检查可运行；配置缺失能给出明确错误；单元测试与静态检查通过；仓库无密钥。

### 阶段 B：数据接入、治理和指标事实层

目标：先建立可信事实，再允许 Agent 推理。

任务：

- 定义连接器协议、同步游标、幂等键、错误分类和审计事件。
- 实现 CSV/XLSX 导入、自动表头探测、列名标准化和映射版本。
- 实现广告、订单、商品、成本、库存、退款、评价、汇率和素材元数据模型。
- 实现合成样例连接器；为 TikTok Ads/TikTok Shop 建立授权适配器和契约测试边界。
- 实现数据质量规则、问题队列和人工映射确认 API。
- 实现广告、贡献利润、盈亏平衡和库存覆盖的版本化公式。

交付门：相同批次重复导入不产生重复事实；核心公式与手工金标准一致；数据血缘可查询；无授权时也能通过样例数据完整演示。

### 阶段 C：Agent 协议与状态化编排

目标：完成 1+8 Agent 的统一运行框架。

任务：

- 定义 `AgentRequest`、`AgentResult`、`EvidenceRef`、`Risk`、`RecommendedAction` 等结构化协议。
- 实现 Agent 注册表、工具权限、超时、重试、错误隔离和确定性 fallback。
- 实现 Supervisor 意图分类、执行计划、条件边、并行分支和结果合并。
- 实现 PostgreSQL 检查点、运行事件、节点追踪和可恢复状态。
- 实现人工审批 interrupt/resume，并用幂等键保护外部动作。
- 先用规则/模拟模型确保流程可测，再接入可配置 LLM 适配器。

交付门：三条主流程均能从请求运行到决策；等待审批后可跨进程恢复；单节点失败不会丢失已完成结果；每条结论可附证据引用。

### 阶段 D：领域分析工具与九个 Agent 实现

目标：让每个 Agent 都有真实工具、边界和可验证输出。

任务：

- Data Governance：映射解释、口径冲突和质量摘要。
- Ad Performance：漏斗分解、周期比较、异常检测、归因比较和预算模拟。
- Product Intelligence：候选特征、硬约束、评分卡、时间切分回测和冷启动计划。
- Customer Insight：评价/退款主题、分群差异和商品—人群适配。
- Creative Intelligence：素材特征、表现关联、疲劳检测和创意 brief。
- Profit & Supply：贡献利润、汇率、盈亏平衡、库存覆盖和补货建议。
- Compliance & Risk：规则检索、声明检查、知识产权提示和不确定性升级。
- Business Decision：证据聚合、冲突消解、优先级和行动计划。
- Supervisor：根据请求和数据状态动态选择上述 Agent，而非固定全量调用。

交付门：每个 Agent 有正常、缺数据、工具失败和风险升级测试；输出通过 Schema；业务计算由确定性工具完成并可复算。

### 阶段 E：评测、回测和可观测性

目标：用证据证明系统行为，而不是依赖演示观感。

任务：

- 建立至少 80 条版本化评测案例和人工/规则金标准。
- 实现路由、工具、Schema、计算、证据、合规和运行成本评分器。
- 实现选品时间切分回测、基线模型和避免未来数据泄漏的验证。
- 建立 prompt/model/rule/formula 版本记录和回归对比。
- 实现运行追踪、节点耗时、token/成本、错误和重试指标。
- 输出机器可读 JSON 与人类可读 Markdown/HTML 评测报告。

交付门：评测可通过单命令复现；阻断问题能使 CI 失败；回测明确训练窗口、预测窗口和基线。

### 阶段 F：企业管理端与业务闭环

目标：将数据、Agent 和审批能力组合成可用的日常工作台。

任务：

- 登录、组织隔离、角色权限和导航。
- 经营总览、数据源/同步、数据质量中心。
- 广告诊断工作台和指标证据钻取。
- 选品候选池、评分卡、回测和冷启动实验。
- 利润供应、客户洞察、素材分析和合规审核页面。
- Agent 运行图、节点详情、证据引用和失败重试。
- 审批中心、每日简报和决策反馈。
- 响应式布局、加载/空/错误状态和无障碍基础检查。

交付门：核心流程 Playwright 测试通过；权限页面和 API 双重校验；任何建议都可回到来源证据。

### 阶段 G：集成、部署与验收

目标：完成可复现部署、全链路演示和项目证据整理。

任务：

- 完善 Docker 镜像、Compose、数据库迁移、种子数据和启动检查。
- 建立 GitHub Actions：格式、类型、单元、集成、前端和构建检查。
- 执行安全检查、脱敏检查、依赖审计和备份恢复演练。
- 执行三条端到端验收：广告诊断、选品决策、每日经营简报。
- 编写部署、运维、故障排查、演示脚本和架构决策记录。
- 根据实测结果形成项目说明和可用于面试的真实成果摘要。

交付门：全新环境按 README 可启动；关键测试和评测通过；敏感数据扫描无阻断项；验收记录可复查。

## 4. 测试策略

| 测试层 | 重点 |
| --- | --- |
| 单元测试 | 公式、状态转换、字段映射、评分、规则、权限判断 |
| 集成测试 | PostgreSQL/Redis、仓储、检查点、导入、API 和工作流 |
| 契约测试 | 平台连接器请求/响应、分页、限流、错误和 Schema 演进 |
| Agent 评测 | 路由、工具调用、证据、合规、结构化输出和成本 |
| 回测 | 选品排序在未来窗口的表现与基线对比 |
| 端到端测试 | 导入数据到诊断/选品、审批、报告和审计完整链路 |
| 安全测试 | 跨组织隔离、越权、提示注入、SQL 白名单、密钥泄漏 |

测试数据使用确定性种子生成，并覆盖空数据、重复数据、乱序、时区边界、币种、退款延迟、API 限流和部分失败。

## 5. 开发与提交节奏

每个阶段按以下循环执行：

1. 先补充或确认验收测试。
2. 实现最小完整垂直切片。
3. 运行格式、类型、单元和相关集成测试。
4. 更新文档和变更记录。
5. 使用清晰、单一职责的 Git 提交并推送功能分支。

计划提交检查点：

- `docs: define product requirements and delivery plan`
- `feat: establish backend foundation and domain contracts`
- `feat: add ingestion governance and metric services`
- `feat: implement agent runtime and supervisor workflow`
- `feat: add domain agents and decision tools`
- `test: add evaluation and product backtesting`
- `feat: build operations console and approval flows`
- `chore: complete deployment and acceptance automation`

## 6. 依赖与风险

| 风险/依赖 | 影响 | 应对 |
| --- | --- | --- |
| TikTok 等平台生产凭证和应用审核 | 无法验证真实 API 数据 | 保持连接器协议一致；使用官方文档契约、录制响应夹具和模拟/文件连接器；获得授权后再做生产验证 |
| 商家数据隐私 | 数据不可公开 | 脱敏、合成数据、最小权限、组织隔离、禁止原始数据入库到公开环境 |
| 不同平台归因与字段变化 | 指标误解或同步失败 | 映射版本、公式版本、契约测试、原始批次和数据血缘 |
| LLM 幻觉或不可用 | 错误建议或流程失败 | 确定性计算、证据约束、严格 Schema、超时重试、fallback、人工审批 |
| 选品未来数据泄漏 | 回测虚高 | 强制时间切分、特征截止时间检查、基线对照 |
| 多 Agent 成本和延迟 | 用户体验与费用不可控 | Supervisor 动态路由、并行执行、缓存、预算上限和运行指标 |
| 合规规则时效性 | 结论过期 | 规则来源与生效日期、更新任务、低置信转人工；不提供法律保证 |

## 7. 完成定义

一个任务只有在以下条件全部满足时才算完成：代码通过评审和自动化检查；测试覆盖正常与失败路径；日志不泄漏敏感信息；文档与接口同步；演示数据可复现；相关指标或评测结果已记录；未完成或未获授权的能力没有被包装成已上线成果。
