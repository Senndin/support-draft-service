"""Тести сіду бази знань."""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import KbArticle
from scripts.seed_kb import ARTICLES_DIR, load_articles, seed


def write(tmp_path: Path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text, encoding="utf-8")


def test_load_parses_front_matter(tmp_path):
    write(tmp_path, "a.md", "---\nslug: a\ntitle: Заголовок: з двокрапкою\nurl: https://x/a\n---\nТіло\nстатті\n")
    assert load_articles(tmp_path) == [
        {"slug": "a", "title": "Заголовок: з двокрапкою", "url": "https://x/a", "body": "Тіло\nстатті"}
    ]


def test_load_requires_slug(tmp_path):
    write(tmp_path, "broken.md", "---\ntitle: T\nurl: https://x\n---\nТіло\n")
    with pytest.raises(ValueError, match=r"broken\.md.*slug"):
        load_articles(tmp_path)


def test_repo_articles_are_valid():
    assert len(load_articles(ARTICLES_DIR)) == len(list(ARTICLES_DIR.glob("*.md")))


async def test_reseed_does_not_duplicate(kb):
    async with kb() as session:
        await seed(session, load_articles(ARTICLES_DIR))
        count = await session.scalar(select(func.count()).select_from(KbArticle))
    assert count == len(list(ARTICLES_DIR.glob("*.md")))


async def test_seed_updates_title(kb):
    articles = load_articles(ARTICLES_DIR)
    changed = [dict(a, title="Новий заголовок") if a["slug"] == "export-pdf" else a for a in articles]
    async with kb() as session:
        await seed(session, changed)
        title = await session.scalar(select(KbArticle.title).where(KbArticle.slug == "export-pdf"))
        count = await session.scalar(select(func.count()).select_from(KbArticle))
    assert title == "Новий заголовок"
    assert count == len(articles)
