"""runtime_constant value longtext

Revision ID: e627476917aa
Revises: 4568316e2265
Create Date: 2021-01-27 12:06:16.956601

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e627476917aa'
down_revision = '4568316e2265'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('runtime_constant', 'value',
                    existing_type=mysql.VARCHAR(length=255),
                    type_=mysql.LONGTEXT(),
                    existing_nullable=True)


def downgrade():
    op.alter_column('runtime_constant', 'value',
                    existing_type=mysql.LONGTEXT(),
                    type_=mysql.VARCHAR(length=255),
                    existing_nullable=True)
