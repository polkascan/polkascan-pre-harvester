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
#  harvester.py

import datetime
import uuid

import falcon
import pytz
from celery.result import AsyncResult
from falcon.media.validators.jsonschema import validate
from scalecodec.base import RuntimeConfiguration
from sqlalchemy import text, func

from app import settings
from app.models.data import Block, BlockTotal
from app.models.harvester import Setting, Status
from app.resources.base import BaseResource
from app.schemas import load_schema
from app.processors.converters import PolkascanHarvesterService, BlockAlreadyAdded, BlockIntegrityError
from substrateinterface import SubstrateInterface
from app.tasks import accumulate_block_recursive, start_harvester, rebuild_search_index, rebuild_account_info_snapshot
from app.settings import SUBSTRATE_RPC_URL, TYPE_REGISTRY, TYPE_REGISTRY_FILE


class PolkascanStartHarvesterResource(BaseResource):

    #@validate(load_schema('start_harvester'))
    def on_post(self, req, resp):

        task = start_harvester.delay(check_gaps=True)

        resp.status = falcon.HTTP_201

        resp.media = {
            'status': 'success',
            'data': {
                'task_id': task.id
            }
        }


class PolkascanStopHarvesterResource(BaseResource):

    def on_post(self, req, resp):

        resp.status = falcon.HTTP_404

        resp.media = {
            'status': 'success',
            'data': {
                'message': 'TODO'
            }
        }


class PolkaScanCheckHarvesterTaskResource(BaseResource):

    def on_get(self, req, resp, task_id):

        task_result = AsyncResult(task_id)
        result = {'status': task_result.status, 'result': task_result.result}
        resp.status = falcon.HTTP_200
        resp.media = result


class PolkascanHarvesterQueueResource(BaseResource):

    def on_get(self, req, resp):

        last_known_block = Block.query(self.session).order_by(Block.id.desc()).first()

        if not last_known_block:
            resp.media = {
                'status': 'success',
                'data': {
                    'message': 'Harvester waiting for first run'
                }
            }
        else:

            remaining_sets_result = Block.get_missing_block_ids(self.session)

            resp.status = falcon.HTTP_200

            resp.media = {
                'status': 'success',
                'data': {
                    'harvester_head': last_known_block.id,
                    'block_process_queue': [
                        {'from': block_set['block_from'], 'to': block_set['block_to']}
                        for block_set in remaining_sets_result
                    ]
                }
            }


class PolkascanHarvesterStatusResource(BaseResource):

    def on_get(self, req, resp):

        sequencer_task = Status.get_status(self.session, 'SEQUENCER_TASK_ID')
        integrity_head = Status.get_status(self.session, 'INTEGRITY_HEAD')
        sequencer_head = self.session.query(func.max(BlockTotal.id)).one()[0]
        best_block = Block.query(self.session).filter_by(
            id=self.session.query(func.max(Block.id)).one()[0]).first()

        if best_block:
            best_block_datetime = best_block.datetime.replace(tzinfo=pytz.UTC).timestamp() * 1000
            best_block_nr = best_block.id
        else:
            best_block_datetime = None
            best_block_nr = None

        substrate = SubstrateInterface(
            url=SUBSTRATE_RPC_URL,
            runtime_config=RuntimeConfiguration(),
            type_registry_preset=settings.TYPE_REGISTRY
        )
        chain_head_block_id = substrate.get_block_number(substrate.get_chain_head())
        chain_finalized_block_id = substrate.get_block_number(substrate.get_chain_finalised_head())

        resp.media = {
            'best_block_datetime': best_block_datetime,
            'best_block_nr': best_block_nr,
            'sequencer_task': sequencer_task.value,
            'sequencer_head': sequencer_head,
            'integrity_head': int(integrity_head.value),
            'chain_head_block_id': chain_head_block_id,
            'chain_finalized_block_id': chain_finalized_block_id
        }


class PolkascanProcessBlockResource(BaseResource):

    def on_post(self, req, resp):

        block_hash = None

        if req.media.get('block_id'):
            substrate = SubstrateInterface(
                url=SUBSTRATE_RPC_URL,
                runtime_config=RuntimeConfiguration(),
                type_registry_preset=settings.TYPE_REGISTRY
            )
            block_hash = substrate.get_block_hash(req.media.get('block_id'))
        elif req.media.get('block_hash'):
            block_hash = req.media.get('block_hash')
        else:
            resp.status = falcon.HTTP_BAD_REQUEST
            resp.media = {'errors': ['Either block_hash or block_id should be supplied']}

        if block_hash:
            print('Processing {} ...'.format(block_hash))
            harvester = PolkascanHarvesterService(
                db_session=self.session,
                type_registry=TYPE_REGISTRY,
                type_registry_file=TYPE_REGISTRY_FILE
            )

            block = Block.query(self.session).filter(Block.hash == block_hash).first()

            if block:
                resp.status = falcon.HTTP_200
                resp.media = {'result': 'already exists', 'parentHash': block.parent_hash}
            else:

                amount = req.media.get('amount', 1)

                for nr in range(0, amount):
                    try:
                        block = harvester.add_block(block_hash)
                    except BlockAlreadyAdded as e:
                        print('Skipping {}'.format(block_hash))
                    block_hash = block.parent_hash
                    if block.id == 0:
                        break

                self.session.commit()

                resp.status = falcon.HTTP_201
                resp.media = {'result': 'added', 'parentHash': block.parent_hash}

        else:
            resp.status = falcon.HTTP_404
            resp.media = {'result': 'Block not found'}


