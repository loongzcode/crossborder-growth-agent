import { AppRouteRecord } from '@/types/router'

export const riskRoutes: AppRouteRecord = {
  path: '/risk',
  name: 'Risk',
  component: '/index/index',
  meta: { title: 'menus.risk.title', icon: 'ri:shield-check-line', roles: ['R_SUPER', 'R_ADMIN'] },
  children: [
    {
      path: 'compliance',
      name: 'ComplianceReview',
      component: '/workspace/index',
      meta: { title: 'menus.risk.compliance', keepAlive: true }
    }
  ]
}
