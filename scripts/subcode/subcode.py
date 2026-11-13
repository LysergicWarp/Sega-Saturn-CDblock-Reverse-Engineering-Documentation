#!/usr/bin/env python3
"""Decode R-W subcode packs as the Saturn CD block does, beside a textbook decoder.

Task 2 checks each 24-symbol pack of R-W subcode with two Reed-Solomon codes over GF(64): Q over
symbols 0..3, which corrects one symbol, and P over the whole pack, which corrects two. For two
errors the firmware finds the error positions with a table and a halving shift instead of a
search. For errors past what the code can correct, the syndromes can point at positions past the
pack's 24 symbols, and for some of those the shift lands inside the pack. The firmware then
changes two good symbols and reports a correction. This script runs the firmware's steps with
the tables from your own dump, and a textbook decoder beside them.

usage:
  subcode.py [--shift N] DUMP [SCRIPT]
  subcode.py [--shift N] DUMP -c "COMMAND; COMMAND; ..."

Commands come from SCRIPT, from -c, or from standard input, one per line. Text after # is a
comment. CDB104, CDB105, CDB106 and YGR022 are recognized by SHA-1. For another dump, --shift
gives the distance of its tables from their CDB105 addresses.

Symbols and error values are six-bit hexadecimal numbers. Symbol 23 - j of a pack has the P
locator alpha^j, so j from 0 to 23 lies in the pack and j from 24 to 62 past it.

commands:
  pack [N]                   a correct pack, made from the number N (default 0)
  error SYMBOL VALUE         XOR VALUE into SYMBOL (0..23, decimal)
  past J1 V1 [J2 V2]         four errors, at symbols 6, 9, 13 and 17, whose P syndromes are those
                             of error V1 at locator alpha^J1, and V2 at alpha^J2 (decimal J)
  decode                     the firmware's P and Q steps, and the textbook decoder on a copy
  pairs                      every pair of locators past the pack that the firmware's shift
                             places inside it

example files, next to this script:
  corrections.txt       one error, two errors, and more than the code can correct
  miscorrection.txt     errors at alpha^40 and alpha^35 corrected at symbols 15 and 19

examples, from the repository's top folder with your dump there as cdb105.bin:
  python scripts/subcode/subcode.py cdb105.bin scripts/subcode/miscorrection.txt
  python scripts/subcode/subcode.py cdb105.bin -c "pack 1; error 9 15; decode"
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

# CDB105 table addresses, 64 bytes each.
ANTILOG_TABLE = 0x6294     # alpha^i for i = 0..63
LOG_TABLE = 0x62d4         # the log of each symbol, 63 for 0
DISTANCE_TABLE = 0x6314    # for c = alpha^d + alpha^-d, d from 1 to 23, and 0 for other c

SYMBOLS = 24
PAST = range(SYMBOLS, 63)
FOUR = (6, 9, 13, 17)
FAILURE = 0x80


class Failure(Exception):
    pass


class Field:
    """GF(64) with the field polynomial x^6 + x + 1 and alpha = x, built without the dump."""

    def __init__(self):
        self.exp, self.log = [], [0] * 64
        x = 1
        for i in range(63):
            self.exp.append(x)
            self.log[x] = i
            x <<= 1
            if x & 0x40:
                x ^= 0x43

    def pow(self, k):
        return self.exp[k % 63]

    def mul(self, a, b):
        return self.exp[(self.log[a] + self.log[b]) % 63] if a and b else 0

    def div(self, a, b):
        return self.exp[(self.log[a] - self.log[b]) % 63] if a else 0


GF = Field()


class Tables:
    """The dump's tables, and the multiply and divide the firmware builds from them."""

    def __init__(self, rom, shift):
        def take(address):
            return rom[address + shift:address + shift + 64]
        self.antilog, self.log, self.distance = (take(ANTILOG_TABLE), take(LOG_TABLE),
                                                 take(DISTANCE_TABLE))
        distance = [0] * 64
        for d in range(1, 24):
            distance[GF.pow(d) ^ GF.pow(63 - d)] = d
        if (list(self.antilog) != [GF.pow(i) for i in range(64)]
                or self.log[0] != 63 or any(self.log[GF.pow(i)] != i for i in range(63))
                or list(self.distance) != distance):
            raise Failure(f'no subcode tables at shift {shift:#x}')

    def mul(self, a, b):
        if not a or not b:
            return 0
        total = self.log[a] + self.log[b]
        return self.antilog[total - 63 if total >= 63 else total]

    def div(self, a, b):
        """a / b, or None for b = 0, where the firmware returns 0x80."""
        if not b:
            return None
        if not a:
            return 0
        difference = self.log[a] - self.log[b]
        return self.antilog[difference + 63 if difference < 0 else difference]


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


