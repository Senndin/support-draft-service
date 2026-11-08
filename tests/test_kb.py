"""Тести пошуку по базі знань."""

from sqlalchemy import func, select

from app.models import KbArticle
from app.services.kb import search, to_query


def test_to_query_prefixes_and_drops_short_words():
    assert to_query("Не можу експортувати звіт у PDF") == "можу:* | експо:* | звіт:* | pdf:*"


def test_to_query_empty_for_no_words():
    assert to_query("у, і ?!") == ""


async def slugs(kb, query, **kw):
    async with kb() as session:
        return [a.slug for a in await search(session, query, **kw)]


async def test_export_pdf_first(kb):
    found = await slugs(kb, "Не можу експортувати звіт у PDF")
    assert found[0] == "export-pdf"
    assert len(found) <= 3


async def test_limit(kb):
    assert len(await slugs(kb, "оплата підписки карткою", limit=1)) == 1


async def test_typo_falls_back_to_trigram(kb):
    query = "інтрегація зі слек"
    async with kb() as session:
        fts_hits = await session.scalar(
            select(func.count()).select_from(KbArticle).where(
                KbArticle.search_vector.op("@@")(func.to_tsquery("simple", to_query(query)))
            )
        )
    assert fts_hits == 0  # FTS не знаходить — спрацьовує fallback
    assert (await slugs(kb, query))[0] == "slack-integration"


async def test_nothing_found(kb):
    assert await slugs(kb, "qwxzv") == []
