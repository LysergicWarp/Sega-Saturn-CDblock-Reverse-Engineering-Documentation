#!/usr/bin/env python3
"""Identify a Saturn CD-block firmware dump and map addresses between its revisions.

Four revisions are known: CDB104, CDB105, CDB106 and YGR022. This script names the revision of a
dump by its SHA-1 and shows what tells the revisions apart: the version number that Get Hardware
Info answers, the checksum and its compensation longword, and anything other than ff in the unused
space. The guides use CDB105 addresses. CDB104 has the same ones, and CDB106 and YGR022 move most
of the code by 0x10 or 0x12.

usage:
  revision.py DUMP                  identify the dump
  revision.py DUMP ADDRESS ...      also map CDB105 addresses to the dump's revision
  revision.py DUMP -r ADDRESS ...   also map the dump's addresses back to CDB105

Addresses are hexadecimal, with or without 0x.

examples, from the repository's top folder with the dumps there:
  python scripts/revision/revision.py cdb106.bin
  python scripts/revision/revision.py cdb106.bin 28b0 9274 07fe
  python scripts/revision/revision.py ygr022.bin -r 1b16
"""

import argparse
import hashlib
import sys

# SHA-1 of each known dump: its name, and whether it has CDB106's layout.
REVISIONS = {
    'fb0993246ed0ad27ca086854295eccd412196254': ('CDB104', 'CD block 1.04', False),
    'eb8393058f324e922c11b43709b64fc6ca94ab86': ('CDB105', 'CD block 1.05', False),
    'b3c20fbe57cd2eb595e9edac86817e5948dccae4': ('CDB106', 'CD block 1.06', True),
    'f4f6c2aac68c352814d396ae41f81f54ad228e68': ('YGR022', 'YGR022 / 315-5962', True),
}

COMPENSATION = 0x0424
VERSION = 0x9290            # CDB105 address of the word Get Hardware Info answers
INTERFACE_PAGE = (0xf800, 0xfacb)
CODE_END = {False: 0xc4ab, True: 0xc4bb}

# The crosswalk from CDB105 addresses to CDB106 and YGR022: first, last, and the distance, or
# None for a range with no counterpart.
FORWARD = [
    (0x0000, 0x07fb, 0),
    (0x07fc, 0x07ff, None),    # replaced by the drive strap code at 0x07fc..0x0811
    (0x0800, 0x08c9, 0x12),
    (0x08ca, 0x08cb, None),    # the padding word CDB106 drops
    (0x08cc, 0xc4ab, 0x10),
    (0xf800, 0xfacb, 0),
]
BACKWARD = [
    (0x0000, 0x07fb, 0),
    (0x07fc, 0x0811, None),    # the drive strap code
    (0x0812, 0x08db, -0x12),
    (0x08dc, 0xc4bb, -0x10),
    (0xf800, 0xfacb, 0),
]
NO_COUNTERPART = {
    (True, 0x07fc): 'CDB105 instructions that the drive strap code at 0x07fc..0x0811 replaces',
    (True, 0x08ca): 'the padding word that CDB106 drops',
    (False, 0x07fc): 'the drive strap code, which replaces CDB105 0x07fc..0x07ff',
}


class Failure(Exception):
    pass


def word(rom, address, size):
    return int.from_bytes(rom[address:address + size], 'big')


def unused(rom, moved):
    """The unused ranges after the code and after the interface page, and the runs in them that
    are not ff."""
    ranges = [(CODE_END[moved] + 1, INTERFACE_PAGE[0] - 1), (INTERFACE_PAGE[1] + 1, 0xffff)]
    runs = []
    for first, last in ranges:
        address = first
        while address <= last:
            if rom[address] == 0xff:
                address += 1
                continue
            start, value = address, rom[address]
            while address <= last and rom[address] == value:
                address += 1
            runs.append((start, address - 1, value))
    return ranges, runs


def identify(path, rom):
    digest = hashlib.sha1(rom).hexdigest()
    total = sum(word(rom, a, 4) for a in range(0, len(rom), 4)) & 0xffffffff
    known = REVISIONS.get(digest)
    if known is None:
        print(f'{path}: not a known revision')
        print(f'  SHA-1         {digest}')
        print(f'  checksum      sum of the big-endian longwords {total:08x}')
        return None
    name, identity, moved = known
    shift = 0x10 if moved else 0
    print(f'{path}: {name}, {identity}')
    print(f'  SHA-1         {digest}')
    print(f'  version       {word(rom, VERSION + shift, 2)}, the word at {VERSION + shift:#06x} '
          'that Get Hardware Info answers')
    print(f'  checksum      sum of the big-endian longwords {total:08x}, compensation longword '
          f'{word(rom, COMPENSATION, 4):08x} at {COMPENSATION:#06x}')
    ranges, runs = unused(rom, moved)
    spans = ' and '.join(f'{first:#06x}..{last:#06x}' for first, last in ranges)
    if not runs:
        print(f'  unused space  {spans}, all ff')
    else:
        print(f'  unused space  {spans}, ff except:')
        for first, last, value in runs:
            print(f'                  {last - first + 1} bytes of {value:02x} at '
                  f'{first:#06x}..{last:#06x}')
    return moved


def hexadecimal(text):
    try:
        value = int(text, 16)
    except ValueError:
        raise Failure(f'{text} is not hexadecimal') from None
    if not 0 <= value <= 0xffff:
        raise Failure(f'{text} is outside the 64 KB ROM')
    return value


def translate(address, moved, backward):
    """Where `address` lies in the other layout, or why it has no counterpart."""
    if not moved:
        return f'{address:#06x}, the same address'
    for first, last, distance in BACKWARD if backward else FORWARD:
        if first <= address <= last:
            if distance is None:
                return NO_COUNTERPART[(not backward, first)]
            return f'{address + distance:#06x}'
    return 'unused space'


def main():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS, description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dump')
    parser.add_argument('addresses', nargs='*')
    parser.add_argument('-r', dest='backward', action='store_true')
    options = parser.parse_intermixed_args()
    try:
        addresses = [hexadecimal(text) for text in options.addresses]
        with open(options.dump, 'rb') as file:
            rom = file.read()
        if len(rom) != 65536:
            raise Failure(f'{options.dump} is not a 65,536-byte dump')
    except (Failure, OSError) as error:
        sys.exit(f'revision.py: {error}')
    moved = identify(options.dump, rom)
    if not addresses:
        return
    if moved is None:
        sys.exit('revision.py: addresses map only for a known revision')
    print()
    source, target = ('this dump', 'CDB105') if options.backward else ('CDB105', 'this dump')
    print(f'  {source:<11} {target}')
    for address in addresses:
        print(f'  {address:#06x}      {translate(address, moved, options.backward)}')


if __name__ == '__main__':
    main()
