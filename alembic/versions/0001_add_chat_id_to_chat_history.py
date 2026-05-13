"""add chat_id to chat_history

Revision ID: 0001
Revises:
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Add chat_id column; existing rows get value 0 (safe fallback)
    op.add_column(
        "chat_history",
        sa.Column("chat_id", sa.BigInteger(), nullable=False, server_default="0"),
    )
    # Drop server_default — future INSERTs must supply chat_id explicitly
    op.alter_column("chat_history", "chat_id", server_default=None)
    # Index for efficient per-chat history queries
    op.create_index(
        "ix_chat_history_chat_id",
        "chat_history",
        ["chat_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_history_chat_id", table_name="chat_history")
    op.drop_column("chat_history", "chat_id")
