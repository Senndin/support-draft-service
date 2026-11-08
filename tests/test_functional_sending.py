"""End-to-end сценарії `helpdesk-mock` і `reply-sending`: воркер надсилає у справжній мок через ASGI."""

import asyncio
import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import update

from app.config import settings
from app.main import app
from app.mock_helpdesk import routes as mock
from app.models import Ticket
from app.worker.sending import claim, process
from tests.test_generation import add_ticket, get
from tests.test_mock_helpdesk import URL, mock_client, replies  # noqa: F401 — фікстура


# --- helpdesk-mock ---


async def test_scenario_new_reply(mock_client):  # noqa: F811
    """Сценарій «Нова відповідь»."""
    r = await mock_client.post(URL, json={"message": "Відповідь"}, headers={"Idempotency-Key": "k1"})
    assert r.status_code == 201
    assert [(x["ticket_id"], x["idempotency_key"]) for x in await replies(mock_client)] == [("T-1", "k1")]


async def test_scenario_same_key_repeat(mock_client):  # noqa: F811
    """Сценарій «Повтор з тим самим ключем»."""
    a = await mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "k1"})
    b = await mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "k1"})
    assert (b.status_code, b.json()["id"]) == (201, a.json()["id"])
    assert len(await replies(mock_client)) == 1


async def test_scenario_always_500(mock_client, monkeypatch):  # noqa: F811
    """Сценарій «Завжди 500»."""
    monkeypatch.setattr(settings, "mock_fail_rate", 1)
    assert (await mock_client.post(URL, json={"message": "A"})).status_code == 500
    assert await replies(mock_client) == []


async def test_scenario_slow_reply_accepted(mock_client, monkeypatch):  # noqa: F811
    """Сценарій «Повільна відповідь приймається»."""
    monkeypatch.setattr(settings, "mock_slow_rate", 1)
    monkeypatch.setattr(settings, "helpdesk_timeout_s", 5)
    slow = asyncio.create_task(mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "slow"}))
    await asyncio.sleep(0.2)
    monkeypatch.setattr(settings, "mock_slow_rate", 0)
    assert [x["idempotency_key"] for x in await replies(mock_client)] == ["slow"]
    slow.cancel()


# --- reply-sending ---


@pytest.fixture
def helpdesk(monkeypatch):
    """Мок без збоїв і HTTP-клієнт воркера, що ходить у нього через ASGI."""
    mock.reset()
    monkeypatch.setattr(settings, "mock_fail_rate", 0)
    monkeypatch.setattr(settings, "mock_slow_rate", 0)
    return httpx.AsyncClient(transport=ASGITransport(app=app))


async def approved(factory, ticket_id="T-7", **fields) -> int:
    return await add_ticket(
        factory,
        status="approved",
        final_message="Відповідь клієнту",
        idempotency_key=uuid.uuid4(),
        reply_url=f"http://test/mock/helpdesk/tickets/{ticket_id}/replies",
        **fields,
    )


async def drain(factory, client, rounds=10) -> None:
    """Обробляє чергу надсилання, не чекаючи backoff (next_attempt_at зсувається на зараз)."""
    for _ in range(rounds):
        async with factory() as s:
            await s.execute(update(Ticket).where(Ticket.status == "approved").values(next_attempt_at=Ticket.created_at))
            await s.commit()
            tickets = await claim(s, 10)
        if not tickets:
            return
        for t in tickets:
            await process(factory, t, client)


def mock_replies_for(ticket_id: str) -> list[dict]:
    return [r for r in mock.REPLIES if r["ticket_id"] == ticket_id]


async def test_scenario_successful_send(session_factory, helpdesk):
    """Сценарій «Успішне надсилання»."""
    ticket_id = await approved(session_factory)
    await drain(session_factory, helpdesk)
    ticket = await get(session_factory, ticket_id)
    assert ticket.status == "sent"
    (reply,) = mock_replies_for("T-7")
    assert (reply["message"], reply["idempotency_key"]) == ("Відповідь клієнту", str(ticket.idempotency_key))


async def test_scenario_two_5xx_then_success(session_factory, helpdesk, monkeypatch):
    """Сценарій «Два 5xx, потім успіх»."""
    monkeypatch.setattr(settings, "mock_fail_rate", 0.5)
    rolls = iter([0.0, 0.0])  # дві перші перевірки — збій, далі 0.9 — без збоїв
    monkeypatch.setattr(mock.random, "random", lambda: next(rolls, 0.9))
    ticket_id = await approved(session_factory)
    await drain(session_factory, helpdesk)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts) == ("sent", 2)
    assert len(mock_replies_for("T-7")) == 1


class TimeoutAfterDelivery(httpx.AsyncBaseTransport):
    """Перший запит доходить до мока, але клієнт отримує таймаут — як при повільному хелпдеску."""

    def __init__(self, inner: httpx.AsyncBaseTransport):
        self.inner = inner
        self.keys: list[str] = []

    async def handle_async_request(self, request):
        self.keys.append(request.headers["idempotency-key"])
        response = await self.inner.handle_async_request(request)
        if len(self.keys) == 1:
            await response.aread()
            raise httpx.ReadTimeout("helpdesk too slow", request=request)
        return response


async def test_scenario_timeout_but_accepted(session_factory, helpdesk):
    """Сценарій «Таймаут, але відповідь прийнята»."""
    transport = TimeoutAfterDelivery(ASGITransport(app=app))
    ticket_id = await approved(session_factory)
    async with httpx.AsyncClient(transport=transport) as c:
        await drain(session_factory, c)
    ticket = await get(session_factory, ticket_id)
    assert ticket.status == "sent"
    assert transport.keys == [str(ticket.idempotency_key)] * 2
    assert len(mock_replies_for("T-7")) == 1


async def test_scenario_attempts_exhausted(session_factory, helpdesk, monkeypatch):
    """Сценарій «Вичерпані спроби надсилання»."""
    monkeypatch.setattr(settings, "mock_fail_rate", 1)
    ticket_id = await approved(session_factory, attempts=7)
    await drain(session_factory, helpdesk, rounds=1)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts) == ("send_failed", 8)


async def test_scenario_helpdesk_404(session_factory, helpdesk):
    """Сценарій «Хелпдеск відповідає 404»."""
    ticket_id = await add_ticket(
        session_factory,
        status="approved",
        final_message="x",
        idempotency_key=uuid.uuid4(),
        reply_url="http://test/mock/helpdesk/no-such-endpoint",
    )
    await drain(session_factory, helpdesk)
    ticket = await get(session_factory, ticket_id)
    assert ticket.status == "send_failed" and "404" in ticket.last_error
