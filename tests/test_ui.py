"""Тести сторінок оператора: список і картка."""

from sqlalchemy import select

from app.models import KbArticle
from tests.test_generation import add_ticket


async def export_article(kb) -> KbArticle:
    async with kb() as s:
        return await s.scalar(select(KbArticle).where(KbArticle.slug == "export-pdf"))


async def draft_ticket(factory, kb, n=1, **fields) -> int:
    """Звернення в `draft_ready` з чернеткою і статтею `export-pdf`."""
    article = await export_article(kb)
    return await add_ticket(
        factory, n=n, ticket_id=f"T-{n}", status="draft_ready", draft="Текст чернетки", article_ids=[article.id], **fields
    )


async def test_list_shows_ticket_with_article(client, session_factory, kb):
    await draft_ticket(session_factory, kb)
    article = await export_article(kb)
    page = (await client.get("/ui")).text
    for text in ("draft_ready", "T-1", "c@example.com", "Не можу експортувати звіт у PDF", "Текст чернетки", article.title, article.url):
        assert text in page
    assert '<meta http-equiv="refresh" content="10">' in page


async def test_list_filter_by_status(client, session_factory, kb):
    await draft_ticket(session_factory, kb, n=1)
    await add_ticket(session_factory, n=2, ticket_id="T-2")
    page = (await client.get("/ui", params={"status": "draft_ready"})).text
    assert "T-1" in page and "T-2" not in page
    assert "T-2" in (await client.get("/ui", params={"status": ""})).text


async def test_card_has_form_for_draft(client, session_factory, kb):
    ticket_id = await draft_ticket(session_factory, kb)
    page = (await client.get(f"/ui/tickets/{ticket_id}")).text
    assert '<textarea name="final_message"' in page
    assert "Текст чернетки</textarea>" in page
    assert "Approve" in page and "Reject" in page
    assert (await export_article(kb)).url in page


async def test_card_without_buttons_after_decision(client, session_factory, kb):
    ticket_id = await add_ticket(session_factory, status="approved", final_message="Відповідь")
    page = (await client.get(f"/ui/tickets/{ticket_id}")).text
    assert "approved" in page
    assert "Approve" not in page and "<textarea" not in page


async def test_card_404(client, session_factory):
    assert (await client.get("/ui/tickets/999")).status_code == 404
