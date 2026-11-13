# Bugs and oddities

Behavior in the CD-block firmware that looks unintended or surprising. Addresses are CDB105. Each
entry is described in full in the guide it links to. The MPEG card's code has its own
[bugs and oddities](../mpeg-card/bugs-and-oddities.md).

## Visible to the host

What host software can run into.

| Where | What happens | Guide |
| --- | --- | --- |
| `AE`, `0xa15c..0xa17a` | The words kept for the card registers skip offsets `0x16`, `0x18` and `0x1e`. `AE` answers the words kept for `0x12`, `0x14` and `0x1c` for them | [`AE` and `AF`](host-commands.md#ae-and-af) |
| Read Directory past the window, `task7_file_past_window` (`0x7fe4`) | The request leaves the filter mode as it was. After Read File it is still the frame range with the file number, so on an XA disc the directory's sectors, file number 0, fail the filter when the file's number was not 0, and the read never ends until `75` or a root `70` | [Read Directory](file-system.md#read-directory) |
| Task 1's result word, `sector_correct` (`0x6438`) | The Q result stays from the last Q pass, even when a later P pass repairs what that pass failed on. A sector that the last allowed P pass completes, the second with an ECC (error correction code) count of 0 or the last pair's otherwise, still carries bit 7 and goes to the retry rules. Rereads of the same damage give the same word, so a repaired sector can end the read with an error or retry without end | [Passes](sector-reads.md#passes) |
| Read File, `0x824c` | For an interleaved file the start frame counts the gaps, but the frame range is only as long as the file's sectors, so it ends before the file does. On a mode 1 disc the gap sectors in the range are read and the file's last sectors are not | [Read File](file-system.md#read-file) |
| Task 2's two-error step, `0x6122..0x6124` | log X1 = (d + log sigma2) / 2 by a shift is right only while the locators' logs add up to less than 63. Uncorrectable errors whose syndromes point at locators past the pack, both logs 31..55 and at most 23 apart, are "corrected" inside it, at two symbols or at one symbol twice, with result 2 and no pack data error | [Bugs and oddities](subcode.md#bugs-and-oddities) |
| Task 2's decode loop, `0x5f66..0x5f76` | The test for the handler's pack comes after each decode, so a message that finds task 2 caught up decodes all 32 ring packs. Each decode swaps symbols first, so the packs waiting for the host are swapped back and fail, and the packs being filled are flagged | [Bugs and oddities](subcode.md#bugs-and-oddities) |
| Copy and move, `0x7272` | Task 13 pairs device `0x89` with the destination filter's source, which disconnects whatever fed that filter. Into the filter of CD device 0 it cuts the drive's sectors off, and the pair stays | [Bugs and oddities](sector-buffer.md#bugs-and-oddities) |
| A move cut short, `task13_move_error` (`0x71d4`) | A move that finds a pair changed returns the slots it has not delivered to the pool, so their sectors end up in neither partition | [Bugs and oddities](sector-buffer.md#bugs-and-oddities) |
| `52` during a move, `0x59c0` | `52` reads the partition when task 4 runs. Accepted while task 13 holds the sector lock for a move out of the same partition, it counts past the new end and reads the header of slot `ff`, beyond the 512 KB buffer. `53` then answers one sector too many, or `ffffff` when the count ran two or more sectors past | [Bugs and oddities](sector-buffer.md#bugs-and-oddities) |
| A timer expiry after the check, `disc_auth_timeout` (`0x77e6`) | `timer_cancel` leaves an expiry the timer has already posted in task 7's mailbox. When the 20 seconds of a disc check run out while task 7 finishes it, as in the 3.5 second countdown for a remembered disc, task 7 takes the message after completion with no request active. It stores result 3 over the accepted result and closes the delivery gate | [A timer expiry left behind](disc-authentication.md#a-timer-expiry-left-behind) |
| An oversized disc extension, `disc_extension_collect` (`0x1a38`) | The encoded length is not checked against the 9 KB area. A longer extension is collected and decoded on into disc authentication's sector-check buffers, and the loader's clears stop at the area's end | [Disc extension loader](extensions.md#disc-extension-loader) |
| Multi-session discs, `0x39da` | `0x09000214` keeps the second largest next-session start of the `B0` reports. Unless the last session's lead-in has a `B0` report too, the seek after the TOC and the root request's volume descriptor come from an earlier session, while disc authentication scans the last one | [Multi-session discs](file-system.md#multi-session-discs) |
| `96`, `0xa85e`, and `97`, `0xa99c` | Where Sega documents the wait response, `96` in video state 6 and `97` in the movie mode with VSYNC timing, the ROM answers with the status response. `96` skips only the pause and still sets the freeze | [`96`](host-commands.md#96-set-decoding-method), [`97`](host-commands.md#97-send-decode-sync) |
| The subcode frame count, `0x5d02..0x5d08` | One frame is 85..425 counts, 255 early to 85 late. An interrupt more than 85 counts late counts two frames and moves the block's later symbols one place on | [Counting frames](subcode.md#counting-frames) |

- The `52` race needs only a host that sends `52` before a move out of the same partition ends.
- Whether task 2 is ever held past a whole pack, which the full-turn decode needs, is unknown.
- Whether the last session of released multi-session discs has a `B0` report is unknown.
- Whether a disc check on a console ever runs close enough to its 20 seconds to leave the timer
  expiry behind is unknown.

## Inside the firmware

Behavior a host rarely meets directly, in the firmware's own tasks, its MPEG handlers and its
kernel.

| Where | What happens | Guide |
| --- | --- | --- |
| Task 7's sector lock releases, `0x864a`, `0x8d94` | The releases use r11 as the acquire left it. After an acquire that had to wait r11 holds `task_return_exception` (`0x11aa`), so the release names lock record 0, fails its owner check with diagnostic 1 and task 7 keeps the lock. When `E0` finds a copy, a move or card code holding the lock, the next acquire at `0x8d28` finds the lock task 7's own (diagnostic 10), the release at `0x8d94` frees it and the request goes on. Every known revision has this code | [A contended sector lock](disc-authentication.md#a-contended-sector-lock) |
| Task 7's sector check, `disc_auth_check_sector` (`0x8a60`), `0x8a7e` | A sector that task 5 completes while task 7 still checks the previous one is checked in the same run, but its message stays in task 7's mailbox. Task 7 wakes once more with no sector past the cursor, `partition_slot` returns slot `ff`, and the check reads a sector at `0x09092900`, beyond the 512 KB buffer. Every known revision has this code | [A sector message left behind](disc-authentication.md#a-sector-message-left-behind) |
| `9F`'s wait path, `0x9e7c..0x9e88` | With bit 3 of the register flags `0x0f000897` set, `9F` returns without clearing r11, so the IRQ6 exit posts r11 as the interrupted code left it. The known cards set the bit only while task 8 reads the card's word 6 under entry 35, where r11 holds task 8's message `088c0010`, or the message entry 36 returned and entry 35 already posted. The post repeats it, and task 8 runs entry 35 once more with no event | [`99` and `9F`](host-commands.md#99-and-9f) |
| `A6`, `0xc470` | Setting an image window also clears `0x09075384`, which holds the last accepted `E0` or `E2` message | [`A6`](host-commands.md#a6-set-image-window) |
| Entry 36, `mpeg_timestamp_check` (`0xae68`) | The entry compares the byte `0x090752ad` over the word `0x090752a8` with the byte `0x090752ae` over the word `0x090752a4`. On the known cards `0x090752ae` over `0x090752a8` is the second video timestamp and `0x090752ad` over `0x090752a4` the audio one, so each byte is paired with the other timestamp's longword. The cards replace the entry with one that compares the two timestamps | [Task 8's card events](extensions.md#task-8s-card-events) |
| Entry 41, `mpeg_video_recover` (`0xad40..0xad7e`) | In state 6 each interval writes `0x0a100014` without bits 2 and 3 and leaves the mode word `0x0f000868`, its kept copy. The register gets the kept word back only when the video partition has filled, so until then `AE` can answer bits the card register lacks | [Recovery](extensions.md#recovery) |
| `98`'s wait path, `0x9d58..0x9d74` | In a still picture mode with bit 3 of the register flags `0x0f000897` set, `98` returns with r11 holding the status byte over the low 24 bits of the current task record's address, and the IRQ6 exit posts it. The status byte lands where a message names its task. The known cards' own `98` does the same, and they set the bit only in task 8, so the class is 0, which no task has a slot for. The post fails, except with status 0, where task 0's slot word is the reset vector's longword and the message is written to the ROM at `0x428` | [`98`](host-commands.md#98-get-mpeg-timecode), [card `98`](../mpeg-card/commands.md#98) |
| `94`, `0xa642..0xa64a` | Coming from a still picture mode, `94` writes `0x0f00086a` without bit 14 to `0x0a10001a` but keeps the word, so `AE` answers a bit the register lacks. The mode 2 that `94` then rejects writes it too | [`94`](host-commands.md#94-set-mpeg-mode) |
| `9D`, `mpeg_command_9d_store` (`0xb334`) | The stream mode byte is stored as it is, so bit 7, Sega's no change, is stored with it | [`9D`](host-commands.md#9d-set-mpeg-stream) |
| The file system's sectors, `task7_file_sector` (`0x7954`), `task7_file_sector_next` (`0x7d2c`) | As in the check loop, a directory sector completed while task 7 parses the one before is parsed in the same run, but its notification stays. Task 7 wakes with partition f empty, and `partition_slot` returns slot `ff` | [Bugs and oddities](file-system.md#bugs-and-oddities) |
| The diagnostic byte, `0x09e0..0x0a28` | The byte is built in r13, which still holds `0x0f000004`, so bit 2 is set on a board that passes and an interface register failure looks like a pass. Card mask bits 0 and 2 share bit 4, and bit 7 is never set | [The report](structure.md#the-report) |
| The monitor's setup, `0x0a5e` | Clearing SSR1 with transmit enabled sends the report's last byte again, at 9600 bps, before the prompt | [The monitor](structure.md#the-monitor) |
| The monitor's transmit ring, `monitor_put` (`0x0cf4`) | There is no full check. With 256 bytes waiting the write index passes the read index and the waiting output is lost | [The monitor](structure.md#the-monitor) |
| DMA address error, `exception_dma_address_error` (`0x0946`) | The handler stops every channel and tells no task, so a read waits in SEEK until a new play command and a transfer until `06` | [DMA address error](structure.md#dma-address-error) |
| `TRAPA 0x20`, `0x0f10..0x0f20` | A destination already in a ready queue is looked for one step short, in the queue whose head slot lies 16 bytes after its own. For the last four heads (IDs 1, 13, 9 and 14) that slot is in the first four longwords of the disc extension's collection state, `0x0f000208..0x0f000217`, followed as a record unless it reads 0. Not found there, the search reads the ROM longwords at `0x10` and `0x944`, then a longword at `0x00090019`, a CPU address error. No ROM code issues the trap | [Send and reply](kernel.md#send-and-reply) |
| The reply, `0x0f52`, `task_restore_reply` (`0x116c`) | The reply's words go to the sender's `+24` and `+28`, its first two mailbox words: for task 1 and task 13 also the next record's first word, for task 14 the current record pointer and the first ready head. A reply replaces a message waiting there, and one sent to a task in state 3 stays there as messages without a count. No ROM code issues the traps | [Send and reply](kernel.md#send-and-reply) |
| `TRAPA 0x26`, `0x123e` | The owner compare sign-extends the stored byte, so a lock held by owner `0x80..0xff` is refused to its own owner. No ROM code issues the trap | [Lock attempt](kernel.md#lock-attempt) |

- Whether the check-loop race and the file system's sector race occur with real drive timing is
  unknown.

## Code nothing reaches

No ROM code reaches the code below. Card code and disc extensions can still call it: the kernel
services through their traps, entry 61 through the interface page, and any routine by its address.

| Where | What it is | Guide |
| --- | --- | --- |
| `exception_restart_unused` (`0x09c0`) | A restart stub like `interrupt_sci1` (`0x09c6`). No vector names it | [Exceptions](structure.md#exceptions) |
| `TRAPA 0x20`, `0x22`, `0x26`, `0x29`, `0x2c` | The kernel's send and wait `message_send_wait_reply` (`0x0ee4`), post and raise `message_post_priority` (`0x0fb8`), lock attempt `trap_lock_try` (`0x121e`), reply `message_reply` (`0x0f44`) and the empty service `trap_unused` (`0x1bfe`). No ROM code issues these traps. Task state 2's dispatch `task_restore_reply` (`0x116c`) runs only for a sender of `TRAPA 0x20` | [Services](kernel.md#services) |
| `expansion_extension_clear_alternate` (`0x1b52`) | The expansion loader's alternate cleanup entry | [Expansion extension loader](extensions.md#expansion-extension-loader) |
| `0x20ca` | A second `jmp @r4` after group 4's reject | [Buffer commands](host-commands.md#buffer-commands) |
| `0x2ae6..0x2af0` | In drive state 0, a check for an ADR 1 report that copies report byte 7 to `0x0f0002fe`. The branch before it always skips it | [Drive state 0](drive.md#drive-state-0) |
| `status_report_jump` (`0x3644`) | The jump to `status_from_report` among the status jumps | [Status bytes](drive.md#status-bytes) |
| `0x3bb2` | An entry after drive state 4's handler that stores r0 as the host status | [Position states](drive.md#position-states) |
| `0x50c4` | The return of a partition's cursor slot in `partition_slot` (`0x506c`) | [Partitions](sector-buffer.md#partitions) |
| `filter_clear` (`0x543e`) | Clears one filter record. The only longword that holds its address, `0x8354`, is never loaded | [Filters](sector-buffer.md#filters) |
| `mpeg_decode_pulse` (`0xb9b2`) | Entry 61, which pulses the decode bit. Only its interface page stub leads there, and no ROM code calls the stub | [DMA channel ends](extensions.md#dma-channel-ends) |
| `mpeg_check_fail` (`0xbc80`), `card_id_check` (`0xbc84`), `card_header_check` (`0xbd78`), `card_ready_masked` (`0xbfba`), `card_control_set` (`0xbff8`) | Card routines among the checks | [Unused card routines](extensions.md#unused-card-routines) |
| Interface page | No ROM code calls the stubs of entries 50, 52, 55, 61..63, 65, 71, 76, 81..84, 87 and 91..97. The ROM table holds 0 for 50, 52, 55, 62, 63, 65 and 71. ROM code reaches the routines of 76, 81..84, 87 and 91..97 without the stubs | [Expansion entries](extensions.md#expansion-entries) |

Every other instruction in the ROM lies on a path from the reset vector, a hardware vector, a trap
some ROM code issues or a table some ROM code reads.

## Messages no ROM code posts

The dispatch and mailbox slots below take messages that no ROM code posts. Card code and disc
extensions can post them, except task 4's class 7.

| Message | What it does | Guide |
| --- | --- | --- |
| Task 6, class `0x81` payloads 1 and 14 | Payload 1 returns at once. Payload 14 resumes a held read, as class 4 payload 0 does | [Requests from the host](drive.md#requests-from-the-host) |
| Task 4, class 7 | Runs the filter settings of `40`, `42`, `44` and `46`. Task 4's mailbox has no class 7 slot, so a post of it fails | [Task 4](sector-buffer.md#task-4) |
| Task 4 classes 3 and 5, task 5 class 4, task 8 classes 8 and `0x8b`, task 9 class 9 | Mailbox slots nothing posts to | [Posting](kernel.md#posting) |
