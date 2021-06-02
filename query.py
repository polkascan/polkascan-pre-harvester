import json
from scalecodec.type_registry import load_type_registry_file
from substrateinterface import SubstrateInterface

substrate = SubstrateInterface(
    url='wss://ws.archivenode-1.ar1.sora2.soramitsu.co.jp/',
    type_registry_preset='default',
    type_registry=load_type_registry_file('../harvester/app/type_registry/custom_types.json'),
)

block_hash = substrate.get_block_hash(block_id=442249)

extrinsics = substrate.get_block_extrinsics(block_hash=block_hash)

print('Extrinsincs:', json.dumps([e.value for e in extrinsics], indent=4))

events = substrate.get_events(block_hash)

print("Events:", json.dumps([e.value for e in events], indent=4))
