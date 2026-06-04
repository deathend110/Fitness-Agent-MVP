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
      <article className="rounded-[1.75rem] border border-dashed border-fitloop-line bg-fitloop-panel/90 p-5 shadow-sm shadow-black/20 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Trend</p>
        <p className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-slate-100">体重趋势</p>
        <p className="mt-3 text-sm leading-7 text-slate-300">{model.emptyMessage}</p>
      </article>
    )
  }

  return (
    <article className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/90 p-5 shadow-sm shadow-black/20 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Trend</p>
          <p className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-slate-100">体重趋势</p>
          <p className="mt-2 text-sm leading-7 text-slate-300">近 14 天有效记录</p>
        </div>
        <p className="rounded-2xl border border-fitloop-orange/30 bg-fitloop-orange/8 px-4 py-2 text-xs font-semibold text-fitloop-orange">
          {model.points.length} 条记录
        </p>
      </div>

      <div className="mt-5 h-64 rounded-[1.5rem] border border-fitloop-line bg-gradient-to-b from-white to-[#f4f7ff] p-3">
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
