"""Сід бази знань: статті з `kb/articles/*.md` → таблиця `kb_articles` (upsert за `slug`).

Запускається сервісом `migrate` після міграцій: `python -m scripts.seed_kb`.
"""

import asyncio
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import KbArticle

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "kb" / "articles"
REQUIRED_FIELDS = ("slug", "title", "url")


def load_articles(directory: Path) -> list[dict]:
    """Читає статті: front-matter `key: value` між рядками `---`, далі — тіло."""
    articles = []
    for path in sorted(directory.glob("*.md")):
        _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
        meta = dict(line.split(":", 1) for line in front.splitlines() if ":" in line)
        meta = {key.strip(): value.strip() for key, value in meta.items()}
        for field in REQUIRED_FIELDS:
            if not meta.get(field):
                raise ValueError(f"{path.name}: немає поля {field}")
        articles.append({**{f: meta[f] for f in REQUIRED_FIELDS}, "body": body.strip()})
    return articles


async def seed(session: AsyncSession, articles: list[dict]) -> None:
    """Вставляє нові статті й оновлює наявні за `slug`; повторний запуск дублів не створює."""
    if not articles:
        return
    stmt = insert(KbArticle).values(articles)
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"],
        set_={"title": stmt.excluded.title, "body": stmt.excluded.body, "url": stmt.excluded.url},
    )
    await session.execute(stmt)
    await session.commit()


async def main() -> None:
    articles = load_articles(ARTICLES_DIR)
    async with SessionLocal() as session:
        await seed(session, articles)
    print(f"seeded {len(articles)} kb articles")


if __name__ == "__main__":
    asyncio.run(main())
