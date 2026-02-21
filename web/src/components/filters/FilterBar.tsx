import { type ReactNode } from 'react'

interface FilterBarProps {
  children: ReactNode
  onReset?: () => void
}

export default function FilterBar({ children, onReset }: FilterBarProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex flex-wrap items-end gap-3">
        {children}
        {onReset && (
          <div className="flex items-end">
            <button
              onClick={onReset}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Reset
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
