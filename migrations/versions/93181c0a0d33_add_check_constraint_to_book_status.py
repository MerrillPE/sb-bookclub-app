"""add check constraint to book status

Revision ID: 93181c0a0d33
Revises: c264e13de148
Create Date: 2026-09-19 18:45:40.992585

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '93181c0a0d33'
down_revision = 'c264e13de148'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("book") as batch_op:
        batch_op.create_check_constraint(
            "ck_book_status",
            "status IN ('TO_BE_READ', 'CURRENTLY_READING', 'FINISHED', 'ABANDONED')",
        )


def downgrade():
    with op.batch_alter_table("book") as batch_op:
        batch_op.drop_constraint("ck_book_status", type_="check")
