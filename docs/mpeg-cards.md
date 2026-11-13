# MPEG cards

The MPEG card adds MPEG video and audio decoding to the Saturn, for Video CD and, on some cards,
Photo CD. It plugs into the MPEG card connector on the CD block's board. Sega, Hitachi and Victor
each sold versions of it. Every card holds a 512 KB ROM with two programs: encoded code for the CD
block's SH-1, and the Video CD player that the Saturn runs.

No ROM content is included. The tables give each known ROM's SHA-1 for identifying a dump.
[SH-1 code](mpeg-card/sh1-code.md) and the guides it lists follow the card's code for the CD block
by address.
[MPEG firmware revisions](mpeg-firmware-revisions.md) compares the two extension versions, their
shared code and the NTSC/PAL changes.

## Cards

Versions and dates come from each ROM's Saturn header. Areas use the Saturn area symbols: `J`
Japan, `T` Asia NTSC, `E` Europe.

| Card | Version | Date | Area | ROM | MAME set | SHA-1 |
| --- | --- | --- | --- | --- | --- | --- |
| Sega Saturn Movie Card HSS-0119, one dot on the back | 1.102 | 1995-05-25 | `J` `T` | MPR-17610A (PZD0) | `ssmovie` | `f7171b2a8f1c464696771941225c32d636b59349` |
| Sega Video CD Card MK-80310 | 1.105 | 1995-07-19 | `E` | MPR-17896 (PZD8) | `vcd` | `2f5ebd434f6d5b82e93d03e5626007bd5380f652` |
| Hitachi Video CD card, one dot on the front | 1.009 | 1995-05-29 | `J` | MPR-17773C (PZD1) | `hivcd1d` | `40f284e79f205728b72c7d7c0cf0bae0ade38f76` |
| Hitachi Video CD card, two dots on the front | 1.011 | 1995-11-02 | `J` | MPR-17773D (PZE7) or MPR-17773E | `hivcd2d` | `88aa35e48e655540e87ebeae10220413a8feee81` |
| Victor RG-VC1 Video CD Decoder | 1.002 | 1995-02-10 | `J` | PZA6 | `jvcvc1` | `eaac576b8b5e79e7df5e3efd70275b220ff70d78` |
| Victor RG-VC2 Twin Operator | 2.000 | 1995-10-06 | `J` | PZD9 | `jvcvc2a` | `567f82a31d5f93676120d699869b3ca64995e167` |
| Victor RG-VC2 Twin Operator | 2.001 | 1995-11-24 | `J` | PZE6 or PA26 | `jvcvc2` | `286f2c75b1a5bb9d7df23db9f0a381e61b1ac76c` |
| Victor RG-VC20 | 3.000 | 1996-08-22 | `J` `T` | PA32 | `jvcvc20` | `bb6459da484864226616c5d45b779d4b1644c527` |

- ROM names are Sega's part numbers with the ROM maker's ID in brackets. The Victor ROMs carry only
  the Hitachi ID.
