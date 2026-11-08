"""create kb articles

Revision ID: bdf2365c46d7
Revises: 3021c65eeb7b
Create Date: 2026-11-08 15:29:33.327875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bdf2365c46d7'
down_revision: Union[str, Sequence[str], None] = '3021c65eeb7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "kb_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', title || ' ' || body)", persisted=True),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_kb_articles_slug"),
    )
    op.create_index("ix_kb_articles_search_vector", "kb_articles", ["search_vector"], postgresql_using="gin")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_kb_articles_search_vector", table_name="kb_articles")
    op.drop_table("kb_articles")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
