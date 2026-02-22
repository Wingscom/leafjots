import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { BalancePeriod } from '../../api/analytics'

interface Props {
  data: BalancePeriod[]
  title?: string
}

const LINE_COLORS = [
  '#3b82f6',
  '#22c55e',
  '#f97316',
  '#a855f7',
  '#06b6d4',
  '#ec4899',
  '#eab308',
  '#64748b',
]

function formatUSD(value: number): string {
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

export function BalanceOverTimeChart({ data, title = 'Balance Over Time' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  // Group by symbol, build map of period -> { symbol: value }
  const symbols = Array.from(new Set(data.map((d) => d.symbol)))
  const periodMap: Record<string, Record<string, number>> = {}
  for (const item of data) {
    if (!periodMap[item.period]) periodMap[item.period] = {}
    periodMap[item.period][item.symbol] = item.period_value_usd
  }
  const chartData = Object.entries(periodMap).map(([period, values]) => ({ period, ...values }))

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => formatUSD(value)} />
          <Legend />
          {symbols.map((symbol, i) => (
            <Line
              key={symbol}
              type="monotone"
              dataKey={symbol}
              stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