def solve(matrix, vector):
    """Solve matrix e = vector over GF(64) by elimination."""
    a = [row[:] for row in matrix]
    b = vector[:]
    n = len(b)
    for c in range(n):
        r = next(r for r in range(c, n) if a[r][c])
        a[r], a[c] = a[c], a[r]
        b[r], b[c] = b[c], b[r]
        inverse = GF.div(1, a[c][c])
        a[c] = [GF.mul(v, inverse) for v in a[c]]
        b[c] = GF.mul(b[c], inverse)
        for k in range(n):
            if k != c and a[k][c]:
                f = a[k][c]
                a[k] = [v ^ GF.mul(f, w) for v, w in zip(a[k], a[c])]
                b[k] ^= GF.mul(f, b[c])
    return b


def p_weight(k, symbol):
    return GF.pow(k * (23 - symbol))


def make_pack(n):
    """Symbol 0 = 09, an instruction, 16 data symbols from n, the Q parity in symbols 2 and 3 and
    the P parity in symbols 20..23."""
    u = n + 1000
    s = [0] * SYMBOLS
    s[0], s[1] = 0x09, (u * 11 + 6) & 63
    for i in range(4, 20):
        s[i] = (u * 7 + i * 13 + 1) & 63
    # Q: the sum of symbols 0..3 and the sum of symbol i times alpha^(3 - i) are 0.
    s[2], s[3] = solve([[1, 1], [GF.pow(1), 1]],
                       [s[0] ^ s[1], GF.mul(s[0], GF.pow(3)) ^ GF.mul(s[1], GF.pow(2))])
    # P: the sum of symbol i times alpha^(k(23 - i)) is 0 for k = 0..3.
    matrix = [[p_weight(k, 20 + j) for j in range(4)] for k in range(4)]
    vector = [0] * 4
    for k in range(4):
        for i in range(20):
            vector[k] ^= GF.mul(s[i], p_weight(k, i))
    s[20:24] = solve(matrix, vector)
    return s


def p_syndromes(pack):
    return [_sum(GF.mul(pack[i], p_weight(k, i)) for i in range(SYMBOLS)) for k in range(4)]


def _sum(values):
    total = 0
    for value in values:
        total ^= value
    return total


def virtual(errors):
    """P syndromes of errors (j, value) at locators alpha^j."""
    return [_sum(GF.mul(v, GF.pow(k * j)) for j, v in errors) for k in range(4)]


# The firmware's steps, from the dump's tables.

def firmware_syndromes(pack, t):
    """S0..S3: symbol 23 - j weighs alpha^(jk) in S_k."""
    s = [0] * 4
    for j in range(SYMBOLS):
        symbol = pack[23 - j]
        if symbol:
            for k in range(4):
                s[k] ^= t.mul(symbol, t.antilog[j * k % 63])
    return s


def firmware_p(s, t):
    """The firmware's P step on syndromes s. Returns the result, the corrections as (symbol,
    value) and the steps taken, as text."""
    s0, s1, s2, s3 = s
    d = t.mul(s0, s2) ^ t.mul(s1, s1)
    e = t.mul(s1, s2) ^ t.mul(s0, s3)
    f = t.mul(s1, s3) ^ t.mul(s2, s2)
    terms = f'D {d:02x}, E {e:02x}, F {f:02x}'
    if not d and not e and not f:
        if not s0 and not s3:
            return 0, [], f'{terms}, S0 and S3 0: nothing to correct'
        ratio = t.div(s1, s0)
        if ratio is None:
            return FAILURE, [], f'{terms}: one error, but S0 is 0'
        if not ratio:
            return FAILURE, [], f'{terms}: one error, but S1 is 0'
        j = t.log[ratio]
        if j >= SYMBOLS:
            return FAILURE, [], f'{terms}: one error at alpha^{j}, past the pack'
        return 1, [(23 - j, s0)], f'{terms}: one error at alpha^{j}'
    if not (d and e and f):
        return FAILURE, [], f'{terms}: some but not all of them 0'
    sigma1, sigma2 = t.div(e, d), t.div(f, d)
    c = t.mul(t.div(e, f), sigma1)
    distance = t.distance[c]
    notes = f'{terms}, sigma1 {sigma1:02x}, sigma2 {sigma2:02x}, c {c:02x}'
    if not distance:
        return FAILURE, [], f'{notes}: no distance for c'
    log_sigma2 = t.log[sigma2]
    l1 = (distance + log_sigma2) >> 1
    l2 = log_sigma2 - l1
    notes += (f', distance {distance}, log sigma2 {log_sigma2}: '
              f'({distance} + {log_sigma2}) / 2 = {l1}, {log_sigma2} - {l1} = {l2}')
    if not 0 <= l1 < SYMBOLS or not 0 <= l2 < SYMBOLS:
        return FAILURE, [], notes + ', not both in the pack'
    x1 = t.antilog[l1]
    e2 = t.div(t.mul(x1, s0) ^ s1, sigma1)
    return 2, [(23 - l2, e2), (23 - l1, e2 ^ s0)], notes + f': alpha^{l1} and alpha^{l2}'


