"""Unit tests for SubscriberManager and subscribers."""

from datetime import datetime

from src.models.trade import Trade
from src.models.result import ProcessResult, ResultStatus
from src.core.subscriber_manager import SubscriberManager
from src.subscribers.risk_subscriber import RiskSubscriber
from src.subscribers.monitor_subscriber import MonitorSubscriber


class TestSubscriberManager:
    """Tests for the SubscriberManager class."""

    def test_subscribe(self):
        """Test subscriber registration."""
        mgr = SubscriberManager()
        mgr.subscribe(RiskSubscriber())
        assert "risk_control" in mgr.subscriber_names

    def test_unsubscribe(self):
        """Test subscriber removal."""
        mgr = SubscriberManager()
        mgr.subscribe(RiskSubscriber())
        mgr.unsubscribe("risk_control")
        assert "risk_control" not in mgr.subscriber_names

    def test_publish_to_all_subscribers(self):
        """Test that publish notifies all subscribers."""
        mgr = SubscriberManager()
        risk = RiskSubscriber()
        monitor = MonitorSubscriber()
        mgr.subscribe(risk)
        mgr.subscribe(monitor)

        result = ProcessResult(
            trade_id="T001",
            status=ResultStatus.SUCCESS,
            matched_rules=["price_limit"],
        )
        mgr.publish(result)

        # Risk subscriber should have logged the rule trigger
        assert risk.stats["rule_triggered_count"] == 1
        # Monitor subscriber should have counted success
        assert monitor.stats["success_count"] == 1

    def test_publish_batch(self):
        """Test batch publishing."""
        mgr = SubscriberManager()
        monitor = MonitorSubscriber()
        mgr.subscribe(monitor)

        results = [
            ProcessResult(trade_id=f"T{i:03d}", status=ResultStatus.SUCCESS)
            for i in range(10)
        ]
        mgr.publish_batch(results)
        assert monitor.stats["success_count"] == 10


class TestRiskSubscriber:
    """Tests for the RiskSubscriber class."""

    def test_handles_rejected_trade(self):
        """Test risk subscriber handles rejected trades."""
        risk = RiskSubscriber()
        result = ProcessResult(
            trade_id="T001",
            status=ResultStatus.REJECTED,
            error_message="Invalid data",
        )
        risk.on_result(result)
        assert risk.stats["rejected_count"] == 1
        assert len(risk.alert_log) == 1

    def test_handles_rule_trigger(self):
        """Test risk subscriber handles rule triggers."""
        risk = RiskSubscriber()
        result = ProcessResult(
            trade_id="T001",
            status=ResultStatus.SUCCESS,
            matched_rules=["price_limit", "volume_check"],
        )
        risk.on_result(result)
        assert risk.stats["rule_triggered_count"] == 1


class TestMonitorSubscriber:
    """Tests for the MonitorSubscriber class."""

    def test_counts_success(self):
        """Test monitor counts successful results."""
        monitor = MonitorSubscriber()
        result = ProcessResult(trade_id="T001", status=ResultStatus.SUCCESS)
        monitor.on_result(result)
        assert monitor.stats["success_count"] == 1

    def test_counts_errors(self):
        """Test monitor counts error results."""
        monitor = MonitorSubscriber()
        result = ProcessResult(
            trade_id="T001",
            status=ResultStatus.ERROR,
            error_message="Test error",
        )
        monitor.on_result(result)
        assert monitor.stats["error_count"] == 1

    def test_throughput_calculation(self):
        """Test monitor calculates throughput."""
        monitor = MonitorSubscriber()
        for i in range(100):
            result = ProcessResult(trade_id=f"T{i:03d}", status=ResultStatus.SUCCESS)
            monitor.on_result(result)
        stats = monitor.stats
        assert stats["success_count"] == 100
        assert stats["throughput_per_sec"] > 0
