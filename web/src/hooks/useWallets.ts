import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { addCEXWallet, addWallet, deleteWallet, importCSV, listWallets, triggerSync, type CEXWalletCreate, type WalletCreate } from '../api/wallets'
import { useEntity } from '../context/EntityContext'

const WALLETS_KEY = ['wallets'] as const

export function useWallets() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...WALLETS_KEY, entityId],
    queryFn: () => listWallets(entityId ?? undefined),
  })
}

export function useAddWallet() {
  const queryClient = useQueryClient()
  const { entityId } = useEntity()
  return useMutation({
    mutationFn: (data: WalletCreate) => addWallet(data, entityId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_KEY })
    },
  })
}

export function useAddCEXWallet() {
  const queryClient = useQueryClient()
  const { entityId } = useEntity()
  return useMutation({
    mutationFn: (data: CEXWalletCreate) => addCEXWallet(data, entityId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_KEY })
    },
  })
}

export function useDeleteWallet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteWallet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_KEY })
    },
  })
}

export function useTriggerSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => triggerSync(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_KEY })
    },
  })
}

export function useImportCSV() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => importCSV(id, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_KEY })
    },
  })
}
