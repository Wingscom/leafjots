import { useQuery } from '@tanstack/react-query'
import { getJournalEntry, listJournalEntries, listUnbalanced, type JournalFilters } from '../api/journal'
import { useEntity } from '../context/EntityContext'

const JOURNAL_KEY = ['journal'] as const

export function useJournalEntries(filters: JournalFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...JOURNAL_KEY, entityId, filters],
    queryFn: () => listJournalEntries(filters, entityId ?? undefined),
  })
}

export function useJournalEntry(id: string | null) {
  return useQuery({
    queryKey: [...JOURNAL_KEY, 'detail', id],
    queryFn: () => getJournalEntry(id!),
    enabled: !!id,
  })
}

export function useUnbalancedEntries() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...JOURNAL_KEY, 'unbalanced', entityId],
    queryFn: () => listUnbalanced(entityId ?? undefined),
  })
}
