import { useQuery } from '@tanstack/react-query'
import { getAccountHistory, listAccounts } from '../api/accounts'
import { useEntity } from '../context/EntityContext'

const ACCOUNTS_KEY = ['accounts'] as const

export function useAccounts() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, entityId],
    queryFn: () => listAccounts(entityId ?? undefined),
  })
}

export function useAccountHistory(accountId: string | null, limit = 50, offset = 0) {
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, 'history', accountId, limit, offset],
    queryFn: () => getAccountHistory(accountId!, limit, offset),
    enabled: !!accountId,
  })
}
