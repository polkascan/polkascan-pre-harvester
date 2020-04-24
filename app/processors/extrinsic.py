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

from app import settings
from app.models.data import IdentityAudit, Account
from app.processors.base import ExtrinsicProcessor


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

    def process_search_index(self, db_session):

        if self.extrinsic.success:

            sorting_value = None

            # Try to retrieve balance of vote
            if self.extrinsic.params[1]['type'] == 'AccountVote<BalanceOf>':
                if 'Standard' in self.extrinsic.params[1]['value']:
                    sorting_value = self.extrinsic.params[1]['value']['Standard']['balance']

            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_DEMOCRACY_VOTE,
                account_id=self.extrinsic.address,
                sorting_value=sorting_value
            )

            search_index.save(db_session)


class DemocracyProxyVote(ExtrinsicProcessor):

    module_id = 'democracy'
    call_id = 'proxy_vote'

    def process_search_index(self, db_session):

        if self.extrinsic.success:

            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_DEMOCRACY_PROXY_VOTE,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class DemocracySecond(ExtrinsicProcessor):

    module_id = 'democracy'
    call_id = 'second'

    def process_search_index(self, db_session):

        if self.extrinsic.success:

            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_DEMOCRACY_SECOND,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class IndentitySetSubsExtrinsicProcessor(ExtrinsicProcessor):

    module_id = 'identity'
    call_id = 'set_subs'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_IDENTITY_SET_SUBS,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class StakingBond(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'bond'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_BONDED,
                account_id=self.extrinsic.address,
                sorting_value=self.extrinsic.params[1]['value']
            )

            search_index.save(db_session)


class StakingBondExtra(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'bond_extra'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_BONDED,
                account_id=self.extrinsic.address,
                sorting_value=self.extrinsic.params[0]['value']
            )

            search_index.save(db_session)


class StakingUnbond(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'unbond'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_UNBONDED,
                account_id=self.extrinsic.address,
                sorting_value=self.extrinsic.params[0]['value']
            )

            search_index.save(db_session)


class StakingWithdrawUnbonded(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'withdraw_unbonded'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_WITHDRAWN,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class StakingNominate(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'nominate'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_NOMINATE,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class StakingValidate(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'validate'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_VALIDATE,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class StakingChill(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'chill'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_CHILL,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class StakingSetPayee(ExtrinsicProcessor):

    module_id = 'staking'
    call_id = 'set_payee'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_STAKING_SET_PAYEE,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class ElectionsSubmitCandidacy(ExtrinsicProcessor):

    module_id = 'electionsphragmen'
    call_id = 'submit_candidacy'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_COUNCIL_CANDIDACY_SUBMIT,
                account_id=self.extrinsic.address
            )

            search_index.save(db_session)


class ElectionsVote(ExtrinsicProcessor):

    module_id = 'electionsphragmen'
    call_id = 'vote'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_COUNCIL_CANDIDACY_VOTE,
                account_id=self.extrinsic.address,
                sorting_value=self.extrinsic.params[1]['value']
            )

            search_index.save(db_session)

            # Reverse lookup
            for candidate in self.extrinsic.params[0]['value']:
                search_index = self.add_search_index(
                    index_type_id=settings.SEARCH_INDEX_COUNCIL_CANDIDACY_VOTE,
                    account_id=candidate.replace('0x', ''),
                    sorting_value=self.extrinsic.params[1]['value']
                )

                search_index.save(db_session)


class TreasuryProposeSpend(ExtrinsicProcessor):

    module_id = 'treasury'
    call_id = 'propose_spend'

    def process_search_index(self, db_session):

        if self.extrinsic.success:
            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_TREASURY_PROPOSED,
                account_id=self.extrinsic.address,
                sorting_value=self.extrinsic.params[0]['value']
            )

            search_index.save(db_session)

            # Add Beneficiary

            search_index = self.add_search_index(
                index_type_id=settings.SEARCH_INDEX_TREASURY_PROPOSED,
                account_id=self.extrinsic.params[1]['value'].replace('0x', ''),
                sorting_value=self.extrinsic.params[0]['value']
            )

            search_index.save(db_session)


class SudoSetKey(ExtrinsicProcessor):

    module_id = 'sudo'
    call_id = 'set_key'

    def sequencing_hook(self, db_session, parent_block, parent_sequenced_block):
        if self.extrinsic.success:

            sudo_key = self.extrinsic.params[0]['value'].replace('0x', '')

            Account.query(db_session).filter(
                Account.id == sudo_key, Account.was_sudo == False
            ).update({Account.was_sudo: True}, synchronize_session='fetch')

            Account.query(db_session).filter(
                Account.id != sudo_key, Account.is_sudo == True
            ).update({Account.is_sudo: False}, synchronize_session='fetch')

            Account.query(db_session).filter(
                Account.id == sudo_key, Account.is_sudo == False
            ).update({Account.is_sudo: True}, synchronize_session='fetch')
