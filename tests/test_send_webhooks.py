"""Юніт-тести скрипта `scripts/send_webhooks.py` без мережі і БД."""

import httpx

from scripts.send_webhooks import build_events, send_all


def test_build_events_adds_duplicates():
    events = build_events(20, 0.5, "http://api:8000")
    assert len(events) == 30
    assert len({e["event_id"] for e in events}) == 20
    for e in events:
        assert e["reply_url"] == f"http://api:8000/mock/helpdesk/tickets/{e['ticket_id']}/replies"


def test_build_events_without_duplicates():
    assert len(build_events(5, 0, "http://api:8000")) == 5


async def test_network_errors_are_counted():
    def fail(request):
        raise httpx.ConnectError("refused", request=request)

    counts = await send_all(build_events(3, 0, "http://x"), "http://x/webhooks/helpdesk", 2, httpx.MockTransport(fail))
    assert counts == {"error": 3}
