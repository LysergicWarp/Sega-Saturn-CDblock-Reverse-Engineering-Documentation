#!/usr/bin/env python3
"""Replay the Saturn CD block's sector error correction with the tables from a firmware dump.

Task 1 repairs a data sector with the two layers of parity that Mode 1 and Mode 2 Form 1 sectors
carry (ECMA-130 Annex A). A P pass checks the 43 columns, a Q pass the 26 diagonals, and each
fixes a single wrong byte wherever one vector can place it. The firmware runs P, Q and P, then as
many Q and P pairs as the ECC count allows, and its result word decides between delivering the
sector and the retry rules. This script runs the same passes on a sector you damage.

usage:
  correct.py [--shift N] DUMP [SCRIPT]
  correct.py [--shift N] DUMP -c "COMMAND; COMMAND; ..."

Commands come from SCRIPT, from -c, or from standard input, one per line. Text after # is a
comment. File paths in commands are relative to the current directory. CDB104, CDB105, CDB106 and
YGR022 are recognized by SHA-1. For another dump, --shift gives the distance of its tables from
their CDB105 addresses.

commands:
  sector mode1 [ADDRESS]   a Mode 1 sector with its EDC and parity, at ADDRESS (LBA or MM:SS:FF,
                           default LBA 0)
  sector form1 [ADDRESS]   a Mode 2 Form 1 sector, the same way
  sector FILE [INDEX]      raw 2352-byte sector INDEX (default 0) from FILE
  error ROW COLUMN BYTE VALUE
                           XOR VALUE (hex) into byte BYTE (0 or 1) of the word at ROW (0..25) and
                           COLUMN (0..42)
  byte OFFSET VALUE        XOR VALUE (hex) into sector byte OFFSET (12..2351)
  ecc COUNT                the ECC count of Initialize CD Block (hex, 0..7f, default 0)
  correct                  run task 1's passes on the sector

The 2340 bytes from the header on are 1170 words of two bytes. Words 0..1117 form 26 rows of 43
columns. The Q parity words 1118..1169 are reached with byte: diagonal d keeps its two at bytes
2248 + 2d and 2300 + 2d, plus the byte position 0 or 1.

example files, next to this script:
  single-errors.txt     one error per vector: P and Q fix all of them
  q-completes.txt       two errors in one column: P fails, Q fixes both
  p-completes.txt       the Q result kept after a P repair, after the second P pass and in the
                        last pair, each with one pair more
  cycle.txt             errors no pass can place, through five pairs

examples, from the repository's top folder with your dump there as cdb105.bin:
  python scripts/correction/correct.py cdb105.bin scripts/correction/single-errors.txt
  python scripts/correction/correct.py cdb105.bin -c "sector mode1; error 6 20 1 04; correct"
"""

import argparse
import hashlib
import inspect
import sys

# SHA-1 of each known dump, and the distance of its tables from their CDB105 addresses.
REVISIONS = {
    'fb0993246ed0ad27ca086854295eccd412196254': ('CDB104', 0x00),
    'eb8393058f324e922c11b43709b64fc6ca94ab86': ('CDB105', 0x00),
    'b3c20fbe57cd2eb595e9edac86817e5948dccae4': ('CDB106', 0x10),
    'f4f6c2aac68c352814d396ae41f81f54ad228e68': ('YGR022', 0x10),
}

# CDB105 table addresses.
LOG_TABLE = 0x675c      # 256 bytes: the logarithm of each byte in GF(2^8)
LANE_TABLE = 0x685c     # 16 big-endian longwords: the reduction after a shift of four lanes

SECTOR = 2352
WORDS = 1170
ROWS, COLUMNS = 26, 43
DIAGONALS = 26
MAX_PAIRS = 5


class Failure(Exception):
    pass


def field():
    """Powers of alpha in GF(2^8) with the field polynomial x^8 + x^4 + x^3 + x^2 + 1."""
    powers, x = [], 1
    for _ in range(255):
        powers.append(x)
        x <<= 1
        if x & 0x100:
            x ^= 0x11d
    return powers


POWERS = field()


