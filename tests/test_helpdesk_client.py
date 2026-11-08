"""Тести клієнта надсилання відповіді в хелпдеск."""

import json

import httpx
import pytest

from app.services.helpdesk import SendError, send_reply


def client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_sends_message_with_key():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), key=request.headers["idempotency-key"], body=json.loads(request.content))
        return httpx.Response(201, json={"id": 1})

    async with client(handler) as c:
        await send_reply(c, "http://h/tickets/T-1/replies", "Відповідь", "k-1")
    assert seen == {"url": "http://h/tickets/T-1/replies", "key": "k-1", "body": {"message": "Відповідь"}}


def raise_(exc_type):
    def handler(request):
        raise exc_type("boom", request=request)

    return handler


@pytest.mark.parametrize(
    "handler, retryable",
    [
        (lambda r: httpx.Response(500), True),
        (lambda r: httpx.Response(503), True),
        (lambda r: httpx.Response(408), True),
        (lambda r: httpx.Response(429), True),
        (raise_(httpx.ReadTimeout), True),
        (raise_(httpx.ConnectError), True),
        (lambda r: httpx.Response(404), False),
        (lambda r: httpx.Response(400), False),
    ],
    ids=["500", "503", "408", "429", "timeout", "connect", "404", "400"],
)
async def test_errors_are_classified(handler, retryable):
    async with client(handler) as c:
        with pytest.raises(SendError) as exc:
            await send_reply(c, "http://h/r", "x", "k")
    assert exc.value.retryable is retryable
