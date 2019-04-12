#  Polkascan PRE Harvester
#
#  Copyright 2018-2019 openAware BV (NL).
#  This file is part of Polkascan.
#
#  Polkascan is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Polkascan is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Polkascan. If not, see <http://www.gnu.org/licenses/>.
#
#  data.py

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import column_property, relationship, foreign

from app.models.base import BaseModel


class Block(BaseModel):
    __tablename__ = 'data_block'

    serialize_exclude = ['json_block']

    serialize_type = 'block'

    id = sa.Column(sa.Integer(), primary_key=True, autoincrement=False)
    parent_id = sa.Column(sa.Integer(), nullable=False)
    hash = sa.Column(sa.String(66), unique=True, index=True, nullable=False)
    parent_hash = sa.Column(sa.String(66), index=True, nullable=False)
    state_root = sa.Column(sa.String(66), nullable=False)
    extrinsics_root = sa.Column(sa.String(66), nullable=False)
    count_extrinsics = sa.Column(sa.Integer(), nullable=False)
    count_events = sa.Column(sa.Integer(), nullable=False)
    spec_version_id = sa.Column(sa.String(64), nullable=False)
    debug_info = sa.Column(sa.JSON(), default=None, server_default=None)

    @classmethod
    def get_head(cls, session):
        with session.begin():
            query = session.query(cls)
            model = query.order_by(cls.id.desc()).first()

        return model

    @classmethod
    def get_missing_block_ids(cls, session):
        return session.execute(text("""
                                            SELECT
                                              z.expected as block_from, z.got-1 as block_to
                                            FROM (
                                             SELECT
                                              @rownum:=@rownum+1 AS expected,
                                              IF(@rownum=id, 0, @rownum:=id) AS got
                                             FROM
                                              (SELECT @rownum:=0) AS a
                                              JOIN data_block
                                              ORDER BY id
                                             ) AS z
                                            WHERE z.got!=0
                                            ORDER BY block_from DESC
                                            """)
                               )


class Event(BaseModel):
    __tablename__ = 'data_event'

    block_id = sa.Column(sa.Integer(), primary_key=True)
    event_idx = sa.Column(sa.Integer(), primary_key=True)

    extrinsic_idx = sa.Column(sa.Integer(), index=True)

    type = sa.Column(sa.String(4), index=True)

    spec_version_id = sa.Column(sa.Integer())

    module_id = sa.Column(sa.String(64))
    event_id = sa.Column(sa.String(64))

    system = sa.Column(sa.SmallInteger(), index=True, nullable=False)
    module = sa.Column(sa.SmallInteger(), index=True, nullable=False)
    phase = sa.Column(sa.SmallInteger())

    attributes = sa.Column(sa.JSON())

    codec_error = sa.Column(sa.Boolean())


class Extrinsic(BaseModel):
    __tablename__ = 'data_extrinsic'

    block_id = sa.Column(sa.Integer(), primary_key=True)
    extrinsic_idx = sa.Column(sa.Integer(), primary_key=True, index=True)

    extrinsic_length = sa.Column(sa.String(10))
    extrinsic_version = sa.Column(sa.String(2))

    signed = sa.Column(sa.SmallInteger(), index=True, nullable=False)
    unsigned = sa.Column(sa.SmallInteger(), index=True, nullable=False)

    address_length = sa.Column(sa.String(2))
    address = sa.Column(sa.String(64))
    account_index = sa.Column(sa.String(16))
    signature = sa.Column(sa.String(128))
    nonce = sa.Column(sa.Integer())

    era = sa.Column(sa.String(4))

    call = sa.Column(sa.String(4))
    module_id = sa.Column(sa.String(64))
    call_id = sa.Column(sa.String(64), index=True)
    params = sa.Column(sa.JSON())

    success = sa.Column(sa.SmallInteger(), default=0, nullable=False)
    error = sa.Column(sa.SmallInteger(), default=0, nullable=False)

    spec_version_id = sa.Column(sa.Integer())

    codec_error = sa.Column(sa.Boolean(), default=False)

    def serialize_id(self):
        return '{}-{}'.format(self.block_id, self.extrinsic_idx)


class Metadata(BaseModel):
    __tablename__ = 'metadata'

    spec_version = sa.Column(sa.Integer(), primary_key=True, autoincrement=False)
    json_metadata = sa.Column(sa.JSON(), default=None, server_default=None, nullable=True)
    json_metadata_decoded = sa.Column(sa.JSON(), default=None, server_default=None, nullable=True)
