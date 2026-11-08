"""Ендпоінт живості сервісу. Навмисно не звертається до БД та зовнішніх сервісів."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Повертає `{"status": "ok"}`, якщо процес `api` приймає запити."""
    return {"status": "ok"}
