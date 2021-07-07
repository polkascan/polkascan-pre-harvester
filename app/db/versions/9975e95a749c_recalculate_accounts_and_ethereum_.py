"""recalculate accounts and ethereum transfers

Revision ID: 9975e95a749c
Revises: e46094aeb47d
Create Date: 2021-07-07 17:11:32.715695

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9975e95a749c'
down_revision = 'e46094aeb47d'
branch_labels = None
depends_on = None


def upgrade():
    sql_outcome = "update data_block_total set total_bridge_outcome = " \
                  "(select count(*) " \
                  "from data_extrinsic " \
                  "where data_extrinsic.module_id = 'EthBridge' " \
                  "and data_extrinsic.call_id = 'transfer_to_sidechain') " \
                  "order by id desc limit 1"
    op.execute(sql_outcome)

    sql_income = "update data_block_total set total_bridge_income = " \
                 "(select count(*) " \
                 "from data_event " \
                 "where data_event.module_id = 'ethbridge' " \
                 "and data_event.event_id = 'IncomingRequestFinalized') " \
                 "order by id desc limit 1 "
    op.execute(sql_income)

    sql_accounts = "update data_block_total set total_accounts = (select count(*) from data_account) ORDER BY id DESC LIMIT 1";
    op.execute(sql_accounts)


def downgrade():
    pass
