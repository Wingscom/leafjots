import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getParseStats, parseTest, parseWallet } from '../api/parse'
import { useEntity } from '../context/EntityContext'

const PARSE_KEY = ['parse'] as const

export function useParseStats() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...PARSE_KEY, 'stats', entityId],
    queryFn: () => getParseStats(entityId ?? undefined),
  })
}

export function useParseTest() {
  const queryClient = useQueryClient()
  const { entityId } = useEntity()
  return useMutation({
    mutationFn: (txHash: string) => parseTest(txHash, entityId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PARSE_KEY })
      queryClient.invalidateQueries({ queryKey: ['journal'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useParseWallet() {
  const queryClient = useQueryClient()
  const { entityId } = useEntity()
  return useMutation({
    mutationFn: (walletId: string) => parseWallet(walletId, entityId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PARSE_KEY })
      queryClient.invalidateQueries({ queryKey: ['journal'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['errors'] })
    },
  })
}
