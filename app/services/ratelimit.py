"""Обмежувач частоти викликів LLM: не більше `rate` викликів за будь-які `period` секунд.

ponytail: in-process — достатньо для одного воркера; при кількох — лічильник у Postgres.
"""

import asyncio
import time
from collections import deque


class RateLimiter:
    """Ковзне вікно: зайві виклики чекають (FIFO), а не відхиляються."""

    def __init__(self, rate: int, period: float = 60.0):
        self.rate = rate
        self.period = period
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Чекає, доки у вікні звільниться місце, і резервує його."""
        # лок тримається і під час сну — черга очікувачів строго за порядком
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= self.period:
                    self._calls.popleft()
                if len(self._calls) < self.rate:
                    self._calls.append(now)
                    return
                await asyncio.sleep(self.period - (now - self._calls[0]))
