import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('TodayTab 源码包含记录优先工作台结构与分组录入区', () => {
  const source = readFileSync('src/tabs/TodayTab.jsx', 'utf8')

  assert.match(source, /buildTodayLogFieldGroups/)
  assert.match(source, /buildTodayLogSummaryItems/)
  assert.match(source, /fieldGroups\.map/)
  assert.match(source, /summaryItems\.map/)
  assert.match(source, /今天的数据录入/)
  assert.match(source, /今天已完成训练/)
  assert.match(source, /已保存摘要/)
  assert.match(source, /今日计划/)
  assert.match(source, /<DailyMetricsPanel/)
  assert.match(source, /<WeightChart/)
})

test('TodayTab 会读取 effectiveWeeklyPlan 而不是 manual weeklyPlan', () => {
  const source = readFileSync('src/tabs/TodayTab.jsx', 'utf8')

  assert.match(source, /function TodayTab\(\{ dailyLog, effectiveWeeklyPlan, profile, onDailyLogChange, onOpenCoach \}\)/)
  assert.match(source, /const todayPlan = effectiveWeeklyPlan\?\.\[todayPlanKey\]/)
  assert.match(source, /buildDailyMetricsPanelModel\(profile, effectiveWeeklyPlan, dailyLog\)/)
  assert.doesNotMatch(source, /function TodayTab\(\{ dailyLog, weeklyPlan, profile, onDailyLogChange, onOpenCoach \}\)/)
})
