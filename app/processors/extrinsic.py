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

from app.models.data import DemocracyVoteAudit, RuntimeStorage
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


class DemocracyVoteExtrinsicProcessor(ExtrinsicProcessor):

    module_id = 'democracy'
    call_id = 'vote'

    def accumulation_hook(self, db_session):

        if self.extrinsic.success:

            vote_account_id = self.extrinsic.address
            stash_account_id = self.extrinsic.address

            # TODO refactor when new runtime aware substrateinterface
            # TODO make substrateinterface part of processor over websockets

            # Get balance of stash_account
            substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='balances',
                name='FreeBalance',
            ).order_by(RuntimeStorage.spec_version.desc()).first()

            stash = substrate.get_storage(
                block_hash=self.block.hash,
                module='Balances',
                function='FreeBalance',
                params=stash_account_id,
                return_scale_type=storage_call.type_value,
                hasher=storage_call.type_hasher,
                metadata_version=SUBSTRATE_METADATA_VERSION
            )

            vote_audit = DemocracyVoteAudit(
                block_id=self.extrinsic.block_id,
                extrinsic_idx=self.extrinsic.extrinsic_idx,
                type_id=DEMOCRACY_VOTE_AUDIT_TYPE_NORMAL,
                data={
                    'vote_account_id': vote_account_id,
                    'stash_account_id': stash_account_id,
                    'stash': stash
                }
            )

            # Process parameters
            for param in self.extrinsic.params:
                if param.get('name') == 'ref_index':
                    vote_audit.democracy_referendum_id = param.get('value')
                if param.get('name') == 'vote':
                    vote_audit.data['vote_raw'] = param.get('value')
                    vote_audit.data['vote_yes'] = bool(vote_audit.data['vote_raw'])
                    vote_audit.data['vote_no'] = not bool(vote_audit.data['vote_raw'])
                    # Determine conviction and weight of vote
                    vote_audit.data['conviction'] = vote_audit.data['vote_raw'] & Conviction.CONVICTION_MASK
                    vote_audit.data['vote_yes_weighted'] = int(vote_audit.data['vote_yes']) * vote_audit.data['stash']
                    vote_audit.data['vote_no_weighted'] = int(vote_audit.data['vote_no']) * vote_audit.data['stash']

            vote_audit.save(db_session)

    def accumulation_revert(self, db_session):
        for item in DemocracyVoteAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)

