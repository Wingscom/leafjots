import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  calculateTax,
  getRealizedGains,
  getOpenLots,
  getTaxSummary,
  type TaxCalculateRequest,
  type RealizedGainsFilters,
  type OpenLotsFilters,
} from '../api/tax'
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

export function useRealizedGains(filters: RealizedGainsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TAX_KEY, 'realized-gains', entityId, filters],
    queryFn: () => getRealizedGains(entityId ?? undefined, filters),
  })
}

export function useOpenLots(filters: OpenLotsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TAX_KEY, 'open-lots', entityId, filters],
    queryFn: () => getOpenLots(entityId ?? undefined, filters),
  })
}

export function useTaxSummary() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...TAX_KEY, 'summary', entityId],
    queryFn: () => getTaxSummary(entityId ?? undefined),
  })
}
