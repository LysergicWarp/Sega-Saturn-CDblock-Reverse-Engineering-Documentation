# SH-1 code

## What it does

The MPEG card's ROM holds two programs. The Saturn runs the Video CD player, and the CD block's
SH-1 runs the code these guides describe. Once `93` turns the card on, that code handles about half
of the MPEG commands the Saturn sends.

- Loading. When the card checks pass, the firmware decodes the code from the card ROM into its own
  RAM and calls its entry point once.
- Entry table. The code lists its routines in a numbered table. Its entry point fills the gaps from
  a matching table in the CD-block ROM, so each number runs either card code or a firmware routine.
- MPEG commands. Most MPEG commands from the Saturn go through that table. On the known cards 16
  of them run card code and 13 run firmware routines.
- Video and audio. The card's own entries start the two transfers, mark the first and last
  pictures, keep the timestamps and switch each part to its next stream.
- Task 8. The card supplies the MPEG task's handlers for the card's status events and for the ends
  of the two transfers, which send each part's data to the card one sector at a time.
- Task 9. The card supplies task 9's card work: it prepares each new connection from its
  partition's sectors and carries out the image and sector jobs.
- Other callers. The card's interrupt lines call into the table as well.
- Firmware interface. The code reaches the firmware's routines only through a fixed page near the
  end of the CD-block ROM, and the kernel through its traps.
- Versions. Seven of the eight known card ROMs carry version 1. The European MK-80310 carries
  version 2, which differs in a few places and takes only PAL where version 1 takes only NTSC.

This page covers the load, the layout, the entry table and the firmware interface. The guides
below follow the rest of the code by address.

