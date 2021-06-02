"""update data_block_total

Revision ID: 14453ff01bef
Revises: b1fecfa7aec3
Create Date: 2021-05-20 23:25:25.333444

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()


# revision identifiers, used by Alembic.
revision = '14453ff01bef'
down_revision = 'b1fecfa7aec3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('data_block_total', sa.Column('total_bridge_income', sa.Numeric(precision=65, scale=0)))
    op.add_column('data_block_total', sa.Column('total_bridge_outcome', sa.Numeric(precision=65, scale=0)))
    op.add_column('data_block', sa.Column('count_bridge_income', sa.Integer(), nullable=False))
    op.add_column('data_block', sa.Column('count_bridge_outcome', sa.Integer(), nullable=False))
    op.add_column('data_reorg_block', sa.Column('count_bridge_income', sa.Integer(), nullable=False))
    op.add_column('data_reorg_block', sa.Column('count_bridge_outcome', sa.Integer(), nullable=False))
    bind = op.get_bind()
    session = Session(bind=bind)
    sql_outcome = "update data_block_total set total_bridge_outcome =" \
                    "(select count(*)" \
                    "from data_extrinsic" \
                    "where data_extrinsic.module_id = 'EthBridge'" \
                        "and data_extrinsic.call_id = 'transfer_to_sidechain')" \
                  "order by id desc limit 1"
    session.execute(sql_outcome)

    sql_income = "update data_block_total set total_bridge_income =" \
                 "(select count(*)" \
                    "from data_event" \
                    "where data_event.module_id = 'ethbridge'" \
                        "and data_event.event_id = 'IncomingRequestFinalized')" \
                "order by id desc limit 1"
    session.execute(sql_income)


def downgrade():
    op.drop_column('data_block_total', 'total_bridge_income')
    op.drop_column('data_block_total', 'total_bridge_outcome')
    op.drop_column('data_block', 'count_bridge_income')
    op.drop_column('data_block', 'count_bridge_outcome')
    op.drop_column('data_reorg_block', 'count_bridge_income')
    op.drop_column('data_reorg_block', 'count_bridge_outcome')

