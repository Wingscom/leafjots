import { useRef, useState } from 'react'
import { Plus, RefreshCw, Trash2, Upload } from 'lucide-react'
import { clsx } from 'clsx'
import { useWallets, useAddWallet, useAddCEXWallet, useDeleteWallet, useTriggerSync, useImportCSV } from '../hooks/useWallets'
import type { Chain, Exchange } from '../api/wallets'

const CHAINS: Chain[] = ['ethereum', 'arbitrum', 'optimism', 'polygon', 'base', 'bsc', 'avalanche', 'solana']
const EXCHANGES: Exchange[] = ['binance']

const SYNC_STATUS_STYLES: Record<string, string> = {
  IDLE: 'bg-gray-100 text-gray-600',
  SYNCING: 'bg-blue-100 text-blue-700',
  SYNCED: 'bg-green-100 text-green-700',
  ERROR: 'bg-red-100 text-red-700',
}

type WalletTab = 'onchain' | 'cex'

export default function Wallets() {
  const { data, isLoading, error } = useWallets()
  const addMutation = useAddWallet()
  const addCEXMutation = useAddCEXWallet()
  const deleteMutation = useDeleteWallet()
  const syncMutation = useTriggerSync()
  const importMutation = useImportCSV()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importWalletId, setImportWalletId] = useState<string | null>(null)

  const [tab, setTab] = useState<WalletTab>('onchain')
  const [chain, setChain] = useState<Chain>('ethereum')
  const [address, setAddress] = useState('')
  const [label, setLabel] = useState('')
  const [exchange, setExchange] = useState<Exchange>('binance')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [cexLabel, setCexLabel] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const handleAddOnchain = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!address.trim()) {
      setFormError('Address is required')
      return
    }
    try {
      await addMutation.mutateAsync({ chain, address: address.trim(), label: label.trim() || undefined })
      setAddress('')
      setLabel('')
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to add wallet')
    }
  }

  const handleAddCEX = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    try {
      await addCEXMutation.mutateAsync({
        exchange,
        api_key: apiKey.trim(),
        api_secret: apiSecret.trim(),
        label: cexLabel.trim() || undefined,
      })
      setApiKey('')
      setApiSecret('')
      setCexLabel('')
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to add CEX wallet')
    }
  }

  const handleImportCSV = (walletId: string) => {
    setImportWalletId(walletId)
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && importWalletId) {
      try {
        await importMutation.mutateAsync({ id: importWalletId, file })
      } catch (err) {
        setFormError(err instanceof Error ? err.message : 'CSV import failed')
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
    setImportWalletId(null)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Wallets</h2>

      {/* Add Wallet Form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setTab('onchain')}
            className={clsx(
              'px-4 py-1.5 rounded-lg text-sm font-medium transition-colors',
              tab === 'onchain' ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'
            )}
          >
            On-Chain
          </button>
          <button
            onClick={() => setTab('cex')}
            className={clsx(
              'px-4 py-1.5 rounded-lg text-sm font-medium transition-colors',
              tab === 'cex' ? 'bg-purple-100 text-purple-700' : 'text-gray-500 hover:bg-gray-100'
            )}
          >
            Exchange
          </button>
        </div>

        {tab === 'onchain' ? (
          <form onSubmit={handleAddOnchain} className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Chain</label>
              <select
                value={chain}
                onChange={(e) => setChain(e.target.value as Chain)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {CHAINS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="flex-1 min-w-64">
              <label className="block text-xs font-medium text-gray-700 mb-1">Address</label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="0x... or base58 address"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Label (optional)</label>
              <input
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="My main wallet"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={addMutation.isPending}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <Plus className="w-4 h-4" />
              {addMutation.isPending ? 'Adding...' : 'Add Wallet'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleAddCEX} className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Exchange</label>
              <select
                value={exchange}
                onChange={(e) => setExchange(e.target.value as Exchange)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {EXCHANGES.map((ex) => (
                  <option key={ex} value={ex}>{ex.charAt(0).toUpperCase() + ex.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="flex-1 min-w-48">
              <label className="block text-xs font-medium text-gray-700 mb-1">API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Binance API Key"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div className="flex-1 min-w-48">
              <label className="block text-xs font-medium text-gray-700 mb-1">API Secret</label>
              <input
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="Binance API Secret"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Label (optional)</label>
              <input
                type="text"
                value={cexLabel}
                onChange={(e) => setCexLabel(e.target.value)}
                placeholder="My Binance"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <button
              type="submit"
              disabled={addCEXMutation.isPending}
              className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              <Plus className="w-4 h-4" />
              {addCEXMutation.isPending ? 'Adding...' : 'Add Exchange'}
            </button>
          </form>
        )}
        {formError && (
          <p className="mt-2 text-sm text-red-600">{formError}</p>
        )}
      </div>

      {/* Hidden file input for CSV import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Wallet Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading wallets...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Failed to load wallets</div>
        ) : !data?.wallets.length ? (
          <div className="p-8 text-center text-gray-400">
            No wallets yet. Add one above to get started.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Chain / Exchange</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Address</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Label</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Last Sync</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.wallets.map((wallet) => (
                <tr key={wallet.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      wallet.wallet_type === 'cex' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                    )}>
                      {wallet.wallet_type === 'cex' ? 'CEX' : 'On-Chain'}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium capitalize">
                    {wallet.wallet_type === 'cex' ? wallet.exchange : wallet.chain}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600 max-w-xs truncate">
                    {wallet.address ?? '\u2014'}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{wallet.label ?? '\u2014'}</td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      SYNC_STATUS_STYLES[wallet.sync_status] ?? 'bg-gray-100 text-gray-600'
                    )}>
                      {wallet.sync_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {wallet.last_synced_at
                      ? new Date(wallet.last_synced_at).toLocaleString()
                      : 'Never'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => syncMutation.mutate(wallet.id)}
                        disabled={syncMutation.isPending}
                        title="Sync Now"
                        className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-50"
                      >
                        <RefreshCw className={clsx('w-4 h-4', syncMutation.isPending && 'animate-spin')} />
                      </button>
                      {wallet.wallet_type === 'cex' && (
                        <button
                          onClick={() => handleImportCSV(wallet.id)}
                          disabled={importMutation.isPending}
                          title="Import CSV"
                          className="p-1.5 rounded-lg text-gray-400 hover:text-purple-600 hover:bg-purple-50 transition-colors disabled:opacity-50"
                        >
                          <Upload className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (confirm(`Delete wallet ${wallet.label || wallet.address || wallet.exchange}?`))
                            deleteMutation.mutate(wallet.id)
                        }}
                        disabled={deleteMutation.isPending}
                        title="Delete"
                        className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
