"""Перевірка структури моделі `Ticket` без підключення до БД."""

from sqlalchemy import UniqueConstraint

from app.models import Ticket


def test_event_id_is_unique():
    table = Ticket.__table__
    unique_cols = {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, UniqueConstraint)}
    assert ("event_id",) in unique_cols


def test_server_defaults():
    cols = Ticket.__table__.c
    assert cols.status.server_default.arg == "received"
    assert cols.attempts.server_default.arg == "0"


def test_queue_index():
    index_cols = {tuple(i.columns.keys()) for i in Ticket.__table__.indexes}
    assert ("status", "next_attempt_at") in index_cols


def test_timestamps_are_timezone_aware():
    cols = Ticket.__table__.c
    assert all(cols[name].type.timezone for name in ("next_attempt_at", "locked_until", "created_at", "updated_at"))
