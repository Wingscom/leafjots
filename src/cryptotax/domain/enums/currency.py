from enum import Enum


class Currency(str, Enum):
    """Reporting currencies. Vietnam tax requires dual USD + VND."""

    USD = "USD"
    VND = "VND"
