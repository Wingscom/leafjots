import { useEffect } from 'react'
import { Building2 } from 'lucide-react'
import { useEntities } from '../hooks/useEntities'
import { useEntity } from '../context/EntityContext'

export default function EntitySelector() {
  const { entityId, setEntityId } = useEntity()
  const { data, isLoading } = useEntities()

  const entities = data?.entities ?? []

  // Stale localStorage guard: validate that the stored entityId still exists in the fetched list.
  // If the entity was soft-deleted or no longer exists, clear it and auto-select the first available.
  useEffect(() => {
    if (isLoading || entities.length === 0) return

    if (entityId) {
      const exists = entities.some((e) => e.id === entityId)
      if (!exists) {
        setEntityId(entities[0].id)
      }
    } else {
      // Auto-select first entity if none selected
      setEntityId(entities[0].id)
    }
  }, [entities, entityId, isLoading, setEntityId])

  const selectedEntity = entities.find((e) => e.id === entityId)

  return (
    <div className="px-3 py-2">
      <label className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
        <Building2 className="w-3.5 h-3.5" />
        Entity
      </label>
      <select
        value={entityId ?? ''}
        onChange={(e) => setEntityId(e.target.value || null)}
        disabled={isLoading || entities.length === 0}
        className="w-full rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading && <option value="">Loading...</option>}
        {!isLoading && entities.length === 0 && <option value="">No entities</option>}
        {entities.map((entity) => (
          <option key={entity.id} value={entity.id}>
            {entity.name} ({entity.base_currency})
          </option>
        ))}
      </select>
      {selectedEntity && (
        <p className="mt-1 text-xs text-gray-400">
          {selectedEntity.wallet_count} wallet{selectedEntity.wallet_count !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
