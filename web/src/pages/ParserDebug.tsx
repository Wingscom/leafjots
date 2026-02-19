import { useState } from 'react'
import { clsx } from 'clsx'
import { Play, RefreshCw, Search } from 'lucide-react'
import { useParseStats, useParseTest, useParseWallet } from '../hooks/useParser'
import { useWallets } from '../hooks/useWallets'
import type { ParseTestResponse } from '../api/parse'

const TYPE_COLORS: Record<string, string> = {
  ASSET: 'text-blue-700 bg-blue-50',
  LIABILITY: 'text-red-700 bg-red-50',
  INCOME: 'text-green-700 bg-green-50',
  EXPENSE: 'text-orange-700 bg-orange-50',
}

export default function ParserDebug() {
  const [txHash, setTxHash] = useState('')
  const [result, setResult] = useState<ParseTestResponse | null>(null)

  const parseTest = useParseTest()
  const parseWallet = useParseWallet()
  const { data: stats, isLoading: statsLoading } = useParseStats()
  const { data: walletData } = useWallets()

  const handleTest = () => {
    if (!txHash.trim()) return
    parseTest.mutate(txHash.trim(), {
      onSuccess: (data) => setResult(data),
    })
  }

  const handleParseWallet = (walletId: string) => {
    parseWallet.mutate(walletId)
  }

  const parsedPct = stats && stats.total > 0
    ? Math.round((stats.parsed / stats.total) * 100)
    : 0

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Parser Debug</h2>

      {/* Stats Panel */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {statsLoading ? (
          <div className="col-span-4 text-gray-400 text-center py-4">Loading stats...</div>
        ) : stats ? (
          <>
            <StatCard label="Total TXs" value={stats.total.toLocaleString()} />
            <StatCard label="Parsed" value={`${stats.parsed.toLocaleString()} (${parsedPct}%)`} />
            <StatCard label="Errors" value={String(stats.errors)} color="text-red-600" />
            <StatCard label="Unknown" value={String(stats.unknown)} color="text-yellow-600" />
          </>
        ) : null}
      </div>

      {/* Test Parse Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Test Parse</h3>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={txHash}
              onChange={(e) => setTxHash(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleTest()}
              placeholder="Paste TX hash (0x...)..."
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleTest}
            disabled={parseTest.isPending || !txHash.trim()}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            <Play className="w-4 h-4" />
            {parseTest.isPending ? 'Parsing...' : 'Parse'}
          </button>
        </div>

        {parseTest.isError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {(parseTest.error as Error).message}
          </div>
        )}
      </div>

      {/* Parse Result */}
      {result && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">Parse Result</h3>
            <div className="flex items-center gap-3">
              <span className={clsx(
                'px-2 py-0.5 rounded-full text-xs font-medium',
                result.balanced ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              )}>
                {result.balanced ? 'Balanced' : 'Unbalanced'}
              </span>
              <span className="text-xs text-gray-500">{result.entry_type}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-gray-500">Parser:</span>
            <span className={clsx(
              'px-2 py-0.5 rounded text-xs font-mono font-medium',
              result.parser_name.includes('Aave') ? 'bg-purple-100 text-purple-700'
                : result.parser_name.includes('Uniswap') ? 'bg-pink-100 text-pink-700'
                : result.parser_name.includes('Curve') ? 'bg-yellow-100 text-yellow-700'
                : result.parser_name.includes('Swap') ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-700'
            )}>
              {result.parser_name}
            </span>
          </div>

          {result.splits.length > 0 ? (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Account</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Type</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Symbol</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-600">Quantity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {result.splits.map((s, i) => (
                  <tr key={i}>
                    <td className="px-3 py-2 font-mono text-xs text-gray-700 max-w-xs truncate">{s.account_label}</td>
                    <td className="px-3 py-2">
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', TYPE_COLORS[s.account_type] ?? 'bg-gray-100 text-gray-600')}>
                        {s.account_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-medium">{s.symbol}</td>
                    <td className={clsx(
                      'px-3 py-2 text-right font-mono text-xs',
                      s.quantity > 0 ? 'text-green-600' : s.quantity < 0 ? 'text-red-600' : 'text-gray-500',
                    )}>
                      {s.quantity > 0 ? '+' : ''}{s.quantity}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-400 text-sm">No splits produced</p>
          )}

          {result.warnings.length > 0 && (
            <div className="mt-3 space-y-1">
              {result.warnings.map((w, i) => (
                <div key={i} className="p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700">{w}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Bulk Parse Wallets */}
      {walletData && walletData.wallets.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Bulk Parse by Wallet</h3>
          <div className="space-y-2">
            {walletData.wallets.map((w) => (
              <div key={w.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <span className="text-sm font-medium capitalize">{w.chain}</span>
                  <span className="ml-2 text-xs font-mono text-gray-500">{w.address}</span>
                </div>
                <button
                  onClick={() => handleParseWallet(w.id)}
                  disabled={parseWallet.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-medium hover:bg-gray-100 disabled:opacity-40 transition-colors"
                >
                  <RefreshCw className={clsx('w-3.5 h-3.5', parseWallet.isPending && 'animate-spin')} />
                  Parse All
                </button>
              </div>
            ))}
          </div>
          {parseWallet.isSuccess && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              Done: {parseWallet.data.processed} parsed, {parseWallet.data.errors} errors, {parseWallet.data.total} total
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={clsx('text-xl font-bold', color ?? 'text-gray-900')}>{value}</p>
    </div>
  )
}
