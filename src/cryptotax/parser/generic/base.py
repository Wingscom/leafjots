"""Base parser interfaces."""

from abc import ABC, abstractmethod

from cryptotax.domain.enums import EntryType
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits
from cryptotax.parser.utils.types import ParsedSplit, ParseResult


class BaseParser(ABC):
    """Minimal interface all parsers must implement."""

    PARSER_NAME: str = "BaseParser"
    ENTRY_TYPE: EntryType = EntryType.UNKNOWN

    @abstractmethod
    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        """Quick check: should this parser handle this TX?"""

    @abstractmethod
    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        """Parse TX and return ParseResult with splits + entry_type. Quantity MUST sum to 0 per symbol."""

    def _make_result(self, splits: list[ParsedSplit], entry_type: EntryType | None = None) -> ParseResult:
        """Helper to build ParseResult from splits and optional entry_type override."""
        return ParseResult(
            splits=splits,
            entry_type=(entry_type or self.ENTRY_TYPE).value,
            parser_name=self.PARSER_NAME,
        )


class EventDrivenParser(BaseParser):
    """Declarative event->handler mapping for protocol-specific parsers.

    Subclasses define:
        EVENT_HANDLERS: dict mapping event names to handler method names
        IGNORED_EVENTS: set of event names to silently skip
        PROTOCOL: str identifying the protocol for account mapping

    Handler method signature:
        def _handle_xxx(self, tx_data, event, context) -> list[ParsedSplit]
    """

    IGNORED_EVENTS: set[str] = set()
    EVENT_HANDLERS: dict[str, str] = {}
    PROTOCOL: str = "unknown"

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        splits: list[ParsedSplit] = []
        chain = tx_data.get("chain", "ethereum")

        # Gas fee first
        splits.extend(make_gas_splits(tx_data, chain, context))

        # Dispatch events to declared handlers
        for event in list(context.remaining_events()):
            if event.event in self.IGNORED_EVENTS:
                context.pop_event(event_name=event.event, address=event.address)
                continue

            handler_name = self.EVENT_HANDLERS.get(event.event)
            if handler_name is not None:
                popped = context.pop_event(event_name=event.event, address=event.address)
                if popped is not None:
                    handler_func = getattr(self, handler_name)
                    splits.extend(handler_func(tx_data, popped, context))

        return self._make_result(splits)
