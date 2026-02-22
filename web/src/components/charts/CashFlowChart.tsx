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
}

function formatUSD(value: number): string {
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

export function CashFlowChart({ data, title = 'Cash Flow' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => formatUSD(value)} />
          <Legend />
          <Bar dataKey="inflow_usd" name="Inflow" fill="#22c55e" stackId="a" />
          <Bar dataKey="outflow_usd" name="Outflow" fill="#ef4444" stackId="b" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
