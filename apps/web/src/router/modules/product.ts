import { AppRouteRecord } from '@/types/router'

export const productRoutes: AppRouteRecord = {
  path: '/products',
  name: 'Products',
  component: '/index/index',
  meta: {
    title: 'menus.products.title',
    icon: 'ri:shopping-bag-3-line',
    roles: ['R_SUPER', 'R_ADMIN']
  },
  children: [
    {
      path: 'candidates',
      name: 'ProductCandidates',
      component: '/workspace/index',
      meta: { title: 'menus.products.candidates', keepAlive: true }
    },
    {
      path: 'backtests',
      name: 'ProductBacktests',
      component: '/workspace/index',
      meta: { title: 'menus.products.backtests', keepAlive: true }
    }
  ]
}
