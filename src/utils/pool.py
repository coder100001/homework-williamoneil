"""Generic object pool for reducing GC pressure through object reuse.

Uses queue.Queue for thread-safe object management.
"""

import logging
from queue import Queue, Empty, Full
from typing import Callable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ObjectPool(Generic[T]):
    """Thread-safe object pool for reusing objects to reduce GC pressure.

    Objects are acquired from the pool, used, and then released back for reuse.
    When the pool is exhausted, new objects are created on demand.

    Args:
        factory: Callable that creates a new object instance.
        pool_size: Maximum number of objects to keep in the pool.
        reset_fn: Optional callable to reset an object before returning it to the pool.
    """

    def __init__(
        self,
        factory: Callable[[], T],
        pool_size: int = 10000,
        reset_fn: Callable[[T], None] | None = None,
    ):
        self._factory = factory
        self._reset_fn = reset_fn
        self._pool: Queue[T] = Queue(maxsize=pool_size)
        self._created = 0
        self._reused = 0
        self._returned = 0

    def acquire(self) -> T:
        """Acquire an object from the pool.

        Returns a pooled object if available, otherwise creates a new one.

        Returns:
            An object instance ready for use.
        """
        try:
            obj = self._pool.get_nowait()
            self._reused += 1
            return obj
        except Empty:
            obj = self._factory()
            self._created += 1
            return obj

    def release(self, obj: T) -> None:
        """Return an object to the pool for reuse.

        If the pool is full, the object is discarded and will be garbage collected.

        Args:
            obj: The object to return to the pool.
        """
        if self._reset_fn:
            self._reset_fn(obj)

        try:
            self._pool.put_nowait(obj)
            self._returned += 1
        except Full:
            # Pool is full, let the object be GC'd
            pass

    @property
    def stats(self) -> dict[str, int]:
        """Get pool utilization statistics."""
        return {
            "created": self._created,
            "reused": self._reused,
            "returned": self._returned,
            "pool_size": self._pool.qsize(),
        }

    def __repr__(self) -> str:
        return (
            f"ObjectPool(created={self._created}, reused={self._reused}, "
            f"returned={self._returned}, available={self._pool.qsize()})"
        )
