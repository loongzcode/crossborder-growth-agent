/**
 * API 接口类型定义模块
 *
 * 提供所有后端接口的类型定义
 *
 * ## 主要功能
 *
 * - 通用类型（分页参数、响应结构等）
 * - 认证类型（登录、用户信息等）
 * - 系统管理类型（用户、角色等）
 * - 全局命名空间声明
 *
 * ## 使用场景
 *
 * - API 请求参数类型约束
 * - API 响应数据类型定义
 * - 接口文档类型同步
 *
 * ## 注意事项
 *
 * - 在 .vue 文件使用需要在 eslint.config.mjs 中配置 globals: { Api: 'readonly' }
 * - 使用全局命名空间，无需导入即可使用
 *
 * ## 使用方式
 *
 * ```typescript
 * const params: Api.Auth.LoginParams = { userName: 'admin', password: '123456' }
 * const response: Api.Auth.UserInfo = await fetchUserInfo()
 * ```
 *
 * @module types/api/api
 * @author Art Design Pro Team
 */

declare namespace Api {
  /** 通用类型 */
  namespace Common {
    /** 分页参数 */
    interface PaginationParams {
      /** 当前页码 */
      current: number
      /** 每页条数 */
      size: number
      /** 总条数 */
      total: number
    }

    /** 通用搜索参数 */
    type CommonSearchParams = Pick<PaginationParams, 'current' | 'size'>

    /** 分页响应基础结构 */
    interface PaginatedResponse<T = any> {
      records: T[]
      current: number
      size: number
      total: number
    }

    /** 启用状态 */
    type EnableStatus = '1' | '2'
  }

  /** 认证类型 */
  namespace Auth {
    /** 登录参数 */
    interface LoginParams {
      userName: string
      password: string
    }

    /** 登录响应 */
    interface LoginResponse {
      token: string
      refreshToken: string
    }

    /** 用户信息 */
    interface UserInfo {
      buttons: string[]
      roles: string[]
      userId: string
      userName: string
      email: string
      avatar?: string
    }
  }

  /** 系统管理类型 */
  namespace SystemManage {
    /** 用户列表 */
    type UserList = Api.Common.PaginatedResponse<UserListItem>

    /** 用户列表项 */
    interface UserListItem {
      id: string
      avatar: string
      status: string
      userName: string
      userGender: string
      nickName: string
      userPhone: string
      userEmail: string
      userRoles: string[]
      createBy: string
      createTime: string
      updateBy: string
      updateTime: string
    }

    /** 用户搜索参数 */
    type UserSearchParams = Partial<
      Pick<UserListItem, 'id' | 'userName' | 'userGender' | 'userPhone' | 'userEmail' | 'status'> &
        Api.Common.CommonSearchParams
    >

    /** 角色列表 */
    type RoleList = Api.Common.PaginatedResponse<RoleListItem>

    /** 角色列表项 */
    interface RoleListItem {
      roleId: string
      roleName: string
      roleCode: string
      description: string
      enabled: boolean
      createTime: string
      isSystem: boolean
    }

    /** 角色搜索参数 */
    type RoleSearchParams = Partial<
      Pick<RoleListItem, 'roleId' | 'roleName' | 'roleCode' | 'description' | 'enabled'> &
        Api.Common.CommonSearchParams & {
          startTime: string | null
          endTime: string | null
        }
    >

    interface UserWrite {
      userName: string
      nickName: string
      userEmail: string
      userPhone: string
      userGender: string
      avatar: string
      password?: string
      userRoles: string[]
      enabled: boolean
    }

    interface RoleWrite {
      roleName: string
      roleCode: string
      description: string
      enabled: boolean
    }

    interface RoleAccess {
      menuIds: string[]
      permissionIds: string[]
    }

    interface MenuWrite {
      parentId?: string | null
      name: string
      path: string
      component: string
      title: string
      icon: string
      sort: number
      enabled: boolean
      hidden: boolean
      hideTab: boolean
      keepAlive: boolean
      fixedTab: boolean
      fullPage: boolean
      link: string
      iframe: boolean
      activePath: string
    }

