"""End-to-end сценарії `kb-search` і `kb-seed` на тестовій БД."""

import pytest
from sqlalchemy import func, select

from app.models import KbArticle
from app.services.kb import search
from scripts.seed_kb import ARTICLES_DIR, load_articles, seed

FILES = len(list(ARTICLES_DIR.glob("*.md")))


async def found(kb, query, **kw) -> list[str]:
    async with kb() as session:
        return [a.slug for a in await search(session, query, **kw)]


# --- kb-search ---


async def test_scenario_export_pdf(kb):
    """Сценарій «Експорт у PDF»."""
    result = await found(kb, "Не можу експортувати звіт у PDF")
    assert result[0] == "export-pdf"
    assert len(result) <= 3


async def test_scenario_limit(kb):
    """Сценарій «Ліміт»."""
    assert len(await found(kb, "оплата підписки карткою", limit=1)) == 1


async def test_scenario_typo(kb):
    """Сценарій «Опечатка»."""
    assert (await found(kb, "інтрегація зі слек"))[0] == "slack-integration"


async def test_scenario_irrelevant_query(kb):
    """Сценарій «Нерелевантний запит»."""
    assert await found(kb, "qwxzv") == []


# --- kb-seed ---


async def test_scenario_reseed(kb):
    """Сценарій «Повторний сід»."""
    async with kb() as session:
        await seed(session, load_articles(ARTICLES_DIR))
        assert await session.scalar(select(func.count()).select_from(KbArticle)) == FILES


async def test_scenario_update_article(kb, tmp_path):
    """Сценарій «Оновлення статті»: змінений title у файлі потрапляє в БД."""
    for path in ARTICLES_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if path.stem == "export-pdf":
            text = text.replace("title: Як експортувати звіт у PDF", "title: Експорт у PDF (оновлено)")
        (tmp_path / path.name).write_text(text, encoding="utf-8")
    async with kb() as session:
        await seed(session, load_articles(tmp_path))
        title = await session.scalar(select(KbArticle.title).where(KbArticle.slug == "export-pdf"))
        count = await session.scalar(select(func.count()).select_from(KbArticle))
    assert (title, count) == ("Експорт у PDF (оновлено)", FILES)


def test_scenario_article_without_slug(tmp_path):
    """Сценарій «Стаття без slug»."""
    (tmp_path / "no-slug.md").write_text("---\ntitle: T\nurl: https://x\n---\nТіло\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"no-slug\.md: немає поля slug"):
        load_articles(tmp_path)
