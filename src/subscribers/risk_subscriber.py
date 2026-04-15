"""Risk control subscriber - monitors for risk events."""

import logging

from src.models.result import ProcessResult, ResultStatus
from src.subscribers.base import BaseSubscriber


class RiskSubscriber(BaseSubscriber):
    """Monitors processing results for risk events and triggers alerts.

    Tracks rejected trades and trades with triggered rules for risk analysis.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"risk_subscriber")
        self._rejected_count = 0
        self._rule_triggered_count = 0
        self._alert_log: list[str] = []

    @property
    def name(self) -> str:
        return "risk_control"

    def on_result(self, result: ProcessResult) -> None:
        """Process result for risk monitoring.

        Args:
            result: The processing result to evaluate.
        """
        if result.status == ResultStatus.REJECTED:
            self._rejected_count += 1
            self._alert_log.append(
                f"REJECTED: {result.trade_id} - {result.error_message}"
            )
            self._logger.warning(
                "Risk alert: Trade %s rejected - %s",
                result.trade_id,
                result.error_message,
            )

        if result.matched_rules:
            self._rule_triggered_count += 1
            rules_str = ", ".join(result.matched_rules)
            self._alert_log.append(
                f"RULES: {result.trade_id} - [{rules_str}]"
            )
            self._logger.info(
                "Risk event: Trade %s triggered rules: %s",
                result.trade_id,
                rules_str,
            )

    @property
    def stats(self) -> dict[str, int]:
        """Get risk monitoring statistics."""
        return {
            "rejected_count": self._rejected_count,
            "rule_triggered_count": self._rule_triggered_count,
            "total_alerts": len(self._alert_log),
        }

    @property
    def alert_log(self) -> list[str]:
        """Get all recorded alerts."""
        return self._alert_log.copy()
