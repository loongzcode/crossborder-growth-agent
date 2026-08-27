import type { FastEnterConfig } from '@/types/config'

const fastEnterConfig: FastEnterConfig = {
  minWidth: 1200,
  applications: [
    {
      name: '经营总览',
      description: '全局经营健康度与每日简报',
      icon: 'ri:dashboard-3-line',
      iconColor: '#377dff',
      enabled: true,
      order: 1,
      routeName: 'Console'
    },
    {
      name: '广告诊断',
      description: '投产异常、归因与预算模拟',
      icon: 'ri:line-chart-line',
      iconColor: '#ff3b30',
      enabled: true,
      order: 2,
      routeName: 'AdDiagnosis'
    },
    {
      name: '智能选品',
      description: '候选评分、回测与冷启动计划',
      icon: 'ri:shopping-bag-3-line',
      iconColor: '#7a7fff',
      enabled: true,
      order: 3,
      routeName: 'ProductCandidates'
    },
    {
      name: 'Agent 运行',
      description: '工作流、节点证据与失败重试',
      icon: 'ri:robot-2-line',
      iconColor: '#13deb9',
      enabled: true,
      order: 4,
      routeName: 'AgentRuns'
    }
  ],
  quickLinks: [
    { name: '登录', enabled: true, order: 1, routeName: 'Login' },
    { name: '个人中心', enabled: true, order: 2, routeName: 'UserCenter' }
  ]
}

export default Object.freeze(fastEnterConfig)
