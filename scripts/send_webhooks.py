"""Імітатор хелпдеску: надсилає пакет подій на вебхук, частину з дублями й одночасно.

Приклад: uv run python -m scripts.send_webhooks --count 500 --dup-rate 0.2 --concurrency 50
"""

import argparse
import asyncio
import random
import statistics
import time
import uuid
from collections import Counter

import httpx


def build_events(count: int, dup_rate: float, reply_base: str) -> list[dict]:
    """`count` унікальних подій плюс `round(count * dup_rate)` копій, перемішані між собою."""
    events = []
    for i in range(count):
        ticket_id = f"T-{i + 1}"
        events.append(
            {
                "event_id": str(uuid.uuid4()),
                "ticket_id": ticket_id,
                "customer_email": f"client{i + 1}@example.com",
                "message": "Не можу експортувати звіт у PDF",
                "reply_url": f"{reply_base}/mock/helpdesk/tickets/{ticket_id}/replies",
            }
        )
    duplicates = random.choices(events, k=round(count * dup_rate)) if events else []
    batch = events + [dict(e) for e in duplicates]
    # перемішування: дублі йдуть упереміш з оригіналами, частина — одночасно
    random.shuffle(batch)
    return batch


async def send_all(
    events: list[dict], url: str, concurrency: int, transport: httpx.AsyncBaseTransport | None = None
) -> tuple[Counter, list[float]]:
    """Надсилає події не більше ніж `concurrency` одночасно.

    Повертає лічильник відповідей за статусом (мережеві помилки — `"error"`) і тривалості
    в секундах запитів, що отримали HTTP-відповідь.
    """
    counts: Counter = Counter()
    durations: list[float] = []
    limit = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(transport=transport, timeout=10) as client:

        async def send(event: dict) -> None:
            async with limit:
                started = time.perf_counter()
                try:
                    response = await client.post(url, json=event)
                except httpx.HTTPError:
                    counts["error"] += 1
                    return
                durations.append(time.perf_counter() - started)
                counts[response.status_code] += 1

        await asyncio.gather(*(send(e) for e in events))
    return counts, durations


def latency_summary(durations: list[float]) -> str | None:
    """`latency ms: p50=… p99=… max=…` у цілих мілісекундах; `None`, якщо вимірів немає."""
    if not durations:
        return None
    ms = [d * 1000 for d in durations]
    if len(ms) == 1:
        p50 = p99 = ms[0]
    else:
        cuts = statistics.quantiles(ms, n=100, method="inclusive")
        p50, p99 = cuts[49], cuts[98]
    return f"latency ms: p50={round(p50)} p99={round(p99)} max={round(max(ms))}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000/webhooks/helpdesk")
    parser.add_argument("--count", type=int, default=10, help="кількість унікальних подій")
    parser.add_argument("--dup-rate", type=float, default=0.2, help="частка повторних подій, 0..1")
    parser.add_argument("--concurrency", type=int, default=10, help="максимум одночасних запитів")
    parser.add_argument("--reply-base", default="http://api:8000", help="адреса api для reply_url (мок хелпдеску)")
    args = parser.parse_args()

    events = build_events(args.count, args.dup_rate, args.reply_base)
    counts, durations = asyncio.run(send_all(events, args.url, args.concurrency))
    print(f"sent: {len(events)}")
    for status, n in sorted(counts.items(), key=lambda item: str(item[0])):
        print(f"{status}: {n}")
    if summary := latency_summary(durations):
        print(summary)


if __name__ == "__main__":
    main()
