"""Performance benchmark tests."""

import time

from src.core.processor import TradeProcessor, RuleEngine
from src.core.concurrent_processor import ConcurrentProcessor
from src.data_source.mock_source import MockDataSource
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy


class TestBenchmark:
    """Performance benchmark tests for the processing engine."""

    def test_single_thread_throughput(self, benchmark):
        """Benchmark single-threaded processing throughput."""
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())
        processor = TradeProcessor(rule_engine=rule_engine)
        data_source = MockDataSource(use_pool=True, pool_size=1000)
        trades = data_source.generate_batch(1000)

        def process_all():
            return processor.process_batch(trades)

        result = benchmark(process_all)
        assert len(result) == 1000

    def test_concurrent_throughput(self, benchmark):
        """Benchmark concurrent processing throughput."""
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())
        processor = TradeProcessor(rule_engine=rule_engine)
        data_source = MockDataSource(use_pool=True, pool_size=5000)

        def process_concurrent():
            trades = data_source.generate_batch(1000)
            cp = ConcurrentProcessor(
                processor=processor,
                max_workers=4,
                batch_size=100,
            )
            cp.start()
            results = cp.submit_batch(trades)
            cp.stop()
            return results

        result = benchmark(process_concurrent)
        total = sum(len(r) for r in result)
        assert total == 1000

    def test_data_generation_throughput(self, benchmark):
        """Benchmark mock data generation throughput."""
        data_source = MockDataSource(use_pool=True, pool_size=5000)

        def generate():
            return data_source.generate_batch(1000)

        result = benchmark(generate)
        assert len(result) == 1000

    def test_object_pool_performance(self, benchmark):
        """Benchmark object pool vs. raw creation performance."""
        from src.utils.pool import ObjectPool
        from src.models.trade import Trade

        pool = ObjectPool(factory=Trade, pool_size=1000, reset_fn=lambda t: t.reset())

        def pool_acquire_release():
            for _ in range(1000):
                obj = pool.acquire()
                obj.trade_id = "T001"
                pool.release(obj)

        benchmark(pool_acquire_release)

    def test_rule_engine_evaluation(self, benchmark):
        """Benchmark rule engine evaluation speed."""
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())
        data_source = MockDataSource(use_pool=True)
        trades = data_source.generate_batch(1000)

        def evaluate_all():
            for trade in trades:
                rule_engine.evaluate(trade)

        benchmark(evaluate_all)

    def test_scaling_with_workers(self):
        """Test how throughput scales with worker count."""
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())
        processor = TradeProcessor(rule_engine=rule_engine)
        data_source = MockDataSource(use_pool=True, pool_size=10000)
        trades = data_source.generate_batch(5000)

        results = {}
        for workers in [1, 2, 4, 8]:
            cp = ConcurrentProcessor(
                processor=processor,
                max_workers=workers,
                batch_size=500,
            )
            cp.start()
            start = time.time()
            cp.submit_batch(trades)
            elapsed = time.time() - start
            cp.stop()

            throughput = 5000 / elapsed if elapsed > 0 else 0
            results[workers] = throughput

        # Basic sanity: more workers should generally not be much slower
        # (may not always be faster due to GIL and overhead)
        for workers, throughput in results.items():
            assert throughput > 0, f"Workers={workers} had zero throughput"
