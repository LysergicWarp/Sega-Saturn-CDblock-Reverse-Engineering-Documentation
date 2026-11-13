# Video and audio

## What it does

The MPEG card decodes a video part and an audio part. The card's own entries move each part from
one of Sega's states to the next.

- States. Each part is stopped, preparing, transferring, switching or recovering. The firmware
  keeps the video state and the audio state in one byte each.
- Events. The card's status events and intervals reach task 8, which calls one card entry for each
  part's state.
- Transfers. At an interval in the preparation state, the card's code starts the DMA channel that
  sends that part's stream to the card.
- Pictures. In the transfer state the card marks the stream's first picture and keeps 33-bit
  timestamps in 90 kHz units.
- Switches. At the end of a stream, or on a change that `9C` asks for, a part moves to the next
  connection that `9A` registered.
- Flags. Each step sets Sega's MPEG interrupt factors, which `91` reports.

Card addresses are those of version 1 ([crosswalk](../mpeg-firmware-revisions.md#crosswalk)).

## Overview

The card's own entries move the decoder's video and audio parts through Sega's states: 1 stop, 2
and 3 preparation, 4 transfer, 5 switch and 6 recovery. The video state is the byte `0x0f00089c`,
the audio state `0x0f00089d`. The card's entry 35, like the ROM's, takes the card's status events
in task 8 and calls one entry for the state
([task 8's card events](../cdblock/extensions.md#task-8s-card-events)).

| Event | Video 3 | Video 4 | Video 5 | Audio 3 | Audio 5 |
| --- | --- | --- | --- | --- | --- |
| Status bit 11, a picture start | | 44 | 45 | | |
| Status bit 6, Sega's picture updated | | 48 | 49 | | |
| An interval, status bit 4 | 74 | `mpeg_video_transfer_interval` (`0x0907bca8`) | 46 | 73 | 85 |

- Status bits are the bits of the card register `0x0a100000` that the capture B handler finds
  clear ([capture B](../cdblock/extensions.md#capture-b)).
- Before these, entry 35 runs entry 43 for a picture start, 47 for a picture update and 75 for an
  interval ([task 8's handlers](task-8.md#card-events)).
- At an interval the video state 1 runs the countdowns and state 6 entry 41, the audio state 6
  entry 42 ([other entries](sh1-code.md#other-entries)).
- `9A` puts a part with a new connection in the state 2. Task 9's card work then finds the stream's
  first packet and sets the state 3 ([preparations](task-9.md#preparations)).
- Flags are Sega's MPEG interrupt factors in `0x0f000848`, which `91` reports. A flag whose mask
  bit is set also writes MPST ([card interrupts](../cdblock/extensions.md#card-interrupts)).
- Bit 0 of the register flags `0x0f000897` ([MPEG flags](../cdblock/host-commands.md#mpeg-flags)) is
  set while the code writes `0x0a180008`, bit 1 for `0x0a100000`, bit 2 for `0x0a10001a` and bit 3
  for `0x0a100022`. The MPEG commands that write the same registers wait while the bit is set.
- Bit 3 is set only in task 8, while entries 43, 44, 45, 63 and 75 read word 6. A `9F`, or a `98`
  in a still picture mode, that waits for it interrupts task 8
  ([bugs and oddities](../cdblock/bugs-and-oddities.md)).

Sega's MPEG part names the 24 interrupt factors in its section 7.2.3
([references](../references.md#sega-documentation)):

| Bit | Flag | Meaning |
| --- | --- | --- |
| 0 | VSRDY | Video stream ready |
| 1 | VSCHG | Video stream switch complete |
| 2 | VORDY | Video output ready |
| 3 | VOSTRT | Video output start |
| 4 | VDERR | Video decode error |
| 5 | VSERR | Video stream data error |
| 6 | VBERR | Video buffer partition connection error |
| 7 | VNERR | Next video stream data error |
| 8 | PSTRT | Picture start detected |
| 9 | GSTRT | Group of pictures (GOP) start detected |
| 10 | SQEND | Sequence end detected |
| 11 | SQSTRT | Sequence start detected |
| 12 | VTRG | Trigger bit of a video sector detected |
| 13 | VEOR | EOR bit of a video sector detected |
| 14 | ATRG | Trigger bit of an audio sector detected |
| 15 | AEOR | EOR bit of an audio sector detected |
| 16 | ASRDY | Audio stream ready |
| 17 | ASCHG | Audio stream switch complete |
| 18 | AORDY | Audio output ready |
| 19 | AOSTRT | Audio output start |
| 20 | ADERR | Audio decode error |
| 21 | ASERR | Audio stream data error |
| 22 | ABERR | Audio buffer partition connection error |
| 23 | ANERR | Next audio stream data error |

## Starting a transfer

Entry 74 starts the video transfer at an interval in state 3, and entry 73 the audio transfer.

- A cut asked for in state 3 returns the part to state 1 instead. `9A` asks for it through bit 0
  (video) or bit 2 (audio) of the cut requests (`0x0907534d`).
- With an automatic video transfer, bit 2 of the play flags `0x0f000890` as `95` sets it, the video
  waits until its partition holds the buffer size (`0x090752e0`) plus 8 sectors. Entry 54 keeps the
  stream's STD (system target decoder) buffer size there in 2048-byte sectors, or 28 for data
  without a pack, and activation keeps 20 ([the video](task-9.md#the-video)). So the transfer
  starts at the STD buffer size plus 16 KB, as Sega documents.
- In a synchronized play, bit 4 of the play flags, the video also waits for the audio state 3.
- Bits 4 and 5 of the video connection's mode choose a clear. Sega's VBV is the video buffer in
  front of the decoder, named for MPEG's video buffering verifier, and its WBC, write buffer
  control, the decoded pictures waiting for display. For 2, Sega's VBV and WBC clear, the word
  `0x0f00086a` goes to `0x0a10001a` without bits 12 to 14. For 1, Sega's VBV clear, it goes without
  bits 12 and 13. Both are written twice, five `nop`s apart.
- In the movie mode the entry sets the decode bit, then writes `ffdf` twice to `0x0a100018`.
- DMA channel 2 then sends the video to `0x0a10001e` from the data entry 54 kept, one word per
  video data request (CHCR2 `0x190d`). The state becomes 4 and the flag VSRDY (video stream ready)
  is set.
- The audio starts on DMA channel 3 (CHCR3 `0x180d`), with the state 4 and the flags ASRDY,
  AORDY and AOSTRT (audio stream ready, output ready and output start).
- In a synchronized play with an automatic audio transfer, bit 6 of the play flags, entry 73 only
  sets ASRDY. The audio then starts at the video's first picture, as Sega documents.

## Pictures and timestamps

In the transfer state the card marks the stream's first picture and keeps its timestamp.

- The card's word 6, read through `0x0a100022` as `98` does, holds a picture type in bits 13 to 15
  and a temporal reference in bits 0 to 9. Type 1 is an I picture and 2 a P picture, as in MPEG-1.
- The low 6 bits of `0x0a100006` tell which picture is shown. The code compares them with the low 6
  bits of a temporal reference it kept.
- Entry 44 keeps the temporal reference of the stream's first I picture. In a still picture mode
  it skips the read and keeps the low 6 bits of `r1`, where entry 43 leaves the picture rate bits
  of `0x0f00086a`: 16, 32 or 48.
- In the movie mode entry 48 waits until that picture is shown. It then sets bit 11 of the video
  status, Sega's first picture shown, and the flag VOSTRT (video output start). In the movie mode it
  sets the decode bit as `95`'s decode switch has it.
- Timestamps are 33 bits in 90 kHz units, a byte over a longword. The video's are the first
  video timestamp (`0x090752ac` over `0x090752a0`) and the second video timestamp (`0x090752ae`
  over `0x090752a8`). The audio's is the audio timestamp (`0x090752ad` over `0x090752a4`), the
  longword `99` answers.
- At the first picture the first video timestamp is copied to the second. With a picture search in
  the video connection and bit 1 of `0x090753fc`, the low 6 bits of the picture's temporal
  reference times one picture's duration are added.
- A picture lasts 3754, 3600 or 3003 ticks, for 1, 2 or any other value in bits 4 and 5 of the word
  `0x0f00086a`: 23.976, 25 and 29.97 pictures per second.
- In a synchronized play the waiting audio starts at the first picture, with the audio state 4
  and the flags AORDY and AOSTRT.
- Each picture update in a synchronized play, with the audio state 4, can write `fffb` or `ffef`
  to `0x0a100018`, as bit 0 of the timestamp distance's byte (`0x090752af`) selects. The write
  subtracts one picture's duration from the timestamp distance's longword (`0x090752b0`), which
  must be above one duration for `fffb` and two for `ffef`.
- While the first picture is awaited, `mpeg_video_transfer_interval` (`0x0907bca8`) clears the
  decode bit at an interval after a sequence end in the movie mode.

## Switching streams

A switch moves a part to the next connection `9A` registered. It follows the end of the current
stream, or a change `9C` asks for.

- The video's switch at the end of a stream runs while bit 0 of the card flags `0x0f000892` is set,
  which entry 51 sets. The end code itself sets no flag. At the next interval entry 46 moves the
  video part to its next connection and sets the flag VSCHG (video stream switch complete). The next
  connection and stream records become the current ones.
- At the sequence end entry 45 keeps two pictures: the old stream's last, the latest among the
  frame banks' records, and the new stream's first from word 6.
- Entry 49 sets bit 4 of the video status, Sega's last picture shown, when the old picture is
  shown. When the new one is shown it ends the switch: bit 11 of the video status, the flag
  VOSTRT, the state 4 and the first video timestamp copied to the second.
- A `9C` change runs with bit 0 of the card flags clear, through entries 88, 64, 63, 65 and 62. They
  keep the video's progress in the video change step (`0x09075378`).
- For a change, entry 88 also stops a part's DMA at once when CR3 asks for an immediate clear: bit 1
  of CR3's low byte clear for video, bit 0 of CR3's high byte set for audio. Sega's
  `CDC_MpChgCon` takes its audio and video clear modes there.
- For an immediate video change, entry 64 writes `0x0f00086a` to `0x0a10001a` without bits 12 to
  14, Sega's VBV and WBC clear, and moves the video part at once.
- Otherwise entry 63 waits for an I or P picture. It stops DMA channel 2 and writes the word
  without bits 12 and 13, Sega's VBV clear at the next I or P picture, before the move.
- Entry 65 makes the move when the next connection is registered only after the cut. A move starts
  DMA channel 2 and sets VSCHG.
- Entry 63 then keeps the next I picture. Entry 62 ends the change when it is shown, as entry 49
  ends a switch, and in the movie mode also clears the decode bit.
- Entry 63 posts `08890000` after the cut. Task 8 takes it at offset 0, entry 32, its own wait.
- An immediate audio change moves the audio part at once, or through entry 85 at an interval
  once the next connection is registered. The other clear mode leaves 2 in the audio change
  (`0x09075379`), and entry 72 ends the audio stream at the next end of DMA channel 3
  ([stream ends](task-8.md#stream-ends)).
- The audio's move copies the audio timestamp, starts DMA channel 3 and sets the flags ASCHG
  (audio stream switch complete) and AOSTRT.
