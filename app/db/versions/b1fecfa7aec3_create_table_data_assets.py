"""create table data assets

Revision ID: b1fecfa7aec3
Revises: e627476917aa
Create Date: 2021-03-27 09:38:59.414385

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1fecfa7aec3'
down_revision = 'e627476917aa'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('data_asset',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('asset_id', sa.String(length=128), nullable=True),
                    sa.Column('symbol', sa.String(length=10), nullable=True),
                    sa.Column('precision', sa.Integer(), nullable=True),
                    sa.Column('is_mintable', sa.Boolean(), nullable=True),
                    sa.Column('name', sa.String(length=128), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_data_asset_asset_id'), 'data_asset', ['asset_id'], unique=True)


def downgrade():
    op.drop_table('data_asset')
