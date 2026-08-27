import { AppRouteRecord } from '@/types/router'

export const advertisingRoutes: AppRouteRecord = {
  path: '/advertising',
  name: 'Advertising',
  component: '/index/index',
  meta: {
    title: 'menus.advertising.title',
    icon: 'ri:megaphone-line',
    roles: ['R_SUPER', 'R_ADMIN']
  },
  children: [
    {
      path: 'diagnosis',
      name: 'AdDiagnosis',
      component: '/workspace/index',
      meta: { title: 'menus.advertising.diagnosis', keepAlive: true }
    },
    {
      path: 'budget-simulation',
      name: 'BudgetSimulation',
      component: '/workspace/index',
      meta: { title: 'menus.advertising.budgetSimulation', keepAlive: true }
    }
  ]
}
