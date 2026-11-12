import random
import threading
import time
from collections import deque
from contextlib import contextmanager

from scraper.config import CONFIG


class RateLimiter:
  """Giới hạn toàn cục: số request đồng thời, số request/phút, nghỉ ngẫu nhiên sau mỗi request."""

  def __init__(self, max_concurrent, max_per_minute, min_delay, max_delay):
    self._sem = threading.BoundedSemaphore(max_concurrent)
    self._max_per_minute = max_per_minute
    self._min_delay = min_delay
    self._max_delay = max_delay
    self._timestamps = deque()
    self._lock = threading.Lock()

  def _wait_for_minute_slot(self):
    while True:
      with self._lock:
        now = time.monotonic()
        while self._timestamps and now - self._timestamps[0] >= 60:
          self._timestamps.popleft()
        if len(self._timestamps) < self._max_per_minute:
          self._timestamps.append(now)
          return
        wait = 60 - (now - self._timestamps[0])
      time.sleep(wait)

  @contextmanager
  def slot(self):
    with self._sem:
      self._wait_for_minute_slot()
      try:
        yield
      finally:
        time.sleep(random.uniform(self._min_delay, self._max_delay))


_rl = CONFIG["rate_limit"]
limiter = RateLimiter(
    _rl["max_concurrent_requests"],
    _rl["max_requests_per_minute"],
    _rl["min_delay_sec"],
    _rl["max_delay_sec"],
)
