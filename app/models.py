"""ORM-моделі. `Ticket` — і звернення, і черга задач; `KbArticle` — стаття бази знань."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Computed, DateTime, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовий клас моделей; його `metadata` використовує Alembic."""

    # усі часові колонки — timestamptz
    type_annotation_map = {datetime: DateTime(timezone=True)}


class Ticket(Base):
    """Звернення з хелпдеску.

    Статуси: received → generating → draft_ready → approved → sending → sent;
    бічні: rejected, generation_failed, send_failed. Переходи контролює код, а не БД.
    """

    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_tickets_event_id"),
        # для захоплення задач воркером: WHERE status=... AND next_attempt_at <= now()
        Index("ix_tickets_status_next_attempt_at", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text)
    ticket_id: Mapped[str] = mapped_column(Text)
    customer_email: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    reply_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="received")

    # чернетка й відповідь (етапи 4–5)
    draft: Mapped[str | None] = mapped_column(Text)
    final_message: Mapped[str | None] = mapped_column(Text)
    article_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    # черга: ретраї та lease (етапи 4, 6)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(server_default=func.now())
    locked_until: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[uuid.UUID | None]

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class KbArticle(Base):
    """Стаття бази знань; `search_vector` рахує PostgreSQL (generated column)."""

    __tablename__ = "kb_articles"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_kb_articles_slug"),
        Index("ix_kb_articles_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', title || ' ' || body)", persisted=True)
    )
