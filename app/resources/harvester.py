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
#  harvester.py

import datetime
import uuid

import falcon
from celery.result import AsyncResult
from falcon.media.validators.jsonschema import validate
from sqlalchemy import text

from app.models.data import Block, BlockTotal
from app.resources.base import BaseResource
from app.schemas import load_schema
from app.processors.converters import PolkascanHarvesterService, BlockAlreadyAdded
from substrateinterface import SubstrateInterface
from app.tasks import accumulate_block_recursive, start_harvester
from app.settings import SUBSTRATE_RPC_URL

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


class PolkascanStatusHarvesterResource(BaseResource):

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


class PolkascanProcessBlockResource(BaseResource):

    def on_post(self, req, resp):

        block_hash = None

        if req.media.get('block_id'):
            substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
            block_hash = substrate.get_block_hash(req.media.get('block_id'))
        elif req.media.get('block_hash'):
            block_hash = req.media.get('block_hash')
        else:
            resp.status = falcon.HTTP_BAD_REQUEST
            resp.media = {'errors': ['Either block_hash or block_id should be supplied']}

        if block_hash:
            print('Processing {} ...'.format(block_hash))
            harvester = PolkascanHarvesterService(self.session)

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

            harvester = PolkascanHarvesterService(self.session)

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

