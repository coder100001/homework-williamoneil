"""Unit tests for ObjectPool."""

from src.utils.pool import ObjectPool
from src.models.trade import Trade


class TestObjectPool:
    """Tests for the ObjectPool class."""

    def test_acquire_creates_new_object(self):
        """Test that acquire creates new object when pool is empty."""
        pool = ObjectPool(factory=Trade, pool_size=100)
        obj = pool.acquire()
        assert isinstance(obj, Trade)
        assert pool.stats["created"] == 1
        assert pool.stats["reused"] == 0

    def test_release_and_reuse(self):
        """Test that released objects are reused."""
        pool = ObjectPool(factory=Trade, pool_size=100, reset_fn=lambda t: t.reset())
        obj1 = pool.acquire()
        obj1.trade_id = "T001"
        pool.release(obj1)
        assert pool.stats["returned"] == 1

        obj2 = pool.acquire()
        assert pool.stats["reused"] == 1
        # Object should be reset
        assert obj2.trade_id == ""

    def test_pool_size_limit(self):
        """Test that pool discards objects when full."""
        pool = ObjectPool(factory=Trade, pool_size=2, reset_fn=lambda t: t.reset())

        obj1 = pool.acquire()
        obj2 = pool.acquire()
        obj3 = pool.acquire()

        pool.release(obj1)
        pool.release(obj2)
        pool.release(obj3)  # Should be discarded (pool full)

        assert pool.stats["pool_size"] == 2

    def test_stats(self):
        """Test pool statistics tracking."""
        pool = ObjectPool(factory=Trade, pool_size=100)

        obj = pool.acquire()
        pool.release(obj)
        obj = pool.acquire()  # Should reuse

        stats = pool.stats
        assert stats["created"] == 1
        assert stats["reused"] == 1
        assert stats["returned"] == 1

    def test_thread_safety(self):
        """Test pool works correctly under concurrent access."""
        import concurrent.futures

        pool = ObjectPool(factory=Trade, pool_size=1000, reset_fn=lambda t: t.reset())

        def worker(n):
            results = []
            for _ in range(n):
                obj = pool.acquire()
                obj.trade_id = f"T_{id(obj)}"
                pool.release(obj)
                results.append(obj)
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, 100) for _ in range(10)]
            for f in concurrent.futures.as_completed(futures):
                assert len(f.result()) == 100

        # Pool should still be functional
        assert pool.stats["created"] > 0

    def test_custom_factory(self):
        """Test pool with a custom factory function."""
        counter = {"value": 0}

        def factory():
            counter["value"] += 1
            return {"id": counter["value"]}

        pool = ObjectPool(factory=factory, pool_size=10)
        obj = pool.acquire()
        assert obj["id"] == 1