    interface PermissionWrite {
      title: string
      code: string
      sort: number
    }
  }

  namespace DataSource {
    type Provider = 'file_upload' | 'tiktok_ads' | 'tiktok_shop'
    type Domain =
      | 'advertising'
      | 'orders'
      | 'products'
      | 'costs'
      | 'inventory'
      | 'refunds'
      | 'reviews'
      | 'currency_rates'
      | 'creatives'
    type ConnectionStatus = 'untested' | 'connected' | 'failed'

    interface ProviderField {
      key: string
      label: string
      secret: boolean
      required: boolean
    }

    interface ProviderSpec {
      value: Provider
      label: string
      domains: Domain[]
      fields: ProviderField[]
    }

    interface DataSourceItem {
      id: string
      name: string
      provider: Provider
      domain: Domain
      configuration: Record<string, string | number | boolean>
      hasCredentials: boolean
      enabled: boolean
      connectionStatus: ConnectionStatus
      lastTestedAt: string | null
      lastErrorCode: string | null
      lastErrorMessage: string | null
      lastSyncStatus: string | null
      lastSyncAt: string | null
      createdAt: string
      updatedAt: string
    }

    type DataSourcePage = Api.Common.PaginatedResponse<DataSourceItem>

    interface SearchParams extends Api.Common.CommonSearchParams {
      name?: string
      provider?: Provider
      domain?: Domain
      connectionStatus?: ConnectionStatus
      enabled?: boolean
      sortBy?: 'createdAt' | 'name' | 'lastTestedAt'
      sortOrder?: 'asc' | 'desc'
    }

    interface DataSourceWrite {
      name: string
      provider: Provider
      domain: Domain
      configuration: Record<string, string | number | boolean>
      credentials?: {
        accessToken?: string
        appSecret?: string
      }
      enabled: boolean
    }

    interface ConnectionTestResult {
      status: ConnectionStatus
      provider: Provider
      message: string
      checkedAt: string
      upstreamRequestId: string | null
      metadata: Record<string, string | number | boolean>
    }
  }

  namespace Ingestion {
    type MappingStatus = 'automatic' | 'confirmed' | 'needs_review' | 'unmapped'

    interface ColumnMapping {
      source_column: string
      canonical_field: string | null
      status: MappingStatus
      confidence: number
    }

    interface QualityIssue {
      code: string
      severity: 'info' | 'warning' | 'error'
      message: string
      row_number: number | null
      column: string | null
      value: unknown
    }

    interface Preview {
      domain: Api.DataSource.Domain
      schema_version: string
      filename: string
      file_checksum_sha256: string
      header_row_number: number
      source_row_count: number
      accepted_row_count: number
      rejected_row_count: number
      mappings: ColumnMapping[]
      mapping_signature: string
      mapping_template_id: string | null
      mapping_template_version: number | null
      unknown_columns: string[]
      issues: QualityIssue[]
      records: Record<string, unknown>[]
      aggregate_metrics?: Record<string, string | number | null>
    }

    interface FieldCatalog {
      domain?: Api.DataSource.Domain
      schema_version?: string
      required_fields: string[]
      aliases: Record<string, string[]>
      example_mappings: ColumnMapping[]
    }

    interface MappingOverride {
      source_column: string
      canonical_field: string | null
    }

    interface MappingTemplate {
      id: string
      data_source_id: string
      domain: Api.DataSource.Domain
      name: string
      version: number
      schema_version: string
      mappings: MappingOverride[]
      mapping_signature: string
      active: boolean
      created_by: string | null
      created_at: string
    }

    interface MappingTemplatePage {
      records: MappingTemplate[]
      total: number
    }

    interface ImportResult {
      status: 'imported' | 'duplicate'
      domain: Api.DataSource.Domain
      sync_job_id: string
      raw_batch_id: string
      source_row_count: number
      imported_row_count: number
      rejected_row_count: number
      file_checksum_sha256: string
      lineage_path: string
    }
  }
}
