"""Abstract base class for subscribers (Observer pattern)."""

from abc import ABC, abstractmethod

from src.models.result import ProcessResult


class BaseSubscriber(ABC):
    """Abstract base class for all subscribers.

    Subscribers receive processing results and perform domain-specific
    actions (e.g., alerting, logging, strategy execution).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this subscriber."""
        ...

    @abstractmethod
    def on_result(self, result: ProcessResult) -> None:
        """Handle a processing result.

        Args:
            result: The processing result to handle.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
