"""Перевірка, що engine і сесії налаштовані з `settings.database_url` без підключення до БД."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal, engine
from app.models import Base


def test_engine_uses_settings_url():
    assert engine.url.render_as_string(hide_password=False) == settings.database_url


def test_session_factory_builds_async_session():
    assert isinstance(SessionLocal(), AsyncSession)


def test_base_has_metadata():
    assert Base.metadata is not None
