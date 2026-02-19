import { useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, RefreshCw, XCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { useErrors, useErrorSummary, useRetryError, useIgnoreError } from '../hooks/useErrors'
import type { DiagnosticData, ErrorFilters } from '../api/errors'
import { addressUrl, txUrl } from '../api/explorer'

const PAGE_SIZE = 25

const ERROR_TYPE_COLORS: Record<string, string> = {
  TxParseError: 'bg-red-100 text-red-700',
  BalanceError: 'bg-orange-100 text-orange-700',
  UnknownTransactionInputError: 'bg-yellow-100 text-yellow-700',
}

export default function Errors() {
  const [filters, setFilters] = useState<ErrorFilters>({ limit: PAGE_SIZE, offset: 0 })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: summary } = useErrorSummary()
  const { data, isLoading, error } = useErrors(filters)
  const retryMutation = useRetryError()
  const ignoreMutation = useIgnoreError()

  const page = Math.floor((filters.offset ?? 0) / PAGE_SIZE)
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Errors & Warnings</h2>

      {/* Summary Bar */}
      {summary && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <SummaryPill
              label="Total"
              count={summary.total}
              color={summary.total > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}
            />
            <SummaryPill label="Unresolved" count={summary.unresolved} color="bg-yellow-100 text-yellow-700" />
            <SummaryPill label="Resolved" count={summary.resolved} color="bg-green-100 text-green-700" />
            <div className="ml-auto flex gap-2">
              {summary.by_type && Object.entries(summary.by_type).map(([type, count]) => (
                <button
                  key={type}
                  onClick={() => setFilters({ ...filters, error_type: filters.error_type === type ? undefined : type, offset: 0 })}
                  className={clsx(
                    'px-2 py-1 rounded-full text-xs font-medium border transition-colors',
                    filters.error_type === type
                      ? 'bg-blue-100 text-blue-700 border-blue-300'
                      : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100',
                  )}
                >
                  {type}: {count}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error List */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading errors...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Failed to load errors</div>
        ) : !data?.errors.length ? (
          <div className="p-8 text-center text-gray-400">
            {filters.error_type ? 'No errors of this type' : 'No errors — all clean!'}
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="w-8" />
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Message</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Created</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.errors.map((err) => {
                  const isExpanded = expandedId === err.id
                  return (
                    <ErrorRow
                      key={err.id}
                      err={err}
                      isExpanded={isExpanded}
                      onToggle={() => setExpandedId(isExpanded ? null : err.id)}
                      onRetry={() => retryMutation.mutate(err.id)}
                      onIgnore={() => ignoreMutation.mutate(err.id)}
                      retrying={retryMutation.isPending}
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

function SummaryPill({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className={clsx('px-3 py-1.5 rounded-lg text-sm font-medium', color)}>
      {label}: {count}
    </div>
  )
}

interface ErrorRowProps {
  err: {
    id: string
    tx_hash?: string | null
    chain?: string | null
    error_type: string
    message: string
    stack_trace: string | null
    resolved: boolean
    created_at: string
    diagnostic_data?: DiagnosticData | null
  }
  isExpanded: boolean
  onToggle: () => void
  onRetry: () => void
  onIgnore: () => void
  retrying: boolean
}

function ErrorRow({ err, isExpanded, onToggle, onRetry, onIgnore, retrying }: ErrorRowProps) {
  const diag = err.diagnostic_data
  return (
    <>
      <tr className="hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="px-2 py-3 text-center text-gray-400">
          <ChevronDown className={clsx('w-4 h-4 inline transition-transform', isExpanded && 'rotate-180')} />
        </td>
        <td className="px-4 py-3">
          <span className={clsx(
            'px-2 py-0.5 rounded-full text-xs font-medium',
            ERROR_TYPE_COLORS[err.error_type] ?? 'bg-gray-100 text-gray-600',
          )}>
            {err.error_type}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-700 text-sm truncate max-w-md">{err.message}</td>
        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
          {new Date(err.created_at).toLocaleString()}
        </td>
        <td className="px-4 py-3">
          <span className={clsx(
            'px-2 py-0.5 rounded-full text-xs font-medium',
            err.resolved ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700',
          )}>
            {err.resolved ? 'Resolved' : 'Open'}
          </span>
        </td>
        <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-center gap-1">
            {!err.resolved && (
              <>
                <button
                  onClick={onRetry}
                  disabled={retrying}
                  className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors"
                  title="Retry"
                >
                  <RefreshCw className={clsx('w-3.5 h-3.5', retrying && 'animate-spin')} />
                </button>
                <button
                  onClick={onIgnore}
                  className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition-colors"
                  title="Ignore"
                >
                  <XCircle className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={6} className="px-6 py-3 bg-gray-50">
            <div className="space-y-3">
              {/* TX + diagnostic info */}
              {(() => {
                const hash = err.tx_hash || diag?.tx_hash
                const errChain = err.chain || diag?.chain || 'ethereum'
                return (
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    {hash && (
                      <div>
                        <span className="font-medium text-gray-500">TX:</span>{' '}
                        <a
                          href={txUrl(errChain, hash)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline font-mono"
                        >
                          {hash.slice(0, 18)}...
                        </a>
                      </div>
                    )}
                    {diag?.contract_address && (
                      <div>
                        <span className="font-medium text-gray-500">To:</span>{' '}
                        <a
                          href={addressUrl(errChain, diag.contract_address)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline font-mono"
                        >
                          {diag.contract_address.slice(0, 18)}...
                        </a>
                      </div>
                    )}
                    {diag?.function_selector && (
                      <div>
                        <span className="font-medium text-gray-500">Selector:</span>{' '}
                        <code className="text-gray-700">{diag.function_selector}</code>
                      </div>
                    )}
                    <div>
                      <span className="font-medium text-gray-500">Chain:</span>{' '}
                      <span className="text-gray-700">{errChain}</span>
                    </div>
                  </div>
                )
              })()}

              {/* Transfers detected */}
              {diag?.detected_transfers && diag.detected_transfers.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 mb-1">Transfers Detected ({diag.detected_transfers.length})</h4>
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-2 py-1 text-left">Type</th>
                          <th className="px-2 py-1 text-left">Symbol</th>
                          <th className="px-2 py-1 text-left">From</th>
                          <th className="px-2 py-1 text-left">To</th>
                        </tr>
                      </thead>
                      <tbody>
                        {diag.detected_transfers.map((t, i) => (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="px-2 py-1">{t.type}</td>
                            <td className="px-2 py-1 font-medium">{t.symbol}</td>
                            <td className="px-2 py-1 font-mono text-gray-500">{t.from.slice(0, 10)}...</td>
                            <td className="px-2 py-1 font-mono text-gray-500">{t.to.slice(0, 10)}...</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Events detected */}
              {diag?.detected_events && diag.detected_events.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 mb-1">Events Detected ({diag.detected_events.length})</h4>
                  <div className="flex flex-wrap gap-1">
                    {diag.detected_events.map((e, i) => (
                      <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs">
                        {e.event}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Parsers attempted */}
              {diag?.parsers_attempted && diag.parsers_attempted.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 mb-1">Parsers Attempted</h4>
                  <div className="flex flex-wrap gap-1">
                    {diag.parsers_attempted.map((p, i) => {
                      const status = !p.matched
                        ? { label: 'skipped', cls: 'bg-gray-100 text-gray-500' }
                        : p.produced_splits
                          ? { label: 'OK', cls: 'bg-green-50 text-green-700' }
                          : { label: 'failed', cls: 'bg-red-50 text-red-600' }
                      return (
                        <span key={i} className={clsx('px-2 py-0.5 rounded text-xs', status.cls)}>
                          {p.parser}: {status.label}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Stack trace */}
              {err.stack_trace && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 mb-1">Stack Trace</h4>
                  <pre className="text-xs font-mono text-gray-600 whitespace-pre-wrap max-h-48 overflow-y-auto bg-white border border-gray-200 rounded-lg p-3">
                    {err.stack_trace}
                  </pre>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