def lane_entry(index):
    """The reduction longword for one table index. Bit 3 of the index is the carry out of bit 31,
    bits 2, 1 and 0 are bits 24, 16 and 8 of the shifted value, inverted. The longword clears each
    bit that crossed into the next lane and adds 0x1d (x^8 = x^4 + x^3 + x^2 + 1) to each lane that
    overflowed."""
    word = 0x1d000000 if index & 8 else 0
    for bit, lane in ((2, 16), (1, 8), (0, 0)):
        if not index & 1 << bit:
            word ^= 0x01000000 >> (16 - lane) ^ 0x1d << lane
    return word


class Tables:
    def __init__(self, rom, shift):
        self.log = rom[LOG_TABLE + shift:LOG_TABLE + shift + 256]
        self.lanes = [int.from_bytes(rom[LANE_TABLE + shift + 4 * i:LANE_TABLE + shift + 4 * i + 4],
                                     'big') for i in range(16)]
        if (any(self.log[POWERS[i]] != i for i in range(255))
                or self.lanes != [lane_entry(i) for i in range(16)]):
            raise Failure(f'no correction tables at shift {shift:#x}')

    def times_alpha(self, value):
        """Multiply every byte lane of a 32-bit value by alpha: shift left, then apply the table
        entry the carry and the crossed bits select."""
        shifted = value << 1 & 0xffffffff
        index = (value >> 31) << 3
        for bit, mask in ((2, 1 << 24), (1, 1 << 16), (0, 1 << 8)):
            if not shifted & mask:
                index |= 1 << bit
        return shifted ^ self.lanes[index]


def load(path, shift=None):
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
    return Tables(rom, shift)


def p_vector(column):
    """Word numbers of P vector `column`: the 26 words of the column."""
    return [COLUMNS * m + column for m in range(ROWS)]


def q_vector(diagonal):
    """Word numbers of Q vector `diagonal`: 43 words along the diagonal, then its two parity
    words."""
    return ([(44 * m + 43 * diagonal) % 1118 for m in range(COLUMNS)]
            + [1118 + diagonal, 1144 + diagonal])


P_VECTORS = [p_vector(v) for v in range(COLUMNS)]
Q_VECTORS = [q_vector(v) for v in range(DIAGONALS)]


def offset(word, position):
    return 12 + 2 * word + position


def place(word, position):
    if word < 1118:
        return f'row {word // COLUMNS} column {word % COLUMNS} byte {position}'
    element = 43 if word < 1144 else 44
    diagonal = word - (1118 if element == 43 else 1144)
    return f'diagonal {diagonal} parity {element - 43} byte {position}'