def firmware_q(pack, t):
    """Q over symbols 0..3: S0 the sum, S1 by Horner's rule, times alpha a shift that adds 0x43
    on overflow."""
    s0 = s1 = 0
    for symbol in pack[:4]:
        s0 ^= symbol
        s1 <<= 1
        if s1 & 0x40:
            s1 ^= 0x43
        s1 ^= symbol
    if not s0 and not s1:
        return 0, None
    if not s0 or not s1:
        return FAILURE, None
    k = t.log[t.div(s1, s0)]
    if k > 3:
        return FAILURE, None
    return 1, (3 - k, s0)


# The textbook decoder, from the field alone.

def textbook_p(s):
    """Newton's identities, then a search for the roots of the locator polynomial over every
    locator of the field."""
    s0, s1, s2, s3 = s
    if not any(s):
        return 0, [], 'nothing to correct'
    d = GF.mul(s0, s2) ^ GF.mul(s1, s1)
    if not d:
        x = GF.div(s1, s0) if s0 else 0
        if not x or GF.mul(x, s1) != s2 or GF.mul(x, s2) != s3:
            return FAILURE, [], 'no single error fits the syndromes'
        j = GF.log[x]
        if j >= SYMBOLS:
            return FAILURE, [], f'one error at alpha^{j}, past the pack'
        return 1, [(23 - j, s0)], f'one error at alpha^{j}'
    sigma1 = GF.div(GF.mul(s1, s2) ^ GF.mul(s0, s3), d)
    sigma2 = GF.div(GF.mul(s1, s3) ^ GF.mul(s2, s2), d)
    roots = [j for j in range(63)
             if not GF.mul(GF.pow(j), GF.pow(j)) ^ GF.mul(sigma1, GF.pow(j)) ^ sigma2]
    if len(roots) != 2:
        return FAILURE, [], f'{len(roots)} roots found, two errors need 2'
    j1, j2 = roots
    where = f'alpha^{j1} and alpha^{j2}'
    if j1 >= SYMBOLS or j2 >= SYMBOLS:
        return FAILURE, [], f'roots {where}, not both in the pack'
    x1 = GF.pow(j1)
    e2 = GF.div(s1 ^ GF.mul(s0, x1), sigma1)
    return 2, [(23 - j2, e2), (23 - j1, e2 ^ s0)], f'roots {where}'


def corrections_text(changes):
    return ', '.join(f'symbol {symbol} ^ {value:02x}' for symbol, value in sorted(changes))


def is_codeword(pack):
    q = pack[0] ^ pack[1] ^ pack[2] ^ pack[3]
    q1 = _sum(GF.mul(pack[i], GF.pow(3 - i)) for i in range(4))
    return not any(p_syndromes(pack)) and not q and not q1


def hexadecimal(text, limit):
    try:
        value = int(text, 16)
    except ValueError:
        raise Failure(f'{text} is not hexadecimal') from None
    if not 0 <= value <= limit:
        raise Failure(f'{text} is out of range')
    return value


def number(text, low, high):
    if not text.isdigit() or not low <= int(text) <= high:
        raise Failure(f'{text} is not a number from {low} to {high}')
    return int(text)


