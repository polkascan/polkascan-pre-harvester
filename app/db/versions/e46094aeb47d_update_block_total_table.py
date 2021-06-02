"""update block total table

Revision ID: e46094aeb47d
Revises: 14453ff01bef
Create Date: 2021-06-02 22:58:08.683654

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e46094aeb47d'
down_revision = '14453ff01bef'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(table_name='data_block_total', column_name='total_bridge_income', existing_type=sa.Numeric(precision=65, scale=0), nullable=False, server_default='0')
    op.alter_column(table_name='data_block_total', column_name='total_bridge_outcome', existing_type=sa.Numeric(precision=65, scale=0), nullable=False, server_default='0')

def downgrade():
    pass
