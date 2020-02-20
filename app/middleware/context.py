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
#  context.py

import uuid


def set_context(req, resp):
    if not req.context.get('request_id'):
        req.context['request_id'] = str(uuid.uuid4())

    resp.set_header('request-id', req.context['request_id'])
    resp.set_header('Access-Control-Allow-Origin', '*')
    resp.set_header('Access-Control-Allow-Headers', '*')


class ContextMiddleware(object):
    def process_request(self, req, resp):
        set_context(req, resp)
