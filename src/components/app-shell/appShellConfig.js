export const appShellTabs = [
  {
    id: 'profile',
    label: '我的档案',
    summary: '维护基础资料、目标与三大项 1RM。',
    icon: 'profile',
  },
  {
    id: 'plan',
    label: '训练计划',
    summary: '查看并维护本周训练安排。',
    icon: 'plan',
  },
  {
    id: 'today',
    label: '今日日志',
    summary: '记录当天恢复、营养与训练完成情况。',
    icon: 'today',
  },
  {
    id: 'coach',
    label: 'AI 教练',
    summary: '结合上下文生成建议，并支持一键采纳。',
    icon: 'coach',
  },
]

export const appShellQuickActions = []

export function getActiveShellTab(activeTabId) {
  return appShellTabs.find((tab) => tab.id === activeTabId) ?? appShellTabs[0]
}

export function buildAppShellStatus() {
  return {
    saveStateLabel: '数据已保存',
    storageLabel: '本地存储',
    helperLabel: '侧栏状态会同步到当前浏览器',
  }
}
