<template>
  <div class="source-page">
    <section class="source-hero">
      <div>
        <span class="eyebrow">DATA CONNECTIONS</span>
        <h1>数据源与同步</h1>
        <p>统一管理平台授权和文件数据源，连接凭证只加密保存，不在页面和接口中回显。</p>
      </div>
      <ElButton v-auth="'add'" type="primary" size="large" @click="openDialog()">
        <ArtSvgIcon icon="ri:add-line" />新增数据源
      </ElButton>
    </section>

    <div class="summary-grid">
      <div class="summary-card">
        <span>符合条件的数据源</span><strong>{{ pagination.total }}</strong>
      </div>
      <div class="summary-card success">
        <span>当前页连接正常</span><strong>{{ connectedCount }}</strong>
      </div>
      <div class="summary-card danger">
        <span>当前页连接失败</span><strong>{{ failedCount }}</strong>
      </div>
      <div class="summary-card muted">
        <span>当前页待测试</span><strong>{{ untestedCount }}</strong>
      </div>
    </div>

    <ElCard class="filter-card" shadow="never">
      <ElForm :inline="true" :model="filters">
        <ElFormItem label="名称">
          <ElInput
            v-model="filters.name"
            clearable
            placeholder="搜索数据源名称"
            @keyup.enter="search"
          />
        </ElFormItem>
        <ElFormItem label="接入方式">
          <ElSelect v-model="filters.provider" clearable placeholder="全部方式">
            <ElOption
              v-for="item in providerSpecs"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="连接状态">
          <ElSelect v-model="filters.connectionStatus" clearable placeholder="全部状态">
            <ElOption label="连接正常" value="connected" />
            <ElOption label="连接失败" value="failed" />
            <ElOption label="待测试" value="untested" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" @click="search">查询</ElButton>
          <ElButton @click="resetFilters">重置</ElButton>
        </ElFormItem>
      </ElForm>
    </ElCard>

    <ElCard shadow="never">
      <ElTable v-loading="loading" :data="records" row-key="id">
        <ElTableColumn label="数据源" min-width="210">
          <template #default="{ row }">
            <div class="source-name"
              ><strong>{{ row.name }}</strong
              ><span>{{ row.id }}</span></div
            >
          </template>
        </ElTableColumn>
        <ElTableColumn label="接入方式" width="145">
          <template #default="{ row }">{{ providerLabel(row.provider) }}</template>
        </ElTableColumn>
        <ElTableColumn label="数据领域" width="120">
          <template #default="{ row }">{{ domainLabel(row.domain) }}</template>
        </ElTableColumn>
        <ElTableColumn label="连接状态" width="130">
          <template #default="{ row }">
            <ElTooltip :content="row.lastErrorMessage || statusLabel(row.connectionStatus)">
              <ElTag :type="statusType(row.connectionStatus)" effect="light" round>
                {{ statusLabel(row.connectionStatus) }}
              </ElTag>
            </ElTooltip>
          </template>
        </ElTableColumn>
        <ElTableColumn label="最近测试" width="180">
          <template #default="{ row }">{{ formatTime(row.lastTestedAt) }}</template>
        </ElTableColumn>
        <ElTableColumn label="最近同步" min-width="170">
          <template #default="{ row }">
            <div class="sync-state">
              <span>{{ syncLabel(row.lastSyncStatus) }}</span>
              <small>{{ formatTime(row.lastSyncAt) }}</small>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="90">
          <template #default="{ row }">
            <ElTag :type="row.enabled ? 'success' : 'info'">{{
              row.enabled ? '启用' : '停用'
            }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <ElButton
              v-auth="'test'"
              link
              type="primary"
              :loading="testingId === row.id"
              :disabled="!row.enabled"
              @click="testConnection(row)"
              >测试连接</ElButton
            >
            <ElButton v-auth="'edit'" link type="primary" @click="openDialog(row)">编辑</ElButton>
            <ElButton
              v-if="row.enabled"
              v-auth="'delete'"
              link
              type="danger"
              @click="disableSource(row)"
              >停用</ElButton
            >
          </template>
        </ElTableColumn>
        <template #empty>
          <ElEmpty description="暂无符合条件的数据源" />
        </template>
      </ElTable>
      <div class="pagination-wrap">
        <ElPagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
          @size-change="handleSizeChange"
        />
      </div>
    </ElCard>

    <SourceDialog
      v-model="dialogVisible"
      :source="editingSource"
      :provider-specs="providerSpecs"
      @saved="handleSaved"
    />
  </div>
</template>

<script setup lang="ts">
  import { ElMessage, ElMessageBox } from 'element-plus'
  import {
    fetchDataSourceList,
    fetchDataSourceProviders,
    fetchDisableDataSource,
    fetchTestDataSourceConnection
  } from '@/api/data-sources'
  import SourceDialog from './modules/source-dialog.vue'

  defineOptions({ name: 'DataSources' })

  const domainLabels: Record<Api.DataSource.Domain, string> = {
    advertising: '广告投放',
    orders: '订单',
    products: '商品',
    costs: '成本',
    inventory: '库存',
    refunds: '退款',
    reviews: '评价',
    currency_rates: '汇率',
    creatives: '素材'
  }
  const statusLabels = { connected: '连接正常', failed: '连接失败', untested: '待测试' }
  const statusTypes = { connected: 'success', failed: 'danger', untested: 'info' } as const
  const providerSpecs = ref<Api.DataSource.ProviderSpec[]>([])
  const records = ref<Api.DataSource.DataSourceItem[]>([])
  const loading = ref(false)
  const testingId = ref('')
  const dialogVisible = ref(false)
  const editingSource = ref<Api.DataSource.DataSourceItem>()
  const pagination = reactive({ current: 1, size: 20, total: 0 })
  const filters = reactive<Partial<Api.DataSource.SearchParams>>({
    name: undefined,
    provider: undefined,
    connectionStatus: undefined
  })
  const connectedCount = computed(
    () => records.value.filter((item) => item.connectionStatus === 'connected').length
  )
  const failedCount = computed(
    () => records.value.filter((item) => item.connectionStatus === 'failed').length
  )
  const untestedCount = computed(
    () => records.value.filter((item) => item.connectionStatus === 'untested').length
  )

  const providerLabel = (provider: Api.DataSource.Provider) =>
    providerSpecs.value.find((item) => item.value === provider)?.label || provider
  const domainLabel = (domain: Api.DataSource.Domain) => domainLabels[domain]
  const statusLabel = (status: Api.DataSource.ConnectionStatus) => statusLabels[status]
  const statusType = (status: Api.DataSource.ConnectionStatus) => statusTypes[status]
  const formatTime = (value: string | null) =>
    value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
  const syncLabel = (status: string | null) => {
    if (!status) return '尚未同步'
    return { completed: '同步完成', running: '同步中', failed: '同步失败' }[status] || status
  }

  const loadData = async () => {
    loading.value = true
    try {
      const result = await fetchDataSourceList({
        current: pagination.current,
        size: pagination.size,
        ...filters,
        sortBy: 'createdAt',
        sortOrder: 'desc'
      })
      records.value = result.records
      pagination.total = result.total
    } finally {
      loading.value = false
    }
  }
  const search = () => {
    pagination.current = 1
    loadData()
  }
  const resetFilters = () => {
    filters.name = undefined
    filters.provider = undefined
    filters.connectionStatus = undefined
    search()
  }
  const handleSizeChange = () => {
    pagination.current = 1
    loadData()
  }
  const openDialog = (source?: Api.DataSource.DataSourceItem) => {
    editingSource.value = source
    dialogVisible.value = true
  }
  const handleSaved = () => {
    editingSource.value = undefined
    loadData()
  }
  const testConnection = async (source: Api.DataSource.DataSourceItem) => {
    testingId.value = source.id
    try {
      const result = await fetchTestDataSourceConnection(source.id)
      if (result.status === 'connected') ElMessage.success(result.message)
      else ElMessage.error(result.message)
      await loadData()
    } finally {
      testingId.value = ''
    }
  }
  const disableSource = async (source: Api.DataSource.DataSourceItem) => {
    await ElMessageBox.confirm(
      `停用“${source.name}”后将不能创建新的同步任务，历史数据不会删除。`,
      '确认停用',
      { type: 'warning', confirmButtonText: '停用', cancelButtonText: '取消' }
    )
    await fetchDisableDataSource(source.id)
    ElMessage.success('数据源已停用')
    await loadData()
  }

  onMounted(async () => {
    providerSpecs.value = await fetchDataSourceProviders()
    await loadData()
  })
</script>

<style scoped lang="scss">
  .source-page {
    display: grid;
    gap: 16px;
  }
  .source-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    padding: 28px 30px;
    border-radius: 16px;
    color: #fff;
    background: linear-gradient(120deg, #172554, #1d4ed8 62%, #0891b2);
  }
  .source-hero h1 {
    margin: 5px 0 8px;
    font-size: 28px;
  }
  .source-hero p {
    max-width: 720px;
    margin: 0;
    color: rgb(255 255 255 / 78%);
  }
  .eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    color: #7dd3fc;
  }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }
  .summary-card {
    padding: 18px 20px;
    border: 1px solid var(--art-border-color);
    border-radius: 12px;
    background: var(--art-main-bg-color);
    box-shadow: 0 6px 20px rgb(15 23 42 / 4%);
  }
  .summary-card span {
    display: block;
    margin-bottom: 8px;
    color: var(--art-gray-600);
    font-size: 13px;
  }
  .summary-card strong {
    font-size: 25px;
    color: var(--main-color);
  }
  .summary-card.success strong {
    color: #16a34a;
  }
  .summary-card.danger strong {
    color: #dc2626;
  }
  .summary-card.muted strong {
    color: #64748b;
  }
  .filter-card :deep(.el-card__body) {
    padding-bottom: 4px;
  }
  .filter-card :deep(.el-select) {
    width: 170px;
  }
  .source-name {
    display: grid;
    gap: 4px;
  }
  .source-name span {
    color: var(--art-gray-500);
    font-size: 11px;
  }
  .sync-state {
    display: grid;
    gap: 3px;
  }
  .sync-state small {
    color: var(--art-gray-500);
  }
  .pagination-wrap {
    display: flex;
    justify-content: flex-end;
    padding-top: 18px;
  }
  @media (width <= 900px) {
    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .source-hero {
      align-items: flex-start;
      flex-direction: column;
    }
  }
  @media (width <= 560px) {
    .summary-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
