"""drop unique constraint on member display_name

Revision ID: b5df0559156b
Revises: 33b3d0c2902d
Create Date: 2026-09-27 13:42:03.310144

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5df0559156b'
down_revision = '33b3d0c2902d'
branch_labels = None
depends_on = None


# The initial migration created this constraint unnamed. Postgres auto-names it
# "member_display_name_key"; SQLite keeps no name at all, so batch mode (which rebuilds
# the table on SQLite) applies this naming convention to the reflected constraint to give
# it the same name there too.
NAMING_CONVENTION = {"uq": "%(table_name)s_%(column_0_name)s_key"}


def upgrade():
    with op.batch_alter_table("member", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint("member_display_name_key", type_="unique")


def downgrade():
    with op.batch_alter_table("member", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_unique_constraint("member_display_name_key", ["display_name"])