class Session:
    def __init__(self, tables):
        self.tables = tables
        self.pack = None

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

    def show(self, label):
        print(f'{label:<10}' + ' '.join(f'{v:02x}' for v in self.pack))

    def loaded(self):
        if self.pack is None:
            raise Failure('make a pack first')
        return self.pack

    def command_pack(self, n='0'):
        self.pack = make_pack(number(n, 0, 10 ** 6))
        self.show(f'pack {n}')

    def command_error(self, symbol, value):
        pack = self.loaded()
        pack[number(symbol, 0, 23)] ^= hexadecimal(value, 0x3f)
        self.show('error')

    def command_past(self, j1, v1, j2=None, v2=None):
        pack = self.loaded()
        pairs = [(j1, v1)] + ([(j2, v2)] if j2 is not None else [])
        if j2 is not None and v2 is None:
            raise Failure('a second locator needs its value')
        errors = [(number(j, 0, 62), hexadecimal(v, 0x3f)) for j, v in pairs]
        if len({j for j, _ in errors}) != len(errors) or not all(v for _, v in errors):
            raise Failure('different locators and nonzero values')
        matrix = [[p_weight(k, i) for i in FOUR] for k in range(4)]
        values = solve(matrix, virtual(errors))
        if not all(values):
            raise Failure('these syndromes need fewer than four errors at symbols 6, 9, 13, 17')
        for i, value in zip(FOUR, values):
            pack[i] ^= value
        self.show('past')
        print(f'          errors ' + ', '.join(f'{v:02x} at symbol {i}' for i, v in
                                               zip(FOUR, values))
              + ', with the P syndromes of '
              + ' and '.join(f'{v:02x} at alpha^{j}' for j, v in errors))

    def command_decode(self):
        pack = self.loaded()
        t = self.tables
        s = firmware_syndromes(pack, t)
        print(f'decode    syndromes S0..S3 ' + ' '.join(f'{v:02x}' for v in s))
        result, changes, notes = firmware_p(s, t)
        print(f'  firmware P  {notes}')
        after = pack[:]
        for symbol, value in changes:
            after[symbol] ^= value
        text = f'result {result:02x}'
        if changes:
            text += ', ' + corrections_text(changes)
        print(f'              {text}')
        q, change = firmware_q(after, t)
        if change:
            after[change[0]] ^= change[1]
        print(f'  firmware Q  result {q:02x}'
              + (f', symbol {change[0]} ^ {change[1]:02x}' if change else ''))
        flagged = (result | q) & FAILURE
        print('              ' + ('bit 7 of symbol 0 set: the host sees the pack data error'
                                  if flagged else
                                  'no flag: the host gets the pack without the pack data error'))
        book, book_changes, book_notes = textbook_p(s)
        print(f'  textbook P  {book_notes}, result {book:02x}'
              + (', ' + corrections_text(book_changes) if book_changes else ''))
        if not flagged:
            print('  the pack afterwards is ' + ('a codeword' if is_codeword(after)
                                                 else 'not a codeword'))
        self.pack = after

    def command_pairs(self):
        t = self.tables
        inside = []
        for a in PAST:
            for b in PAST:
                if b >= a:
                    continue
                result, changes, _ = firmware_p(virtual([(a, 1), (b, 1)]), t)
                if result == 2:
                    inside.append((a, b, sorted(symbol for symbol, _ in changes)))
        total = len(PAST) * (len(PAST) - 1) // 2
        print(f'pairs     {total} pairs of locators past the pack, alpha^24..alpha^62')
        print(f'          {len(inside)} land inside it: the firmware changes the pack and '
              'returns 2')
        logs = [j for a, b, _ in inside for j in (a, b)]
        if not inside:
            return
        print(f'          their logs run from {min(logs)} to {max(logs)}, at most '
              f'{max(a - b for a, b, _ in inside)} apart')
        one = [(a, b, symbols) for a, b, symbols in inside if symbols[0] == symbols[1]]
        two = [(a, b, symbols) for a, b, symbols in inside if symbols[0] != symbols[1]]
        if two:
            a, b, symbols = two[0]
            print(f'          {len(two)} land on two symbols, such as alpha^{a} and alpha^{b} '
                  f'on symbols {symbols[0]} and {symbols[1]}')
        if one:
            a, b, symbols = one[0]
            print(f'          {len(one)} land both corrections on one symbol, which changes by '
                  f'S0, such as alpha^{a} and alpha^{b} on symbol {symbols[0]}')


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
        sys.exit(f'subcode.py: {error}')
    interactive = options.commands is None and options.script is None and sys.stdin.isatty()
    for count, line in enumerate(lines, 1):
        try:
            session.run(line)
        except (Failure, OSError) as error:
            message = f'line {count}: {error}' if options.commands is None else str(error)
            sys.stdout.flush()
            print(f'subcode.py: {message}', file=sys.stderr)
            if not interactive:
                sys.exit(1)


if __name__ == '__main__':
    main()
