#!/usr/bin/env python3
"""Build small ISO 9660 images for directory.py.

usage:
  make.py                  both images, as plain.iso and xa.iso
  make.py OUTPUT           an image without XA fields
  make.py --xa [OUTPUT]    an image whose records carry CD-ROM XA fields, xa.iso by default

Both images hold 2048-byte sectors from LBA 0, with the volume descriptor at LBA 16. Without
OUTPUT the images go to the current directory under the names the example files use.

Without --xa the root holds MANY, a directory of 300 one-sector files, FILM.DAT, an interleaved
file of 6 sectors in units of 2 with gaps of 1, and README.TXT. With --xa the root holds XADIR, a
directory of 300 files with XA attributes, whose first file has file number 1, and DATA.BIN.

examples, from the repository's top folder:
  python scripts/directory/make.py
  python scripts/directory/make.py --xa
  python scripts/directory/make.py example.iso
"""

import argparse
import sys

SECTOR = 2048
FILES = 300
DATE = bytes([95, 11, 22, 12, 0, 0, 36])
XA_FILE = 0x0d55         # form 1 data, with the XA permission bits
XA_DIRECTORY = 0x8d55    # the same with the XA directory bit


class Entry:
    def __init__(self, name, lba=0, size=SECTOR, directory=False, unit=0, gap=0, xa=None,
                 number=0):
        self.name, self.lba, self.size, self.directory = name, lba, size, directory
        self.unit, self.gap, self.xa, self.number = unit, gap, xa, number


def both(value, size):
    return value.to_bytes(size, 'little') + value.to_bytes(size, 'big')


def record(entry, identifier):
    """A directory record: length, extent and data length in both byte orders, the date, flags,
    unit size and gap, volume sequence number, the identifier and its pad byte, then the XA
    system use area."""
    data = bytearray([0, 0]) + both(entry.lba, 4) + both(entry.size, 4) + DATE
    data += bytes([2 if entry.directory else 0, entry.unit, entry.gap]) + both(1, 2)
    data += bytes([len(identifier)]) + identifier
    if len(identifier) % 2 == 0:
        data.append(0)
    if entry.xa is not None:
        data += bytes([0, 0, 0, 0]) + entry.xa.to_bytes(2, 'big') + b'XA'
        data += bytes([entry.number, 0, 0, 0, 0, 0])
    data[0] = len(data)
    return bytes(data)


def directory_sectors(own, parent, entries):
    """The records of a directory in sectors. A record that would cross a sector's end starts the
    next sector."""
    records = [record(own, b'\x00'), record(parent, b'\x01')]
    records += [record(e, e.name.encode() + (b'' if e.directory else b';1')) for e in entries]
    sectors, current = [], bytearray()
    for data in records:
        if len(current) + len(data) > SECTOR:
            sectors.append(bytes(current) + bytes(SECTOR - len(current)))
            current = bytearray()
        current += data
    sectors.append(bytes(current) + bytes(SECTOR - len(current)))
    return sectors


def build(xa):
    root = Entry('', lba=18, directory=True, xa=XA_DIRECTORY if xa else None)
    many = Entry('XADIR' if xa else 'MANY', lba=19, directory=True,
                 xa=XA_DIRECTORY if xa else None)
    files = [Entry(f'F{n:03d}.DAT', xa=XA_FILE if xa else None, number=1 if xa and n == 0 else 0)
             for n in range(FILES)]
    # The directory's size depends on its records, not on where the files lie.
    many.size = len(directory_sectors(many, root, files)) * SECTOR
    lba = many.lba + many.size // SECTOR
    for entry in files:
        entry.lba = lba
        lba += 1
    if xa:
        others = [Entry('DATA.BIN', lba=lba, xa=XA_FILE)]
        lba += 1
    else:
        # 6 file sectors in units of 2 with gaps of 1: 8 frames from the first.
        film = Entry('FILM.DAT', lba=lba, size=6 * SECTOR, unit=2, gap=1)
        readme = Entry('README.TXT', lba=lba + 8, size=100)
        others = [film, readme]
        lba += 9
    top = [many] + others
    root.size = len(directory_sectors(root, root, top)) * SECTOR
    image = bytearray(SECTOR * lba)

    def put(at, data):
        image[at * SECTOR:at * SECTOR + len(data)] = data

    descriptor = bytearray(SECTOR)
    descriptor[0:7] = b'\x01CD001\x01'
    descriptor[156:156 + 34] = record(Entry('', lba=root.lba, size=root.size, directory=True),
                                      b'\x00')
    put(16, descriptor)
    put(17, b'\xffCD001\x01')
    for i, data in enumerate(directory_sectors(root, root, top)):
        put(root.lba + i, data)
    for i, data in enumerate(directory_sectors(many, root, files)):
        put(many.lba + i, data)
    for entry in files + others:
        if entry.unit:
            for k in range(entry.size // SECTOR):
                frame = entry.lba + k // entry.unit * (entry.unit + entry.gap) + k % entry.unit
                put(frame, bytes([k + 1]) * SECTOR)
        else:
            put(entry.lba, entry.name.encode().ljust(SECTOR, b'.'))
    return bytes(image)


def main():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS, description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', nargs='?')
    parser.add_argument('--xa', action='store_true')
    options = parser.parse_args()
    if options.output:
        jobs = [(options.output, options.xa)]
    elif options.xa:
        jobs = [('xa.iso', True)]
    else:
        jobs = [('plain.iso', False), ('xa.iso', True)]
    for output, xa in jobs:
        image = build(xa)
        try:
            with open(output, 'wb') as file:
                file.write(image)
        except OSError as error:
            sys.exit(f'make.py: {error}')
        print(f'{output}: {len(image) // SECTOR} sectors of 2048 bytes')


if __name__ == '__main__':
    main()
