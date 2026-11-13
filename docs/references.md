# References

Outside sources for the CD-block firmware documentation, and the facts drawn from each.

Special thanks to the MAME team for their [SH-1 emulator][MAME-SH], which was used extensively for
this project.

## Host command map

The command number is the high byte of CR1. A command's name mirrors the function of Sega's CD
communication library that issues it ([ST-162-062094][ST162], table 8.1, printed pages 74-75). The
manual gives no command numbers. The library's version 1.20, shipped in SBL 6.01 and SGL 3.02j,
sends each command from the function named, and [Yabause `cs2.c`][YAB-CS2] (`Cs2Execute`) numbers
the commands the same way. The library has no function for group E. Those names are Yabause's,
except `E1`, named for what it returns. FAD in the names is Sega's frame address, a sector's
position on the disc.

| Command | Name | Sega function | Yabause name |
| --- | --- | --- | --- |
| `00` | Get CD Status | `CDC_GetCurStat` | Get Status |
| `01` | Get Hardware Info | `CDC_GetHwInfo` | Get Hardware Info |
| `02` | Get TOC | `CDC_TgetToc` | Get TOC |
| `03` | Get Session Info | `CDC_GetSes` | Get Session Info |
| `04` | Initialize CD Block | `CDC_CdInit` | Initialize CD System |
| `05` | Open Tray | `CDC_CdOpen` | Open Tray |
| `06` | End Data Transfer | `CDC_DataEnd` | End Data Transfer |
| `10` | CD Play | `CDC_CdPlay` | Play Disc |
| `11` | CD Seek | `CDC_CdSeek` | Seek Disc |
| `12` | CD Scan | `CDC_CdScan` | Scan Disc |
| `20` | Get Subcode | `CDC_TgetScdQch` (type 0), `CDC_TgetScdRwch` (type 1) | Get Subcode Q/RW |
| `30` | Set CD Device Connection | `CDC_CdSetCon` | Set CD Device Connection |
| `31` | Get CD Device Connection | `CDC_CdGetCon` | Get CD Device Connection |
| `32` | Get Last Buffer | `CDC_CdGetLastBuf` | Get Last Buffer Destination |
| `40` | Set Filter Range | `CDC_SetFiltRange` | Set Filter Range |
| `41` | Get Filter Range | `CDC_GetFiltRange` | Get Filter Range |
| `42` | Set Filter Subheader Condition | `CDC_SetFiltSubh` | Set Filter Subheader Conditions |
| `43` | Get Filter Subheader Condition | `CDC_GetFiltSubh` | Get Filter Subheader Conditions |
| `44` | Set Filter Mode | `CDC_SetFiltMode` | Set Filter Mode |
| `45` | Get Filter Mode | `CDC_GetFiltMode` | Get Filter Mode |
| `46` | Set Filter Connection | `CDC_SetFiltCon` | Set Filter Connection |
| `47` | Get Filter Connection | `CDC_GetFiltCon` | Get Filter Connection |
| `48` | Reset Selector | `CDC_ResetSelector` | Reset Selector |
| `50` | Get Buffer Size | `CDC_GetBufSiz` | Get Buffer Size |
| `51` | Get Sector Number | `CDC_GetSctNum` | Get Sector Number |
| `52` | Calculate Actual Size | `CDC_CalActSiz` | Calculate Actual Size |
| `53` | Get Actual Size | `CDC_GetActSiz` | Get Actual Size |
| `54` | Get Sector Info | `CDC_GetSctInfo` | Get Sector Info |
| `55` | Execute FAD Search | `CDC_ExeFadSearch` | Exec FAD Search |
| `56` | Get FAD Search Results | `CDC_GetFadSearch` | Get FAD Search Results |
| `60` | Set Sector Length | `CDC_SetSctLen` | Set Sector Length |
| `61` | Get Sector Data | `CDC_GetSctData` | Get Sector Data |
| `62` | Delete Sector Data | `CDC_DelSctData` | Delete Sector Data |
| `63` | Get and Delete Sector Data | `CDC_GetdelSctData` | Get Then Delete Sector Data |
| `64` | Put Sector Data | `CDC_PutSctData` | Put Sector Data |
| `65` | Copy Sector Data | `CDC_CopySctData` | Copy Sector Data |
| `66` | Move Sector Data | `CDC_MoveSctData` | Move Sector Data |
| `67` | Get Copy Error | `CDC_GetCopyErr` | Get Copy Error |
| `70` | Change Directory | `CDC_ChgDir` | Change Directory |
| `71` | Read Directory | `CDC_ReadDir` | Read Directory |
| `72` | Get File System Scope | `CDC_GetFileScope` | Get File System Scope |
| `73` | Get File Info | `CDC_TgetFileInfo` | Get File Info |
| `74` | Read File | `CDC_ReadFile` | Read File |
| `75` | Abort File | `CDC_AbortFile` | Abort File |
| `90` | Get MPEG Status | `CDC_MpGetCurStat` | MPEG Get Status |
| `91` | Get MPEG Interrupt | `CDC_MpGetInt` | MPEG Get Interrupt |
| `92` | Set MPEG Interrupt Mask | `CDC_MpSetIntMsk` | MPEG Set Interrupt Mask |
| `93` | Initialize MPEG | `CDC_MpInit` | MPEG Init |
| `94` | Set MPEG Mode | `CDC_MpSetMode` | MPEG Set Mode |
| `95` | MPEG Play | `CDC_MpPlay` | MPEG Play |
| `96` | Set Decoding Method | `CDC_MpSetDec` | MPEG Set Decoding Method |
| `97` | Send Decode Sync | `CDC_MpOutDsync` | None |
| `98` | Get MPEG Timecode | `CDC_MpGetTc` | None |
| `99` | Get MPEG Timestamp | `CDC_MpGetPts` | None |
| `9A` | Set MPEG Connection | `CDC_MpSetCon` | MPEG Set Connection |
| `9B` | Get MPEG Connection | `CDC_MpGetCon` | MPEG Get Connection |
| `9C` | Change MPEG Connection | `CDC_MpChgCon` | None |
| `9D` | Set MPEG Stream | `CDC_MpSetStm` | MPEG Set Stream |
| `9E` | Get MPEG Stream | `CDC_MpGetStm` | MPEG Get Stream |
| `9F` | Get Picture Size | `CDC_MpGetPictSiz` | None |
| `A0` | Display Picture | `CDC_MpDisp` | MPEG Display |
| `A1` | Set Window | `CDC_MpSetWinFpos` (type 0), `CDC_MpSetWinFrat` (type 1), `CDC_MpSetWinDpos` (type 2), `CDC_MpSetWinDsiz` (type 3), `CDC_MpSetWinDofs` (type 4) | MPEG Set Window |
| `A2` | Set Border Color | `CDC_MpSetBcolor` | MPEG Set Border Color |
| `A3` | Set Fade | `CDC_MpSetFade` | MPEG Set Fade |
| `A4` | Set Video Effects | `CDC_MpSetVeff` | MPEG Set Video Effects |
| `A5` | Get Image | `CDC_MpGetImg` | None |
| `A6` | Set Image Window | `CDC_MpSetImgPos` (type 0), `CDC_MpSetImgSiz` (type 1) | None |
| `A7` | Read Image | `CDC_MpReadImg` | None |
| `A8` | Write Image | `CDC_MpWriteImg` | None |
| `A9` | Read MPEG Sector | `CDC_MpReadSct` | None |
| `AA` | Write MPEG Sector | `CDC_MpWriteSct` | None |
| `AE` | Get Card Register Copy | `CDC_MpGetLsi` | None |
| `AF` | Card Register Access | `CDC_MpSetLsi` | MPEG Set LSI |
| `E0` | Authenticate Device | None | Authenticate Device |
| `E1` | Get Authentication Result | None | Is Device Authenticated |
| `E2` | Get MPEG ROM | None | Get MPEG ROM |

