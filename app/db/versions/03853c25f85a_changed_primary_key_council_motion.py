"""Changed primary key council motion

Revision ID: 03853c25f85a
Revises: 0e1658a7de2a
Create Date: 2019-12-11 11:54:51.229972

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03853c25f85a'
down_revision = '0e1658a7de2a'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE `data_council_motion`
    MODIFY COLUMN `proposal_id`  int(11) NOT NULL""")

    op.execute("""ALTER TABLE `data_council_motion`
                    DROP PRIMARY KEY,
                    ADD PRIMARY KEY (`proposal_id`);
    """)



def downgrade():
    op.execute("""ALTER TABLE `data_council_motion`
                            DROP PRIMARY KEY,
                            ADD PRIMARY KEY (`motion_hash`);
            """)
    op.execute("""ALTER TABLE `data_council_motion`
        MODIFY COLUMN `proposal_id`  int(11) NULL""")

