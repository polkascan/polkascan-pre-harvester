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
from app.models.data import Account, AccountIndex, DemocracyProposal, Contract, Session, AccountAudit, \
    AccountIndexAudit, DemocracyProposalAudit, SessionTotal, SessionValidator, DemocracyReferendumAudit, RuntimeStorage, \
    SessionNominator
from app.processors.base import EventProcessor
from app.settings import ACCOUNT_AUDIT_TYPE_NEW, ACCOUNT_AUDIT_TYPE_REAPED, ACCOUNT_INDEX_AUDIT_TYPE_NEW, \
    ACCOUNT_INDEX_AUDIT_TYPE_REAPED, DEMOCRACY_PROPOSAL_AUDIT_TYPE_PROPOSED, DEMOCRACY_PROPOSAL_AUDIT_TYPE_TABLED, \
    SUBSTRATE_RPC_URL, DEMOCRACY_REFERENDUM_AUDIT_TYPE_STARTED, DEMOCRACY_REFERENDUM_AUDIT_TYPE_PASSED, \
    DEMOCRACY_REFERENDUM_AUDIT_TYPE_NOTPASSED, DEMOCRACY_REFERENDUM_AUDIT_TYPE_CANCELLED, \
    DEMOCRACY_REFERENDUM_AUDIT_TYPE_EXECUTED
from app.utils.ss58 import ss58_encode
from scalecodec import ScaleBytes
from scalecodec.base import ScaleDecoder
from substrateinterface import SubstrateInterface


class NewSessionEventProcessor(EventProcessor):

    module_id = 'session'
    event_id = 'NewSession'

    def accumulation_hook(self, db_session):
        self.block.count_sessions_new += 1

    def sequencing_hook(self, db_session, parent_block_data, parent_sequenced_block_data):
        session_id = self.event.attributes[0]['value']

        substrate = SubstrateInterface(SUBSTRATE_RPC_URL)

        # Retrieve current era
        storage_call = RuntimeStorage.query(db_session).filter_by(
            module_id='staking',
            name='CurrentEra',
            spec_version=self.block.spec_version_id
        ).one()

        current_era = substrate.get_storage(
            block_hash=self.block.hash,
            module="Staking",
            function="CurrentEra",
            return_scale_type=storage_call.type_value,
            hasher=storage_call.type_hasher
        )

        # Retrieve validators for new session from storage

        storage_call = RuntimeStorage.query(db_session).filter_by(
            module_id='session',
            name='Validators',
            spec_version=self.block.spec_version_id
        ).one()

        validators = substrate.get_storage(
            block_hash=self.block.hash,
            module="Session",
            function="Validators",
            return_scale_type=storage_call.type_value,
            hasher=storage_call.type_hasher
        ) or []

        for rank_nr, validator_controller in enumerate(validators):
            validator_controller = validator_controller.replace('0x', '')

            # Retrieve stash account
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='staking',
                name='Ledger',
                spec_version=self.block.spec_version_id
            ).one()

            validator_ledger = substrate.get_storage(
                block_hash=self.block.hash,
                module="Staking",
                function="Ledger",
                params=validator_controller,
                return_scale_type=storage_call.type_value,
                hasher=storage_call.type_hasher
            )
            print(rank_nr, validator_ledger)

            # Retrieve session account
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='session',
                name='NextKeyFor',
                spec_version=self.block.spec_version_id
            ).one()

            validator_session = substrate.get_storage(
                block_hash=self.block.hash,
                module="Session",
                function="NextKeyFor",
                params=validator_controller,
                return_scale_type=storage_call.type_value,
                hasher=storage_call.type_hasher
            )

            # Retrieve nominators
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='staking',
                name='Stakers',
                spec_version=self.block.spec_version_id
            ).one()

            exposure = substrate.get_storage(
                block_hash=self.block.hash,
                module="Staking",
                function="Stakers",
                params=validator_ledger['stash'].replace('0x', ''),
                return_scale_type=storage_call.type_value,
                hasher=storage_call.type_hasher
            ) or {}

            session_validator = SessionValidator(
                session_id=session_id,
                validator_controller=validator_controller,
                validator_stash=validator_ledger['stash'].replace('0x', ''),
                bonded_total=exposure['total'],
                bonded_active=validator_ledger['active'],
                bonded_own=exposure['own'],
                bonded_nominators=exposure['total'] - exposure['own'],
                validator_session=validator_session.replace('0x', ''),
                rank_validator=rank_nr,
                unlocking=validator_ledger['unlocking']
            )

            session_validator.save(db_session)

            # Store nominators

            for rank_nominator, nominator_info in enumerate(exposure['others']):
                session_nominator = SessionNominator(
                    session_id=session_id,
                    rank_validator=rank_nr,
                    rank_nominator=rank_nominator,
                    nominator_stash=nominator_info['who'].replace('0x', ''),
                    bonded=nominator_info['value'],
                )

                session_nominator.save(db_session)

        # Store session
        session = Session(
            id=session_id,
            start_at_block=self.event.block_id + 1,
            created_at_block=self.event.block_id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
            count_validators=len(validators),
            era=current_era
        )

        session.save(db_session)

        # Retrieve previous session to calculate count_blocks
        prev_session = Session.query(db_session).filter_by(id=session_id - 1).first()

        if prev_session:
            count_blocks = self.event.block_id - prev_session.start_at_block + 1
        else:
            count_blocks = self.event.block_id

        session_total = SessionTotal(
            id=session_id - 1,
            end_at_block=self.event.block_id,
            count_blocks=count_blocks
        )

        session_total.save(db_session)


