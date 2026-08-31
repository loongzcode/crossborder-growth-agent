<template>
  <ElDialog
    v-model="visible"
    :title="source ? '编辑数据源' : '新增数据源'"
    width="min(620px, 92vw)"
    align-center
    destroy-on-close
    @closed="resetForm"
  >
    <ElAlert
      class="security-alert"
      type="info"
      :closable="false"
      show-icon
      title="平台令牌和应用密钥会在服务端加密保存，保存后不再回显。"
    />
    <ElForm ref="formRef" :model="form" :rules="rules" label-width="108px">
      <ElFormItem label="数据源名称" prop="name">
        <ElInput v-model="form.name" maxlength="200" placeholder="例如：美国站广告账户" />
      </ElFormItem>
      <ElFormItem label="接入方式" prop="provider">
        <ElSelect
          v-model="form.provider"
          :disabled="Boolean(source)"
          @change="handleProviderChange"
        >
          <ElOption
            v-for="item in providerSpecs"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="数据领域" prop="domain">
        <ElSelect v-model="form.domain">
          <ElOption
            v-for="domain in selectedSpec?.domains || []"
            :key="domain"
            :label="domainLabels[domain]"
            :value="domain"
          />
        </ElSelect>
      </ElFormItem>
      <ElFormItem v-for="field in selectedSpec?.fields || []" :key="field.key" :label="field.label">
        <ElInput
          v-if="field.secret"
          v-model="form.credentials[field.key]"
          type="password"
          show-password
          autocomplete="new-password"
          :placeholder="source ? '留空表示保持现有凭证' : `请输入${field.label}`"
        />
        <ElInput
          v-else
          :model-value="String(form.configuration[field.key] ?? '')"
          :placeholder="`请输入${field.label}`"
          @update:model-value="(value) => (form.configuration[field.key] = value)"
        />
      </ElFormItem>
      <ElFormItem label="启用状态">
        <ElSwitch v-model="form.enabled" active-text="启用" inactive-text="停用" />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" :loading="submitting" @click="submit">保存数据源</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
  import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
  import { fetchCreateDataSource, fetchUpdateDataSource } from '@/api/data-sources'

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

  interface Props {
    modelValue: boolean
    source?: Api.DataSource.DataSourceItem
    providerSpecs: Api.DataSource.ProviderSpec[]
  }

  const props = withDefaults(defineProps<Props>(), { source: undefined })
  const emit = defineEmits<{
    (event: 'update:modelValue', value: boolean): void
    (event: 'saved'): void
  }>()
  const visible = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value)
  })
  const formRef = ref<FormInstance>()
  const submitting = ref(false)
  const form = reactive({
    name: '',
    provider: 'file_upload' as Api.DataSource.Provider,
    domain: 'advertising' as Api.DataSource.Domain,
    configuration: {} as Record<string, string | number | boolean>,
    credentials: {} as Record<string, string>,
    enabled: true
  })

  const selectedSpec = computed(() =>
    props.providerSpecs.find((item) => item.value === form.provider)
  )
  const rules: FormRules = {
    name: [
      { required: true, message: '请输入数据源名称', trigger: 'blur' },
      { min: 2, max: 200, message: '名称长度为 2 到 200 个字符', trigger: 'blur' }
    ],
    provider: [{ required: true, message: '请选择接入方式', trigger: 'change' }],
    domain: [{ required: true, message: '请选择数据领域', trigger: 'change' }]
  }

  const handleProviderChange = () => {
    form.configuration = {}
    form.credentials = {}
    form.domain = selectedSpec.value?.domains[0] || 'advertising'
  }

  const resetForm = () => {
    form.name = ''
    form.provider = 'file_upload'
    form.domain = props.providerSpecs[0]?.domains[0] || 'advertising'
    form.configuration = {}
    form.credentials = {}
    form.enabled = true
    formRef.value?.clearValidate()
  }

  watch(
    () => props.modelValue,
    (open) => {
      if (!open) return
      if (!props.source) {
        resetForm()
        return
      }
      form.name = props.source.name
      form.provider = props.source.provider
      form.domain = props.source.domain
      form.configuration = { ...props.source.configuration }
      form.credentials = {}
      form.enabled = props.source.enabled
    }
  )

  const validateProviderFields = (): boolean => {
    const missing = (selectedSpec.value?.fields || []).find((field) => {
      if (!field.required) return false
      if (field.secret && props.source?.hasCredentials) return false
      const bucket = field.secret ? form.credentials : form.configuration
      return !String(bucket[field.key] || '').trim()
    })
    if (missing) ElMessage.warning(`请填写${missing.label}`)
    return !missing
  }

  const submit = async () => {
    if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
    if (!validateProviderFields()) return
    const credentials: Api.DataSource.DataSourceWrite['credentials'] = {}
    if (form.credentials.accessToken?.trim()) {
      credentials.accessToken = form.credentials.accessToken.trim()
    }
    if (form.credentials.appSecret?.trim()) {
      credentials.appSecret = form.credentials.appSecret.trim()
    }
    const payload: Api.DataSource.DataSourceWrite = {
      name: form.name.trim(),
      provider: form.provider,
      domain: form.domain,
      configuration: { ...form.configuration },
      enabled: form.enabled,
      ...(Object.keys(credentials).length ? { credentials } : {})
    }
    submitting.value = true
    try {
      if (props.source) await fetchUpdateDataSource(props.source.id, payload)
      else await fetchCreateDataSource(payload)
      ElMessage.success(props.source ? '数据源更新成功' : '数据源创建成功')
      emit('saved')
      visible.value = false
    } finally {
      submitting.value = false
    }
  }
</script>

<style scoped>
  .security-alert {
    margin-bottom: 20px;
  }

  :deep(.el-select) {
    width: 100%;
  }
</style>
