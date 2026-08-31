import request from '@/utils/http'

function ingestionPath(domain: Api.DataSource.Domain, action: 'preview' | 'import') {
  return domain === 'advertising'
    ? `/api/v1/ingestion/advertising/${action}`
    : `/api/v1/ingestion/datasets/${domain}/${action}`
}

export function fetchFieldCatalog(domain: Api.DataSource.Domain) {
  const url =
    domain === 'advertising'
      ? '/api/v1/ingestion/advertising/fields'
      : `/api/v1/ingestion/datasets/${domain}/fields`
  return request.get<Api.Ingestion.FieldCatalog>({ url })
}

export function fetchIngestionPreview(
  dataSourceId: string,
  domain: Api.DataSource.Domain,
  file: File,
  options: {
    mappings?: Api.Ingestion.MappingOverride[]
    templateId?: string
  } = {}
) {
  const data = new FormData()
  data.append('data_source_id', dataSourceId)
  data.append('file', file)
  if (options.mappings) data.append('mappings_json', JSON.stringify(options.mappings))
  if (options.templateId) data.append('template_id', options.templateId)
  return request.post<Api.Ingestion.Preview>({ url: ingestionPath(domain, 'preview'), data })
}

export function fetchMappingTemplates(dataSourceId: string) {
  return request.get<Api.Ingestion.MappingTemplatePage>({
    url: `/api/v1/ingestion/data-sources/${dataSourceId}/mapping-templates`,
    params: { active_only: false }
  })
}

export function fetchSaveMappingTemplate(
  dataSourceId: string,
  data: {
    name: string
    domain: Api.DataSource.Domain
    schema_version: string
    mappings: Api.Ingestion.MappingOverride[]
    expected_mapping_signature: string
  }
) {
  return request.post<Api.Ingestion.MappingTemplate>({
    url: `/api/v1/ingestion/data-sources/${dataSourceId}/mapping-templates`,
    params: data,
    showSuccessMessage: true
  })
}

export function fetchConfirmImport(
  dataSourceId: string,
  domain: Api.DataSource.Domain,
  file: File,
  preview: Api.Ingestion.Preview,
  mappings: Api.Ingestion.MappingOverride[]
) {
  const data = new FormData()
  data.append('data_source_id', dataSourceId)
  data.append('file', file)
  data.append('expected_checksum_sha256', preview.file_checksum_sha256)
  data.append('expected_mapping_signature', preview.mapping_signature)
  data.append('mappings_json', JSON.stringify(mappings))
  return request.post<Api.Ingestion.ImportResult>({
    url: ingestionPath(domain, 'import'),
    data,
    showSuccessMessage: true
  })
}
