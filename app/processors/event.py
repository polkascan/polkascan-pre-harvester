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
#  event.py
#
from packaging import version

from app.models.data import Contract, Session, AccountAudit, AccountIndexAudit, SessionTotal, SessionValidator, \
    SessionNominator, RuntimeCall, IdentityAudit, IdentityJudgementAudit, RuntimeStorage
from app.processors.base import EventProcessor
from app.settings import ACCOUNT_AUDIT_TYPE_NEW, ACCOUNT_AUDIT_TYPE_REAPED, ACCOUNT_INDEX_AUDIT_TYPE_NEW, \
    ACCOUNT_INDEX_AUDIT_TYPE_REAPED, SUBSTRATE_RPC_URL, LEGACY_SESSION_VALIDATOR_LOOKUP, SEARCH_INDEX_SLASHED_ACCOUNT, \
    SEARCH_INDEX_BALANCETRANSFER, SEARCH_INDEX_HEARTBEATRECEIVED, SUBSTRATE_METADATA_VERSION, \
    IDENTITY_TYPE_SET, IDENTITY_TYPE_CLEARED, IDENTITY_TYPE_KILLED, IDENTITY_JUDGEMENT_TYPE_GIVEN

from app.utils.ss58 import ss58_encode
from scalecodec import ScaleBytes, Proposal
from scalecodec.base import ScaleDecoder
from scalecodec.exceptions import RemainingScaleBytesNotEmptyException
from substrateinterface import SubstrateInterface


