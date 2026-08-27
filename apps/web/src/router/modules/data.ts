import { AppRouteRecord } from '@/types/router'

export const dataRoutes: AppRouteRecord = {
  path: '/data',
  name: 'DataCenter',
  component: '/index/index',
  meta: { title: 'menus.data.title', icon: 'ri:database-2-line', roles: ['R_SUPER', 'R_ADMIN'] },
  children: [
    {
      path: 'sources',
      name: 'DataSources',
      component: '/workspace/index',
      meta: { title: 'menus.data.sources', keepAlive: true }
    },
    {
      path: 'quality',
      name: 'DataQuality',
      component: '/workspace/index',
      meta: { title: 'menus.data.quality', keepAlive: true }
    }
  ]
}
