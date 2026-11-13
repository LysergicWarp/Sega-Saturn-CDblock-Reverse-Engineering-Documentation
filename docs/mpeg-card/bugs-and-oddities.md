# Bugs and oddities

Behavior in the MPEG card's SH-1 code that looks unintended or surprising. Addresses are those of
version 1 ([crosswalk](../mpeg-firmware-revisions.md#crosswalk)). Each entry is described in full
in the guide it links to. The CD-block firmware's own are listed in its
[bugs and oddities](../cdblock/bugs-and-oddities.md).

| Where | What happens | Guide |
| --- | --- | --- |
| `97`, `0x0907c536..0x0907c53e` | In a still picture mode with the decode state stopped, `97` reads a word at offset 26 from the kept card register words at `0x0f000854` and writes it at offset 26 from `0x0a100000`. The kept words skip the registers at offsets `0x16`, `0x18` and `0x1e`, so `0x0a10001a` gets the word kept for `0x0a100020`, without bit 13. Entry 50's routine makes the same write with `0x0f00086a`, the word kept for `0x0a10001a` | [`97`](commands.md#97) |
| `A1`, `0x0907f604..0x0907f608` | Setting 0 halves the frame buffer window position's y with a shift of CR3 and CR4 as one longword, so the halved y takes bit 0 of the x as its bit 15. An odd x gives a y of `0x8000` or more | [`A1`](commands.md#a1) |
| Entry 44, `0x0907bb50` | In a still picture mode the entry skips the read of the card's word 6 but still keeps the low 6 bits of `r1`, which it never set, as the picture's temporal reference. Entry 43, which runs before it, leaves the picture rate bits of `0x0f00086a` there, so the number is 16, 32 or 48. Entry 48 compares it with the picture shown only in the movie mode, but with a picture search and bit 1 of `0x090753fc` it adds that many pictures' durations to the video timestamp in either mode | [Pictures and timestamps](video-and-audio.md#pictures-and-timestamps) |
| Entry 63, `0x0907d67c` | After the cut it posts `08890000`, task 8's offset 0. On the known cards that is entry 32, task 8's own wait, so the message wakes task 8 only to wait again | [Switching streams](video-and-audio.md#switching-streams) |
| Entry 58's literal pool, `0x0907daa4` | The pool holds `0x09075314`, the address of the picture record, the longword the ROM's entry 58 clears. The card's entry 58 leaves it, and no instruction loads the literal | [Other entries](sh1-code.md#other-entries) |
| Entry 51, `0x0907b684..0x0907b692` | The video data goes out in words from its start rounded down to even. A packet whose data starts at an odd byte sends the byte before it, and an odd length leaves out the last byte. Entry 72 sends such bytes of the audio alone | [Video data](task-8.md#video-data) |
| Entry 72, `0x0907cd56` | With bit 1 of the connection mode the audio looks for the system end code at +2324 of a system stream's sector, 20 bytes before the last longword of a form 2 sector's data, where the video looks | [Stream ends](task-8.md#stream-ends) |
| Entries 72, 69 and 70, `0x0907cd98`, `0x0907f9b6` and `0x0907fd14` | A PTS (presentation time stamp) below 783 with bit 32 set should become the PTS less 783 with bit 32 cleared. The entries invert the difference where they would negate it, so the audio timestamp is 1 lower | [Audio data](task-8.md#audio-data), [the audio](task-9.md#the-audio) |
| Entry 72's literal pool, `0x0907cedc` | The pool holds `0x0f000895`, and no instruction loads it. The entry reaches that byte through `0x0f000890` | [Sector feeds](task-8.md#sector-feeds) |
| Entries 69 and 70, `0x0907f94a` and `0x0907fcc4` | With bit 1 of the connection mode the audio preparations look for the system end code at +2320 of a system stream's sector, 24 bytes before the last longword of a form 2 sector's data. Entry 72 looks at +2324 and the video at +2344 | [The audio](task-9.md#the-audio) |
| Entry 69, `0x0907fad0..0x0907fad4` | In the audio layer the entry reads the word at +18 and tests bit 5 of its low byte, the coding information at +19, for form 2. Entries 70 and 72 test the submode at +18 | [The audio](task-9.md#the-audio) |
| Entry 79, `0x0907ddb6..0x0907ddc4` | With `AA`'s position `ffff`, Sega's last sector, each pass takes the partition's last sector. A count above 1 writes the partition's sectors into the MPEG sector buffer last first, and the count `ffff` writes all of them so | [Sector jobs](task-9.md#sector-jobs) |
| Entry 54, `0x0907ecb4..0x0907ece6` | The picture search writes the bytes it kept from a packet's end just before the next packet's data, over the end of that packet's header in the buffered sector | [The picture search](task-9.md#the-picture-search) |
| Entries 77 to 80, `0x0907dd08`, `0x0907de92`, `0x0907e1a6` and `0x0907e50c` | Four short paths that no instruction reaches: an end of a sector job and an end of an image job that each return the slot first, a jump to the first, and a choice between the image job's ends by the clear mode | [Jobs](task-9.md#jobs) |

- As entry 33 keeps it, the word `97` writes is `d7af`, which has bit 13 clear already.
