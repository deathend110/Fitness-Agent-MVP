import { buildDailyMetricsSummary } from './dailyMetrics.js'

function formatMetricValue(value, unit = '', fractionDigits = 1) {
  if (!Number.isFinite(value)) {
    return '未记录'
  }

  return `${Number(value.toFixed(fractionDigits))}${unit}`
}

function getPlanTypeLabel(planType) {
  if (planType === 'rest') {
    return '休息日'
  }

  if (!planType) {
    return '未设置'
  }

  return planType
}

function getTrainingTag(isTrainingDay) {
  return isTrainingDay ? '训练日' : '休息日'
}

function getCalorieStatusCopy(status) {
  if (status === 'deficit') {
    return { value: '热量缺口', tone: 'warning' }
  }

  if (status === 'surplus') {
    return { value: '热量盈余', tone: 'accent' }
  }

  if (status === 'balanced') {
    return { value: '热量基本持平', tone: 'success' }
  }

  return { value: '热量未知', tone: 'neutral' }
}

function getProteinStatusCopy(status) {
  if (status === 'met') {
    return { value: '已达到建议下限', tone: 'success' }
  }

  if (status === 'low') {
    return { value: '低于建议下限', tone: 'warning' }
  }

  return { value: '蛋白质未知', tone: 'neutral' }
}

export function getMetricToneClassNames(tone) {
  if (tone === 'success') {
    return {
      cardClassName: 'border-emerald-400/30 bg-emerald-500/10',
      labelClassName: 'text-emerald-200/80',
      valueClassName: 'text-emerald-100',
    }
  }

  if (tone === 'warning') {
    return {
      cardClassName: 'border-amber-400/30 bg-amber-500/10',
      labelClassName: 'text-amber-100/80',
      valueClassName: 'text-amber-50',
    }
  }

  if (tone === 'accent') {
    return {
      cardClassName: 'border-fitloop-orange/40 bg-fitloop-orange/10',
      labelClassName: 'text-fitloop-orange/80',
      valueClassName: 'text-fitloop-orange',
    }
  }

  return {
    cardClassName: 'border-fitloop-line bg-fitloop-ink/20',
    labelClassName: 'text-slate-400',
    valueClassName: 'text-slate-100',
  }
}

/**
 * 将复杂指标 summary 转成 Today 页可直接消费的展示模型。
 * 这里统一复用 buildDailyMetricsSummary，避免页面自行重复计算。
 */
export function buildDailyMetricsPanelModel(
  profile = {},
  weeklyPlan = {},
  dailyLog = {},
  referenceDate,
) {
  const summary = buildDailyMetricsSummary(profile, weeklyPlan, dailyLog, referenceDate)
  const calorieStatus = getCalorieStatusCopy(summary.calorie.status)
  const proteinStatus = getProteinStatusCopy(summary.protein.status)

  return {
    header: {
      date: summary.todayStr,
      trainingTag: getTrainingTag(summary.isTrainingDay),
      planTypeLabel: getPlanTypeLabel(summary.todayPlan?.type),
    },
    metrics: {
      bmr: {
        label: 'BMR',
        value: formatMetricValue(summary.bmr, ' kcal', 0),
      },
      trainingKcal: {
        label: '训练消耗',
        value: formatMetricValue(summary.trainingKcal, ' kcal', 0),
      },
      steps: {
        label: '步数',
        value: formatMetricValue(summary.steps, ' 步', 0),
      },
      tdee: {
        label: summary.tdeeSource === 'manual' ? 'TDEE（手填）' : 'TDEE（估算）',
        value: formatMetricValue(summary.tdee, ' kcal', 0),
      },
      bmi: {
        label: 'BMI',
        value: formatMetricValue(summary.bmi, '', 1),
      },
      calorie: {
        label: '热量摄入',
        value: formatMetricValue(summary.calorie.intake, ' kcal', 0),
      },
      calorieStatus: {
        label: '热量状态',
        value: calorieStatus.value,
        tone: calorieStatus.tone,
      },
      protein: {
        label: '蛋白质',
        value:
          summary.protein.intake === null || summary.protein.gramsPerKg === null
            ? '未记录'
            : `${formatMetricValue(summary.protein.intake, ' g', 0)} / ${formatMetricValue(summary.protein.gramsPerKg, ' g/kg', 1)}`,
      },
      proteinStatus: {
        label: '蛋白质状态',
        value: proteinStatus.value,
        tone: proteinStatus.tone,
      },
      recovery: {
        label: '恢复数据',
        value: `睡眠 ${formatMetricValue(summary.recovery.sleepHours, ' h', 1)} / 疲劳 ${formatMetricValue(summary.recovery.fatigueLevel, ' / 5', 0)}`,
      },
    },
    aiEntry: {
      title: '去 AI 教练获取辅助判断',
      description: '基于同一份本地复杂指标与 prompt 注入口径，继续查看 AI 的训练与恢复判断。',
      ctaLabel: '查看 AI 教练',
    },
    source: {
      summary,
    },
  }
}
