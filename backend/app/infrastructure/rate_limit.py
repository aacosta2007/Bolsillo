import time
from collections import defaultdict, deque


class LoginRateLimiter:
    """Límite en memoria: `max_failures` intentos fallidos por IP en `window` segundos."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        q = self._failures[key]
        cutoff = time.monotonic() - self.window
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            self._failures.pop(key, None)
            return deque()
        return q

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self.max_failures

    def register_failure(self, key: str) -> None:
        self._prune(key)
        self._failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()
