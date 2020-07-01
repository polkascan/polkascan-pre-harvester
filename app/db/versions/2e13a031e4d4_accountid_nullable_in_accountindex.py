"""Accountid nullable in accountindex

Revision ID: 2e13a031e4d4
Revises: 3aa6678d275f
Create Date: 2020-07-01 11:27:18.752541

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2e13a031e4d4'
down_revision = '3aa6678d275f'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('data_account_index_audit', 'account_id',
               existing_type=mysql.VARCHAR(length=64),
               nullable=True)


def downgrade():
    op.alter_column('data_account_index_audit', 'account_id',
               existing_type=mysql.VARCHAR(length=64),
               nullable=False)