class NewSessionEventProcessor(EventProcessor):

    module_id = 'session'
    event_id = 'NewSession'

    def add_session(self, db_session, session_id):
        current_era = None
        validators = []
        nominators = []
        validation_session_lookup = {}

        substrate = SubstrateInterface(SUBSTRATE_RPC_URL)

        # Retrieve current era
        storage_call = RuntimeStorage.query(db_session).filter_by(
            module_id='staking',
            name='CurrentEra',
            spec_version=self.block.spec_version_id
        ).first()

        if storage_call:
            try:
                current_era = substrate.get_storage(
                    block_hash=self.block.hash,
                    module="Staking",
                    function="CurrentEra",
                    return_scale_type=storage_call.get_return_type(),
                    hasher=storage_call.type_hasher,
                    metadata_version=SUBSTRATE_METADATA_VERSION
                )
            except RemainingScaleBytesNotEmptyException:
                pass

        # Retrieve validators for new session from storage

        storage_call = RuntimeStorage.query(db_session).filter_by(
            module_id='session',
            name='Validators',
            spec_version=self.block.spec_version_id
        ).first()

        if storage_call:
            try:
                validators = substrate.get_storage(
                    block_hash=self.block.hash,
                    module="Session",
                    function="Validators",
                    return_scale_type=storage_call.get_return_type(),
                    hasher=storage_call.type_hasher,
                    metadata_version=SUBSTRATE_METADATA_VERSION
                ) or []
            except RemainingScaleBytesNotEmptyException:
                pass

        # Retrieve all sessions in one call
        if not LEGACY_SESSION_VALIDATOR_LOOKUP:

            # Retrieve session account
            # TODO move to network specific data types
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='session',
                name='QueuedKeys',
                spec_version=self.block.spec_version_id
            ).first()

            if storage_call:
                try:
                    validator_session_list = substrate.get_storage(
                        block_hash=self.block.hash,
                        module="Session",
                        function="QueuedKeys",
                        return_scale_type=storage_call.get_return_type(),
                        hasher=storage_call.type_hasher,
                        metadata_version=SUBSTRATE_METADATA_VERSION
                    ) or []
                except RemainingScaleBytesNotEmptyException:

                    try:
                        validator_session_list = substrate.get_storage(
                            block_hash=self.block.hash,
                            module="Session",
                            function="QueuedKeys",
                            return_scale_type='Vec<(ValidatorId, LegacyKeys)>',
                            hasher=storage_call.type_hasher,
                            metadata_version=SUBSTRATE_METADATA_VERSION
                        ) or []
                    except RemainingScaleBytesNotEmptyException:
                        validator_session_list = substrate.get_storage(
                            block_hash=self.block.hash,
                            module="Session",
                            function="QueuedKeys",
                            return_scale_type='Vec<(ValidatorId, EdgewareKeys)>',
                            hasher=storage_call.type_hasher,
                            metadata_version=SUBSTRATE_METADATA_VERSION
                        ) or []

                # build lookup dict
                validation_session_lookup = {}
                for validator_session_item in validator_session_list:
                    session_key = ''

                    if validator_session_item['keys'].get('grandpa'):
                        session_key = validator_session_item['keys'].get('grandpa')

                    if validator_session_item['keys'].get('ed25519'):
                        session_key = validator_session_item['keys'].get('ed25519')

                    validation_session_lookup[
                        validator_session_item['validator'].replace('0x', '')] = session_key.replace('0x', '')

        for rank_nr, validator_account in enumerate(validators):
            validator_stash = None
            validator_controller = None
            validator_ledger = {}
            validator_prefs = {}
            validator_session = ''
            exposure = {}

            if not LEGACY_SESSION_VALIDATOR_LOOKUP:
                validator_stash = validator_account.replace('0x', '')

                # Retrieve stash account
                storage_call = RuntimeStorage.query(db_session).filter_by(
                    module_id='staking',
                    name='Bonded',
                    spec_version=self.block.spec_version_id
                ).first()

                if storage_call:
                    try:
                        validator_controller = substrate.get_storage(
                            block_hash=self.block.hash,
                            module="Staking",
                            function="Bonded",
                            params=validator_stash,
                            return_scale_type=storage_call.get_return_type(),
                            hasher=storage_call.type_hasher,
                            metadata_version=SUBSTRATE_METADATA_VERSION
                        ) or ''

                        validator_controller = validator_controller.replace('0x', '')

                    except RemainingScaleBytesNotEmptyException:
                        pass

                # Retrieve session account
                validator_session = validation_session_lookup.get(validator_stash)

            else:
                validator_controller = validator_account.replace('0x', '')

                # Retrieve stash account
                storage_call = RuntimeStorage.query(db_session).filter_by(
                    module_id='staking',
                    name='Ledger',
                    spec_version=self.block.spec_version_id
                ).first()

                if storage_call:
                    try:
                        validator_ledger = substrate.get_storage(
                            block_hash=self.block.hash,
                            module="Staking",
                            function="Ledger",
                            params=validator_controller,
                            return_scale_type=storage_call.get_return_type(),
                            hasher=storage_call.type_hasher,
                            metadata_version=SUBSTRATE_METADATA_VERSION
                        ) or {}

                        validator_stash = validator_ledger.get('stash', '').replace('0x', '')

                    except RemainingScaleBytesNotEmptyException:
                        pass

                # Retrieve session account
                storage_call = RuntimeStorage.query(db_session).filter_by(
                    module_id='session',
                    name='NextKeyFor',
                    spec_version=self.block.spec_version_id
                ).first()

                if storage_call:
                    try:
                        validator_session = substrate.get_storage(
                            block_hash=self.block.hash,
                            module="Session",
                            function="NextKeyFor",
                            params=validator_controller,
                            return_scale_type=storage_call.get_return_type(),
                            hasher=storage_call.type_hasher,
                            metadata_version=SUBSTRATE_METADATA_VERSION
                        ) or ''
                    except RemainingScaleBytesNotEmptyException:
                        pass

                    validator_session = validator_session.replace('0x', '')

            # Retrieve validator preferences for stash account
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='staking',
                name='Validators',
                spec_version=self.block.spec_version_id
            ).first()

            if storage_call:
                try:
                    validator_prefs = substrate.get_storage(
                        block_hash=self.block.hash,
                        module="Staking",
                        function="Validators",
                        params=validator_stash,
                        return_scale_type=storage_call.get_return_type(),
                        hasher=storage_call.type_hasher,
                        metadata_version=SUBSTRATE_METADATA_VERSION
                    ) or {'col1': {}, 'col2': {}}
                except RemainingScaleBytesNotEmptyException:
                    pass

            # Retrieve nominators
            storage_call = RuntimeStorage.query(db_session).filter_by(
                module_id='staking',
                name='Stakers',
                spec_version=self.block.spec_version_id
            ).first()

            if storage_call:
                try:
                    exposure = substrate.get_storage(
                        block_hash=self.block.hash,
                        module="Staking",
                        function="Stakers",
                        params=validator_stash,
                        return_scale_type=storage_call.get_return_type(),
                        hasher=storage_call.type_hasher,
                        metadata_version=SUBSTRATE_METADATA_VERSION
                    ) or {}
                except RemainingScaleBytesNotEmptyException:
                    pass

            if exposure.get('total'):
                bonded_nominators = exposure.get('total') - exposure.get('own')
            else:
                bonded_nominators = None

            session_validator = SessionValidator(
                session_id=session_id,
                validator_controller=validator_controller,
                validator_stash=validator_stash,
                bonded_total=exposure.get('total'),
                bonded_active=validator_ledger.get('active'),
                bonded_own=exposure.get('own'),
                bonded_nominators=bonded_nominators,
                validator_session=validator_session,
                rank_validator=rank_nr,
                unlocking=validator_ledger.get('unlocking'),
                count_nominators=len(exposure.get('others', [])),
                unstake_threshold=validator_prefs.get('col1', {}).get('unstakeThreshold'),
                commission=validator_prefs.get('col1', {}).get('validatorPayment')
            )

            session_validator.save(db_session)

            # Store nominators
            for rank_nominator, nominator_info in enumerate(exposure.get('others', [])):
                nominator_stash = nominator_info.get('who').replace('0x', '')
                nominators.append(nominator_stash)

                session_nominator = SessionNominator(
                    session_id=session_id,
                    rank_validator=rank_nr,
                    rank_nominator=rank_nominator,
                    nominator_stash=nominator_stash,
                    bonded=nominator_info.get('value'),
                )

                session_nominator.save(db_session)

        # Store session
        session = Session(
            id=session_id,
            start_at_block=self.block.id + 1,
            created_at_block=self.block.id,
            created_at_extrinsic=self.event.extrinsic_idx,
            created_at_event=self.event.event_idx,
            count_validators=len(validators),
            count_nominators=len(set(nominators)),
            era=current_era
        )

        session.save(db_session)

        # Retrieve previous session to calculate count_blocks
        prev_session = Session.query(db_session).filter_by(id=session_id - 1).first()

        if prev_session:
            count_blocks = self.block.id - prev_session.start_at_block + 1
        else:
            count_blocks = self.block.id

        session_total = SessionTotal(
            id=session_id - 1,
            end_at_block=self.block.id,
            count_blocks=count_blocks
        )

        session_total.save(db_session)

    def accumulation_hook(self, db_session):
        self.block.count_sessions_new += 1

    def sequencing_hook(self, db_session, parent_block_data, parent_sequenced_block_data):
        session_id = self.event.attributes[0]['value']
        self.add_session(db_session, session_id)


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

    def accumulation_revert(self, db_session):
        for item in AccountAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)


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

    def accumulation_revert(self, db_session):

        for item in AccountIndexAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)

        for item in AccountAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)


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

    def accumulation_revert(self, db_session):
        for item in AccountIndexAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)

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

    def accumulation_revert(self, db_session):
        for item in Contract.query(db_session).filter_by(created_at_block=self.block.id):
            db_session.delete(item)


