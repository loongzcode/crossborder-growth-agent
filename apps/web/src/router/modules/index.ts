import { AppRouteRecord } from '@/types/router'
import { dashboardRoutes } from './dashboard'
import { dataRoutes } from './data'
import { advertisingRoutes } from './advertising'
import { productRoutes } from './product'
import { insightRoutes } from './insight'
import { profitSupplyRoutes } from './profitSupply'
import { riskRoutes } from './risk'
import { agentRoutes } from './agents'
import { systemRoutes } from './system'

/**
 * 导出所有模块化路由
 */
export const routeModules: AppRouteRecord[] = [
  dashboardRoutes,
  dataRoutes,
  advertisingRoutes,
  productRoutes,
  insightRoutes,
  profitSupplyRoutes,
  riskRoutes,
  agentRoutes,
  systemRoutes
]
