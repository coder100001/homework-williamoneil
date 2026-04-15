"""Trade processor with validation pipeline and rule execution."""

import logging
from typing import Protocol

from src.models.trade import Trade
from src.models.result import ProcessResult, ResultStatus


class Strategy(Protocol):
    """Protocol for rule strategies that can be registered with the rule engine."""

    @property
    def name(self) -> str:
        """Unique name of the strategy."""
        ...

    def apply(self, trade: Trade) -> bool:
        """Apply the rule to a trade.

        Returns:
            True if the rule is triggered (trade matches the rule condition).
        """
        ...


class TradeProcessor:
    """Processes individual trades through validation and rule execution.

    The processor runs a pipeline:
    1. Data validation
    2. Rule engine execution
    3. Result aggregation

    Args:
        rule_engine: The rule engine to apply to each trade.
    """

    def __init__(self, rule_engine: "RuleEngine | None" = None):
        self._rule_engine = rule_engine or RuleEngine()
        self._logger = logging.getLogger(__name__)

    @property
    def rule_engine(self) -> "RuleEngine":
        """Access the rule engine for strategy registration."""
        return self._rule_engine

    def process(self, trade: Trade) -> ProcessResult:
        """Process a single trade through the validation and rule pipeline.

        Args:
            trade: The trade to process.

        Returns:
            ProcessResult with status and matched rules.

        Raises:
            ValueError: If trade data is invalid.
        """
        result = ProcessResult(trade_id=trade.trade_id)

        # Step 1: Validate trade data
        if not trade.validate():
            result.status = ResultStatus.REJECTED
            result.details = "Trade validation failed"
            result.error_message = (
                f"Invalid trade: symbol={trade.symbol}, "
                f"price={trade.price}, quantity={trade.quantity}"
            )
            self._logger.warning("Trade rejected: %s", trade.trade_id)
            return result

        # Step 2: Execute rules
        try:
            matched_rules = self._rule_engine.evaluate(trade)
            result.matched_rules = matched_rules
            result.status = ResultStatus.SUCCESS
            result.details = (
                f"Processed successfully, {len(matched_rules)} rules triggered"
            )
        except Exception as e:
            result.status = ResultStatus.ERROR
            result.error_message = str(e)
            self._logger.error("Rule execution failed for %s: %s", trade.trade_id, e)

        return result

    def process_batch(self, trades: list[Trade]) -> list[ProcessResult]:
        """Process a batch of trades.

        Args:
            trades: List of trades to process.

        Returns:
            List of processing results, one per trade.
        """
        return [self.process(trade) for trade in trades]


class RuleEngine:
    """Dynamic rule execution engine using Strategy pattern.

    Strategies can be registered at runtime, allowing new rules to be added
    without modifying core processing logic.

    Example:
        engine = RuleEngine()
        engine.register(PriceLimitStrategy(max_price=500.0))
        engine.register(VolumeCheckStrategy(min_volume=10))

        matched = engine.evaluate(trade)
    """

    def __init__(self):
        self._strategies: dict[str, Strategy] = {}
        self._logger = logging.getLogger(__name__)

    def register(self, strategy: Strategy) -> None:
        """Register a strategy with the engine.

        Args:
            strategy: The strategy instance to register.
        """
        self._strategies[strategy.name] = strategy
        self._logger.info("Registered strategy: %s", strategy.name)

    def unregister(self, name: str) -> None:
        """Remove a strategy by name.

        Args:
            name: The name of the strategy to remove.
        """
        if name in self._strategies:
            del self._strategies[name]
            self._logger.info("Unregistered strategy: %s", name)

    def evaluate(self, trade: Trade) -> list[str]:
        """Evaluate all registered strategies against a trade.

        Args:
            trade: The trade to evaluate.

        Returns:
            List of strategy names that were triggered.
        """
        matched: list[str] = []
        for name, strategy in self._strategies.items():
            try:
                if strategy.apply(trade):
                    matched.append(name)
            except Exception as e:
                self._logger.error("Strategy %s failed: %s", name, e)
        return matched

    @property
    def strategy_names(self) -> list[str]:
        """List all registered strategy names."""
        return list(self._strategies.keys())

    def __repr__(self) -> str:
        return f"RuleEngine(strategies={list(self._strategies.keys())})"
