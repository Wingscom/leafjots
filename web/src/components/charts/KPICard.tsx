import type { ReactNode } from 'react'

interface ChangeIndicator {
  value: number
  label: string
}

interface Props {
  label: string
  value: string | number
  subtitle?: string
  icon?: ReactNode
  change?: ChangeIndicator
  color?: string
}

export function KPICard({ label, value, subtitle, icon, change, color = '#3b82f6' }: Props) {
  const isPositive = change ? change.value >= 0 : null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
        {icon && (
          <span className="text-gray-400" style={{ color }}>
            {icon}
          </span>
        )}
      </div>

      <div className="text-2xl font-bold text-gray-900">
        {typeof value === 'number' ? value.toLocaleString('en-US') : value}
      </div>

      {subtitle && (
        <div className="text-xs text-gray-400">{subtitle}</div>
      )}

      {change && (
        <div
          className={`text-xs font-medium flex items-center gap-1 ${
            isPositive ? 'text-green-600' : 'text-red-600'
          }`}
        >
          <span>{isPositive ? '+' : ''}{change.value.toFixed(1)}%</span>
          <span className="text-gray-400 font-normal">{change.label}</span>
        </div>
      )}
    </div>
  )
}
