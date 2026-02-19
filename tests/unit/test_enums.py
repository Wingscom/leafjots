from cryptotax.domain.enums import (
    AccountType,
    BalanceType,
    Chain,
    Currency,
    DataSource,
    EntryType,
    Exchange,
    GainsMode,
    ParseErrorType,
    Protocol,
    ScanProvider,
    TaxExemptionReason,
    TradeSide,
    TxStatus,
    WalletSyncStatus,
)


class TestEnumsAreStringMixin:
    """All enums use (str, Enum) so they serialize to strings in JSON and DB."""

    def test_account_type_is_str(self):
        assert isinstance(AccountType.ASSET, str)
        assert AccountType.ASSET == "ASSET"

    def test_chain_is_str(self):
        assert isinstance(Chain.ETHEREUM, str)
        assert Chain.ETHEREUM == "ethereum"

    def test_entry_type_is_str(self):
        assert isinstance(EntryType.SWAP, str)
        assert EntryType.SWAP == "SWAP"

    def test_tx_status_is_str(self):
        assert isinstance(TxStatus.LOADED, str)

    def test_trade_side_is_str(self):
        assert isinstance(TradeSide.BUY, str)


class TestEnumCounts:
    """Verify expected member counts to catch accidental additions/removals."""

    def test_account_type_has_4(self):
        assert len(AccountType) == 4

    def test_chain_has_8(self):
        assert len(Chain) == 8

    def test_entry_type_has_14(self):
        assert len(EntryType) == 14

    def test_parse_error_type_has_11(self):
        assert len(ParseErrorType) == 11

    def test_protocol_has_9(self):
        assert len(Protocol) == 9

    def test_tx_status_has_4(self):
        assert len(TxStatus) == 4

    def test_wallet_sync_status_has_4(self):
        assert len(WalletSyncStatus) == 4


class TestVietnamSpecificEnums:
    """Enums specific to Vietnam tax law."""

    def test_vnd_currency_exists(self):
        assert Currency.VND == "VND"

    def test_global_fifo_mode(self):
        assert GainsMode.GLOBAL_FIFO == "GLOBAL_FIFO"

    def test_tax_exemption_reasons(self):
        assert TaxExemptionReason.BELOW_THRESHOLD == "BELOW_THRESHOLD"
        assert TaxExemptionReason.SELF_TRANSFER == "SELF_TRANSFER"
        assert TaxExemptionReason.GAS_FEE == "GAS_FEE"

    def test_balance_type(self):
        assert BalanceType.SUPPLY == "supply"
        assert BalanceType.BORROW == "borrow"

    def test_data_source(self):
        assert DataSource.ONCHAIN == "ONCHAIN"
        assert DataSource.CEX_API == "CEX_API"

    def test_exchange(self):
        assert isinstance(Exchange.BINANCE, str)
        assert Exchange.BINANCE == "binance"

    def test_scan_provider(self):
        assert ScanProvider.ETHERSCAN == "ETHERSCAN"

    def test_trade_side(self):
        assert TradeSide.BUY == "BUY"
        assert TradeSide.SELL == "SELL"
