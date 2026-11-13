# Kernel

## What it does

The CD block's SH-1 has several jobs at once: it runs the drive, takes sectors from the disc,
answers the Saturn and checks discs. The kernel is the firmware's own small operating system, which
lets these jobs share one processor.

- Tasks. Each job is a task with its own stack. A task keeps the processor until it waits, or until
  an interrupt wakes a task with a higher priority. Eleven tasks start at power-on.
- Messages. Tasks wait for messages of one 32-bit word. A host command, a sector, a drive report or
  an expired timer becomes a message to the task that handles it.
- Locks. A lock keeps two tasks from changing the same records at once, such as the sector
  buffer's lists.
- Timers. A timer is a message that arrives after a delay, so a task can give up after a deadline.
- Restart. The host's reset request starts every task afresh, except the drive task and the idle
  task.
- Services no ROM code uses. The kernel also has a send that waits for the receiver's reply, a post
  that lets the woken task run at the sender's priority and a lock attempt that does not wait.
  Neither the ROM nor the known cards' code uses them, but loaded code can, through `TRAPA`.

Tasks and interrupt handlers reach these services through `TRAPA` traps. The sections below follow
CDB105 by address.

## Services

The trap entries below are the ROM vector table's, which applies while VBR is 0. An installed
extension can change VBR and with it every service.

