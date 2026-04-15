"""Monitor subscriber - collects metrics and system health data."""

import logging
import time

from src.models.result import ProcessResult, ResultStatus
from src.subscribers.base import BaseSubscriber


class MonitorSubscriber(BaseSubscriber):
    """Collects processing metrics for system health monitoring.

    Tracks throughput, latency percentiles, and error rates.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"monitor_subscriber")
        self._success_count = 0
        self._error_count = 0
        self._rejected_count = 0
        self._start_time = time.time()
        self._latencies: list[float] = []

    @property
    def name(self) -> str:
        return "monitor"

    def on_result(self, result: ProcessResult) -> None:
        """Collect metrics from processing results.

        Args:
            result: The processing result to collect metrics from.
        """
        if result.status == ResultStatus.SUCCESS:
            self._success_count += 1
        elif result.status == ResultStatus.REJECTED:
            self._rejected_count += 1
        elif result.status == ResultStatus.ERROR:
            self._error_count += 1

        self._logger.debug(
            "Monitor: %s status=%s rules=%s",
            result.trade_id,
            result.status.value,
            result.matched_rules,
        )

    @property
    def stats(self) -> dict:
        """Get monitoring statistics."""
        elapsed = time.time() - self._start_time
        total = self._success_count + self._error_count + self._rejected_count
        throughput = total / elapsed if elapsed > 0 else 0

        return {
            "success_count": self._success_count,
            "error_count": self._error_count,
            "rejected_count": self._rejected_count,
            "total_processed": total,
            "throughput_per_sec": round(throughput, 1),
            "elapsed_seconds": round(elapsed, 1),
        }
