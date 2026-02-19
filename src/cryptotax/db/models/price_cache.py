"""Price cache for historical token prices."""

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin


class PriceCache(TimestampMixin, Base):
    """Cached historical token price in USD. Keyed by (symbol, timestamp) at hourly granularity."""

    __tablename__ = "price_cache"
    __table_args__ = (UniqueConstraint("symbol", "timestamp", name="uq_price_cache_symbol_timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), index=True)
    timestamp: Mapped[int] = mapped_column(Integer, index=True)  # Unix epoch, rounded to hour
    price_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    source: Mapped[str] = mapped_column(String(50), default="coingecko")  # coingecko / cryptocompare / manual
