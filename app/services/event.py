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
#  event.py
#
from app.models.data import Account, AccountIndex, DemocracyProposal, Contract, Session
from app.services.base import EventProcessor
from app.utils.ss58 import ss58_encode


class NewSessionEventProcessor(EventProcessor):

    module_id = 'session'
    event_id = 'NewSession'

    def process(self, db_session):

        session = Session(
            id=self.event.attributes[0]['value'],
            start_at_block=self.event.block_id + 1,
            created_at_block=self.event.block_id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
        )

        session.save(db_session)


class NewAccountEventProcessor(EventProcessor):

    module_id = 'balances'
    event_id = 'NewAccount'

    def process(self, db_session):
        self.block.count_accounts_new += 1

        account_id = self.event.attributes[0]['value'].replace('0x', '')
        balance = self.event.attributes[1]['value']

        account = Account(
            id=account_id,
            address=ss58_encode(account_id),
            balance_at_creation=balance,
            created_at_block=self.event.block_id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
        )

        account.save(db_session)


class NewAccountIndexEventProcessor(EventProcessor):

    module_id = 'indices'
    event_id = 'NewAccountIndex'

    def process(self, db_session):

        account_id = self.event.attributes[0]['value'].replace('0x', '')
        id = self.event.attributes[1]['value']

        account_index = AccountIndex(
            id=id,
            account_at_creation=account_id,
            created_at_block=self.event.block_id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
        )

        account_index.save(db_session)


class ProposedEventProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Proposed'

    def process(self, db_session):

        proposal = DemocracyProposal(
            id=self.event.attributes[0]['value'],
            bond=self.event.attributes[1]['value'],
            created_at_block=self.event.block_id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
        )

        for param in self.extrinsic.params:
            if param.get('name') == 'proposal':
                proposal.proposal = param.get('value')

        proposal.save(db_session)


class CodeStoredEventProcessor(EventProcessor):

    module_id = 'contract'
    event_id = 'CodeStored'

    def process(self, db_session):

        contract = Contract(
            code_hash=self.event.attributes[0]['value'].replace('0x', ''),
            created_at_block=self.event.block_id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
        )

        for param in self.extrinsic.params:
            if param.get('name') == 'code':
                contract.bytecode = param.get('value')

        contract.save(db_session)
