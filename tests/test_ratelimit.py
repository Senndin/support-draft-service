"""Тести ковзного вікна `RateLimiter`."""

import asyncio
import time

from app.services.ratelimit import RateLimiter


async def test_limiter_holds_extra_calls():
    limiter = RateLimiter(3, 0.5)
    start = time.monotonic()
    stamps: list[float] = []

    async def call():
        await limiter.acquire()
        stamps.append(time.monotonic() - start)

    await asyncio.gather(*(call() for _ in range(6)))
    stamps.sort()
    assert all(t < 0.1 for t in stamps[:3])
    assert all(t >= 0.5 for t in stamps[3:])
    # у будь-якому вікні 0.5 с — не більше 3 викликів
    assert all(sum(1 for s in stamps if t <= s < t + 0.5 - 1e-3) <= 3 for t in stamps)
