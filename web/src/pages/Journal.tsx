import { useState, useEffect } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, CheckCircle, XCircle } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { useJournalEntries, useJournalEntry } from '../hooks/useJournal'
import { useWallets } from '../hooks/useWallets'
import {
  FilterBar,
  DateRangePicker,
  WalletSelector,
  SymbolInput,
  EntryTypeSelector,
  AccountTypeSelector,
  ProtocolSelector,
} from '../components/filters'
import type { JournalFilters, JournalSplit } from '../api/journal'

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

function formatVnd(v: number | null): string {
  if (v === null || v === undefined) return '\u2014'
  return `VND ${Math.round(v).toLocaleString()}`
}

function isSplitsBalanced(splits: JournalSplit[]): boolean {
  // Splits are balanced when the sum of value_usd across all splits is approximately zero
  const total = splits.reduce((sum, s) => sum + (s.value_usd ?? 0), 0)
  return Math.abs(total) < 0.01
}

export default function Journal() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Read initial filter state from URL params
  const [dateFrom, setDateFrom] = useState<string | null>(searchParams.get('date_from'))
  const [dateTo, setDateTo] = useState<string | null>(searchParams.get('date_to'))
  const [walletId, setWalletId] = useState<string | null>(searchParams.get('wallet_id'))
  const [symbol, setSymbol] = useState<string>(searchParams.get('symbol') ?? '')
  const [entryType, setEntryType] = useState<string | null>(searchParams.get('entry_type'))
  const [accountType, setAccountType] = useState<string | null>(searchParams.get('account_type'))
  const [protocol, setProtocol] = useState<string | null>(searchParams.get('protocol'))
  const [offset, setOffset] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: walletData } = useWallets()
  const wallets = (walletData?.wallets ?? []).map((w) => ({
    id: w.id,
    label: w.label ?? w.address ?? w.id,
  }))

  // Sync filter state to URL params
  useEffect(() => {
    const params: Record<string, string> = {}
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (walletId) params.wallet_id = walletId
    if (symbol) params.symbol = symbol
    if (entryType) params.entry_type = entryType
    if (accountType) params.account_type = accountType
    if (protocol) params.protocol = protocol
    setSearchParams(params, { replace: true })
  }, [dateFrom, dateTo, walletId, symbol, entryType, accountType, protocol, setSearchParams])

  const filters: JournalFilters = {
    limit: PAGE_SIZE,
    offset,
    date_from: dateFrom ?? undefined,
    date_to: dateTo ?? undefined,
    wallet_id: walletId ?? undefined,
    symbol: symbol || undefined,
    entry_type: entryType ?? undefined,
    account_type: accountType ?? undefined,
    protocol: protocol ?? undefined,
  }

  const { data, isLoading, error } = useJournalEntries(filters)
  const { data: detail } = useJournalEntry(expandedId)

  const page = Math.floor(offset / PAGE_SIZE)
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  function handleReset() {
    setDateFrom(null)
    setDateTo(null)
    setWalletId(null)
    setSymbol('')
    setEntryType(null)
    setAccountType(null)
    setProtocol(null)
    setOffset(0)
    setSearchParams({}, { replace: true })
  }

  function updateFilter() {
    setOffset(0)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Journal Entries</h2>

      {/* Filters */}
      <div className="mb-6">
        <FilterBar onReset={handleReset}>
          <DateRangePicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateFromChange={(v) => { setDateFrom(v); updateFilter() }}
            onDateToChange={(v) => { setDateTo(v); updateFilter() }}
          />
          <WalletSelector
            value={walletId}
            onChange={(v) => { setWalletId(v); updateFilter() }}
            wallets={wallets}
          />
          <SymbolInput
            value={symbol}
            onChange={(v) => { setSymbol(v); updateFilter() }}
          />
          <EntryTypeSelector
            value={entryType}
            onChange={(v) => { setEntryType(v); updateFilter() }}
          />
          <AccountTypeSelector
            value={accountType}
            onChange={(v) => { setAccountType(v); updateFilter() }}
          />
          <ProtocolSelector
            value={protocol}
            onChange={(v) => { setProtocol(v); updateFilter() }}
          />
          {data && (
            <span className="text-sm text-gray-500 ml-auto self-center">
              {data.total.toLocaleString()} entr{data.total !== 1 ? 'ies' : 'y'}
            </span>
          )}
        </FilterBar>
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
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Balance</th>
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
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    disabled={page === 0}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" /> Prev
                  </button>
                  <button
                    onClick={() => setOffset(offset + PAGE_SIZE)}
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
  detail?: { splits: JournalSplit[] } | undefined
}

function EntryRow({ entry, isExpanded, onToggle, detail }: EntryRowProps) {
  const balanced = detail ? isSplitsBalanced(detail.splits) : null

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
        <td className="px-4 py-3 text-center">
          {balanced === null ? (
            <span className="text-gray-300 text-xs">—</span>
          ) : balanced ? (
            <CheckCircle className="w-4 h-4 text-green-500 inline" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500 inline" />
          )}
        </td>
      </tr>
      {isExpanded && detail && (
        <tr>
          <td colSpan={5} className="px-6 py-3 bg-gray-50">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500">
                  <th className="px-2 py-1 text-left font-medium">Account</th>
                  <th className="px-2 py-1 text-left font-medium">Type</th>
                  <th className="px-2 py-1 text-left font-medium">Symbol</th>
                  <th className="px-2 py-1 text-right font-medium">Quantity</th>
                  <th className="px-2 py-1 text-right font-medium">USD</th>
                  <th className="px-2 py-1 text-right font-medium">VND</th>
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
                    <td className="px-2 py-1 text-right text-gray-400">
                      {s.value_usd !== null ? `$${s.value_usd}` : '\u2014'}
                    </td>
                    <td className="px-2 py-1 text-right text-gray-400">
                      {formatVnd(s.value_vnd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Balance check summary */}
            <div className={clsx(
              'mt-2 flex items-center gap-1.5 text-xs font-medium',
              isSplitsBalanced(detail.splits) ? 'text-green-600' : 'text-red-600',
            )}>
              {isSplitsBalanced(detail.splits) ? (
                <><CheckCircle className="w-3.5 h-3.5" /> Entry is balanced</>
              ) : (
                <><XCircle className="w-3.5 h-3.5" /> Entry is NOT balanced — splits do not sum to zero</>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
