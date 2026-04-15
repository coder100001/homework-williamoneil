"""Unit tests for RuleEngine."""

from datetime import datetime

from src.models.trade import Trade
from src.core.processor import RuleEngine
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy


class TestRuleEngine:
    """Tests for the RuleEngine class."""

    def test_register_strategy(self):
        """Test strategy registration."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy())
        assert "price_limit" in engine.strategy_names

    def test_register_multiple_strategies(self):
        """Test registering multiple strategies."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy())
        engine.register(VolumeCheckStrategy())
        assert len(engine.strategy_names) == 2

    def test_unregister_strategy(self):
        """Test strategy unregistration."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy())
        engine.unregister("price_limit")
        assert "price_limit" not in engine.strategy_names

    def test_evaluate_no_rules(self):
        """Test evaluation with no registered rules."""
        engine = RuleEngine()
        trade = Trade(
            trade_id="T001", symbol="TEST", price=100.0,
            quantity=50, timestamp=datetime.now()
        )
        matched = engine.evaluate(trade)
        assert matched == []

    def test_evaluate_price_limit_triggered(self):
        """Test that price limit rule triggers correctly."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy(max_price=1000.0))
        trade = Trade(
            trade_id="T001", symbol="TEST", price=5000.0,
            quantity=50, timestamp=datetime.now()
        )
        matched = engine.evaluate(trade)
        assert "price_limit" in matched

    def test_evaluate_price_limit_not_triggered(self):
        """Test that price limit rule does not trigger for normal prices."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy(max_price=1000.0))
        trade = Trade(
            trade_id="T001", symbol="TEST", price=500.0,
            quantity=50, timestamp=datetime.now()
        )
        matched = engine.evaluate(trade)
        assert "price_limit" not in matched

    def test_evaluate_volume_check_triggered(self):
        """Test that volume check rule triggers correctly."""
        engine = RuleEngine()
        engine.register(VolumeCheckStrategy(max_volume=10000))
        trade = Trade(
            trade_id="T001", symbol="TEST", price=100.0,
            quantity=50000, timestamp=datetime.now()
        )
        matched = engine.evaluate(trade)
        assert "volume_check" in matched

    def test_evaluate_multiple_rules_triggered(self):
        """Test that multiple rules can trigger simultaneously."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy(max_price=1000.0))
        engine.register(VolumeCheckStrategy(max_volume=10000))
        trade = Trade(
            trade_id="T001", symbol="TEST", price=5000.0,
            quantity=50000, timestamp=datetime.now()
        )
        matched = engine.evaluate(trade)
        assert "price_limit" in matched
        assert "volume_check" in matched

    def test_repr(self):
        """Test string representation."""
        engine = RuleEngine()
        engine.register(PriceLimitStrategy())
        repr_str = repr(engine)
        assert "price_limit" in repr_str
