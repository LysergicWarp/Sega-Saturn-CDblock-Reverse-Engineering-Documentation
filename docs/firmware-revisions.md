# Firmware revisions

Four revisions of the CD-block firmware are known. CDB104 is the baseline here, and each later
revision is described by its changes from the one before: the instructions and data that differ,
then what the change does. The other guides use CDB105 addresses, and the [crosswalk](#crosswalk)
maps them to the later revisions.

[`revision.py`](../scripts/revision/revision.py) names the revision of your dump and shows its
version number, checksum and unused space, the differences this page describes. It also maps
addresses from the guides to the dump's revision, and back with `-r`. From the repository's top
folder, with your dumps there as `cdb105.bin` and `cdb106.bin`:

```
python scripts/revision/revision.py cdb105.bin
python scripts/revision/revision.py cdb106.bin 28b0 9274 07fe
python scripts/revision/revision.py cdb106.bin -r 28c0
```

## Changes in brief

The firmware changes little across the four revisions: an audio fix in CDB105, a second drive type
in CDB106 and no code change in YGR022. Each code change also raises the version number that
command `01` reports. Sega published no change notes, so the purposes given here are inferred from
what the code does.

CDB105 no longer clears the de-emphasis output in the lead-in
([details](#pre-emphasis-output-in-the-lead-in)).

- Audio tracks can be mastered with pre-emphasis, a treble boost that the player undoes while they
  play. The firmware sets the board's de-emphasis output from the current track's flag.
- In the lead-in, before track 1, the drive reports track 0, whose flag describes no audio. CDB104
  turns the output off there, CDB105 leaves it as it was until a numbered track is reported.
- The likely aim is to keep the filter from switching off and on when a play or read passes
  through the lead-in, as one near the start of track 1 can. Only discs with pre-emphasized audio
  are affected, and only where the output reaches the DAC ([audio](board.md#audio)).

CDB106 lets one board take either drive type ([details](#drive-strap)).

- The earliest Saturns use a drive with a 20-pin cable, later ones a 21-pin cable
  ([drive generations](board.md#drive-generations)). CDB106 boards normally take the 21-pin drive.
  Those fitted with the 20-pin drive tie SH-1 pin PC0 high ([SegaXtreme #41][SX-P41]).
- CDB106 reads that pin at reset and, when it is high, sets two bits in the interface chip's
  decoder control register. What the bits do is unknown. They likely set the chip up for the older
  drive.
- The new instructions move the code after them by 16 to 18 bytes, which accounts for every other
  difference from CDB105.

YGR022 carries CDB106's firmware on a single chip ([details](#ygr022)).

- The chip combines the interface chip, the SH-1 and the ROM. Its ROM differs from CDB106's only in
  512 bytes of unused space, which are zeros instead of `ff`.
- No code points into those bytes, and startup does not act on the checksum they change, so they
  have no effect. Whether they come from chip production or from the dump is unknown.

## Revisions

Every revision is 65,536 bytes. The CDB105, CDB106 and YGR022 hashes also appear in
[MAME's `satcdb` definitions][MAME]. The CDB104 dump was published by elcid in 2025
([resource][CDB104]).

| Revision | Identity | SHA-1 | Changes from the previous revision |
| --- | --- | --- | --- |
| CDB104 | CD block 1.04 | `fb0993246ed0ad27ca086854295eccd412196254` | Baseline |
| CDB105 | CD block 1.05 | `eb8393058f324e922c11b43709b64fc6ca94ab86` | Pre-emphasis output kept in the lead-in, version 1 |
| CDB106 | CD block 1.06 | `b3c20fbe57cd2eb595e9edac86817e5948dccae4` | Drive strap read at reset, version 2 |
| YGR022 | YGR022 / 315-5962 | `f4f6c2aac68c352814d396ae41f81f54ad228e68` | 512 zero bytes in unused space |

- Big-endian reset vectors at `0x0000` and `0x0008` give PC `0x00000428`, and the stack values at
  `0x0004` and `0x000c` are `0x0f001000`, in every revision.
- Every revision carries the quoted Hitachi 1993 copyright string from `0x0400`, with `Copyright`
  at `0x0401`.
- Command `01` (Get Hardware Info) answers a version number in the low byte of CR2: 0 in CDB104, 1
  in CDB105, 2 in CDB106 and YGR022 ([version number](#version-number)).

## ROM layout

Every revision ends the same way: code and data, unused `ff` bytes, the interface page
`0xf800..0xfacb` and unused `ff` bytes to the end
([expansion entries](cdblock/extensions.md#expansion-entries)).

| Revision | Code and data | Unused | Interface page | Unused |
| --- | --- | --- | --- | --- |
| CDB104, CDB105 | `0x0000..0xc4ab` | `0xc4ac..0xf7ff`, 13,140 bytes | `0xf800..0xfacb` | `0xfacc..0xffff`, 1,332 bytes |
| CDB106, YGR022 | `0x0000..0xc4bb` | `0xc4bc..0xf7ff`, 13,124 bytes | `0xf800..0xfacb` | `0xfacc..0xffff`, 1,332 bytes |

- The page stays at `0xf800` while the code before it moves in CDB106. Its stubs
  `0xf800..0xf937` are identical in all four revisions.
- The ROM table's 59 code entries follow the routines they name. Its other 42 entries, zeros and
  RAM addresses, are equal.

## Checksum

The 32-bit sum of every aligned big-endian longword, modulo `2^32`, is zero for CDB104, CDB105 and
CDB106.

- The longword at `0x0424`, just before the reset entry, is the compensation field. Each revision
  changes it to keep the sum at zero.
- Startup computes the sum at `0x06f0` and stores it at `0x0f000004`, but normal startup does not
  act on it.
- YGR022 sums to `0x80` ([YGR022](#ygr022)).

## CDB104

CDB104 (MD5 `deac6b0785647f53aa09f1e2e07a450a`) is the earliest known revision. It already has
everything the later revisions build on: both extension loaders, the decoder, disc authentication
and the interface page.

- The extension mechanism is the same in every known revision. CDB104's two loaders and its
  decoder are byte for byte those of CDB105.
- The last reset check, at `0x08ec`, returns 0 in every revision, so the caller never sets bit 0
  of the hardware flag `0x0f00027d` ([reset and startup](cdblock/structure.md#reset-and-startup)).
- The literal `0x05ffffd0` follows that check at `0x08f4`. It is PCDR, the Port C data register,
  and no CDB104 or CDB105 instruction loads it. The check likely read Port C in an earlier build.
  CDB106 reads PCDR through this literal ([drive strap](#drive-strap)).

## CDB105

CDB105 differs from CDB104 in four bytes: one branch target, the version number, and the
compensation longword to match.

| Address | CDB104 | CDB105 | Change |
| --- | --- | --- | --- |
| `0x0424` | `e2e19bac` | `e2e09ba6` | Checksum compensation longword |
| `0x2902` | `8907`, `bt 0x2914` | `890d`, `bt 0x2920` | [Pre-emphasis output in the lead-in](#pre-emphasis-output-in-the-lead-in) |
| `0x9290` | `0000` | `0001` | [Version number](#version-number) |

### Pre-emphasis output in the lead-in

After each drive report, the periodic status at `0x28b0` sets PB6 (bit 6 of `0x05ffffc3`) from
the pre-emphasis bit of the current track during play and reads
([periodic status](cdblock/drive.md#periodic-status)). The branch at `0x2902` handles reports from
the lead-in, where the track byte is 0.

- `cmp/eq #0,r0` at `0x2900` tests the track byte `0x0f0002d2`, and `bt` at `0x2902` takes track 0.
- CDB104 branches to `0x2914`, which clears PB6.
- CDB105 branches to `0x2920`, past the PB6 update. PB6 keeps its value until a report from a
  numbered track.
- The change applies in drive states 6 and 12, playing and reading, with status bit 2 set. Other
  drive states clear PB6 in both revisions.
- Effect: passing through the lead-in during play or a read no longer turns the pre-emphasis output
  off. Once a numbered track is reported, both revisions set PB6 the same way.
- PB6 is the de-emphasis output `DEMP` ([board](board.md#audio)).

### Version number

`01` at `0x9274` loads the literal at `0x9290` with `mov.w` at `0x927c` and ORs it into CR2 below
the hardware flag ([commands `01` and `03`](cdblock/host-commands.md#commands-01-and-03)). It is the
CD block version of Sega's hardware information, and it rises
from 0 to 1 in CDB105 and to 2 in CDB106, so the host can tell which revision answers.

## CDB106

CDB106 reads a board strap at reset and sets two interface bits on boards with the 20-pin drive.
The new code moves everything after it, so a same-offset comparison with CDB105 finds 44,097
differing bytes. Aligned, the differences are these:

| CDB105 address | CDB105 | CDB106 | Change |
| --- | --- | --- | --- |
| `0x0424` | `e2e09ba6` | `a7f196f8` | Checksum compensation longword |
| `0x07fc..0x07ff` | 2 instructions | 11 instructions at `0x07fc..0x0811` | [Drive strap](#drive-strap) |
| `0x08ca` | `0009` | Removed | Padding before a literal pool |
| `0x9290` | `0001` | `0002` at `0x92a0` | [Version number](#version-number) |

Every other difference is an address that moved ([moved code](#moved-code)).

### Drive strap

The interface setup at `0x07e0` clears the interface registers at reset. CDB105 writes 0 to
`0x0a00001a`. CDB106 first reads PC0, bit 0 of PCDR
([SH7034 notes](sh7034.md#port-b-and-port-c)):

| CDB106 address | Instructions | Effect |
| --- | --- | --- |
| `0x07fc` | `mov.l`, `mov.w @r1,r0` | Read PCDR through the literal at `0x0904` |
| `0x0800` | `mov.l` | r1 = `0x0a000000` from `0x08dc` |
| `0x0802` | `tst #1,r0`, `bf 0x080c` | PC0 high goes to `0x080c` |
| `0x0806` | `mov #0,r0`, `bra 0x0810` | PC0 low: r0 = 0 |
| `0x080c` | `mov #17,r0`, `shll8 r0` | PC0 high: r0 = `0x1100` |
| `0x0810` | `mov.w r0,@(26,r1)` | r0 to `0x0a00001a` |

- PC0 low: the register gets 0, as in CDB105. PC0 high: it gets `0x1100`, bits 8 and 12.
- The other documented writes to `0x0a00001a` change only bits 0..2, 4, 6 and 7
  ([sector reads](cdblock/sector-reads.md), [periodic status](cdblock/drive.md#periodic-status)),
  so bits 8 and 12 stay as set until the next reset.
- On a CDB106 machine with a 20-pin drive, pin 87 of the SH-1 (PC0) is tied to +5 V instead of
  ground. CDB106 boards normally use 21-pin drives ([SegaXtreme #41][SX-P41]). PC0 is therefore
  high only with the 20-pin drive. Otherwise it is tied to ground with the rest of Port C
  ([board](board.md#test-pads-and-other-pins)).
- What bits 8 and 12 do in the interface chip is unknown. The change likely sets the interface up
  for the 20-pin drive, so that one firmware serves CDB106 boards with either drive.

### Moved code

The 18 new bytes and the dropped padding word move the rest of the code.

- CDB105 `0x0800..0x08c9` moves by `0x12`.
- From the literal pool at CDB105 `0x08cc` to the end of the code, the move is `0x10`. The code
  ends at `0xc4bb`.
- Every address that points across the move is adjusted: literal pool pointers, jump table
  entries, branch and PC-relative displacements, and the ROM table's code entries.
- No other instruction, RAM address or constant differs.

## YGR022

YGR022 combines the interface, the SH-1 and the ROM in one chip. Its firmware is CDB106 with the
512 bytes at `0xd0f8..0xd2f7` set to `00` instead of `ff`.

- The range lies in the unused space after the code, and no literal in the ROM points into it.
- The compensation longword is CDB106's, so the sum is `0x80`: 128 longwords of `ffffffff` became
  zero. The zeros were not part of the image when its compensation longword was computed.
- Whether they come from chip production or from the dump is unknown.

## Crosswalk

CDB104 uses CDB105 addresses. For CDB106 and YGR022 (`revision.py` maps any address both ways):

| CDB104 / CDB105 | CDB106 / YGR022 | Offset |
| --- | --- | --- |
| `0x0000..0x07fb` | `0x0000..0x07fb` | Same |
| `0x07fc..0x07ff` | `0x07fc..0x0811` | [Drive strap](#drive-strap) |
| `0x0800..0x08c9` | `0x0812..0x08db` | `+0x12` |
| `0x08cc..0xc4ab` | `0x08dc..0xc4bb` | `+0x10` |
| `0xf800..0xfacb` | `0xf800..0xfacb` | Same |

| Landmark | CDB104 / CDB105 | CDB106 / YGR022 |
| --- | --- | --- |
| Interface setup | `0x07e0` | `0x07e0` |
| Runtime initialization | `0x08f8` | `0x0908` |
| Disc and expansion loaders | `0x19ec..0x1b7b` | `0x19fc..0x1b8b` |
| Begin complete-payload processing | `0x1a88` | `0x1a98` |
| Load extension VBR value | `0x1abc` | `0x1acc` |
| Call disc extension entry | `0x1ac6` | `0x1ad6` |
| Expansion loader | `0x1b06` | `0x1b16` |
| `CDBLOCK` text | `0x1f39` | `0x1f49` |
| Periodic status | `0x28b0` | `0x28c0` |
| Disc-header parser | `0x86ee..0x883b` | `0x86fe..0x884b` |
| Copy header `0xf8`/`0xfc` fields | `0x87b0` | `0x87c0` |
| `SEGA SEGASATURN ` text | `0x8a2c` | `0x8a3c` |
| `SEGASYSTEM` text | `0x8cf4` | `0x8d04` |
| `01` handler | `0x9274` | `0x9284` |
| Decoder | `0x9904` | `0x9914` |
| `Hitachi.PublicKeyCipher.` text | `0x99e4` | `0x99f4` |
| Interface page stubs | `0xf800` | `0xf800` |
| ROM table | `0xf938` | `0xf938` |

[MAME]: https://github.com/mamedev/mame/blob/master/src/mame/sega/saturn_cdb.cpp
[CDB104]: https://segaxtreme.net/resources/cdb104.463/
[SX-P41]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-178458
