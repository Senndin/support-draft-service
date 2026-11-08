"""Цикл надсилання відповідей: approved → sending → sent.

Тимчасові збої (таймаут, мережа, 5xx, 408, 429) повторюються з експоненційним
backoff і повним jitter, завжди з тим самим `Idempotency-Key`; після 8 спроб або
при постійній помилці (інший 4xx) — `send_failed`.
"""

import asyncio
import logging
import random
from datetime import timedelta

import httpx
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Ticket
from app.services.helpdesk import SendError, send_reply
from app.worker.loop import run_queue

log = logging.getLogger(__name__)

LEASE_S = 60  # таймаут хелпдеску 10 с з великим запасом
MAX_ATTEMPTS = 8
BACKOFF_CAP_S = 60
CONCURRENCY = 10  # одночасних запитів до хелпдеску
POLL_S = 1
SHUTDOWN_GRACE_S = 25


async def claim(session: AsyncSession, limit: int) -> list[Ticket]:
    """Захоплює `approved`, чий час настав, і `sending` з протермінованим lease."""
    due = (
        select(Ticket.id)
        .where(
            or_(
                and_(Ticket.status == "approved", Ticket.next_attempt_at <= func.now()),
                and_(Ticket.status == "sending", Ticket.locked_until < func.now()),
            )
        )
        .order_by(Ticket.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    stmt = (
        update(Ticket)
        .where(Ticket.id.in_(due.scalar_subquery()))
        .values(status="sending", locked_until=func.now() + timedelta(seconds=LEASE_S), updated_at=func.now())
        .returning(Ticket)
        .execution_options(synchronize_session=False)
    )
    claimed = list((await session.scalars(stmt)).all())
    await session.commit()
    return sorted(claimed, key=lambda t: t.id)


async def _finish(factory: async_sessionmaker, ticket_id: int, **values) -> None:
    """Оновлює звернення, лише якщо воно досі `sending` (lease не перехоплено)."""
    async with factory() as session:
        await session.execute(
            update(Ticket)
            .where(Ticket.id == ticket_id, Ticket.status == "sending")
            .values(**values, locked_until=None, updated_at=func.now())
        )
        await session.commit()


async def process(factory: async_sessionmaker, ticket: Ticket, client: httpx.AsyncClient) -> None:
    """Надсилає `final_message` на `reply_url`; результат — `sent`, повтор або `send_failed`."""
    try:
        await send_reply(client, ticket.reply_url, ticket.final_message, str(ticket.idempotency_key))
    except SendError as exc:
        attempts = ticket.attempts + 1
        error = str(exc)[:1000]
        if not exc.retryable or attempts >= MAX_ATTEMPTS:
            await _finish(factory, ticket.id, status="send_failed", attempts=attempts, last_error=error)
            log.warning("ticket %s: send failed for good after %s attempt(s): %s", ticket.id, attempts, error)
            return
        delay = random.uniform(0, min(2 ** (attempts - 1), BACKOFF_CAP_S))
        await _finish(
            factory,
            ticket.id,
            status="approved",
            attempts=attempts,
            last_error=error,
            next_attempt_at=func.now() + timedelta(seconds=delay),
        )
        log.info("ticket %s: send attempt %s failed, retry in %.1f s: %s", ticket.id, attempts, delay, error)
        return
    await _finish(factory, ticket.id, status="sent")
    log.info("ticket %s: reply sent", ticket.id)


async def release(factory: async_sessionmaker, ids: list[int]) -> None:
    """Повертає незавершені надсилання в `approved` без збільшення `attempts`."""
    async with factory() as session:
        await session.execute(
            update(Ticket)
            .where(Ticket.id.in_(ids), Ticket.status == "sending")
            .values(status="approved", locked_until=None, updated_at=func.now())
        )
        await session.commit()


async def run(factory: async_sessionmaker, client: httpx.AsyncClient, stop: asyncio.Event) -> None:
    """Обробляє чергу надсилання, доки не встановлено `stop`."""

    async def claim_batch(limit: int) -> list[Ticket]:
        async with factory() as session:
            return await claim(session, limit)

    await run_queue(
        "sending",
        claim_batch,
        lambda ticket: process(factory, ticket, client),
        lambda ids: release(factory, ids),
        CONCURRENCY,
        stop,
        POLL_S,
        SHUTDOWN_GRACE_S,
    )
