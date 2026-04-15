"""Shared pytest fixtures."""

import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime

from src.models.trade import Trade
from src.models.result import ProcessResult, ResultStatus
from src.core.processor import TradeProcessor, RuleEngine
from src.core.concurrent_processor import ConcurrentProcessor
from src.core.subscriber_manager import SubscriberManager
from src.data_source.mock_source import MockDataSource
from src.strategies.price_limit import PriceLimitStrategy
from src.strategies.volume_check import VolumeCheckStrategy
from src.subscribers.risk_subscriber import RiskSubscriber
from src.subscribers.monitor_subscriber import MonitorSubscriber


@pytest.fixture
def sample_trade() -> Trade:
    """Create a valid sample trade."""
    return Trade(
        trade_id="T00000001",
        symbol="SYNTH1",
        price=150.0,
        quantity=100,
        timestamp=datetime.now(),
        exchange="EXCH_A",
    )


@pytest.fixture
def invalid_trade() -> Trade:
    """Create an invalid trade for testing rejection."""
    return Trade(
        trade_id="T00000002",
        symbol="",
        price=-10.0,
        quantity=0,
        timestamp=datetime.now(),
    )


@pytest.fixture
def anomalous_price_trade() -> Trade:
    """Create a trade with anomalous price."""
    return Trade(
        trade_id="T00000003",
        symbol="SYNTH2",
        price=99999.0,
        quantity=100,
        timestamp=datetime.now(),
        exchange="EXCH_B",
    )


@pytest.fixture
def anomalous_volume_trade() -> Trade:
    """Create a trade with anomalous volume."""
    return Trade(
        trade_id="T00000004",
        symbol="SYNTH3",
        price=100.0,
        quantity=5000000,
        timestamp=datetime.now(),
        exchange="EXCH_C",
    )


@pytest.fixture
def rule_engine() -> RuleEngine:
    """Create a rule engine with default strategies."""
    engine = RuleEngine()
    engine.register(PriceLimitStrategy(max_price=10000.0, min_price=0.01))
    engine.register(VolumeCheckStrategy(max_volume=1000000, min_volume=1))
    return engine


@pytest.fixture
def processor(rule_engine: RuleEngine) -> TradeProcessor:
    """Create a trade processor with default rule engine."""
    return TradeProcessor(rule_engine=rule_engine)


@pytest.fixture
def concurrent_processor(processor: TradeProcessor) -> ConcurrentProcessor:
    """Create a concurrent processor for testing."""
    cp = ConcurrentProcessor(
        processor=processor,
        max_workers=4,
        batch_size=50,
        queue_size=100,
    )
    cp.start()
    yield cp
    cp.stop()


@pytest.fixture
def subscriber_manager() -> SubscriberManager:
    """Create a subscriber manager with default subscribers."""
    mgr = SubscriberManager()
    mgr.subscribe(RiskSubscriber())
    mgr.subscribe(MonitorSubscriber())
    return mgr


@pytest.fixture
def data_source() -> MockDataSource:
    """Create a mock data source."""
    return MockDataSource(use_pool=True, pool_size=1000)
