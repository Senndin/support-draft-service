"""Тести `generate_draft`: OpenAI-сумісний провайдер через `httpx.MockTransport`."""

import asyncio
import json

import httpx
import pytest

from app.config import settings
from app.models import KbArticle
from app.services import llm
from app.services.llm import LLMError, generate_draft

ARTICLES = [
    KbArticle(id=1, slug="export-pdf", title="Як експортувати звіт у PDF", body="Натисніть Експорт.", url="https://h/export-pdf"),
    KbArticle(id=2, slug="payment-billing", title="Оплата підписки", body="Карткою.", url="https://h/payment-billing"),
]


@pytest.fixture(autouse=True)
def llm_settings(monkeypatch):
    """Ключ, модель і свіжі ліміти для кожного тесту."""
    monkeypatch.setattr(settings, "llm_api_key", "secret")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "http://llm/v1")
    monkeypatch.setattr(settings, "stub_delay_min_s", 0)
    monkeypatch.setattr(settings, "stub_delay_max_s", 0)
    llm.reset_limits()


def client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def completion(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": text}}]})


async def test_provider_answer_becomes_draft():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return completion("Чернетка")

    async with client_for(handler) as client:
        result = await generate_draft("Не можу експортувати звіт", ARTICLES, client)
    assert result == llm.DraftResult(text="Чернетка", article_ids=[1, 2])
    assert seen["url"] == "http://llm/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "test-model"
    user = seen["body"]["messages"][-1]["content"]
    assert "[1] Як експортувати звіт у PDF — https://h/export-pdf" in user
    assert "https://h/payment-billing" in user
    assert "Не можу експортувати звіт" in user


@pytest.mark.parametrize(
    "handler, reason",
    [
        (lambda r: httpx.Response(500, text="boom"), "500"),
        (lambda r: httpx.Response(200, json={"choices": []}), "choices"),
        (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=r)), "ReadTimeout"),
    ],
    ids=["status-500", "no-choices", "timeout"],
)
async def test_provider_errors_raise(handler, reason):
    async with client_for(handler) as client:
        with pytest.raises(LLMError, match=reason):
            await generate_draft("питання", ARTICLES, client)


# --- режим без ключа ---


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")


async def test_stub_draft_lists_articles(no_key):
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(401, json={"error": "no key"})

    async with client_for(handler) as client:
        result = await generate_draft("Не можу експортувати звіт", ARTICLES, client)
    assert seen == {"auth": None}  # запит був, але без Authorization
    for a in ARTICLES:
        assert a.title in result.text and a.url in result.text
    assert result.article_ids == [1, 2]


async def test_stub_survives_unreachable_provider(no_key):
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    async with client_for(handler) as client:
        result = await generate_draft("питання", ARTICLES, client)
    assert ARTICLES[0].url in result.text


async def test_stub_without_articles_offers_operator(no_key):
    async with client_for(lambda r: httpx.Response(401)) as client:
        result = await generate_draft("питання", [], client)
    assert "оператор" in result.text
    assert result.article_ids == []


async def test_stub_delay_is_applied(no_key, monkeypatch):
    monkeypatch.setattr(settings, "stub_delay_min_s", 0.2)
    monkeypatch.setattr(settings, "stub_delay_max_s", 0.2)
    loop = asyncio.get_running_loop()
    started = loop.time()
    async with client_for(lambda r: httpx.Response(401)) as client:
        await generate_draft("питання", ARTICLES, client)
    assert loop.time() - started >= 0.2


async def test_concurrency_limit(no_key, monkeypatch):
    monkeypatch.setattr(settings, "llm_concurrency", 2)
    llm.reset_limits()
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.05)
        active -= 1
        return httpx.Response(401)

    async with client_for(handler) as client:
        await asyncio.gather(*(generate_draft("питання", ARTICLES, client) for _ in range(5)))
    assert peak == 2
