import {
  ResponsiveContainer,
  AreaChart,
  Area,
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

export function IncomeExpenseChart({ data, title = 'Income vs Expense' }: Props) {
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
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
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
          <XAxis dataKey="period" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => formatUSD(value)} />
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
