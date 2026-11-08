"""Тести `POST /webhooks/helpdesk` на тестовій БД."""

import pytest
from sqlalchemy import func, select

from app.models import Ticket


def event(**overrides) -> dict:
    """Валідна подія хелпдеску; поля можна перевизначити."""
    body = {
        "event_id": "evt-1",
        "ticket_id": "T-1",
        "customer_email": "client@example.com",
        "message": "Не можу експортувати звіт у PDF",
        "reply_url": "http://api:8000/mock/helpdesk/tickets/T-1/replies",
    }
    body.update(overrides)
    return body


async def count_tickets(session_factory) -> int:
    async with session_factory() as s:
        return await s.scalar(select(func.count()).select_from(Ticket))


async def test_new_event_is_stored(client, session_factory):
    response = await client.post("/webhooks/helpdesk", json=event())
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    async with session_factory() as s:
        ticket = await s.scalar(select(Ticket))
    assert (ticket.event_id, ticket.ticket_id, ticket.status) == ("evt-1", "T-1", "received")
    assert ticket.reply_url == "http://api:8000/mock/helpdesk/tickets/T-1/replies"


async def test_duplicate_keeps_first_version(client, session_factory):
    await client.post("/webhooks/helpdesk", json=event())
    response = await client.post("/webhooks/helpdesk", json=event(message="інший текст"))
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    async with session_factory() as s:
        messages = (await s.scalars(select(Ticket.message))).all()
    assert messages == ["Не можу експортувати звіт у PDF"]


@pytest.mark.parametrize(
    "body",
    [
        {k: v for k, v in event().items() if k != "event_id"},
        event(message="   "),
        event(reply_url="not-a-url"),
    ],
    ids=["missing-event_id", "blank-message", "bad-reply_url"],
)
async def test_invalid_body_is_rejected(client, session_factory, body):
    response = await client.post("/webhooks/helpdesk", json=body)
    assert response.status_code == 422
    assert await count_tickets(session_factory) == 0
