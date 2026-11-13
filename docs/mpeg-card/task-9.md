# Task 9's card work

## What it does

Task 9 runs the card's code for the connections `9A` registers and for the image and sector jobs
that `A7` to `AA` hand to it.

- Preparations. For each new connection the card looks at the partition's sectors one at a time
  until it finds the stream's first packet, and keeps that packet's data for the transfer.
- Picture search. With Sega's picture search the video starts at a sequence header instead, and
  the first video timestamp moves on by the pictures left out.
- Audio with the search. The search can drop audio sectors older than the video and prepare the
  audio part with it.
- Image jobs. `A7` and `A8` copy a frame bank's image window, a picture's Y, Cr and Cb, between
  the card's memory and buffer partitions.
- Sector jobs. `A9` and `AA` copy sectors between the card's memory, used as Sega's MPEG sector
  buffer, and buffer partitions.
- One sector at a time. Each call moves at most one sector and returns to task 9's loop, which
  runs again while work is left.

Card addresses are those of version 1 ([crosswalk](../mpeg-firmware-revisions.md#crosswalk)).

## Overview

Task 9's card work loop calls the card's entries for the bits of two bytes
([card work loop](../cdblock/extensions.md#card-work-loop)).

| Byte | Bit | Set by | Entry |
| --- | --- | --- | --- |
| Preparation requests (`0x09075388`) | 0 | `9A`, a new video connection | 54, `mpeg_video_prepare` (`0x0907e908`) |
| | 1 | `9A`, a new next video connection | 53, `mpeg_video_next_prepare` (`0x0907f1f4`) |
| | 2 | `9A`, a new audio connection | 69, `mpeg_audio_prepare` (`0x0907f7c2`) |
| | 3 | `9A`, a new next audio connection | 70, `mpeg_audio_next_prepare` (`0x0907fba0`) |
| Job requests (`0x09075389`) | 0 | `A7` | 78, `mpeg_image_read_job` (`0x0907dfb4`) |
| | 1 | `A8` | 77, `mpeg_image_write_job` (`0x0907e206`) |
| | 2 | `A9` | 80, `mpeg_sector_read_job` (`0x0907dc10`) |
| | 3 | `AA` | 79, `mpeg_sector_write_job` (`0x0907dd68`) |

- The loop calls the entries for the preparation requests in the order 54, 53, 69 and 70. It then
  jumps to the job of the lowest bit of the job requests, whose pass ends at entry 76, the loop's
  recheck.
- An entry clears its bit when it is done. Until then task 9 runs the loop again, so a preparation
  or a job that waits for sectors keeps task 9 busy. Sega documents that the jobs do not end while
  the buffer is full or a partition is empty.
- A cut that `9A` asks for through bits 0 to 3 of the cut requests (`0x0907534d`) ends a
  preparation at its next call. A current connection's part goes to the state 1, and a next
  connection is dropped.
- The entries take the sector lock as task 9 (`0x0b090000`) around each buffer service.

## Preparations

A preparation looks at the sector at its part's position each time it runs. It skips sectors until
one holds the stream's first packet, keeps that packet's data for the transfer and clears its bit.

| | Video, 54 | Next video, 53 | Audio, 69 | Next audio, 70 |
| --- | --- | --- | --- | --- |
| Connection and stream records | `0x09075328`, `0x09075338` | `0x09075330`, `0x09075340` | `0x0907532c`, `0x0907533c` | `0x09075334`, `0x09075344` |
| Position | Feed position (`0x09075324`) | `0x09075348` | Feed position (`0x09075326`) | `0x0907534a` |
| Kept data | `0x090752c0`, `0x090752d8` | `0x090752c4`, `0x090752da` | `0x090752c8`, `0x090752dc`, `0x090752d0` | `0x090752cc`, `0x090752de`, `0x090752d4` |
| Timestamp | First video timestamp (`0x090752ac` over `0x090752a0`) | `0x090752b8` over `0x090752b4` | Audio timestamp (`0x090752ad` over `0x090752a4`) | `0x090752b9` over `0x090752bc` |
| When done | Video state 3 | Bit 1 of the next connections (`0x0907534c`) | Audio state 3 | Bit 3 of the next connections (`0x0907534c`) |

- The kept data is the DMA channel's source, its length in words and, for audio, its destination.
  Entry 74 or 73 starts the transfer from it
  ([starting a transfer](video-and-audio.md#starting-a-transfer)), and a switch takes the next
  connection's ([switching streams](video-and-audio.md#switching-streams)).
- A next connection's prepared bit in the next connections byte waits for entry 75, which marks
  the connection ready for a switch ([intervals](task-8.md#intervals)).
- A skipped sector moves the position on by 1, or with Sega's delete mode, bit 2 of the connection
  mode, is released.
- Sectors are read as the feeds read them ([sector feeds](task-8.md#sector-feeds)). Data without a
  pack counts whole. In a system stream the packet at +36, after the pack header, is read with
  entry 52 ([packet headers](task-8.md#packet-headers)).
- A packet of another stream type flags the part's stream data error: VSERR or ASERR for a current
  connection, Sega's VNERR or ANERR (next stream data error) for a next one.
- Entries 54 and 69 pair their decoder's device end, `0x8d` or `0x8c`, with the partition's end
  whenever the partition holds sectors. Entries 53 and 70 do not.

### The video

Entry 54 prepares a new video connection.

- The first video packet with a PTS, a presentation time stamp, starts the stream, and its PTS is
  the first video timestamp. With Sega's IGPTS, bit 3 of the connection mode, the first video
  packet does.
- Data without a pack, in mode 0, mode 1 or mode 2, starts the stream at once.
- The first STD (system target decoder) buffer size, in 2048-byte units, is kept as the buffer
  size (`0x090752e0`), the count of sectors entry 74 waits for with an automatic transfer. Data
  without a pack sets 28.
- A packet's data is kept from its start rounded down to even, as entry 51 sends it.
- The stream's end in the first sector, an EOR bit with bit 0 of the mode or the system end code at
  +2344 with bit 1, sets bit 0 of the video stream flags (`0x0907535c`) for entry 51.
- The byte `0x0907535d` holds the progress. A new stream record from `9D` starts it over.

### The picture search

With Sega's picture search, bit 7 of the layer byte `0x0907532a`, the video starts at a sequence
header after the first PTS. Entry 55, `mpeg_start_code_find` (`0x0907f190`), finds each start code
`000001` in the packets' data.

- A sequence header before any picture starts the stream there, with the PTS as the timestamp.
- From the first picture on, the search counts pictures in `0x090753fa`. Until a picture whose
  header's first 16 bits, the temporal reference first, are above the first picture's, the
  pictures after it do not count.
- A sequence header then starts the stream, or a GOP (group of pictures) header once more than 64
  pictures are counted.
- The first video timestamp grows by the count times one picture's duration in 90 kHz units: by
  the sequence header's picture rate code, 3754 for 1 and 2, 3600 for 3 and 3003 otherwise, or at
  a GOP header by the rate bits of `0x0f00086a`.
- More than 240 pictures give up. The sector is skipped and the search starts again at the next
  PTS.
- A start code can span two packets. The search keeps the last 2 bytes of a packet without one, or
  the last 8 when one ends within them, and writes them just before the next packet's data, over
  the end of its packet header.
- The stream starts at the start code, in whole words: an odd start takes the byte before it,
  zeroed, and an odd length takes one byte more.
- Sectors before the start are skipped, so they never reach the decoder.

### With audio

Sega's `CDC_MPSRCH_AV`, bits 6 and 7 of the layer byte, lets the picture search discard audio data
to match. Entry 54 then prepares the audio as well. The ROM's `9A` keeps bit 6 only when it sets
both current connections at once in the system layer, and then leaves entry 69's bit clear.

- Each skipped video sector drops the audio sector at the audio position when that sector is
  older, by the sector header's address at +12 to +14.
- With the buffer full and no video sector at the position, an audio sector goes to make room.
- Once the video's start is found, entry 71, `mpeg_audio_prepare_with_video` (`0x0907f7b4`), runs
  entry 69's steps on the audio part and returns to entry 54 through the address kept at
  `0x0907537c`.
- An audio packet with a PTS starts the audio with its own timestamp. One without takes the
  video's.
- Both parts then go to the state 3 together, the audio after entry 57's pulse of bit 14 of
  `0x0a180008`.
- Without an audio sector the video waits. With the buffer full its sector goes and the search
  goes on. A sector that is not an audio packet is dropped.
- The audio stream's end in the video's first sector, with bit 0 or 1 of the audio connection
  mode, sets bit 7 of the audio feed flags (`0x09075370`) for entry 72.

### The next video

Entry 53 prepares a next video connection as entry 54 does, without the picture search.

- The first video packet with a PTS, or data without a pack, is kept for the switch.
- It takes no STD buffer size, IGPTS or stream end.

### The audio

Entries 69 and 70 prepare a new audio and a new next audio connection.

- The first audio packet with a PTS is kept, and a packet without one is skipped.
- The PTS less 783 is the audio timestamp, as entry 72 takes it
  ([audio data](task-8.md#audio-data)).
- An odd first byte is kept to go alone to `0x0a180002`, as in entry 72, and an odd length leaves
  the last byte for it. Entry 69 marks them in bits 4 and 5 of the audio feed flags (`0x09075370`),
  entry 70 in bits 0 and 1, which a switch moves up.
- The stream's end in the first sector, the EOR bit with bit 0 of the mode or the system end code
  at +2320 with bit 1, sets bit 7 of the audio feed flags, or bit 3 for entry 70. Entry 72 looks
  at +2324 ([bugs and oddities](bugs-and-oddities.md)).
- In the audio layer, bit 0 of the layer byte, the sector's data counts as it is. A system end code
  at its start with bit 1 of the mode stops the audio, or drops the next connection.
- Entry 69 takes the audio layer's form 2 length, 2324 bytes, from bit 5 of the coding information
  byte, +19. Entry 70 takes it from the submode, +18, as entry 72 does.

## Jobs

`A7` to `AA` keep a job and set its bit of the job requests (`0x09075389`)
([image and sector jobs](commands.md#image-and-sector-jobs)). Each pass of the job moves one sector
and ends at entry 76.

- The job ends by clearing the job requests and writing `0x0800`, MPED, to `0x0a00001e`.
- A job waits for a free slot or a partition's sector by ending its pass, and the loop runs it
  again.
- `93`, which clears the job requests when it stops or resets the card, ends a job during a pass.
  A slot the pass took from the pool or out of a partition goes back to the pool, and no MPED
  follows.
- The image jobs end at once in the movie mode, the sector jobs outside the sector buffer mode.
- Filed sectors go through a filter as Get MPEG ROM files its pages: entries 81, 82, 84 and 87 of
  the ROM table take the slot, clear its header and tail and deliver it from CD device 3
  ([Get MPEG ROM](../cdblock/extensions.md#get-mpeg-rom)). Their header reads as a mode 0 sector's.

### Card memory

The jobs reach the card's 512 KB of memory through the window the card checks use
([card memory](../cdblock/extensions.md#card-memory)).

| Register | Use by the jobs |
| --- | --- |
| `0x0a100030` | Address, in 8-byte units |
| `0x0a100032` | `fb00` before reading sectors, `ff00` before writing them, `fa04` before reading image groups, `fe04` before writing them |
| `0x0a100034` | `fffc` after the command. Bit 0 set means ready |
| `0x0a100036` | Data, one word per access |

- Before each block the jobs wait for ready, up to 32 reads (`card_memory_ready`, `0x0907e71c`). A
  read without bit 0 writes `ffff` to `0x0a100034` and writes back the word it reads from
  `0x0a100036`.
- After each block they wait up to 112 reads for bit 0 (`card_memory_wait`, `0x0907e742`). No
  caller checks either wait's result.
- Each data word waits for a capture of the card's video data request line, up to 80 reads of
  TSR1, and clears it (`card_data_request_wait`, `0x0907e814`).
- A read restarts its block or group when a request does not come, up to five times, then goes on
  without the requests. Writes go on without them.
- The sector jobs move 2048 bytes in four blocks of 512. The image jobs move one 8-byte group at a
  time.
- The image jobs keep the video's DMA channel off while they run. `card_memory_open` (`0x0907e75c`)
  clears DE in CHCR2 and bit 7 of the mode word `0x0f000868`
  ([MPEG flags](../cdblock/host-commands.md#mpeg-flags)), which goes to `0x0a100014`. At the end
  `card_memory_close` (`0x0907e7b2`) reads 81 words from address 0, then undoes both.

### Sector jobs

`A9` and `AA` use the card's memory as Sega's MPEG sector buffer: 256 sectors of 2048 bytes, MPEG
sector n at byte 2048 × n.

- `A9` (entry 80) reads the next MPEG sector into a free slot and files it through the job's
  filter.
- `AA` (entry 79) takes one sector out of the partition at the job's position through entry 96,
  writes 2048 bytes of its data to the next MPEG sector and returns the slot to the pool. As Sega
  documents, the sectors leave the partition.
- The data starts at +16 in a mode 1 sector and at +24 otherwise, so a form 2 sector's last 276
  bytes stay behind.
- `AA` first pairs the device end `0x8b` with the partition's end.
- Both end after the job's last MPEG sector. With the count `ffff`, `AA` also ends when the
  partition is empty, and with another count it waits for sectors.
- The position `ffff`, Sega's last sector, takes the partition's last sector at each pass
  ([bugs and oddities](bugs-and-oddities.md)).

### Image jobs

`A7` and `A8` move a frame bank's image window, as `A6` set it, plane by plane: the Y plane, then
Cr and Cb at half the width and height, one byte per pixel.

- `A7` (entry 78) reads the pixels row by row into slots of 2048 bytes and files each through its
  plane's filter. A plane's last slot ends in zeros.
- `A8` (entry 77) writes each plane from its own partition. A pass takes a sector for the first
  unfinished plane whose partition holds one, and a pass without one waits.
- A mode 1 sector gives 2048 bytes from +16, a form 2 sector 2324 bytes from +24 and any other
  sector 2048 bytes from +24.
- `A8` writes a whole 8-byte group at once when the pixel starts a group and 8 bytes are left in
  the row and in the sector. Otherwise it reads the group, changes its bytes and writes it back.
- With clear mode 0, `A8` keeps the sectors and counts those each plane used. Mode 1 takes each
  sector out of its partition and returns its slot, as Sega's clear mode describes.
- Both end after the last plane.

The pixel addresses (`mpeg_frame_address`, `0x0907e84a`) lay the memory out as 512 rows of 1024
bytes.

| Pixels | Row | Column |
| --- | --- | --- |
| Y | y | x |
| Cr and Cb, x below 160 | 2y + 1 for Cr, 2y for Cb | x + 352 |
| Cr and Cb, x from 160 to 175 | 244 + y / 32 for Cr, 240 + y / 32 for Cb | x - 160 + 16 × (y mod 32) |

- A bank covers 256 rows of 512 bytes. Bank bit 0 selects the columns from 512, bit 1 the rows from
  256.
- In high definition the picture of 704 by 480 lies in four quarters of 352 by 240, 176 by 120 for
  Cr and Cb, laid out as the four banks. The bank only chooses the window.
