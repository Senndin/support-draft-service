"""Інтерфейс оператора: список звернень, картка, підтвердження і відхилення чернетки.

Рішення оператора — атомарний `UPDATE ... WHERE status='draft_ready'`: із двох
одночасних запитів (подвійний клік, дві вкладки) спрацьовує рівно один.
"""

import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import KbArticle, Ticket

STATUSES = [
    "received", "generating", "draft_ready", "approved", "sending", "sent",
    "rejected", "generation_failed", "send_failed",
]
LIST_LIMIT = 200  # ponytail: без пагінації; додати, коли звернень стане тисячі

basic = HTTPBasic(auto_error=False)


def require_operator(credentials: HTTPBasicCredentials | None = Depends(basic)) -> None:
    """Basic Auth за `OPERATOR_PASSWORD` (логін довільний); порожній пароль вимикає перевірку."""
    expected = settings.operator_password
    if not expected:
        return
    if credentials is None or not secrets.compare_digest(credentials.password.encode(), expected.encode()):
        raise HTTPException(401, "Потрібна автентифікація", headers={"WWW-Authenticate": "Basic"})


router = APIRouter(prefix="/ui", dependencies=[Depends(require_operator)])
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


async def load_articles(session: AsyncSession, tickets: list[Ticket]) -> dict[int, KbArticle]:
    """Статті всіх звернень сторінки одним запитом."""
    ids = {aid for t in tickets for aid in (t.article_ids or [])}
    if not ids:
        return {}
    rows = await session.scalars(select(KbArticle).where(KbArticle.id.in_(ids)))
    return {a.id: a for a in rows}


@router.get("")
async def ticket_list(request: Request, status: str = "", session: AsyncSession = Depends(get_session)):
    """Таблиця звернень (новіші зверху) з фільтром за статусом."""
    query = select(Ticket).order_by(Ticket.id.desc()).limit(LIST_LIMIT)
    if status:
        query = query.where(Ticket.status == status)
    tickets = list((await session.scalars(query)).all())
    return templates.TemplateResponse(
        request,
        "list.html",
        {"tickets": tickets, "articles": await load_articles(session, tickets), "status": status, "statuses": STATUSES},
    )


@router.get("/tickets/{ticket_id}")
async def ticket_card(request: Request, ticket_id: int, session: AsyncSession = Depends(get_session)):
    """Картка звернення; для `draft_ready` — форма з редагованою чернеткою."""
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Звернення не знайдено")
    return templates.TemplateResponse(
        request, "ticket.html", {"ticket": ticket, "articles": await load_articles(session, [ticket])}
    )


async def decide(request: Request, session: AsyncSession, ticket_id: int, **values):
    """Переводить звернення з `draft_ready`; `303` на картку, `409` якщо вже оброблено, `404` якщо немає."""
    changed = await session.scalar(
        update(Ticket)
        .where(Ticket.id == ticket_id, Ticket.status == "draft_ready")
        .values(**values, updated_at=func.now())
        .returning(Ticket.id)
    )
    await session.commit()
    if changed is not None:
        return RedirectResponse(f"/ui/tickets/{ticket_id}", status_code=303)
    status = await session.scalar(select(Ticket.status).where(Ticket.id == ticket_id))
    if status is None:
        raise HTTPException(404, "Звернення не знайдено")
    return templates.TemplateResponse(
        request, "conflict.html", {"ticket_id": ticket_id, "status": status}, status_code=409
    )


@router.post("/tickets/{ticket_id}/approve")
async def approve(
    request: Request, ticket_id: int, final_message: str = Form(...), session: AsyncSession = Depends(get_session)
):
    """Підтверджує (можливо виправлену) чернетку і готує ключ ідемпотентності для надсилання."""
    text = final_message.strip()
    if not text:
        raise HTTPException(422, "Текст відповіді порожній")
    return await decide(
        request, session, ticket_id, status="approved", final_message=text, idempotency_key=uuid.uuid4()
    )


@router.post("/tickets/{ticket_id}/reject")
async def reject(request: Request, ticket_id: int, session: AsyncSession = Depends(get_session)):
    """Відхиляє чернетку; клієнту нічого не надсилається."""
    return await decide(request, session, ticket_id, status="rejected")
