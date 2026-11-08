"""End-to-end сценарії `llm-draft`, `llm-rate-limit` і `draft-generation`."""

import asyncio
import json
import time
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import KbArticle
from app.services import llm
from app.services.llm import LLMError, generate_draft
from app.services.ratelimit import RateLimiter
from app.worker import generation
from app.worker.generation import claim, process, run
from tests.test_generation import add_ticket, get, now, wait_status


@pytest.fixture
def llm_env(monkeypatch):
    """Налаштування LLM для сценаріїв; за замовчуванням — з ключем."""
    monkeypatch.setattr(settings, "llm_api_key", "secret")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "http://llm/v1")
    monkeypatch.setattr(settings, "stub_delay_min_s", 0)
    monkeypatch.setattr(settings, "stub_delay_max_s", 0)
    llm.reset_limits()
    return monkeypatch


async def kb_articles(kb, *slugs) -> list[KbArticle]:
    async with kb() as s:
        rows = (await s.scalars(select(KbArticle).where(KbArticle.slug.in_(slugs)).order_by(KbArticle.slug))).all()
    return list(rows)


def client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --- llm-draft ---


async def test_scenario_provider_answer(kb, llm_env):
    """Сценарій «Відповідь провайдера»."""
    articles = await kb_articles(kb, "export-pdf", "payment-billing")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Чернетка"}}]})

    async with client(handler) as c:
        result = await generate_draft("Не можу експортувати звіт", articles, c)
    assert result.text == "Чернетка"
    assert sorted(result.article_ids) == sorted(a.id for a in articles)
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "test-model"
    assert all(a.url in seen["body"]["messages"][-1]["content"] for a in articles)


async def test_scenario_provider_500(llm_env):
    """Сценарій «Провайдер повертає 500»."""
    async with client(lambda r: httpx.Response(500)) as c:
        with pytest.raises(LLMError, match="500"):
            await generate_draft("питання", [], c)


async def test_scenario_stub_draft_with_articles(kb, llm_env):
    """Сценарій «Статична чернетка зі статтями»."""
    llm_env.setattr(settings, "llm_api_key", "")
    articles = await kb_articles(kb, "export-pdf", "payment-billing")
    auth = []

    def handler(request):
        auth.append(request.headers.get("authorization"))
        return httpx.Response(401)

    async with client(handler) as c:
        result = await generate_draft("Не можу експортувати звіт", articles, c)
    assert auth == [None]
    assert all(a.title in result.text and a.url in result.text for a in articles)
    assert sorted(result.article_ids) == sorted(a.id for a in articles)


async def test_scenario_stub_provider_unreachable(kb, llm_env):
    """Сценарій «Провайдер недоступний без ключа»."""
    llm_env.setattr(settings, "llm_api_key", "")
    articles = await kb_articles(kb, "export-pdf")

    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    async with client(handler) as c:
        result = await generate_draft("питання", articles, c)
    assert articles[0].url in result.text


async def test_scenario_no_articles(llm_env):
    """Сценарій «Статей немає»."""
    llm_env.setattr(settings, "llm_api_key", "")
    async with client(lambda r: httpx.Response(401)) as c:
        result = await generate_draft("питання", [], c)
    assert "оператор" in result.text
    assert result.article_ids == []


# --- llm-rate-limit ---


async def test_scenario_rate_exceeded():
    """Сценарій «Перевищення ліміту»: 6 викликів при ліміті 3 за 0.5 с."""
    limiter = RateLimiter(3, 0.5)
    start = time.monotonic()
    stamps = []

    async def call():
        await limiter.acquire()
        stamps.append(time.monotonic() - start)

    await asyncio.gather(*(call() for _ in range(6)))
    stamps.sort()
    assert stamps[2] < 0.1 and stamps[3] >= 0.5
    assert all(sum(1 for s in stamps if t <= s < t + 0.5 - 1e-3) <= 3 for t in stamps)


