<template>
  <div class="import-page">
    <section class="import-hero">
      <div>
        <span class="eyebrow">CONTROLLED INGESTION</span>
        <h1>文件导入工作台</h1>
        <p>上传跨境业务报表，确认系统识别的列映射，再将通过校验的数据写入标准事实层。</p>
      </div>
      <ElTag size="large" effect="dark" type="primary">映射签名 + 文件校验和双重锁定</ElTag>
    </section>

    <ElCard class="step-card" shadow="never">
      <ElSteps :active="activeStep" finish-status="success" align-center>
        <ElStep title="选择数据源" description="绑定组织与业务领域" />
        <ElStep title="上传预检" description="识别表头与数据质量" />
        <ElStep title="确认映射" description="人工修正或复用模板" />
        <ElStep title="正式导入" description="生成事实与血缘记录" />
      </ElSteps>
    </ElCard>

    <ElCard v-if="!importResult" class="workspace-card" shadow="never">
      <div class="source-grid">
        <ElFormItem label="数据源">
          <ElSelect
            v-model="dataSourceId"
            filterable
            placeholder="请选择已启用的数据源"
            style="width: 100%"
            @change="handleSourceChange"
          >
            <ElOption
              v-for="source in dataSources"
              :key="source.id"
              :label="`${source.name} · ${domainLabels[source.domain]}`"
              :value="source.id"
            />
          </ElSelect>
        </ElFormItem>

        <ElFormItem label="映射模板">
          <ElSelect
            v-model="selectedTemplateId"
            clearable
            placeholder="可选：复用历史模板"
            style="width: 100%"
            :disabled="!dataSourceId"
            @change="handleTemplateChange"
          >
            <ElOption
              v-for="template in activeTemplates"
              :key="template.id"
              :label="`${template.name} · v${template.version}`"
              :value="template.id"
            />
          </ElSelect>
        </ElFormItem>
      </div>

      <ElUpload
        class="file-drop"
        drag
        action="#"
        accept=".csv,.xlsx"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
      >
        <ArtSvgIcon icon="ri:upload-cloud-2-line" class="upload-icon" />
        <div class="el-upload__text">将 CSV / XLSX 拖到这里，或<em>点击选择文件</em></div>
        <template #tip>
          <div class="el-upload__tip"
            >单个文件不超过 10 MB；服务端会重新解析，不信任浏览器计算结果。</div
          >
        </template>
      </ElUpload>

      <div class="action-row">
        <ElButton
          v-auth="'preview'"
          type="primary"
          size="large"
          :loading="previewing"
          :disabled="!dataSourceId || !uploadFile"
          @click="handlePreview"
        >
          {{ preview ? (mappingDirty ? '应用映射并重新预检' : '重新预检') : '开始预检' }}
        </ElButton>
        <span v-if="mappingDirty" class="dirty-tip">映射已修改，需重新预检后才能导入</span>
      </div>

      <template v-if="preview">
        <ElDivider />
        <div class="metric-grid">
          <div
            ><span>文件行数</span><strong>{{ preview.source_row_count }}</strong></div
          >
          <div class="success"
            ><span>校验通过</span><strong>{{ preview.accepted_row_count }}</strong></div
          >
          <div :class="{ danger: preview.rejected_row_count }">
            <span>拒绝行数</span><strong>{{ preview.rejected_row_count }}</strong>
          </div>
          <div
            ><span>表头所在行</span><strong>{{ preview.header_row_number }}</strong></div
          >
        </div>

        <div v-if="preview.issues.length" class="issue-block">
          <ElAlert
            v-for="(issue, index) in preview.issues.slice(0, 8)"
            :key="`${issue.code}-${issue.row_number}-${index}`"
            :title="issue.message"
            :type="issue.severity === 'error' ? 'error' : 'warning'"
            :closable="false"
            show-icon
          />
          <p v-if="preview.issues.length > 8">另有 {{ preview.issues.length - 8 }} 条问题未展开</p>
        </div>

        <MappingTable
          v-model="mappings"
          :fields="canonicalFields"
          :required-fields="requiredFields"
          @change="markMappingDirty"
        />

        <div class="template-bar">
          <ElInput
            v-model="templateName"
            maxlength="120"
            placeholder="模板名称，例如：TikTok 广告日报"
          />
          <ElButton
            v-auth="'template'"
            :loading="savingTemplate"
            :disabled="!mappingReady || mappingDirty"
            @click="saveTemplate"
          >
            保存为映射模板
          </ElButton>
          <span>保存同名模板会自动生成新版本，旧版本继续保留。</span>
        </div>

        <div class="confirm-bar">
          <div>
            <strong>确认写入标准事实层</strong>
            <p>导入时服务端会再次核对文件 SHA-256 和列映射签名，任何变化都会拒绝。</p>
          </div>
          <ElButton
            v-auth="'import'"
            type="success"
            size="large"
            :loading="importing"
            :disabled="!canImport"
            @click="confirmImport"
          >
            正式导入 {{ preview.accepted_row_count }} 行
          </ElButton>
        </div>
      </template>
    </ElCard>

    <ElCard v-else class="workspace-card" shadow="never">
      <ImportResult :result="importResult" @restart="resetWorkspace" />
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import type { UploadFile } from 'element-plus'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { fetchDataSourceList } from '@/api/data-sources'
  import {
    fetchConfirmImport,
    fetchFieldCatalog,
    fetchIngestionPreview,
    fetchMappingTemplates,
    fetchSaveMappingTemplate
  } from '@/api/ingestion'
  import ImportResult from './modules/import-result.vue'
  import MappingTable from './modules/mapping-table.vue'

  const dataSources = ref<Api.DataSource.DataSourceItem[]>([])
  const dataSourceId = ref('')
  const uploadFile = ref<File | null>(null)
  const preview = ref<Api.Ingestion.Preview | null>(null)
  const mappings = ref<Api.Ingestion.ColumnMapping[]>([])
  const requiredFields = ref<string[]>([])
  const canonicalFields = ref<string[]>([])
  const templates = ref<Api.Ingestion.MappingTemplate[]>([])
  const selectedTemplateId = ref('')
  const templateName = ref('')
  const mappingDirty = ref(false)
  const previewing = ref(false)
  const savingTemplate = ref(false)
  const importing = ref(false)
  const importResult = ref<Api.Ingestion.ImportResult | null>(null)

  const domainLabels: Record<Api.DataSource.Domain, string> = {
    advertising: '广告',
    orders: '订单',
    products: '商品',
    costs: '成本',
    inventory: '库存',
    refunds: '退款',
    reviews: '评价',
    currency_rates: '汇率',
    creatives: '素材'
  }

  const selectedSource = computed(() =>
    dataSources.value.find((source) => source.id === dataSourceId.value)
  )
  const activeTemplates = computed(() => templates.value.filter((template) => template.active))
  const mappingPayload = computed<Api.Ingestion.MappingOverride[]>(() =>
    mappings.value.map(({ source_column, canonical_field }) => ({
      source_column,
      canonical_field
    }))
  )
  const mappingReady = computed(() => {
    const selected = new Set(
      mappings.value.map((mapping) => mapping.canonical_field).filter(Boolean)
    )
    return (
      mappings.value.every((mapping) => mapping.status !== 'needs_review') &&
      requiredFields.value.every((field) => selected.has(field))
    )
  })
  const canImport = computed(
    () =>
      Boolean(preview.value?.accepted_row_count) &&
      preview.value?.rejected_row_count === 0 &&
      mappingReady.value &&
      !mappingDirty.value
  )
  const activeStep = computed(() => {
    if (importResult.value) return 4
    if (preview.value) return 2
    if (uploadFile.value) return 1
    return dataSourceId.value ? 1 : 0
  })

  const loadDataSources = async () => {
    const page = await fetchDataSourceList({ current: 1, size: 100, enabled: true })
    dataSources.value = page.records
  }

  const clearPreview = () => {
    preview.value = null
    mappings.value = []
    mappingDirty.value = false
    importResult.value = null
  }

  const handleSourceChange = async () => {
    clearPreview()
    selectedTemplateId.value = ''
    templateName.value = ''
    templates.value = []
    requiredFields.value = []
    canonicalFields.value = []
    if (!selectedSource.value) return
    const [catalog, page] = await Promise.all([
      fetchFieldCatalog(selectedSource.value.domain),
      fetchMappingTemplates(selectedSource.value.id)
    ])
    requiredFields.value = catalog.required_fields
    canonicalFields.value = Object.keys(catalog.aliases)
    templates.value = page.records
  }

  const handleTemplateChange = () => {
    if (preview.value) {
      preview.value = null
      mappings.value = []
    }
    mappingDirty.value = false
  }

  const handleFileChange = (file: UploadFile) => {
    uploadFile.value = file.raw || null
    clearPreview()
  }

  const handleFileRemove = () => {
    uploadFile.value = null
    clearPreview()
  }

  const handlePreview = async () => {
    if (!selectedSource.value || !uploadFile.value) return
    previewing.value = true
    try {
      const result = await fetchIngestionPreview(
        selectedSource.value.id,
        selectedSource.value.domain,
        uploadFile.value,
        mappingDirty.value
          ? { mappings: mappingPayload.value }
          : { templateId: selectedTemplateId.value || undefined }
      )
      preview.value = result
      mappings.value = result.mappings.map((mapping) => ({ ...mapping }))
      mappingDirty.value = false
      if (result.mapping_template_id) selectedTemplateId.value = result.mapping_template_id
    } finally {
      previewing.value = false
    }
  }

  const markMappingDirty = () => {
    mappingDirty.value = true
    selectedTemplateId.value = ''
  }

  const saveTemplate = async () => {
    if (!preview.value || !selectedSource.value) return
    if (!templateName.value.trim()) {
      ElMessage.warning('请输入模板名称')
      return
    }
    savingTemplate.value = true
    try {
      const saved = await fetchSaveMappingTemplate(selectedSource.value.id, {
        name: templateName.value.trim(),
        domain: selectedSource.value.domain,
        schema_version: preview.value.schema_version,
        mappings: mappingPayload.value,
        expected_mapping_signature: preview.value.mapping_signature
      })
      templates.value = [
        saved,
        ...templates.value.map((template) =>
          template.name.toLowerCase() === saved.name.toLowerCase()
            ? { ...template, active: false }
            : template
        )
      ]
      selectedTemplateId.value = saved.id
    } finally {
      savingTemplate.value = false
    }
  }

  const confirmImport = async () => {
    if (!preview.value || !selectedSource.value || !uploadFile.value) return
    try {
      await ElMessageBox.confirm(
        `确认将 ${preview.value.accepted_row_count} 行数据写入“${selectedSource.value.name}”？`,
        '正式导入确认',
        { type: 'warning', confirmButtonText: '确认导入', cancelButtonText: '再检查一下' }
      )
    } catch {
      return
    }
    importing.value = true
    try {
      importResult.value = await fetchConfirmImport(
        selectedSource.value.id,
        selectedSource.value.domain,
        uploadFile.value,
        preview.value,
        mappingPayload.value
      )
    } finally {
      importing.value = false
    }
  }

  const resetWorkspace = () => {
    uploadFile.value = null
    selectedTemplateId.value = ''
    templateName.value = ''
    clearPreview()
  }

  onMounted(loadDataSources)
