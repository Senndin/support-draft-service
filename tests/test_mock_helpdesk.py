"""Тести мока хелпдеску."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.mock_helpdesk import routes as mock

URL = "/mock/helpdesk/tickets/T-1/replies"


@pytest.fixture
async def mock_client(monkeypatch):
    """Клієнт до мока з чистим сховищем і без збоїв."""
    mock.reset()
    monkeypatch.setattr(settings, "mock_fail_rate", 0)
    monkeypatch.setattr(settings, "mock_slow_rate", 0)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def replies(c) -> list[dict]:
    return (await c.get("/mock/helpdesk/replies")).json()


async def test_new_reply(mock_client):
    r = await mock_client.post(URL, json={"message": "Відповідь"}, headers={"Idempotency-Key": "k1"})
    assert r.status_code == 201
    body = r.json()
    assert (body["ticket_id"], body["message"], body["idempotency_key"]) == ("T-1", "Відповідь", "k1")
    assert [x["id"] for x in await replies(mock_client)] == [body["id"]]


async def test_same_key_is_deduplicated(mock_client):
    first = await mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "k1"})
    second = await mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "k1"})
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert len(await replies(mock_client)) == 1


async def test_without_key_every_request_is_stored(mock_client):
    await mock_client.post(URL, json={"message": "A"})
    await mock_client.post(URL, json={"message": "A"})
    assert len(await replies(mock_client)) == 2


async def test_fail_rate(mock_client, monkeypatch):
    monkeypatch.setattr(settings, "mock_fail_rate", 1)
    r = await mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "k1"})
    assert r.status_code == 500
    assert await replies(mock_client) == []


async def test_slow_reply_is_stored_before_delay(mock_client, monkeypatch):
    monkeypatch.setattr(settings, "mock_slow_rate", 1)
    monkeypatch.setattr(settings, "helpdesk_timeout_s", 5)  # затримка 10 с
    slow = asyncio.create_task(mock_client.post(URL, json={"message": "A"}, headers={"Idempotency-Key": "k1"}))
    await asyncio.sleep(0.2)
    monkeypatch.setattr(settings, "mock_slow_rate", 0)
    assert [x["idempotency_key"] for x in await replies(mock_client)] == ["k1"]
    slow.cancel()