class SlashEventProcessor(EventProcessor):

    module_id = 'staking'
    event_id = 'Slash'

    def process_search_index(self, db_session):

        search_index = self.add_search_index(
            index_type_id=SEARCH_INDEX_SLASHED_ACCOUNT,
            account_id=self.event.attributes[0]['value'].replace('0x', ''),
            sorting_value=self.event.attributes[1]['value']
        )

        db_session.add(search_index)


class BalancesTransferProcessor(EventProcessor):
    module_id = 'balances'
    event_id = 'Transfer'

    def process_search_index(self, db_session):
        search_index = self.add_search_index(
            index_type_id=SEARCH_INDEX_BALANCETRANSFER,
            account_id=self.event.attributes[0]['value'].replace('0x', ''),
            sorting_value=self.event.attributes[2]['value']
        )

        db_session.add(search_index)

        search_index = self.add_search_index(
            index_type_id=SEARCH_INDEX_BALANCETRANSFER,
            account_id=self.event.attributes[1]['value'].replace('0x', ''),
            sorting_value=self.event.attributes[2]['value']
        )

        db_session.add(search_index)


class HeartbeatReceivedEventProcessor(EventProcessor):

    module_id = 'imonline'
    event_id = 'HeartbeatReceived'

    def process_search_index(self, db_session):

        search_index = self.add_search_index(
            index_type_id=SEARCH_INDEX_HEARTBEATRECEIVED,
            account_id=self.event.attributes[0]['value'].replace('0x', ''),
            sorting_value=None
        )

        db_session.add(search_index)


