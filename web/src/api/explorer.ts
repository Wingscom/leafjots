/** Block explorer URL helpers for multi-chain support. */

const EXPLORERS: Record<string, string> = {
  ethereum: 'https://etherscan.io',
  arbitrum: 'https://arbiscan.io',
  optimism: 'https://optimistic.etherscan.io',
  polygon: 'https://polygonscan.com',
  base: 'https://basescan.org',
  avalanche: 'https://snowtrace.io',
  bsc: 'https://bscscan.com',
}

export function txUrl(chain: string, txHash: string): string {
  const base = EXPLORERS[chain] ?? EXPLORERS.ethereum
  return `${base}/tx/${txHash}`
}

export function addressUrl(chain: string, address: string): string {
  const base = EXPLORERS[chain] ?? EXPLORERS.ethereum
  return `${base}/address/${address}`
}
