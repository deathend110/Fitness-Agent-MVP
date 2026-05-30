import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatWeightDisplay } from '../utils/calc.js'

function renderTooltipLabel(label) {
  return `日期：${label}`
}

function renderTooltipValue(value) {
  return [formatWeightDisplay(value), '体重']
}

function WeightChart({ model }) {
  if (!model.hasEnoughData) {
    return (
      <article className="rounded-md border border-dashed border-fitloop-line bg-fitloop-ink/30 p-4">
        <p className="text-sm font-medium text-white">体重趋势</p>
        <p className="mt-3 text-sm leading-6 text-slate-300">{model.emptyMessage}</p>
      </article>
    )
  }

  return (
    <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white">体重趋势</p>
          <p className="mt-1 text-xs text-slate-400">近 14 天有效记录</p>
        </div>
        <p className="text-xs text-fitloop-mint">{model.points.length} 条记录</p>
      </div>

      <div className="mt-4 h-56">
        <ResponsiveContainer height="100%" width="100%">
          <LineChart data={model.points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="label"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              tickLine={false}
            />
            <YAxis
              axisLine={false}
              domain={['dataMin - 1', 'dataMax + 1']}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              tickFormatter={(value) => formatWeightDisplay(value)}
              tickLine={false}
              width={56}
            />
            <Tooltip
              contentStyle={{
                border: '1px solid rgba(71, 85, 105, 0.8)',
                borderRadius: '8px',
                backgroundColor: 'rgba(15, 23, 42, 0.96)',
                color: '#e2e8f0',
              }}
              formatter={renderTooltipValue}
              labelFormatter={renderTooltipLabel}
            />
            <Line
              dataKey="weight"
              dot={{ fill: '#f97316', r: 3, strokeWidth: 0 }}
              stroke="#f97316"
              strokeWidth={2.5}
              type="monotone"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}

export default WeightChart
