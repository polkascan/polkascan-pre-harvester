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
#  base.py


class BaseService(object):
    pass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ProcessorRegistry(metaclass=Singleton):

    registry = {'event': {}, 'extrinsic': {}, 'block': []}

    @classmethod
    def all_subclasses(cls, class_):
        return set(class_.__subclasses__()).union(
            [s for c in class_.__subclasses__() for s in cls.all_subclasses(c)])

    def __init__(self):
        for cls in self.all_subclasses(EventProcessor):
            key = '{}-{}'.format(cls.module_id, cls.event_id)

            if key not in self.registry['event']:
                self.registry['event'][key] = []

            self.registry['event']['{}-{}'.format(cls.module_id, cls.event_id)].append(cls)

        for cls in self.all_subclasses(ExtrinsicProcessor):
            key = '{}-{}'.format(cls.module_id, cls.call_id)

            if key not in self.registry['extrinsic']:
                self.registry['extrinsic'][key] = []

            self.registry['extrinsic'][key].append(cls)

        for cls in self.all_subclasses(BlockProcessor):
            self.registry['block'].append(cls)

    def get_event_processors(self, module_id, event_id):
        return self.registry['event'].get('{}-{}'.format(module_id, event_id), [])

    def get_extrinsic_processors(self, module_id, call_id):
        return self.registry['extrinsic'].get('{}-{}'.format(module_id, call_id), [])

    def get_block_processors(self):
        return self.registry['block']


class Processor(object):

    def process(self, db_session):
        raise NotImplemented()


class EventProcessor(Processor):

    module_id = None
    event_id = None

    def __init__(self, block, event, extrinsic=None):
        self.block = block
        self.event = event
        self.extrinsic = extrinsic


class ExtrinsicProcessor(Processor):

    module_id = None
    call_id = None

    def __init__(self, block, extrinsic):
        self.block = block
        self.extrinsic = extrinsic


class BlockProcessor(Processor):

    def __init__(self, block):
        self.block = block
