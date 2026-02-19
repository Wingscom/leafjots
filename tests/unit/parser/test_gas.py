from decimal import Decimal

from cryptotax.parser.utils.gas import calculate_gas_fee_decimal, calculate_gas_fee_wei, native_symbol


class TestNativeSymbol:
    def test_ethereum(self):
        assert native_symbol("ethereum") == "ETH"

    def test_polygon(self):
        assert native_symbol("polygon") == "MATIC"

    def test_bsc(self):
        assert native_symbol("bsc") == "BNB"

    def test_avalanche(self):
        assert native_symbol("avalanche") == "AVAX"

    def test_arbitrum(self):
        assert native_symbol("arbitrum") == "ETH"

    def test_unknown_chain_defaults_eth(self):
        assert native_symbol("unknown_chain") == "ETH"


class TestGasFeeCalculation:
    def test_basic_gas_fee(self):
        tx_data = {"gasUsed": "21000", "gasPrice": "20000000000"}
        assert calculate_gas_fee_wei(tx_data) == 21000 * 20000000000

    def test_gas_fee_decimal(self):
        tx_data = {"gasUsed": "21000", "gasPrice": "20000000000"}
        result = calculate_gas_fee_decimal(tx_data)
        expected = Decimal("21000") * Decimal("20000000000") / Decimal(10) ** 18
        assert result == expected

    def test_zero_gas(self):
        tx_data = {"gasUsed": "0", "gasPrice": "20000000000"}
        assert calculate_gas_fee_wei(tx_data) == 0
        assert calculate_gas_fee_decimal(tx_data) == Decimal(0)

    def test_missing_fields(self):
        assert calculate_gas_fee_wei({}) == 0
        assert calculate_gas_fee_decimal({}) == Decimal(0)

    def test_l2_l1_fee(self):
        tx_data = {
            "gasUsed": "100000",
            "gasPrice": "1000000",
            "l1Fee": "5000000000000",
        }
        expected = 100000 * 1000000 + 5000000000000
        assert calculate_gas_fee_wei(tx_data) == expected

    def test_l2_l1_fee_hex_string(self):
        tx_data = {
            "gasUsed": "100000",
            "gasPrice": "1000000",
            "l1Fee": "0x48c27395000",
        }
        l1_fee = int("0x48c27395000", 16)
        expected = 100000 * 1000000 + l1_fee
        assert calculate_gas_fee_wei(tx_data) == expected
