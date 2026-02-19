import { apiFetch, withEntityId } from './client'

export type Chain = 'ethereum' | 'arbitrum' | 'optimism' | 'polygon' | 'base' | 'bsc' | 'avalanche' | 'solana'

export type Exchange = 'binance'

export type WalletType = 'onchain' | 'cex'

export interface Wallet {
  id: string
  entity_id: string
  wallet_type: WalletType
  chain: string | null
  address: string | null
  exchange: string | null
  label: string | null
  sync_status: 'IDLE' | 'SYNCING' | 'SYNCED' | 'ERROR'
  last_block_loaded: number | null
  last_synced_at: string | null
  created_at: string
  updated_at: string
}

export interface WalletList {
  wallets: Wallet[]
  total: number
}

export interface WalletCreate {
  chain: Chain
  address: string
  label?: string
}

export interface CEXWalletCreate {
  exchange: Exchange
  api_key: string
  api_secret: string
  label?: string
}

export async function listWallets(entityId?: string): Promise<WalletList> {
  return apiFetch<WalletList>(withEntityId('/wallets', entityId))
}

export async function addWallet(data: WalletCreate, entityId?: string): Promise<Wallet> {
  return apiFetch<Wallet>(withEntityId('/wallets', entityId), {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function addCEXWallet(data: CEXWalletCreate, entityId?: string): Promise<Wallet> {
  return apiFetch<Wallet>(withEntityId('/wallets/cex', entityId), {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteWallet(id: string): Promise<void> {
  await apiFetch<void>(`/wallets/${id}`, { method: 'DELETE' })
}

export async function triggerSync(id: string): Promise<Wallet> {
  return apiFetch<Wallet>(`/wallets/${id}/sync`, { method: 'POST' })
}

export async function importCSV(id: string, file: File): Promise<{ imported: number }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`/api/wallets/${id}/import-csv`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}
