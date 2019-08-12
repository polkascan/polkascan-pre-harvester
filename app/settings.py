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
#  settings.py

import os

DB_NAME = os.environ.get("DB_NAME", "polkascan")
DB_HOST = os.environ.get("DB_HOST", "mysql")
DB_PORT = os.environ.get("DB_PORT", 3306)
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")

DB_CONNECTION = os.environ.get("DB_CONNECTION", "mysql+mysqlconnector://{}:{}@{}:{}/{}".format(
    DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
))

SUBSTRATE_RPC_URL = os.environ.get("SUBSTRATE_RPC_URL", "http://substrate-node:9933/")
SUBSTRATE_ADDRESS_TYPE = int(os.environ.get("SUBSTRATE_ADDRESS_TYPE", 42))

TYPE_REGISTRY = os.environ.get("TYPE_REGISTRY", "default")

DEBUG = bool(os.environ.get("DEBUG", False))

# Constants

ACCOUNT_AUDIT_TYPE_NEW = 1
ACCOUNT_AUDIT_TYPE_REAPED = 2

ACCOUNT_INDEX_AUDIT_TYPE_NEW = 1
ACCOUNT_INDEX_AUDIT_TYPE_REAPED = 2

DEMOCRACY_PROPOSAL_AUDIT_TYPE_PROPOSED = 1
DEMOCRACY_PROPOSAL_AUDIT_TYPE_TABLED = 2

DEMOCRACY_REFERENDUM_AUDIT_TYPE_STARTED = 1
DEMOCRACY_REFERENDUM_AUDIT_TYPE_PASSED = 2
DEMOCRACY_REFERENDUM_AUDIT_TYPE_NOTPASSED = 3
DEMOCRACY_REFERENDUM_AUDIT_TYPE_CANCELLED = 4
DEMOCRACY_REFERENDUM_AUDIT_TYPE_EXECUTED = 5


try:
    from app.local_settings import *
except ImportError:
    pass
