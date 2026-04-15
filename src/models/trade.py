"""Trade data model with validation and reset support."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Trade:
    """Represents a single market trade event.

    Attributes:
        trade_id: Unique identifier for the trade.
        symbol: Ticker symbol (e.g., 'AAPL', 'GOOGL').
        price: Trade price per share, must be positive.
        quantity: Number of shares traded, must be positive.
        timestamp: When the trade occurred.
        exchange: Source exchange identifier (optional).
    """

    trade_id: str = ""
    symbol: str = ""
    price: float = 0.0
    quantity: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    exchange: str = ""

    def validate(self) -> bool:
        """Validate trade data integrity.

        Returns:
            True if all required fields are valid, False otherwise.
        """
        return (
            len(self.trade_id) > 0
            and len(self.symbol) > 0
            and self.price > 0
            and self.quantity > 0
        )

    def reset(self) -> None:
        """Reset all fields to default values for object reuse."""
        self.trade_id = ""
        self.symbol = ""
        self.price = 0.0
        self.quantity = 0
        self.timestamp = datetime.now()
        self.exchange = ""

    def __repr__(self) -> str:
        return (
            f"Trade(id={self.trade_id}, symbol={self.symbol}, "
            f"price={self.price}, qty={self.quantity})"
        )
