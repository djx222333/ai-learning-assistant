"""add foreign key for conversation_id in documents

Revision ID: cb11c54d0b2c
Revises: d273a8d8ffad
Create Date: 2026-06-13 11:57:02.486961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cb11c54d0b2c'
down_revision: Union[str, Sequence[str], None] = 'd273a8d8ffad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.create_foreign_key(
            "fk_documents_conversation_id",
            "conversations",
            ["conversation_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_conversation_id", type_="foreignkey")
