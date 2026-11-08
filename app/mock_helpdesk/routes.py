"""Мок хелпдеску: приймає відповіді клієнтам, поважає `Idempotency-Key`, імітує збої.

Живе в тому ж застосунку `api`, щоб не піднімати окремий сервіс. Сховище — у пам'яті
процесу: це інструмент перевірки, перезапуск `api` очищує список.
"""

import asyncio
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/mock/helpdesk")

# ponytail: пам'ять одного процесу — при кількох репліках api дедуплікація не спільна
REPLIES: list[dict] = []
BY_KEY: dict[str, dict] = {}


class Reply(BaseModel):
    message: str


def reset() -> None:
    """Очищує сховище (для тестів)."""
    REPLIES.clear()
    BY_KEY.clear()


@router.post("/tickets/{ticket_id}/replies", status_code=201)
async def receive_reply(ticket_id: str, reply: Reply, idempotency_key: str | None = Header(default=None)):
    """Зберігає відповідь (повтор за ключем повертає збережену); збої — за `MOCK_FAIL_RATE`/`MOCK_SLOW_RATE`."""
    if random.random() < settings.mock_fail_rate:
        return JSONResponse({"error": "mock failure"}, status_code=500)

    stored = BY_KEY.get(idempotency_key) if idempotency_key else None
    if stored is None:
        stored = {
            "id": len(REPLIES) + 1,
            "ticket_id": ticket_id,
            "message": reply.message,
            "idempotency_key": idempotency_key,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        REPLIES.append(stored)
        if idempotency_key:
            BY_KEY[idempotency_key] = stored

    if random.random() < settings.mock_slow_rate:
        # відповідь уже прийнята, але клієнт не дочекається — імітація таймауту
        await asyncio.sleep(2 * settings.helpdesk_timeout_s)
    return stored


@router.get("/replies")
async def list_replies() -> list[dict]:
    """Усі отримані відповіді — для перевірки, що клієнт не отримав дублів."""
    return REPLIES
