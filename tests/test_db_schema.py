"""Фікстура тестової БД піднімає схему міграціями."""

from sqlalchemy import inspect


async def test_schema_has_tickets(db_engine):
    async with db_engine.connect() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert "tickets" in tables
