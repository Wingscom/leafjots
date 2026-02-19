"""Extract transfers from Solana parsed transaction data."""

from cryptotax.parser.utils.types import RawTransfer

# SOL has 9 decimal places (lamports)
SOL_DECIMALS = 9
SOL_SYMBOL = "SOL"


def extract_solana_transfers(tx_data: dict, chain: str = "solana") -> list[RawTransfer]:
    """Extract SOL native + SPL token transfers from a Solana parsed transaction.

    Uses preBalances/postBalances for SOL and preTokenBalances/postTokenBalances for SPL tokens.
    """
    transfers: list[RawTransfer] = []
    meta = tx_data.get("meta", {}) or {}
    transaction = tx_data.get("transaction", {}) or {}
    message = transaction.get("message", {}) or {}
    account_keys = message.get("accountKeys", [])

    if not account_keys or not meta:
        return transfers

    # Build pubkey list
    pubkeys = []
    for key in account_keys:
        if isinstance(key, dict):
            pubkeys.append(key.get("pubkey", ""))
        else:
            pubkeys.append(str(key))

    # 1. SOL native transfers from balance diffs
    transfers.extend(_extract_sol_transfers(meta, pubkeys))

    # 2. SPL token transfers from token balance diffs
    transfers.extend(_extract_spl_transfers(meta, pubkeys))

    return transfers


def _extract_sol_transfers(meta: dict, pubkeys: list[str]) -> list[RawTransfer]:
    """Extract SOL transfers by diffing pre/post balances."""
    transfers: list[RawTransfer] = []
    pre_balances = meta.get("preBalances", [])
    post_balances = meta.get("postBalances", [])

    if not pre_balances or not post_balances:
        return transfers

    # Find accounts with balance changes (ignoring fee payer's fee deduction)
    senders: list[tuple[str, int]] = []
    receivers: list[tuple[str, int]] = []

    for i in range(min(len(pre_balances), len(post_balances), len(pubkeys))):
        diff = post_balances[i] - pre_balances[i]
        if diff < 0:
            senders.append((pubkeys[i], abs(diff)))
        elif diff > 0:
            receivers.append((pubkeys[i], diff))

    # Create transfer pairs: match senders to receivers
    for sender_addr, sent_amount in senders:
        for receiver_addr, recv_amount in receivers:
            # Use the smaller amount as the transfer value
            transfer_amount = min(sent_amount, recv_amount)
            if transfer_amount > 0:
                transfers.append(RawTransfer(
                    token_address=None,
                    from_address=sender_addr,
                    to_address=receiver_addr,
                    value=transfer_amount,
                    decimals=SOL_DECIMALS,
                    symbol=SOL_SYMBOL,
                    transfer_type="native",
                ))

    return transfers


def _extract_spl_transfers(meta: dict, pubkeys: list[str]) -> list[RawTransfer]:
    """Extract SPL token transfers by diffing pre/post token balances."""
    transfers: list[RawTransfer] = []
    pre_token_balances = meta.get("preTokenBalances", [])
    post_token_balances = meta.get("postTokenBalances", [])

    # Build index: (accountIndex, mint) -> balance info
    pre_map: dict[tuple[int, str], dict] = {}
    for tb in pre_token_balances:
        key = (tb.get("accountIndex", -1), tb.get("mint", ""))
        pre_map[key] = tb

    post_map: dict[tuple[int, str], dict] = {}
    for tb in post_token_balances:
        key = (tb.get("accountIndex", -1), tb.get("mint", ""))
        post_map[key] = tb

    # Find all mints involved
    all_keys = set(pre_map.keys()) | set(post_map.keys())

    # Group by mint to find senders and receivers
    mint_changes: dict[str, list[tuple[str, int, int, str]]] = {}
    for account_index, mint in all_keys:
        if account_index < 0 or account_index >= len(pubkeys):
            continue

        pre_info = pre_map.get((account_index, mint), {})
        post_info = post_map.get((account_index, mint), {})

        pre_amount = int(pre_info.get("uiTokenAmount", {}).get("amount", "0") if pre_info else "0")
        post_amount = int(post_info.get("uiTokenAmount", {}).get("amount", "0") if post_info else "0")
        decimals = int(
            (post_info or pre_info).get("uiTokenAmount", {}).get("decimals", 0)
        )

        # Get owner address (from token account info)
        owner = (post_info or pre_info).get("owner", pubkeys[account_index])

        # Get symbol from tokenInfo if available
        symbol = _get_token_symbol(post_info or pre_info, mint)

        diff = post_amount - pre_amount
        if diff != 0:
            mint_changes.setdefault(mint, []).append((owner, diff, decimals, symbol))

    # Create transfer pairs per mint
    for mint, changes in mint_changes.items():
        senders = [(owner, abs(diff), decimals, symbol) for owner, diff, decimals, symbol in changes if diff < 0]
        receivers = [(owner, diff, decimals, symbol) for owner, diff, decimals, symbol in changes if diff > 0]

        for sender_addr, sent, decimals, symbol in senders:
            for receiver_addr, recv, _, _ in receivers:
                amount = min(sent, recv)
                if amount > 0:
                    transfers.append(RawTransfer(
                        token_address=mint,
                        from_address=sender_addr,
                        to_address=receiver_addr,
                        value=amount,
                        decimals=decimals,
                        symbol=symbol,
                        transfer_type="erc20",  # Reuse erc20 type for SPL tokens
                    ))

    return transfers


def _get_token_symbol(token_balance: dict, mint: str) -> str:
    """Extract symbol from Solana parsed token balance info."""
    # Some RPC providers (Helius) include tokenInfo
    if "tokenInfo" in token_balance:
        return token_balance["tokenInfo"].get("symbol", mint[:8])
    # Fallback: use truncated mint address
    return mint[:8]
