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
import type { IncomeExpensePeriod } from '../../api/analytics'

interface Props {
  data: IncomeExpensePeriod[]
  title?: string
}

function formatPeriod(period: string): string {
  try {
    const d = new Date(period)
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  } catch {
    return period
  }
}

export function IncomeExpenseCountChart({ data, title = 'Income & Expense Activity' }: Props) {
  if (!data || data.length === 0) return null

  const hasCount = data.some((d) => d.income_count > 0 || d.expense_count > 0)
  if (!hasCount) return null

  const chartData = data.map((d) => ({ ...d, label: formatPeriod(d.period) }))

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        {title} <span className="text-xs text-gray-400 font-normal">(entry count)</span>
      </h3>
      <ResponsiveContainer width="100%" height={200}>
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
