#  Polkascan PRE Explorer GUI
#
#  Copyright 2018-2020 openAware BV (NL).
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
#  harvester.py
#
from app.models.base import BaseModel
import sqlalchemy as sa


class Status(BaseModel):
    __tablename__ = 'harvester_status'
    key = sa.Column(sa.String(64), primary_key=True)
    value = sa.Column(sa.String(255))
    last_modified = sa.Column(sa.DateTime(timezone=True))
    notes = sa.Column(sa.String(255))

    @classmethod
    def get_status(cls, session, key):
        model = session.query(cls).filter_by(key=key).first()

        if not model:
            return Status(
                key=key
            )

        return model


class Setting(BaseModel):
    __tablename__ = 'harvester_setting'
    key = sa.Column(sa.String(64), primary_key=True)
    value = sa.Column(sa.String(255))
    notes = sa.Column(sa.String(255))
