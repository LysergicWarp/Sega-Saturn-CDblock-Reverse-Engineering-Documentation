#!/usr/bin/env python3
"""Print the SEGA logo bitmap stored in a Saturn CD-block firmware dump.

Disc authentication compares sectors from three places on the disc with rows of this bitmap. The
bitmap has 17 rows of 106 bits, 16 bytes to a row, most significant bit first, and the last 22
bits of each row clear. Row 0 is the bottom of the logo. Pass i of a check uses row z + i for the
zone z the timer picks, so rows 15 and 16 are never compared. This script prints the rows from 16
down to 0 beside their numbers, # for a set bit.

usage:
  logo.py [--shift N] DUMP

CDB104, CDB105, CDB106 and YGR022 are recognized by SHA-1. For another dump, --shift gives the
distance of the bitmap from its CDB105 address, 0x8fb4.

examples, from the repository's top folder with the dumps there:
  python scripts/logo/logo.py cdb105.bin
  python scripts/logo/logo.py --shift 0x10 other.bin
"""

import argparse
import hashlib
import sys

# SHA-1 of each known dump, and the distance of its bitmap from the CDB105 address.
REVISIONS = {
    'fb0993246ed0ad27ca086854295eccd412196254': ('CDB104', 0x00),
    'eb8393058f324e922c11b43709b64fc6ca94ab86': ('CDB105', 0x00),
    'b3c20fbe57cd2eb595e9edac86817e5948dccae4': ('CDB106', 0x10),
    'f4f6c2aac68c352814d396ae41f81f54ad228e68': ('YGR022', 0x10),
}

LOGO_BITMAP = 0x8fb4    # CDB105 address of row 0
ROWS, COLUMNS, ROW_BYTES = 17, 106, 16
PADDING = 8 * ROW_BYTES - COLUMNS


class Failure(Exception):
    pass


def load(path, shift=None):
    """The 17 rows of the bitmap as 128-bit numbers, row 0 first."""
    with open(path, 'rb') as file:
        rom = file.read()
    if len(rom) != 65536:
        raise Failure(f'{path} is not a 65,536-byte dump')
    digest = hashlib.sha1(rom).hexdigest()
    name, known = REVISIONS.get(digest, (None, None))
    if shift is None:
        if name is None:
            raise Failure(f'unknown dump {digest}, pass --shift')
        shift = known
    start = LOGO_BITMAP + shift
    if not 0 <= start <= len(rom) - ROWS * ROW_BYTES:
        raise Failure(f'shift {shift:#x} puts the bitmap outside the dump')
    rows = [int.from_bytes(rom[start + ROW_BYTES * row:start + ROW_BYTES * (row + 1)], 'big')
            for row in range(ROWS)]
    if not any(rows) or any(row & (1 << PADDING) - 1 for row in rows):
        raise Failure(f'no logo bitmap at shift {shift:#x}')
    return rows


def main():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS, description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dump')
    parser.add_argument('--shift', type=lambda text: int(text, 0))
    options = parser.parse_args()
    try:
        rows = load(options.dump, options.shift)
    except (Failure, OSError) as error:
        sys.exit(f'logo.py: {error}')
    for number in range(ROWS - 1, -1, -1):
        bits = rows[number] >> PADDING
        line = ''.join('#' if bits >> (COLUMNS - 1 - column) & 1 else ' '
                       for column in range(COLUMNS))
        print(f'{number:2} |{line}|')


if __name__ == '__main__':
    main()
