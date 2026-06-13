"""add conversation_id to documents

Revision ID: d273a8d8ffad
Revises: 2e800fb14a4a
Create Date: 2026-06-13 11:49:19.306335

Add conversation_id column to documents table for conversation-scoped knowledge base.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d273a8d8ffad"
down_revision: Union[str, Sequence[str], None] = "2e800fb14a4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add conversation_id to documents table."""
    op.add_column(
        "documents",
        sa.Column("conversation_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_documents_conversation_id",
        "documents",
        ["conversation_id"],
    )


def downgrade() -> None:
    """Remove conversation_id from documents table."""
    op.drop_index("ix_documents_conversation_id", table_name="documents")
    op.drop_column("documents", "conversation_id")
