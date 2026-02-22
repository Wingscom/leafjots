import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts'
import type { CompositionItem } from '../../api/analytics'

interface Props {
  data: CompositionItem[]
  title?: string
}

const ACCOUNT_TYPE_COLORS: Record<string, string> = {
  ASSET: '#3b82f6',
  LIABILITY: '#ef4444',
  INCOME: '#22c55e',
  EXPENSE: '#f97316',
}

function formatUSD(value: number): string {
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

export function CompositionDonut({ data, title = 'Portfolio Composition' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  // Aggregate by account_type
  const aggregated: Record<string, number> = {}
  for (const item of data) {
    const abs = Math.abs(item.balance_usd)
    aggregated[item.account_type] = (aggregated[item.account_type] ?? 0) + abs
  }
  const chartData = Object.entries(aggregated).map(([name, value]) => ({ name, value }))

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={3}
            dataKey="value"
            nameKey="name"
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={ACCOUNT_TYPE_COLORS[entry.name] ?? '#94a3b8'}
              />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => formatUSD(value)} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
