import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'
import type { EntryTypeBreakdown } from '../../api/analytics'

interface Props {
  data: EntryTypeBreakdown[]
  metric?: 'count' | 'volume_usd'
  title?: string
}

const BAR_COLORS = [
  '#3b82f6',
  '#22c55e',
  '#f97316',
  '#a855f7',
  '#06b6d4',
  '#ec4899',
  '#eab308',
  '#ef4444',
]

export function EntryTypeBar({ data, metric = 'count', title = 'Entry Types' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  const dataKey = metric
  const formatter =
    metric === 'volume_usd'
      ? (v: number) => `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
      : (v: number) => v.toLocaleString('en-US')

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={formatter} />
          <YAxis type="category" dataKey="entry_type" tick={{ fontSize: 11 }} width={75} />
          <Tooltip formatter={formatter} />
          <Bar dataKey={dataKey} name={metric === 'count' ? 'Count' : 'Volume (USD)'} radius={[0, 4, 4, 0]}>
            {data.map((_, index) => (
              <Cell key={index} fill={BAR_COLORS[index % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
