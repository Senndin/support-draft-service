"""create tickets

Revision ID: 3021c65eeb7b
Revises: 325acc2e9ced
Create Date: 2026-11-08 15:21:46.930018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3021c65eeb7b'
down_revision: Union[str, Sequence[str], None] = '325acc2e9ced'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("ticket_id", sa.Text(), nullable=False),
        sa.Column("customer_email", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reply_url", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="received", nullable=False),
        sa.Column("draft", sa.Text(), nullable=True),
        sa.Column("final_message", sa.Text(), nullable=True),
        sa.Column("article_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_tickets_event_id"),
    )
    op.create_index("ix_tickets_status_next_attempt_at", "tickets", ["status", "next_attempt_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tickets_status_next_attempt_at", table_name="tickets")
    op.drop_table("tickets")
