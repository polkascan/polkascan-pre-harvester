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
#  extrinsic.py
#

import dateutil.parser
import pytz

from app.models.data import  RuntimeStorage
from app.processors.base import ExtrinsicProcessor
from app.settings import DEMOCRACY_VOTE_AUDIT_TYPE_NORMAL, SUBSTRATE_RPC_URL, SUBSTRATE_METADATA_VERSION
from scalecodec import Conviction
from substrateinterface import SubstrateInterface


class TimestampExtrinsicProcessor(ExtrinsicProcessor):

    module_id = 'timestamp'
    call_id = 'set'

    def accumulation_hook(self, db_session):

        if self.extrinsic.success:
            # Store block date time related fields
            for param in self.extrinsic.params:
                if param.get('name') == 'now':
                    self.block.set_datetime(dateutil.parser.parse(param.get('value')).replace(tzinfo=pytz.UTC))
