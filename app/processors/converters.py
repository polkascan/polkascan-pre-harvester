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
import math

from scalecodec.base import ScaleBytes, ScaleDecoder
from scalecodec.metadata import MetadataDecoder
from scalecodec.block import ExtrinsicsDecoder, EventsDecoder, ExtrinsicsBlock61181Decoder

from app.processors.base import BaseService, ProcessorRegistry
from substrateinterface import SubstrateInterface, SubstrateRequestException

from app.settings import DEBUG, SUBSTRATE_RPC_URL
from app.models.data import Extrinsic, Block, Event, Runtime, RuntimeModule, RuntimeCall, RuntimeCallParam, \
    RuntimeEvent, RuntimeEventAttribute, RuntimeType, RuntimeStorage, BlockTotal, RuntimeConstant


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
                # TODO FIX ScaleBytes('0x00') does not process Option<*> properly
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

    def process_metadata(self, runtime_version_data, block_hash):

        spec_version = runtime_version_data.get('specVersion', 0)

        # Check if metadata already in store
        if spec_version not in self.metadata_store:
            print('Metadata: CACHE MISS', spec_version)

            runtime = Runtime.query(self.db_session).get(spec_version)

            if runtime:

                metadata_decoder = MetadataDecoder(ScaleBytes(runtime.json_metadata))
                metadata_decoder.decode()

                self.metadata_store[spec_version] = metadata_decoder

            else:
                self.db_session.begin(subtransactions=True)
                try:

                    # ==== Get block Metadata from Substrate ==================
                    substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
                    metadata_decoder = substrate.get_block_metadata(block_hash)

                    # Store metadata in database
                    runtime = Runtime(
                        id=spec_version,
                        impl_name=runtime_version_data["implName"],
                        impl_version=runtime_version_data["implVersion"],
                        spec_name=runtime_version_data["specName"],
                        spec_version=spec_version,
                        json_metadata=str(metadata_decoder.data),
                        json_metadata_decoded=metadata_decoder.value,
                        apis=runtime_version_data["apis"],
                        authoring_version=runtime_version_data["authoringVersion"],
                        count_call_functions=0,
                        count_events=0,
                        count_modules=len(metadata_decoder.metadata.modules),
                        count_storage_functions=0
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
                                count_storage_functions=len(module.storage or []),
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

                                runtime_module.count_events += 1

                                for arg_index, arg in enumerate(event.args):
                                    runtime_event_attr = RuntimeEventAttribute(
                                        runtime_event_id=runtime_event.id,
                                        index=arg_index,
                                        type=arg
                                    )
                                    runtime_event_attr.save(self.db_session)

                        runtime_module.save(self.db_session)

                    else:
                        for module in metadata_decoder.metadata.modules:

                            # Check if module exists
                            if RuntimeModule.query(self.db_session).filter_by(
                                spec_version=spec_version,
                                module_id=module.get_identifier()
                            ).count() == 0:
                                module_id = module.get_identifier()
                            else:
                                module_id = '{}_1'.format(module.get_identifier())

                            runtime_module = RuntimeModule(
                                spec_version=spec_version,
                                module_id=module_id,
                                prefix=module.prefix,
                                name=module.name,
                                count_call_functions=len(module.calls or []),
                                count_storage_functions=len(module.storage or []),
                                count_events=len(module.events or [])
                            )
                            runtime_module.save(self.db_session)

                            # Update totals in runtime
                            runtime.count_call_functions += runtime_module.count_call_functions
                            runtime.count_events += runtime_module.count_events
                            runtime.count_storage_functions += runtime_module.count_storage_functions

                            if len(module.calls or []) > 0:
                                for idx, call in enumerate(module.calls):
                                    runtime_call = RuntimeCall(
                                        spec_version=spec_version,
                                        module_id=module_id,
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
                                        module_id=module_id,
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

                            if len(module.storage or []) > 0:
                                for idx, storage in enumerate(module.storage):

                                    # Determine type
                                    type_hasher = None
                                    type_key1 = None
                                    type_key2 = None
                                    type_value = None
                                    type_is_linked = None
                                    type_key2hasher = None

                                    if storage.type.get('PlainType'):
                                        type_value = storage.type.get('PlainType')

                                    elif storage.type.get('MapType'):
                                        type_hasher = storage.type['MapType'].get('hasher')
                                        type_key1 = storage.type['MapType'].get('key')
                                        type_value = storage.type['MapType'].get('value')
                                        type_is_linked = storage.type['MapType'].get('isLinked', False)

                                    elif storage.type.get('DoubleMapType'):
                                        type_hasher = storage.type['DoubleMapType'].get('hasher')
                                        type_key1 = storage.type['DoubleMapType'].get('key1')
                                        type_key2 = storage.type['DoubleMapType'].get('key2')
                                        type_value = storage.type['DoubleMapType'].get('value')
                                        type_key2hasher = storage.type['DoubleMapType'].get('key2Hasher')

                                    runtime_storage = RuntimeStorage(
                                        spec_version=spec_version,
                                        module_id=module_id,
                                        index=idx,
                                        name=storage.name,
                                        lookup=None,
                                        default=storage.fallback,
                                        modifier=storage.modifier,
                                        type_hasher=type_hasher,
                                        type_key1=type_key1,
                                        type_key2=type_key2,
                                        type_value=type_value,
                                        type_is_linked=type_is_linked,
                                        type_key2hasher=type_key2hasher,
                                        documentation='\n'.join(storage.docs)
                                    )
                                    runtime_storage.save(self.db_session)

                                    # Check if types already registered in database

                                    self.process_metadata_type(type_value, spec_version)

                                    if type_key1:
                                        self.process_metadata_type(type_key1, spec_version)

                                    if type_key2:
                                        self.process_metadata_type(type_key2, spec_version)

                            if len(module.constants or []) > 0:
                                for idx, constant in enumerate(module.constants):

                                    # Decode value
                                    try:
                                        value_obj = ScaleDecoder.get_decoder_class(
                                            constant.type,
                                            ScaleBytes("0x{}".format(constant.constant_value))
                                        )
                                        value = value_obj.decode()
                                    except ValueError:
                                        value = constant.constant_value

                                    runtime_constant = RuntimeConstant(
                                        spec_version=spec_version,
                                        module_id=module_id,
                                        index=idx,
                                        name=constant.name,
                                        type=constant.type,
                                        value=value,
                                        documentation='\n'.join(constant.docs)
                                    )
                                    runtime_constant.save(self.db_session)

                                    # Check if types already registered in database
                                    self.process_metadata_type(constant.type, spec_version)

                        runtime.save(self.db_session)

                    self.db_session.commit()

                    # Put in local store
                    self.metadata_store[spec_version] = metadata_decoder
                except:
                    self.db_session.rollback()

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
        digest_logs = json_block['block']['header'].get('digest', {}).pop('logs', None)

        # Convert block number to numeric
        if not block_id.isnumeric():
            block_id = int(block_id, 16)

        # ==== Get block runtime from Substrate ==================
        json_runtime_version = substrate.get_block_runtime_version(block_hash)

        # Get spec version
        spec_version = json_runtime_version.get('specVersion', 0)

        self.process_metadata(json_runtime_version, block_hash)

        # ==== Get parent block runtime ===================

        if block_id > 0:
            json_parent_runtime_version = substrate.get_block_runtime_version(parent_hash)

            parent_spec_version = json_parent_runtime_version.get('specVersion', 0)

            self.process_metadata(json_parent_runtime_version, parent_hash)
        else:
            parent_spec_version = spec_version

        # ==== Set initial block properties =====================

        block = Block(
            id=block_id,
            parent_id=block_id - 1,
            hash=block_hash,
            parent_hash=parent_hash,
            state_root=state_root,
            extrinsics_root=extrinsics_root,
            count_extrinsics=0,
            count_events=0,
            count_accounts_new=0,
            count_accounts_reaped=0,
            count_accounts=0,
            count_events_extrinsic=0,
            count_events_finalization=0,
            count_events_module=0,
            count_events_system=0,
            count_extrinsics_error=0,
            count_extrinsics_signed=0,
            count_extrinsics_signedby_address=0,
            count_extrinsics_signedby_index=0,
            count_extrinsics_success=0,
            count_extrinsics_unsigned=0,
            count_sessions_new=0,
            count_contracts_new=0,
            count_log=0,
            range10000=math.floor(block_id / 10000),
            range100000=math.floor(block_id / 100000),
            range1000000=math.floor(block_id / 1000000),
            spec_version_id=spec_version,
            logs=digest_logs
        )

        # Set temp helper variables
        block._accounts_new = []
        block._accounts_reaped = []

        # ==== Get block events from Substrate ==================
        extrinsic_success_idx = {}
        events = []

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

                # Process event

                if event.value['phase'] == 0:
                    block.count_events_extrinsic += 1
                elif event.value['phase'] == 1:
                    block.count_events_finalization += 1

                if event.value['module_id'] == 'system':

                    block.count_events_system += 1

                    # Store result of extrinsic
                    if event.value['event_id'] == 'ExtrinsicSuccess':
                        extrinsic_success_idx[event.value['extrinsic_idx']] = True
                        block.count_extrinsics_success += 1

                    if event.value['event_id'] == 'ExtrinsicFailed':
                        extrinsic_success_idx[event.value['extrinsic_idx']] = False
                        block.count_extrinsics_error += 1
                else:

                    block.count_events_module += 1

                model.save(self.db_session)

                events.append(model)

                event_idx += 1

            block.count_events = len(events_decoder.elements)

        except SubstrateRequestException:
            block.count_events = 0

        # === Extract extrinsics from block ====

        extrinsics_data = json_block['block'].pop('extrinsics')

        block.count_extrinsics = len(extrinsics_data)

        extrinsic_idx = 0

        extrinsics = []

        for extrinsic in extrinsics_data:

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

            model = Extrinsic(
                block_id=block_id,
                extrinsic_idx=extrinsic_idx,
                extrinsic_hash=extrinsics_decoder.extrinsic_hash,
                extrinsic_length=extrinsic_data.get('extrinsic_length'),
                extrinsic_version=extrinsic_data.get('version_info'),
                signed=extrinsics_decoder.contains_transaction,
                unsigned=not extrinsics_decoder.contains_transaction,
                signedby_address=bool(extrinsics_decoder.contains_transaction and extrinsic_data.get('account_id')),
                signedby_index=bool(extrinsics_decoder.contains_transaction and extrinsic_data.get('account_index')),
                address_length=extrinsic_data.get('account_length'),
                address=extrinsic_data.get('account_id'),
                account_index=extrinsic_data.get('account_index'),
                account_idx=extrinsic_data.get('account_idx'),
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

            extrinsics.append(model)

            extrinsic_idx += 1

            # Process extrinsic
            if extrinsics_decoder.contains_transaction:
                block.count_extrinsics_signed += 1

                if model.signedby_address:
                    block.count_extrinsics_signedby_address += 1
                if model.signedby_index:
                    block.count_extrinsics_signedby_index += 1

            else:
                block.count_extrinsics_unsigned += 1

            # Process extrinsic processors
            for processor_class in ProcessorRegistry().get_extrinsic_processors(model.module_id, model.call_id):
                extrinsic_processor = processor_class(block, model)
                extrinsic_processor.accumulation_hook(self.db_session)

        # Process event processors
        for event in events:
            extrinsic = None
            if event.extrinsic_idx is not None:
                extrinsic = extrinsics[event.extrinsic_idx]

            for processor_class in ProcessorRegistry().get_event_processors(event.module_id, event.event_id):
                event_processor = processor_class(block, event, extrinsic)
                event_processor.accumulation_hook(self.db_session)

        # Process block processors
        for processor_class in ProcessorRegistry().get_block_processors():
            block_processor = processor_class(block)
            block_processor.accumulation_hook(self.db_session)

        # Debug info
        if DEBUG:
            block.debug_info = json_block

        # ==== Save data block ==================================

        block.save(self.db_session)

        return block

    def sequence_block(self, block, parent_block_data=None, parent_sequenced_block_data=None):

        sequenced_block = BlockTotal(
            id=block.id
        )

        if block:
            # Process block processors
            for processor_class in ProcessorRegistry().get_block_processors():
                block_processor = processor_class(block, sequenced_block)
                block_processor.sequencing_hook(
                    self.db_session,
                    parent_block_data,
                    parent_sequenced_block_data
                )

            extrinsics = Extrinsic.query(self.db_session).filter_by(block_id=block.id)

            for extrinsic in extrinsics:
                # Process extrinsic processors
                for processor_class in ProcessorRegistry().get_extrinsic_processors(extrinsic.module_id, extrinsic.call_id):
                    extrinsic_processor = processor_class(block, extrinsic)
                    extrinsic_processor.sequencing_hook(
                        self.db_session,
                        parent_block_data,
                        parent_sequenced_block_data
                    )

            events = Event.query(self.db_session).filter_by(block_id=block.id).order_by('event_idx')

            # Process event processors
            for event in events:
                extrinsic = None
                if event.extrinsic_idx is not None:
                    extrinsic = extrinsics[event.extrinsic_idx]

                for processor_class in ProcessorRegistry().get_event_processors(event.module_id, event.event_id):
                    event_processor = processor_class(block, event, extrinsic)
                    event_processor.sequencing_hook(
                        self.db_session,
                        parent_block_data,
                        parent_sequenced_block_data
                    )

        sequenced_block.save(self.db_session)

        return sequenced_block
