const CHAINS = [
  'Ethereum',
  'Arbitrum',
  'Optimism',
  'Polygon',
  'Base',
  'BSC',
  'Avalanche',
  'CEX',
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
          <option key={chain} value={chain}>
            {chain}
          </option>
        ))}
      </select>
    </div>
  )
}
