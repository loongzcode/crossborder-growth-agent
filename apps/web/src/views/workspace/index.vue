<template>
  <section class="art-card workspace-shell">
    <header>
      <div class="icon-wrap"><ArtSvgIcon :icon="workspace.icon" /></div>
      <div class="heading">
        <span class="eyebrow">{{ workspace.domain }}</span>
        <h1>{{ workspace.title }}</h1>
        <p>{{ workspace.description }}</p>
      </div>
      <ElTag type="info" effect="light" round>等待业务 API 接入</ElTag>
    </header>
    <ElDivider />
    <div class="workspace-grid">
      <div>
        <h2>交付范围</h2>
        <ul>
          <li v-for="item in workspace.deliverables" :key="item">
            <ArtSvgIcon icon="ri:checkbox-circle-line" /><span>{{ item }}</span>
          </li>
        </ul>
      </div>
      <ElAlert
        title="当前是工程骨架状态"
        type="warning"
        :closable="false"
        show-icon
        description="页面入口和产品边界已建立，但这里暂不展示虚构经营指标。后端事实层完成后，将通过真实 API 或明确标记的合成演示数据驱动界面。"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'

  defineOptions({ name: 'FeatureWorkspace' })

  interface WorkspaceDefinition {
    domain: string
    title: string
    description: string
    icon: string
    deliverables: string[]
  }

  const definitions: Record<string, WorkspaceDefinition> = {
    DataSources: {
      domain: 'DATA GOVERNANCE',
      title: '数据源与同步',
      description: '管理平台授权、文件导入、同步游标、批次与数据血缘。',
      icon: 'ri:database-2-line',
      deliverables: ['TikTok Ads / Shop 连接器协议', 'CSV/XLSX 自动导入', '同步任务、重试与审计']
    },
    DataQuality: {
      domain: 'DATA GOVERNANCE',
      title: '数据质量中心',
      description: '统一处理字段映射、口径冲突、完整性和时间连续性。',
      icon: 'ri:filter-3-line',
      deliverables: ['字段映射确认队列', '质量规则与问题等级', '指标公式、时区与币种版本']
    },
    AdDiagnosis: {
      domain: 'AD PERFORMANCE',
      title: '广告投产诊断',
      description: '从流量、点击、转化、客单、退款和素材等维度定位异常。',
      icon: 'ri:megaphone-line',
      deliverables: ['多层级指标钻取', '异常与根因证据链', '建议动作和复查条件']
    },
    BudgetSimulation: {
      domain: 'AD PERFORMANCE',
      title: '预算情景模拟',
      description: '在利润、库存和风险约束下比较预算调整方案。',
      icon: 'ri:line-chart-line',
      deliverables: ['预算上下限与假设', '贡献利润情景', '审批前影响预估']
    },
    ProductCandidates: {
      domain: 'PRODUCT INTELLIGENCE',
      title: '智能选品',
      description: '以可解释评分卡管理候选商品并生成冷启动测试计划。',
      icon: 'ri:shopping-bag-3-line',
      deliverables: ['候选池与硬约束', '多维评分证据卡', '冷启动预算与停止条件']
    },
    ProductBacktests: {
      domain: 'PRODUCT INTELLIGENCE',
      title: '选品回测',
      description: '使用严格时间切分验证候选排序对未来经营结果的预测能力。',
      icon: 'ri:history-line',
      deliverables: ['训练/预测窗口隔离', 'Precision@K 与 NDCG@K', '预测与真实结果反馈']
    },
    CustomerInsights: {
      domain: 'CUSTOMER INSIGHT',
      title: '客户洞察',
      description: '分析受众、评价、退款原因和商品—人群适配。',
      icon: 'ri:user-search-line',
      deliverables: ['评价与退款主题', '市场与新老客分群', '脱敏证据样本']
    },
    CreativeInsights: {
      domain: 'CREATIVE INTELLIGENCE',
      title: '素材洞察',
      description: '结合视频、图片、文案结构和投放表现识别创意机会。',
      icon: 'ri:movie-2-line',
      deliverables: ['素材结构化特征', '疲劳检测', '带证据的创意 brief']
    },
    ContributionProfit: {
      domain: 'PROFIT & SUPPLY',
      title: '贡献利润',
      description: '纳入商品、平台、支付、物流、税费、退款和广告成本计算真实利润。',
      icon: 'ri:money-dollar-circle-line',
      deliverables: ['订单与商品利润', '多币种换算', '盈亏平衡 CPA / ROAS']
    },
    InventoryRisk: {
      domain: 'PROFIT & SUPPLY',
      title: '库存与供应风险',
      description: '评估库存覆盖、在途、交期、补货和现金占用。',
      icon: 'ri:archive-stack-line',
      deliverables: ['库存覆盖天数', '缺货窗口', '补货数量与履约约束']
    },
    ComplianceReview: {
      domain: 'COMPLIANCE & RISK',
      title: '合规审核',
      description: '检查平台规则、营销声明、禁限售和知识产权风险。',
      icon: 'ri:shield-check-line',
      deliverables: ['规则来源与版本', '命中片段与严重等级', '低置信和高风险转人工']
    },
    AgentRuns: {
      domain: 'MULTI-AGENT RUNTIME',
      title: 'Agent 运行中心',
      description: '查看 Supervisor 路由、领域节点、工具调用、证据和失败恢复。',
      icon: 'ri:robot-2-line',
      deliverables: ['九个 Agent 执行图', '节点耗时与成本', '检查点、重试和追踪']
    },
    ApprovalCenter: {
      domain: 'HUMAN IN THE LOOP',
      title: '人工审批中心',
      description: '处理预算、广告、发布、补货和高风险内容等高影响建议。',
      icon: 'ri:task-line',
      deliverables: ['批准、驳回和修改后批准', '跨进程恢复', '审批意见与审计']
    },
    EvaluationCenter: {
      domain: 'AI EVALUATION',
      title: '评测中心',
      description: '持续评估路由、工具、计算、证据、合规和选品回测。',
      icon: 'ri:test-tube-line',
      deliverables: ['至少 80 条基准案例', '版本回归对比', '质量、延迟与成本报告']
    }
  }

  const route = useRoute()
  const workspace = computed(() => definitions[String(route.name)] ?? definitions.AgentRuns)
</script>

<style scoped lang="scss">
  .workspace-shell {
    min-height: calc(100vh - 150px);
    padding: 28px;
  }
  header {
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }
  .heading {
    flex: 1;
  }
  h1 {
    margin: 5px 0 8px;
    font-size: 26px;
  }
  h2 {
    margin: 0 0 16px;
    font-size: 16px;
  }
  p {
    margin: 0;
    color: var(--art-gray-600);
    line-height: 1.7;
  }
  .icon-wrap {
    display: grid;
    flex: 0 0 auto;
    width: 50px;
    height: 50px;
    border-radius: 14px;
    color: var(--main-color);
    background: color-mix(in srgb, var(--main-color) 12%, transparent);
    font-size: 23px;
    place-items: center;
  }
  .eyebrow {
    color: var(--main-color);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
  }
  .workspace-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 0.8fr);
    gap: 28px;
    margin-top: 24px;
  }
  ul {
    display: grid;
    gap: 12px;
    padding: 0;
    margin: 0;
    list-style: none;
  }
  li {
    display: flex;
    align-items: center;
    gap: 9px;
    color: var(--art-gray-700);
  }
  li svg {
    color: var(--main-color);
  }
  @media (width <= 768px) {
    header {
      flex-wrap: wrap;
    }
    .workspace-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
