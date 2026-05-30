const storageKeys = {
  profile: 'fitloop_profile',
  weeklyPlan: 'fitloop_weeklyPlan',
  dailyLog: 'fitloop_dailyLog',
  chatHistory: 'fitloop_chatHistory',
  storageVersion: 'fitloop_storageVersion',
}

const weekdayOrder = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]

function getDateOffsetString(offset) {
  const date = new Date()
  date.setDate(date.getDate() + offset)

  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')

  return `${year}-${month}-${day}`
}

function createEmptyDayPlan() {
  return {
    type: 'rest',
    exercises: [],
  }
}

function createEmptyWeeklyPlan() {
  return weekdayOrder.reduce((plan, dayKey) => {
    plan[dayKey] = createEmptyDayPlan()
    return plan
  }, {})
}

// 应用启动默认值保持为空白，确保首次进入页面时由用户自行填写真实情况。
const defaultProfile = {
  basic: {
    name: '',
    sex: '',
    age: null,
    height: null,
    weight: null,
    waist: null,
  },
  oneRM: {
    squat: null,
    bench: null,
    deadlift: null,
  },
  goal: '',
  targetWeight: null,
  notes: '',
}

const defaultWeeklyPlan = createEmptyWeeklyPlan()

const defaultDailyLog = {}

const defaultChatHistory = []

// demo fixture 只给测试和离线演示脚本使用，不再作为应用默认灌入页面。
const demoProfile = {
  basic: {
    name: '小林',
    sex: 'male',
    age: 23,
    height: 178,
    weight: 82.1,
    waist: 82,
  },
  oneRM: {
    squat: 120,
    bench: 90,
    deadlift: 150,
  },
  goal: '增肌减脂',
  targetWeight: 78,
  notes: '工作日容易睡眠不足，当前每周训练 3 次，希望先把恢复节奏稳定下来。',
}

const demoWeeklyPlan = {
  Monday: {
    type: '腿日',
    exercises: [
      {
        id: 'monday-squat',
        name: '深蹲',
        ref1RM: 'squat',
        pct: 0.75,
        kg: null,
        sets: 4,
        reps: 6,
        rpe: null,
        note: '主项',
      },
      {
        id: 'monday-rdl',
        name: '罗马尼亚硬拉',
        ref1RM: null,
        pct: null,
        kg: 80,
        sets: 3,
        reps: 10,
        rpe: null,
        note: '',
      },
    ],
  },
  Tuesday: createEmptyDayPlan(),
  Wednesday: {
    type: '推日',
    exercises: [
      {
        id: 'wednesday-bench',
        name: '卧推',
        ref1RM: 'bench',
        pct: 0.72,
        kg: null,
        sets: 4,
        reps: 6,
        rpe: null,
        note: '主项',
      },
    ],
  },
  Thursday: createEmptyDayPlan(),
  Friday: {
    type: '拉日',
    exercises: [
      {
        id: 'friday-deadlift',
        name: '硬拉',
        ref1RM: 'deadlift',
        pct: 0.7,
        kg: null,
        sets: 3,
        reps: 5,
        rpe: null,
        note: '主项',
      },
    ],
  },
  Saturday: createEmptyDayPlan(),
  Sunday: createEmptyDayPlan(),
}

const demoDailyLog = {
  [getDateOffsetString(-2)]: {
    weight: 82.4,
    kcal: 2280,
    protein: 168,
    trainingDone: false,
    trainingNotes: '休息日，但昨晚睡得比较少，恢复一般。',
    fatigue: 3,
    sleep: 6.5,
  },
  [getDateOffsetString(-1)]: {
    weight: 82.2,
    kcal: 2210,
    protein: 170,
    trainingDone: true,
    trainingNotes: '卧推最后一组速度下降，但整体完成度还可以。',
    fatigue: 3,
    sleep: 7.2,
  },
  [getDateOffsetString(0)]: {
    weight: 82.1,
    kcal: 2150,
    protein: 165,
    trainingDone: true,
    trainingNotes: '深蹲第三组没有按计划完成，膝盖有一点紧。',
    fatigue: 4,
    sleep: 6.8,
  },
}

const demoChatHistory = [
  { role: 'user', content: '最近训练后疲劳感有点高，需要调整计划吗？' },
  {
    role: 'assistant',
    content: '可以先从下肢主项强度和睡眠恢复一起看，后续我会结合训练计划给你建议。',
  },
]

export {
  defaultChatHistory,
  defaultDailyLog,
  defaultProfile,
  defaultWeeklyPlan,
  demoChatHistory,
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
  storageKeys,
}
