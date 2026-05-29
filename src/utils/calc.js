const WEEKDAY_KEYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
]

function toNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function getRestPlan() {
  return { type: 'rest', exercises: [] }
}

// 返回与 weeklyPlan 对齐的英文星期键，避免多个页面各自维护映射。
export function getTodayKey() {
  return WEEKDAY_KEYS[new Date().getDay()]
}

// 使用本地时区拼接 YYYY-MM-DD，避免 ISO 字符串跨时区偏移到前一天。
export function getTodayStr() {
  const now = new Date()
  const year = now.getFullYear()
  const month = `${now.getMonth() + 1}`.padStart(2, '0')
  const day = `${now.getDate()}`.padStart(2, '0')

  return `${year}-${month}-${day}`
}

// 统一解析动作实际重量，兼容 ref1RM 百分比模式和固定 kg 模式。
export function getExerciseKg(exercise = {}, oneRM = {}) {
  if (exercise.ref1RM) {
    const baseKg = toNumber(oneRM?.[exercise.ref1RM])
    const pct = toNumber(exercise.pct)
    return Math.round(baseKg * pct)
  }

  return toNumber(exercise.kg)
}

// 按 spec 中的 Mifflin-St Jeor 公式估算基础代谢。
export function calcBMR(profileBasic = {}) {
  const weight = toNumber(profileBasic.weight)
  const height = toNumber(profileBasic.height)
  const age = toNumber(profileBasic.age)
  const offset = profileBasic.sex === 'female' ? -161 : 5

  return Math.round(10 * weight + 6.25 * height - 5 * age + offset)
}

// 训练消耗按 kg * sets * reps * 0.1 估算，空计划或休息日调用时自然返回 0。
export function calcTrainingKcal(exercises = [], oneRM = {}) {
  const totalVolume = exercises.reduce((sum, exercise) => {
    const kg = getExerciseKg(exercise, oneRM)
    const sets = toNumber(exercise.sets)
    const reps = toNumber(exercise.reps)

    return sum + kg * sets * reps
  }, 0)

  return Math.round(totalVolume * 0.1)
}

// 汇总今天的训练与热量上下文，供页面或后续 prompt 构建按需解构。
export function calcTDEE(profile = {}, weeklyPlan = {}, dailyLog = {}) {
  const todayKey = getTodayKey()
  const todayStr = getTodayStr()
  const todayPlan = weeklyPlan?.[todayKey] ?? getRestPlan()
  const isTrainingDay = todayPlan.type !== 'rest'
  const bmr = calcBMR(profile.basic)
  const trainingKcal = isTrainingDay
    ? calcTrainingKcal(todayPlan.exercises, profile.oneRM)
    : 0
  const tdee = Math.round(bmr * 1.2 + trainingKcal)
  const todayKcal = toNumber(dailyLog?.[todayStr]?.kcal)

  return {
    todayKey,
    todayStr,
    todayPlan,
    isTrainingDay,
    bmr,
    trainingKcal,
    tdee,
    todayKcal,
    delta: todayKcal - tdee,
  }
}
