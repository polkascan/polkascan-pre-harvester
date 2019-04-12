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
#  converters.py

from app.models.data import Block

from app.services.base import BaseService
from substrateinterface import SubstrateInterface

from app.settings import DEBUG, SUBSTRATE_RPC_URL


class HarvesterCouldNotAddBlock(Exception):
    pass


class BlockAlreadyAdded(Exception):
    pass


class PolkascanHarvesterService(BaseService):

    def __init__(self, db_session):
        self.db_session = db_session
        self.metadata_store = {}

    def add_block(self, block_hash):

        # Check if block is already process
        if Block.query(self.db_session).filter_by(hash=block_hash).count() > 0:
            raise BlockAlreadyAdded(block_hash)

        # Extract data from json_block
        substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
        json_block = substrate.get_chain_block(block_hash)

        parent_hash = json_block['result']['block']['header'].pop('parentHash')
        block_id = json_block['result']['block']['header'].pop('number')
        extrinsics_root = json_block['result']['block']['header'].pop('extrinsicsRoot')
        state_root = json_block['result']['block']['header'].pop('stateRoot')

        # Convert block number to numeric

        if not block_id.isnumeric():
            block_id = int(block_id, 16)

        # ==== Get block runtime from Substrate ==================
        json_runtime_version = substrate.get_block_runtime_version(block_hash)

        # Get spec version
        spec_version = json_runtime_version['result'].pop('specVersion', 0)

        extrinsics = json_block['result']['block'].pop('extrinsics')

        # Debug info
        debug_info = None
        if DEBUG:
            debug_info = json_block['result']

        # ==== Save data block ==================================

        block = Block(
            id=block_id,
            parent_id=block_id - 1,
            hash=block_hash,
            parent_hash=parent_hash,
            state_root=state_root,
            extrinsics_root=extrinsics_root,
            count_extrinsics=len(extrinsics),
            count_events=0,
            spec_version_id=spec_version,
            debug_info=debug_info
        )

        block.save(self.db_session)

        return block

