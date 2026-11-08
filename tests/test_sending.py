"""Тести черги надсилання: захоплення, успіх, повтори, відмова."""

import uuid
from datetime import timedelta

import httpx
from sqlalchemy import update

from app.models import Ticket

from app.worker.sending import LEASE_S, claim, process
from tests.test_generation import add_ticket, get, now


async def approved(factory, **fields) -> int:
    return await add_ticket(
        factory,
        status="approved",
        final_message="Відповідь",
        idempotency_key=uuid.uuid4(),
        reply_url="http://helpdesk/tickets/T-1/replies",
        **fields,
    )


def client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def claim_one(factory):
    async with factory() as s:
        (ticket,) = await claim(s, 1)
    return ticket


async def test_claim_marks_sending_with_lease(session_factory):
    ticket_id = await approved(session_factory)
    await add_ticket(session_factory, n=2, status="draft_ready")
    ticket = await claim_one(session_factory)
    assert ticket.id == ticket_id
    stored = await get(session_factory, ticket_id)
    assert stored.status == "sending"
    assert stored.locked_until > now() + timedelta(seconds=LEASE_S - 10)


async def test_claim_retakes_expired_sending(session_factory):
    ticket_id = await approved(session_factory, n=1)
    async with session_factory() as s:
        await s.execute(update(Ticket).values(status="sending", locked_until=now() - timedelta(seconds=1)))
        await s.commit()
    assert (await claim_one(session_factory)).id == ticket_id


async def test_success_marks_sent(session_factory):
    ticket_id = await approved(session_factory)
    seen = []

    def handler(request):
        seen.append(request.headers["idempotency-key"])
        return httpx.Response(201)

    async with client(handler) as c:
        await process(session_factory, await claim_one(session_factory), c)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.locked_until) == ("sent", None)
    assert seen == [str(ticket.idempotency_key)]


async def test_server_error_schedules_retry(session_factory):
    ticket_id = await approved(session_factory)
    async with client(lambda r: httpx.Response(500)) as c:
        await process(session_factory, await claim_one(session_factory), c)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts, ticket.locked_until) == ("approved", 1, None)
    assert "500" in ticket.last_error
    assert ticket.next_attempt_at - now() <= timedelta(seconds=1)


async def test_eighth_failure_is_final(session_factory):
    ticket_id = await approved(session_factory, attempts=7)
    async with client(lambda r: httpx.Response(503)) as c:
        await process(session_factory, await claim_one(session_factory), c)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts) == ("send_failed", 8)


async def test_client_error_is_final(session_factory):
    ticket_id = await approved(session_factory)
    async with client(lambda r: httpx.Response(404)) as c:
        await process(session_factory, await claim_one(session_factory), c)
    ticket = await get(session_factory, ticket_id)
    assert ticket.status == "send_failed"
    assert "404" in ticket.last_error
