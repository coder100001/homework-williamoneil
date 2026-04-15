"""Subscriber manager implementing the Observer pattern for result distribution."""

import logging
from typing import Protocol

from src.models.result import ProcessResult


class Subscriber(Protocol):
    """Protocol for subscribers that receive processing results."""

    @property
    def name(self) -> str:
        ...

    def on_result(self, result: ProcessResult) -> None:
        ...


class SubscriberManager:
    """Manages subscriber registration and result distribution (Observer pattern).

    Allows multiple subscribers to register for processing result notifications.
    When a result is published, all registered subscribers are notified.

    Example:
        manager = SubscriberManager()
        manager.subscribe(RiskSubscriber())
        manager.subscribe(MonitorSubscriber())

        manager.publish(result)  # Notifies all subscribers
    """

    def __init__(self):
        self._subscribers: dict[str, Subscriber] = {}
        self._logger = logging.getLogger(__name__)

    def subscribe(self, subscriber: Subscriber) -> None:
        """Register a subscriber to receive result notifications.

        Args:
            subscriber: The subscriber to register.
        """
        self._subscribers[subscriber.name] = subscriber
        self._logger.info("Subscriber registered: %s", subscriber.name)

    def unsubscribe(self, name: str) -> None:
        """Remove a subscriber by name.

        Args:
            name: The name of the subscriber to remove.
        """
        if name in self._subscribers:
            del self._subscribers[name]
            self._logger.info("Subscriber unsubscribed: %s", name)

    def publish(self, result: ProcessResult) -> None:
        """Publish a result to all registered subscribers.

        Each subscriber's on_result method is called. If one subscriber
        raises an exception, it is logged but does not affect other subscribers.

        Args:
            result: The processing result to publish.
        """
        for name, subscriber in self._subscribers.items():
            try:
                subscriber.on_result(result)
            except Exception as e:
                self._logger.error(
                    "Subscriber %s failed to handle result %s: %s",
                    name,
                    result.trade_id,
                    e,
                )

    def publish_batch(self, results: list[ProcessResult]) -> None:
        """Publish a batch of results to all subscribers.

        Args:
            results: List of processing results to publish.
        """
        for result in results:
            self.publish(result)

    @property
    def subscriber_names(self) -> list[str]:
        """List all registered subscriber names."""
        return list(self._subscribers.keys())

    def __repr__(self) -> str:
        return f"SubscriberManager(subscribers={list(self._subscribers.keys())})"
