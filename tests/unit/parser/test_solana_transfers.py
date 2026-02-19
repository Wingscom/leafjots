"""Tests for Solana transfer extraction from parsed TX data."""

from cryptotax.parser.utils.solana_transfers import extract_solana_transfers


def _make_solana_tx(
    pre_balances=None,
    post_balances=None,
    pre_token_balances=None,
    post_token_balances=None,
    account_keys=None,
):
    if account_keys is None:
        account_keys = [
            {"pubkey": "SenderAddr1111111111111111111111111111111111", "signer": True},
            {"pubkey": "ReceiverAddr222222222222222222222222222222222", "signer": False},
        ]
    if pre_balances is None:
        pre_balances = [1_000_000_000, 500_000_000]
    if post_balances is None:
        post_balances = [1_000_000_000, 500_000_000]
    if pre_token_balances is None:
        pre_token_balances = []
    if post_token_balances is None:
        post_token_balances = []

    return {
        "transaction": {
            "message": {"accountKeys": account_keys},
        },
        "meta": {
            "fee": 5000,
            "preBalances": pre_balances,
            "postBalances": post_balances,
            "preTokenBalances": pre_token_balances,
            "postTokenBalances": post_token_balances,
        },
    }


class TestSolNativeTransfers:
    def test_simple_sol_transfer(self):
        """Sender sends SOL to receiver — should detect transfer."""
        tx = _make_solana_tx(
            pre_balances=[2_000_000_000, 500_000_000],
            post_balances=[1_000_000_000, 1_500_000_000],
        )
        transfers = extract_solana_transfers(tx)

        assert len(transfers) >= 1
        sol_transfers = [t for t in transfers if t.symbol == "SOL"]
        assert len(sol_transfers) >= 1
        assert sol_transfers[0].decimals == 9
        assert sol_transfers[0].transfer_type == "native"

    def test_no_balance_change(self):
        """No SOL movement — no transfers."""
        tx = _make_solana_tx(
            pre_balances=[1_000_000_000, 500_000_000],
            post_balances=[1_000_000_000, 500_000_000],
        )
        transfers = extract_solana_transfers(tx)
        sol_transfers = [t for t in transfers if t.symbol == "SOL"]
        assert len(sol_transfers) == 0


class TestSPLTokenTransfers:
    def test_spl_token_transfer(self):
        """USDC SPL token transfer."""
        mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC mint
        tx = _make_solana_tx(
            pre_token_balances=[
                {
                    "accountIndex": 0,
                    "mint": mint,
                    "owner": "SenderAddr1111111111111111111111111111111111",
                    "uiTokenAmount": {"amount": "1000000000", "decimals": 6},
                },
            ],
            post_token_balances=[
                {
                    "accountIndex": 0,
                    "mint": mint,
                    "owner": "SenderAddr1111111111111111111111111111111111",
                    "uiTokenAmount": {"amount": "500000000", "decimals": 6},
                },
                {
                    "accountIndex": 1,
                    "mint": mint,
                    "owner": "ReceiverAddr222222222222222222222222222222222",
                    "uiTokenAmount": {"amount": "500000000", "decimals": 6},
                },
            ],
        )
        transfers = extract_solana_transfers(tx)
        spl_transfers = [t for t in transfers if t.transfer_type == "erc20"]
        assert len(spl_transfers) >= 1
        assert spl_transfers[0].token_address == mint
        assert spl_transfers[0].decimals == 6

    def test_spl_with_token_info_symbol(self):
        """Token with tokenInfo should use its symbol."""
        mint = "SomeMintAddress"
        tx = _make_solana_tx(
            pre_token_balances=[
                {
                    "accountIndex": 0,
                    "mint": mint,
                    "owner": "SenderAddr1111111111111111111111111111111111",
                    "uiTokenAmount": {"amount": "1000", "decimals": 9},
                    "tokenInfo": {"symbol": "BONK"},
                },
            ],
            post_token_balances=[
                {
                    "accountIndex": 0,
                    "mint": mint,
                    "owner": "SenderAddr1111111111111111111111111111111111",
                    "uiTokenAmount": {"amount": "500", "decimals": 9},
                    "tokenInfo": {"symbol": "BONK"},
                },
                {
                    "accountIndex": 1,
                    "mint": mint,
                    "owner": "ReceiverAddr222222222222222222222222222222222",
                    "uiTokenAmount": {"amount": "500", "decimals": 9},
                    "tokenInfo": {"symbol": "BONK"},
                },
            ],
        )
        transfers = extract_solana_transfers(tx)
        spl_transfers = [t for t in transfers if t.transfer_type == "erc20"]
        assert any(t.symbol == "BONK" for t in spl_transfers)


class TestEdgeCases:
    def test_empty_tx_data(self):
        transfers = extract_solana_transfers({})
        assert transfers == []

    def test_no_meta(self):
        transfers = extract_solana_transfers({"transaction": {"message": {"accountKeys": []}}})
        assert transfers == []

    def test_empty_meta(self):
        tx = _make_solana_tx(
            pre_balances=[],
            post_balances=[],
            pre_token_balances=[],
            post_token_balances=[],
        )
        transfers = extract_solana_transfers(tx)
        assert transfers == []


class TestTransfersDispatch:
    def test_extract_all_dispatches_to_solana(self):
        """extract_all_transfers should use Solana extractor for chain='solana'."""
        from cryptotax.parser.utils.transfers import extract_all_transfers

        tx = _make_solana_tx(
            pre_balances=[2_000_000_000, 500_000_000],
            post_balances=[1_000_000_000, 1_500_000_000],
        )
        transfers = extract_all_transfers(tx, chain="solana")
        # Should find SOL transfers
        sol_transfers = [t for t in transfers if t.symbol == "SOL"]
        assert len(sol_transfers) >= 1

    def test_extract_all_dispatches_to_evm(self):
        """extract_all_transfers should use EVM extractor for EVM chains."""
        from cryptotax.parser.utils.transfers import extract_all_transfers

        tx = {"from": "0xabc", "to": "0xdef", "value": "1000000000000000000", "token_transfers": []}
        transfers = extract_all_transfers(tx, chain="ethereum")
        # Should find ETH native transfer
        eth_transfers = [t for t in transfers if t.symbol == "ETH"]
        assert len(eth_transfers) == 1
