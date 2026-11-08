"""End-to-end сценарії `operator-ui`, `moderation` і `operator-auth`."""

import asyncio

import pytest

from app.config import settings
from tests.test_generation import add_ticket, get
from tests.test_ui import draft_ticket, export_article
from tests.test_webhooks import event

# --- operator-ui ---


async def test_scenario_ticket_in_list(client, session_factory, kb):
    """Сценарій «Звернення з чернеткою в списку»."""
    await draft_ticket(session_factory, kb)
    article = await export_article(kb)
    page = (await client.get("/ui")).text
    for text in ("draft_ready", "T-1", "c@example.com", "Не можу експортувати звіт у PDF", "Текст чернетки", article.title, article.url):
        assert text in page
    assert '<meta http-equiv="refresh" content="10">' in page


async def test_scenario_filter_draft_ready(client, session_factory, kb):
    """Сценарій «Фільтр draft_ready»."""
    await draft_ticket(session_factory, kb, n=1)
    await add_ticket(session_factory, n=2, ticket_id="T-2")
    page = (await client.get("/ui?status=draft_ready")).text
    assert "T-1" in page and "T-2" not in page


async def test_scenario_card_with_draft(client, session_factory, kb):
    """Сценарій «Картка з чернеткою»."""
    ticket_id = await draft_ticket(session_factory, kb)
    page = (await client.get(f"/ui/tickets/{ticket_id}")).text
    assert "Текст чернетки</textarea>" in page
    assert ">Approve<" in page and ">Reject<" in page


async def test_scenario_unknown_ticket(client, session_factory):
    """Сценарій «Неіснуюче звернення»."""
    assert (await client.get("/ui/tickets/999")).status_code == 404


# --- moderation ---


async def draft(factory) -> int:
    return await add_ticket(factory, status="draft_ready", draft="Чернетка")


async def test_scenario_approve_with_edit(client, session_factory):
    """Сценарій «Підтвердження з правкою»."""
    ticket_id = await draft(session_factory)
    r = await client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "Виправлена відповідь"})
    assert (r.status_code, r.headers["location"]) == (303, f"/ui/tickets/{ticket_id}")
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.final_message) == ("approved", "Виправлена відповідь")
    assert ticket.idempotency_key


async def test_scenario_blank_text(client, session_factory):
    """Сценарій «Порожній текст»."""
    ticket_id = await draft(session_factory)
    assert (await client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "  "})).status_code == 422
    assert (await get(session_factory, ticket_id)).status == "draft_ready"


async def test_scenario_reject(client, session_factory):
    """Сценарій «Відхилення»."""
    ticket_id = await draft(session_factory)
    assert (await client.post(f"/ui/tickets/{ticket_id}/reject")).status_code == 303
    assert (await get(session_factory, ticket_id)).status == "rejected"


async def test_scenario_two_parallel_approves(client, session_factory):
    """Сценарій «Два паралельні approve»."""
    ticket_id = await draft(session_factory)
    r1, r2 = await asyncio.gather(
        client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "Перша вкладка"}),
        client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "Друга вкладка"}),
    )
    assert sorted([r1.status_code, r2.status_code]) == [303, 409]
    winner = "Перша вкладка" if r1.status_code == 303 else "Друга вкладка"
    assert (await get(session_factory, ticket_id)).final_message == winner


async def test_scenario_approve_after_reject(client, session_factory):
    """Сценарій «Approve після reject»."""
    ticket_id = await add_ticket(session_factory, status="rejected")
    r = await client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "Текст"})
    assert r.status_code == 409 and "rejected" in r.text
    assert (await get(session_factory, ticket_id)).status == "rejected"


# --- operator-auth ---


@pytest.fixture
def password(monkeypatch):
    monkeypatch.setattr(settings, "operator_password", "s3cret")


async def test_scenario_no_password_denied(client, password):
    """Сценарій «Без пароля відмова»."""
    r = await client.get("/ui")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Basic"


async def test_scenario_password_grants_access(client, password):
    """Сценарій «З паролем доступ»."""
    assert (await client.get("/ui", auth=("operator", "s3cret"))).status_code == 200


async def test_scenario_protection_disabled(client, monkeypatch):
    """Сценарій «Захист вимкнено»."""
    monkeypatch.setattr(settings, "operator_password", "")
    assert (await client.get("/ui")).status_code == 200


async def test_scenario_webhook_without_auth(client, password):
    """Сценарій «Вебхук без автентифікації»."""
    assert (await client.post("/webhooks/helpdesk", json=event(event_id="auth-e2e"))).status_code == 202
