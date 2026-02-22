import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { IncomeExpensePeriod } from '../../api/analytics'

interface Props {
  data: IncomeExpensePeriod[]
  title?: string
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

export function IncomeExpenseChart({ data, title = 'Income vs Expense' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  const hasUSD = data.some((d) => d.income_usd !== 0 || d.expense_usd !== 0)
  const chartData = data.map((d) => ({ ...d, label: formatPeriod(d.period) }))

  if (hasUSD) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => formatUSD(value)} labelFormatter={(l) => l} />
            <Legend />
            <Area
              type="monotone"
              dataKey="income_usd"
              name="Income"
              stroke="#22c55e"
              fill="url(#incomeGrad)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="expense_usd"
              name="Expense"
              stroke="#f97316"
              fill="url(#expenseGrad)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // No price data — fallback to entry count
  const hasCount = data.some((d) => d.income_count > 0 || d.expense_count > 0)
  if (!hasCount) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        {title}
        <span className="text-xs text-gray-400 font-normal ml-2">— no price data, showing entry count</span>
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip formatter={(value: number) => [`${value}`, 'Entries']} labelFormatter={(l) => l} />
          <Legend />
          <Bar dataKey="income_count" name="Income" fill="#22c55e" radius={[4, 4, 0, 0]} />
          <Bar dataKey="expense_count" name="Expense" fill="#f97316" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