def slow_multiply(a, b):
    """Multiplication in GF(2^8) for building sectors, independent of the dump."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11d
        b >>= 1
    return result


def encode_vector(sector, words, position):
    """Set the last two elements of a vector so that the sum and the weighted sum are 0."""
    n = len(words)
    a = w = 0
    for m, word in enumerate(words[:-2]):
        value = sector[offset(word, position)]
        a ^= value
        w ^= slow_multiply(value, POWERS[n - 1 - m])
    # p0 + p1 = a and alpha p0 + p1 = w give p0 = (a + w) / (alpha + 1), and alpha + 1 is 3.
    p0 = slow_multiply(a ^ w, POWERS[(255 - POWERS.index(3)) % 255])
    sector[offset(words[-2], position)] = p0
    sector[offset(words[-1], position)] = a ^ p0


def edc(data):
    """The EDC: a CRC with (x^16 + x^15 + x^2 + 1)(x^16 + x^2 + x + 1), least significant bit
    first."""
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = crc >> 1 ^ (0xd8018001 if crc & 1 else 0)
    return crc


def bcd(value):
    return value // 10 << 4 | value % 10


def generate(mode, frame):
    sector = bytearray(SECTOR)
    sector[1:11] = b'\xff' * 10
    sector[12:16] = bytes([bcd(frame // 4500), bcd(frame // 75 % 60), bcd(frame % 75),
                           1 if mode == 'mode1' else 2])
    if mode == 'mode1':
        for i in range(16, 2064):
            sector[i] = (i * 7 + frame) & 0xff
        sector[2064:2068] = edc(sector[0:2064]).to_bytes(4, 'little')
    else:
        sector[16:24] = bytes([1, 0, 0x08, 0]) * 2
        for i in range(24, 2072):
            sector[i] = (i * 5 + frame) & 0xff
        sector[2072:2076] = edc(sector[16:2072]).to_bytes(4, 'little')
    header = bytes(sector[12:16])
    if mode == 'form1':
        sector[12:16] = bytes(4)
    for position in (0, 1):
        for words in P_VECTORS:
            encode_vector(sector, words, position)
        for words in Q_VECTORS:
            encode_vector(sector, words, position)
    sector[12:16] = header
    return sector


def edc_matches(sector):
    if sector[15] == 1:
        return edc(sector[0:2064]).to_bytes(4, 'little') == sector[2064:2068]
    return edc(sector[16:2072]).to_bytes(4, 'little') == sector[2072:2076]


class Pass:
    def __init__(self, kind):
        self.kind, self.fixed, self.failed = kind, [], []

    def result(self):
        return min(len(self.fixed), 0x7f) | (0x80 if self.failed else 0)


def run_pass(sector, kind, tables):
    """One pass. Each vector's words are read as big-endian halfwords, two lanes: the word's first
    byte in bits 8..15 and its second in bits 0..7. S0 is the XOR of the elements, S1 the running
    value times alpha plus the next element."""
    found = Pass(kind)
    for number, words in enumerate(P_VECTORS if kind == 'P' else Q_VECTORS):
        s0 = s1 = 0
        for word in words:
            element = sector[offset(word, 0)] << 8 | sector[offset(word, 1)]
            s0 ^= element
            s1 = tables.times_alpha(s1) ^ element
        n = len(words)
        for position, lane in ((0, 8), (1, 0)):
            a, b = s0 >> lane & 0xff, s1 >> lane & 0xff
            if not a and not b:
                continue
            name = f'{"column" if kind == "P" else "diagonal"} {number} byte {position}'
            if not a or not b:
                found.failed.append(name)
                continue
            k = (tables.log[b] - tables.log[a]) % 255
            if k >= n:
                found.failed.append(name)
                continue
            word = words[n - 1 - k]
            sector[offset(word, position)] ^= a
            found.fixed.append(place(word, position))
    return found


def check_count(sector):
    """The vectors whose syndromes are not both 0. Mode 2 parity covers a zero header."""
    if sector[15] == 2:
        sector = sector[:12] + bytes(4) + sector[16:]
    bad = 0
    for words in P_VECTORS + Q_VECTORS:
        n = len(words)
        for position in (0, 1):
            s0 = s1 = 0
            for m, word in enumerate(words):
                value = sector[offset(word, position)]
                s0 ^= value
                s1 ^= slow_multiply(value, POWERS[n - 1 - m])
            bad += bool(s0 or s1)
    return bad


def address(text):
    try:
        if ':' in text:
            minutes, seconds, frames = (int(part) for part in text.split(':'))
            return (minutes * 60 + seconds) * 75 + frames
        return int(text) + 150
    except ValueError:
        raise Failure(f'{text} is not an LBA or MM:SS:FF') from None


def hexadecimal(text, limit):
    try:
        value = int(text, 16)
    except ValueError:
        raise Failure(f'{text} is not hexadecimal') from None
    if not 0 <= value <= limit:
        raise Failure(f'{text} is out of range')
    return value


def number(text, limit):
    if not text.isdigit() or int(text) > limit:
        raise Failure(f'{text} is not a number from 0 to {limit}')
    return int(text)


def msf(frame):
    return f'{frame // 4500:02d}:{frame // 75 % 60:02d}:{frame % 75:02d}'


class Session:
    def __init__(self, tables):
        self.tables = tables
        self.sector = None
        self.ecc = 0

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
        command(*arguments)

    def command_sector(self, source, where=None):
        if source in ('mode1', 'form1'):
            frame = address(where or '0')
            self.sector = generate(source, frame)
            kind = 'Mode 1' if source == 'mode1' else 'Mode 2 Form 1'
            print(f'sector: {kind} at {msf(frame)}, EDC and parity in place')
            return
        index = number(where or '0', 10 ** 9)
        with open(source, 'rb') as file:
            file.seek(index * SECTOR)
            data = file.read(SECTOR)
        if len(data) != SECTOR:
            raise Failure(f'sector {index:,} is past the end of {source}')
        self.sector = bytearray(data)
        print(f'sector: {source} sector {index:,}, mode {data[15]}')

    def loaded(self):
        if self.sector is None:
            raise Failure('make or read a sector first')
        return self.sector

    def damage(self, at, value, where):
        sector = self.loaded()
        value = hexadecimal(value, 0xff)
        if value == 0:
            raise Failure('an error of 0 changes nothing')
        sector[at] ^= value
        print(f'error: {value:02x} into {where} (byte {at})')

    def command_error(self, row, column, position, value):
        row, column, position = number(row, ROWS - 1), number(column, COLUMNS - 1), number(position, 1)
        word = COLUMNS * row + column
        self.damage(offset(word, position), value, place(word, position))

    def command_byte(self, at, value):
        at = number(at, SECTOR - 1)
        if at < 12:
            raise Failure('bytes 0..11 are the sync pattern, which no vector holds')
        word, position = divmod(at - 12, 2)
        self.damage(at, value, place(word, position))

    def command_ecc(self, count):
        self.ecc = hexadecimal(count, 0x7f)
        print(f'ecc: {self.ecc:#04x}')

    def command_correct(self):
        sector = self.loaded()
        header = bytes(sector[12:16])
        mode2 = sector[15] == 2
        if mode2:
            sector[12:16] = bytes(4)
        passes = []

        def step(kind):
            found = run_pass(sector, kind, self.tables)
            passes.append(found)
            return found.result()

        p = step('P')
        q = step('Q')
        p = step('P')
        if p and self.ecc:
            pairs = min(self.ecc, MAX_PAIRS)
            while True:
                q = step('Q')
                if not q:
                    break
                p = step('P')
                if not p:
                    break
                pairs -= 1
                if not pairs:
                    break
        if mode2 and not any(sector[12:16]):
            sector[12:16] = header
        print(f'correct: ECC count {self.ecc:#04x}' + (', mode 2 header zero while decoding'
                                                       if mode2 else ''))
        for found in passes:
            line = f'  {found.kind} pass  {found.result():02x}'
            if found.fixed:
                line += f'  fixed {len(found.fixed)}: ' + ', '.join(found.fixed)
            if found.failed:
                line += f'  failed {len(found.failed)}: ' + ', '.join(found.failed)
            print(line)
        word = q << 8 | p
        if word & 0x8080:
            verdict = 'bit 7 is set, so task 5 applies the retry rules'
        else:
            verdict = 'task 5 delivers the sector'
        print(f'  result word {word:04x}: {verdict}')
        bad = check_count(sector)
        whole = 'every vector checks' if not bad else f'{bad} vectors still fail their check'
        edc_text = 'matches' if edc_matches(sector) else 'does not match'
        print(f'  afterwards {whole}, and the EDC {edc_text}. The firmware does not check the EDC')


def main():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS, description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dump')
    parser.add_argument('script', nargs='?')
    parser.add_argument('-c', dest='commands')
    parser.add_argument('--shift', type=lambda text: int(text, 0))
    options = parser.parse_args()
    try:
        session = Session(load(options.dump, options.shift))
        if options.commands is not None:
            lines = options.commands.split(';')
        elif options.script is not None:
            with open(options.script) as file:
                lines = file.read().splitlines()
        else:
            lines = sys.stdin
    except (Failure, OSError) as error:
        sys.exit(f'correct.py: {error}')
    interactive = options.commands is None and options.script is None and sys.stdin.isatty()
    for count, line in enumerate(lines, 1):
        try:
            session.run(line)
        except (Failure, OSError) as error:
            message = f'line {count}: {error}' if options.commands is None else str(error)
            sys.stdout.flush()
            print(f'correct.py: {message}', file=sys.stderr)
            if not interactive:
                sys.exit(1)


if __name__ == '__main__':
    main()
