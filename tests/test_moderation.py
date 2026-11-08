"""Тести approve/reject: атомарний перехід зі статусу `draft_ready`."""

from tests.test_generation import add_ticket, get


async def draft(factory, **fields) -> int:
    return await add_ticket(factory, status="draft_ready", draft="Чернетка", **fields)


async def test_approve_with_edit(client, session_factory):
    ticket_id = await draft(session_factory)
    r = await client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "  Виправлена відповідь  "})
    assert (r.status_code, r.headers["location"]) == (303, f"/ui/tickets/{ticket_id}")
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.final_message) == ("approved", "Виправлена відповідь")
    assert ticket.idempotency_key is not None


async def test_reject(client, session_factory):
    ticket_id = await draft(session_factory)
    r = await client.post(f"/ui/tickets/{ticket_id}/reject")
    assert r.status_code == 303
    assert (await get(session_factory, ticket_id)).status == "rejected"


async def test_blank_message_rejected(client, session_factory):
    ticket_id = await draft(session_factory)
    r = await client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "   "})
    assert r.status_code == 422
    assert (await get(session_factory, ticket_id)).status == "draft_ready"


async def test_approve_after_reject_conflicts(client, session_factory):
    ticket_id = await add_ticket(session_factory, status="rejected")
    r = await client.post(f"/ui/tickets/{ticket_id}/approve", data={"final_message": "Текст"})
    assert r.status_code == 409
    assert "rejected" in r.text and f"/ui/tickets/{ticket_id}" in r.text
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.final_message) == ("rejected", None)


async def test_unknown_ticket_404(client, session_factory):
    assert (await client.post("/ui/tickets/999/reject")).status_code == 404
    assert (await client.post("/ui/tickets/999/approve", data={"final_message": "x"})).status_code == 404
