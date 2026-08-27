import { AppRouteRecord } from '@/types/router'

export const agentRoutes: AppRouteRecord = {
  path: '/agents',
  name: 'Agents',
  component: '/index/index',
  meta: { title: 'menus.agents.title', icon: 'ri:robot-2-line', roles: ['R_SUPER', 'R_ADMIN'] },
  children: [
    {
      path: 'runs',
      name: 'AgentRuns',
      component: '/workspace/index',
      meta: { title: 'menus.agents.runs', keepAlive: true }
    },
    {
      path: 'approvals',
      name: 'ApprovalCenter',
      component: '/workspace/index',
      meta: { title: 'menus.agents.approvals', keepAlive: true }
    },
    {
      path: 'evaluations',
      name: 'EvaluationCenter',
      component: '/workspace/index',
      meta: { title: 'menus.agents.evaluations', keepAlive: true }
    }
  ]
}
