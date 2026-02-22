const CHAINS = [
  { value: 'ethereum', label: 'Ethereum' },
  { value: 'arbitrum', label: 'Arbitrum' },
  { value: 'optimism', label: 'Optimism' },
  { value: 'polygon', label: 'Polygon' },
  { value: 'base', label: 'Base' },
  { value: 'bsc', label: 'BSC' },
  { value: 'avalanche', label: 'Avalanche' },
  { value: 'cex', label: 'CEX' },
]

interface ChainSelectorProps {
  value: string | null
  onChange: (v: string | null) => void
}

export default function ChainSelector({ value, onChange }: ChainSelectorProps) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">Chain</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Chains</option>
        {CHAINS.map((chain) => (
          <option key={chain.value} value={chain.value}>
            {chain.label}
          </option>
        ))}
      </select>
    </div>
  )
}
