#  Polkascan PRE Harvester
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
#  base.py

from dictalchemy import DictableModel
from sqlalchemy.ext.declarative import declarative_base


class BaseModelObj(DictableModel):

    serialize_exclude = None

    def save(self, session):
        session.add(self)
        session.flush()

    @property
    def serialize_type(self):
        return self.__class__.__name__.lower()

    def serialize_id(self):
        return self.id

    def serialize(self, exclude=None):
        return {
            'type': self.serialize_type,
            'id': self.serialize_id(),
            'attributes': self.asdict(exclude=exclude or self.serialize_exclude)
        }

    @classmethod
    def query(cls, session):
        return session.query(cls)


BaseModel = declarative_base(cls=BaseModelObj)  ## type: BaseModelObj

