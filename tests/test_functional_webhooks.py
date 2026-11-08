"""End-to-end сценарії `webhook-intake` і `webhook-sender` на справжньому PostgreSQL."""

import asyncio
import time

import httpx
from httpx import ASGITransport
from sqlalchemy import func, select

from app.main import app
from app.models import Ticket
from scripts.send_webhooks import build_events, send_all
from tests.test_webhooks import count_tickets, event


# --- webhook-intake ---


async def test_scenario_new_event(client, session_factory):
    """Сценарій «Нова подія»."""
    response = await client.post("/webhooks/helpdesk", json=event(event_id="evt-1"))
    assert (response.status_code, response.json()) == (202, {"status": "accepted"})
    async with session_factory() as s:
        ticket = await s.scalar(select(Ticket).where(Ticket.event_id == "evt-1"))
    assert ticket.status == "received"
    assert (ticket.ticket_id, ticket.customer_email, ticket.message) == (
        "T-1",
        "client@example.com",
        "Не можу експортувати звіт у PDF",
    )


async def test_scenario_sequential_duplicate(client, session_factory):
    """Сценарій «Послідовний дубль»."""
    await client.post("/webhooks/helpdesk", json=event(event_id="evt-1"))
    response = await client.post("/webhooks/helpdesk", json=event(event_id="evt-1", message="інше"))
    assert (response.status_code, response.json()) == (202, {"status": "accepted"})
    async with session_factory() as s:
        messages = (await s.scalars(select(Ticket.message).where(Ticket.event_id == "evt-1"))).all()
    assert messages == ["Не можу експортувати звіт у PDF"]


async def test_scenario_concurrent_duplicates(client, session_factory):
    """Сценарій «Одночасні дублі»: 10 запитів з одним event_id → 1 рядок."""
    responses = await asyncio.gather(
        *(client.post("/webhooks/helpdesk", json=event(event_id="evt-2")) for _ in range(10))
    )
    assert [r.status_code for r in responses] == [202] * 10
    async with session_factory() as s:
        n = await s.scalar(select(func.count()).select_from(Ticket).where(Ticket.event_id == "evt-2"))
    assert n == 1


async def test_scenario_missing_field(client, session_factory):
    """Сценарій «Відсутнє поле»."""
    body = {k: v for k, v in event().items() if k != "event_id"}
    response = await client.post("/webhooks/helpdesk", json=body)
    assert response.status_code == 422
    assert await count_tickets(session_factory) == 0


async def test_scenario_no_external_calls(client, monkeypatch):
    """Сценарій «Відповідь без зовнішніх викликів»: вихідні HTTP-з'єднання заборонені."""

    async def forbidden(self, request):
        raise AssertionError(f"вихідний запит під час вебхука: {request.url}")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    started = time.perf_counter()
    response = await client.post("/webhooks/helpdesk", json=event(event_id="evt-fast"))
    assert response.status_code == 202
    assert time.perf_counter() - started < 0.5


# --- webhook-sender ---


async def test_scenario_sender_with_duplicates(client, session_factory):
    """Сценарії «Прогін із дублями» і «Звіт про відповіді»: 20 унікальних + 10 дублів → 20 рядків."""
    # фікстура client уже перевизначила сесію застосунку на тестову БД
    events = build_events(20, 0.5, "http://api:8000")
    counts = await send_all(events, "http://test/webhooks/helpdesk", 10, ASGITransport(app=app))
    assert len(events) == 30
    assert counts == {202: 30}
    assert await count_tickets(session_factory) == 20
