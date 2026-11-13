#!/usr/bin/env python3
"""Decode frames of the link between the Saturn CD block and its drive.

In every frame the CD block sends the drive one command and the drive sends back one report, 13
bytes each way. Bytes 0..10 are the command or the report, byte 11 the inverted sum of bytes
0..10, and byte 12 an answer: from the CD block 00 when the drive's sum matched, from the drive
00 to take the next command or another value to have the same one sent again. This script names
the commands and status codes, decodes the report fields and checks both sums.

usage:
  link.py FRAMES

FRAMES is a text file with two lines per frame: > and the 13 bytes the CD block sent, then < and
the 13 bytes the drive sent, in hexadecimal. Text after # is a comment. Runs of identical frames
with the null command are shown once with their count.

The script reads frames from a text file, so they can come from any logic analyzer export or be
written by hand. It could be adjusted to read frames live from a capture tool instead.

example files, next to this script:
  startup.txt       the first report, the table of contents, and the seek to frame 150
  checksum.txt      a report with a bad sum, and a command the drive asks for again

example, from the repository's top folder:
  python scripts/drive-link/link.py scripts/drive-link/startup.txt
"""

import argparse
import sys

COMMANDS = {
    0x00: 'null', 0x02: 'ring seek', 0x03: 'read TOC', 0x04: 'stop', 0x05: 'standby',
    0x06: 'play', 0x08: 'pause', 0x09: 'seek', 0x0a: 'scan forward', 0x0b: 'scan backward',
    0x0c: 'open tray',
}
STATUS = {
    0: 'TOC entry', 1: 'stopped', 2: 'seeking', 3: 'playing', 4: 'paused', 5: 'scanning',
    8: 'tray or disc', 9: 'TOC end', 11: 'ring seek',
}
TRAY = {0x80: 'tray open', 0x83: 'no disc'}
# Byte 10 of a command read as the speed, as the firmware's use of it suggests. Whether the drive
# takes the byte as its speed is unknown.
SPEED = {0: '', 1: ', single speed', 2: ', double speed'}


class Failure(Exception):
    pass


def checksum(data):
    return ~sum(data[:11]) & 0xff


def bcd(value):
    return (value >> 4) * 10 + (value & 15)


def msf(frame):
    return f'{frame // 4500:02d}:{frame // 75 % 60:02d}:{frame % 75:02d}'


def time_text(data, at):
    return f'{data[at]:02x}:{data[at + 1]:02x}:{data[at + 2]:02x}'


def command_text(data):
    code = data[0]
    if not any(data[:11]):
        return 'null'
    name = COMMANDS.get(code, 'unknown command')
    text = f'{code:02x} {name}'
    frame = int.from_bytes(data[1:4], 'big')
    if code == 0x03:
        text += f', session {data[1]}'
    elif code in (0x06, 0x09) and data[8]:
        text += f', track {data[8]:02x} index {data[4]:02x}'
    elif code in (0x02, 0x06, 0x09):
        text += f', frame {frame} ({msf(frame)})'
    return text + SPEED.get(data[10], f', byte 10 {data[10]:02x}')


def report_text(data):
    status = data[0]
    code = status >> 4
    name = TRAY.get(status, STATUS.get(code, 'unknown status'))
    text = f'status {status:02x}, code {code} {name}'
    if code == 11:
        frame = int.from_bytes(data[3:6], 'big')
        text += (f': report word {data[1]:02x}{data[2]:02x}, frame {frame} ({msf(frame)}), '
                 f'words {data[6]:02x}{data[7]:02x} and {data[8]:02x}{data[9]:02x}')
    elif status & 4:
        control = f'control and ADR {data[1]:02x}'
        if data[2] == 0:
            if data[3] == 0xa0:
                point = f'first track {data[8]:02x}, disc type {data[9]:02x}'
            elif data[3] == 0xa1:
                point = f'last track {data[8]:02x}'
            else:
                point = f'at {time_text(data, 8)}'
            text += (f': {control}, lead-in, point {data[3]:02x} {point}, '
                     f'lead-in time {time_text(data, 4)}')
        else:
            absolute = bcd(data[8]) * 4500 + bcd(data[9]) * 75 + bcd(data[10])
            text += (f': {control}, track {data[2]:02x} index {data[3]:02x}, relative '
                     f'{time_text(data, 4)}, absolute {time_text(data, 8)}, frame {absolute}')
    return text


def read_frames(path):
    frames, pending = [], None
    with open(path) as file:
        for number, line in enumerate(file, 1):
            words = line.split('#', 1)[0].split()
            if not words:
                continue
            side, values = words[0], words[1:]
            try:
                data = bytes(int(v, 16) for v in values)
            except ValueError:
                raise Failure(f'line {number}: bytes are hexadecimal') from None
            if len(data) != 13:
                raise Failure(f'line {number}: a frame side has 13 bytes, not {len(data)}')
            if side == '>':
                if pending is not None:
                    raise Failure(f'line {number}: the frame before has no < line')
                pending = (data, number)
            elif side == '<':
                if pending is None:
                    raise Failure(f'line {number}: a < line needs the > line before it')
                frames.append((pending[0], data, pending[1]))
                pending = None
            else:
                raise Failure(f'line {number}: a line starts with > or <')
    if pending is not None:
        raise Failure(f'line {pending[1]}: the last frame has no < line')
    return frames


def show(index, sent, received, repeats):
    sent_ok = sent[11] == checksum(sent)
    received_ok = received[11] == checksum(received)
    head = f'frame {index}' + (f' (and {repeats - 1} more like it)' if repeats > 1 else '')
    print(head)
    print(f'  > {command_text(sent)}')
    print('    sum ' + ('matches' if sent_ok else f'{sent[11]:02x}, should be {checksum(sent):02x}')
          + f', answer {sent[12]:02x}: '
          + ('the drive\'s sum matched' if sent[12] == 0 else 'the drive\'s sum did not match'))
    if not received_ok:
        print(f'  < report sum {received[11]:02x}, should be {checksum(received):02x}. The CD '
              'block ignores this report')
    else:
        print(f'  < {report_text(received)}')
    print(f'    final byte {received[12]:02x}: '
          + ('the next frame carries the next command' if received[12] == 0
             else 'the CD block sends the same command again'))


def main():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS, description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('frames')
    options = parser.parse_args()
    try:
        frames = read_frames(options.frames)
    except (Failure, OSError) as error:
        sys.exit(f'link.py: {error}')
    index = 0
    while index < len(frames):
        sent, received, _ = frames[index]
        repeats = 1
        if not any(sent[:11]):
            while (index + repeats < len(frames)
                   and frames[index + repeats][:2] == (sent, received)):
                repeats += 1
        show(index + 1, sent, received, repeats)
        index += repeats


if __name__ == '__main__':
    main()
