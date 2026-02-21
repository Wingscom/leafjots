import { type ReactNode } from 'react'
import { clsx } from 'clsx'

export interface Column<T> {
  key: string
  header: string
  render?: (item: T) => ReactNode
  sortable?: boolean
  align?: 'left' | 'right' | 'center'
  width?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  sortKey?: string
  sortDir?: 'asc' | 'desc'
  onSort?: (key: string) => void
  emptyMessage?: string
  rowKey: (item: T) => string
  onRowClick?: (item: T) => void
}

function SortArrow({ active, dir }: { active: boolean; dir?: 'asc' | 'desc' }) {
  if (!active) {
    return <span className="ml-1 text-gray-300">&uarr;&darr;</span>
  }
  return (
    <span className="ml-1 text-blue-600">
      {dir === 'asc' ? '\u2191' : '\u2193'}
    </span>
  )
}

export default function DataTable<T>({
  columns,
  data,
  sortKey,
  sortDir,
  onSort,
  emptyMessage = 'No data available',
  rowKey,
  onRowClick,
}: DataTableProps<T>) {
  const alignClass = (align?: 'left' | 'right' | 'center') => {
    if (align === 'right') return 'text-right'
    if (align === 'center') return 'text-center'
    return 'text-left'
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  'px-4 py-3',
                  alignClass(col.align),
                  col.sortable && onSort && 'cursor-pointer select-none hover:text-gray-700'
                )}
                style={col.width ? { width: col.width } : undefined}
                onClick={col.sortable && onSort ? () => onSort(col.key) : undefined}
              >
                {col.header}
                {col.sortable && onSort && (
                  <SortArrow active={sortKey === col.key} dir={sortKey === col.key ? sortDir : undefined} />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-12 text-center text-gray-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item) => (
              <tr
                key={rowKey(item)}
                className={clsx(
                  'border-b border-gray-100 hover:bg-gray-50 transition-colors',
                  onRowClick && 'cursor-pointer'
                )}
                onClick={onRowClick ? () => onRowClick(item) : undefined}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx('px-4 py-3', alignClass(col.align))}
                  >
                    {col.render
                      ? col.render(item)
                      : String((item as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