- The MPEG commands take their functions from Sega's MPEG part, table 8.1
  ([MPEG functions][SEGA-MPEG-FN]). `A7` to `AA` have only the card's handlers
  ([image and sector jobs](mpeg-card/commands.md#image-and-sector-jobs)). Only the commands whose
  handlers are documented are named. The MPEG part names no function for `AE` or `AF`. The CD
  communication library sends them from `CDC_MpGetLsi` and `CDC_MpSetLsi`. Both reach the card's
  registers by offset, and `AE` answers the firmware's copy
  ([the other ROM handlers](cdblock/host-commands.md#the-other-rom-handlers)).
- Games reach the MPEG card check, `E0` and then `E1`, both subcode 1, through the BIOS routine at
  `0x3174` ([the BIOS and the card](mpeg-cards.md#the-bios-and-the-card)). SBL's `SEGA_SYS.H`
  defines `SYS_CHKMPEG` as a call through its vector at `0x06000274`. Sega's
  [MPEG part][SEGA-MPEG], section 3.3, has games run it after `04` and an `01` that reports a card,
  and before `93`.
- `E1` returns a result from 0 to 4 for a disc and two status words for the MPEG card, not a yes or
  no ([group E](cdblock/host-commands.md#group-e)).
- The firmware checks `E2`'s filter, offset and count and runs expansion entry 86. The known
  cards leave that entry to a ROM routine that copies the card ROM into the sector buffer, which
  fits the Yabause name ([Get MPEG ROM](cdblock/extensions.md#get-mpeg-rom)).

In CDB105 the IRQ6 handler indexes a 16-entry table at `0x1fe0` with the command high nibble:

| Group | Handler | Group | Handler |
| --- | --- | --- | --- |
| 0 | `0x2020` | 8 | `0x2294` |
| 1 | `0x2050` | 9 | `0x2190` |
| 2 | `0x2074` | A | `0x2200` |
| 3 | `0x2090` | B | `0x2294` |
| 4 | `0x20b4` | C | `0x2294` |
| 5 | `0x20f4` | D | `0x2294` |
| 6 | `0x2128` | E | `0x2270` |
| 7 | `0x2160` | F | `0x2298` |

Group 0 accepts `00..06`, matching the first seven commands above. Group 3 accepts `30..32` through
a three-entry table at `0x20a8` ([host commands](cdblock/host-commands.md#commands-30-31-and-32)).
Groups 4 and 5 accept `40..48` and `50..56` through tables at `0x20d0` and `0x210c`
([buffer commands](cdblock/host-commands.md#buffer-commands)).
Groups 8, B, C and D share the reject path at `0x2294`. Group E accepts `E0..E2` through a
three-entry table at `0x2288` ([host commands](cdblock/host-commands.md#group-e)). Groups 9 and A
cover the MPEG command range `0x90..0xaf`
([host commands](cdblock/host-commands.md#groups-9-and-a)).

## Drive emulation

- [Yabause `cd_drive.c`][YAB-CDD] (copyright James Laird-Wah and Theo Berkau) emulates the optical
  drive at the level of the [link](cdblock/drive.md#link). Its frames hold 11 bytes, their inverted
  sum and a 13th byte of 0 (`set_checksum`).
- Its command switch names `00` nop, `02` seeking ring, `03` read toc, `04` stop disc, `06` read
  data sectors, `08` pause and `09` seek. The firmware stages these bytes as described under
  [commands](cdblock/drive.md#commands), and also sends `06` to play audio.
- Its drive status values are `04` ReadToc, `12` Stopped, `22` Seeking, `30` Unknown, `34`
  ReadingAudioData, `36` ReadingDataSectors, `46` Idle, `80` LidOpen, `83` NoDisc, and `b2` and `b6`
  (`SeekSecurityRing1` and `SeekSecurityRing2`). Its TOC read (`do_toc`) reports `04`, then `46`.
  `make_ring_status` answers a ring seek with status `b6`, word `44f1`, a frame address and report
  bytes `09 09 09 09`.
- The guides name drive commands and status codes by what the firmware does with them. Yabause's
  names remain only for status codes 1 (Stopped) and 2 (Seeking), which the firmware does not
  explain further. The ring report values are an emulation that the firmware accepts, not a
  measurement.
- [Yabause `cs2.c`][YAB-CS2] uses Sega's names for the host status codes and the interrupt bits
  ([Sega documentation](#sega-documentation)).

## Interface chip emulation

- [Ymir][YMIR] runs the SH-1 firmware on an emulated interface chip. Its notes list the SH-1's pin
  connections ([`sh1-pins.txt`][YMIR-PINS]), and [`ygr.hpp`][YMIR-YGR] names the register bits:
  `TRCTL` at `0x0a000002` (direction, FIFO reset, transfer enable), `CDIRQL` and `CDMSKL` at
  `0x0a000004` and `0x0a000008` (command written, response read), `CDIRQU` and `CDMSKU` at
  `0x0a000006` and `0x0a00000a` (bit 4 a sector header). It models a six-word transfer FIFO.
- [Yabause `ygr.c`][YAB-YGR] raises IRQ6 when the host writes CR4, and IRQ7 when an enabled flag at
  `0x0a000006` is set. It sends SH-1 accesses from `0x0a100000` on to the MPEG card.
- [libyaul][LIBYAUL-CDB] gives the Saturn-side addresses of the interface registers: the CD block at
  `0x25890000` in its [memory map][LIBYAUL-MAP], with the data transfer register at offset 0, HIRQ
  at 8 and CR1 to CR4 from `0x18` ([host commands](cdblock/host-commands.md#names)).
- These are emulator names, not firmware symbols. The guides name these registers by what the
  firmware does with them ([board](board.md)).

## Sega documentation

- [ST-162-062094, System Library User's Guide][ST162], Fig. 1.2 (printed page 22): host commands
  and responses use the command registers, and data transfer uses a separate transfer register.
  Both reach the CD-block program, which talks to the optical drive.
- Same manual, section 1.3 (printed page 23): transfers use software, SH-2 DMA or SCU DMA. The CD
  buffer holds 200 sectors, about 460 KB. Sections 5.0 and 5.1 (printed page 41) define the
  2352-byte stream unit and show host Get/Put and buffer copy/move in Fig. 5.1.
- Same manual, section 3.3 and data 4.0 (printed pages 31 and 59): the first response byte is the
  status. `ff` is REJECT, a command in the wrong format. Bit 7 is WAIT: the command cannot be
  executed now and is not accepted. Bit 6 is the data transfer request, bit 5 marks the periodic
  response, and bits 3..0 are the drive status: 0 BUSY, 1 PAUSE, 2 STANDBY, 3 PLAY, 4 SEEK, 5 SCAN,
  6 OPEN, 7 NODISC, 8 RETRY, 9 ERROR, 10 FATAL.
- Section 4.1 (printed page 33): drive commands (initialize, open tray, play, seek, pause, stop,
  scan) are answered with BUSY. Printed page 79: in NODISC a drive command opens the tray.
- Printed page 28: the host's interrupt factor register HIRQREQ. Bit 0 CMOK (a command can be
  issued), 1 DRDY (data transfer ready), 2 CSCT (a sector stored or discarded), 3 BFUL (buffer
  full), 4 PEND (play ended), 5 DCHG (disc change), 6 ESEL (selector setting or soft reset ended),
  7 EHST (host input or output ended), 8 ECPY (copy or move ended), 9 EFLS (file system operation
  ended), 10 SCDQ (subcode Q renewed). Sega's [MPEG part][SEGA-MPEG] adds bit 11 MPED (MPEG
  processing ended), 12 MPCM and 13 MPST. The host can write a bit only to 0, clearing it, not
  to 1.
- The values the firmware writes to `0x0a00001e` match these bits, each at the point Sega describes
  ([interrupt flags](cdblock/host-commands.md#interrupt-flags)). The firmware also sets EFLS when an
  `E0` disc request ends.
- Printed pages 78-79, `CDC_CdInit`: the parameters of `04`. Initialization flags: bit 0 resets the
  CD block software, bit 1 decodes R-W subcode, bit 2 skips the Mode 2 subheader check, bit 3
  retries Form 2 reads, bit 4 reads CD-ROM data at standard speed instead of double, bit 7 changes
  nothing. Standby time in seconds, 0 for 180 and `ffff` for no change. ECC (error correction code)
  count: 0 one pass, `01..05` up to that many more, `80` none, `ff` no change. Retry count: 0 no
  retry and stop, `01..0f` that many retries then stop, `40` no retry and output anyway, `41..4f`
  retries then output, `80` retry without limit, `ff` no change ([sector
  reads](cdblock/sector-reads.md#names)).
- Printed page 64, `CdcHw`: `01` returns the hardware flag (bit 1 MPEG card present, bit 7
  hardware error), the CD block version, the MPEG version, the CD drive information and the CD
  block revision ([commands `01` and `03`](cdblock/host-commands.md#commands-01-and-03)). Printed
  page 77: the TOC is 102 longwords, 204 words.
- Printed pages 87..91, section 8.2.5: a filter's frame range, subheader condition and mode. Mode
  bit 4 reverses the subheader condition, bit 6 selects the frame range and bit 7 initializes the
  filter: range, condition and mode 0. The connection flags select the true output (bit 0) and the
  false output (bit 1). Reset Selector's flags: bit 2 all partition data, 3 all partition output
  connectors, 4 all filter conditions, 5 all filter input connectors, 6 true outputs to the
  partition of the same number, 7 false outputs. Flags 0 clear one partition
  ([settings](cdblock/sector-buffer.md#settings)).
- Printed pages 92..94, section 8.2.6: 200 sectors and 24 partitions, and the free size, which can
  be 0 without the buffer being full since the system uses sectors. The actual data size is the
  words a get would send, by the get sector length, and disconnects the partition's output. The
  frame address search keeps the partition, the position and the frame of the sector with the
  greatest frame not above the key, from the given position on, and also disconnects the
  partition's output ([buffer information](cdblock/sector-buffer.md#buffer-information)).
- Printed pages 95..98, section 8.2.7: every buffer input and output function makes its own
  connections and disconnects the partition's output. Copy and move work between selectors. The
  copy and move error is normal, an error (a selector disconnected during the copy or move, or no
  space left in the buffer) or busy ([copy and move](cdblock/sector-buffer.md#copy-and-move)).
- Printed page 85, `CDC_TgetScdRwch`: 12 words, one pack of 24 bytes of R-W subcode, and a subcode
  flag with bit 0 pack data error and bit 1 overrun error. The command returns WAIT when no pack is
  buffered ([subcode](cdblock/subcode.md#the-host)).
- `200 * 2352 = 470400 = 0x72d80` bytes, less than the 512 KB physical buffer. In CDB105, raw
  sector slots start at `0x09000230` with a `0x930` stride. CDB105 lays out 202 slots,
  `0x09000230..0x0907420f`. Task 5's queue keeps two, so 200 hold sectors. The file system table at
  `0x09074210`, the disc extension area at `0x09075800` and the expansion area at `0x0907b000` lie
  above them.
- [CD-ROM system overview, section 3.6][SEGA-CD]: Fig. 3.28 shows the SH-1, buffer, CD interface,
  optional MPEG parts and the interface's connection to the SCU A-bus. Fig. 3.29 shows host Get/Put
  through the transfer register and a separate MPEG frame-buffer route.
- [Sega Saturn (PAL) Service Manual 013-1][SM], June 1995. Schematic Diagram-7, "SH-1 C.B"
  (printed pages 25-26), is the SH-1 board: the SH-1 `HD6437097`, the `YGR019A` interface, the
  `HM514260` buffer DRAM, the 20-pin drive connector and the MPEG card connector. Schematic
  Diagram-5 (printed page 21) takes `DEEM` to the audio DAC through R157, which the main board's
  parts list (printed page 76) marks not used. "SH1 board IC101" (printed pages 63-64) lists the
  SH-1's pins and their functions, the MPEG card's interrupt and data request inputs and `VCD`
  among them. The wiring is in [board](board.md).
- [ST-040-R4-051795, Disc Format Standards Specification Sheet][ST040], Figure 4.1 (printed page
  25): the system ID at the start of a disc holds the maker ID at `+0x10` (16 bytes), the product
  number at `+0x20` (10 bytes) and reserved fields at `+0xf8` and `+0xfc`. Printed page 26: Sega
  titles use maker ID `SEGA ENTERPRISES`, third parties `SEGA TP ` plus a company code, and
  reserved areas hold 00. The firmware's header ID is the first eight bytes of the maker ID
  ([disc authentication](cdblock/disc-authentication.md#a-header)).
- Command dispatch and bulk data transfer are separate mechanisms. The documented host write path
  moves data into the CD buffer. It is not documented as reaching other SH-1 RAM or starting code.
- [US 5,627,895][PAT] (Sega Enterprises, inventor Hidetaka Owaki, granted 1997): a CD-ROM carries
  a mark such as "SEGA" formed from sets of pit arrays and visible from the underside of the disc.
  A device reads specific tracks of the mark and compares them with stored base data. It may
  describe the scheme behind the firmware's
  [sector checks](cdblock/disc-authentication.md#sector-checks).

## CD subcode

- [US 5,502,696][PAT-RW] (Cirrus Logic, inventors Tony J. Yoon, Michael J. McGrath and Phuc Tran,
  granted 1996): 96 bytes of R-W subcode accompany each sector, as four packs of 24. In each pack
  bytes 1 and 18, 2 and 5, and 3 and 23 are swapped, and byte i of pack x is placed in pack
  x + (i mod 8). The firmware's ring and task 2 undo exactly this
  ([subcode](cdblock/subcode.md#the-ring)).

## Historical reports

- jhl (James Laird-Wah, also abrasive), 2014-06-30, [original dump report][JHL-1]: CDB105 was first
  dumped through hardware boot-mode manipulation. The MPEG-slot code loader was then used to dump a
  YGR022 unit.
- jhl, 2014-07-01, [firmware findings][JHL-4]: encrypted SH-1 code can load from an authenticated
  Saturn disc, using header fields `0xf8`/`0xfc`. jhl suggested development bug fixes as the
  purpose. The same source reports no designed command for direct SH-2-to-SH-1 code injection, and
  says most MPEG commands `0x90..0xaf` dispatch into card-loaded code, except `0x93`, `0xae` and
  `0xaf`.
- The same post reports that "both scrambled ring data (the logo) and the track wobble data from the
  CD mechanism are used for authentication".
- It also describes system discs, found by `SEGASYSTEM` in the disc header. An authenticated system
  disc enables a bypass for later discs. Its maker ID is stored, so "a system disc that has SEGA TP
  will only work with SEGA TP discs". A "super system disc" also bypasses the maker check. It needs
  exactly 30 tracks "and some weird subcode stuff in the TOC region". The firmware side is described
  under [trusted-ID shortcut](cdblock/disc-authentication.md#trusted-id-shortcut).
- Brilliant2meNu, 2010-09-01, [forum post][KD02] quoting what appear to be the operating
  instructions of Sega's System Disc KD02: once the system disc shows its maker ID, it is swapped
  for the development disc without turning the power off, and both work together until power-off.
  If the IDs do not match, the program does not run.
- [Micro Machines V3 developer recollections][MMV3]: Richard Applin says the team tried to use the
  SH-1 for rendering. Nick Pavis describes an unfinished, cancelled Saturn port. The method and
  outcome are not recorded.

## Prior community work

- [SegaXtreme: Saturn CD block ROM dumped again][SX-1] (2020-2026) collects dumps, dumping methods, a
  9600-bps serial monitor on CD-block test pads ([#28][SX-P28]), CPU-only SH-1 emulation
  ([#29][SX-P29]), board strap observations ([#41][SX-P41]) and the observation of cipher strings
  and bit operations in the ROM ([#60][SX-P60]).
- The same thread identifies YGR019A/B as the OCU and YGR022 as the integrated OCU, SH-1 and ROM
  ([#50][SX-P50]). OCU is the service manual's name for the interface chip, "IC CUSTOM CHIP OCU
  YGR019A" in its parts list ([service manual][SM], printed page 76). The thread has the SH-1 send
  its requests to the H8 microcontroller that drives the CD chipset ([#37][SX-P37]), and places the
  RF chip, the DSP and the servo microcontroller in the optical drive, apart from the CD block's
  SH-1 and YGR ([#38][SX-P38]).
- [srg320, partial CDB105 disassembly][SRG-CDB] for FPGA development ([#58][SX-P58]).
- [Rings of Saturn][RINGS] rebuilds a Saturn System Disc, which it says disabled the copy
  protection and booted burned games from any CD-R. For the ring it cites a 2008
  [redump.org thread][REDUMP]. After a featureless transition at roughly LBA 297,000..297,700, the
  ring lasts up to about LBA 328,300. Left scrambled, its sector data consists of `A8h` and `59h`
  bytes, and when interleaved these form the visible inscription, with `59h` as background and
  `A8h` as data.
- [Prototopia, Sophia development units][Sophia]: Nemesis reports a unit that boots games from a
  regular CD-R with "no security ring checking". The post gives its SH-1 as a socketed PROM
  `HD6477034F20` in place of the mask-ROM part. Posters there expect custom firmware on it but have
  not checked where the override sits, and some owners say their units run only retail discs.
- [CDB104 dump][CDB104], published by elcid in 2025.
- [MAME `satcdb`][MAME] catalogs the CDB105, CDB106 and YGR022 dumps. Its CD-block device does not
  run the SH-1.
- [Yabause][Yabause] contains an SH-1 interpreter (`SHMT_SH1` in `sh2int.c`).

[YAB-CS2]: https://github.com/Yabause/yabause/blob/master/yabause/src/cs2.c
[YAB-CDD]: https://github.com/Yabause/yabause/blob/master/yabause/src/cd_drive.c
[YAB-YGR]: https://github.com/Yabause/yabause/blob/master/yabause/src/ygr.c
[YMIR]: https://github.com/ymir-emu/Ymir
[LIBYAUL-CDB]: https://github.com/yaul-org/libyaul/blob/develop/libyaul/scu/bus/a/cs2/cd-block/cd-block-internal.h
[LIBYAUL-MAP]: https://github.com/yaul-org/libyaul/blob/develop/libyaul/scu/scu/map.h
[YMIR-PINS]: https://github.com/ymir-emu/Ymir/blob/main/docs/dev-notes/system-info/sh1-pins.txt
[YMIR-YGR]: https://github.com/ymir-emu/Ymir/blob/main/libs/ymir-core/include/ymir/hw/cdblock/ygr.hpp
[SM]: https://segaretro.org/images/4/4e/Sega_Service_Manual_-_Sega_Saturn_(PAL)_-_013-1_-_June_1995.pdf
[ST162]: https://antime.kapsi.fi/sega/files/ST-162-062094.pdf
[ST040]: https://antime.kapsi.fi/sega/files/ST-040-R4-051795.pdf
[PAT]: https://patents.google.com/patent/US5627895A/en
[PAT-RW]: https://patents.google.com/patent/US5502696A/en
[SEGA-CD]: https://www.infochunk.com/saturn/segahtml_en/hard/intr/hon/p03_60.htm
[SEGA-MPEG]: https://www.infochunk.com/saturn/segahtml_en/prgg/sysg/cdmp/hon/p03_10.htm
[SEGA-MPEG-FN]: https://www.infochunk.com/saturn/segahtml_en/prgg/sysg/cdmp/hon/p08_10.htm
[JHL-1]: https://assemblergames-archive.com/thread-45129.html
[JHL-4]: https://assemblergames-archive.com/printthread.php?page=4&tid=45129
[KD02]: https://assemblergames.org/viewtopic.php?t=41782&start=10
[MMV3]: https://sega-saturn.net/nr/micromachinesv3.php
[SX-1]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/
[SX-P28]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-178407
[SX-P29]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-178429
[SX-P37]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-178452
[SX-P38]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-178454
[SX-P41]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-178458
[SX-P50]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-180498
[SX-P58]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-180707
[SX-P60]: https://segaxtreme.net/threads/saturn-cd-block-rom-dumped-again.24610/post-183433
[SRG-CDB]: https://github.com/srg320/Saturn_hw/tree/main/CDB
[RINGS]: https://github.com/AlexIII/rings-of-saturn
[REDUMP]: http://forum.redump.org/topic/3367/sega-saturn-cp-talk/
[Sophia]: https://www.prototopia.net/threads/sophia-systems-segasaturn-programming-box-taisen-cable-hss-0107-system-link.304/
[CDB104]: https://segaxtreme.net/resources/cdb104.463/
[MAME]: https://github.com/mamedev/mame/blob/master/src/mame/sega/saturn_cdb.cpp
[MAME-SH]: https://github.com/mamedev/mame/tree/master/src/devices/cpu/sh
[Yabause]: https://github.com/Yabause/yabause
