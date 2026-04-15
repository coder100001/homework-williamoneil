"""Real-time Trade Data Processing Engine - Main Entry Point.

Assembles the complete processing pipeline:
    MockDataSource → ConcurrentProcessor → RuleEngine → SubscriberManager → Subscribers

Usage:
    python src/main.py                          # Default: process 10000 trades
    python src/main.py --count 50000            # Custom trade count
    python src/main.py --workers 20             # Custom worker count
    python src/main.py --mode benchmark         # Benchmark mode
    python src/main.py --mode demo              # Demo with detailed output
"""

import argparse
import os
import sys
import time

from src.core.processor import TradeProcessor, RuleEngine
from src.core.concurrent_processor import ConcurrentProcessor
from src.core.subscriber_manager import SubscriberManager
from src.data_source.mock_source import MockDataSource
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy
from src.subscribers.risk_subscriber import RiskSubscriber
from src.subscribers.monitor_subscriber import MonitorSubscriber
from src.utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Real-time Trade Data Processing Engine POC"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=int(os.environ.get("TRADE_COUNT", "10000")),
        help="Number of trades to process (default: 10000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("WORKERS", "10")),
        help="Number of worker threads (default: 10)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("BATCH_SIZE", "100")),
        help="Batch size for concurrent processing (default: 100)",
    )
    parser.add_argument(
        "--queue-size",
        type=int,
        default=int(os.environ.get("QUEUE_SIZE", "1000")),
        help="Queue size for backpressure control (default: 1000)",
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "benchmark", "stress"],
        default="demo",
        help="Execution mode (default: demo)",
    )
    return parser.parse_args()


def build_pipeline(
    workers: int = 10,
    batch_size: int = 100,
    queue_size: int = 1000,
) -> tuple[TradeProcessor, ConcurrentProcessor, SubscriberManager, MockDataSource]:
    """Build the complete processing pipeline.

    Returns:
        Tuple of (processor, concurrent_processor, subscriber_manager, data_source)
    """
    # 1. Rule Engine with strategies
    rule_engine = RuleEngine()
    rule_engine.register(PriceLimitStrategy(max_price=10000.0, min_price=0.01))
    rule_engine.register(VolumeCheckStrategy(max_volume=1000000, min_volume=1))

    # 2. Trade Processor
    processor = TradeProcessor(rule_engine=rule_engine)

    # 3. Concurrent Processor
    concurrent_proc = ConcurrentProcessor(
        processor=processor,
        max_workers=workers,
        batch_size=batch_size,
        queue_size=queue_size,
    )

    # 4. Subscriber Manager with subscribers
    subscriber_mgr = SubscriberManager()
    subscriber_mgr.subscribe(RiskSubscriber())
    subscriber_mgr.subscribe(MonitorSubscriber())

    # 5. Mock Data Source with object pool
    data_source = MockDataSource(
        use_pool=True,
        pool_size=batch_size * workers,
    )

    return processor, concurrent_proc, subscriber_mgr, data_source


