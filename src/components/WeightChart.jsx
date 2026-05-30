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
      <article className="rounded-xl border border-dashed border-fitloop-line bg-fitloop-panel p-4 shadow-xl shadow-black/20">
        <p className="text-sm font-medium text-slate-100">体重趋势</p>
        <p className="mt-3 text-sm leading-6 text-slate-300">{model.emptyMessage}</p>
      </article>
    )
  }

  return (
    <article className="rounded-xl border border-fitloop-line bg-fitloop-panel p-4 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-100">体重趋势</p>
          <p className="mt-1 text-xs text-slate-400">近 14 天有效记录</p>
        </div>
        <p className="text-xs text-fitloop-orange">{model.points.length} 条记录</p>
      </div>

      <div className="mt-4 h-56">
        <ResponsiveContainer height="100%" width="100%">
          <LineChart data={model.points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="rgba(215, 222, 240, 0.8)" vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="label"
              tick={{ fill: '#7f8aa3', fontSize: 12 }}
              tickLine={false}
            />
            <YAxis
              axisLine={false}
              domain={['dataMin - 1', 'dataMax + 1']}
              tick={{ fill: '#7f8aa3', fontSize: 12 }}
              tickFormatter={(value) => formatWeightDisplay(value)}
              tickLine={false}
              width={56}
            />
            <Tooltip
              contentStyle={{
                border: '1px solid rgba(215, 222, 240, 0.92)',
                borderRadius: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                color: '#182033',
                boxShadow: '0 16px 36px -24px rgba(157, 169, 206, 0.45)',
              }}
              formatter={renderTooltipValue}
              labelFormatter={renderTooltipLabel}
            />
            <Line
              dataKey="weight"
              dot={{ fill: '#6d5efc', r: 3, strokeWidth: 0 }}
              stroke="#6d5efc"
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