</script>

<style scoped lang="scss">
  .import-page {
    padding: 4px;

    .import-hero {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 28px 32px;
      margin-bottom: 16px;
      color: #fff;
      background:
        radial-gradient(circle at 88% 20%, rgb(49 212 172 / 35%), transparent 28%),
        linear-gradient(125deg, #102c3a, #153f54 58%, #176078);
      border-radius: 16px;

      .eyebrow {
        font-size: 11px;
        letter-spacing: 0.18em;
        opacity: 0.72;
      }

      h1 {
        margin: 8px 0;
        font-size: 28px;
      }

      p {
        margin: 0;
        opacity: 0.78;
      }
    }

    .step-card,
    .workspace-card {
      margin-bottom: 16px;
      border: 0;
      border-radius: 14px;
    }

    .source-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }

    .file-drop {
      margin-top: 4px;

      .upload-icon {
        display: block;
        margin: 0 auto 12px;
        font-size: 44px;
        color: var(--el-color-primary);
      }
    }

    .action-row,
    .template-bar,
    .confirm-bar {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 20px;
    }

    .dirty-tip {
      color: var(--el-color-warning);
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 20px;

      div {
        padding: 18px;
        background: var(--art-main-bg-color);
        border-radius: 10px;
      }

      span,
      strong {
        display: block;
      }

      span {
        margin-bottom: 8px;
        color: var(--art-text-gray-600);
      }

      strong {
        font-size: 26px;
      }

      .success strong {
        color: var(--el-color-success);
      }

      .danger strong {
        color: var(--el-color-danger);
      }
    }

    .issue-block {
      display: grid;
      gap: 8px;
      margin-bottom: 20px;
    }

    .template-bar {
      padding: 18px;
      background: var(--art-main-bg-color);
      border-radius: 10px;

      .el-input {
        width: 310px;
      }

      span {
        color: var(--art-text-gray-600);
      }
    }

    .confirm-bar {
      justify-content: space-between;
      padding: 22px;
      background: linear-gradient(105deg, rgb(33 150 120 / 10%), rgb(64 158 255 / 8%));
      border: 1px solid rgb(33 150 120 / 20%);
      border-radius: 12px;

      p {
        margin: 6px 0 0;
        color: var(--art-text-gray-600);
      }
    }
  }

  @media (width <= 800px) {
    .import-page {
      .import-hero {
        align-items: flex-start;
        gap: 18px;
        flex-direction: column;
      }

      .source-grid,
      .metric-grid {
        grid-template-columns: 1fr 1fr;
      }

      .template-bar,
      .confirm-bar {
        align-items: stretch;
        flex-direction: column;

        .el-input {
          width: 100%;
        }
      }
    }
  }
</style>
