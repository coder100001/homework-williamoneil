"""Volume check strategy - detects unusual trading volumes."""

from src.models.trade import Trade
from src.strategies.base import BaseStrategy


class VolumeCheckStrategy(BaseStrategy):
    """Detects trades with unusually high or low volume.

    This rule triggers when the trade quantity exceeds the configured maximum
    or falls below the configured minimum, flagging potential market
    manipulation or execution errors.

    Args:
        max_volume: Maximum acceptable volume per trade (default: 1000000).
        min_volume: Minimum acceptable volume per trade (default: 1).
    """

    def __init__(self, max_volume: int = 1000000, min_volume: int = 1):
        self._max_volume = max_volume
        self._min_volume = min_volume

    @property
    def name(self) -> str:
        return "volume_check"

    def apply(self, trade: Trade) -> bool:
        """Check if trade volume is outside acceptable bounds.

        Args:
            trade: The trade to evaluate.

        Returns:
            True if volume is outside bounds (rule triggered).
        """
        return trade.quantity > self._max_volume or trade.quantity < self._min_volume

    @property
    def max_volume(self) -> int:
        return self._max_volume

    @property
    def min_volume(self) -> int:
        return self._min_volume
