"""Runtimestorage default type

Revision ID: 4568316e2265
Revises: 47f2f1505ac5
Create Date: 2021-01-13 14:54:13.124161

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4568316e2265'
down_revision = '2e13a031e4d4'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('runtime_storage', 'default',
                    existing_type=mysql.VARCHAR(length=255),
                    type_=mysql.LONGTEXT(),
                    existing_nullable=True)


def downgrade():
    op.alter_column('runtime_storage', 'default',
                    existing_type=mysql.LONGTEXT(),
                    type_=mysql.VARCHAR(length=255),
                    existing_nullable=True)
