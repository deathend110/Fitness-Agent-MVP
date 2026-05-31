export const appShellLayoutModes = {
  default: {
    mode: 'default',
    wrapperClassName:
      'flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-4 sm:p-5 lg:p-6',
    contentClassName:
      'fitloop-shell__content min-h-0 flex-1 overflow-y-auto overflow-x-hidden',
  },
  coach: {
    mode: 'coach',
    wrapperClassName:
      'flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-0',
    contentClassName: 'fitloop-shell__content min-h-0 flex-1 overflow-hidden',
  },
}

export function getAppShellLayout(activeTabId) {
  // AI 教练页把滚动和留白控制下沉给内部布局，其余页面继续沿用默认壳层。
  return activeTabId === 'coach'
    ? appShellLayoutModes.coach
    : appShellLayoutModes.default
}
