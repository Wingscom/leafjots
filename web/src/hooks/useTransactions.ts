import { useQuery } from '@tanstack/react-query'
import { getTransaction, listTransactions, type TransactionFilters } from '../api/transactions'
import { useEntity } from '../context/EntityContext'

const TXS_KEY = ['transactions'] as const

export function useTransactions(filters: TransactionFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TXS_KEY, entityId, filters],
    queryFn: () => listTransactions(filters, entityId ?? undefined),
  })
}

export function useTransaction(txHash: string | null) {
  return useQuery({
    queryKey: [...TXS_KEY, 'detail', txHash],
    queryFn: () => getTransaction(txHash!),
    enabled: !!txHash,
  })
}
