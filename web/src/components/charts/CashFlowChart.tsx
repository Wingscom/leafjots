import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { CashFlowPeriod } from '../../api/analytics'

interface Props {
  data: CashFlowPeriod[]
  title?: string
  onBarClick?: (period: string) => void
}

function formatUSD(value: number): string {
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

function formatPeriod(period: string): string {
  try {
    const d = new Date(period)
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  } catch {
    return period
  }
}

export function CashFlowChart({ data, title = 'Cash Flow', onBarClick }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  const hasUSD = data.some((d) => d.inflow_usd !== 0 || d.outflow_usd !== 0)
  const chartData = data.map((d) => ({ ...d, label: formatPeriod(d.period) }))

  if (hasUSD) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }} onClick={onBarClick ? (state) => { if (state?.activeLabel) onBarClick(state.activeLabel) } : undefined}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => formatUSD(value)} labelFormatter={(l) => l} />
            <Legend />
            <Bar dataKey="inflow_usd" name="Inflow (USD)" fill="#22c55e" stackId="a" />
            <Bar dataKey="outflow_usd" name="Outflow (USD)" fill="#ef4444" stackId="b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // No price data — fallback to entry count
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        {title}
        <span className="text-xs text-gray-400 font-normal ml-2">— no price data, showing entry count</span>
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }} onClick={onBarClick ? (state) => { if (state?.activeLabel) onBarClick(state.activeLabel) } : undefined}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip formatter={(value: number) => [`${value}`, 'Entries']} labelFormatter={(l) => l} />
          <Legend />
          <Bar dataKey="entry_count" name="Entries" fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
