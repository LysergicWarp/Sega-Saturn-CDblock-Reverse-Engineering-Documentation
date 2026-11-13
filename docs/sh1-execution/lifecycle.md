# Card extension lifecycle

What the firmware does to a loaded card extension at each event, and what the host sends to use it
again. The card bit opens the MPEG commands and task 9's card work loop
([card activation](../cdblock/extensions.md#card-activation)).

| Event | Card bit | The extension | To use it again |
| --- | --- | --- | --- |
| `E0` subcode 1, the checks and the load pass | Clear | Decoded, its entry called | `93` with bit 0 |
| `E0` subcode 1, the checks or the load fail | Clear | Cleared, with the MPEG version | `E0` subcode 1, then `93` |
| `93` with bit 0, card off | Set | Entry 34 called | Nothing |
| `93` with bit 0, card on | Set | Reset, then entry 34 called again | Nothing |
| `93` with bit 0 clear | Clear | Kept | `93` with bit 0 |
| `04` with the reset bit | Clear | Kept, with the MPEG version. Work in task 9 is abandoned | `93` with bit 0 |
| `E0` subcode 1 after a stop | Clear | Decoded again over the old one | `93` with bit 0 |
| A disc accepted | Clear | Cleared, with the MPEG version and card status | `E0` subcode 1, then `93` |
| A CD-block reset: power-on, SYSRES, or CDOFF then CDON | Clear | Forgotten: startup clears the MPEG version | The disc checked again, then `E0` subcode 1 and `93` |

- `E0` of any subcode is rejected while the card bit is set, so a disc is checked with the card
  off. Data reads need the [delivery gate](../cdblock/disc-authentication.md#delivery-gate) the
  disc check opens. A game therefore checks the disc first, then loads and activates the card, and
  loads it again after a later accepted disc.
- `04`'s [restart](../cdblock/kernel.md#restart) disables the interrupts from the card's lines and
  runs task 8's setup again, which clears the MPEG state and the card bit with it.
- Task 9 also starts afresh, so a job it was running never finishes. An extension that keeps job
  state should reset it at activation.
- `93` clears the card work loop's request bytes but does not interrupt a call that task 9 is
  running. Task 9 writes the stop's MPED only after that call returns. Until then an accepted disc
  can clear the expansion area under the call, and another activation can clear MPEG state it
  still uses.
- A reset restarts the SH-1 and the drive from ROM ([board](../board.md#clock-reset-and-mode)).
  The authentication result and the [delivery gate](../cdblock/disc-authentication.md#delivery-gate)
  start at 0, so the order after a reset is the one at power-on: the disc first, then the card.
- `01` reports a nonzero MPEG version while an extension is loaded. After `93` the extension's own
  commands can identify it.
- A reload decodes only as many bytes as the extension's code, so code or data the extension
  placed after its image stays until a disc is accepted or a card load fails. A record the
  extension keeps in its image is reset with it.

[lifecycle-extension.s][emulator-lifecycle-extension.s] is a minimal extension that goes through
this lifecycle. `AD` answers its identity and activation count, `AB` submits a job that task 9 runs
and `AC` reports it. [decompress-extension.s][emulator-decompress-extension.s] runs a longer job a
sector per call, which `93` ends between calls. [module-extension.s][emulator-module-extension.s]
keeps an uploaded module installed through `93` and `04`, and forgets it at a reload. The
[emulator's examples][emulator-examples] run them after a build of the emulator, with SH binutils to
assemble them and your dump in its `dumps/` folder, and say what they have run on and what turning
one into card firmware takes.

[emulator-decompress-extension.s]: https://github.com/LysergicWarp/Sega-Saturn-CDB-Emulator/blob/main/examples/decompress-extension.s
[emulator-examples]: https://github.com/LysergicWarp/Sega-Saturn-CDB-Emulator/tree/main/examples
[emulator-lifecycle-extension.s]: https://github.com/LysergicWarp/Sega-Saturn-CDB-Emulator/blob/main/examples/lifecycle-extension.s
[emulator-module-extension.s]: https://github.com/LysergicWarp/Sega-Saturn-CDB-Emulator/blob/main/examples/module-extension.s