| Guide | Covers |
| --- | --- |
| [MPEG commands](commands.md) | Which commands run card code, the card's handlers and the image and sector jobs |
| [Video and audio](video-and-audio.md) | The video and audio parts' states: starting a transfer, pictures and timestamps, switching streams |
| [Task 8's handlers](task-8.md) | The card's events in task 8, picture starts and updates, intervals, the sector feeds of both parts, packet headers and changes |
| [Task 9's card work](task-9.md) | The preparations of new connections, the picture search, and the image and sector jobs in the card's memory |
| [Bugs and oddities](bugs-and-oddities.md) | Behavior in the card's code that looks unintended or surprising |

## Overview

The first 20 KB of each card ROM is encoded code for the CD block's SH-1
([ROM layout](../mpeg-cards.md#rom-layout)). This page covers the cards listed in
[MPEG cards](../mpeg-cards.md#cards). The CD-block firmware decodes it into its buffer RAM when
the [card checks](../cdblock/extensions.md#card-checks) pass, and once `93` turns the card on, the
code handles half of the MPEG commands. The firmware guides call it the card extension
([extensions](../cdblock/extensions.md#expansion-extension-loader)).

Card addresses are SH-1 addresses in the decoded code, which the firmware places at `0x0907b000`.
Firmware addresses are in CD-block revision CDB105 (SHA-1
`eb8393058f324e922c11b43709b64fc6ca94ab86`), whose ROM sits at address 0.

## Names

The card's code keeps its state in buffer RAM from `0x090752a0`. The card guides use these names
for the state that comes up in more than one place.

| Name | Address | Contents |
| --- | --- | --- |
| First video timestamp | `0x090752ac` over `0x090752a0` | 33 bits, a byte over a longword |
| Second video timestamp | `0x090752ae` over `0x090752a8` | Moved on by one picture's duration at each picture update |
| Audio timestamp | `0x090752ad` over `0x090752a4` | The longword is what `99` answers |
| Timestamp distance | `0x090752b0`, `0x090752af` | The longword is the distance between the audio and second video timestamps. The byte is 1 when the audio's is the greater |
| Buffer size | `0x090752e0` | Word, the stream's first STD (system target decoder) buffer size in 2048-byte units. 20 from activation |
| Picture record | `0x09075314` | Longword, the new picture's GOP count over word 6 |
| Feed positions | `0x09075324` (video), `0x09075326` (audio) | Word, each feed's position in its partition |
| Feed partitions | `0x0907532b` (video), `0x0907532f` (audio) | Byte, the partition each feed reads |
| Next connections | `0x0907534c` | Bit 1 a next video connection prepared, bit 3 a next audio one. Bit 5 the next video connection waiting, bit 7 the next audio one. Bit 6 the audio waiting for the video's first picture |
| Cut requests | `0x0907534d` | The cuts `9A` asks for: bit 0 current video, bit 1 next video, bit 2 current audio, bit 3 next audio |
| Update flags | `0x09075351` | Bit 2 a correction marked. Bits 4 and 5 count picture updates modulo 4 |
| Video stream flags | `0x0907535c` | Bit 0 the stream's end, bit 1 a move to the next connection, bit 2 a position kept after a recovery, bit 3 new current streams from `9D` |
| Audio feed flags | `0x09075370` | Bits 4 and 5 an odd first and last byte, bit 6 the audio held in a synchronized pause, bit 7 the stream's end. Bits 0, 1 and 3 hold the same for the next connection |
| Audio stream flags | `0x09075371` | Bit 0 a move to the next connection, bit 1 entry 57 to run before the next transfer, set by `9D` for new current streams and after a held pause, bit 2 a synchronized pause that held the audio, bit 7 set by `9A` for a new current connection |
| Video change step | `0x09075378` | The step of a video change `9C` asked for |
| Audio change | `0x09075379` | 1 while a change or a stream's end waits for the next connection, 2 while a change waits for the next DMA end |
| Preparation requests | `0x09075388` | One bit for each new connection, set by `9A` |
| Job requests | `0x09075389` | Bits 0 to 3 for `A7`, `A8`, `A9` and `AA` |
| Correction pair | `0x090753fd` | Version 1 only. Keeps a correction's two writes together |

## Decoding

The code decodes with the CD block's [payload decoder](../cdblock/decoder.md)
as the expansion loader runs it: the length from ROM offset 0, the encoded data from offset 4.

| Cards | SHA-1 of the first 20 KB | Decoded SHA-1 | Version |
| --- | --- | --- | --- |
| HSS-0119, Hitachi, RG-VC1, RG-VC2, RG-VC20 | `02a9dccd531b659106155a87d9bbee5cdd0d5d21` | `74beb5ab13c72279f99fa82cbf5905c1b162b607` | 1 |
| MK-80310 | `9e5939f185b3776230b3d3a46e70ef67f944b1ed` | `b9bd40dea50a5ed00abed5c9cab5bcab6026293b` | 2 |

- The length `0x4ff8` gives 2558 blocks of code, `0x4ff0` bytes, and the check value at ROM offset
  `0x4ff4`. Both versions pass the check with the ROM's bytes in the order they are dumped.
- The two versions differ in only a few places ([version 2](#version-2)).

## Layout

| Address | Contents |
| --- | --- |
| `card_version` (`0x0907b000`) | Version, 1 or 2. The loader copies it to the MPEG version that command `01` returns |
| `card_version_copy` (`0x0907b001`) | The same value. The loader compares it with byte `+0x45` of a disc extension |
| `0x0907b002` | Two zero bytes |
| `card_entry_pointer` (`0x0907b004`) | Entry point, `card_entry_point` (`0x0907b170`) |
| `card_entry_table` (`0x0907b008`) | Entry table: entries 0 to 88, one longword each |
| `card_entry_table_end` (`0x0907b16c`) | Zero |
| `card_entry_point` (`0x0907b170`) | Code, padded with zeros up to `0x0907ffef` |

## The entry table

The firmware reaches the card's code by entry number n through the entry table. The card's entry
point only fills the table's gaps from the firmware's own ROM table, then returns.

- The loader calls the entry point once, right after the load.
- The ROM table at `rom_table` (`0xf938`) holds firmware routines under the same entry numbers
  ([ROM table](../cdblock/extensions.md#rom-table)).
- The entry point compares the byte at `rom_table_version` (`0xf934`) with the card's version.
  When the byte is greater, every nonzero ROM entry replaces the card's. Otherwise each empty card
  entry takes the ROM's.
- The byte is 0 in every known CD-block revision, so the card's own entries always stay.
- Afterwards 86 of the 89 entries are set. 36 come from the card alone, 18 are card entries that
  replace a ROM routine and 32 come from the ROM alone. Both versions set the same entries.
- Entries 3, 30 and 31 stay empty. They belong to commands `93`, `AE` and `AF`, which the firmware
  runs without the table.

## Other entries

Entries 0 to 31 serve the MPEG commands `90..AF` ([MPEG commands](commands.md#routing)). Entries
32 to 88 are reached through the stubs at `0xf80a + 4 * (n - 32)`.

| Caller | Entries | On the known cards |
| --- | --- | --- |
| Task 8's message handlers at offsets 0, 8, 12, 16 and 20 ([MPEG task](../cdblock/structure.md#mpeg-task)) | 32, 51, 72, 35, 64 | Entry 32 is the ROM's `task8_message_wait` (`0xa022`), task 8's own wait. The others are card code ([task 8's handlers](task-8.md)) |
| Task 8's card activation ([card activation](../cdblock/extensions.md#card-activation)) | 34, then 33 | Entry 34 is the ROM's `mpeg_state_activate` (`0xa4f0`), which sets the card bit and calls entry 33, card code |
| Task 9's card work loop ([card work loop](../cdblock/extensions.md#card-work-loop)) | 53, 54, 69, 70, 77, 78, 79, 80 | Card code ([task 9's card work](task-9.md)) |
| `E2` | 86 | The ROM's [Get MPEG ROM](../cdblock/extensions.md#get-mpeg-rom), with its helpers in 81 to 84 and 87 |
| `9C` ([Change MPEG Connection](../cdblock/host-commands.md#9c-change-mpeg-connection)) | 88 | Card code, replacing the ROM's `mpeg_command_9c_apply` (`0xb5d2`) |
| Entry 88 | 58, 59, 60 | 58 and 60 are card code. 59 is the ROM's `mpeg_audio_channel_stop` (`0xb994`) |
| The card's interrupt lines ([card interrupts](../cdblock/extensions.md#card-interrupts)) | 56 and 57 for line A, 38, 39 and 40 for line B, 37 from 40 | 56, 57 and 38 to 40 are the ROM's. 37 is card code |

- ROM routines in the firmware's MPEG code call further entries through the stubs. ROM entry 35
  `task8_card_events` (`0xab78`), which the card replaces, calls entries 43 to 49, 73 to 75 and 85,
  which only the card supplies, and 36, 41 and 42, which the card replaces too.
- Entry 61, the ROM's `mpeg_decode_pulse` (`0xb9b2`), has no caller in the ROM. The card leaves it
  to the ROM table.
- The card's code calls many entries through the stubs as well, its own and the ROM's.
- ROM entries 66, 67 and 68 build an MPEG command's response, adding MPEG status from
  `0x0f000840..0x0f000847`, the decode flags `0x0f000891` ([MPEG
  flags](../cdblock/host-commands.md#mpeg-flags)) and `0x0f00089c`. 66 answers with status `ff`, the
  reject status, and 67 and 68 go through the wait and status responses (services 90 and 89).

The card's entries 33, 35, 36, 37, 41, 42, 58, 60 and 88 are versions of the ROM's with small
differences.

- Entry 33 keeps `fffe` for `0x0a10001a` and `d7af` for `0x0a100020`, where the ROM's keeps `ff7e`
  and `47af` ([card activation](../cdblock/extensions.md#card-activation)). Version 2 keeps `ffb6`
  for `0x0a10001a` ([revisions](../mpeg-firmware-revisions.md#version-2)).
- Entry 33 also writes `dfff` to `0x0a10003e` and clears `0x090753ec..0x090753ff`.
- Entry 33 starts the pause and freeze fields of the pause flags `0x0f000893` at paused and frozen,
  as the decoder modes it sets say. The ROM's entry 33 leaves them at 0.
- Entry 36 pairs the bytes of its timestamp comparison the other way round from the ROM's
  ([task 8's card events](../cdblock/extensions.md#task-8s-card-events)). Its pairs are the
  video and audio [timestamps](video-and-audio.md#pictures-and-timestamps) as the card's code
  keeps them.
- Entry 37 takes the frame bank shown from bits 6 and 7 of `0x0a100006` and keeps that bank's
  records. The ROM's looks the register's low 6 bits up among the four banks' records.
- Entry 58 also calls entry 60 when bit 3 of the play flags `0x0f000890` is set. It leaves the
  picture record (`0x09075314`), which the ROM's clears. Its literal pool still holds that address,
  and no instruction loads it.
- Entry 60 toggles bit 1 of the play flags as the ROM's does.
- Entry 88 cuts a part as the ROM's does, and also acts on a change
  ([switching streams](video-and-audio.md#switching-streams)).
- Entry 41 clears the decode bit at the end of video recovery only in the movie mode
  ([recovery](../cdblock/extensions.md#recovery)).
- Entry 42 runs the ROM's entry 42 first. When the audio partition holds 1 to 3 sectors, fewer than
  the ROM's 4, it ends the recovery itself. It needs 2 sectors while bit 6 of the play flags is set.
- The card's entry 35 also runs the countdowns for a stopped video, state 1, at an interval in the
  movie mode with VSYNC timing ([countdowns](../cdblock/extensions.md#countdowns)), and a step for
  the transfer state. It keeps the synchronized pause in bit 7 of the pause flags, where the
  ROM's keeps it in bit 7 of the play flags ([card events](task-8.md#card-events)).

## Firmware interface

The card's code reaches the firmware only through the fixed interface page at `0xf800..0xfacb`
([expansion entries](../cdblock/extensions.md#expansion-entries)). No firmware
code address appears in it.

- Firmware services through the stubs for entries 89 to 97: the status response (89), connections
  (91, 92) and the partition and slot routines (93, 94, 96, 97). It does not call 90 or 95 itself.
- RAM addresses from ROM table entries 98 to 100: the first sector slot, the partition records and
  the free pool's count.
- ROM table entries 6, 10, 16 and 42, read directly, and the byte at `rom_table_version` (`0xf934`).
- Kernel services: it takes and releases the sector lock (`TRAPA 0x2a` and `0x27`) as owner 8 or 9,
  and posts messages (`TRAPA 0x21`). It has no mailbox wait of its own. Four of its paths end by
  jumping to task 8's wait through entry 32.

It uses this hardware and memory:

- MPEG card registers from `0x0a100000` and `0x0a180000`
  ([board](../board.md#mpeg-card)).
- The interface chip's host interrupt flags at `0x0a00001e` and its register `0x0a00000c`.
- SH7034 peripheral registers from `0x05ffff00`.
- State in on-chip RAM `0x0f000842..0x0f00089d` and in buffer RAM from `0x090752a0` to
  `0x09075400`, mostly inside the areas task 8 clears at startup.
- It never reads the card ROM at `0x0e000000`.

## MPEG streams

The code looks for MPEG-1 system stream codes. It compares longwords with the start codes
`0x000001ba` (pack), `0x000001bb` (system header) and `0x000001b9` (end), and with the stream IDs
`0x000001c0..0x000001df` (audio) and `0x000001e0..0x000001ef` (video).

## Version 2

MK-80310 carries a PAL variant of version 1. It changes entry 47's thresholds and flag handling,
command `94`'s video-mode check, entry 33's value for the card register `0x0a10001a` and the
version bytes. Code after entry 47 sits `0x28` bytes lower. The
[revision comparison](../mpeg-firmware-revisions.md#version-2) gives the changes and their effects,
and the [crosswalk](../mpeg-firmware-revisions.md#crosswalk) maps the card guides' addresses to
version 2.
