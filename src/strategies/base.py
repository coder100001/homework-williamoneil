"""Abstract base class for rule strategies."""

from abc import ABC, abstractmethod

from src.models.trade import Trade


class BaseStrategy(ABC):
    """Abstract base class for all rule strategies.

    Subclasses must implement `name` property and `apply` method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this strategy."""
        ...

    @abstractmethod
    def apply(self, trade: Trade) -> bool:
        """Apply the rule to a trade.

        Args:
            trade: The trade to evaluate.

        Returns:
            True if the rule is triggered (trade matches the condition).
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
