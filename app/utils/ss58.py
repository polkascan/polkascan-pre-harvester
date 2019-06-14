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
#  ss58.py

""" SS58 is a simple address format designed for Substrate based chains. 
    Encoding/decoding according to specification on https://wiki.parity.io/External-Address-Format-(SS58)

"""
import base58
from hashlib import blake2b


def ss58_decode(address, valid_address_type=42):
    checksum_prefix = b'SS58PRE'

    ss58_format = base58.b58decode(address)

    if ss58_format[0] != valid_address_type:
        raise ValueError("Invalid Address type")

    # Public keys has a two byte checksum, account index 1 byte
    if len(ss58_format) == 35:
        checksum_length = 2
    else:
        checksum_length = 1

    checksum = blake2b(checksum_prefix + ss58_format[0:-checksum_length]).digest()

    if checksum[0:checksum_length] != ss58_format[-checksum_length:]:
        raise ValueError("Invalid checksum")

    return ss58_format[1:33].hex()


def ss58_encode(address, address_type=42):
    checksum_prefix = b'SS58PRE'

    address_bytes = bytes.fromhex(address)
    
    if len(address_bytes) == 32:
        # Checksum size is 2 bytes for public key
        checksum_length = 2
    elif len(address_bytes) in [1, 2, 4, 8]:
        # Checksum size is 1 byte for account index
        checksum_length = 1
    else:
        raise ValueError("Invalid length for address")

    address_format = bytes([address_type]) + address_bytes
    checksum = blake2b(checksum_prefix + address_format).digest()

    return base58.b58encode(address_format + checksum[:checksum_length]).decode()


#print(ss58_decode('5D68ZpzRB3SGBBGgv4iaRfwR7K8XPpuD99g7Rja9cD9TiNHe'))

#print(ss58_encode('2d52a8b05d209a6fecdc3d80941cf0a571353d4203b0858c44b5e27b0eeee3c4'))
