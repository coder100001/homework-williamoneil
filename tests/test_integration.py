"""Integration tests for end-to-end processing pipeline."""

from datetime import datetime

from src.models.trade import Trade
from src.models.result import ResultStatus
from src.core.processor import TradeProcessor, RuleEngine
from src.core.concurrent_processor import ConcurrentProcessor
from src.core.subscriber_manager import SubscriberManager
from src.data_source.mock_source import MockDataSource
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy
from src.subscribers.risk_subscriber import RiskSubscriber
from src.subscribers.monitor_subscriber import MonitorSubscriber


class TestEndToEndPipeline:
    """End-to-end integration tests."""

    def test_full_pipeline_normal_trades(self):
        """Test complete pipeline with normal trades."""
        # Build pipeline
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())

        processor = TradeProcessor(rule_engine=rule_engine)
        subscriber_mgr = SubscriberManager()
        risk = RiskSubscriber()
        monitor = MonitorSubscriber()
        subscriber_mgr.subscribe(risk)
        subscriber_mgr.subscribe(monitor)

        data_source = MockDataSource(use_pool=True, pool_size=500)

        # Generate and process
        trades = data_source.generate_batch(500)
        results = processor.process_batch(trades)

        # Distribute results
        subscriber_mgr.publish_batch(results)

        # Verify
        assert len(results) == 500
        assert all(r.is_success for r in results)
        assert monitor.stats["success_count"] == 500
        assert risk.stats["rejected_count"] == 0

    def test_full_pipeline_with_anomalies(self):
        """Test pipeline with anomalous trades mixed in."""
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy(max_price=1000.0))
        rule_engine.register(VolumeCheckStrategy(max_volume=10000))

        processor = TradeProcessor(rule_engine=rule_engine)
        subscriber_mgr = SubscriberManager()
        risk = RiskSubscriber()
        monitor = MonitorSubscriber()
        subscriber_mgr.subscribe(risk)
        subscriber_mgr.subscribe(monitor)

        data_source = MockDataSource(use_pool=True)

        # Normal trades
        normal_trades = data_source.generate_batch(100)
        # Anomalous trades
        anomalous_trades = [
            data_source.generate_anomalous_trade("price_spike"),
            data_source.generate_anomalous_trade("volume_spike"),
            data_source.generate_anomalous_trade("price_drop"),
        ]
        # Invalid trade
        invalid_trade = Trade(
            trade_id="INVALID",
            symbol="",
            price=-1.0,
            quantity=0,
            timestamp=datetime.now(),
        )

        all_trades = normal_trades + anomalous_trades + [invalid_trade]
        results = processor.process_batch(all_trades)
        subscriber_mgr.publish_batch(results)

        # Verify
        assert len(results) == 104
        # Invalid trade should be rejected
        rejected = [r for r in results if r.status == ResultStatus.REJECTED]
        assert len(rejected) >= 1

        # Some anomalous trades should trigger rules
        rule_triggered = [r for r in results if r.matched_rules]
        assert len(rule_triggered) >= 1

        # Risk subscriber should have alerts
        assert risk.stats["total_alerts"] >= 1

    def test_concurrent_pipeline(self):
        """Test full pipeline with concurrent processing."""
        rule_engine = RuleEngine()
        rule_engine.register(PriceLimitStrategy())
        rule_engine.register(VolumeCheckStrategy())

        processor = TradeProcessor(rule_engine=rule_engine)
        subscriber_mgr = SubscriberManager()
        risk = RiskSubscriber()
        monitor = MonitorSubscriber()
        subscriber_mgr.subscribe(risk)
        subscriber_mgr.subscribe(monitor)

        data_source = MockDataSource(use_pool=True, pool_size=5000)

        # Generate trades
        trades = data_source.generate_batch(2000)

        # Concurrent processing
        cp = ConcurrentProcessor(
            processor=processor,
            max_workers=4,
            batch_size=200,
        )
        cp.start()
        batch_results = cp.submit_batch(trades)
        cp.stop()

        # Distribute results
        for results in batch_results:
            subscriber_mgr.publish_batch(results)

        # Verify total processed
        total = sum(len(r) for r in batch_results)
        assert total == 2000

        # Monitor should have tracked all
        assert monitor.stats["total_processed"] == 2000

    def test_dynamic_rule_registration(self):
        """Test adding and removing rules at runtime."""
        rule_engine = RuleEngine()
        processor = TradeProcessor(rule_engine=rule_engine)

        trade = Trade(
            trade_id="T_DYNAMIC",
            symbol="TEST",
            price=99999.0,
            quantity=100,
            timestamp=datetime.now(),
        )

        # No rules - should succeed with no matched rules
        result1 = processor.process(trade)
        assert result1.is_success
        assert result1.matched_rules == []

        # Add price limit rule
        rule_engine.register(PriceLimitStrategy(max_price=10000.0))
        result2 = processor.process(trade)
        assert result2.is_success
        assert "price_limit" in result2.matched_rules

        # Remove rule
        rule_engine.unregister("price_limit")
        result3 = processor.process(trade)
        assert result3.is_success
        assert result3.matched_rules == []
