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
#  main.py

from app.settings import DB_CONNECTION, DEBUG

import falcon

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.middleware.context import ContextMiddleware
from app.middleware.sessionmanager import SQLAlchemySessionManager

from app.resources.harvester import PolkascanStartHarvesterResource, PolkascanStopHarvesterResource, \
    PolkascanHarvesterStatusResource, PolkascanProcessBlockResource, \
    PolkaScanCheckHarvesterTaskResource, SequenceBlockResource, StartSequenceBlockResource, StartIntegrityResource, \
    RebuildSearchIndexResource, ProcessGenesisBlockResource, PolkascanHarvesterQueueResource, RebuildAccountInfoResource
from app.resources.tools import ExtractMetadataResource, ExtractExtrinsicsResource, \
    HealthCheckResource, ExtractEventsResource, CreateSnapshotResource

# Database connection
engine = create_engine(DB_CONNECTION, echo=DEBUG, isolation_level="READ_UNCOMMITTED")
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Define application
app = falcon.API(middleware=[ContextMiddleware(), SQLAlchemySessionManager(session_factory)])

# Application routes
app.add_route('/healthcheck', HealthCheckResource())

app.add_route('/start', PolkascanStartHarvesterResource())
app.add_route('/stop', PolkascanStopHarvesterResource())
app.add_route('/status', PolkascanHarvesterStatusResource())
app.add_route('/queue', PolkascanHarvesterQueueResource())
app.add_route('/process', PolkascanProcessBlockResource())
app.add_route('/sequence', SequenceBlockResource())
app.add_route('/sequencer/start', StartSequenceBlockResource())
app.add_route('/integrity-check', StartIntegrityResource())
app.add_route('/process-genesis', ProcessGenesisBlockResource())
app.add_route('/rebuild-searchindex', RebuildSearchIndexResource())
app.add_route('/rebuild-balances', RebuildAccountInfoResource())
app.add_route('/task/result/{task_id}', PolkaScanCheckHarvesterTaskResource())

app.add_route('/tools/metadata/extract', ExtractMetadataResource())
app.add_route('/tools/extrinsics/extract', ExtractExtrinsicsResource())
app.add_route('/tools/events/extract', ExtractEventsResource())
app.add_route('/tools/balance-snapshot', CreateSnapshotResource())

