# MPEG commands

## What it does

Most MPEG commands from the Saturn run through the card code's entry table. On the known cards 16
of them run card code and 13 run firmware routines.

- Routing. Commands `90..AF` go through entries 0 to 31. `93`, `AE` and `AF` run firmware
  routines without the table.
- A wait, then the ROM's handler. The card's `96`, `9A` and `A0` add a wait condition, then run the
  firmware's own handler.
- The card's versions. `94`, `97`, `98`, `9D`, `A1` and `A5` are versions of the firmware's
  handlers with other checks and a few other results.
- Image and sector jobs. `A7` to `AA`, which only the card has, check a copy's parameters and hand
  it to task 9.
- `AB`, `AC` and `AD` share one handler that answers `ffff`.

Card addresses are those of version 1 ([crosswalk](../mpeg-firmware-revisions.md#crosswalk)).
Firmware addresses are in CD-block revision CDB105 ([SH-1 code](sh1-code.md#overview)).

## Routing

Commands `90..AF` go through entries 0 to 31, the command minus `0x90`
([groups 9 and A](../cdblock/host-commands.md#groups-9-and-a)).

| Command | Entry | Runs | Address | ROM routine the card replaces |
| --- | --- | --- | --- | --- |
| `90` | 0 | ROM | `mpeg_command_90` (`0xaeda`) | |
| `91` | 1 | ROM | `mpeg_command_91` (`0xaeea`) | |
| `92` | 2 | ROM | `mpeg_command_92` (`0xaf1a`) | |
| `93` | | ROM, without the table | `mpeg_command_93` (`0xa050`) | |
| `94` | 4 | Card | `mpeg_command_94` (`0x0907c308`) | `mpeg_command_94` (`0xa5dc`) |
| `95` | 5 | ROM | `mpeg_command_95` (`0xa750`) | |
| `96` | 6 | Card | `mpeg_command_96` (`0x0907c880`) | `mpeg_command_96` (`0xa824`), which the card can jump to |
| `97` | 7 | Card | `mpeg_command_97` (`0x0907c4a8`) | `mpeg_command_97` (`0xa98c`) |
| `98` | 8 | Card | `mpeg_command_98` (`0x0907f464`) | `mpeg_command_98` (`0x9d44`) |
| `99` | 9 | ROM | `mpeg_command_99` (`0x9e5c`) | |
| `9A` | 10 | Card | `mpeg_command_9a` (`0x0907c89c`) | `mpeg_command_9a` (`0xaf64`), which the card calls |
| `9B` | 11 | ROM | `mpeg_command_9b` (`0xb3a8`) | |
| `9C` | 12 | ROM | `mpeg_command_9c` (`0xb528`) | |
| `9D` | 13 | Card | `mpeg_command_9d` (`0x0907fec4`) | `mpeg_command_9d` (`0xb2c4`) |
| `9E` | 14 | ROM | `mpeg_command_9e` (`0xb44c`) | |
| `9F` | 15 | ROM | `mpeg_command_9f` (`0x9e74`) | |
| `A0` | 16 | Card | `mpeg_command_a0` (`0x0907c7c4`) | `mpeg_command_a0` (`0xaa64`), which the card can jump to |
| `A1` | 17 | Card | `mpeg_command_a1` (`0x0907f5f0`) | `mpeg_command_a1` (`0x9ed8`) |
| `A2` | 18 | ROM | `mpeg_command_a2` (`0xb678`) | |
| `A3` | 19 | ROM | `mpeg_command_a3` (`0xb686`) | |
| `A4` | 20 | ROM | `mpeg_command_a4` (`0xb6d6`) | |
| `A5` | 21 | Card | `mpeg_command_a5` (`0x0907dab8`) | `mpeg_command_a5` (`0xb7ca`) |
| `A6` | 22 | ROM | `mpeg_command_a6` (`0xc43e`) | |
| `A7` | 23 | Card | `mpeg_command_a7` (`0x0907e57c`) | |
| `A8` | 24 | Card | `mpeg_command_a8` (`0x0907e5e4`) | |
| `A9` | 25 | Card | `mpeg_command_a9` (`0x0907ded4`) | |
| `AA` | 26 | Card | `mpeg_command_aa` (`0x0907df2a`) | |
| `AB`, `AC`, `AD` | 27, 28, 29 | Card | `mpeg_command_ab_ad` (`0x0907c5d0`) | |
| `AE` | | ROM, without the table | `mpeg_command_ae` (`0xa148`) | |
| `AF` | | ROM, without the table | `mpeg_command_af` (`0xa0f0`) | |

- The card's `96` and `A0` handlers jump to the ROM routine they replace after a check of their
  own, and its `9A` handler calls it. All three take the routine's address from the ROM table. The
  card's entry 42 does the same with ROM entry 42.
- The ROM routines the cards replace are described with the host commands
  ([the handlers the cards replace](../cdblock/host-commands.md#the-handlers-the-cards-replace)).
  The ROM has none for `A7..AD`.
- `AB`, `AC` and `AD` share one handler, which answers `ffff` in CR1 to CR4 and posts nothing.
- `90`, `91` and `92` run the ROM's handlers
  ([`90`, `91` and `92`](../cdblock/host-commands.md#90-91-and-92)), and so do the other commands
  marked ROM above ([the other ROM handlers](../cdblock/host-commands.md#the-other-rom-handlers)).
- The ROM's `9C` calls entry 88 and posts to task 8's offset 20, entry 64. On the known cards both
  entries are card code ([switching streams](video-and-audio.md#switching-streams)).
- The command handlers run inside the firmware's command interrupt, like the firmware's own
  handlers.

## The card's handlers

The card's handlers read the same parameters as the ROM's and answer through the same responses.
Three of them add a wait condition and then run the ROM's handler. The others are the card's own
versions, with different checks and a few different results. `A7` to `AA` have no ROM version.

| Command | Name | The card's handler |
| --- | --- | --- |
| `94` | Set MPEG Mode | Its own, with more wait conditions and one more card register |
| `96` | Set Decoding Method | Waits in recovery, then the ROM's |
| `97` | Send Decode Sync | Its own, with more wait conditions and a longer decode pulse |
| `98` | Get MPEG Timecode | Its own, checking the bank against the card's picture number |
| `9A` | Set MPEG Connection | Waits for the DMA channel ends too, then the ROM's |
| `9D` | Set MPEG Stream | Its own, leaving a part with no change alone |
| `A0` | Display Picture | Waits while task 8 takes an interval, then the ROM's |
| `A1` | Set Window | Its own, halving the frame buffer window position |
| `A5` | Get Image | Its own, also answering the window's width and height |
| `A7..AA` | Image and sector copies | Hand a job to task 9 ([image and sector jobs](#image-and-sector-jobs)) |

The ROM's versions are described with the host commands ([the handlers the cards
replace](../cdblock/host-commands.md#the-handlers-the-cards-replace)). Several of the card's wait
conditions use bit 1 of the decode flags `0x0f000891` ([MPEG
flags](../cdblock/host-commands.md#mpeg-flags)), which task 8's card events set while they take an
interval ([task 8's card events](../cdblock/extensions.md#task-8s-card-events)).

### `94`

- It waits while bit 1 of the decode flags or bit 1 or 2 of the register flags `0x0f000897` is
  set. The ROM waits for bit 1 of the register flags only.
- The sector buffer mode also writes `ffff` to the card register `0x0a100020`.
- Coming from a still picture mode, it writes `0x0f00086a` without bit 14 to `0x0a10001a` at once.
  The ROM waits while bit 2 of the register flags is set. The card writes the register again at the
  end when the new mode is a still picture mode.
- Leaving the sector buffer mode keeps the decoder modes entry 33 sets. The ROM writes back the
  modes from before, with bit 7 set.
- The scan mode also writes `0x0a10003e`: `dfff` for interlace, `ffff` otherwise.

### `96`

- In the video state 6, recovery, a pause or freeze other than `ffff` gives the wait response, as
  Sega documents. The ROM's handler goes on there
  ([`96`](../cdblock/host-commands.md#96-set-decoding-method)).
- Otherwise the ROM's handler runs.

### `97`

- It waits while bit 1 of the decode flags is set, and in the video state 6.
- In the movie mode with VSYNC timing it gives the wait response. The ROM's handler only answers.
- It runs the countdowns in the video states 1, 4 and 5, paused or not. The ROM runs them in the
  states 4 and 5 and not while paused.
- In a still picture mode it waits for bit 1 or 2 of the register flags, where the ROM waits for
  bit 1.
- The decode pulse on `0x0a100000` sets, clears and sets the decode bit, with a short delay after
  the first two writes. The ROM clears and sets it once.
- In a still picture mode with bit 0 of the decode flags set, the decode state stopped, it first
  writes the word `0x0f00086e` without bit 13 to `0x0a10001a`. That word is the one kept for
  `0x0a100020`. Entry 50's routine, which makes the same write before a decode pulse, takes
  `0x0f00086a`, the word kept for `0x0a10001a`.

### `98`

- In the movie mode it checks the record of the bank shown against the card's picture number, the
  low 6 bits of `0x0a100006`. When they differ, CR1's low byte gets bit 7 and CR2's low byte the
  card's number.
- While frozen with CR2's bit 0 clear, it answers what entry 37 kept, as the ROM does, but takes
  the bank from `0x0a100006` rather than from entry 37's copy.
- While frozen with CR2's bit 0 set, it looks for the card's picture number in the records of the
  other three banks. One match answers that bank, otherwise the bank is `80`.
- CR2's low byte is the whole low byte of the record or card word it comes from. The ROM's handler
  answers its low 6 bits.
- In a still picture mode it waits while bit 3 of the register flags is set and leaves r11 at the
  status byte over the current task record's low 24 bits, which the IRQ6 exit posts, as the ROM's
  `98` does. The card sets that bit only in task 8, so the message has class 0, and no task has a
  class 0 slot. The post fails, except with status 0 (BUSY): task 0's slot word is the reset
  vector's longword, so the message is written to the ROM at `0x428` ([bugs and
  oddities](../cdblock/bugs-and-oddities.md)).

### `9A`

- It waits while any of bits 1 to 3 of the card flags `0x0f000892` is set: a DMA channel 2 or 3 end
  not yet taken, or task 8's card events.
- Then the ROM's handler runs with its own checks, bit 3 and, for video, bit 6.
- For the next connections, the current video connection record, which `9B` returns, is written
  back afterwards when it was not 0 before. The ROM's handler clears its bit 6, the picture search
  with audio, when it sets next connections, and the card keeps it.

### `9D`

- A mode with bit 7 set, Sega's no change, leaves its part alone. The ROM stores the mode anyway.
- Every other mode has its stream number checked. The ROM checks it only for a mode with bit 0.
- It waits for a part in state 5, and for bits 1 and 2 of the card flags with the next streams too.
- It sets the new stream bits of the audio stream flags (`0x09075371`) and the video stream flags
  (`0x0907535c`) only for a part not in state 1.

### `A0`

- It waits while bit 1 of the decode flags is set, then the ROM's handler runs.

### `A1`

- The frame buffer window position, setting 0, is stored halved. The ROM stores it as given and
  doubles it outside high definition.
- The halved y takes bit 0 of the x as its bit 15.

### `A5`

- It ANDs the card register `0x0a100000` into `0x0f000852`, which each capture B sets to `ffff`. So
  bit 8 gives the wait response only while it was set in every read `A5` made since the last
  capture B.
- It answers the display window's width and height in CR3 and CR4. The ROM leaves the interface's
  address there.

## Image and sector jobs

`A7` to `AA` match Sega's image and sector functions. Each checks its parameters, keeps them and
hands the copy to task 9 as a card job.

| Command | Sega function | Parameters | Task 9 entry |
| --- | --- | --- | --- |
| `A7` | `CDC_MpReadImg`, the image window into buffer partitions | Three filters in CR1's low byte and CR2, the frame bank in CR3's high byte | 78 |
| `A8` | `CDC_MpWriteImg`, buffer partitions into the image window | Three buffer partitions in CR1's low byte and CR2, the frame bank and clear mode in CR3 | 77 |
| `A9` | `CDC_MpReadSct`, sectors of the MPEG sector buffer into a partition | The filter in CR1's low byte, the first MPEG sector in CR3, the count in CR4 | 80 |
| `AA` | `CDC_MpWriteSct`, sectors of a partition into the MPEG sector buffer | The partition in CR1's low byte, its first sector in CR2, the first MPEG sector in CR3, the count in CR4 | 79 |

- A job needs no other card job pending. Otherwise, or with a parameter out of range, the answer
  is the reject response.
- Filters and partitions are 0 to 23, frame banks 0 to 3.
- `A7` and `A8` need a still picture mode outside the sector buffer mode, as Sega documents. The
  bank's image window, as `A6` set it, must lie within 352 by 240, or 704 by 480 in high
  definition.
- `A9` and `AA` need the sector buffer mode. The MPEG sector buffer has 256 sectors, and the first
  MPEG sector plus the count may be at most 256.
- `AA` takes `ffff` as the partition's last sector and as a count that runs to the end. Other
  sector positions must be below 199.
- The job goes to task 9's card work loop through the job requests (`0x09075389`), bits 0 to 3 for
  `A7`, `A8`, `A9` and `AA` ([card work loop](../cdblock/extensions.md#card-work-loop)).
- The handler answers through the status response and returns `09810001` for the command
  interrupt to post, the same message the ROM's `9A` posts.
- `A7` and `A8` also clear bit 0 of TIER1, the interrupt enable of capture A on ITU1, channel 1 of
  the SH-1's integrated timer pulse unit (ITU). The card's video data request line drives that
  capture ([board](../board.md#mpeg-card)).
- Task 9 carries out the jobs one sector at a time in entries 78, 77, 80 and 79
  ([jobs](task-9.md#jobs)).
