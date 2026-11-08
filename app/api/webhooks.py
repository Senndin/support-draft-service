"""Прийом звернень від хелпдеску.

Вебхук лише зберігає подію і одразу відповідає 202 — жодних зовнішніх викликів,
щоб вкластися в 2 с до повтору хелпдеску. Дублі (зокрема одночасні) відсікає
унікальний індекс на `event_id` через `INSERT ... ON CONFLICT DO NOTHING`.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import AnyHttpUrl, BaseModel, StringConstraints
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Ticket

log = logging.getLogger(__name__)
router = APIRouter()

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class WebhookEvent(BaseModel):
    """Тіло вебхука; зайві поля хелпдеску ігноруються."""

    event_id: NonBlank
    ticket_id: NonBlank
    customer_email: NonBlank
    message: NonBlank
    reply_url: AnyHttpUrl


@router.post("/webhooks/helpdesk", status_code=202)
async def receive_event(event: WebhookEvent, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Зберігає нову подію зі статусом `received`; на дубль відповідає так само, нічого не змінюючи."""
    stmt = (
        insert(Ticket)
        .values(**event.model_dump(exclude={"reply_url"}), reply_url=str(event.reply_url))
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = await session.execute(stmt)
    await session.commit()
    if result.rowcount == 0:
        log.info("duplicate event %s ignored", event.event_id)
    return {"status": "accepted"}
