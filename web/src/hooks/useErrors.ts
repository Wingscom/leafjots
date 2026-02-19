import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getErrorSummary, ignoreError, listErrors, retryError, retryErrorGroup, type ErrorFilters } from '../api/errors'
import { useEntity } from '../context/EntityContext'

const ERRORS_KEY = ['errors'] as const

export function useErrors(filters: ErrorFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ERRORS_KEY, entityId, filters],
    queryFn: () => listErrors(filters, entityId ?? undefined),
  })
}

export function useErrorSummary() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ERRORS_KEY, 'summary', entityId],
    queryFn: () => getErrorSummary(entityId ?? undefined),
  })
}

export function useRetryError() {
  const queryClient = useQueryClient()
  const { entityId } = useEntity()
  return useMutation({
    mutationFn: (errorId: string) => retryError(errorId, entityId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ERRORS_KEY })
      queryClient.invalidateQueries({ queryKey: ['parse'] })
      queryClient.invalidateQueries({ queryKey: ['journal'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useIgnoreError() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (errorId: string) => ignoreError(errorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ERRORS_KEY })
    },
  })
}

export function useRetryErrorGroup() {
  const queryClient = useQueryClient()
  const { entityId } = useEntity()
  return useMutation({
    mutationFn: ({ contractAddress, functionSelector }: { contractAddress?: string; functionSelector?: string }) =>
      retryErrorGroup(contractAddress, functionSelector, entityId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ERRORS_KEY })
      queryClient.invalidateQueries({ queryKey: ['parse'] })
      queryClient.invalidateQueries({ queryKey: ['journal'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}
