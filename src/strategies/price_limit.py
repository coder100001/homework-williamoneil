"""Price limit strategy - detects abnormal price movements."""

from src.models.trade import Trade
from src.strategies.base import BaseStrategy


class PriceLimitStrategy(BaseStrategy):
    """Detects trades with prices outside acceptable bounds.

    This rule triggers when a trade's price exceeds the configured maximum
    or falls below the configured minimum, indicating potential market
    anomalies or data errors.

    Args:
        max_price: Maximum acceptable price (default: 10000.0).
        min_price: Minimum acceptable price (default: 0.01).
    """

    def __init__(self, max_price: float = 10000.0, min_price: float = 0.01):
        self._max_price = max_price
        self._min_price = min_price

    @property
    def name(self) -> str:
        return "price_limit"

    def apply(self, trade: Trade) -> bool:
        """Check if trade price is outside acceptable bounds.

        Args:
            trade: The trade to evaluate.

        Returns:
            True if price is outside bounds (rule triggered).
        """
        return trade.price > self._max_price or trade.price < self._min_price

    @property
    def max_price(self) -> float:
        return self._max_price

    @property
    def min_price(self) -> float:
        return self._min_price
