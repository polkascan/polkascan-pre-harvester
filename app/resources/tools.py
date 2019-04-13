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
#  tools.py

import falcon

from app.resources.base import BaseResource

from scalecodec.base import ScaleBytes
from scalecodec.metadata import MetadataDecoder
from scalecodec.block import EventsDecoder, ExtrinsicsDecoder, ExtrinsicsBlock61181Decoder

from substrateinterface import SubstrateInterface
from app.settings import SUBSTRATE_RPC_URL


class PolkascanExtractMetadataResource(BaseResource):

    def on_get(self, req, resp):

        if 'block_hash' in req.params:
            substrate = SubstrateInterface(SUBSTRATE_RPC_URL)
            json_metadata = substrate.get_block_metadata(req.params.get('block_hash'))
            data = ScaleBytes(json_metadata.get('result'))

            metadata = MetadataDecoder(data)

            resp.status = falcon.HTTP_200
            resp.media = metadata.decode()
        else:
            resp.status = falcon.HTTP_BAD_REQUEST

    def on_post(self, req, resp):
        metadata = MetadataDecoder(ScaleBytes(req.media.get('result')))

        resp.status = falcon.HTTP_200
        resp.media = metadata.process()


class PolkascanExtractExtrinsicsResource(BaseResource):

    def on_get(self, req, resp):

        substrate = SubstrateInterface(SUBSTRATE_RPC_URL)

        # Get extrinsics
        json_block = substrate.get_chain_block(req.params.get('block_hash'))

        if not json_block['result']:
            resp.status = falcon.HTTP_404
        else:

            extrinsics = json_block['result']['block']['extrinsics']

            # Get metadata
            json_metadata = substrate.get_block_metadata(json_block['result']['block']['header']['parentHash'])
            data = ScaleBytes(json_metadata.get('result'))
            metadata_decoder = MetadataDecoder(data)
            metadata_decoder.decode()

            #result = [{'runtime': substrate.get_block_runtime_version(req.params.get('block_hash')), 'metadata': metadata_result.get_data_dict()}]
            result = []

            for extrinsic in extrinsics:
                if int(json_block['result']['block']['header']['number'], 16) == 61181:
                    extrinsics_decoder = ExtrinsicsBlock61181Decoder(ScaleBytes(extrinsic), metadata=metadata_decoder)
                else:
                    extrinsics_decoder = ExtrinsicsDecoder(ScaleBytes(extrinsic), metadata=metadata_decoder)
                result.append(extrinsics_decoder.decode())

            resp.status = falcon.HTTP_201
            resp.media = result


class PolkascanExtractEventsResource(BaseResource):

    def on_get(self, req, resp):

        substrate = SubstrateInterface(SUBSTRATE_RPC_URL)

        # Get Parent hash
        json_block = substrate.get_block_header(req.params.get('block_hash'))

        # Get metadata
        json_metadata = substrate.get_block_metadata(json_block['result']['parentHash'])
        data = ScaleBytes(json_metadata.get('result'))
        metadata_decoder = MetadataDecoder(data)
        metadata_decoder.decode()

        # Get events for block hash
        json_events = substrate.get_block_events(req.params.get('block_hash'))

        events_decoder = EventsDecoder(ScaleBytes(json_events.get('result')), metadata=metadata_decoder)

        resp.status = falcon.HTTP_201
        resp.media = {'events': events_decoder.decode(), 'runtime': substrate.get_block_runtime_version(req.params.get('block_hash'))}


class PolkascanHealthCheckResource(BaseResource):
    def on_get(self, req, resp):
        resp.media = {'status': 'OK'}
