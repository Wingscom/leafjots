import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { calculateTax, getRealizedGains, getOpenLots, getTaxSummary, type TaxCalculateRequest } from '../api/tax'
import { useEntity } from '../context/EntityContext'

const TAX_KEY = ['tax'] as const

export function useCalculateTax() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: TaxCalculateRequest) => calculateTax(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TAX_KEY })
    },
  })
}

export function useRealizedGains() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TAX_KEY, 'realized-gains', entityId],
    queryFn: () => getRealizedGains(entityId ?? undefined),
  })
}

export function useOpenLots() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TAX_KEY, 'open-lots', entityId],
    queryFn: () => getOpenLots(entityId ?? undefined),
  })
}

export function useTaxSummary() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TAX_KEY, 'summary', entityId],
    queryFn: () => getTaxSummary(entityId ?? undefined),
  })
}
