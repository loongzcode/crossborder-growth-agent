<template>
  <div class="operations-overview">
    <section class="hero art-card">
      <div>
        <span class="eyebrow">CROSS-BORDER OPERATIONS</span>
        <h1>经营决策总览</h1>
        <p>连接广告、订单、商品、利润、库存与合规数据，由九个 Agent 协同生成可追溯的经营建议。</p>
      </div>
      <ElTag type="warning" effect="light" round>工程初始化 · 暂无生产数据</ElTag>
    </section>

    <ElRow :gutter="16">
      <ElCol v-for="metric in metrics" :key="metric.label" :xs="12" :sm="12" :lg="6">
        <div class="metric-card art-card">
          <div
            class="metric-icon"
            :style="{ color: metric.color, background: `${metric.color}18` }"
          >
            <ArtSvgIcon :icon="metric.icon" />
          </div>
          <div
            ><span>{{ metric.label }}</span
            ><strong>{{ metric.value }}</strong></div
          >
        </div>
      </ElCol>
    </ElRow>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="15">
        <section class="art-card panel">
          <h2>系统能力地图</h2>
          <p class="panel-copy"
            >当前导航已经按最终 PRD 建立，后续模块将沿纵向业务切片接入真实 API。</p
          >
          <div class="capability-grid">
            <div v-for="item in capabilities" :key="item.title" class="capability-item">
              <ArtSvgIcon :icon="item.icon" />
              <div
                ><strong>{{ item.title }}</strong
                ><span>{{ item.description }}</span></div
              >
            </div>
          </div>
        </section>
      </ElCol>
      <ElCol :xs="24" :lg="9">
        <section class="art-card panel delivery-panel">
          <h2>当前交付状态</h2>
          <ElSteps direction="vertical" :active="1" finish-status="success">
            <ElStep title="需求与架构" description="PRD、Agent 地图与开发计划已固化" />
            <ElStep title="工程基础" description="Vue 管理端基座已接入，后端基础建设中" />
            <ElStep title="数据与 Agent" description="等待按计划实现与评测" />
            <ElStep title="集成验收" description="等待端到端验证" />
          </ElSteps>
        </section>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
  defineOptions({ name: 'Console' })

  const metrics = [
    { label: '已授权数据源', value: '0', icon: 'ri:database-2-line', color: '#377dff' },
    { label: '运行中任务', value: '0', icon: 'ri:loader-4-line', color: '#8b5cf6' },
    { label: '待审批决策', value: '0', icon: 'ri:task-line', color: '#f59e0b' },
    { label: '数据质量问题', value: '0', icon: 'ri:shield-check-line', color: '#10b981' }
  ]

  const capabilities = [
    { title: '数据治理', description: '自动同步、字段映射与质量校验', icon: 'ri:database-2-line' },
    { title: '广告诊断', description: '投产异常、归因与预算模拟', icon: 'ri:megaphone-line' },
    { title: '智能选品', description: '评分、回测与冷启动实验', icon: 'ri:shopping-bag-3-line' },
    {
      title: '客户与素材',
      description: '评价、退款、分群与创意疲劳',
      icon: 'ri:lightbulb-flash-line'
    },
    { title: '利润与供应', description: '贡献利润、库存覆盖与补货风险', icon: 'ri:funds-box-line' },
    {
      title: '合规与审批',
      description: '规则证据、高风险转人工与审计',
      icon: 'ri:shield-check-line'
    }
  ]
</script>

<style scoped lang="scss">
  .operations-overview {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .hero {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    padding: 28px;
    background:
      radial-gradient(circle at 90% 10%, rgb(55 125 255 / 16%), transparent 32%),
      var(--default-box-color);
  }
  .hero h1 {
    margin: 6px 0 8px;
    font-size: 28px;
    line-height: 1.25;
  }
  .hero p {
    max-width: 760px;
    margin: 0;
    color: var(--art-gray-600);
    line-height: 1.7;
  }
  .eyebrow {
    color: var(--main-color);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.14em;
  }
  .metric-card {
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 104px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .metric-icon {
    display: grid;
    width: 48px;
    height: 48px;
    border-radius: 14px;
    font-size: 22px;
    place-items: center;
  }
  .metric-card span,
  .metric-card strong {
    display: block;
  }
  .metric-card span {
    color: var(--art-gray-600);
    font-size: 13px;
  }
  .metric-card strong {
    margin-top: 3px;
    font-size: 25px;
  }
  .panel {
    min-height: 420px;
    padding: 24px;
  }
  .panel h2 {
    margin: 0;
    font-size: 18px;
  }
  .panel-copy {
    margin: 8px 0 20px;
    color: var(--art-gray-600);
    line-height: 1.6;
  }
  .capability-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  .capability-item {
    display: flex;
    gap: 12px;
    padding: 17px;
    border: 1px solid var(--art-gray-200);
    border-radius: 12px;
  }
  .capability-item > svg {
    flex: 0 0 auto;
    color: var(--main-color);
    font-size: 20px;
  }
  .capability-item strong,
  .capability-item span {
    display: block;
  }
  .capability-item span {
    margin-top: 5px;
    color: var(--art-gray-600);
    font-size: 12px;
    line-height: 1.5;
  }
  .delivery-panel h2 {
    margin-bottom: 24px;
  }
  @media (width <= 768px) {
    .hero {
      flex-direction: column;
      padding: 22px;
    }
    .capability-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
