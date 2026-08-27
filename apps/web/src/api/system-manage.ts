import request from '@/utils/http'
import { AppRouteRecord } from '@/types/router'

// 获取用户列表
export function fetchGetUserList(params: Api.SystemManage.UserSearchParams) {
  return request.get<Api.SystemManage.UserList>({
    url: '/api/user/list',
    params
  })
}

export function fetchCreateUser(data: Api.SystemManage.UserWrite) {
  return request.post<Api.SystemManage.UserListItem>({ url: '/api/user', params: data })
}

export function fetchUpdateUser(id: string, data: Api.SystemManage.UserWrite) {
  return request.put<Api.SystemManage.UserListItem>({ url: `/api/user/${id}`, params: data })
}

export function fetchDisableUser(id: string) {
  return request.del<{ disabled: boolean }>({ url: `/api/user/${id}` })
}

// 获取角色列表
export function fetchGetRoleList(params: Api.SystemManage.RoleSearchParams) {
  return request.get<Api.SystemManage.RoleList>({
    url: '/api/role/list',
    params
  })
}

export function fetchCreateRole(data: Api.SystemManage.RoleWrite) {
  return request.post<Api.SystemManage.RoleListItem>({ url: '/api/role', params: data })
}

export function fetchUpdateRole(id: string, data: Api.SystemManage.RoleWrite) {
  return request.put<Api.SystemManage.RoleListItem>({ url: `/api/role/${id}`, params: data })
}

export function fetchDeleteRole(id: string) {
  return request.del<{ deleted: boolean }>({ url: `/api/role/${id}` })
}

export function fetchGetRoleAccess(id: string) {
  return request.get<Api.SystemManage.RoleAccess>({ url: `/api/role/${id}/permissions` })
}

export function fetchUpdateRoleAccess(id: string, data: Api.SystemManage.RoleAccess) {
  return request.put<Api.SystemManage.RoleAccess>({
    url: `/api/role/${id}/permissions`,
    params: data
  })
}

// 获取菜单列表
export function fetchGetMenuList() {
  return request.get<AppRouteRecord[]>({
    url: '/api/v3/system/menus/simple'
  })
}

export function fetchGetMenuAdminList() {
  return request.get<AppRouteRecord[]>({ url: '/api/menu/list' })
}

export function fetchCreateMenu(data: Api.SystemManage.MenuWrite) {
  return request.post<{ id: string }>({ url: '/api/menu', params: data })
}

export function fetchUpdateMenu(id: string, data: Api.SystemManage.MenuWrite) {
  return request.put<{ id: string }>({ url: `/api/menu/${id}`, params: data })
}

export function fetchDeleteMenu(id: string) {
  return request.del<{ deleted: boolean }>({ url: `/api/menu/${id}` })
}

export function fetchCreateMenuPermission(menuId: string, data: Api.SystemManage.PermissionWrite) {
  return request.post<{ id: string }>({
    url: `/api/menu/${menuId}/permissions`,
    params: data
  })
}

export function fetchUpdateMenuPermission(id: string, data: Api.SystemManage.PermissionWrite) {
  return request.put<{ id: string }>({
    url: `/api/menu/permissions/${id}`,
    params: data
  })
}

export function fetchDeleteMenuPermission(id: string) {
  return request.del<{ deleted: boolean }>({ url: `/api/menu/permissions/${id}` })
}
