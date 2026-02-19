"""FIFO lot matching — pure functions, no DB dependency.

Implements Vietnam's GLOBAL_FIFO requirement: oldest buy lot consumed first.
"""

from collections import deque
from decimal import Decimal

from cryptotax.domain.enums.tax import TradeSide
from cryptotax.domain.models.tax import ClosedLot, OpenLot, Trade


def fifo_match(trades: list[Trade]) -> tuple[list[ClosedLot], list[OpenLot]]:
    """Match trades using FIFO for a single symbol.

    Args:
        trades: Sorted by timestamp, all for the same symbol.

    Returns:
        (closed_lots, remaining_open_lots)
    """
    buy_queue: deque[OpenLot] = deque()
    closed_lots: list[ClosedLot] = []

    for trade in trades:
        if trade.side == TradeSide.BUY:
            buy_queue.append(OpenLot(
                symbol=trade.symbol,
                buy_trade=trade,
                remaining_quantity=trade.quantity,
                cost_basis_per_unit_usd=trade.price_usd,
            ))
        elif trade.side == TradeSide.SELL:
            sell_remaining = trade.quantity
            while sell_remaining > 0 and buy_queue:
                front = buy_queue[0]
                match_qty = min(sell_remaining, front.remaining_quantity)

                cost_basis = match_qty * front.cost_basis_per_unit_usd
                proceeds = match_qty * trade.price_usd
                holding_days = (trade.timestamp - front.buy_trade.timestamp).days

                closed_lots.append(ClosedLot(
                    symbol=trade.symbol,
                    buy_trade=front.buy_trade,
                    sell_trade=trade,
                    quantity=match_qty,
                    cost_basis_usd=cost_basis,
                    proceeds_usd=proceeds,
                    gain_usd=proceeds - cost_basis,
                    holding_days=holding_days,
                ))

                front.remaining_quantity -= match_qty
                sell_remaining -= match_qty

                if front.remaining_quantity <= 0:
                    buy_queue.popleft()

    # Remaining open lots
    open_lots = [lot for lot in buy_queue if lot.remaining_quantity > 0]
    return closed_lots, open_lots


def trades_from_splits(
    splits_with_accounts: list[dict],
    symbol: str,
) -> list[Trade]:
    """Convert journal split data into Trade events for a single symbol.

    Each dict in splits_with_accounts should have:
        - account_type: str (ASSET, LIABILITY, etc.)
        - account_subtype: str
        - symbol: str
        - quantity: Decimal
        - value_usd: Decimal | None
        - timestamp: datetime
        - journal_entry_id: UUID
        - description: str

    Positive quantity on ASSET account = BUY, Negative = SELL.
    Only processes ASSET-type accounts (native_asset, erc20_token, protocol_asset).
    """
    trades: list[Trade] = []
    asset_subtypes = {"native_asset", "erc20_token", "protocol_asset"}

    for s in splits_with_accounts:
        if s["symbol"] != symbol:
            continue
        if s.get("account_subtype") not in asset_subtypes:
            continue

        qty = s["quantity"]
        if qty == Decimal(0):
            continue

        value_usd = s.get("value_usd") or Decimal(0)
        abs_qty = abs(qty)
        price_usd = abs(value_usd) / abs_qty if abs_qty > 0 else Decimal(0)

        trades.append(Trade(
            symbol=symbol,
            side=TradeSide.BUY if qty > 0 else TradeSide.SELL,
            quantity=abs_qty,
            price_usd=price_usd,
            value_usd=abs(value_usd),
            timestamp=s["timestamp"],
            journal_entry_id=s["journal_entry_id"],
            description=s.get("description", ""),
        ))

    trades.sort(key=lambda t: t.timestamp)
    return trades
