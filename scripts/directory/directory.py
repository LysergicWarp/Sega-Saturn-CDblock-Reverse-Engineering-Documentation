#!/usr/bin/env python3
"""Show what the Saturn CD block's file system commands build from an ISO 9660 image.

The CD block reads a directory into a table of 256 records: the directory itself, its parent and
up to 254 files. The window names the files the table holds. Change Directory, Read Directory,
Get File System Scope, Get File Info, Read File and Abort File work on that table. This script
runs the same rules on an image, and warns where the firmware's reads go wrong: the frame range
of Read File on an interleaved file, and Read Directory after Read File on an XA disc.

usage:
  directory.py IMAGE [SCRIPT]
  directory.py IMAGE -c "COMMAND; COMMAND; ..."

IMAGE holds 2048-byte sectors or raw 2352-byte sectors from LBA 0, frame 150, so the volume
descriptor is at frame 166. Commands come from SCRIPT, from -c, or from standard input, one per
line. Text after # is a comment. File IDs number a directory's records from 0: 0 is the directory
itself, 1 its parent and 2 the first file. The names shown come from the directory records. The
firmware's table keeps no names.

commands:
  root              70 with ID ffffff: the volume descriptor, then the root directory
  cd ID             70: change to the directory with this ID
  dir ID            71: Read Directory, move the window to start at this ID
  scope             72: Get File System Scope
  info [ID]         73: the record of one file, or of every file in the window
  read ID [OFFSET]  74: Read File from sector OFFSET of the file (default 0)
  abort             75: Abort File
  table             every record the table holds

make.py, next to this script, builds the example images, plain.iso and xa.iso, in the current
directory.

example files, next to this script:
  window.txt            how Read Directory moves the window through 300 files, on plain.iso
  interleaved.txt       Read File on an interleaved file, on plain.iso
  xa-filter.txt         Read Directory after Read File on an XA disc, on xa.iso

examples, from the repository's top folder:
  python scripts/directory/make.py
  python scripts/directory/directory.py plain.iso scripts/directory/window.txt
  python scripts/directory/directory.py plain.iso -c "root; cd 2; dir 200; scope"
"""

import argparse
import inspect
import sys

RAW, DATA = 2352, 2048
SYNC = b'\x00' + b'\xff' * 10 + b'\x00'
TABLE_FILES = 254
LAST_ID = 0xffffff


class Failure(Exception):
    pass


class Answer(Exception):
    """A command the firmware answers with WAIT or REJECT, or a request that ends early."""


class Image:
    def __init__(self, path):
        with open(path, 'rb') as file:
            self.data = file.read()
        at = 16 * RAW
        if len(self.data) % RAW == 0 and self.data[at:at + 12] == SYNC:
            self.size = RAW
        elif len(self.data) % DATA == 0:
            self.size = DATA
        else:
            raise Failure(f'{path} holds neither 2048- nor 2352-byte sectors')

    def sector(self, frame):
        """The 2048 data bytes of the sector at `frame`: from byte 16 of a raw mode 1 sector, from
        byte 24 of a raw mode 2 sector."""
        at = (frame - 150) * self.size
        if at < 0 or at + self.size > len(self.data):
            raise Failure(f'frame {frame} is outside the image')
        if self.size == DATA:
            return self.data[at:at + DATA]
        start = 24 if self.data[at + 15] == 2 else 16
        return self.data[at + start:at + start + DATA]


class Record:
    """A table record: frame, data length, unit size, gap, file number and attributes."""

    def __init__(self, data, place):
        self.frame = int.from_bytes(data[6:10], 'big') + 150
        self.length = int.from_bytes(data[14:18], 'big')
        self.unit, self.gap = data[26], data[27]
        size = data[32]
        name = data[33:33 + size]
        self.name = {b'\x00': '.', b'\x01': '..'}.get(name, name.decode('ascii', 'replace'))
        system_use = 33 + size + (1 - size % 2)
        self.number, xa = 0, 0
        if system_use < len(data):
            area = data[system_use:] + bytes(9)
            xa, self.number = area[4], area[8]
        self.attributes = (2 if data[25] & 2 else 0) | (xa & 0xf8)
        self.place = place

    def is_directory(self):
        if self.attributes & 0xf8:
            return bool(self.attributes & 0x80)
        return bool(self.attributes & 2)

    def sectors(self):
        return (self.length + DATA - 1) // DATA

    def words(self):
        return [self.frame >> 16, self.frame & 0xffff, self.length >> 16, self.length & 0xffff,
                self.unit << 8 | self.gap, self.number << 8 | self.attributes]

    def line(self, fid):
        interleave = f'  unit {self.unit} gap {self.gap}' if self.unit else ''
        xa = f'  file number {self.number}' if self.number else ''
        kind = '  directory' if self.is_directory() else ''
        return (f'{fid:5}  {self.name:<14} frame {self.frame:<7} {self.length:>9} bytes  '
                f'attributes {self.attributes:02x}{kind}{interleave}{xa}')


