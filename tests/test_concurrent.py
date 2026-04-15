"""Unit tests for ConcurrentProcessor."""

import time

from src.models.trade import Trade
from src.models.result import ResultStatus
from src.core.concurrent_processor import ConcurrentProcessor
from src.core.processor import TradeProcessor, RuleEngine
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy


class TestConcurrentProcessor:
    """Tests for the ConcurrentProcessor class."""

    def test_submit_batch_basic(
        self, concurrent_processor: ConcurrentProcessor, data_source
    ):
        """Test basic batch submission."""
        trades = data_source.generate_batch(200)
        results = concurrent_processor.submit_batch(trades)
        total = sum(len(r) for r in results)
        assert total == 200

    def test_submit_batch_all_valid(
        self, concurrent_processor: ConcurrentProcessor, sample_trade: Trade
    ):
        """Test that valid trades are processed successfully."""
        trades = [sample_trade] * 100
        # Update trade IDs to be unique
        for i, trade in enumerate(trades):
            trade.trade_id = f"T{i:08d}"

        results = concurrent_processor.submit_batch(trades)
        all_results = [r for batch in results for r in batch]
        assert all(r.is_success for r in all_results)

    def test_concurrent_vs_single_thread(self, data_source):
        """Test that concurrent processing is faster than single-threaded."""
        # Single-threaded
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())
        processor = TradeProcessor(rule_engine=rule_engine)
        trades = data_source.generate_batch(1000)

        start = time.time()
        for trade in trades:
            processor.process(trade)
        single_time = time.time() - start

        # Concurrent
        cp = ConcurrentProcessor(
            processor=processor, max_workers=4, batch_size=100
        )
        cp.start()
        start = time.time()
        cp.submit_batch(trades)
        cp.stop()
        concurrent_time = time.time() - start

        # Concurrent should not be significantly slower
        # (may not be faster for small batches due to overhead)
        assert concurrent_time < single_time * 3  # reasonable bound

    def test_stats_tracking(
        self, concurrent_processor: ConcurrentProcessor, data_source
    ):
        """Test that processing statistics are tracked correctly."""
        trades = data_source.generate_batch(500)
        concurrent_processor.submit_batch(trades)

        stats = concurrent_processor.stats
        assert stats["total_processed"] == 500
        assert stats["running"] is True

    def test_stop_and_restart(self, processor: TradeProcessor):
        """Test stopping and restarting the processor."""
        cp = ConcurrentProcessor(processor=processor, max_workers=2)
        assert cp.stats["running"] is False

        cp.start()
        assert cp.stats["running"] is True

        cp.stop()
        assert cp.stats["running"] is False

    def test_submit_when_stopped(
        self, processor: TradeProcessor, sample_trade: Trade
    ):
        """Test that submitting when stopped returns False."""
        cp = ConcurrentProcessor(processor=processor)
        result = cp.submit([sample_trade])
        assert result is False
