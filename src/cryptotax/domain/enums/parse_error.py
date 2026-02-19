from enum import Enum


class ParseErrorType(str, Enum):
    """Categorized parse errors for the Error Dashboard."""

    TX_PARSE_ERROR = "TxParseError"
    INTERNAL_PARSE_ERROR = "InternalParseError"
    HANDLER_PARSE_ERROR = "HandlerParseError"
    UNHANDLED_FUNCTION_ERROR = "UnhandledFunctionError"
    UNKNOWN_CHAIN_ERROR = "UnknownChainError"
    UNKNOWN_CONTRACT_ERROR = "UnknownContractError"
    UNKNOWN_TOKEN_ERROR = "UnknownTokenError"
    UNKNOWN_TRANSACTION_INPUT_ERROR = "UnknownTransactionInputError"
    UNSUPPORTED_EVENTS_ERROR = "UnsupportedEventsError"
    MISSING_PRICE_ERROR = "MissingPriceError"
    BALANCE_ERROR = "BalanceError"
