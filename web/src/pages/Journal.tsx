import { useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from 'lucide-react'
import { clsx } from 'clsx'
import { useJournalEntries, useJournalEntry } from '../hooks/useJournal'
import type { JournalFilters } from '../api/journal'

const ENTRY_TYPES = ['', 'SWAP', 'TRANSFER', 'GAS_FEE', 'UNKNOWN']
const PAGE_SIZE = 25

const TYPE_COLORS: Record<string, string> = {
  ASSET: 'text-blue-700 bg-blue-50',
  LIABILITY: 'text-red-700 bg-red-50',
  INCOME: 'text-green-700 bg-green-50',
  EXPENSE: 'text-orange-700 bg-orange-50',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

export default function Journal() {
  const [filters, setFilters] = useState<JournalFilters>({ limit: PAGE_SIZE, offset: 0 })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data, isLoading, error } = useJournalEntries(filters)
  const { data: detail } = useJournalEntry(expandedId)

  const page = Math.floor((filters.offset ?? 0) / PAGE_SIZE)
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Journal Entries</h2>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Entry Type</label>
          <select
            value={filters.entry_type ?? ''}
            onChange={(e) => setFilters({ ...filters, entry_type: e.target.value || undefined, offset: 0 })}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {ENTRY_TYPES.map((t) => (
              <option key={t} value={t}>{t || 'All types'}</option>
            ))}
          </select>
        </div>
        {data && (
          <span className="text-sm text-gray-500 ml-auto">
            {data.total.toLocaleString()} entr{data.total !== 1 ? 'ies' : 'y'}
          </span>
        )}
      </div>

      {/* Journal Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading journal entries...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Failed to load journal</div>
        ) : !data?.entries.length ? (
          <div className="p-8 text-center text-gray-400">
            No journal entries yet. Parse transactions to create journal entries.
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="w-8" />
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Timestamp</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.entries.map((entry) => {
                  const isExpanded = expandedId === entry.id
                  return (
                    <EntryRow
                      key={entry.id}
                      entry={entry}
                      isExpanded={isExpanded}
                      onToggle={() => setExpandedId(isExpanded ? null : entry.id)}
                      detail={isExpanded ? detail : undefined}
                    />
                  )
                })}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
                <span className="text-sm text-gray-500">Page {page + 1} of {totalPages}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setFilters({ ...filters, offset: Math.max(0, (filters.offset ?? 0) - PAGE_SIZE) })}
                    disabled={page === 0}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" /> Prev
                  </button>
                  <button
                    onClick={() => setFilters({ ...filters, offset: (filters.offset ?? 0) + PAGE_SIZE })}
                    disabled={page >= totalPages - 1}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                  >
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

interface EntryRowProps {
  entry: { id: string; timestamp: string; entry_type: string; description: string }
  isExpanded: boolean
  onToggle: () => void
  detail?: { splits: Array<{ id: string; account_label: string; account_type: string; symbol: string; quantity: number; value_usd: number | null }> } | undefined
}

function EntryRow({ entry, isExpanded, onToggle, detail }: EntryRowProps) {
  return (
    <>
      <tr className="hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="px-2 py-3 text-center text-gray-400">
          {isExpanded ? <ChevronUp className="w-4 h-4 inline" /> : <ChevronDown className="w-4 h-4 inline" />}
        </td>
        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{formatDate(entry.timestamp)}</td>
        <td className="px-4 py-3">
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
            {entry.entry_type}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-700 text-sm">{entry.description}</td>
      </tr>
      {isExpanded && detail && (
        <tr>
          <td colSpan={4} className="px-6 py-3 bg-gray-50">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500">
                  <th className="px-2 py-1 text-left font-medium">Account</th>
                  <th className="px-2 py-1 text-left font-medium">Type</th>
                  <th className="px-2 py-1 text-left font-medium">Symbol</th>
                  <th className="px-2 py-1 text-right font-medium">Quantity</th>
                  <th className="px-2 py-1 text-right font-medium">USD</th>
                </tr>
              </thead>
              <tbody>
                {detail.splits.map((s) => (
                  <tr key={s.id}>
                    <td className="px-2 py-1 font-mono text-gray-600 max-w-xs truncate">{s.account_label}</td>
                    <td className="px-2 py-1">
                      <span className={clsx('px-1.5 py-0.5 rounded text-xs', TYPE_COLORS[s.account_type] ?? 'bg-gray-100 text-gray-600')}>
                        {s.account_type}
                      </span>
                    </td>
                    <td className="px-2 py-1 font-medium">{s.symbol}</td>
                    <td className={clsx(
                      'px-2 py-1 text-right font-mono',
                      s.quantity > 0 ? 'text-green-600' : s.quantity < 0 ? 'text-red-600' : 'text-gray-500',
                    )}>
                      {s.quantity > 0 ? '+' : ''}{s.quantity}
                    </td>
                    <td className="px-2 py-1 text-right text-gray-400">{s.value_usd ?? '\u2014'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  )
}
