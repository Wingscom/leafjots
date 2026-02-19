"""TransactionContext — mutable working set for parsing one transaction."""

from collections import defaultdict
from decimal import Decimal

from cryptotax.parser.utils.types import EventData, RawTransfer


class TransactionContext:
    """Mutable context that parsers consume transfers from during parsing."""

    def __init__(
        self,
        transfers: list[RawTransfer],
        wallet_addresses: set[str],
        events: list[EventData] | None = None,
    ) -> None:
        self._transfers: list[RawTransfer] = list(transfers)
        self._wallet_addresses: set[str] = {a.lower() for a in wallet_addresses}
        self._events: list[EventData] = list(events or [])

    def is_wallet(self, address: str) -> bool:
        return address.lower() in self._wallet_addresses

    def pop_transfer(
        self,
        *,
        from_address: str | None = None,
        to_address: str | None = None,
        token_address: str | None = ...,  # type: ignore[assignment]  # sentinel
        transfer_type: str | None = None,
    ) -> RawTransfer | None:
        """Find and remove the first matching transfer. Returns None if not found."""
        for i, t in enumerate(self._transfers):
            if from_address is not None and t.from_address.lower() != from_address.lower():
                continue
            if to_address is not None and t.to_address.lower() != to_address.lower():
                continue
            if token_address is not ... and t.token_address != token_address:
                continue
            if transfer_type is not None and t.transfer_type != transfer_type:
                continue
            return self._transfers.pop(i)
        return None

    def peek_transfers(
        self,
        *,
        from_address: str | None = None,
        to_address: str | None = None,
        token_address: str | None = ...,  # type: ignore[assignment]
    ) -> list[RawTransfer]:
        """Return matching transfers without consuming them."""
        result = []
        for t in self._transfers:
            if from_address is not None and t.from_address.lower() != from_address.lower():
                continue
            if to_address is not None and t.to_address.lower() != to_address.lower():
                continue
            if token_address is not ... and t.token_address != token_address:
                continue
            result.append(t)
        return result

    def remaining_transfers(self) -> list[RawTransfer]:
        """Unconsumed transfers — potential unknowns."""
        return list(self._transfers)

    def net_flows(self) -> dict[str, dict[str, Decimal]]:
        """Net token flows per address. {address: {symbol: net_quantity}}.

        Positive = received, negative = sent. Only includes wallet addresses.
        """
        flows: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for t in self._transfers:
            qty = Decimal(str(t.value)) / Decimal(10) ** t.decimals
            from_lower = t.from_address.lower()
            to_lower = t.to_address.lower()
            if self.is_wallet(from_lower):
                flows[from_lower][t.symbol] -= qty
            if self.is_wallet(to_lower):
                flows[to_lower][t.symbol] += qty
        return dict(flows)

    # --- Event support (for EventDrivenParser) ---

    def pop_event(
        self,
        *,
        event_name: str,
        address: str | None = None,
    ) -> EventData | None:
        """Find and remove the first matching event."""
        for i, e in enumerate(self._events):
            if e.event != event_name:
                continue
            if address is not None and e.address.lower() != address.lower():
                continue
            return self._events.pop(i)
        return None

    def filter_events(self, *, event_name: str) -> list[EventData]:
        """Return all events matching name without consuming them."""
        return [e for e in self._events if e.event == event_name]

    def remaining_events(self) -> list[EventData]:
        """Unconsumed events."""
        return list(self._events)
