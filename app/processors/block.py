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
#  block.py
#
import datetime

import dateutil
from sqlalchemy.orm.exc import NoResultFound

from app.models.data import Log, AccountAudit, Account, AccountIndexAudit, AccountIndex
from app.settings import ACCOUNT_AUDIT_TYPE_NEW, ACCOUNT_AUDIT_TYPE_REAPED, ACCOUNT_INDEX_AUDIT_TYPE_NEW, \
    ACCOUNT_INDEX_AUDIT_TYPE_REAPED
from app.utils.ss58 import ss58_encode
from scalecodec.base import ScaleBytes

from app.processors.base import BlockProcessor
from scalecodec.block import LogDigest


class LogBlockProcessor(BlockProcessor):

    def accumulation_hook(self, db_session):

        self.block.count_log = len(self.block.logs)

        for idx, log_data in enumerate(self.block.logs):
            log_digest = LogDigest(ScaleBytes(log_data))
            log_digest.decode()

            log = Log(
                block_id=self.block.id,
                log_idx=idx,
                type_id=log_digest.index,
                type=log_digest.index_value,
                data=log_digest.value,
            )

            log.save(db_session)


class BlockTotalProcessor(BlockProcessor):

    def sequencing_hook(self, db_session, parent_block_data, parent_sequenced_block_data):

        if not parent_sequenced_block_data:
            parent_sequenced_block_data = {}

        if parent_block_data:
            self.sequenced_block.parent_datetime = parent_block_data['datetime']

            self.sequenced_block.blocktime = (self.block.datetime - dateutil.parser.parse(parent_block_data['datetime'])).total_seconds()
            #self.sequenced_block.blocktime = (self.block.datetime - parent_block_data['datetime']).total_seconds()
        else:
            self.sequenced_block.blocktime = 0

        self.sequenced_block.total_extrinsics = int(parent_sequenced_block_data.get('total_extrinsics', 0)) + self.block.count_extrinsics
        self.sequenced_block.total_extrinsics_success = int(parent_sequenced_block_data.get('total_extrinsics_success', 0)) + self.block.count_extrinsics_success
        self.sequenced_block.total_extrinsics_error = int(parent_sequenced_block_data.get('total_extrinsics_error', 0)) + self.block.count_extrinsics_error
        self.sequenced_block.total_extrinsics_signed = int(parent_sequenced_block_data.get('total_extrinsics_signed', 0)) + self.block.count_extrinsics_signed
        self.sequenced_block.total_extrinsics_unsigned = int(parent_sequenced_block_data.get('total_extrinsics_unsigned', 0)) + self.block.count_extrinsics_unsigned
        self.sequenced_block.total_extrinsics_signedby_address = int(parent_sequenced_block_data.get('total_extrinsics_signedby_address', 0)) + self.block.count_extrinsics_signedby_address
        self.sequenced_block.total_extrinsics_signedby_index = int(parent_sequenced_block_data.get('total_extrinsics_signedby_index', 0)) + self.block.count_extrinsics_signedby_index
        self.sequenced_block.total_events = int(parent_sequenced_block_data.get('total_events', 0)) + self.block.count_events
        self.sequenced_block.total_events_system = int(parent_sequenced_block_data.get('total_events_system', 0)) + self.block.count_events_system
        self.sequenced_block.total_events_module = int(parent_sequenced_block_data.get('total_events_module', 0)) + self.block.count_events_module
        self.sequenced_block.total_events_extrinsic = int(parent_sequenced_block_data.get('total_events_extrinsic', 0)) + self.block.count_events_extrinsic
        self.sequenced_block.total_events_finalization = int(parent_sequenced_block_data.get('total_events_finalization', 0)) + self.block.count_events_finalization
        self.sequenced_block.total_blocktime = int(parent_sequenced_block_data.get('total_blocktime', 0)) + self.sequenced_block.blocktime
        self.sequenced_block.total_accounts_new = int(parent_sequenced_block_data.get('total_accounts_new', 0)) + self.block.count_accounts_new

        self.sequenced_block.total_logs = int(parent_sequenced_block_data.get('total_logs', 0)) + self.block.count_log
        self.sequenced_block.total_accounts = int(parent_sequenced_block_data.get('total_accounts', 0)) + self.block.count_accounts
        self.sequenced_block.total_accounts_reaped = int(parent_sequenced_block_data.get('total_accounts_reaped', 0)) + self.block.count_accounts_reaped
        self.sequenced_block.total_sessions_new = int(parent_sequenced_block_data.get('total_sessions_new', 0)) + self.block.count_sessions_new
        self.sequenced_block.total_contracts_new = int(parent_sequenced_block_data.get('total_contracts_new', 0)) + self.block.count_contracts_new


class AccountBlockProcessor(BlockProcessor):

    def sequencing_hook(self, db_session, parent_block_data, parent_sequenced_block_data):

        for account_audit in AccountAudit.query(db_session).filter_by(block_id=self.block.id).order_by('event_idx'):
            try:
                account = Account.query(db_session).filter_by(id=account_audit.account_id).one()

                if account_audit.type_id == ACCOUNT_AUDIT_TYPE_REAPED:
                    account.count_reaped += 1
                    account.is_reaped = True

                elif account_audit.type_id != ACCOUNT_AUDIT_TYPE_NEW:
                    account.is_reaped = False

                account.updated_at_block = self.block.id

            except NoResultFound:

                # Sanity check on type
                if account_audit.type_id != ACCOUNT_AUDIT_TYPE_NEW:
                    raise ValueError(
                        "Account is in invalid state: does not exists and has type {}".format(account_audit.type_id)
                    )

                account = Account(
                    id=account_audit.account_id,
                    address=ss58_encode(account_audit.account_id),
                    created_at_block=self.block.id,
                    updated_at_block=self.block.id,
                    balance=0
                )

            account.save(db_session)


class AccountIndexBlockProcessor(BlockProcessor):

    def sequencing_hook(self, db_session, parent_block_data, parent_sequenced_block_data):

        for account_index_audit in AccountIndexAudit.query(db_session).filter_by(block_id=self.block.id).order_by('event_idx'):
            try:
                account_index = AccountIndex.query(db_session).filter_by(id=account_index_audit.account_index_id).one()

                if account_index_audit.type_id == ACCOUNT_INDEX_AUDIT_TYPE_REAPED:
                    account_index.account_id = None

                account_index.updated_at_block = self.block.id

            except NoResultFound:

                # Sanity check on type
                if account_index_audit.type_id != ACCOUNT_INDEX_AUDIT_TYPE_NEW:
                    raise ValueError(
                        "Account Index is in invalid state: does not exists and has type {}".format(
                            account_index_audit.type_id
                        )
                    )

                account_index = AccountIndex(
                    id=account_index_audit.account_index_id,
                    account_id=account_index_audit.account_id,
                    created_at_block=self.block.id,
                    updated_at_block=self.block.id
                )

            account_index.save(db_session)
