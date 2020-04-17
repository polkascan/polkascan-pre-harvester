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
from app.models.data import SearchIndex


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

    def initialization_hook(self, db_session):
        """
        Hook during initialization phase, which will be a one-time call during processing of the genesis block
        :param db_session:
        :type db_session: sqlalchemy.orm.Session
        :return:
        """
        pass

    def accumulation_hook(self, db_session):
        """
        Hook during accumulation phase, which means processing on an isolated block level; no context outside the
        current block is available
        :param db_session:
        :type db_session: sqlalchemy.orm.Session
        :return:
        """
        pass

    def accumulation_revert(self, db_session):
        """
        Revert hook during accumulation phase when block was not on correct chain, e.g. fork or uncle, which means
        processing on an isolated block level; no context outside the current block is available
        :param db_session:
        :type db_session: sqlalchemy.orm.Session
        :return:
        """
        pass

    def sequencing_hook(self, db_session, parent_block, parent_sequenced_block):
        """
        Hook during sequencing phase, which means processing block for block from genesis to chaintip where this order
        of processing is crucial
        :param parent_block:
        :param parent_sequenced_block:
        :type parent_sequenced_block: BlockTotal
        :param db_session:
        :type db_session: sqlalchemy.orm.Session
        :return:
        """
        pass

    def aggregation_hook(self, db_session):
        """
        Hook during aggregation phase, which will be a periodic call on several pre-defined timeframes in order to
        write aggregated data over this timeframe
        :param db_session:
        :type db_session: sqlalchemy.orm.Session
        :return:
        """
        pass


class EventProcessor(Processor):

    module_id = None
    event_id = None

    def __init__(self, block, event, extrinsic=None, metadata=None, substrate=None):
        self.block = block
        self.event = event
        self.extrinsic = extrinsic
        self.metadata = metadata
        self.substrate = substrate

    def add_search_index(self, index_type_id, account_id=None, sorting_value=None):
        return SearchIndex(
            index_type_id=index_type_id,
            block_id=self.block.id,
            event_idx=self.event.event_idx,
            extrinsic_idx=self.event.extrinsic_idx,
            account_id=account_id,
            sorting_value=sorting_value
        )

    def process_search_index(self, db_session):
        pass

    def add_search_index(self, index_type_id, account_id=None, sorting_value=None):
        return SearchIndex(
            index_type_id=index_type_id,
            block_id=self.block.id,
            event_idx=self.event.event_idx,
            extrinsic_idx=self.event.extrinsic_idx,
            account_id=account_id,
            sorting_value=sorting_value
        )

    def process_search_index(self, db_session):
        pass


class ExtrinsicProcessor(Processor):

    module_id = None
    call_id = None

    def __init__(self, block, extrinsic, substrate=None):
        self.block = block
        self.extrinsic = extrinsic
        self.substrate = substrate

    def add_search_index(self, index_type_id, account_id=None, sorting_value=None):
        return SearchIndex(
            index_type_id=index_type_id,
            block_id=self.block.id,
            event_idx=None,
            extrinsic_idx=self.extrinsic.extrinsic_idx,
            account_id=account_id,
            sorting_value=sorting_value
        )

    def process_search_index(self, db_session):
        pass


class BlockProcessor(Processor):

    def __init__(self, block, sequenced_block=None, substrate=None, harvester=None):
        self.block = block
        self.sequenced_block = sequenced_block
        self.substrate = substrate
        self.harvester = harvester
