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

from scalecodec.base import ScaleBytes
from scalecodec.metadata import MetadataDecoder
from scalecodec.block import ExtrinsicsDecoder, EventsDecoder, ExtrinsicsBlock61181Decoder

from app.services.base import BaseService
from substrateinterface import SubstrateInterface

from app.settings import DEBUG, SUBSTRATE_RPC_URL
from app.models.data import Extrinsic, Block, Event, Metadata


class HarvesterCouldNotAddBlock(Exception):
    pass


class BlockAlreadyAdded(Exception):
    pass


class PolkascanHarvesterService(BaseService):

    def __init__(self, db_session):
        self.db_session = db_session
        self.metadata_store = {}

    def process_metadata(self, spec_version, block_hash):

        # Check if metadata already in store
        if spec_version not in self.metadata_store:
            print('CACHE MISS')

            metadata = Metadata.query(self.db_session).get(spec_version)

            if metadata:

                metadata_decoder = MetadataDecoder(ScaleBytes(metadata.json_metadata.get('result')))
                metadata_decoder.decode()

                self.metadata_store[spec_version] = metadata_decoder

            else:
                # ==== Get block Metadata from Substrate ==================
                substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
                json_metadata = substrate.get_block_metadata(block_hash)

                metadata_decoder = MetadataDecoder(ScaleBytes(json_metadata.get('result')))

                metadata = Metadata(
                    spec_version=spec_version,
                    json_metadata=json_metadata,
                    json_metadata_decoded=metadata_decoder.decode()
                )
                metadata.save(self.db_session)

                self.metadata_store[spec_version] = metadata_decoder

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

        self.process_metadata(spec_version, block_hash)

        # ==== Get parent block runtime ===================

        if block_id > 0:
            json_parent_runtime_version = substrate.get_block_runtime_version(parent_hash)

            parent_spec_version = json_parent_runtime_version['result'].pop('specVersion', 0)

            self.process_metadata(parent_spec_version, parent_hash)
        else:
            parent_spec_version = spec_version

        # ==== Get block events from Substrate ==================

        json_events = substrate.get_block_events(block_hash)

        if json_events.get('result'):

            # Process events
            events_decoder = EventsDecoder(
                data=ScaleBytes(json_events.get('result')),
                metadata=self.metadata_store[parent_spec_version]
            )
            events_decoder.decode()

            event_idx = 0

            extrinsic_success_idx = {}

            for event in events_decoder.elements:
                model = Event(
                    block_id=block_id,
                    event_idx=event_idx,
                    phase=event.value['phase'],
                    extrinsic_idx=event.value['extrinsic_idx'],
                    type=event.value['type'],
                    spec_version_id=parent_spec_version,
                    module_id=event.value['module_id'],
                    event_id=event.value['event_id'],
                    system=int(event.value['module_id'] == 'system'),
                    module=int(event.value['module_id'] != 'system'),
                    attributes=event.value['params'],
                    codec_error=False
                )

                # Store result of extrinsic
                if event.value['module_id'] == 'system' and event.value['event_id'] == 'ExtrinsicSuccess':
                    extrinsic_success_idx[event.value['extrinsic_idx']] = True

                if event.value['module_id'] == 'system' and event.value['event_id'] == 'ExtrinsicFailed':
                    extrinsic_success_idx[event.value['extrinsic_idx']] = False

                model.save(self.db_session)

                event_idx += 1

            events_count = len(events_decoder.elements)

        else:
            events_count = 0

        # === Extract extrinsics from block ====

        extrinsics = json_block['result']['block'].pop('extrinsics')

        extrinsic_idx = 0

        for extrinsic in extrinsics:

            # Save to data table

            if block_id == 61181:
                # TODO TEMP fix
                extrinsics_decoder = ExtrinsicsBlock61181Decoder(
                    data=ScaleBytes(extrinsic),
                    metadata=self.metadata_store[parent_spec_version]
                )
            else:
                extrinsics_decoder = ExtrinsicsDecoder(
                    data=ScaleBytes(extrinsic),
                    metadata=self.metadata_store[parent_spec_version]
                )

            extrinsic_data = extrinsics_decoder.decode()

            # Lookup result of extrinsic
            extrinsic_success = extrinsic_success_idx.get(extrinsic_idx, False)

            model = Extrinsic(
                block_id=block_id,
                extrinsic_idx=extrinsic_idx,
                extrinsic_length=extrinsic_data.get('extrinsic_length'),
                extrinsic_version=extrinsic_data.get('version_info'),
                signed=extrinsics_decoder.contains_transaction,
                unsigned=not extrinsics_decoder.contains_transaction,
                address_length=extrinsic_data.get('account_length'),
                address=extrinsic_data.get('account_id'),
                account_index=extrinsic_data.get('account_index'),
                signature=extrinsic_data.get('signature'),
                nonce=extrinsic_data.get('nonce'),
                era=extrinsic_data.get('era'),
                call=extrinsic_data.get('call_code'),
                module_id=extrinsic_data.get('call_module'),
                call_id=extrinsic_data.get('call_module_function'),
                params=extrinsic_data.get('params'),
                spec_version_id=parent_spec_version,
                success=int(extrinsic_success),
                error=int(not extrinsic_success),
                codec_error=False
            )
            model.save(self.db_session)

            extrinsic_idx += 1

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
            count_events=events_count,
            spec_version_id=spec_version,
            debug_info=debug_info
        )

        block.save(self.db_session)

        return block

