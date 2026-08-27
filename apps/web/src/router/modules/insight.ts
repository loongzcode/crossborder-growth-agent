import { AppRouteRecord } from '@/types/router'

export const insightRoutes: AppRouteRecord = {
  path: '/insights',
  name: 'Insights',
  component: '/index/index',
  meta: {
    title: 'menus.insights.title',
    icon: 'ri:lightbulb-flash-line',
    roles: ['R_SUPER', 'R_ADMIN']
  },
  children: [
    {
      path: 'customers',
      name: 'CustomerInsights',
      component: '/workspace/index',
      meta: { title: 'menus.insights.customers', keepAlive: true }
    },
    {
      path: 'creatives',
      name: 'CreativeInsights',
      component: '/workspace/index',
      meta: { title: 'menus.insights.creatives', keepAlive: true }
    }
  ]
}