- Where two ROMs are listed, both were dumped and hold the same data. They differ only in the part
  (see [boards](#boards)).
- The RG-VC1 header gives version 1.002. MAME lists the same ROM as v1.003.
- Victor card serials give the month of manufacture. RG-VC2 version 2.000 was found on a card made
  in November 1995. Version 2.001 was found on PZE6 in cards from January to November 1996, and on
  PA26 in cards made later. Sega and Hitachi cards carry no serial or date code.
- MAME also lists a Victor Twin Operator ROM, version 4.000 from 1997 (`jvcvc3`, SHA-1
  `2b070ecd1c10e9dd94454797395a57c6e53fd16c`). It is not described here.

Known versions without a public dump:

- HSS-0119 version 1.003 of 1995-02-14, on cards with no dot on the back. Its ROM is presumably
  MPR-17610.
- Hitachi versions before MPR-17773C. The C suffix implies earlier revisions, most likely on
  cards with no dot.
- The Asian Video CD card bundled with the MK-80229-07 Saturn. It has the same case labels as
  MK-80310 but a different ROM.

## Boards

The cards use three board designs. Every board carries the same two custom chips, the ROM and at
least one 512 KB DRAM.

| Board | Assembly | Cards | DRAM |
| --- | --- | --- | --- |
| 171-6814D PC BD MPEG | 837-10835 IC BD MPEG | HSS-0119, the one-dot and early two-dot Hitachi cards, RG-VC1, RG-VC2 | IC302 |
| 171-7184A PC BD MPEG VA | Not printed | Later two-dot Hitachi cards | IC302, with IC304 left empty |
| 171-7027B PC BD MPEG | 837-11697 IC BD MPEG | MK-80310, RG-VC20 | IC302 and IC304 |

| IC | Part | Package |
| --- | --- | --- |
| IC301 | Custom, Sega 315-5745 (Hitachi HD814101FE) | 144-pin QFP |
| IC302, IC304 | 256K x 16 DRAM: Hyundai HY514260B or Hitachi HM514260AJ7, HM514260CJ7 | 40-pin SOJ |
| IC303 | 512 KB mask ROM: Hitachi HN62444BNC or HN62454BNC, Toshiba on 171-7184A | 44-pin PLCC, 40-pin SOP for Toshiba |
| IC401 | Custom, Hitachi HD814102F | 100-pin QFP |

- The newer Hitachi HN62454BNC appears on RG-VC20 and on the PA26 RG-VC2 cards. The 171-7184A
  board takes the Toshiba ROM (Toshiba ID 5Y75-L786).
- The header's device field reads `MPEG4M` on every card except RG-VC20, which reads `MPEG8M`.
  Both 171-7027B cards carry two DRAMs, so MK-80310 has as much DRAM as RG-VC20 but reads `MPEG4M`.

## ROM layout

The ROM holds the CD block's code first and the Saturn's code after it.

| Offset | Size | Contents |
| --- | --- | --- |
| `0x00000` | 4 | Length of the encoded SH-1 code, big-endian. `0x00004ff8` on every known card |
| `0x00004` | `0x4ff8` | Encoded SH-1 code |
| `0x04ffc` | 4 | Zero on every known card |
| `0x05000` | 256 | Saturn header, starting with `SEGA SEGASATURN ` |
| `0x05100` | To the end | The Saturn's player software, padded with `0xff` |

- The first 20 KB is code for the CD block's SH-1. It handles half of the MPEG commands the Saturn
  sends to the CD block. James Laird-Wah (jhl) identified it.
- The CD-block firmware reads a big-endian length at the start of the card's address space,
  `0x0e000000`, accepts up to 20 KB and decodes what follows into the last 20 KB of its buffer RAM.
  `0x4ff8` is within that limit and a whole number of the decoder's 8-byte blocks.
- The SH-1 code of every card listed above decodes and passes the decoder's check, with the ROM's
  bytes in the order they are dumped. The SH-1 sees the ROM from offset 0.
- Seven of the eight card ROMs carry the same SH-1 code, version 1. MK-80310 carries version 2,
  which differs in a few places. Its encoded form differs in most bytes after the length word
  ([MPEG firmware revisions](mpeg-firmware-revisions.md)).
- The Saturn reads the ROM through the CD block. Command `E2`, Get MPEG ROM, copies it in
  2048-byte pages starting at offset `0x5000`, so the Saturn's view starts with the header
  ([Get MPEG ROM](cdblock/extensions.md#get-mpeg-rom)).
- The card connector carries address lines for 512 KB only, so the ROM repeats in the CD block's
  address space ([board](board.md#mpeg-card)). Reads past the end start over
  at offset 0, which puts the SH-1 code at the end of the Saturn's view, from `0x7b000`. A dump
  made through the Saturn has to be rotated back by 20 KB before its SHA-1 matches.

## Saturn header

Every card's header names the product `SEGAVIEWER` and carries peripheral code `J`. The maker ID
and the title tell the makers apart. The title's second 32-byte part holds the card's catalog
number. Offsets in this section count from the start of the header.

| Cards | Maker ID | Title | Catalog number |
| --- | --- | --- | --- |
| HSS-0119 | `SEGA ENTERPRISES` | `SEGASATURN VIDEO CD PLAYER` | `HSS-0119` |
| MK-80310 | `SEGA ENTERPRISES` | `SEGASATURN VIDEO CD PLAYER PAL` | `MK-80310` |
| Hitachi | `SEGA ENTERPRISES` | `PHOTO/VIDEO CD   PLAYER` | `T-17801C` |
| RG-VC1, RG-VC2 | `SEGA TP T-60` | `SEGASATURN VIDEO CD PLAYER` | `T-6001C` |
| RG-VC20 | `SEGA TP T-60` | `SEGASATURN VIDEO CD PLAYER` | `T-6002C` |

- Sega's Photo CD Operator boot disc (MK-81681, 1995) carries the same product number and
  peripheral code. It brings its own Photo CD player and its own build of the BIOS's disc
  identification, so a Saturn without a card can show Photo CDs.
- The RG-VC20 header is one byte short. The fields up to the area symbols are in place, and from
  the peripheral field on every field sits one byte early. The peripheral code is at `0x4f`, the
  title at `0x5f`, and the longwords from `0xe0` read shifted.
- The two Hitachi headers give `0x00200000` in the longword at `0xf0`. The other cards give 0. The
  BIOS loads the player's first part there whatever the field holds
  ([the BIOS and the card](#the-bios-and-the-card)).

## The card and the CD block

- The Saturn asks the CD block to check the card with command `E0`. The checks send the card a
  video sequence header and a few audio words through its data request lines, and write its 512 KB
  of memory and read it back ([card checks](cdblock/extensions.md#card-checks)).
- When the checks pass, the CD block's firmware loads and decodes the card's SH-1 code
  ([CD-block extension code](../README.md#extension-code)).
- The code's entry point fills the gaps in its command table from a table in the CD-block ROM. Of
  the 29 MPEG commands that go through that table, 16 then run card code and 13 run CD-block
  routines. `93`, `AE` and `AF` always run CD-block routines
  ([MPEG commands](mpeg-card/commands.md#routing)).
- `E2`, Get MPEG ROM, runs a CD-block routine that copies the rest of the card ROM into the sector
  buffer, where the Saturn gets it with command `61` like sectors read from a disc.
- The code looks for MPEG-1 system stream codes, and it reaches the CD-block firmware only through
  the fixed interface page of the CD-block ROM
  ([firmware interface](mpeg-card/sh1-code.md#firmware-interface)).

## The BIOS and the card

When the Saturn's CD player starts, the BIOS checks the card, loads the first part of the card's
player and lets it identify discs.

- Card check (BIOS `0x3174`): `E0` subcode 1, then `E1` subcode 1. The BIOS accepts the card when
  the low byte of CR2 is 2. The CD-block firmware leaves 2 there whenever the card checks pass, even
  when the load that follows fails ([MPEG card requests](cdblock/extensions.md#mpeg-card-requests)).
- Games run the same check through the vector at `0x06000274`, Sega's `SYS_CHKMPEG`, before they
  start the card with `93` ([command map](references.md#host-command-map)).
- Page reads (BIOS `0x31f4`): `E2` with filter 0, then `E1` subcode 1. The BIOS needs 3 in the high
  byte of CR2 and exactly the requested number of pages in partition 0 before it reads them.
- Pages 0 and 1, the header, go to `0x06002000`. The BIOS checks them like a disc's boot area: the
  `SEGA SEGASATURN ` mark, the size, the security code and the area symbols.
- Pages 2 and 3, card ROM `0x6000..0x6fff`, go to low work RAM at `0x00200000`.
- The BIOS calls `0x00200000` when the disc in the drive has a data track but its boot area did not
  pass, before its own Photo CD and Video CD tests. A nonzero return is the disc type. A disc that
  boots, an audio CD or an empty drive never reaches the call.
- The boot-area check returns -2, not a game, for a disc whose product number is `SEGAPLAYER`, so
  such a disc also goes to the card. The check runs only after
  [result 4](cdblock/disc-authentication.md#how-the-bios-uses-the-result). Which discs carry that
  product number is unknown.

## Sources

- Dumps, board details, ROM part numbers, manufacturing dates, undumped versions and the 20 KB
  rotation: zyrobs' notes that accompany each dump (2013 and 2014). MAME's list below quotes their
  note on the rotation. Every dump except RG-VC2 version 2.000 matched a second, independent dump.
- MAME software list `sat_vccart`, Sega Saturn VideoCD cartridges ([source][MAME-VCC], CC0-1.0).

[MAME-VCC]: https://github.com/mamedev/mame/blob/master/hash/sat_vccart.xml
