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
#  base.py

from sqlalchemy.orm import Session


class BaseResource(object):

    session: Session

    def get_jsonapi_response(self, data, meta=None, errors=None, links=None, relationships=None, included=None):

        result = {
            'meta': {
                "authors": [
                    "WEB3SCAN",
                    "POLKASCAN",
                    "openAware BV"
                ]
            },
            'errors': [],
            "data": data,
            "links": {}
        }

        if meta:
            result['meta'].update(meta)

        if errors:
            result['errors'] = errors

        if links:
            result['links'] = links

        if relationships:
            result['data']['relationships'] = relationships

        if included:
            result['included'] = included

        return result