| Trap | Entry | Service |
| --- | --- | --- |
| `20` | `message_send_wait_reply` (`0x0ee4`) | [Send and wait for a reply](#send-and-reply). No ROM code issues it |
| `21` | `message_post_and_ready` (`0x0f72`) | [Post a message](#posting) |
| `22` | `message_post_priority` (`0x0fb8`) | [Post and raise the destination](#post-and-raise). No ROM code issues it |
| `23` | `task_wait_message` (`0x0e80`) | [Wait for a message](#waiting) |
| `24` | `timer_start` (`0x1d96`) | [Start timer](#timers) r11 with duration r10 |
| `25` | `timer_cancel` (`0x1e46`) | [Cancel timer](#timers) r11 |
| `26` | `trap_lock_try` (`0x121e`) | [Try a lock without waiting](#lock-attempt). No ROM code issues it |
| `27` | `trap_lock_release` (`0x1250`) | [Release a lock](#locks) |
| `28` | `task_reinit` (`0x0e5c`) | Initialize the record of task r11 >> 24 again through `task_initialize` (`0x1058`), as at startup, with SR mask 6. Task 5 uses it to start task 1 afresh ([sector reads](sector-reads.md#stop)) |
| `29` | `message_reply` (`0x0f44`) | [Reply](#send-and-reply). No ROM code issues it |
| `2a` | `trap_lock_acquire` (`0x12d2`) | [Acquire a lock](#locks), blocking |
| `2b` | `trap_diagnostic` (`0x1bf8`) | Diagnostic, with r0 naming the condition |
| `2c` | `trap_unused` (`0x1bfe`) | Returns at once. No ROM code issues it |
| `2d` | `deferred_post` (`0x1eac`) | [Post from an interrupt handler](#posting-from-interrupts) |
| `2e` | `task_restart` (`0x0d94`) | [Restart the other tasks](#restart) |

The diagnostic trap is `nop` and `rte` in the ROM vectors, so in effect the kernel notes an internal
error in r0 and carries on. The conditions that raise it are listed with each service.
`TRAPA 0x2f..0x3f`, which no ROM code issues, return at once like the reserved vectors, and the
other exceptions and interrupts go to the handlers in [exceptions](structure.md#exceptions).

## Names

| Name | Address | Contents |
| --- | --- | --- |
| Current record | `0x0f0001d4` | Pointer to the running task's record |
| Ready heads | `0x0f0001d8..0x0f000204` | Twelve ready-queue heads, scanned in address order |
| Ready table | `trap_ready_table` (`0x13ec`) | Ready-list head pointers, indexed by record `+6` |
| Record table | `trap_record_table` (`0x1464`) | Record pointers, indexed by r11 bits 31..24 in the lock services |
| Dispatch table | `task_dispatch_table` (`0x1358`) | Restore path for each task state |
| Mailbox table | `0x1428` | Mailbox base for each task |
| Descriptor table | `task_descriptor_table` (`0x14a0`) | Descriptor for each task: its mailbox slots and its clear range |
| Handler stack | `0x0f0008f8` | Stack used by the IRQ6, timer and compare match B handlers |
| Timer table | `0x0f000220..0x0f00023f` | Four timers of identifier and deadline |
| Time high part | `0x0f00021c` | Counts overflows of ITU4, channel 4 of the SH-1's integrated timer pulse unit (ITU) |
| Deferred messages | `0x0f000240`, `0x0f000244` | Messages from interrupt handlers, waiting for compare match B |

### Task records

| Offset | Field |
| --- | --- |
| `+2` | Lock byte, in records used as locks |
| `+3` | Lock owner, or the source filter for posted messages |
| `+4` | Class of the last consumed message, also a partner match byte |
| `+5` | Partner match byte |
| `+6` | Ready-table byte offset. Dispatch clears it |
| `+7` | Pending message count |
| `+8` | Saved stack pointer |
| `+12` | Waiter link for locks |
| `+16` | Ready-queue link |
| `+20` | Partner task |
| `+24`, `+28` | The first two mailbox words, where a reply leaves its result ([send and reply](#send-and-reply)) |

A record is 24 bytes and the task's mailbox follows it, so `+24` and `+28` are the mailbox's first
two words. Task 1's mailbox is one word, so its `+28` is task 2's first record word. Task 13's `+28`
is task 14's, and task 14's `+24` and `+28` are the current record pointer and the first ready head.

### Task states

| State | Meaning | Dispatch restores through |
| --- | --- | --- |
| 0 | Created | `task_return_exception` (`0x11aa`), PC and SR only |
| 1 | Waiting for a message | Message resumption `task_resume_message` (`0x1130`) |
| 2 | Waiting for a reply after `TRAPA 0x20` | `task_restore_reply` (`0x116c`), r12 and r13 from `+24` and `+28`, both cleared, then PC and SR |
| 3 | Replied with `TRAPA 0x29`, waiting for the partner's next wait | `task_return_exception` (`0x11aa`) |
| 4 | Ready with a full saved context | `task_restore_context` (`0x117c`), all registers except r14 |
| 5 | Running | `task_return_exception` (`0x11aa`) |
| 6 | Waiting for a lock | `task_return_exception` (`0x11aa`) |

## Tasks

Startup creates every task record through `task_initialize` (`0x1058`) and chains the first eleven
into one ready list.

- IDs 1, 2, 4, 12, 13, 7, 9, 8, 5, 6, 14, 11 and 3 are initialized in that order. The first eleven
  are chained in that order under ready head `0x0f0001d8`, and the other heads start empty. This
  bootstrap chain is separate from the later per-ID ready queues.
- `task_initialize` writes each record's ID and zero state, clears the queue and message fields,
  and pushes an eight-byte entry PC/SR frame (SR `0x20`) when the task has a stack. A null stack
  pointer leaves record `+8` unchanged. Task IDs are not validated.
- The task's descriptor gives a half-open RAM range to clear at `+0x6c/+0x70`, after its mailbox
  slot words ([posting](#posting)). Task 14's descriptor pointer is zero, so it reads vector
  longwords `0x006c/0x0070`, which both hold `exception_ignored` (`0x09d2`). In effect task 14
  clears nothing.
- IDs 11 and 3 get records but no entry or stack. Record 11 at `0x0f000168` serves as the
  [sector lock](#locks).

| ID | Entry PC | Initial stack top | Clear range |
| --- | --- | --- | --- |
| 1 | `task1_message_entry` (`0x63dc`) | `0x0f000cb0` | `0x0f000020..0x0f000024` |
| 2 | `task2_entry` (`0x5e68`) | `0x0f000d38` | `0x0f00003c..0x0f000048` |
| 4 | `task4_buffer_entry` (`0x56f8`) | `0x0f000c28` | `0x0f000078..0x0f000084` |
| 12 | `task12_entry` (`0x6990`) | `0x0f000f10` | `0x0f000198..0x0f0001a0` |
| 13 | `task13_entry` (`0x6fc8`) | `0x0f000f98` | `0x0f0001b8..0x0f0001bc` |
| 7 | `task7_disc_entry` (`0x77b2`) | `0x0f000b18` | `0x0f000100..0x0f000114` |
| 9 | `task9_message_wait` (`0xba46`) | `0x0f000e88` | `0x0f000160..0x0f000168` |
| 8 | `task8_mpeg_entry` (`0xa010`) | `0x0f000de0` | `0x0f00012c..0x0f000148` |
| 5 | `task5_setup` (`0x4594`) | `0x0f000ba0` | `0x0f00009c..0x0f0000b4` |
| 6 | `task6_setup` (`0x2718`) | `0x0f000a90` | `0x0f0000cc..0x0f0000e8` |
| 14 | `task14_entry` (`0x1be0`) | `0x0f001000` | Empty |
| 11, 3 | None | None | Empty |

What each task does after setup is in [structure](structure.md#initial-tasks).

## Restart

`TRAPA 0x2e` (vector longword `0x00b8`) starts every task except 6 and 14 afresh, as after reset.
Task 6 calls it for the host's reset request, command `04` with bit 0 of the CR1 low byte set
([drive](drive.md#requests-from-the-host)), after saving and clearing IPRA..IPRD.

- `task_restart` (`0x0d94`) sets SR `0xf0` and clears TIER0, TIER1 and TIER2 and TSR0, TSR1 and
  TSR2, the interrupt enables and flags of ITU channels 0..2 ([SH7034
  notes](../sh7034.md#itu-channels-0-to-2-and-the-dmac)).
- `timer_reset` (`0x1c46`) resets the timers: TIOR4 0, TIER4 4 (overflow interrupt only), the timer
  table `0x0f000220..0x0f00023f` and the deferred messages `0x0f000240` and `0x0f000244` cleared.
  Unlike startup's `startup_timer_state` (`0x1c04`) it leaves the time high part, TCR4 and TSTR
  alone, so the clock keeps running.
- `startup_dmac` (`0x06bc`) writes DMAOR and CHCR0..CHCR3 as at startup, and
  `startup_transfer_state` (`0x2388`) resets the transfer state `0x0f000248..0x0f00025b` ([data
  transfer](data-transfer.md#names)).
- The first eleven ready heads are cleared. The twelfth, `0x0f000204`, keeps the idle task that the
  host command interrupted.
- The records of IDs 1, 2, 4, 12, 13, 7, 9, 8, 5, 11 and 3 (bytes `task_restart_ids`,
  `0x134d..0x1357`) are initialized through `task_initialize` (`0x1058`) as at startup. Records 11
  and 3 are the sector lock and the transfer lock, so both come back free.
- IDs 1, 2, 4, 12, 13, 7, 9, 8, 5 and 6 (bytes `0x1340..0x1349`) are chained under the first ready
  head.
- Task 6's record is rewritten in place: ID 6 and state 0, `+4`, `+12`, `+16` and `+20` cleared,
  `+8` the current SP, which holds the trap's PC and SR. Its mailbox `0x0f0000cc..0x0f0000e7` is
  cleared, so pending messages for it are dropped.
- Selection and dispatch follow. Each restarted task runs its setup to its first wait, with the same
  records and saved continuations as after reset. Task 6 then resumes after its trap with PC and SR
  only, and task 14 idles again.
- The restart leaves VBR and the extension areas of DRAM alone, so an installed disc extension keeps
  its vectors and resume words ([extensions](extensions.md#lifetime)).
- Task 8's setup runs again and clears the MPEG state, the card bit with it, in on-chip RAM and in
  DRAM `0x090752a0..0x090753eb` ([MPEG task](structure.md#mpeg-task)).

## Scheduling

The running task keeps the CPU until it waits, blocks on a lock or is interrupted. The scheduler
then runs the first task from twelve ready queues in a fixed priority order.

- Requeue `task_requeue_current` (`0x102e`) marks the current record state 4 and appends it to its
  ID-selected ready queue. It does not clear the incoming link. The IRQ6 handler, the timer handler
  and lock release all end here, so an interrupt can switch tasks.
- Selection `task_select_ready` (`0x10a8`) scans the ready heads in address order. The first
  nonempty head wins, and the selected record's `+16` link is cleared. The scan order corresponds to
  IDs 0, 4, 6, 5, 12, 7, 8, 2, 1, 13, 9, 14, which is the priority order. Task 6 therefore runs
  before task 7 when both are ready. An empty scan raises the diagnostic trap with r0 6.
- Dispatch `task_dispatch` (`0x1118`) indexes the dispatch table with the selected record's old
  signed state, sets state 5, clears `+6`, publishes the current record and switches SP in the
  indirect jump's delay slot. The restore path per state is in [Task states](#task-states).
- The full restore, `task_restore_context` (`0x117c`), loads MACL, MACH, GBR, PR, r13..r0, PC and SR
  from 80 bytes and advances record `+8` past them. `task_return_exception` (`0x11aa`) restores only
  PC and SR. Neither touches r14 or VBR.
- A released lock waiter is not guaranteed to run next. If the releasing task's queue outranks the
  waiter's, the releaser resumes first while the waiter owns the lock and stays ready.

## Messages

A message is one 32-bit word. Each task has one mailbox slot per message class, and a waiting task
resumes with the message in r11.

| Bits | Field |
| --- | --- |
| 31..24 | Destination task |
| 23..16 | Class, or the sending task |
| 15..0 | Payload |

### Posting

`TRAPA 0x21` (vector longword `0x0084`) enters `message_post_and_ready` (`0x0f72`), which sets SR
mask 6 and calls `message_store` (`0x11be`).

- The destination selects its descriptor through the descriptor table, and the class selects a slot
  word in it: classes 0..13 from `+0`, classes `0x80..0x8c` from `+56`. The tables are not
  validated.
- An empty slot increments the destination's count at `+7`. An occupied slot is overwritten without
  incrementing, so an unconsumed message of the same class is lost.
- Class bit 7 bypasses the record `+3` source filter. A null slot or a source mismatch raises the
  diagnostic trap.
- The destination joins its ready queue only when it is in state 1 with `+6` zero. The service
  returns to its caller without switching tasks. Interrupt handlers switch afterwards through
  `task_requeue_current` (`0x102e`).
- r0 returns 0 when the destination joined its queue, its state when that is not 1, its `+6` when
  it is already queued, and -1 when the post fails.

| Destination | Descriptor | Class and slot |
| --- | --- | --- |
| 1 | `task1_descriptor` (`0x14d8`) | 5 `0x0f000020` |
| 2 | `task2_descriptor` (`0x154c`) | 3 `0x0f00003c`, `0x80` `0x0f000040`, `0x81` `0x0f000044` |
| 4 | `task4_descriptor` (`0x15c0`) | 3 `0x0f000078`, 5 `0x0f00007c`, `0x81` `0x0f000080` |
| 5 | `task5_descriptor` (`0x1634`) | 1 `0x0f0000ac`, 4 `0x0f0000a8`, 6 `0x0f0000a4`, `0x80` `0x0f00009c`, `0x81` `0x0f0000b0`, `0x84` `0x0f0000a0` |
| 6 | `task6_descriptor` (`0x16a8`) | 3 `0x0f0000d0`, 4 `0x0f0000d4`, 5 `0x0f0000d8`, 6 `0x0f0000dc`, 7 `0x0f0000e0`, `0x81` `0x0f0000e4`, `0x83` `0x0f0000cc` |
| 7 | `task7_descriptor` (`0x171c`) | 3 `0x0f000100`, 4 `0x0f000104`, 6 `0x0f000108`, 7 `0x0f00010c`, `0x81` `0x0f000110` |
| 8 | `task8_descriptor` (`0x1790`) | 8 `0x0f00013c`, 9 `0x0f000140`, `0x81` `0x0f000144`, `0x89` `0x0f00012c`, `0x8a` `0x0f000130`, `0x8b` `0x0f000138`, `0x8c` `0x0f000134` |
| 9 | `task9_descriptor` (`0x1804`) | 9 `0x0f000164`, `0x81` `0x0f000160` |
| 12 | `task12_descriptor` (`0x1878`) | 3 `0x0f000198`, `0x81` `0x0f00019c` |
| 13 | `task13_descriptor` (`0x18ec`) | `0x81` `0x0f0001b8` |
| 3, 10, 11 | `shared_descriptor` (`0x1960`) | None |

- Every other slot word is null.
- No ROM code posts to task 4's classes 3 and 5, task 5's class 4, task 8's classes 8 and `0x8b`,
  or task 9's class 9. Task 4 handles class 7, which has no slot
  ([task 4](sector-buffer.md#task-4)).
- IDs 0 and 14 have no descriptor. The pointer is 0, so a post to them takes its slot word from
  the vector table.
- The clear range follows the slot words at `+0x6c` ([tasks](#tasks)).

### Posting from interrupts

The decoder interrupt IRQ7 and the end of DMA channel 0 run on stacks of their own and do not post
directly. They leave the message for ITU4 compare match B, which posts it from the handler stack
([sector reads](sector-reads.md)).

- `TRAPA 0x2d` (vector longword `0x00b4`) enters `deferred_post` (`0x1eac`). It keeps r11 at
  `0x0f000240`, or at `0x0f000244` when the first slot is taken. With both taken the second is
  overwritten.
- It sets GRB4 to TCNT4 plus `0x7d`, clears IMFB and sets IMIEB, then returns. `0x7d` counts are
  50 µs at 2.5 MHz ([SH7034 notes](../sh7034.md#itu-channel-4)).
- Compare match B enters `deferred_post_deliver` (`0x1d38`, vector 97, ROM longword `0x0184`). Like
  the IRQ6 handler it saves r0..r13, PR, GBR, MACH and MACL, keeps the frame pointer in the current
  record and switches to the handler stack.
- It clears IMFB and, with interrupts masked, takes both slots, clears them and clears IMIEB.
- It posts the first message and the second when there is one, then reschedules at
  `task_requeue_current` (`0x102e`). A woken task with the higher priority runs before the
  interrupted one.

### Waiting

`TRAPA 0x23` enters `task_wait_message` (`0x0e80`) and sets SR `0x60`.

- A nonzero pending count at `+7` means a message is already there, and the task goes straight back
  to its ready queue.
- Record `+20` can name a partner, the other side of a [send and reply](#send-and-reply). If the
  partner's ID matches byte `+4` or `+5`, that byte and `+20` are cleared and the partner runs
  directly. Otherwise `+20` is kept, `+4` is cleared and the ready selector chooses.
- The waiting task enters state 1 and saves only its exception SP, so only PC and SR come back.
  Ordinary selection sets PR to `0x0ed2`, and the partner path keeps the incoming PR.

### Resumption

State-1 dispatch at `task_resume_message` (`0x1130`) hands the task its next message.

- It first reads the word at `0x09075800 + 4*ID` in the disc extension area. A nonzero word
  replaces the saved PC, with no active-flag, range or alignment check
  ([Extension hooks](extensions.md#hooks)).
- It scans the task's mailbox, from the base in the mailbox table, for the first nonzero word. It
  checks neither the count nor the mailbox end. The word's high byte must be this task's ID,
  otherwise the diagnostic trap runs with r0 7.
- The slot order therefore sets the priority between classes. Task 7 takes a sector message (class
  4) before a seek report (class 6) or a timer expiry (class 7).
- The message stays in r11 and r13 becomes zero. The class byte goes to record `+4`, `+7` drops by
  one modulo 256, the slot is cleared in the RTE delay slot and PC/SR are restored.

### Send and reply

`TRAPA 0x20` sends a message and hands the processor straight to its destination. The sender waits
until the destination answers with `TRAPA 0x29` or waits again. No ROM code issues either trap.

- `TRAPA 0x20` enters `message_send_wait_reply` (`0x0ee4`) and sets SR `0x60`. Bits 31..24 of r11
  name the destination and bits 23..16 the sender. The sender's record comes from that byte, not
  from the current record, so the byte must be the caller's own ID.
- A destination in state 2 or 3 is refused: the diagnostic trap runs with r0 4 and the service
  returns r0 = -1 without posting.
- Otherwise the message is posted through the mailbox routine, whose result is not checked. The
  sender waits in state 2, the destination's `+20` names it and the destination is dispatched at
  once, whatever its priority. A waiting destination takes the message through resumption.
- `TRAPA 0x29` enters `message_reply` (`0x0f44`). The current task's `+20` names its partner. r12
  and r13 go to the partner's `+24` and `+28`, the partner's `+5` and `+20` name the replier, the
  replier's `+20` is cleared, and the replier waits in state 3 while the partner is dispatched. The
  partner's state is not checked. With no partner the diagnostic trap runs with r0 5 and r0
  returns -1.
- State 2's dispatch at `task_restore_reply` (`0x116c`) gives the sender r12 and r13 from `+24` and
  `+28`, clears both and returns with r0 0 and r10 its record.
- The partner's next `TRAPA 0x23` runs the replier again: the wait finds the replier's ID in `+5`
  and dispatches it directly ([waiting](#waiting)), which restores only PC and SR.
- A destination that waits without replying releases the sender the same way through `+4`, the
  class of the message it took. The sender resumes with its first two mailbox words, 0 when they
  are empty.

Side effects:

- `+24` and `+28` are the sender's first two mailbox words. A reply replaces a message waiting
  there, and the dispatch clears both, so the message is lost while the count keeps it. The next
  resumption scans past the mailbox and raises the diagnostic trap with r0 7 at the first word that
  names another task.
- When the sender replies in turn to its replier, which waits in state 3, the replier is dispatched
  through PC and SR only. r12 and r13 stay in its first two mailbox words without a count, and its
  next resumption takes them as messages.
- A destination already in a ready queue (`+6` nonzero), such as a task woken by an earlier post
  that has not run yet, is looked for one step short. The search takes the head slot's address as
  the first record, so it walks the queue whose head slot lies 16 bytes after its own. When the
  destination is not in that queue, the zero link sends the search on through the ROM longwords at
  `0x10` and `0x944`, and the next read is a longword at `0x00090019`, a CPU address error. The
  error handler returns, and what that read leaves is not defined.
- For the last four heads (IDs 1, 13, 9 and 14) the slot 16 bytes on is past the ready heads, in
  the first four longwords of the disc extension's collection state, `0x0f000208..0x0f000217`
  ([extensions](extensions.md#names)). The search reads the longword at `0x0f000208`,
  `0x0f00020c`, `0x0f000210` or `0x0f000214`, in that order, as the first record. While it is 0
  the search goes on as above. A nonzero one is followed as a record address: an unaligned value
  faults at the next read, and an aligned one sends the search through whatever memory it points
  to.
- All four are 0 after reset, and on a disc that follows the standard they stay 0, so these heads
  behave like the others. The header scan copies the extension's disc address and length into
  `0x0f00020c` and `0x0f000210` from every Saturn header it finds, even when the disc then fails.
  Preparing a disc extension, after the disc is accepted, sets `0x0f000208`, the sector count in
  its top byte, and `0x0f000214`, the collection pointer that collection then advances. Only a
  reset clears those two.

### Post and raise

`TRAPA 0x22` posts a message and puts the destination in the ready queue its class byte names, so
the woken task runs at another task's priority once.

- `TRAPA 0x22` enters `message_post_priority` (`0x0fb8`). It posts r11 through the mailbox routine
  and returns r0 = -1 when that fails.
- A destination in state 1 or 4 is taken out of the queue its `+6` names, if any, and appended to
  the head its class byte names: bit 7 the first head, otherwise the head of the task whose ID is
  the class byte. `+6` records that queue until dispatch clears it. r0 returns the offset written
  to `+6`: the class byte times 4, or `0xffffff80` for bit 7.
- A destination in another state keeps its place and r0 returns its state.
- The class byte of an ordinary message is the sender's ID, so the woken task runs at the sender's
  priority. A class byte naming a task without a ready head (3, 10 and 11) is not checked.

## Locks

In effect each lock is a mutex with a queue of waiting tasks. The lock is a byte in a record, taken
with `TAS.B`.

- `TRAPA 0x2a` enters acquire at `trap_lock_acquire` (`0x12d2`) and `TRAPA 0x27` enters release at
  `trap_lock_release` (`0x1250`).
- r11 names the lock: bits 31..24 index the record table, bits 23..16 are the owner token and bits
  15..0 are ignored.
- The sector lock is record 11 at `0x0f000168`. ROM code in six tasks takes it, each task with its
  own ID as the owner:
  - Task 4's buffer settings, `0x0b040000`.
  - Sector completion in task 5, `0x0b050000`.
  - Task 7's sector and header code and extension collection, `0x0b070000`.
  - Task 9's [Get MPEG ROM](extensions.md#get-mpeg-rom), `0x0b090000`.
  - Task 12's [data transfers](data-transfer.md), `0x0b0c0000`.
  - Task 13's sector copies and moves, `0x0b0d0000`.
- The known cards' code also takes it as task 8 and task 9 ([card firmware
  interface](../mpeg-card/sh1-code.md#firmware-interface)).
- The transfer lock is record 3 at `0x0f000048`. Tasks 2, 6, 7 and 12 take it around a transfer to
  or from the host, as `03020000`, `03060000`, `03070000` and `030c0000`
  ([data transfer](data-transfer.md)).
- Record `+2` is the lock byte, `+3` the owner and `+12` the waiter link. Acquire succeeds only when
  the whole lock byte is zero.
- Both handlers set SR to `0x60` (mask 6, which can lower a higher incoming mask). Uncontended
  paths return r0 = 0 through RTE, clobber r10, r12 and r13, and preserve r1..r9, r11, r14 and the
  other special registers.

### Contention

- A busy acquire appends the current record to the waiter chain and calls selection
  `task_select_ready` (`0x10a8`). Its continuation at `lock_wait_suspend` (`0x1316`) marks the
  waiter state 6, saves its exception SP and branches to dispatch `task_dispatch` (`0x1118`).
- The waiter later resumes with only PC and SR restored, not its general registers or PR. Callers
  must tolerate that. Two of task 7's releases in disc authentication do not
  ([a contended sector lock](disc-authentication.md#a-contended-sector-lock)).
- Release with no waiter clears the owner, then the lock in the RTE delay slot. With a waiter it
  transfers ownership, appends the waiter to its ready queue, saves an 80-byte context (exception
  PC/SR, r0..r13, PR, GBR, MACH, MACL, not r14) and branches to `task_requeue_current` (`0x102e`).

### Owner checks

- Acquire compares the signed stored owner with the unsigned token, while release compares low bytes
  only, so owner bytes `0x80..0xff` behave differently in each.
- When a busy lock's stored owner equals the token, acquire raises the diagnostic trap with r0 10.
  Releasing with the wrong owner raises it with r0 1.
- Indices, pointers and chains are not validated.

### Lock attempt

- `TRAPA 0x26` enters `trap_lock_try` (`0x121e`) and names the lock in r11 as `TRAPA 0x2a` does.
  `TAS.B` sets the lock byte. When it was clear the owner token is stored and r0 returns 0.
- A held lock returns r0 = 0 when its owner byte equals the token and -1 otherwise, and changes
  nothing. Unlike the blocking acquire, the same owner is not a diagnostic.
- The stored owner is sign-extended and the token zero-extended, so owners `0x80..0xff` never
  match.

## Timers

Up to four software timers share ITU channel 4. When one expires, its identifier is posted as a
message, so a timer is a delayed message.

- The table at `0x0f000220` holds four eight-byte entries (identifier, deadline), ordered by
  deadline ([SH7034 notes](../sh7034.md#itu-channel-4)).
- Time is the time high part shifted left 8, plus TCNT4 bits 15..8. Startup sets TCR4 to 3 (internal
  clock φ/8), TIER4 to 4 (overflow interrupt) and IPRD to `0x6666`, so ITU4's interrupts have
  priority 6, and starts channel 4.
- At the 20 MHz clock one time unit is 256 counts, 102.4 µs. Durations subtract r10 * 6 / 256,
  which makes r10 count 100 µs steps. The disc authentication timeout of 200,000 is 20 seconds.

| Routine | Entry | Role |
| --- | --- | --- |
| Overflow | `timer_overflow` (`0x1c70`), vector 98 (ROM longword `0x0188`) | Clears OVF and increments the time high part |
| Start | `timer_start` (`0x1d96`), `TRAPA 0x24` | Inserts timer r11 with duration r10 |
| Cancel | `timer_cancel` (`0x1e46`), `TRAPA 0x25` | Removes timer r11 |
| Expiry | `timer_expiry` (`0x1c90`), vector 96 (ROM longword `0x0180`) | Posts due timers |

### Start and cancel

- Start reads the time high part before and after TCNT4 until both reads match, sets SR `0x60` and
  adds r10 less r10 * 6 / 256 to the current time.
- It inserts the entry after any entry whose deadline is not later (signed difference). A new head
  writes GRA4 = deadline low byte << 8 | `0x7f`, clears IMFA and sets IMIEA.
- A full table raises the diagnostic trap with r0 9 and returns r0 = -1. Otherwise it returns 0.
- Cancel removes the r11 entry, moves later entries forward and returns r0 = 0, or -1 when no entry
  matches. Removing the head writes GRA4 from the next deadline, or clears IMIEA when the table
  becomes empty.
- Cancel does not touch the mailboxes. A message the timer posted before the cancel stays in its
  slot ([a timer expiry left behind](disc-authentication.md#a-timer-expiry-left-behind)).

### Expiry

GRA4 can only hold the low part of a deadline, so the compare-match handler fires once per overflow
period until the high part is due as well.

- The handler clears IMFA and takes the time as the time high part << 8 plus GRA4 bits 15..8. While
  the first deadline is still ahead it returns with RTE.
- Once due, it saves the interrupted context in its task record, switches to the handler stack,
  posts the identifier with `TRAPA 0x21` and moves the table forward. Further due entries are posted
  the same way.
- The next deadline then programs GRA4, or an empty table clears IMIEA, and the scheduler continues
  at `task_requeue_current` (`0x102e`).
- Task 7 uses identifier `07070000` for the [disc authentication](disc-authentication.md#timeout)
  timeout. Task 6 uses `06060000` for the drive's [standby timer](drive.md#standby-timer).
