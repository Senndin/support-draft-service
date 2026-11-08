"""ORM-моделі. Таблиці `tickets` і `kb_articles` додаються на етапах 2–3."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовий клас моделей; його `metadata` використовує Alembic."""