class IdentitySetEventProcessor(EventProcessor):

    module_id = 'identity'
    event_id = 'IdentitySet'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 1 and \
                self.event.attributes[0]['type'] == 'AccountId':

            identity_audit = IdentityAudit(
                account_id=self.event.attributes[0]['value'].replace('0x', ''),
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=IDENTITY_TYPE_SET
            )

            identity_audit.data = {
                'display': None,
                'email': None,
                'legal': None,
                'riot': None,
                'web': None,
                'twitter': None
            }

            for param in self.extrinsic.params:
                if param.get('name') == 'info':
                    identity_audit.data['display'] = param.get('value', {}).get('display', {}).get('Raw')
                    identity_audit.data['email'] = param.get('value', {}).get('email', {}).get('Raw')
                    identity_audit.data['legal'] = param.get('value', {}).get('legal', {}).get('Raw')
                    identity_audit.data['web'] = param.get('value', {}).get('web', {}).get('Raw')
                    identity_audit.data['riot'] = param.get('value', {}).get('riot', {}).get('Raw')
                    identity_audit.data['twitter'] = param.get('value', {}).get('twitter', {}).get('Raw')

            identity_audit.save(db_session)

    def accumulation_revert(self, db_session):
        for item in IdentityAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)


class IdentityClearedEventProcessor(EventProcessor):

    module_id = 'identity'
    event_id = 'IdentityCleared'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'AccountId' and \
                self.event.attributes[1]['type'] == 'Balance':

            identity_audit = IdentityAudit(
                account_id=self.event.attributes[0]['value'].replace('0x', ''),
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=IDENTITY_TYPE_CLEARED
            )

            identity_audit.save(db_session)

    def accumulation_revert(self, db_session):
        for item in IdentityAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)


class IdentityKilledEventProcessor(EventProcessor):

    module_id = 'identity'
    event_id = 'IdentityKilled'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'AccountId' and \
                self.event.attributes[1]['type'] == 'Balance':

            identity_audit = IdentityAudit(
                account_id=self.event.attributes[0]['value'].replace('0x', ''),
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=IDENTITY_TYPE_KILLED
            )

            identity_audit.save(db_session)

    def accumulation_revert(self, db_session):
        for item in IdentityAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)


class IdentityJudgementGivenEventProcessor(EventProcessor):

    module_id = 'identity'
    event_id = 'JudgementGiven'

    def accumulation_hook(self, db_session):

        # Check event requirements
        if len(self.event.attributes) == 2 and \
                self.event.attributes[0]['type'] == 'AccountId' and \
                self.event.attributes[1]['type'] == 'RegistrarIndex':

            identity_audit = IdentityJudgementAudit(
                account_id=self.event.attributes[0]['value'].replace('0x', ''),
                registrar_index=self.event.attributes[1]['value'],
                block_id=self.event.block_id,
                extrinsic_idx=self.event.extrinsic_idx,
                event_idx=self.event.event_idx,
                type_id=IDENTITY_JUDGEMENT_TYPE_GIVEN
            )

            for param in self.extrinsic.params:
                if param.get('name') == 'judgement':
                    identity_audit.data = {'judgement': list(param.get('value').keys())[0]}

            identity_audit.save(db_session)

    def accumulation_revert(self, db_session):
        for item in IdentityJudgementAudit.query(db_session).filter_by(block_id=self.block.id):
            db_session.delete(item)
