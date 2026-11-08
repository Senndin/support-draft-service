"""Генерація чернетки відповіді через OpenAI-сумісний API (`POST {LLM_BASE_URL}/chat/completions`).

Провайдер змінюється лише змінними оточення. Усі виклики проходять через
глобальний лімітер `LLM_RPM`/хв і семафор `LLM_CONCURRENCY`.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from functools import cache

import httpx

from app.config import settings
from app.models import KbArticle
from app.services.ratelimit import RateLimiter

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ти агент підтримки продукту ReportFlow. Відповідай мовою клієнта, коротко, "
    "лише на основі наданих статей. Обов'язково додай посилання на використані статті. "
    "Якщо статті не покривають питання — чесно скажи і запропонуй звернутись до оператора."
)


@dataclass
class DraftResult:
    """Чернетка і `id` статей, переданих у LLM."""

    text: str
    article_ids: list[int]


class LLMError(Exception):
    """Провайдер не дав чернетки: таймаут, мережа, не-2xx або неочікувана відповідь."""


@cache
def _limits() -> tuple[RateLimiter, asyncio.Semaphore]:
    """Лімітер і семафор на весь процес, створюються при першому виклику."""
    return RateLimiter(settings.llm_rpm, 60), asyncio.Semaphore(settings.llm_concurrency)


def reset_limits() -> None:
    """Скидає ліміти (для тестів зі зміненими налаштуваннями)."""
    _limits.cache_clear()


def build_messages(message: str, articles: list[KbArticle]) -> list[dict]:
    """Промпт: системна інструкція + звернення і статті у форматі `[id] title — url` з тілом."""
    kb = "\n\n".join(f"[{a.id}] {a.title} — {a.url}\n{a.body}" for a in articles) or "Статей не знайдено."
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Звернення клієнта:\n{message}\n\nСтатті бази знань:\n{kb}"},
    ]


async def _call_provider(client: httpx.AsyncClient, messages: list[dict], api_key: str) -> httpx.Response:
    """Один запит до провайдера в межах ліміту частоти й паралельності."""
    limiter, semaphore = _limits()
    await limiter.acquire()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {"model": settings.llm_model, "messages": messages}
    if settings.llm_reasoning_effort:
        payload["reasoning_effort"] = settings.llm_reasoning_effort
    async with semaphore:
        return await client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=settings.llm_timeout_s,
        )


def stub_draft(articles: list[KbArticle]) -> str:
    """Статична чернетка режиму без ключа: назви й посилання знайдених статей."""
    if not articles:
        return (
            "Вітаємо! На жаль, у нашій базі знань немає статті з відповіддю на ваше питання. "
            "Ми передали звернення оператору — він зв'яжеться з вами найближчим часом."
        )
    links = "\n".join(f"- {a.title}: {a.url}" for a in articles)
    return f"Вітаємо! Відповідь на ваше питання є в статтях бази знань:\n{links}\nЯкщо це не допомогло — напишіть нам, і оператор допоможе."


async def generate_draft(message: str, articles: list[KbArticle], client: httpx.AsyncClient) -> DraftResult:
    """Чернетка для звернення на основі статей; `LLMError`, якщо провайдер не відповів як слід.

    Без `LLM_API_KEY` реальний запит усе одно надсилається (без Authorization, через ті самі
    ліміти), але його результат ігнорується: після затримки повертається статична чернетка.
    """
    messages = build_messages(message, articles)
    article_ids = [a.id for a in articles]
    if not settings.llm_api_key:
        try:
            response = await _call_provider(client, messages, "")
            log.info("LLM без ключа відповів %s (ігноруємо)", response.status_code)
        except httpx.HTTPError as exc:
            log.info("LLM без ключа недоступний: %r (ігноруємо)", exc)
        await asyncio.sleep(random.uniform(settings.stub_delay_min_s, settings.stub_delay_max_s))
        return DraftResult(text=stub_draft(articles), article_ids=article_ids)
    try:
        response = await _call_provider(client, messages, settings.llm_api_key)
    except httpx.HTTPError as exc:
        raise LLMError(f"{type(exc).__name__}: {exc}") from exc
    if not response.is_success:
        raise LLMError(f"LLM відповів {response.status_code}: {response.text[:200]}")
    try:
        text = response.json()["choices"][0]["message"]["content"]
        if not text or not text.strip():
            raise ValueError("порожній content")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise LLMError(f"неочікувана відповідь LLM без непорожнього choices[0].message.content: {response.text[:200]}") from exc
    return DraftResult(text=text, article_ids=article_ids)
