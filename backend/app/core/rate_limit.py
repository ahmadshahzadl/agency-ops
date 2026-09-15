"""In-memory failed-attempt rate limiter for credential endpoints.

Single-process by design: the app already requires one worker because of the
in-memory WebSocket managers, so process-local state covers all traffic.
Tracks only FAILED attempts per key (e.g. login email), so normal successful
logins are never throttled; a success clears the key.
"""
import time
from collections import defaultdict, deque
from threading import Lock


class FailureRateLimiter:
    def __init__(self, max_failures: int = 10, window_seconds: int = 900):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> None:
        q = self._failures.get(key)
        if q is None:
            return
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            self._failures.pop(key, None)

    def retry_after(self, key: str) -> int:
        """Seconds until the key is allowed again; 0 if not currently blocked."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            q = self._failures.get(key)
            if q is None or len(q) < self.max_failures:
                return 0
            return max(1, int(q[0] + self.window_seconds - now))

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


# 10 failed attempts per email within 15 minutes, then locked for the remainder
# of the window. Successful login resets the counter.
login_limiter = FailureRateLimiter(max_failures=10, window_seconds=900)


class RequestRateLimiter:
    """Sliding-window request counter per key (e.g. client IP) for public, unauthenticated
    endpoints. Unlike FailureRateLimiter it counts every call, not just failures."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            cutoff = now - self.window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
