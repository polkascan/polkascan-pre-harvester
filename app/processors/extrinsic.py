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
#  extrinsic.py
#

import dateutil.parser
import pytz
from app.processors.base import ExtrinsicProcessor


class TimestampExtrinsicProcessor(ExtrinsicProcessor):

    module_id = 'timestamp'
    call_id = 'set'

    def accumulation_hook(self, db_session):
        # Store block date time related fields
        for param in self.extrinsic.params:
            if param.get('name') == 'now':
                self.block.datetime = dateutil.parser.parse(param.get('value')).replace(tzinfo=pytz.UTC)
                self.block.year = self.block.datetime.year
                self.block.month = self.block.datetime.month
                self.block.week = self.block.datetime.strftime("%W")
                self.block.day = self.block.datetime.day
                self.block.hour = self.block.datetime.hour
                self.block.full_month = self.block.datetime.strftime("%Y%m")
                self.block.full_week = self.block.datetime.strftime("%Y%W")
                self.block.full_day = self.block.datetime.strftime("%Y%m%d")
                self.block.full_hour = self.block.datetime.strftime("%Y%m%d%H")


