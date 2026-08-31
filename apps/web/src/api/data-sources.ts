import request from '@/utils/http'

export function fetchDataSourceProviders() {
  return request.get<Api.DataSource.ProviderSpec[]>({ url: '/api/data-sources/providers' })
}

export function fetchDataSourceList(params: Api.DataSource.SearchParams) {
  return request.get<Api.DataSource.DataSourcePage>({ url: '/api/data-sources', params })
}

export function fetchCreateDataSource(data: Api.DataSource.DataSourceWrite) {
  return request.post<Api.DataSource.DataSourceItem>({ url: '/api/data-sources', params: data })
}

export function fetchUpdateDataSource(id: string, data: Api.DataSource.DataSourceWrite) {
  return request.put<Api.DataSource.DataSourceItem>({
    url: `/api/data-sources/${id}`,
    params: data
  })
}

export function fetchDisableDataSource(id: string) {
  return request.del<{ disabled: boolean }>({ url: `/api/data-sources/${id}` })
}

export function fetchTestDataSourceConnection(id: string) {
  return request.post<Api.DataSource.ConnectionTestResult>({
    url: `/api/data-sources/${id}/test-connection`
  })
}
