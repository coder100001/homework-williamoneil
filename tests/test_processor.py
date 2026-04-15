"""Unit tests for TradeProcessor."""

from datetime import datetime

from src.models.trade import Trade
from src.models.result import ResultStatus
from src.core.processor import TradeProcessor, RuleEngine
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy


class TestTradeProcessor:
    """Tests for the TradeProcessor class."""

    def test_process_valid_trade(self, processor: TradeProcessor, sample_trade: Trade):
        """Test processing a valid trade."""
        result = processor.process(sample_trade)
        assert result.trade_id == "T00000001"
        assert result.status == ResultStatus.SUCCESS
        assert result.is_success is True

    def test_process_invalid_trade(self, processor: TradeProcessor, invalid_trade: Trade):
        """Test processing an invalid trade results in rejection."""
        result = processor.process(invalid_trade)
        assert result.trade_id == "T00000002"
        assert result.status == ResultStatus.REJECTED
        assert result.error_message is not None

    def test_process_anomalous_price_triggers_rule(
        self, processor: TradeProcessor, anomalous_price_trade: Trade
    ):
        """Test that anomalous price triggers the price_limit rule."""
        result = processor.process(anomalous_price_trade)
        assert result.is_success is True
        assert "price_limit" in result.matched_rules

    def test_process_anomalous_volume_triggers_rule(
        self, processor: TradeProcessor, anomalous_volume_trade: Trade
    ):
        """Test that anomalous volume triggers the volume_check rule."""
        result = processor.process(anomalous_volume_trade)
        assert result.is_success is True
        assert "volume_check" in result.matched_rules

    def test_process_batch(self, processor: TradeProcessor, sample_trade: Trade):
        """Test batch processing of multiple trades."""
        trades = [sample_trade] * 10
        results = processor.process_batch(trades)
        assert len(results) == 10
        assert all(r.is_success for r in results)

    def test_process_without_rule_engine(self):
        """Test processor works without a rule engine (no rules triggered)."""
        proc = TradeProcessor()
        trade = Trade(
            trade_id="T_TEST",
            symbol="TEST",
            price=100.0,
            quantity=50,
            timestamp=datetime.now(),
        )
        result = proc.process(trade)
        assert result.is_success is True
        assert result.matched_rules == []

    def test_process_mixed_batch(
        self,
        processor: TradeProcessor,
        sample_trade: Trade,
        invalid_trade: Trade,
        anomalous_price_trade: Trade,
    ):
        """Test batch with mixed valid, invalid, and anomalous trades."""
        trades = [sample_trade, invalid_trade, anomalous_price_trade]
        results = processor.process_batch(trades)
        assert len(results) == 3
        assert results[0].is_success is True
        assert results[1].status == ResultStatus.REJECTED
        assert "price_limit" in results[2].matched_rules