def read_directory(image, frame, sectors):
    """Every record of a directory, parsed from each sector's start until a record length of 0
    or the sector's end."""
    records = []
    for s in range(max(sectors, 1)):
        data = image.sector(frame + s)
        at = 0
        while at < DATA and data[at]:
            length = data[at]
            records.append(Record(data[at:at + length], (frame + s, at)))
            at += length
    return records


def frame_text(frame):
    return f'frame {frame} ({frame // 4500:02d}:{frame // 75 % 60:02d}:{frame % 75:02d})'


def frames_text(frames):
    if len(frames) == 1:
        return f'frame {frames[0]}'
    return f'frames {", ".join(map(str, frames[:-1]))} and {frames[-1]}'


def plural(count, word):
    return f'{count} {word}' + ('' if count == 1 else 's')


def number(text, limit=None):
    try:
        value = int(text, 16) if text.lower() == 'ffffff' else int(text)
    except ValueError:
        raise Failure(f'{text} is not a number') from None
    if value < 0 or limit is not None and value > limit:
        raise Failure(f'{text} is out of range')
    return value


class Session:
    def __init__(self, image):
        self.image = image
        self.root = None             # frame and sectors of the root, once known
        self.records = None          # every record of the current directory
        self.first = self.count = 0  # the window
        self.state = 0               # 0 no table, 1 reading, 2 ready, 4 aborting
        self.stuck = False           # a read that never ends
        self.mode, self.file_number = 0x40, 0

    def run(self, line):
        words = line.split('#', 1)[0].split()
        if not words:
            return
        name, arguments = words[0], words[1:]
        command = getattr(self, 'command_' + name, None)
        if command is None:
            raise Failure(f'unknown command {name}')
        try:
            inspect.signature(command).bind(*arguments)
        except TypeError:
            raise Failure(f'wrong arguments for {name}') from None
        try:
            command(*arguments)
        except Answer as answer:
            print(f'  {answer}')

    # The table and the window.

    def window(self, first):
        """The table holds records 0 and 1, then the directory's records from `first`, up to 254
        files."""
        total = len(self.records)
        self.first = first
        self.count = min(TABLE_FILES, max(total - first, 0))

    def at_end(self):
        return self.first + self.count >= len(self.records)

    def in_window(self, fid):
        return fid in (0, 1) or self.first <= fid < self.first + self.count

    def summary(self):
        if not self.count:
            print('  window: no files')
        else:
            last = self.first + self.count - 1
            end = ', the directory\'s last record' if self.at_end() else ''
            print(f'  window: IDs {self.first}..{last}, {self.count} files{end}')
        shown = [0, 1] + list(range(self.first, self.first + self.count))
        if len(shown) > 7:
            shown = shown[:5] + [None] + shown[-2:]
        for fid in shown:
            print('    ...' if fid is None else self.records[fid].line(fid))
        if not self.at_end():
            frame, offset = self.records[self.first + self.count].place
            print(f'  next record kept: {frame_text(frame)}, offset {offset}')

    def parse(self, frame, sectors, first, what):
        self.records = read_directory(self.image, frame, sectors)
        if len(self.records) < 2:
            raise Failure(f'{what} at {frame_text(frame)} has no records')
        self.window(first)
        self.state = 2
        self.mode, self.file_number = 0x40, 0
        print(f'  {what}: {frame_text(frame)}, {plural(sectors, "sector")}, '
              f'{plural(len(self.records) - 2, "file")}')

    # Command checks.

    def accepted(self, name, needs_table=True, during_read=False):
        if self.state == 4:
            raise Answer(f'{name}: WAIT, an abort is in progress')
        if self.stuck and not during_read:
            raise Answer(f'{name}: WAIT, a read is still running. Abort or root ends it')
        if needs_table and self.state == 0:
            raise Answer(f'{name}: REJECT, there is no table')

    def placed(self, name, text):
        fid = number(text)
        if not self.in_window(fid):
            raise Answer(f'{name}: REJECT, ID {fid} is not in the window')
        return fid

    def command_root(self):
        self.accepted('root', needs_table=False, during_read=True)
        print('root')
        if self.stuck:
            self.stuck = False
            print('  the root request replaces the stuck read: filter mode 40, partition f '
                  'emptied, task 6 reads the root')
        if self.root is None:
            data = self.image.sector(166)
            if data[0:6] != b'\x01CD001':
                self.state = 0
                raise Answer('root: frame 166 holds no primary volume descriptor. The request '
                              'ends without a table')
            record = Record(data[156:156 + data[156]], None)
            self.root = (record.frame, record.length // DATA)
            print(f'  volume descriptor: {frame_text(166)}, root at {frame_text(record.frame)}')
        self.parse(*self.root, 2, 'root')
        self.summary()

    def command_cd(self, text):
        self.accepted('cd')
        fid = self.placed('cd', text)
        record = self.records[fid]
        if not record.is_directory():
            raise Answer(f'cd: REJECT, ID {fid} is not a directory')
        print(f'cd {fid}')
        if fid == 0:
            print('  ID 0 is the directory itself: only EFLS, the table and the window stay')
            return
        self.parse(record.frame, record.sectors(), 2, record.name)
        self.summary()

    def command_dir(self, text):
        self.accepted('dir')
        fid = number(text)
        print(f'dir {fid}')
        if fid in (0, 1) or fid == self.first:
            print('  in the window at index 2 or below: only EFLS, the table stays')
        elif self.first < fid < self.first + self.count:
            if self.at_end():
                rest = 'the rest of the table is cleared'
            else:
                rest = 'the rest is read on from the kept record, with filter mode 40'
                self.mode = 0x40
            print(f'  in the window: its records move to index 2, and {rest}')
            self.window(fid)
        elif 2 <= fid < self.first:
            print('  before the window: the whole directory is read again, skipping to it')
            self.mode, self.file_number = 0x40, 0
            self.window(fid)
        elif self.at_end():
            print('  past the window with nothing left to read: only EFLS, the table stays')
            return
        else:
            print('  past the window: the read goes on from the next record, without setting '
                  'the filter mode')
            if self.mode == 0x41 and self.file_number:
                self.stuck = True
                self.state = 1
                print(f'  warning: the filter still has mode 41 and file number '
                      f'{self.file_number} from Read File. On an XA disc the directory\'s '
                      'sectors carry file number 0 and fail the filter, so the read never '
                      'ends. Abort ends it, root replaces it')
                return
            if fid >= len(self.records):
                print('  the skip reaches the directory\'s end: the request ends and the table '
                      'stays')
                return
            self.window(fid)
        self.summary()

    def command_scope(self):
        self.accepted('scope')
        end = 1 if self.at_end() else 0
        first = self.first if self.count else 0  # no files clears the whole window word
        print(f'scope: {self.count} files, first ID {first}, last record flag {end}')

    def command_info(self, text=None):
        self.accepted('info')
        if text is None or number(text) == LAST_ID:
            if not self.count:
                raise Answer('info: REJECT, the window holds no files')
            ids = list(range(self.first, self.first + self.count))
        else:
            ids = [self.placed('info', text)]
        print(f'info: {6 * len(ids)} words')
        for fid in ids:
            words = ' '.join(f'{w:04x}' for w in self.records[fid].words())
            print(f'  {fid:5}  {words}')

    def command_read(self, text, offset='0'):
        self.accepted('read')
        fid = self.placed('read', text)
        record = self.records[fid]
        sectors = record.sectors()
        offset = number(offset)
        if offset >= sectors:
            raise Answer(f'read: REJECT, offset {offset} is not below the file\'s '
                         + plural(sectors, 'sector'))
        u, g = record.unit, record.gap

        def physical(k):
            return record.frame + (k // u * (u + g) + k % u if u else k)

        start, count = physical(offset), sectors - offset
        end = start + count - 1
        self.mode, self.file_number = 0x41, record.number
        print(f'read {fid} from sector {offset}: {record.name}, {plural(sectors, "sector")}')
        print(f'  frames {start}..{end} ({plural(count, "sector")}), filter mode 41, file number '
              f'{record.number}')
        if not u:
            return
        frames = [physical(k) for k in range(offset, sectors)]
        missed = [f for f in frames if f > end]
        gaps = [f for f in range(start, end + 1) if f not in frames]
        print(f'  interleaved: the file\'s sectors lie at frames {frames[0]}..{frames[-1]}, '
              f'units of {u} with gaps of {g}')
        if missed:
            verb = 'lies' if len(missed) == 1 else 'lie'
            print(f'  warning: the range ends before the file does. The file\'s '
                  f'{frames_text(missed)} {verb} past it')
        if gaps:
            verb = 'passes' if len(gaps) == 1 else 'pass'
            print(f'  on a mode 1 disc the gap {frames_text(gaps)} in the range {verb} the '
                  'filter, and the file\'s last sectors are not read')

    def command_abort(self):
        print('abort')
        if self.state == 4 or not self.stuck:
            print('  nothing in progress: only EFLS')
            return
        self.stuck = False
        self.state = 0
        print('  the read ends. The table must be read again')

    def command_table(self):
        self.accepted('table')
        print('table')
        for index, fid in enumerate([0, 1] + list(range(self.first, self.first + self.count))):
            print(f'  record {index:3}  ' + self.records[fid].line(fid))


def main():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS, description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('image')
    parser.add_argument('script', nargs='?')
    parser.add_argument('-c', dest='commands')
    options = parser.parse_args()
    try:
        session = Session(Image(options.image))
        if options.commands is not None:
            lines = options.commands.split(';')
        elif options.script is not None:
            with open(options.script) as file:
                lines = file.read().splitlines()
        else:
            lines = sys.stdin
    except (Failure, OSError) as error:
        sys.exit(f'directory.py: {error}')
    interactive = options.commands is None and options.script is None and sys.stdin.isatty()
    for count, line in enumerate(lines, 1):
        try:
            session.run(line)
        except (Failure, OSError) as error:
            message = f'line {count}: {error}' if options.commands is None else str(error)
            sys.stdout.flush()
            print(f'directory.py: {message}', file=sys.stderr)
            if not interactive:
                sys.exit(1)


if __name__ == '__main__':
    main()
