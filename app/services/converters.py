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

from hashlib import blake2b
from scalecodec.base import ScaleBytes, ScaleDecoder
from scalecodec.metadata import MetadataDecoder
from scalecodec.block import ExtrinsicsDecoder, EventsDecoder, ExtrinsicsBlock61181Decoder

from app.services.base import BaseService
from substrateinterface import SubstrateInterface, SubstrateRequestException

from app.settings import DEBUG, SUBSTRATE_RPC_URL
from app.models.data import Extrinsic, Block, Event, Metadata, Runtime, RuntimeModule, RuntimeCall, RuntimeCallParam, \
    RuntimeEvent, RuntimeEventAttribute, RuntimeType


class HarvesterCouldNotAddBlock(Exception):
    pass


class BlockAlreadyAdded(Exception):
    pass


class PolkascanHarvesterService(BaseService):

    def __init__(self, db_session):
        self.db_session = db_session
        self.metadata_store = {}

    def process_metadata_type(self, type_string, spec_version):

        runtime_type = RuntimeType.query(self.db_session).filter_by(type_string=type_string, spec_version=spec_version).first()

        if not runtime_type:

            # Get current Runtime configuration
            try:
                # TODO move logic to RuntimeConfiguration.get_decoder_class
                decoder_obj = ScaleDecoder.get_decoder_class(type_string, ScaleBytes('0x00'))

                if decoder_obj.sub_type:
                    # Also process sub type
                    self.process_metadata_type(decoder_obj.sub_type, spec_version)

                decoder_class_name = decoder_obj.__class__.__name__

            except NotImplementedError:
                decoder_class_name = '[not implemented]'

            runtime_type = RuntimeType(
                spec_version=spec_version,
                type_string=type_string,
                decoder_class=decoder_class_name,
            )

            runtime_type.save(self.db_session)

    def process_metadata(self, spec_version, block_hash):

        # Check if metadata already in store
        if spec_version not in self.metadata_store:
            print('Metadata: CACHE MISS', spec_version)

            metadata = Metadata.query(self.db_session).get(spec_version)

            if metadata:

                metadata_decoder = MetadataDecoder(ScaleBytes(metadata.json_metadata))
                metadata_decoder.decode()

                self.metadata_store[spec_version] = metadata_decoder

            else:
                # ==== Get block Metadata from Substrate ==================
                substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
                metadata_decoder = substrate.get_block_metadata(block_hash)

                # Store metadata in database
                metadata = Metadata(
                    spec_version=spec_version,
                    json_metadata=str(metadata_decoder.data),
                    json_metadata_decoded=metadata_decoder.value
                )
                metadata.save(self.db_session)

                runtime = Runtime(
                    id=spec_version,
                    impl_name=substrate.get_system_name(),
                    spec_version=spec_version
                )

                runtime.save(self.db_session)

                print('store version to db', metadata_decoder.version)

                if not metadata_decoder.version:
                    # Legacy V0 fallback
                    for module in metadata_decoder.metadata.modules:
                        runtime_module = RuntimeModule(
                            spec_version=spec_version,
                            module_id=module.get_identifier(),
                            prefix=module.prefix,
                            name=module.get_identifier(),
                            count_call_functions=len(module.functions or []),
                            # TODO implement
                            count_storage_functions=0,
                            # TODO update
                            count_events=0
                        )
                        runtime_module.save(self.db_session)

                        if len(module.functions or []) > 0:
                            for idx, call in enumerate(module.functions):
                                runtime_call = RuntimeCall(
                                    spec_version=spec_version,
                                    module_id=module.get_identifier(),
                                    call_id=call.get_identifier(),
                                    index=idx,
                                    name=call.name,
                                    lookup=call.lookup,
                                    documentation='\n'.join(call.docs),
                                    count_params=len(call.args)
                                )
                                runtime_call.save(self.db_session)

                                for arg in call.args:
                                    runtime_call_param = RuntimeCallParam(
                                        runtime_call_id=runtime_call.id,
                                        name=arg.name,
                                        type=arg.type
                                    )
                                    runtime_call_param.save(self.db_session)

                                    # Check if type already registered in database
                                    self.process_metadata_type(arg.type, spec_version)

                    for event_module in metadata_decoder.metadata.events_modules:
                        for event_index, event in enumerate(event_module.events):
                            runtime_event = RuntimeEvent(
                                spec_version=spec_version,
                                module_id=event_module.name,
                                event_id=event.name,
                                index=event_index,
                                name=event.name,
                                lookup=event.lookup,
                                documentation='\n'.join(event.docs),
                                count_attributes=len(event.args)
                            )
                            runtime_event.save(self.db_session)

                            for arg_index, arg in enumerate(event.args):
                                runtime_event_attr = RuntimeEventAttribute(
                                    runtime_event_id=runtime_event.id,
                                    index=arg_index,
                                    type=arg
                                )
                                runtime_event_attr.save(self.db_session)

                else:
                    for module in metadata_decoder.metadata.modules:
                        runtime_module = RuntimeModule(
                            spec_version=spec_version,
                            module_id=module.get_identifier(),
                            prefix=module.prefix,
                            name=module.name,
                            count_call_functions=len(module.calls or []),
                            # TODO implement
                            count_storage_functions=0,
                            count_events=len(module.events or [])
                        )
                        runtime_module.save(self.db_session)

                        if len(module.calls or []) > 0:
                            for idx, call in enumerate(module.calls):
                                runtime_call = RuntimeCall(
                                    spec_version=spec_version,
                                    module_id=module.get_identifier(),
                                    call_id=call.get_identifier(),
                                    index=idx,
                                    name=call.name,
                                    lookup=call.lookup,
                                    documentation='\n'.join(call.docs),
                                    count_params=len(call.args)
                                )
                                runtime_call.save(self.db_session)

                                for arg in call.args:
                                    runtime_call_param = RuntimeCallParam(
                                        runtime_call_id=runtime_call.id,
                                        name=arg.name,
                                        type=arg.type
                                    )
                                    runtime_call_param.save(self.db_session)

                                    # Check if type already registered in database
                                    self.process_metadata_type(arg.type, spec_version)

                        if len(module.events or []) > 0:
                            for event_index, event in enumerate(module.events):
                                runtime_event = RuntimeEvent(
                                    spec_version=spec_version,
                                    module_id=module.get_identifier(),
                                    event_id=event.name,
                                    index=event_index,
                                    name=event.name,
                                    lookup=event.lookup,
                                    documentation='\n'.join(event.docs),
                                    count_attributes=len(event.args)
                                )
                                runtime_event.save(self.db_session)

                                for arg_index, arg in enumerate(event.args):
                                    runtime_event_attr = RuntimeEventAttribute(
                                        runtime_event_id=runtime_event.id,
                                        index=arg_index,
                                        type=arg
                                    )
                                    runtime_event_attr.save(self.db_session)

                # Put in local store
                self.metadata_store[spec_version] = metadata_decoder

    def add_block(self, block_hash):

        # Check if block is already process
        if Block.query(self.db_session).filter_by(hash=block_hash).count() > 0:
            raise BlockAlreadyAdded(block_hash)

        # Extract data from json_block
        substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
        json_block = substrate.get_chain_block(block_hash)

        parent_hash = json_block['block']['header'].pop('parentHash')
        block_id = json_block['block']['header'].pop('number')
        extrinsics_root = json_block['block']['header'].pop('extrinsicsRoot')
        state_root = json_block['block']['header'].pop('stateRoot')

        # Convert block number to numeric

        if not block_id.isnumeric():
            block_id = int(block_id, 16)

        # ==== Get block runtime from Substrate ==================
        json_runtime_version = substrate.get_block_runtime_version(block_hash)

        # Get spec version
        spec_version = json_runtime_version.pop('specVersion', 0)

        self.process_metadata(spec_version, block_hash)

        # ==== Get parent block runtime ===================

        if block_id > 0:
            json_parent_runtime_version = substrate.get_block_runtime_version(parent_hash)

            parent_spec_version = json_parent_runtime_version.pop('specVersion', 0)

            self.process_metadata(parent_spec_version, parent_hash)
        else:
            parent_spec_version = spec_version

        # ==== Get block events from Substrate ==================

        extrinsic_success_idx = {}

        try:
            events_decoder = substrate.get_block_events(block_hash, self.metadata_store[parent_spec_version])

            event_idx = 0

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

        except SubstrateRequestException:
            events_count = 0

        # === Extract extrinsics from block ====

        extrinsics = json_block['block'].pop('extrinsics')

        extrinsic_idx = 0

        for extrinsic in extrinsics:

            # Save to data table
            if block_hash == '0x911a0bf66d5494b6b24f612b3cc14841134c6b73ab9ce02f7e012973070e5661':
                # TODO TEMP fix for exception in Alexander network, remove when network is obsolete
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

            # Generate hash for signed extrinsics
            if extrinsics_decoder.contains_transaction:
                extrinsic_hash = blake2b(bytes.fromhex(extrinsic[2:]), digest_size=32).digest().hex()
            else:
                extrinsic_hash = None

            model = Extrinsic(
                block_id=block_id,
                extrinsic_idx=extrinsic_idx,
                extrinsic_hash=extrinsic_hash,
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
            debug_info = json_block

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

