interface WalletSelectorProps {
  value: string | null
  onChange: (v: string | null) => void
  wallets: { id: string; label: string }[]
}

export default function WalletSelector({ value, onChange, wallets }: WalletSelectorProps) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">Wallet</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Wallets</option>
        {wallets.map((w) => (
          <option key={w.id} value={w.id}>
            {w.label}
          </option>
        ))}
      </select>
    </div>
  )
}
