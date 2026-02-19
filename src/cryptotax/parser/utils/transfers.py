"""Extract transfers from Etherscan transaction data."""

from cryptotax.parser.utils.gas import native_symbol
from cryptotax.parser.utils.types import RawTransfer


def extract_transfers_from_etherscan(tx_data: dict, chain: str) -> list[RawTransfer]:
    """Extract native value transfers from an Etherscan normal TX response."""
    transfers: list[RawTransfer] = []
    symbol = native_symbol(chain)

    # Native ETH transfer (from tx value field)
    value = int(tx_data.get("value", 0))
    if value > 0:
        from_addr = tx_data.get("from", "").lower()
        to_addr = tx_data.get("to", "").lower()
        if from_addr and to_addr:
            transfers.append(RawTransfer(
                token_address=None,
                from_address=from_addr,
                to_address=to_addr,
                value=value,
                decimals=18,
                symbol=symbol,
                transfer_type="native",
            ))

    return transfers


def extract_erc20_transfers(token_txs: list[dict]) -> list[RawTransfer]:
    """Convert Etherscan tokentx API response items into RawTransfer objects.

    Each item has: contractAddress, tokenSymbol, tokenDecimal, from, to, value.
    """
    transfers: list[RawTransfer] = []
    for ttx in token_txs:
        value = int(ttx.get("value", 0))
        if value == 0:
            continue
        transfers.append(RawTransfer(
            token_address=ttx.get("contractAddress", "").lower(),
            from_address=ttx.get("from", "").lower(),
            to_address=ttx.get("to", "").lower(),
            value=value,
            decimals=int(ttx.get("tokenDecimal", 18)),
            symbol=ttx.get("tokenSymbol", "UNKNOWN"),
            transfer_type="erc20",
        ))
    return transfers


def extract_internal_transfers(internal_txs: list[dict], chain: str) -> list[RawTransfer]:
    """Extract native value transfers from Etherscan txlistinternal responses."""
    transfers: list[RawTransfer] = []
    symbol = native_symbol(chain)
    for itx in internal_txs:
        value = int(itx.get("value", 0))
        if value == 0:
            continue
        # Skip errored internal TXs
        if itx.get("isError", "0") == "1":
            continue
        transfers.append(RawTransfer(
            token_address=None,
            from_address=itx.get("from", "").lower(),
            to_address=itx.get("to", "").lower(),
            value=value,
            decimals=18,
            symbol=symbol,
            transfer_type="internal",
        ))
    return transfers


def extract_all_transfers(tx_data: dict, chain: str) -> list[RawTransfer]:
    """Extract native + token + internal transfers from enriched tx_data."""
    if chain == "solana":
        from cryptotax.parser.utils.solana_transfers import extract_solana_transfers
        return extract_solana_transfers(tx_data, chain)

    # EVM chains: Etherscan format
    transfers = extract_transfers_from_etherscan(tx_data, chain)
    token_txs = tx_data.get("token_transfers", [])
    transfers.extend(extract_erc20_transfers(token_txs))
    internal_txs = tx_data.get("internal_transfers", [])
    transfers.extend(extract_internal_transfers(internal_txs, chain))
    return transfers
