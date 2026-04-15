"""Concurrent processor with thread pool, batching, and backpressure control.

Key technical challenges addressed:
1. High-concurrency: Thread pool executor for parallel trade processing
2. Backpressure: Queue-based flow control to prevent memory overflow
3. Batching: Batch submission to reduce thread context switching overhead
4. Graceful shutdown: Signal handling + executor shutdown with wait
"""

import logging
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from queue import Queue, Full
from typing import Callable

from src.models.trade import Trade
from src.models.result import ProcessResult
from src.core.processor import TradeProcessor

logger = logging.getLogger(__name__)


class ConcurrentProcessor:
    """High-concurrency trade processor with thread pool and backpressure control.

    Uses a bounded queue for backpressure: when the queue is full, producers
    block, preventing memory overflow under high load. Trades are submitted in
    batches for efficient processing.

    Args:
        processor: The trade processor to use for each trade.
        max_workers: Number of worker threads in the pool.
        batch_size: Number of trades per batch.
        queue_size: Maximum queue size for backpressure control.
    """

    def __init__(
        self,
        processor: TradeProcessor,
        max_workers: int = 10,
        batch_size: int = 100,
        queue_size: int = 1000,
    ):
        self._processor = processor
        self._max_workers = max_workers
        self._batch_size = batch_size
        self._queue: Queue[list[Trade]] = Queue(maxsize=queue_size)
        self._executor: ThreadPoolExecutor | None = None
        self._running = False
        self._futures: list[Future] = []

        # Statistics
        self._total_processed = 0
        self._total_errors = 0
        self._start_time: float = 0

    def start(self) -> None:
        """Start the processor thread pool."""
        if self._running:
            logger.warning("ConcurrentProcessor is already running")
            return

        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._running = True
        self._start_time = time.time()
        logger.info(
            "ConcurrentProcessor started: workers=%d, batch_size=%d, queue_size=%d",
            self._max_workers,
            self._batch_size,
            self._queue.maxsize,
        )

    def stop(self, timeout: float = 30.0) -> None:
        """Gracefully stop the processor.

        Waits for all submitted tasks to complete before shutting down.

        Args:
            timeout: Maximum time to wait for pending tasks.
        """
        if not self._running:
            return

        self._running = False

        # Wait for all futures to complete
        if self._futures:
            logger.info("Waiting for %d pending tasks...", len(self._futures))
            for future in as_completed(self._futures, timeout=timeout):
                try:
                    future.result()
                except Exception as e:
                    logger.error("Task failed during shutdown: %s", e)

        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("Thread pool shut down")

        elapsed = time.time() - self._start_time if self._start_time else 0
        throughput = self._total_processed / elapsed if elapsed > 0 else 0
        logger.info(
            "ConcurrentProcessor stopped: total=%d, errors=%d, "
            "throughput=%.0f trades/sec, elapsed=%.1fs",
            self._total_processed,
            self._total_errors,
            throughput,
            elapsed,
        )

    def submit(self, trades: list[Trade], block: bool = True, timeout: float = 5.0) -> bool:
        """Submit a batch of trades for processing.

        Args:
            trades: List of trades to process.
            block: If True, block when queue is full (backpressure).
            timeout: Max time to wait if blocking.

        Returns:
            True if the batch was accepted, False if the queue was full.
        """
        if not self._running:
            logger.error("Cannot submit: processor is not running")
            return False

        try:
            self._queue.put(trades, block=block, timeout=timeout)
            # Submit batch processing task
            future = self._executor.submit(self._process_batch_from_queue)
            self._futures.append(future)
            return True
        except Full:
            logger.warning("Queue full, batch rejected (size=%d)", len(trades))
            return False

    def submit_batch(self, trades: list[Trade]) -> list[list[ProcessResult]]:
        """Submit trades in pre-sized batches and collect all results.

        This is a synchronous API that blocks until all batches are processed.
        Useful for benchmarking and testing.

        Args:
            trades: All trades to process.

        Returns:
            List of result lists, one per batch.
        """
        if not self._running:
            self.start()

        all_results: list[list[ProcessResult]] = []
        futures: list[Future] = []

        for i in range(0, len(trades), self._batch_size):
            batch = trades[i : i + self._batch_size]
            future = self._executor.submit(self._processor.process_batch, batch)
            futures.append(future)

        for future in as_completed(futures):
            try:
                batch_results = future.result()
                all_results.append(batch_results)
                self._total_processed += len(batch_results)
            except Exception as e:
                self._total_errors += 1
                logger.error("Batch processing failed: %s", e)

        return all_results

    def _process_batch_from_queue(self) -> list[ProcessResult]:
        """Process a batch of trades from the queue.

        Returns:
            List of processing results.
        """
        try:
            trades = self._queue.get_nowait()
        except Exception:
            return []

        try:
            results = self._processor.process_batch(trades)
            self._total_processed += len(results)
            return results
        except Exception as e:
            self._total_errors += len(trades)
            logger.error("Batch processing error: %s", e)
            return []

    def setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def _signal_handler(signum, frame):
            logger.info("Received signal %d, initiating graceful shutdown...", signum)
            self.stop()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    @property
    def stats(self) -> dict[str, int | float]:
        """Get processing statistics."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        throughput = self._total_processed / elapsed if elapsed > 0 else 0
        return {
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "throughput_per_sec": round(throughput, 1),
            "queue_size": self._queue.qsize(),
            "elapsed_seconds": round(elapsed, 1),
            "running": self._running,
        }

    def __repr__(self) -> str:
        return (
            f"ConcurrentProcessor(workers={self._max_workers}, "
            f"batch_size={self._batch_size}, running={self._running})"
        )