class SequenceBlockResource(BaseResource):

    def on_post(self, req, resp):

        block_hash = None

        if 'block_id' in req.media:
            block = Block.query(self.session).filter(Block.id == req.media.get('block_id')).first()
        elif req.media.get('block_hash'):
            block_hash = req.media.get('block_hash')
            block = Block.query(self.session).filter(Block.hash == block_hash).first()
        else:
            block = None
            resp.status = falcon.HTTP_BAD_REQUEST
            resp.media = {'errors': ['Either block_hash or block_id should be supplied']}

        if block:
            print('Sequencing #{} ...'.format(block.id))

            harvester = PolkascanHarvesterService(
                db_session=self.session,
                type_registry=TYPE_REGISTRY,
                type_registry_file=TYPE_REGISTRY_FILE
            )

            if block.id == 1:
                # Add genesis block
                parent_block = harvester.add_block(block.parent_hash)

            block_total = BlockTotal.query(self.session).filter_by(id=block.id).first()
            parent_block = Block.query(self.session).filter(Block.id == block.id - 1).first()
            parent_block_total = BlockTotal.query(self.session).filter_by(id=block.id - 1).first()

            if block_total:
                resp.status = falcon.HTTP_200
                resp.media = {'result': 'already exists', 'blockId': block.id}
            else:

                if parent_block_total:
                    parent_block_total = parent_block_total.asdict()

                if parent_block:
                    parent_block = parent_block.asdict()

                harvester.sequence_block(block, parent_block, parent_block_total)

                self.session.commit()

                resp.status = falcon.HTTP_201
                resp.media = {'result': 'added', 'parentHash': block.parent_hash}

        else:
            resp.status = falcon.HTTP_404
            resp.media = {'result': 'Block not found'}


class StartSequenceBlockResource(BaseResource):

    def on_post(self, req, resp):

        sequencer_task = Status.get_status(self.session, 'SEQUENCER_TASK_ID')

        if sequencer_task.value is None:
            # 3. IF NOT RUNNING: set task id is status table
            sequencer_task.value = "123"
            sequencer_task.save(self.session)

            harvester = PolkascanHarvesterService(
                db_session=self.session,
                type_registry=TYPE_REGISTRY,
                type_registry_file=TYPE_REGISTRY_FILE
            )
            result = harvester.start_sequencer()

            sequencer_task.value = None
            sequencer_task.save(self.session)

        # 4. IF RUNNING: check if task id is active
        else:

            # task_result = AsyncResult(sequencer_task)
            # task_result = {'status': task_result.status, 'result': task_result.result}
            sequencer_task.value = None
            sequencer_task.save(self.session)

            result = 'Busy'

        self.session.commit()

        resp.media = {
            'result': result
        }


class ProcessGenesisBlockResource(BaseResource):

    def on_post(self, req, resp):

        harvester = PolkascanHarvesterService(
            db_session=self.session,
            type_registry=TYPE_REGISTRY,
            type_registry_file=TYPE_REGISTRY_FILE
        )
        block = Block.query(self.session).get(1)
        if block:
            result = harvester.process_genesis(block=block)
        else:
            result = 'Block #1 required to process genesis'

        self.session.commit()

        resp.media = {
            'result': result
        }


class StartIntegrityResource(BaseResource):

    def on_post(self, req, resp):
        harvester = PolkascanHarvesterService(
            db_session=self.session,
            type_registry=TYPE_REGISTRY,
            type_registry_file=TYPE_REGISTRY_FILE
        )
        try:
            result = harvester.integrity_checks()
        except BlockIntegrityError as e:
            result = str(e)

        resp.media = {
            'result': result
        }


class RebuildSearchIndexResource(BaseResource):

    def on_post(self, req, resp):
        if settings.CELERY_RUNNING:
            task = rebuild_search_index.delay()
            data = {
                'task_id': task.id
            }
        else:
            data = rebuild_search_index()

        resp.status = falcon.HTTP_201

        resp.media = {
            'status': 'Search index rebuild task created',
            'data': data
        }


class RebuildAccountInfoResource(BaseResource):

    def on_post(self, req, resp):
        if settings.CELERY_RUNNING:
            task = rebuild_account_info_snapshot.delay()
            data = {
                'task_id': task.id
            }
        else:
            data = rebuild_account_info_snapshot()

        resp.status = falcon.HTTP_201

        resp.media = {
            'status': 'Search index rebuild task created',
            'data': data
        }