def run_demo(args: argparse.Namespace) -> None:
    """Run in demo mode with detailed output."""
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("Real-time Trade Data Processing Engine - Demo Mode")
    logger.info("=" * 60)

    processor, concurrent_proc, subscriber_mgr, data_source = build_pipeline(
        workers=args.workers,
        batch_size=args.batch_size,
        queue_size=args.queue_size,
    )

    logger.info("Configuration:")
    logger.info("  Trade count: %d", args.count)
    logger.info("  Workers: %d", args.workers)
    logger.info("  Batch size: %d", args.batch_size)
    logger.info("  Queue size: %d", args.queue_size)
    logger.info("  Strategies: %s", processor.rule_engine.strategy_names)
    logger.info("  Subscribers: %s", subscriber_mgr.subscriber_names)
    logger.info("")

    # Generate trades
    logger.info("Generating %d trades...", args.count)
    start_time = time.time()
    trades = data_source.generate_batch(args.count)
    gen_time = time.time() - start_time
    logger.info("Generated %d trades in %.3fs", args.count, gen_time)
    logger.info("")

    # Process trades concurrently
    logger.info("Starting concurrent processing...")
    concurrent_proc.start()
    concurrent_proc.setup_signal_handlers()

    process_start = time.time()
    batch_results = concurrent_proc.submit_batch(trades)

    # Distribute results to subscribers
    for results in batch_results:
        subscriber_mgr.publish_batch(results)

    process_time = time.time() - process_start
    concurrent_proc.stop()

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Processing Summary")
    logger.info("=" * 60)

    total_results = sum(len(r) for r in batch_results)
    success_count = sum(
        1 for r in batch_results for res in r if res.is_success
    )
    rejected_count = sum(
        1 for r in batch_results for res in r
        if res.status.value == "rejected"
    )
    error_count = sum(
        1 for r in batch_results for res in r
        if res.status.value == "error"
    )
    rule_triggered = sum(
        1 for r in batch_results for res in r if res.matched_rules
    )

    throughput = total_results / process_time if process_time > 0 else 0

    logger.info("  Total processed: %d", total_results)
    logger.info("  Successful: %d", success_count)
    logger.info("  Rejected: %d", rejected_count)
    logger.info("  Errors: %d", error_count)
    logger.info("  Rules triggered: %d", rule_triggered)
    logger.info("  Processing time: %.3fs", process_time)
    logger.info("  Throughput: %.0f trades/sec", throughput)
    logger.info("  Pool stats: %s", data_source.pool_stats)

    # Subscriber stats
    for name in subscriber_mgr.subscriber_names:
        subscriber = subscriber_mgr._subscribers[name]
        if hasattr(subscriber, "stats"):
            logger.info("  %s stats: %s", name, subscriber.stats)


def run_benchmark(args: argparse.Namespace) -> None:
    """Run in benchmark mode for performance measurement."""
    logger = setup_logger(level="WARNING")
    print("=" * 60)
    print("Benchmark Mode - Performance Measurement")
    print("=" * 60)

    configs = [
        (1, 100),     # Single thread
        (4, 100),     # 4 workers
        (10, 100),    # 10 workers
        (10, 500),    # 10 workers, larger batch
    ]

    for workers, batch_size in configs:
        processor, concurrent_proc, _, data_source = build_pipeline(
            workers=workers,
            batch_size=batch_size,
        )

        trades = data_source.generate_batch(args.count)

        concurrent_proc.start()
        start = time.time()
        concurrent_proc.submit_batch(trades)
        elapsed = time.time() - start
        concurrent_proc.stop()

        throughput = args.count / elapsed if elapsed > 0 else 0
        print(
            f"  workers={workers}, batch={batch_size}: "
            f"{elapsed:.3f}s, {throughput:.0f} trades/sec"
        )

        data_source.release_batch(trades)


def run_stress(args: argparse.Namespace) -> None:
    """Run stress test with backpressure."""
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("Stress Test Mode - Backpressure Validation")
    logger.info("=" * 60)

    # Small queue to trigger backpressure
    processor, concurrent_proc, subscriber_mgr, data_source = build_pipeline(
        workers=args.workers,
        batch_size=args.batch_size,
        queue_size=10,  # Very small queue
    )

    large_count = args.count * 5
    logger.info("Generating %d trades with queue_size=10...", large_count)

    trades = data_source.generate_batch(large_count)

    concurrent_proc.start()
    start = time.time()

    accepted = 0
    rejected = 0
    for i in range(0, len(trades), args.batch_size):
        batch = trades[i : i + args.batch_size]
        if concurrent_proc.submit(batch, block=True, timeout=1.0):
            accepted += len(batch)
        else:
            rejected += len(batch)

    # Wait for processing
    time.sleep(2)
    concurrent_proc.stop()
    elapsed = time.time() - start

    logger.info("Stress test results:")
    logger.info("  Accepted: %d", accepted)
    logger.info("  Rejected (backpressure): %d", rejected)
    logger.info("  Elapsed: %.3fs", elapsed)
    logger.info("  Processor stats: %s", concurrent_proc.stats)


def main():
    """Main entry point."""
    args = parse_args()

    if args.mode == "demo":
        run_demo(args)
    elif args.mode == "benchmark":
        run_benchmark(args)
    elif args.mode == "stress":
        run_stress(args)


if __name__ == "__main__":
    main()
