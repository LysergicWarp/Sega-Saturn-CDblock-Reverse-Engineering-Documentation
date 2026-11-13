# MPEG firmware revisions

The eight card ROMs listed in [MPEG cards](mpeg-cards.md#cards) carry two versions of the SH-1
extension. Seven carry identical code. The European MK-80310 carries a PAL variant of the same
implementation, with changes in the version bytes, one routine, one command branch and one data
word. Version 1 is the baseline here. The [SH-1 code guides](mpeg-card/sh1-code.md) use its
addresses, and the [crosswalk](#crosswalk) maps them to version 2.

These versions belong to the SH-1 extension. They are separate from the Saturn player versions
in each card's header. The comparison covers the extension only.

## Revisions

Both versions occupy the first 20,480 bytes of the card ROM and decode to 20,464 bytes at
`0x0907b000`. Both pass the [payload decoder's check](cdblock/decoder.md).

| Revision | Cards | Decoded SHA-1 | Changes from version 1 |
| --- | --- | --- | --- |
| Version 1 | HSS-0119, both Hitachi ROMs, RG-VC1, both RG-VC2 ROMs, RG-VC20 | `74beb5ab13c72279f99fa82cbf5905c1b162b607` | Baseline, NTSC |
| Version 2 | MK-80310 | `b9bd40dea50a5ed00abed5c9cab5bcab6026293b` | Version bytes, PAL mode check, four thresholds, flag handling removed, one data word |

| Revision | SHA-1 of the first 20 KB, before decoding |
| --- | --- |
| Version 1 | `02a9dccd531b659106155a87d9bbee5cdd0d5d21` |
| Version 2 | `9e5939f185b3776230b3d3a46e70ef67f944b1ed` |

- The encoded length at ROM offset 0 is `0x4ff8` in both versions. The encoded data starts at
  offset 4, its check value at `0x4ff4`, and the final four bytes are zero.
- Both decoded headers point to entry `0x0907b170` and supply the same 54 nonzero entries in
  the 89-entry table. The loader entry merges this table with the CD-block firmware's table
  ([entry table](mpeg-card/sh1-code.md#the-entry-table)).

## Decoded layout

Version 2's entry 47 routine is 40 bytes shorter. Everything after it moves down by `0x28`,
and the final zero padding grows by 40 bytes. The total decoded size stays the same.

| Contents | Version 1 | Version 2 |
| --- | --- | --- |
| Header and entry table | `0x0907b000..0x0907b16f` | Same addresses |
| Code before entry 47 | `0x0907b170..0x0907bdc5` | Same addresses |
| Entry 47, including its literal pool | `0x0907bdc6..0x0907bf6d` | `0x0907bdc6..0x0907bf45` |
| Remaining code and data | `0x0907bf6e..0x0907ffe3` | `0x0907bf46..0x0907ffbb` |
| Zero padding | `0x0907ffe4..0x0907ffef`, 12 bytes | `0x0907ffbc..0x0907ffef`, 52 bytes |

## Version 1

Version 1 is shared byte for byte across the seven listed NTSC card ROMs, despite their
different makers, player versions and board designs. It already has the command handlers,
stream parsing and firmware interface used by version 2.

- The card supplies 16 of the 29 MPEG commands routed through the extension table in both
  versions ([MPEG commands](mpeg-card/commands.md#routing)).
- Both use the same CD-block services, card register windows and RAM state
  ([firmware interface](mpeg-card/sh1-code.md#firmware-interface)).

## Version 2

With the `0x28` shift after entry 47 taken out and relocated addresses counted as matching, 20,024
of the 20,464 decoded bytes match, about 97.85%, even counting all of entry 47 and the final padding
as different. Entry 47 keeps most of its instruction flow.

The changes are these. Addresses in the first column belong to version 1.

| Version 1 address | Version 1 | Version 2 | Change |
| --- | --- | --- | --- |
| `0x0907b000..0x0907b001` | `01 01` | `02 02` | [Version bytes](#version-bytes) |
| `0x0907bdc6..0x0907bf6d` | Entry 47 and literals, 424 bytes | 384 bytes at `0x0907bdc6..0x0907bf45` | [Thresholds and flag handling](#thresholds-and-flag-handling) |
| `0x0907c2ea` | `fffe`, -2 | `ffb6`, -74 at `0x0907c2c2` | The word entry 33 keeps for the card register `0x0a10001a` and writes there ([other entries](mpeg-card/sh1-code.md#other-entries)) |
| `0x0907c316` | `bt` | `bf` at `0x0907c2ee` | [Video mode](#video-mode) |

Every other difference is a relocated address or the extra zero padding.

### Version bytes

The loader copies byte `0x0907b000` to the MPEG version returned by command `01`. It compares
byte `0x0907b001` with byte `+0x45` of a disc extension. Both bytes rise from 1 to 2
([extension layout](mpeg-card/sh1-code.md#layout)).

### Thresholds and flag handling

Entry 47 begins at `0x0907bdc6` in both versions. The card's entry 35 calls it through stub
`0xf846`, from `0x0907c650` in version 1 and `0x0907c628` in version 2. CDB105's own entry 35
makes the same call from `0xabd0`, but the known cards replace that entry
([card events](cdblock/extensions.md#task-8s-card-events)).

| Version 1 literal | Version 1 value | Version 2 literal | Version 2 value |
| --- | --- | --- | --- |
| `0x0907bf60` | 525 | `0x0907bf38` | 3000 |
| `0x0907bf62` | 1008 | `0x0907bf3a` | 1500 |
| `0x0907bf64` | 437 | `0x0907bf3c` | 625 |
| `0x0907bf66` | 875 | `0x0907bf3e` | 1250 |

Version 1 also tests and writes the flag byte at `0x090753fd`. Version 2 removes that handling,
shortening the routine by 40 bytes. Its literal pool moves down by the same amount, and the
loads and branches adjust to the new addresses.

In version 1 the four values are limits for a count of pictures in an interlaced scan: 525 at 29.97
pictures per second, 1008 at 23.976, and 437 and 875 at 25. When the count reaches its limit the
card writes `fffb` to `0x0a100018` twice, and the flag byte keeps the two writes together
([picture updates](mpeg-card/task-8.md#picture-updates)). What the writes do on the card is not
known, nor what version 2's values count.

### Video mode

Command `94`, Set MPEG Mode, takes the scan mode in CR3's high byte. When bit 7 is clear,
version 1 rejects a mode with bit 1 set, while version 2 rejects one with bit 1 clear.
Both reject through entry 66.

Bit 1 is the PAL selector in Sega's `CDC_MpSetMode`. The branch reversal therefore makes
version 1 accept only NTSC and version 2 accept only PAL on this path. The MK-80310 Saturn
header also names a PAL player ([Saturn header](mpeg-cards.md#saturn-header)).
The CD-block ROM's own `94` handler rejects PAL as version 1 does.

## Crosswalk

All addresses are in the decoded SH-1 extension.

| Version 1 | Version 2 | Offset |
| --- | --- | --- |
| `0x0907b000..0x0907bdc5` | `0x0907b000..0x0907bdc5` | Same |
| `0x0907bdc6..0x0907bf6d` | `0x0907bdc6..0x0907bf45` | Changed routine and literal pool |
| `0x0907bf6e..0x0907ffe3` | `0x0907bf46..0x0907ffbb` | `-0x28` |

| Landmark | Version 1 | Version 2 |
| --- | --- | --- |
| Loader entry | `0x0907b170` | `0x0907b170` |
| Entry 47 | `0x0907bdc6` | `0x0907bdc6` |
| Entry 48 | `0x0907bf6e` | `0x0907bf46` |
| Command `94` | `0x0907c308` | `0x0907c2e0` |
| Command `A0` | `0x0907c7c4` | `0x0907c79c` |
| Command `9A` | `0x0907c89c` | `0x0907c874` |
| Command `9D` | `0x0907fec4` | `0x0907fe9c` |
