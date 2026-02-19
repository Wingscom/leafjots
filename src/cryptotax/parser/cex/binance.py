"""Binance CEX parsers — Trade, Deposit, Withdrawal."""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import ParsedSplit, ParseResult


def _parse_pair(symbol: str) -> tuple[str, str]:
    """Split a Binance trading pair like 'BTCUSDT' into ('BTC', 'USDT')."""
    known_quotes = ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB", "TUSD", "DAI", "FDUSD", "EUR", "TRY", "GBP"]
    for quote in known_quotes:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            base = symbol[: -len(quote)]
            return base, quote
    if len(symbol) > 3:
        return symbol[:-3], symbol[-3:]
    return symbol, "UNKNOWN"


class BinanceTradeParser(BaseParser):
    """Parse Binance spot trade into balanced journal splits."""

    PARSER_NAME = "BinanceTradeParser"
    ENTRY_TYPE = EntryType.SWAP

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        chain = tx_data.get("chain", "")
        has_trade_fields = "qty" in tx_data and "quoteQty" in tx_data
        return chain == "binance" and has_trade_fields

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        symbol_pair = tx_data.get("symbol", "")
        base_asset, quote_asset = _parse_pair(symbol_pair)
        is_buyer = tx_data.get("isBuyer", tx_data.get("side", "").upper() == "BUY")

        qty = Decimal(str(tx_data.get("qty", "0")))
        quote_qty = Decimal(str(tx_data.get("quoteQty", "0")))
        commission = Decimal(str(tx_data.get("commission", "0")))
        commission_asset = tx_data.get("commissionAsset", "")

        splits: list[ParsedSplit] = []

        if is_buyer:
            splits.append(ParsedSplit(account_subtype="cex_asset", symbol=base_asset, quantity=qty))
            splits.append(ParsedSplit(account_subtype="cex_asset", symbol=quote_asset, quantity=-quote_qty))
        else:
            splits.append(ParsedSplit(account_subtype="cex_asset", symbol=base_asset, quantity=-qty))
            splits.append(ParsedSplit(account_subtype="cex_asset", symbol=quote_asset, quantity=quote_qty))

        if commission > 0 and commission_asset:
            splits.append(ParsedSplit(account_subtype="cex_asset", symbol=commission_asset, quantity=-commission))
            splits.append(ParsedSplit(account_subtype="wallet_expense", symbol=commission_asset, quantity=commission))

        return self._make_result(splits)


class BinanceDepositParser(BaseParser):
    """Parse Binance deposit into balanced journal splits."""

    PARSER_NAME = "BinanceDepositParser"
    ENTRY_TYPE = EntryType.DEPOSIT

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        chain = tx_data.get("chain", "")
        has_deposit = "depositOrderId" in tx_data or ("txId" in tx_data and "insertTime" in tx_data)
        return chain == "binance" and has_deposit

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        coin = tx_data.get("coin", tx_data.get("asset", "UNKNOWN"))
        amount = Decimal(str(tx_data.get("amount", "0")))

        splits = [
            ParsedSplit(account_subtype="cex_asset", symbol=coin, quantity=amount),
            ParsedSplit(
                account_subtype="external_transfer", symbol=coin, quantity=-amount,
                account_params={"ext_address": tx_data.get("address", "external")},
            ),
        ]
        return self._make_result(splits)


class BinanceWithdrawalParser(BaseParser):
    """Parse Binance withdrawal into balanced journal splits."""

    PARSER_NAME = "BinanceWithdrawalParser"
    ENTRY_TYPE = EntryType.WITHDRAWAL

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        chain = tx_data.get("chain", "")
        has_withdrawal = "withdrawOrderId" in tx_data or ("applyTime" in tx_data and "transactionFee" in tx_data)
        return chain == "binance" and has_withdrawal

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        coin = tx_data.get("coin", tx_data.get("asset", "UNKNOWN"))
        amount = Decimal(str(tx_data.get("amount", "0")))
        fee = Decimal(str(tx_data.get("transactionFee", "0")))

        net_amount = amount - fee

        splits = [
            ParsedSplit(account_subtype="cex_asset", symbol=coin, quantity=-amount),
            ParsedSplit(
                account_subtype="external_transfer", symbol=coin, quantity=net_amount,
                account_params={"ext_address": tx_data.get("address", "external")},
            ),
        ]

        if fee > 0:
            splits.append(ParsedSplit(account_subtype="wallet_expense", symbol=coin, quantity=fee))

        return self._make_result(splits)
