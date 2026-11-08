"""Спільний цикл обробки черги в таблиці `tickets` для генерації й надсилання."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.models import Ticket

log = logging.getLogger(__name__)


async def run_queue(
    name: str,
    claim: Callable[[int], Awaitable[list[Ticket]]],
    handle: Callable[[Ticket], Awaitable[None]],
    release: Callable[[list[int]], Awaitable[None]],
    capacity: int,
    stop: asyncio.Event,
    poll_s: float,
    grace_s: float,
) -> None:
    """Захоплює задачі за вільними слотами, доки не встановлено `stop`.

    На зупинці чекає поточні задачі до `grace_s`, решту скасовує й повертає в чергу через `release`.
    """
    running: dict[asyncio.Task, int] = {}
    while not stop.is_set():
        free = capacity - len(running)
        claimed: list[Ticket] = []
        if free > 0:
            try:
                claimed = await claim(free)
            except Exception:  # noqa: BLE001 — БД тимчасово недоступна: пробуємо знову
                log.exception("%s: claim failed", name)
        for ticket in claimed:
            task = asyncio.create_task(handle(ticket))
            running[task] = ticket.id
            task.add_done_callback(lambda t: running.pop(t, None))
        if not claimed:
            try:
                await asyncio.wait_for(stop.wait(), poll_s)
            except TimeoutError:
                pass

    if running:
        log.info("%s stopping: waiting for %s task(s)", name, len(running))
        _, pending = await asyncio.wait(list(running), timeout=grace_s)
        # id беремо до скасування: done-callback прибирає задачі з running
        unfinished = [running[t] for t in pending]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if unfinished:
            log.info("%s: releasing %s unfinished ticket(s)", name, len(unfinished))
            await release(unfinished)
