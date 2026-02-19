import { useState } from 'react'
import { Building2, Plus, Pencil, Trash2, X, Check } from 'lucide-react'
import { clsx } from 'clsx'
import { useEntities, useCreateEntity, useUpdateEntity, useDeleteEntity } from '../hooks/useEntities'
import { useEntity } from '../context/EntityContext'
import type { Entity } from '../api/entities'

const CURRENCIES = ['VND', 'USD', 'EUR', 'SGD', 'JPY']

export default function Entities() {
  const { data, isLoading, error } = useEntities()
  const { entityId, setEntityId } = useEntity()
  const createMutation = useCreateEntity()
  const updateMutation = useUpdateEntity()
  const deleteMutation = useDeleteEntity()

  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createCurrency, setCreateCurrency] = useState('VND')

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editCurrency, setEditCurrency] = useState('')

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const entities = data?.entities ?? []

  function handleCreate() {
    if (!createName.trim()) return
    createMutation.mutate(
      { name: createName.trim(), base_currency: createCurrency },
      {
        onSuccess: () => {
          setCreateName('')
          setCreateCurrency('VND')
          setShowCreate(false)
        },
      },
    )
  }

  function startEdit(entity: Entity) {
    setEditingId(entity.id)
    setEditName(entity.name)
    setEditCurrency(entity.base_currency)
  }

  function handleUpdate() {
    if (!editingId || !editName.trim()) return
    updateMutation.mutate(
      { id: editingId, data: { name: editName.trim(), base_currency: editCurrency } },
      {
        onSuccess: () => {
          setEditingId(null)
        },
      },
    )
  }

  function handleDelete(id: string) {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        setDeleteConfirmId(null)
        // If the deleted entity was selected, clear selection so the selector auto-picks another
        if (entityId === id) {
          setEntityId(null)
        }
      },
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Building2 className="w-6 h-6 text-gray-400" />
          <h2 className="text-2xl font-bold text-gray-900">Entities</h2>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          New Entity
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Create New Entity</h3>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">Name</label>
              <input
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="e.g. My Fund, Personal"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
            </div>
            <div className="w-32">
              <label className="block text-xs text-gray-500 mb-1">Currency</label>
              <select
                value={createCurrency}
                onChange={(e) => setCreateCurrency(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCreate}
              disabled={!createName.trim() || createMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Check className="w-4 h-4" />
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="flex items-center gap-1.5 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm"
            >
              <X className="w-4 h-4" />
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Entity Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading entities...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Failed to load entities</div>
        ) : entities.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No entities yet. Create one to get started.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Currency</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Wallets</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Created</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entities.map((entity) => {
                const isEditing = editingId === entity.id
                const isSelected = entityId === entity.id
                const isDeleting = deleteConfirmId === entity.id

                return (
                  <tr
                    key={entity.id}
                    className={clsx('hover:bg-gray-50', isSelected && 'bg-blue-50/50')}
                  >
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 w-full"
                          onKeyDown={(e) => e.key === 'Enter' && handleUpdate()}
                        />
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">{entity.name}</span>
                          {isSelected && (
                            <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                              Active
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {isEditing ? (
                        <select
                          value={editCurrency}
                          onChange={(e) => setEditCurrency(e.target.value)}
                          className="rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        >
                          {CURRENCIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      ) : (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-medium">
                          {entity.base_currency}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{entity.wallet_count}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(entity.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-1">
                        {isEditing ? (
                          <>
                            <button
                              onClick={handleUpdate}
                              disabled={updateMutation.isPending}
                              className="p-1.5 rounded-lg text-green-600 hover:bg-green-50 transition-colors"
                              title="Save"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition-colors"
                              title="Cancel"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        ) : isDeleting ? (
                          <>
                            <span className="text-xs text-red-600 mr-1">Delete?</span>
                            <button
                              onClick={() => handleDelete(entity.id)}
                              disabled={deleteMutation.isPending}
                              className="p-1.5 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
                              title="Confirm delete"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(null)}
                              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition-colors"
                              title="Cancel"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => startEdit(entity)}
                              className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors"
                              title="Edit"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(entity.id)}
                              className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
