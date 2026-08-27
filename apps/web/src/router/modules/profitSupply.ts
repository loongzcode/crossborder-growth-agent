import { AppRouteRecord } from '@/types/router'

export const profitSupplyRoutes: AppRouteRecord = {
  path: '/profit-supply',
  name: 'ProfitSupply',
  component: '/index/index',
  meta: {
    title: 'menus.profitSupply.title',
    icon: 'ri:funds-box-line',
    roles: ['R_SUPER', 'R_ADMIN']
  },
  children: [
    {
      path: 'profit',
      name: 'ContributionProfit',
      component: '/workspace/index',
      meta: { title: 'menus.profitSupply.profit', keepAlive: true }
    },
    {
      path: 'inventory',
      name: 'InventoryRisk',
      component: '/workspace/index',
      meta: { title: 'menus.profitSupply.inventory', keepAlive: true }
    }
  ]
}
