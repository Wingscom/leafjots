const ACCOUNT_TYPES = ['ASSET', 'LIABILITY', 'INCOME', 'EXPENSE']

interface AccountTypeSelectorProps {
  value: string | null
  onChange: (v: string | null) => void
}

export default function AccountTypeSelector({ value, onChange }: AccountTypeSelectorProps) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">Account Type</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Account Types</option>
        {ACCOUNT_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
    </div>
  )
}
