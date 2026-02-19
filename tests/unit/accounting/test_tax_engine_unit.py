"""Unit tests for tax calculation logic — transfer tax + VND 20M exemption."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from cryptotax.accounting.tax_engine import TaxEngine, TAX_RATE, EXEMPTION_THRESHOLD_VND
from cryptotax.domain.enums.tax import TaxExemptionReason


class TestTransferTaxConstants:
    def test_tax_rate(self):
        assert TAX_RATE == Decimal("0.001")

    def test_exemption_threshold(self):
        assert EXEMPTION_THRESHOLD_VND == Decimal("20000000")


class TestCalculateTransferTax:
    def _make_splits(self, value_usd: str, symbol: str = "ETH", entry_type: str = "SWAP") -> list[dict]:
        return [{
            "account_type": "ASSET",
            "account_subtype": "native_asset",
            "symbol": symbol,
            "quantity": Decimal("-1"),
            "value_usd": Decimal(f"-{value_usd}"),
            "value_vnd": None,
            "timestamp": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "test",
            "entry_type": entry_type,
        }]

    def test_basic_tax_calculation(self):
        engine = TaxEngine.__new__(TaxEngine)
        splits = self._make_splits("100")  # $100 → 2,500,000 VND
        vnd_rate = Decimal("25000")
        transfers = engine._calculate_transfer_tax(splits, vnd_rate)

        assert len(transfers) == 1
        t = transfers[0]
        assert t.value_vnd == Decimal("2500000")
        assert t.tax_amount_vnd == Decimal("2500")  # 0.1% of 2.5M VND
        assert t.exemption_reason is None

    def test_large_transfer_exempt(self):
        engine = TaxEngine.__new__(TaxEngine)
        # $1000 → 25,000,000 VND > 20M → EXEMPT
        splits = self._make_splits("1000")
        vnd_rate = Decimal("25000")
        transfers = engine._calculate_transfer_tax(splits, vnd_rate)

        assert len(transfers) == 1
        t = transfers[0]
        assert t.value_vnd == Decimal("25000000")
        assert t.exemption_reason == TaxExemptionReason.BELOW_THRESHOLD
        assert t.tax_amount_vnd == Decimal(0)  # Exempt → no tax

    def test_gas_fee_exempt(self):
        engine = TaxEngine.__new__(TaxEngine)
        splits = self._make_splits("10", entry_type="GAS_FEE")
        vnd_rate = Decimal("25000")
        transfers = engine._calculate_transfer_tax(splits, vnd_rate)

        assert len(transfers) == 1
        assert transfers[0].exemption_reason == TaxExemptionReason.GAS_FEE
        assert transfers[0].tax_amount_vnd == Decimal(0)

    def test_positive_asset_not_taxed(self):
        """Only outflows (negative qty) are taxed."""
        engine = TaxEngine.__new__(TaxEngine)
        splits = [{
            "account_type": "ASSET",
            "account_subtype": "erc20_token",
            "symbol": "USDC",
            "quantity": Decimal("100"),
            "value_usd": Decimal("100"),
            "value_vnd": None,
            "timestamp": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "receive",
            "entry_type": "TRANSFER",
        }]
        vnd_rate = Decimal("25000")
        transfers = engine._calculate_transfer_tax(splits, vnd_rate)
        assert len(transfers) == 0

    def test_expense_account_not_taxed(self):
        """wallet_expense splits are not asset transfers."""
        engine = TaxEngine.__new__(TaxEngine)
        splits = [{
            "account_type": "EXPENSE",
            "account_subtype": "wallet_expense",
            "symbol": "ETH",
            "quantity": Decimal("-0.01"),
            "value_usd": Decimal("-20"),
            "value_vnd": None,
            "timestamp": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "gas",
            "entry_type": "GAS_FEE",
        }]
        vnd_rate = Decimal("25000")
        transfers = engine._calculate_transfer_tax(splits, vnd_rate)
        assert len(transfers) == 0
