function formatMetricValue(value, unit) {
  if (value === null || value === undefined || value === '') {
    return '未填写'
  }

  return `${value} ${unit}`.trim()
}

export function buildProfileSummaryCards(profile = {}) {
  return [
    {
      key: 'weight',
      label: '当前体重',
      value: formatMetricValue(profile.basic?.weight, 'kg'),
      hint: '当前记录',
    },
    {
      key: 'targetWeight',
      label: '目标体重',
      value: formatMetricValue(profile.targetWeight, 'kg'),
      hint: '目标值',
    },
    {
      key: 'waist',
      label: '腰围',
      value: formatMetricValue(profile.basic?.waist, 'cm'),
      hint: '围度记录',
    },
    {
      key: 'goal',
      label: '训练目标',
      value: profile.goal?.trim() ? profile.goal.trim() : '未填写',
      hint: '当前方向',
    },
  ]
}

export function getProfileFieldHint(fieldKey) {
  switch (fieldKey) {
    case 'height':
      return '单位 cm'
    case 'weight':
      return '单位 kg'
    case 'waist':
      return '单位 cm'
    case 'targetWeight':
      return '目标体重，单位 kg'
    case 'goal':
      return '例如减脂、增肌或力量提升'
    case 'notes':
      return '记录补充信息，例如伤病或训练限制'
    default:
      return ''
  }
}
