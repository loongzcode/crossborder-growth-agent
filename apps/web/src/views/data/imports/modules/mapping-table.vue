<template>
  <div class="mapping-panel">
    <div class="panel-title">
      <div>
        <h3>列映射确认</h3>
        <p>必填字段已标记 *。同一个标准字段只能映射一次。</p>
      </div>
      <ElTag :type="reviewCount ? 'danger' : 'success'">
        {{ reviewCount ? `${reviewCount} 项待处理` : '映射可用' }}
      </ElTag>
    </div>

    <ElTable :data="modelValue" max-height="430" stripe>
      <ElTableColumn prop="source_column" label="源文件列" min-width="180" />
      <ElTableColumn label="标准字段" min-width="230">
        <template #default="{ row }">
          <ElSelect
            :model-value="row.canonical_field"
            clearable
            filterable
            placeholder="忽略该列"
            style="width: 100%"
            @change="updateMapping(row.source_column, $event)"
          >
            <ElOption
              v-for="field in fields"
              :key="field"
              :label="requiredFields.includes(field) ? `${field} *` : field"
              :value="field"
              :disabled="isUsed(field, row.source_column)"
            />
          </ElSelect>
        </template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="130">
        <template #default="{ row }">
          <ElTag :type="statusMetaFor(row.status).type" effect="plain">
            {{ statusMetaFor(row.status).label }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="置信度" width="110">
        <template #default="{ row }">{{ Math.round(row.confidence * 100) }}%</template>
      </ElTableColumn>
    </ElTable>
  </div>
</template>

<script setup lang="ts">
  import type { TagProps } from 'element-plus'

  const props = defineProps<{
    modelValue: Api.Ingestion.ColumnMapping[]
    fields: string[]
    requiredFields: string[]
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: Api.Ingestion.ColumnMapping[]]
    change: []
  }>()

  const statusMeta: Record<Api.Ingestion.MappingStatus, { label: string; type: TagProps['type'] }> =
    {
      automatic: { label: '自动映射', type: 'success' },
      confirmed: { label: '人工确认', type: 'primary' },
      needs_review: { label: '需要确认', type: 'danger' },
      unmapped: { label: '已忽略', type: 'info' }
    }

  const reviewCount = computed(
    () => props.modelValue.filter((item) => item.status === 'needs_review').length
  )

  const statusMetaFor = (status: Api.Ingestion.MappingStatus | undefined) =>
    statusMeta[status || 'unmapped']

  const isUsed = (field: string, sourceColumn: string) =>
    props.modelValue.some(
      (item) => item.source_column !== sourceColumn && item.canonical_field === field
    )

  const updateMapping = (sourceColumn: string, value: string | null) => {
    emit(
      'update:modelValue',
      props.modelValue.map((item) =>
        item.source_column === sourceColumn
          ? {
              ...item,
              canonical_field: value || null,
              status: value ? 'confirmed' : 'unmapped',
              confidence: value ? 1 : 0
            }
          : item
      )
    )
    emit('change')
  }
</script>

<style scoped lang="scss">
  .mapping-panel {
    .panel-title {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 18px;

      h3 {
        margin: 0 0 5px;
        font-size: 18px;
      }

      p {
        margin: 0;
        color: var(--art-text-gray-600);
      }
    }
  }
</style>
