import { apiFetch, withEntityId } from './client'

export interface ParsedSplit {
  account_label: string
  account_type: string
  symbol: string
  quantity: number
}

export interface ParseTestResponse {
  tx_hash: string
  parser_name: string
  entry_type: string
  splits: ParsedSplit[]
  balanced: boolean
  warnings: string[]
}

export interface ParseWalletResponse {
  processed: number
  errors: number
  total: number
}

export interface ParseStatsResponse {
  total: number
  parsed: number
  errors: number
  unknown: number
}

export async function parseTest(txHash: string, entityId?: string): Promise<ParseTestResponse> {
  return apiFetch<ParseTestResponse>(withEntityId('/parse/test', entityId), {
    method: 'POST',
    body: JSON.stringify({ tx_hash: txHash }),
  })
}

export async function parseWallet(walletId: string, entityId?: string): Promise<ParseWalletResponse> {
  return apiFetch<ParseWalletResponse>(withEntityId(`/parse/wallet/${walletId}`, entityId), {
    method: 'POST',
  })
}

export async function getParseStats(entityId?: string): Promise<ParseStatsResponse> {
  return apiFetch<ParseStatsResponse>(withEntityId('/parse/stats', entityId))
}
