"""Юніт-тести скрипта `scripts/send_webhooks.py` без мережі і БД."""

import httpx

from scripts.send_webhooks import build_events, latency_summary, send_all


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

    counts, durations = await send_all(build_events(3, 0, "http://x"), "http://x/webhooks/helpdesk", 2, httpx.MockTransport(fail))
    assert counts == {"error": 3}
    assert durations == []  # мережеві помилки не входять у затримки


def test_latency_summary_empty():
    assert latency_summary([]) is None


def test_latency_summary_percentiles():
    durations = [i / 1000 for i in range(1, 101)]  # 1..100 мс
    assert latency_summary(durations) == "latency ms: p50=50 p99=99 max=100"


def test_latency_summary_single_value():
    assert latency_summary([0.012]) == "latency ms: p50=12 p99=12 max=12"


async def test_successful_requests_are_timed():
    counts, durations = await send_all(
        build_events(4, 0, "http://x"), "http://x/webhooks/helpdesk", 2, httpx.MockTransport(lambda r: httpx.Response(202))
    )
    assert counts == {202: 4}
    assert len(durations) == 4 and all(d >= 0 for d in durations)
