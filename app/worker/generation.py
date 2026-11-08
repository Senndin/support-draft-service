"""Цикл генерації чернеток: received → generating → draft_ready.

Черга — таблиця `tickets`. Задачі захоплюються атомарно через
`SELECT ... FOR UPDATE SKIP LOCKED` з lease (`locked_until`): якщо воркер упав,
задача повертається в обробку після закінчення lease.
"""

import asyncio
import logging
from datetime import timedelta

import httpx
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models import Ticket
from app.services.kb import search
from app.services.llm import generate_draft

log = logging.getLogger(__name__)

LEASE_S = 300  # з запасом: лімітер (до 60 с) + таймаут LLM (60 с) + затримка stub (до 30 с)
MAX_ATTEMPTS = 5
BACKOFF_BASE_S = 10  # затримка перед повтором: 10, 20, 40, 80 с
POLL_S = 1  # пауза, коли черга порожня або всі слоти зайняті
SHUTDOWN_GRACE_S = 25  # менше за stop_grace_period (30 с) у docker-compose.yml


async def claim(session: AsyncSession, limit: int) -> list[Ticket]:
    """Захоплює до `limit` задач: `received`, чий час настав, і `generating` з протермінованим lease."""
    due = (
        select(Ticket.id)
        .where(
            or_(
                and_(Ticket.status == "received", Ticket.next_attempt_at <= func.now()),
                and_(Ticket.status == "generating", Ticket.locked_until < func.now()),
            )
        )
        .order_by(Ticket.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    stmt = (
        update(Ticket)
        .where(Ticket.id.in_(due.scalar_subquery()))
        .values(
            status="generating",
            locked_until=func.now() + timedelta(seconds=LEASE_S),
            updated_at=func.now(),
        )
        .returning(Ticket)
        .execution_options(synchronize_session=False)
    )
    claimed = list((await session.scalars(stmt)).all())
    await session.commit()
    return sorted(claimed, key=lambda t: t.id)


async def process(factory: async_sessionmaker, ticket: Ticket, client: httpx.AsyncClient) -> None:
    """Пошук статей → LLM → `draft_ready`; будь-яка помилка — повтор з backoff або `generation_failed`."""
    try:
        async with factory() as session:
            articles = await search(session, ticket.message)
        result = await generate_draft(ticket.message, articles, client)
        async with factory() as session:
            # умова на status: якщо lease сплив і задачу вже взяли знову, не перезаписуємо
            await session.execute(
                update(Ticket)
                .where(Ticket.id == ticket.id, Ticket.status == "generating")
                .values(
                    status="draft_ready",
                    draft=result.text,
                    article_ids=result.article_ids,
                    locked_until=None,
                    updated_at=func.now(),
                )
            )
            await session.commit()
        log.info("ticket %s: draft ready", ticket.id)
    except Exception as exc:  # noqa: BLE001 — будь-яка помилка генерації веде до повтору
        await fail(factory, ticket, exc)


async def fail(factory: async_sessionmaker, ticket: Ticket, exc: Exception) -> None:
    """Фіксує невдалу спробу: `received` з відкладеним `next_attempt_at` або `generation_failed`."""
    attempts = ticket.attempts + 1
    values = dict(attempts=attempts, last_error=f"{type(exc).__name__}: {exc}"[:1000], locked_until=None, updated_at=func.now())
    if attempts >= MAX_ATTEMPTS:
        values["status"] = "generation_failed"
    else:
        values["status"] = "received"
        values["next_attempt_at"] = func.now() + timedelta(seconds=BACKOFF_BASE_S * 2 ** (attempts - 1))
    async with factory() as session:
        await session.execute(update(Ticket).where(Ticket.id == ticket.id, Ticket.status == "generating").values(**values))
        await session.commit()
    log.warning("ticket %s: attempt %s failed: %r", ticket.id, attempts, exc)


async def release(factory: async_sessionmaker, ids: list[int]) -> None:
    """Повертає незавершені задачі в чергу без збільшення `attempts`."""
    async with factory() as session:
        await session.execute(
            update(Ticket)
            .where(Ticket.id.in_(ids), Ticket.status == "generating")
            .values(status="received", locked_until=None, updated_at=func.now())
        )
        await session.commit()


async def run(factory: async_sessionmaker, client: httpx.AsyncClient, stop: asyncio.Event) -> None:
    """Обробляє чергу, доки не встановлено `stop`; потім дочікується поточних задач або відпускає їх."""
    running: dict[asyncio.Task, int] = {}
    while not stop.is_set():
        free = settings.llm_concurrency - len(running)
        claimed = []
        if free > 0:
            try:
                async with factory() as session:
                    claimed = await claim(session, free)
            except Exception:  # noqa: BLE001 — БД тимчасово недоступна: пробуємо знову
                log.exception("claim failed")
        for ticket in claimed:
            task = asyncio.create_task(process(factory, ticket, client))
            running[task] = ticket.id
            task.add_done_callback(lambda t: running.pop(t, None))
        if not claimed:
            try:
                await asyncio.wait_for(stop.wait(), POLL_S)
            except TimeoutError:
                pass

    if running:
        log.info("stopping: waiting for %s generation(s)", len(running))
        _, pending = await asyncio.wait(list(running), timeout=SHUTDOWN_GRACE_S)
        # id беремо до скасування: done-callback прибирає задачі з running
        unfinished = [running[t] for t in pending]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if unfinished:
            log.info("releasing %s unfinished ticket(s)", len(unfinished))
            await release(factory, unfinished)
