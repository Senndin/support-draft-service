"""Воркер: працює до SIGTERM і завершується штатно (сценарій «Воркер працює до зупинки»)."""

import asyncio
import os
import signal

from app.worker.__main__ import main


async def test_worker_stops_on_sigterm(session_factory):
    task = asyncio.create_task(main(session_factory))
    await asyncio.sleep(0.2)  # даємо main() встановити обробники сигналів
    assert not task.done()
    os.kill(os.getpid(), signal.SIGTERM)
    await asyncio.wait_for(task, timeout=5)


async def test_worker_sends_approved_replies(session_factory):
    import uuid

    import httpx

    from tests.test_generation import add_ticket, wait_status

    ticket_id = await add_ticket(session_factory, status="approved", final_message="Відповідь", idempotency_key=uuid.uuid4())
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(201)))
    task = asyncio.create_task(main(session_factory, client))
    await wait_status(session_factory, ticket_id, "sent")
    os.kill(os.getpid(), signal.SIGTERM)
    await asyncio.wait_for(task, timeout=5)
