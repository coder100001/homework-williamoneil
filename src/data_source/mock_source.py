"""Mock market data source for generating synthetic trade data.

Generates realistic-looking market trades for testing and demonstration.
All data is completely synthetic and contains no real market information.
"""

import logging
import random
import string
from datetime import datetime, timedelta

from src.models.trade import Trade
from src.utils.pool import ObjectPool

logger = logging.getLogger(__name__)

# Default ticker symbols (completely synthetic)
DEFAULT_SYMBOLS = [
    "SYNTH1", "SYNTH2", "SYNTH3", "SYNTH4", "SYNTH5",
    "MOCKA", "MOCKB", "MOCKC", "MOCKD", "MOCKE",
    "TESTX", "TESTY", "TESTZ",
]

# Default exchange identifiers
DEFAULT_EXCHANGES = ["EXCH_A", "EXCH_B", "EXCH_C"]


class MockDataSource:
    """Generates synthetic market trade data for testing.

    Uses an object pool for Trade objects to reduce GC pressure when
    generating large volumes of data.

    Args:
        symbols: List of ticker symbols to use (default: synthetic symbols).
        exchanges: List of exchange identifiers (default: synthetic exchanges).
        price_range: Tuple of (min_price, max_price) for generated trades.
        volume_range: Tuple of (min_volume, max_volume) for generated trades.
        use_pool: Whether to use object pool for Trade reuse.
        pool_size: Maximum pool size if use_pool is True.
    """

    def __init__(
        self,
        symbols: list[str] | None = None,
        exchanges: list[str] | None = None,
        price_range: tuple[float, float] = (1.0, 500.0),
        volume_range: tuple[int, int] = (1, 10000),
        use_pool: bool = True,
        pool_size: int = 10000,
    ):
        self._symbols = symbols or DEFAULT_SYMBOLS
        self._exchanges = exchanges or DEFAULT_EXCHANGES
        self._price_range = price_range
        self._volume_range = volume_range
        self._trade_counter = 0

        # Object pool for Trade reuse
        self._pool: ObjectPool[Trade] | None = None
        if use_pool:
            self._pool = ObjectPool(
                factory=Trade,
                pool_size=pool_size,
                reset_fn=lambda t: t.reset(),
            )

    def generate_trade(self) -> Trade:
        """Generate a single synthetic trade.

        Returns:
            A Trade object with random but realistic data.
        """
        if self._pool:
            trade = self._pool.acquire()
        else:
            trade = Trade()

        self._trade_counter += 1
        trade.trade_id = f"T{self._trade_counter:08d}"
        trade.symbol = random.choice(self._symbols)
        trade.price = round(random.uniform(*self._price_range), 2)
        trade.quantity = random.randint(*self._volume_range)
        trade.timestamp = datetime.now() - timedelta(
            microseconds=random.randint(0, 1_000_000)
        )
        trade.exchange = random.choice(self._exchanges)

        return trade

    def generate_batch(self, count: int) -> list[Trade]:
        """Generate a batch of synthetic trades.

        Args:
            count: Number of trades to generate.

        Returns:
            List of Trade objects.
        """
        return [self.generate_trade() for _ in range(count)]

    def generate_anomalous_trade(
        self,
        anomaly_type: str = "price_spike",
    ) -> Trade:
        """Generate a trade with anomalous characteristics for rule testing.

        Args:
            anomaly_type: Type of anomaly to inject:
                - 'price_spike': Extremely high price
                - 'price_drop': Extremely low price
                - 'volume_spike': Extremely high volume
                - 'zero_volume': Zero volume (invalid)

        Returns:
            A Trade object with anomalous data.
        """
        trade = self.generate_trade()

        if anomaly_type == "price_spike":
            trade.price = random.uniform(50000.0, 100000.0)
        elif anomaly_type == "price_drop":
            trade.price = random.uniform(0.001, 0.009)
        elif anomaly_type == "volume_spike":
            trade.quantity = random.randint(1000000, 10000000)
        elif anomaly_type == "zero_volume":
            trade.quantity = 0

        return trade

    def release_trade(self, trade: Trade) -> None:
        """Return a trade object to the pool for reuse.

        Args:
            trade: The trade object to release.
        """
        if self._pool:
            self._pool.release(trade)

    def release_batch(self, trades: list[Trade]) -> None:
        """Return a batch of trade objects to the pool.

        Args:
            trades: List of trade objects to release.
        """
        for trade in trades:
            self.release_trade(trade)

    @property
    def pool_stats(self) -> dict[str, int] | None:
        """Get object pool statistics, if pool is enabled."""
        return self._pool.stats if self._pool else None
