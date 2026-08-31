<template>
  <ElResult
    icon="success"
    title="数据已进入标准事实层"
    sub-title="本次导入已生成批次、同步任务与完整血缘记录。"
  >
    <template #extra>
      <div class="result-grid">
        <div
          ><span>原始行数</span><strong>{{ result.source_row_count }}</strong></div
        >
        <div
          ><span>成功导入</span><strong>{{ result.imported_row_count }}</strong></div
        >
        <div
          ><span>拒绝行数</span><strong>{{ result.rejected_row_count }}</strong></div
        >
        <div
          ><span>批次编号</span><strong class="batch-id">{{ result.raw_batch_id }}</strong></div
        >
      </div>
      <ElButton type="primary" @click="$emit('restart')">继续导入新文件</ElButton>
    </template>
  </ElResult>
</template>

<script setup lang="ts">
  defineProps<{ result: Api.Ingestion.ImportResult }>()
  defineEmits<{ restart: [] }>()
</script>

<style scoped lang="scss">
  .result-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    width: min(780px, 80vw);
    margin-bottom: 24px;

    div {
      padding: 16px;
      text-align: left;
      background: var(--art-main-bg-color);
      border: 1px solid var(--art-card-border);
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
      font-size: 20px;
    }

    .batch-id {
      overflow: hidden;
      font-size: 12px;
      text-overflow: ellipsis;
    }
  }

  @media (width <= 760px) {
    .result-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
