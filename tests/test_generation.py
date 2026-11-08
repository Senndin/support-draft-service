"""Тести черги генерації: захоплення, обробка, повтори, зупинка."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models import Ticket
from app.worker.generation import LEASE_S, claim


def now() -> datetime:
    return datetime.now(timezone.utc)


async def add_ticket(factory, **fields) -> int:
    """Додає звернення (за замовчуванням `received`) і повертає його id."""
    n = fields.pop("n", 1)
    defaults = dict(
        event_id=f"evt-{n}",
        ticket_id=f"T-{n}",
        customer_email="c@example.com",
        message="Не можу експортувати звіт у PDF",
        reply_url="http://api:8000/mock/helpdesk/tickets/T/replies",
    )
    async with factory() as s:
        ticket = Ticket(**{**defaults, **fields})
        s.add(ticket)
        await s.commit()
        return ticket.id


async def get(factory, ticket_id) -> Ticket:
    async with factory() as s:
        return await s.get(Ticket, ticket_id)


async def test_claim_takes_due_received(session_factory):
    due = await add_ticket(session_factory, n=1)
    await add_ticket(session_factory, n=2, next_attempt_at=now() + timedelta(minutes=5))
    async with session_factory() as s:
        claimed = await claim(s, 10)
    assert [t.id for t in claimed] == [due]
    ticket = await get(session_factory, due)
    assert ticket.status == "generating"
    assert ticket.locked_until > now() + timedelta(seconds=LEASE_S - 30)


async def test_claim_retakes_expired_lease(session_factory):
    stale = await add_ticket(session_factory, status="generating", locked_until=now() - timedelta(seconds=1))
    await add_ticket(session_factory, n=2, status="generating", locked_until=now() + timedelta(minutes=1))
    async with session_factory() as s:
        claimed = await claim(s, 10)
    assert [t.id for t in claimed] == [stale]
    assert (await get(session_factory, stale)).locked_until > now()


async def test_concurrent_claims_do_not_overlap(session_factory):
    for n in range(4):
        await add_ticket(session_factory, n=n)

    async def take():
        async with session_factory() as s:
            return {t.id for t in await claim(s, 4)}

    first, second = await asyncio.gather(take(), take())
    assert not first & second
    assert len(first | second) == 4


# --- обробка ---

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.models import KbArticle  # noqa: E402
from app.services import llm  # noqa: E402
from app.worker import generation  # noqa: E402
from app.worker.generation import process  # noqa: E402


@pytest.fixture
def stub_llm(monkeypatch):
    """Режим без ключа з нульовою затримкою; провайдер відповідає 401."""
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "stub_delay_min_s", 0)
    monkeypatch.setattr(settings, "stub_delay_max_s", 0)
    llm.reset_limits()
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(401)))


async def claim_one(factory) -> Ticket:
    async with factory() as s:
        (ticket,) = await claim(s, 1)
    return ticket


async def test_process_saves_draft(kb, session_factory, stub_llm):
    ticket_id = await add_ticket(session_factory)
    await process(session_factory, await claim_one(session_factory), stub_llm)
    ticket = await get(session_factory, ticket_id)
    async with kb() as s:
        export = await s.scalar(select(KbArticle).where(KbArticle.slug == "export-pdf"))
    assert ticket.status == "draft_ready"
    assert export.url in ticket.draft
    assert export.id in ticket.article_ids
    assert ticket.locked_until is None


@pytest.fixture
def failing_llm(monkeypatch, stub_llm):
    async def boom(*args, **kwargs):
        raise llm.LLMError("LLM відповів 500")

    monkeypatch.setattr(generation, "generate_draft", boom)
    return stub_llm


async def test_error_schedules_retry(kb, session_factory, failing_llm):
    ticket_id = await add_ticket(session_factory)
    await process(session_factory, await claim_one(session_factory), failing_llm)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts, ticket.locked_until) == ("received", 1, None)
    assert "500" in ticket.last_error
    assert timedelta(seconds=8) < ticket.next_attempt_at - now() <= timedelta(seconds=10)


async def test_last_attempt_fails_ticket(kb, session_factory, failing_llm):
    ticket_id = await add_ticket(session_factory, attempts=4)
    await process(session_factory, await claim_one(session_factory), failing_llm)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts) == ("generation_failed", 5)


# --- цикл і зупинка ---

from app.worker.generation import run  # noqa: E402


async def wait_status(factory, ticket_id, status, timeout=5.0) -> Ticket:
    """Чекає, доки звернення набуде статусу."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        ticket = await get(factory, ticket_id)
        if ticket.status == status:
            return ticket
        await asyncio.sleep(0.05)
    raise AssertionError(f"ticket {ticket_id} не став {status}, а {ticket.status}")


async def test_run_processes_queue_until_stop(kb, session_factory, stub_llm):
    ticket_id = await add_ticket(session_factory)
    stop = asyncio.Event()
    worker = asyncio.create_task(run(session_factory, stub_llm, stop))
    await wait_status(session_factory, ticket_id, "draft_ready")
    stop.set()
    await asyncio.wait_for(worker, timeout=3)


async def test_stop_releases_unfinished_ticket(kb, session_factory, stub_llm, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(30)

    monkeypatch.setattr(generation, "generate_draft", slow)
    monkeypatch.setattr(generation, "SHUTDOWN_GRACE_S", 0.1)
    ticket_id = await add_ticket(session_factory)
    stop = asyncio.Event()
    worker = asyncio.create_task(run(session_factory, stub_llm, stop))
    await wait_status(session_factory, ticket_id, "generating")
    stop.set()
    await asyncio.wait_for(worker, timeout=3)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.locked_until, ticket.attempts) == ("received", None, 0)
