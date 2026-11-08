"""Пошук статей бази знань за текстом звернення.

Спершу повнотекстовий пошук PostgreSQL (конфігурація `simple`), якщо нічого
не знайдено — нечіткий пошук за триграмами (`pg_trgm`, стійкий до опечаток).
"""

import re

from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KbArticle

MIN_WORD = 3
PREFIX = 5
TRIGRAM_THRESHOLD = 0.3  # дефолтний поріг word_similarity у pg_trgm


def to_query(text: str) -> str:
    """Перетворює текст на tsquery: слова від 3 літер → префікси з `:*`, об'єднані через OR.

    ponytail: префікс із 5 символів — грубий стемінг для української
    («експортувати» ~ «експорт»); для великої бази — словник hunspell або ембеддинги.
    """
    words = [w for w in re.findall(r"\w+", text.lower()) if len(w) >= MIN_WORD]
    return " | ".join(f"{w[:PREFIX]}:*" for w in words)


async def search(session: AsyncSession, query: str, limit: int = 3) -> list[KbArticle]:
    """До `limit` найрелевантніших статей; порожній список, якщо збігів немає."""
    if tsquery := to_query(query):
        ts = func.to_tsquery("simple", tsquery)
        found = (
            await session.scalars(
                select(KbArticle)
                .where(KbArticle.search_vector.op("@@")(ts))
                .order_by(func.ts_rank(KbArticle.search_vector, ts).desc())
                .limit(limit)
            )
        ).all()
        if found:
            return list(found)

    # ponytail: без триграмного індексу — повний скан; додати gin_trgm_ops, коли статей будуть сотні
    similarity = func.word_similarity(literal(query), KbArticle.title + " " + KbArticle.body)
    return list(
        (
            await session.scalars(
                select(KbArticle).where(similarity > TRIGRAM_THRESHOLD).order_by(similarity.desc()).limit(limit)
            )
        ).all()
    )
