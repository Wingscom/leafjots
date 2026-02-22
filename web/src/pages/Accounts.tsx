import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight, X, DollarSign, TrendingDown, TrendingUp, Receipt } from 'lucide-react'
import { clsx } from 'clsx'
import { useAccounts, useAccountHistory } from '../hooks/useAccounts'
import { useWallets } from '../hooks/useWallets'
import {
  FilterBar,
  WalletSelector,
  SymbolInput,
  ProtocolSelector,
  AccountTypeSelector,
} from '../components/filters'
import type { Account, AccountHistorySplit } from '../api/accounts'

/* ─── Style config per account type ─── */
const TYPE_STYLES: Record<string, { color: string; bg: string; border: string; label: string; icon: typeof DollarSign }> = {
  ASSET: { color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Assets', icon: DollarSign },
  LIABILITY: { color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', label: 'Liabilities', icon: TrendingDown },
  INCOME: { color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', label: 'Income', icon: TrendingUp },
  EXPENSE: { color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200', label: 'Expenses', icon: Receipt },
}

const TYPE_ORDER = ['ASSET', 'LIABILITY', 'INCOME', 'EXPENSE'] as const

/* ─── Number formatting helpers ─── */

/** Format quantity with up to 6 meaningful decimal places, with commas */
function fmtQty(val: number | undefined | null): string {
  if (val == null) return '-'
  // Remove trailing zeros but keep up to 6 decimals
  const formatted = Number(val).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  })
  return formatted
}

/** Format USD value */
function fmtUsd(val: number | undefined | null): string {
  if (val == null || val === 0) return '-'
  return Number(val).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** Format VND value */
function fmtVnd(val: number | undefined | null): string {
  if (val == null || val === 0) return '-'
  return Number(val).toLocaleString('vi-VN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }) + '\u20AB'
}

/* ─── Helpers ─── */

function groupByType(accounts: Account[]): Record<string, Account[]> {
  const groups: Record<string, Account[]> = {}
  for (const acc of accounts) {
    const key = acc.account_type
    if (!groups[key]) groups[key] = []
    groups[key].push(acc)
  }
  return groups
}

function shortLabel(label: string): string {
  const parts = label.split(':')
  return parts.length > 2 ? parts.slice(2).join(':') : label
}

/** Get the balance quantity — handle both field names from backend */
function getBalance(acc: Account): number {
  return acc.current_balance ?? acc.balance ?? 0
}

/* ─── Summary Card ─── */

function SummaryCard({
  title,
  value,
  colorClass,
  icon: Icon,
}: {
  title: string
  value: number
  colorClass: string
  icon: typeof DollarSign
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-start gap-3">
      <div className={clsx('rounded-lg p-2', colorClass.replace('text-', 'bg-').replace('700', '100'))}>
        <Icon className={clsx('w-5 h-5', colorClass)} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 font-medium">{title}</p>
        <p className={clsx('text-lg font-bold mt-0.5 truncate', colorClass)}>
          {fmtUsd(value)}
        </p>
      </div>
    </div>
  )
}

/* ─── Main Component ─── */

export default function Accounts() {
  const { data, isLoading, error } = useAccounts()
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['ASSET']))
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null)

  // Filter state
  const [walletId, setWalletId] = useState<string | null>(null)
  const [symbol, setSymbol] = useState<string>('')
  const [protocol, setProtocol] = useState<string | null>(null)
  const [accountType, setAccountType] = useState<string | null>(null)
  const [balanceAtDate, setBalanceAtDate] = useState<string>('')

  const { data: walletData } = useWallets()
  const wallets = (walletData?.wallets ?? []).map((w) => ({
    id: w.id,
    label: w.label ?? w.address ?? w.id,
  }))

  // Apply client-side filters
  const allAccounts = data?.accounts ?? []
  const filteredAccounts = allAccounts.filter((acc) => {
    if (walletId && acc.wallet_id !== walletId) return false
    if (symbol && !acc.symbol?.toUpperCase().includes(symbol.toUpperCase())) return false
    if (protocol && acc.protocol !== protocol) return false
    if (accountType && acc.account_type !== accountType) return false
    return true
  })

  const grouped = groupByType(filteredAccounts)

  // Compute summary totals per type
  const summaryTotals = useMemo(() => {
    const totals: Record<string, number> = { ASSET: 0, LIABILITY: 0, INCOME: 0, EXPENSE: 0 }
    for (const acc of filteredAccounts) {
      const type = acc.account_type
      if (type in totals) {
        totals[type] += Number(acc.balance_usd ?? 0)
      }
    }
    return totals
  }, [filteredAccounts])

  function toggleType(type: string) {
    setExpandedTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }

  function handleReset() {
    setWalletId(null)
    setSymbol('')
    setProtocol(null)
    setAccountType(null)
    setBalanceAtDate('')
  }

  return (
    <div>
      {/* Header */}
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Balance Sheet</h2>

      {/* Summary Cards */}
      {!isLoading && !error && filteredAccounts.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <SummaryCard
            title="Total Assets"
            value={summaryTotals.ASSET}
            colorClass="text-blue-700"
            icon={DollarSign}
          />
          <SummaryCard
            title="Total Liabilities"
            value={summaryTotals.LIABILITY}
            colorClass="text-red-700"
            icon={TrendingDown}
          />
          <SummaryCard
            title="Total Income"
            value={summaryTotals.INCOME}
            colorClass="text-green-700"
            icon={TrendingUp}
          />
          <SummaryCard
            title="Total Expenses"
            value={summaryTotals.EXPENSE}
            colorClass="text-orange-700"
            icon={Receipt}
          />
        </div>
      )}

      {/* Filters */}
      <div className="mb-6">
        <FilterBar onReset={handleReset}>
          <WalletSelector value={walletId} onChange={setWalletId} wallets={wallets} />
          <SymbolInput value={symbol} onChange={setSymbol} />
          <ProtocolSelector value={protocol} onChange={setProtocol} />
          <AccountTypeSelector value={accountType} onChange={setAccountType} />
          <div>
            <label className="block text-xs text-gray-500 mb-1">Balance at Date</label>
            <input
              type="date"
              value={balanceAtDate}
              onChange={(e) => setBalanceAtDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {balanceAtDate && (
            <span className="self-end text-xs text-blue-600 bg-blue-50 px-2 py-1.5 rounded-lg border border-blue-200">
              Snapshot: {new Date(balanceAtDate).toLocaleDateString()}
            </span>
          )}
        </FilterBar>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="p-8 text-center text-gray-400">Loading accounts...</div>
      ) : error ? (
        <div className="p-8 text-center text-red-500">Failed to load accounts</div>
      ) : !filteredAccounts.length ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          {allAccounts.length > 0
            ? 'No accounts match the current filters.'
            : 'No accounts yet. Parse transactions to create accounts.'}
        </div>
      ) : (
        <div className="space-y-4">
          {TYPE_ORDER.map((type) => {
            const accounts = grouped[type]
            if (!accounts || accounts.length === 0) return null
            const style = TYPE_STYLES[type] ?? {
              color: 'text-gray-700',
              bg: 'bg-gray-50',
              border: 'border-gray-200',
              label: type,
              icon: DollarSign,
            }
            const isOpen = expandedTypes.has(type)
            const typeTotal = summaryTotals[type] ?? 0

            return (
              <div key={type} className={clsx('rounded-xl border overflow-hidden', style.bg, style.border)}>
                {/* Group Header */}
                <button
                  onClick={() => toggleType(type)}
                  className="w-full flex items-center justify-between px-5 py-3 text-left"
                >
                  <div className="flex items-center gap-2">
                    {isOpen
                      ? <ChevronDown className="w-4 h-4 text-gray-500" />
                      : <ChevronRight className="w-4 h-4 text-gray-500" />
                    }
                    <span className={clsx('font-semibold text-sm', style.color)}>
                      {style.label}
                    </span>
                    <span className="text-xs text-gray-500">({accounts.length})</span>
                  </div>
                  <span className={clsx('text-sm font-semibold', style.color)}>
                    {fmtUsd(typeTotal)}
                  </span>
                </button>

                {/* Expanded Table */}
                {isOpen && (
                  <div className="bg-white border-t border-gray-200">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b border-gray-100">
                        <tr>
                          <th className="px-4 py-2.5 text-left font-medium text-gray-600">Account</th>
                          <th className="px-4 py-2.5 text-left font-medium text-gray-600">Subtype</th>
                          <th className="px-4 py-2.5 text-left font-medium text-gray-600">Symbol</th>
                          <th className="px-4 py-2.5 text-right font-medium text-gray-600">
                            Quantity
                            {balanceAtDate ? (
                              <span className="text-xs text-gray-400 ml-1">
                                (as of {new Date(balanceAtDate).toLocaleDateString()})
                              </span>
                            ) : null}
                          </th>
                          <th className="px-4 py-2.5 text-right font-medium text-gray-600">Value (USD)</th>
                          <th className="px-4 py-2.5 text-right font-medium text-gray-600">Value (VND)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {accounts.map((acc) => {
                          const bal = getBalance(acc)
                          return (
                            <tr
                              key={acc.id}
                              className="hover:bg-gray-50 cursor-pointer transition-colors"
                              onClick={() => setSelectedAccount(acc)}
                            >
                              <td className="px-4 py-2.5 font-mono text-xs text-gray-700 max-w-[200px] truncate" title={acc.label}>
                                {shortLabel(acc.label)}
                              </td>
                              <td className="px-4 py-2.5 text-xs text-gray-500">{acc.subtype}</td>
                              <td className="px-4 py-2.5 font-medium text-gray-800">{acc.symbol}</td>
                              <td className={clsx(
                                'px-4 py-2.5 text-right font-mono text-xs',
                                bal > 0 ? 'text-green-600' : bal < 0 ? 'text-red-600' : 'text-gray-400',
                              )}>
                                {bal > 0 ? '+' : ''}{fmtQty(bal)}
                              </td>
                              <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-700">
                                {fmtUsd(acc.balance_usd)}
                              </td>
                              <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-700">
                                {fmtVnd(acc.balance_vnd)}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                      {/* Group footer with totals */}
                      <tfoot className="bg-gray-50 border-t border-gray-200">
                        <tr>
                          <td colSpan={4} className={clsx('px-4 py-2 text-right text-xs font-semibold', style.color)}>
                            Total {style.label}
                          </td>
                          <td className={clsx('px-4 py-2 text-right font-mono text-xs font-semibold', style.color)}>
                            {fmtUsd(typeTotal)}
                          </td>
                          <td className={clsx('px-4 py-2 text-right font-mono text-xs font-semibold', style.color)}>
                            {fmtVnd(accounts.reduce((sum, a) => sum + Number(a.balance_vnd ?? 0), 0))}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Account History Modal */}
      {selectedAccount && (
        <AccountHistoryModal
          account={selectedAccount}
          balanceAtDate={balanceAtDate || undefined}
          onClose={() => setSelectedAccount(null)}
        />
      )}
    </div>
  )
}

/* ─── Account History Modal ─── */

function AccountHistoryModal({
  account,
  balanceAtDate,
  onClose,
}: {
  account: Account
  balanceAtDate?: string
  onClose: () => void
}) {
  const [histDateFrom, setHistDateFrom] = useState<string>('')
  const [histDateTo, setHistDateTo] = useState<string>(balanceAtDate ?? '')
  const { data, isLoading } = useAccountHistory(account.id)

  // Apply client-side date filter for splits
  const splits: AccountHistorySplit[] = (data?.splits ?? []).filter((s) => {
    const ts = new Date(s.created_at)
    if (histDateFrom && ts < new Date(histDateFrom)) return false
    if (histDateTo && ts > new Date(histDateTo + 'T23:59:59Z')) return false
    return true
  })

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Account History</h3>
            <p className="text-xs font-mono text-gray-500 mt-0.5">{account.label}</p>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-xs text-gray-500">
                Balance: <span className="font-medium text-gray-700">{fmtQty(getBalance(account))} {account.symbol}</span>
              </span>
              {account.balance_usd != null && account.balance_usd !== 0 && (
                <span className="text-xs text-gray-500">
                  Value: <span className="font-medium text-gray-700">{fmtUsd(account.balance_usd)}</span>
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Date filter for history */}
        <div className="px-6 py-3 border-b border-gray-100 flex items-end gap-3 bg-gray-50">
          <div>
            <label className="block text-xs text-gray-500 mb-1">From</label>
            <input
              type="date"
              value={histDateFrom}
              onChange={(e) => setHistDateFrom(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">To</label>
            <input
              type="date"
              value={histDateTo}
              onChange={(e) => setHistDateTo(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {(histDateFrom || histDateTo) && (
            <button
              onClick={() => { setHistDateFrom(''); setHistDateTo('') }}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {/* Splits Table */}
        <div className="px-6 py-4">
          {isLoading ? (
            <p className="text-gray-400 text-center py-4">Loading...</p>
          ) : !splits.length ? (
            <p className="text-gray-400 text-center py-4">No transactions for this account</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Date</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-600">Quantity</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-600">Value (USD)</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-600">Value (VND)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {splits.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(s.created_at).toLocaleDateString()}
                    </td>
                    <td className={clsx(
                      'px-3 py-2 text-right font-mono text-xs',
                      s.quantity > 0 ? 'text-green-600' : s.quantity < 0 ? 'text-red-600' : 'text-gray-400',
                    )}>
                      {s.quantity > 0 ? '+' : ''}{fmtQty(s.quantity)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-gray-700">
                      {fmtUsd(s.value_usd)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-gray-700">
                      {fmtVnd(s.value_vnd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
