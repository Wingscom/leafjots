import { useState } from 'react'
import { ChevronDown, ChevronRight, X } from 'lucide-react'
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
import type { Account } from '../api/accounts'

const TYPE_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  ASSET: { color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', label: 'Assets' },
  LIABILITY: { color: 'text-red-700', bg: 'bg-red-50 border-red-200', label: 'Liabilities' },
  INCOME: { color: 'text-green-700', bg: 'bg-green-50 border-green-200', label: 'Income' },
  EXPENSE: { color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', label: 'Expenses' },
}

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

export default function Accounts() {
  const { data, isLoading, error } = useAccounts()
  const [expandedType, setExpandedType] = useState<string | null>('ASSET')
  const [selectedId, setSelectedId] = useState<string | null>(null)

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

  // Apply client-side filters (API supports server-side filtering if needed)
  const allAccounts = data?.accounts ?? []
  const filteredAccounts = allAccounts.filter((acc) => {
    if (walletId && acc.wallet_id !== walletId) return false
    if (symbol && !acc.symbol.toUpperCase().includes(symbol.toUpperCase())) return false
    if (protocol && acc.protocol !== protocol) return false
    if (accountType && acc.account_type !== accountType) return false
    return true
  })

  const grouped = groupByType(filteredAccounts)
  const typeOrder = ['ASSET', 'LIABILITY', 'INCOME', 'EXPENSE']

  function handleReset() {
    setWalletId(null)
    setSymbol('')
    setProtocol(null)
    setAccountType(null)
    setBalanceAtDate('')
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Accounts & Balances</h2>

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
          {typeOrder.map((type) => {
            const accounts = grouped[type]
            if (!accounts || accounts.length === 0) return null
            const style = TYPE_STYLES[type] ?? { color: 'text-gray-700', bg: 'bg-gray-50 border-gray-200', label: type }
            const isOpen = expandedType === type

            return (
              <div key={type} className={clsx('rounded-xl border overflow-hidden', style.bg)}>
                <button
                  onClick={() => setExpandedType(isOpen ? null : type)}
                  className="w-full flex items-center justify-between px-5 py-3 text-left"
                >
                  <div className="flex items-center gap-2">
                    {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    <span className={clsx('font-semibold text-sm', style.color)}>{style.label}</span>
                    <span className="text-xs text-gray-500">({accounts.length})</span>
                  </div>
                </button>

                {isOpen && (
                  <div className="bg-white border-t border-gray-200">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b border-gray-100">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Account</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Subtype</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-600">Symbol</th>
                          <th className="px-4 py-2 text-right font-medium text-gray-600">
                            Balance{balanceAtDate ? ` (as of ${new Date(balanceAtDate).toLocaleDateString()})` : ''}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {accounts.map((acc) => (
                          <tr
                            key={acc.id}
                            className="hover:bg-gray-50 cursor-pointer"
                            onClick={() => setSelectedId(acc.id)}
                          >
                            <td className="px-4 py-2 font-mono text-xs text-gray-700 max-w-sm truncate">
                              {shortLabel(acc.label)}
                            </td>
                            <td className="px-4 py-2 text-xs text-gray-500">{acc.subtype}</td>
                            <td className="px-4 py-2 font-medium">{acc.symbol}</td>
                            <td className={clsx(
                              'px-4 py-2 text-right font-mono text-xs',
                              acc.balance > 0 ? 'text-green-600' : acc.balance < 0 ? 'text-red-600' : 'text-gray-400',
                            )}>
                              {acc.balance}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Account History Modal */}
      {selectedId && (
        <AccountHistoryModal
          accountId={selectedId}
          balanceAtDate={balanceAtDate || undefined}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}

function AccountHistoryModal({
  accountId,
  balanceAtDate,
  onClose,
}: {
  accountId: string
  balanceAtDate?: string
  onClose: () => void
}) {
  const [histDateFrom, setHistDateFrom] = useState<string>('')
  const [histDateTo, setHistDateTo] = useState<string>(balanceAtDate ?? '')
  const { data, isLoading } = useAccountHistory(accountId)

  // Apply client-side date filter for splits
  const splits = (data?.splits ?? []).filter((s) => {
    const ts = new Date(s.timestamp)
    if (histDateFrom && ts < new Date(histDateFrom)) return false
    if (histDateTo && ts > new Date(histDateTo + 'T23:59:59Z')) return false
    return true
  })

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Account History</h3>
            {data?.account && (
              <p className="text-xs font-mono text-gray-500 mt-0.5">{data.account.label}</p>
            )}
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
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Type</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Description</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-600">Quantity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {splits.map((s) => (
                  <tr key={s.id}>
                    <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(s.timestamp).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700">
                        {s.entry_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600 text-xs truncate max-w-xs">{s.description}</td>
                    <td className={clsx(
                      'px-3 py-2 text-right font-mono text-xs',
                      s.quantity > 0 ? 'text-green-600' : s.quantity < 0 ? 'text-red-600' : 'text-gray-400',
                    )}>
                      {s.quantity > 0 ? '+' : ''}{s.quantity}
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
