# Task 8's handlers

## What it does

Task 8 runs the card's code for the card's interrupts and for the changes `9C` asks for. Five of
task 8's six message handlers go through the card's table, and the card supplies four of them.

- Card events. Entry 35 takes the card's status events, a picture start, a picture update and an
  interval, and runs the entries for each part's state.
- Pictures. At each picture start and update the card keeps the picture's record and time code and
  advances the second video timestamp.
- Feeds. At each end of DMA channel 2 or 3 the card sends the next sector's video or audio data
  to the card.
- Packet headers. One entry reads an MPEG-1 packet header for both feeds.
- Changes. Entry 64 starts the change `9C` asks for.
- Status. These entries set most of the MPEG status that `90` reports and the interrupt factors
  that `91` reports.

Card addresses are those of version 1 ([crosswalk](../mpeg-firmware-revisions.md#crosswalk)).

## Overview

Task 8 takes a message by its offset and runs the entry for it
([MPEG task](../cdblock/structure.md#mpeg-task)).

| Message | Offset | Posted by | Entry |
| --- | --- | --- | --- |
| `08890000` | 0 | Entry 63 | 32, task 8's own wait, the ROM's `task8_message_wait` (`0xa022`) |
| `08890008` | 8 | The DMA channel 2 end, entry 41 | 51, `mpeg_video_feed` (`0x0907b1c0`) |
| `088a000c` | 12 | The DMA channel 3 end, entry 35, entry 42 | 72, `mpeg_audio_feed` (`0x0907c99c`) |
| `088c0010` | 16 | Capture B | 35, `mpeg_card_events` (`0x0907c600`) |
| `08810014` | 20 | `9C` | 64, `mpeg_change_start` (`0x0907d4b8`) |

- Each handler ends by jumping to entry 32, task 8's wait.
- The DMA channel ends and capture B are described with the card's interrupts
  ([card interrupts](../cdblock/extensions.md#card-interrupts)).
- Flags are Sega's MPEG interrupt factors in `0x0f000848`, as in
  [video and audio](video-and-audio.md#overview). A flag whose mask bit is set also writes MPST.

## Card events

Entry 35, `mpeg_card_events` (`0x0907c600`), is the card's version of the ROM's
`task8_card_events` (`0xab78`). It takes the bits that capture B sets in `0x0f000896` in order and
clears each first ([capture B](../cdblock/extensions.md#capture-b)).

| Bit | Capture B's status bit | Entries |
| --- | --- | --- |
| 0 | 11, a picture start | 43, then 44 for the video state 4 or 45 for 5 |
| 1 | 6, Sega's picture updated | 47, then 48 or 49 the same way, then 36 in a synchronized pause with the audio held |
| 2 | 4, an interval | 75, then a step for the video state and one for the audio state |

- At an interval the video state picks its step from the table at `mpeg_video_interval_steps`
  (`0x0907c78c`): the countdowns for 1, entry 74 for 3, the step `mpeg_video_transfer_interval`
  (`0x0907bca8`) for 4, entry 46 for 5 and entry 41 for 6. The audio state 3 runs entry 73, 5 entry
  85 and 6 entry 42 ([video and audio](video-and-audio.md#overview)).
- The ROM's entry 35 has no step for the video states 1 and 4.
- Bit 3 of the card flags `0x0f000892` ([MPEG flags](../cdblock/host-commands.md#mpeg-flags)) stays
  set while the entry runs, so `95` and `9C` wait meanwhile, as in the ROM's.
- The interval counter `0x0f000842` counts while bits 0 and 6 of the mode word `0x0f000868` are set.
- After an interval, bit 7 of the pause flags `0x0f000893` marks a synchronized pause: both states
  4, bits 0 and 1 of the play flags `0x0f000890` set, and the pause (bit 0 or 1 of the pause flags)
  set. The ROM's entry 35 keeps the same condition in bit 7 of the play flags.
- In a synchronized pause with the audio held, bit 6 of the audio feed flags (`0x09075370`), each
  picture update runs entry 36. It returns `088a000c` for posting when the second video timestamp is
  past the audio timestamp, and entry 72 then moves the held audio on.
- An interval outside the pause clears a set bit 6 of the audio feed flags and posts `088a000c`.

## Picture starts

Entry 43, `mpeg_picture_start` (`0x0907b842`), runs at each picture start.

- It flags PSTRT (picture start detected).
- It flags GSTRT (group of pictures, or GOP, start detected) for status bit 12, which capture B
  keeps in bit 2 of the decode flags `0x0f000891`, and clears that bit.
- It flags SQSTRT (sequence start detected) when status bit 14 is clear in the word `0x0f000850`.
- It reads the card's word 6 for the new picture's type and temporal reference, and words 4 and 5
  for its time code, as `98` reads them in a still picture mode ([`98`](commands.md#98)).
- The new picture's record, the GOP count over word 6, goes to the picture record (`0x09075314`),
  and its time code to `0x09075318`.
- The record there before goes to the frame bank that bits 8 and 9 of `0x0a100006` give, the
  records `98` answers: `0x090752e4 + 4k` with bit 31 set and the time code at `0x090752f4 + 4k`.
  The other records lose bit 31. A record of picture type 0 is not kept, and a bank whose record
  has bit 31 already keeps it.
- The bank bits are those read at the first picture update since the previous start, otherwise
  those read at this start or the previous one.
- A GOP starts with status bit 12, or with a temporal reference of 0 outside one. The GOP count
  `0x09075310` counts up to 3. Past 3 each bank record's count drops by 1.
- The GOP start's temporal reference is kept at `0x0907530a`. Bit 6 of the decode flags stays set
  from there until a picture with a later temporal reference.
- With the decode stopped bit, bit 0 of the decode flags, the bank records lose bit 31 first. The
  stopped bit is cleared, except during a stream switch, whose entry 45 waits for it.
- Bits 12 to 15 of the card's word 1 hold the picture rate code of an MPEG-1 sequence header. They
  set bits 4 and 5 of the word `0x0f00086a`: 2 for code 3 (25 pictures per second), 1 for codes 1
  and 2 (23.976 and 24), 3 otherwise. The word goes to `0x0a10001a`. These bits set the picture
  duration ([pictures and timestamps](video-and-audio.md#pictures-and-timestamps)).
- The entry returns with those bits in `r1`, where entry 44 finds them
  ([bugs and oddities](bugs-and-oddities.md)).

## Picture updates

Entry 47, `mpeg_picture_update` (`0x0907bdc6`), runs at each picture update.

- It clears bits 11 and 4 of the video status, Sega's first and last picture shown.
- It adds one picture's duration to the second video timestamp, `0x090752ae` over `0x090752a8`.
  At 23.976 pictures per second the duration is 3754 with 3753 every fourth update, 3753.75 on
  average. Otherwise it is 3600 or 3003.
- Bits 4 and 5 of the update flags (`0x09075351`) count updates modulo 4. Entry 48's correction
  waits for 0.
- In an interlaced scan, bit 7 of the decode flags as `94` sets it, the word `0x090752e2` counts
  pictures. At 1008 for 23.976 pictures per second, 875 for 25 and 525 for 29.97 it restarts at 0
  and marks a correction, bit 2 of the update flags. At 437 for 25 it marks one without a restart.
- A correction writes `fffb` to `0x0a100018` the next two times the modulo 4 count reaches 0,
  three updates apart. The correction pair byte (`0x090753fd`) keeps the two together.
- Version 2 changes the counts and drops the pairing
  ([revisions](../mpeg-firmware-revisions.md#thresholds-and-flag-handling)).

## Intervals

Entry 75, `mpeg_interval_status` (`0x0907d0a0`), runs first at each interval.

- The picture type in the card's word 6 goes to `0x0f000844`, the picture information `90`
  reports.
- VORDY (video output ready) comes once for each transfer entry 74 starts, when bit 8 of the video
  status, Sega's output ready, is set.
- The flag VDERR sets bit 7 of the video status, Sega's video error.
- The audio status takes bit 4 of the connection flags `0x0f000894`, the audio transfer, as bit 0,
  Sega's decoding. Its bits 6 and 7, Sega's left and right output, are bits 10 and 11 of the word
  `0x0f000884`, which `96`'s mute sets, inverted.
- Bit 15 of the video status follows the sector buffer mode, bit 6 of the card flags.
- A next connection that task 9 prepared, bit 1 of the next connections (`0x0907534c`) for video
  (entry 53) and bit 3 for audio (entry 70), becomes a waiting one, bit 5 or bit 7. A next cut that
  `9A` asked for, bit 1 or bit 3 of the cut requests (`0x0907534d`), drops it instead.
- The entry then jumps to entry 50, which returns to entry 35.

## Decode errors

The routine at `mpeg_decode_error_recover` (`0x0907f728`) runs first in entries 43, 47 and 50. It
acts only in the movie mode with status bit 15 clear, the bit capture B turns into VDERR.

- It writes the word `0x0f00086a` without bit 13 to `0x0a10001a`. The kept word does not change.
- It pulses the decode bit, bit 0 of the control word `0x0f000854`: cleared, then set as `95`'s
  decode switch has it, each written to `0x0a100000`.

## Sector feeds

At each end of its DMA channel, a part's feed moves past the sector sent and starts the channel on
the next sector's data. Entry 51, `mpeg_video_feed` (`0x0907b1c0`), feeds the video, and entry
72, `mpeg_audio_feed` (`0x0907c99c`), the audio.

| | Video, entry 51 | Audio, entry 72 |
| --- | --- | --- |
| Partition | Feed partition (`0x0907532b`) | Feed partition (`0x0907532f`) |
| Position in it | Feed position (`0x09075324`) | Feed position (`0x09075326`) |
| Device end | `0x8d` | `0x8c` |
| Transfer | DMA channel 2 to `0x0a10001e` | DMA channel 3 to `0x0a180000`, single bytes to `0x0a180002` |
| Packet start codes | `000001e0..000001ef` | `000001c0..000001df` |

- Entry 51 takes the sector lock as task 8 at its start and releases it at its end, letting it go
  briefly between buffer services. Entry 72 takes it around each service.
- Bit 1 of the video stream flags (`0x0907535c`) for video and bit 0 of the audio stream flags
  (`0x09075371`) for audio, which a move to the next connection sets, make the feed pair its device
  end with the partition's end ([connections](../cdblock/sector-buffer.md#connections)).
- A connection that no longer holds is Sega's VBERR or ABERR, and the part stops.
- Moving past the sector sent adds 1 to the position. With Sega's delete mode, bit 2 of the
  connection mode, it releases the sector instead.
- After a recovery the position stays, since the sector there was not sent
  ([recovery](../cdblock/extensions.md#recovery)).
- No sector at the position sets the part's buffer empty bit and the state 6, recovery, the old
  state kept at `0x0f000898` or `0x0f000899`.
- In the movie mode the video then writes the mode word without bit 2 to `0x0a100014`, as the ROM's
  entry 41 does in the state 6.
- A sector that is not the part's data flags VSERR or ASERR (stream data error), sets the part's
  error bit and is skipped.
- The EOR and trigger bits of a sector's submode flag VEOR and VTRG, or AEOR and ATRG.

### Video data

| Sector | Data |
| --- | --- |
| Mode 0 | 2048 bytes from +24 |
| Mode 1 | 2048 bytes from +16 |
| Mode 2, form 1 | 2048 bytes from +24 |
| Mode 2, form 2 | 2324 bytes from +24 |
| Mode 2, form 2 with a pack | A video packet at +36, after the pack header |

- A pack with a system header at +36 is skipped. A packet of another stream type is not video.
- With Sega's stream number check, bit 1 of the stream mode, the stream ID's low 4 bits must equal
  the stream number. With the channel number check, bit 5, the subheader's channel number must
  equal the stream record's.
- The data goes out in words from its start rounded down to even.
- Only the packet's data goes out. The pack and packet headers and whatever follows the packet in
  the sector, such as a padding packet or the end code, stay behind, so the card gets the video
  elementary stream.
- Before the search, bit 3 of the video stream flags (`0x0907535c`), which `9D` sets for new
  current streams, writes `0x0f00086a` without bits 12 to 14 to `0x0a10001a`, Sega's VBV and WBC
  clear, which empties the video buffer in front of the decoder (VBV, after MPEG's video buffering
  verifier) and the decoded pictures waiting for display (WBC, write buffer control), then `ffdf`
  to `0x0a100018`.

### Audio data

- In the system layer, an audio packet at +36 after the pack header. Its PTS (presentation time
  stamp) less 783 becomes the audio timestamp, `0x090752ad` over `0x090752a4`. As for the video,
  only the packet's data goes out.
- The distance from the second video timestamp goes to the timestamp distance's longword
  (`0x090752b0`), at most `ffffffff`, and its byte (`0x090752af`) becomes 1 when the audio
  timestamp is the greater. Entry 48 corrects by them
  ([pictures and timestamps](video-and-audio.md#pictures-and-timestamps)).
- In the audio layer, bit 0 of the layer byte `0x0907532e`, the sector's data as it is: 2048 bytes
  for mode 1 and form 1, 2324 for form 2.
- An odd first byte goes alone to `0x0a180002` as a word's high byte, and so does an odd last
  byte after the words.
- Entry 72 first reads the audio register `0x0a180008`. Bit 15 clear, bits 12 and 13 both set, or
  bits 8 to 11 at 0 or 15 set bit 3 of the audio status, Sega's audio illegal, and pulse bit 14
  through entry 57.
- Otherwise the audio illegal bit is cleared and bit 4 of the register goes to bit 7 of the
  connection flags. With bit 0 set and a new high byte, kept at `0x09075372`, bits 8 to 11 pick a
  value from one of two tables at `0x0907ca74`, by bits 14 and 15, for bits 0 to 3 of the word
  `0x0f000884`, which goes to `0x0a180008`.
- In a synchronized pause entry 72 loads the channel but leaves it stopped, bit 6 of the audio
  feed flags (`0x09075370`). Each `088a000c` from entry 35 then moves one sector on. After the
  pause the next transfer first pulses bit 14 of `0x0a180008`.

### Stream ends

- A stream ends at a sector's EOR bit with bit 0 of the connection mode, or at a system end code
  `000001b9` with bit 1.
- The end code counts at the start of a sector's data. In a system stream's sector it counts in
  the last longword of the sector's data for the video and at +2324 for the audio. The audio
  preparations look at +2320 ([bugs and oddities](bugs-and-oddities.md)).
- Sega's BEF bit, bit 6 of the video connection mode, checks for the end code before the stream
  number.
- At its end the video part goes to the state 5 when a next connection is registered, and entry
  46 moves it there ([switching streams](video-and-audio.md#switching-streams)). Otherwise it stops.
- The audio part moves to its next connection at once when it is waiting, or sets the audio
  change byte (`0x09075379`) to 1 for entry 85, or stops.
- An audio change that entry 64 left, the value 2 in that byte, ends the audio stream at the next
  end of DMA channel 3.

## Packet headers

Entry 52, `mpeg_packet_header` (`0x0907b72c`), reads an MPEG-1 packet header from its length
field. Entries 51 and 72 and task 9's card work call it.

- Stuffing bytes, those with bit 7 set, are skipped.
- An STD (system target decoder) buffer size comes back in 2048-byte units.
- A PTS, alone or with a DTS (decoding time stamp), comes back as 33 bits.
- Any byte other than `0f`, the end of a header without timestamps, marks the header bad.
- The data's start and length come back, the length 0 when the header fills the packet.

## Changes

Entry 64, `mpeg_change_start` (`0x0907d4b8`), starts the change that `9C` asked for, with the
bytes `9C` keeps at `0x09075374` and `0x09075376`
([switching streams](video-and-audio.md#switching-streams)). It ends by clearing `0x0907537b`, so a
later `9C` no longer waits.
