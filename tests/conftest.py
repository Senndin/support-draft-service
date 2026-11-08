"""Спільні фікстури: тестова БД PostgreSQL і HTTP-клієнт до застосунку.

DB-тести потребують запущеного PostgreSQL (`docker compose up -d db`);
без нього вони пропускаються, решта тестів працює як завжди.
"""

import os
import subprocess
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/support_test"
)


async def _create_database_if_missing(url: str) -> None:
    """Створює тестову БД через службову БД `postgres`."""
    db_name = make_url(url).database
    admin = create_async_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name})
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
async def db_engine():
    """Engine тестової БД зі схемою, піднятою `alembic upgrade head`."""
    try:
        await _create_database_if_missing(TEST_DATABASE_URL)
    except OSError:
        pytest.skip("PostgreSQL недоступний: docker compose up -d db")
    # alembic запускаємо окремим процесом: env.py сам викликає asyncio.run()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
        capture_output=True,
    )
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    """Фабрика сесій до порожньої таблиці `tickets`."""
    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE tickets RESTART IDENTITY"))
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def client(session_factory):
    """HTTP-клієнт до застосунку, що працює з тестовою БД."""

    async def _session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def kb(db_engine):
    """Фабрика сесій до бази знань, засіяної статтями з `kb/articles`."""
    from scripts.seed_kb import ARTICLES_DIR, load_articles, seed

    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE kb_articles RESTART IDENTITY"))
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        await seed(session, load_articles(ARTICLES_DIR))
    return factory