async def test_scenario_parallel_generations(llm_env):
    """Сценарій «Паралельні генерації»: LLM_CONCURRENCY=2, 5 генерацій."""
    llm_env.setattr(settings, "llm_concurrency", 2)
    llm.reset_limits()
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.05)
        active -= 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with client(handler) as c:
        await asyncio.gather(*(generate_draft("питання", [], c) for _ in range(5)))
    assert peak == 2


# --- draft-generation ---


@pytest.fixture
def stub_client(llm_env):
    llm_env.setattr(settings, "llm_api_key", "")
    return client(lambda r: httpx.Response(401))


async def test_scenario_received_to_draft_ready(kb, session_factory, stub_client):
    """Сценарій «Від received до draft_ready»."""
    ticket_id = await add_ticket(session_factory, message="Не можу експортувати звіт у PDF")
    stop = asyncio.Event()
    worker = asyncio.create_task(run(session_factory, stub_client, stop))
    ticket = await wait_status(session_factory, ticket_id, "draft_ready")
    stop.set()
    await worker
    (export,) = await kb_articles(kb, "export-pdf")
    assert export.url in ticket.draft
    assert export.id in ticket.article_ids


async def test_scenario_concurrent_claims(session_factory):
    """Сценарій «Два одночасні захоплення»."""
    for n in range(4):
        await add_ticket(session_factory, n=n)

    async def take():
        async with session_factory() as s:
            return {t.id for t in await claim(s, 4)}

    a, b = await asyncio.gather(take(), take())
    assert not a & b and len(a | b) == 4


async def test_scenario_expired_lease(session_factory):
    """Сценарій «Повторне захоплення»."""
    ticket_id = await add_ticket(session_factory, status="generating", locked_until=now() - timedelta(seconds=5))
    async with session_factory() as s:
        claimed = await claim(s, 10)
    assert [t.id for t in claimed] == [ticket_id]
    assert (await get(session_factory, ticket_id)).locked_until > now()


@pytest.fixture
def failing(monkeypatch, stub_client):
    async def boom(*args, **kwargs):
        raise LLMError("LLM відповів 500")

    monkeypatch.setattr(generation, "generate_draft", boom)
    return stub_client


async def claim_and_process(factory, c):
    async with factory() as s:
        (ticket,) = await claim(s, 1)
    await process(factory, ticket, c)


async def test_scenario_temporary_error(kb, session_factory, failing):
    """Сценарій «Тимчасова помилка»."""
    ticket_id = await add_ticket(session_factory)
    await claim_and_process(session_factory, failing)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts) == ("received", 1)
    assert ticket.last_error
    assert timedelta(seconds=8) < ticket.next_attempt_at - now() <= timedelta(seconds=10)


async def test_scenario_attempts_exhausted(kb, session_factory, failing):
    """Сценарій «Вичерпані спроби»."""
    ticket_id = await add_ticket(session_factory, attempts=4)
    await claim_and_process(session_factory, failing)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.attempts) == ("generation_failed", 5)
    async with session_factory() as s:
        assert await claim(s, 10) == []


async def test_scenario_stop_during_generation(kb, session_factory, stub_client, monkeypatch):
    """Сценарій «Зупинка під час генерації»."""

    async def slow(*args, **kwargs):
        await asyncio.sleep(30)

    monkeypatch.setattr(generation, "generate_draft", slow)
    monkeypatch.setattr(generation, "SHUTDOWN_GRACE_S", 0.1)
    ticket_id = await add_ticket(session_factory)
    stop = asyncio.Event()
    worker = asyncio.create_task(run(session_factory, stub_client, stop))
    await wait_status(session_factory, ticket_id, "generating")
    stop.set()
    await asyncio.wait_for(worker, timeout=3)
    ticket = await get(session_factory, ticket_id)
    assert (ticket.status, ticket.locked_until) == ("received", None)
