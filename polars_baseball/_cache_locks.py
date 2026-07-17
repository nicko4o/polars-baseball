import asyncio
import contextlib
import threading
import weakref
from collections.abc import Generator


class SharedExclusiveLock:
    """A basic reader-writer lock implementation for thread safety."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._readers = 0
        self._writers = 0
        self._writer_waiting = 0

    @contextlib.contextmanager
    def shared(self) -> Generator[None, None, None]:
        with self._lock:
            while self._writers > 0 or self._writer_waiting > 0:
                self._cond.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._lock:
                self._readers -= 1
                if self._readers == 0:
                    self._cond.notify_all()

    @contextlib.contextmanager
    def exclusive(self) -> Generator[None, None, None]:
        with self._lock:
            self._writer_waiting += 1
            while self._readers > 0 or self._writers > 0:
                self._cond.wait()
            self._writer_waiting -= 1
            self._writers += 1
        try:
            yield
        finally:
            with self._lock:
                self._writers -= 1
                self._cond.notify_all()


_IN_FLIGHT_LOCKS: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, weakref.WeakValueDictionary[str, asyncio.Lock]
] = weakref.WeakKeyDictionary()
_IN_FLIGHT_LOCKS_GUARD = threading.Lock()


def _in_flight_lock_for(cache: object, key: str) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    composite_key = f"{id(cache)}:{key}"
    with _IN_FLIGHT_LOCKS_GUARD:
        loop_locks = _IN_FLIGHT_LOCKS.get(loop)
        if loop_locks is None:
            loop_locks = weakref.WeakValueDictionary()
            _IN_FLIGHT_LOCKS[loop] = loop_locks
        lock = loop_locks.get(composite_key)
        if lock is None:
            lock = asyncio.Lock()
            loop_locks[composite_key] = lock
        return lock