class NewAccountEventProcessor(EventProcessor):

    module_id = 'balances'
    event_id = 'NewAccount'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'AccountId' and self.event.attributes[1]['type'] == 'Balance':

            account_id = self.event.attributes[0]['value'].replace('0x', '')
            balance = self.event.attributes[1]['value']

            self.block._accounts_new.append(account_id)

            account_audit = AccountAudit(
                account_id=account_id,
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=ACCOUNT_AUDIT_TYPE_NEW
            )

            account_audit.save(db_session)


class ReapedAccount(EventProcessor):
    module_id = 'balances'
    event_id = 'ReapedAccount'

    def accumulation_hook(self, db_session):
        # Check event requirements
        if len(self.event.attributes) == 1 and \
                self.event.attributes[0]['type'] == 'AccountId':

            account_id = self.event.attributes[0]['value'].replace('0x', '')

            self.block._accounts_reaped.append(account_id)

            account_audit = AccountAudit(
                account_id=account_id,
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=ACCOUNT_AUDIT_TYPE_REAPED
            )

            account_audit.save(db_session)

            # Insert account index audit record

            new_account_index_audit = AccountIndexAudit(
                account_index_id=None,
                account_id=account_id,
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=ACCOUNT_INDEX_AUDIT_TYPE_REAPED
            )

            new_account_index_audit.save(db_session)


class NewAccountIndexEventProcessor(EventProcessor):

    module_id = 'indices'
    event_id = 'NewAccountIndex'

    def accumulation_hook(self, db_session):

        account_id = self.event.attributes[0]['value'].replace('0x', '')
        id = self.event.attributes[1]['value']

        account_index_audit = AccountIndexAudit(
            account_index_id=id,
            account_id=account_id,
            block_id=self.event.block_id,
            extrinsic_idx=self.event.extrinsic_idx,
            event_idx=self.event.event_idx,
            type_id=ACCOUNT_INDEX_AUDIT_TYPE_NEW
        )

        account_index_audit.save(db_session)


class ProposedEventProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Proposed'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'PropIndex' and self.event.attributes[1]['type'] == 'Balance':

            proposal_audit = DemocracyProposalAudit(
                democracy_proposal_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_PROPOSAL_AUDIT_TYPE_PROPOSED
            )

            proposal_audit.data = {'bond': self.event.attributes[1]['value'], 'proposal': None}

            for param in self.extrinsic.params:
                if param.get('name') == 'proposal':
                    proposal_audit.data['proposal'] = param.get('value')

            proposal_audit.save(db_session)


class DemocracyTabledEventProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Tabled'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 3 and self.event.attributes[0]['type'] == 'PropIndex' \
                and self.event.attributes[1]['type'] == 'Balance' and \
                self.event.attributes[2]['type'] == 'Vec<AccountId>':

            proposal_audit = DemocracyProposalAudit(
                democracy_proposal_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_PROPOSAL_AUDIT_TYPE_TABLED
            )

            proposal_audit.data = self.event.attributes

            proposal_audit.save(db_session)


class DemocracyStartedProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Started'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'ReferendumIndex' and \
                self.event.attributes[1]['type'] == 'VoteThreshold':

            referendum_audit = DemocracyReferendumAudit(
                democracy_referendum_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_REFERENDUM_AUDIT_TYPE_STARTED,
                data={'vote_threshold': self.event.attributes[1]['value']}
            )

            referendum_audit.save(db_session)


class DemocracyPassedProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Passed'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 1 and \
                self.event.attributes[0]['type'] == 'ReferendumIndex':

            referendum_audit = DemocracyReferendumAudit(
                democracy_referendum_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_REFERENDUM_AUDIT_TYPE_PASSED
            )

            referendum_audit.save(db_session)


class DemocracyNotPassedProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'NotPassed'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 1 and \
                self.event.attributes[0]['type'] == 'ReferendumIndex':

            referendum_audit = DemocracyReferendumAudit(
                democracy_referendum_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_REFERENDUM_AUDIT_TYPE_NOTPASSED
            )

            referendum_audit.save(db_session)


class DemocracyCancelledProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Cancelled'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 1 and \
                self.event.attributes[0]['type'] == 'ReferendumIndex':

            referendum_audit = DemocracyReferendumAudit(
                democracy_referendum_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_REFERENDUM_AUDIT_TYPE_CANCELLED
            )

            referendum_audit.save(db_session)


class DemocracyExecutedProcessor(EventProcessor):

    module_id = 'democracy'
    event_id = 'Executed'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'ReferendumIndex' and \
                self.event.attributes[1]['type'] == 'bool':

            referendum_audit = DemocracyReferendumAudit(
                democracy_referendum_id=self.event.attributes[0]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=DEMOCRACY_REFERENDUM_AUDIT_TYPE_EXECUTED,
                data={'success': self.event.attributes[1]['value']}
            )

            referendum_audit.save(db_session)


class CodeStoredEventProcessor(EventProcessor):

    module_id = 'contract'
    event_id = 'CodeStored'

    def accumulation_hook(self, db_session):

        self.block.count_contracts_new += 1

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
