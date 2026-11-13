# Board

How the SH-1 connects to the rest of the CD block: its memory areas, clock and reset, the interface
chip, the optical drive, the audio output, the main board and MPEG card connectors and the test
pads. The wiring is the SH-1 board in Sega's Saturn PAL
service manual, with the SH-1 and a YGR019A interface chip as separate parts
([Schematic Diagram-7][SM], "SH-1 C.B", printed pages 25-26). YGR022 combines the two chips, so on
those boards the interface signals are internal. Pin numbers are the SH-1's 112-pin package
([SH7034 notes](sh7034.md)), and signal names are the schematic's.

## Parts

| Part | Role |
| --- | --- |
| IC101 `HD6437097` | The SH-1, an SH7034 with the firmware in mask ROM, clocked by a 20 MHz crystal |
| IC103 `YGR019A` | The interface chip: host registers, the drive's data and subcode streams, the host transfer register and the bus to the MPEG card |
| IC102 `HM514260` | The 512 KB buffer DRAM, 256K by 16 bits |
| E101 | Connector to the main board: the A-bus, digital CD audio, the MPEG card's video lines and `DEMP` |
| E102 | The 20-pin optical drive connector |
| E103 | The MPEG card connector |
| X101 | The SH-1's 20 MHz crystal |

## Memory areas

The SH-1 divides its address space into eight areas, each with its own chip select. The board
wires three of them to outside parts. The others hold memory inside the SH-1 or have their chip
select pin used for another function.

| Area | Addresses the firmware uses | On this board |
| --- | --- | --- |
| 0 | `0x00000000..0x0000ffff` | The mask ROM inside the SH-1. The mode pins select on-chip ROM ([clock, reset and mode](#clock-reset-and-mode)), and CS0 (pin 48) is not connected |
| 1 | `0x09000000..0x0907ffff` | The buffer DRAM, on RAS (pin 54, PA1), CASH (pin 49, the CS1 pin) and CASL (pin 51, the CS3 pin) |
| 2 | `0x0a000000` and up | The interface chip, selected by CS2 (pin 50) on its `SCS2` input (pin 75). Its registers start at `0x0a000000` ([interface registers](#interface-registers)), and the MPEG card's registers from `0x0a100000` ([MPEG card](#mpeg-card)) |
| 3 | None | No device. The CS3 pin is CASL |
| 4 | None | No device. The CS4 pin is PA0, used as TIOCA0 |
| 5 | `0x05fffe00..0x05ffffff` | The SH-1's own peripheral registers. The CS5 pin is PA1, used as RAS |
| 6 | `0x0e000000` and up | CS6 (pin 55, PA2) as `SCS6`, to the interface chip (pin 42) and the MPEG card connector (E103 A31) |
| 7 | `0x0f000000..0x0f000fff` | The SH-1's 4 KB of on-chip RAM. The CS7 pin is PA3, an input the schematic ties high ([test pads and other pins](#test-pads-and-other-pins)) |

- The address pins A0..A21 drive the board's `SA0..SA21` lines and the data pins D0..D15 the
  `SDH0..SDH15` bus, which the DRAM and the interface chip share.

## Clock, reset and mode

| SH-1 pin | Function | Connection |
| --- | --- | --- |
| 73, 74 | EXTAL, XTAL | X101, 20 MHz, with C103 and C104 (10 pF) to ground |
| 71 | CK | The interface chip's clock input `SHCK` (pin 72) |
| 79 | RES | `RESET` from the main board on E101 B3, also on the drive connector as E102 pin 1. R109 2.2K pull-up |
| 80, 81, 82 | MD0, MD1, MD2 | MD1 high, MD0 and MD2 grounded: mode 010, on-chip ROM |
| 76 | NMI | Tied high |
| 78 | WDTOVF | Not connected |

- One line from the main board resets the SH-1 and the drive together. PA7 then holds the interface
  chip in reset until startup releases it ([firmware pin setup](#firmware-pin-setup)).
- That line is `CDRES` from the SMPC (IC9 pin 3, port R72), also the MPEG card's `RESET` (E103 B30)
  ([service manual][SM]). Power-on and SYSRES hold it low for about 0.1 s, CDOFF holds it low until
  CDON, and the clock change and the reset button leave it alone.

## Interrupts

The interface chip drives both external interrupts the firmware uses.

| Input | SH-1 pin | Signal | Interface pin | Raised when |
| --- | --- | --- | --- | --- |
| IRQ6 | 1, PB14 | `IRQ L` | 113, `SIRQL` | The host writes CR4 |
| IRQ7 | 2, PB15 | `IRQ H` | 111, `SIRQH` | The drive's data stream reaches a sector header, or its subcode stream a new frame |

The interface sets a flag for each event and holds the line asserted while an enabled flag is set.
Both inputs are level-sensed (ICR is 0). Emulators that run the firmware model these registers the
same way ([Ymir][YMIR-YGR], [Yabause][YAB-YGR]), and the firmware's accesses agree with them.

| Register | Contents |
| --- | --- |
| `0x0a000004` | Bit 0 set when the host writes CR4, bit 1 set when the host reads the fourth response word. The IRQ6 handler writes 0 at entry ([IRQ6 entry](cdblock/host-commands.md#irq6-entry)), and the periodic status writes a new status only while bit 1 is set ([periodic status](cdblock/drive.md#periodic-status)) |
| `0x0a000008` | Enables for those two bits. Task 14 writes `0x0001`, so only a command raises IRQ6 |
| `0x0a000006` | Bit 4 the sector header, bit 5 a subcode frame, bit 6 with it the start of a subcode block ([subcode](cdblock/subcode.md#frames)). A write clears the bits written as 0, as the pulse handler's `0xffef` clears bit 4 ([sector pulse](cdblock/sector-reads.md#sector-pulse)) |
| `0x0a00000a` | Enables for those three bits |

## DMA requests

The interface chip requests DMA channels 0 and 1.

| Channel | SH-1 pins | Serves |
| --- | --- | --- |
| 0 | DREQ0 67 (PA13), DACK0 66 (PA12) | Sector data from the interface into the buffer ([DMA channel 0](cdblock/sector-reads.md#dma-channel-0)) |
| 1 | DREQ1 69 (PA15), DACK1 68 (PA14) | Host data transfers through the data port `0x0a000000` ([data transfer](cdblock/data-transfer.md)) |

- Ymir models the transfer control `0x0a000002` with bit 0 the direction (1 from the host), bit 1
  a FIFO reset and bit 2 the transfer enable. Bit 3 is unknown. The firmware writes 2 and then 0
  before arming channel 1 and 4 after arming it, each with the direction bit. It writes 8 at the
  end, with the direction bit at the channel's end and for a transfer that finds no sector, and
  without it when `06` ends the transfer.
- Ymir models a six-word FIFO, which matches the six leftover words that `06` copies by hand
  ([ending a transfer](cdblock/data-transfer.md#ending-a-transfer)).
- Ymir models bit 7 of `0x0a00001a` as set by the interface when it finds a sector header, and as
  the gate for DREQ0. The firmware clears it before each sector transfer.

## Interface registers

The firmware reaches the interface chip through word registers from `0x0a000000`. Each is
described where the firmware uses it.

| Register | Use | Described in |
| --- | --- | --- |
| `0x0a000000` | Data port, channel 1's device address and the words `06` copies by hand | [Data transfer](cdblock/data-transfer.md#names) |
| `0x0a000002` | Transfer control | [DMA requests](#dma-requests) |
| `0x0a000004`, `0x0a000008` | Command flags and their enables | [Interrupts](#interrupts) |
| `0x0a000006`, `0x0a00000a` | Sector header and subcode flags and their enables | [Interrupts](#interrupts) |
| `0x0a00000c` | Written 3 by the interface setup `startup_interface_setup` (`0x07e0`), the transfer reset `startup_transfer_state` (`0x2388`), entry 58 `mpeg_video_channel_stop` (`0xb95c`) and task 9's payload 0 `task9_mpeg_stop` (`0xbbc6`). In the card's version 1 code, entries 51 (`0x0907b1c0`) and 58 (`0x0907d8d2`) write 3, and entries 51, 46 (`0x0907bce2`) and 74 (`0x0907d1e4`) and the routine at `0x0907d85a` write 8 as they start DMA channel 2 with video data | Unknown |
| `0x0a000010..0x0a000017` | CR1..CR4, command in and response out | [Host commands](cdblock/host-commands.md#names) |
| `0x0a000018` | Subcode symbol word, a subcode frame's R-W symbol | [Subcode](cdblock/subcode.md#names) |
| `0x0a00001a` | Decoder control | [Sector reads](cdblock/sector-reads.md#names) |
| `0x0a00001c` | Decoder status, read for each sector | [Sector reads](cdblock/sector-reads.md#names) |
| `0x0a00001e` | The host's interrupt flags, HIRQREQ | [Interrupt flags](cdblock/host-commands.md#interrupt-flags) |

- Ymir keeps the two low bits of `0x0a00000c`, so it drops the card's 8, and neither emulator gives
  the register a function ([references](references.md#interface-chip-emulation)).
- Also without a known function: bit 3 of `0x0a000002`, and bits 8 and 12 of `0x0a00001a`, which
  CDB106 sets on boards with the 20-pin drive ([drive strap](firmware-revisions.md#drive-strap)).

## Optical drive

The drive link runs on SCI0 and two port pins to the drive connector. The service manual's board wires
them straight, VA8 puts series resistors on the two outputs
([21-pin drive connector](#21-pin-drive-connector)). `CDATA`, `COMREQ` and `COMSYNC` have 4.7K
pull-ups.

| SH-1 pin | Function | Signal | Direction | Firmware use ([link](cdblock/drive.md#link)) |
| --- | --- | --- | --- | --- |
| 111, PB12 | SCK0 | `COMCLK` | Out | Serial clock |
| 108, PB9 | TxD0 | `HDATA` | Out | Command bytes |
| 107, PB8 | RxD0 | `CDATA` | In | Report bytes |
| 101, PB3 | TIOCB3 | `COMREQ` | In | Byte strobe |
| 100, PB2 | PB2 | `COMSYNC` | In | Frame start |

| E102 pin | Signal | E102 pin | Signal |
| --- | --- | --- | --- |
| 1 | `RESET` | 11 | `DAS` |
| 2 | GND | 12 | `CKX` |
| 3 | `CDATA` | 13 | `MPX` |
| 4 | `HDATA` | 14 | GND |
| 5 | `COMREQ` | 15 | `C2F` |
| 6 | `COMCLK` | 16 | `SMPX` |
| 7 | `COMSYNC` | 17 | `SCKX` |
| 8 | GND | 18 | `SDAS` |
| 9 | `MCK` | 19 | GND |
| 10 | GND | 20 | `ACCESS` |

- `DAS`, `CKX`, `MPX` and `C2F` carry the drive's data stream, and `SDAS`, `SCKX` and `SMPX` its
  subcode stream. They go to the interface chip, not to the SH-1.
- Pin 1 `RESET` is the board reset that also drives the SH-1's RES
  ([clock, reset and mode](#clock-reset-and-mode)).
- Boards that take a 21-pin drive use a different connector, which the manual does not show
  ([21-pin drive connector](#21-pin-drive-connector)).

### Drive generations

Four drive types are in use across the main board revisions ([GDEMU][GDEMU]). Each drive has its
own controller, which takes the SH-1's commands and runs the mechanism. No dump of any
controller's firmware is known.

| Type | Main boards | Cable | Drive controller | Drives |
| --- | --- | --- | --- | --- |
| 1 | VA0, VA1 | 20-pin | Hitachi H8 `HD6433712H`, program `CDM103V` ([SegaXtreme][SX-H8]) | JVC ENR-007B/D, Hitachi JA0027 |
| 2 | VA2..VA5 | 21-pin | 64-pin Hitachi H8 `HD6433612H`, program `CDM202V` | JVC ENR-011A |
| 3 | VA6..VA9 | 21-pin | 32-pin Mitsubishi `M37477M8-241FP`, program `CDM301V` | JVC ENR-013A, Sanyo 610-6185-20/-30 |
| 4 | VA10..VA15 | 21-pin | 32-pin, program `CDM301V` ([TriMesh][TM-PINS]) | JVC HQA-001A, Sanyo 610-6294-30, 610-6473-30 |

- The `HD6433612H` is a Hitachi H8/3612, an H8/300L single-chip MCU with 16 KB of mask ROM at
  `0x0000..0x3fff` and 512 B of RAM (Hitachi H8/3614 Series Hardware Manual).
- The `M37477M8` is a Mitsubishi 740-family (6502-derived) single-chip MCU with 16 KB of mask ROM
  at `0xc000..0xffff` and no external bus (Mitsubishi 7477/7478 Group data sheet, Rev. 1.0,
  December 1997).
- The rest of the type 3 and 4 drive board: `MN662724` servo and signal processor, `AN8809` RF
  amplifier, `M56754SP` actuator and motor driver ([TriMesh][TM-PINS]).

### 21-pin drive connector

The 21-pin pinout is from one JVC HQA-001A drive on a VA11 board ([TriMesh][TM-PINS]). No
schematic is published. Pin numbers are the drive's CN102, which match the numbers printed at the
ends of the main board's socket. The last column matches each line to the 20-pin signal with the
same job.

| Pin | Signal | Drive side | 20-pin signal |
| --- | --- | --- | --- |
| 1 | 33 MHz clock from the main board | DSP pin 58, through a capacitor | `MCK` |
| 2, 12, 16 | Ground | | |
| 3 | Drive status | Controller pin 3 | `CDATA` |
| 4 | Drive commands | Controller pin 4 | `HDATA` |
| 5 | Byte sync, one pulse per byte | Controller pin 1 | `COMREQ` |
| 6 | Frame signal, at the CD frame rate during play and 60 Hz when idle | Controller pin 5 | `COMSYNC` |
| 7 | Bit clock | Controller pin 2 | `COMCLK` |
| 8 | Ground on JVC drives. The main board reads it: ground selects 33 MHz, open 16 MHz | | |
| 9, 14 | `BCLK`, joined on the drive | DSP pin 1 | Data stream |
| 10 | `BLKCLK`, high at the start of each subcode block (75 Hz at 1x) | DSP pin 13 | Subcode stream |
| 11 | `/RESET` | Controller pin 18 | `RESET` |
| 13 | `LRCLK` | DSP pin 2 | Data stream |
| 15 | `DATA`, CD-ROM and digital audio | DSP pin 3 | Data stream |
| 17 | `/CD-ROM`, high with audio | Controller pin 25 | |
| 18 | `SUBC`, subcode out | DSP pin 55 | Subcode stream |
| 19 | `SBCK`, subcode clock | DSP pin 56 | Subcode stream |
| 20 | `IPFLG`, high on a C2 error | DSP pin 64 | `C2F` |
| 21 | `/CLDCLK`, subcode frame clock | DSP pin 62 | Subcode stream |

- A VA8 board wires the link the same way. SH-1 pins 111, 108, 107, 101 and 100 reach pins 7, 4,
  3, 5 and 6, and the board reset reaches pin 11. `COMCLK` and `HDATA` pass through series
  resistors of about 300 Ω, the other lines connect directly. Pins 2, 8, 12 and 16 are ground, and
  `PC0` (pin 87) is grounded, the 21-pin drive strap.
- On the `M37477M8` the five link pins are its clock-synchronous serial I/O and a timer output:
  pin 1 `SRDY`, pin 2 `SCLK`, pin 3 `TxD`, pin 4 `RxD` and pin 5 `T1`. The SH-1 drives `COMCLK`
  from SCK0, so the controller's serial I/O runs on that external clock and signals each byte with
  `SRDY`.
- The drive's power connector CN103 carries +5 V for the motor driver's output stage, +5 V for the
  rest of the board, a ground for each, and the lid switch to controller pin 30 (low when closed).

## Audio

- PB6 (pin 104) is `DEMP`, the de-emphasis output. It leaves on pin A4 of E101 and reaches the main
  board as `DEEM`. The schematic takes it through jumper R157 to pin 13 of the TDA1386T audio DAC,
  labeled `APP3`, with a 4.7K pull-down, and draws a second, buffered path through two inverters
  of a 74VHC04 whose resistors it marks not used ([Schematic Diagram-5][SM], printed page 21). The
  main board's parts list marks R157 not used as well (printed page 76), so as listed nothing
  connects `DEEM` to the DAC.
- The firmware sets PB6 from the pre-emphasis bit of the current track
  ([periodic status](cdblock/drive.md#periodic-status)).
- The interface chip sends the digital CD audio to the main board on `BCK`, `SD` and `LRCK`, where
  it feeds the sound chip.

## Main board connector

E101 (`CL576`, 100 pins) links the CD block to the main board. It carries the A-bus through which
the host reaches the interface chip (`AD0..AD15`, address lines, `ACS2`, strobes, `AWAIT` and
`AIRQ`), the digital audio and `DEMP`, the MPEG card's video (`MVR`, `MVG`, `MVB`, sync and pixel
clock), clocks and the board reset.

| Pin | Side A | Side B |
| --- | --- | --- |
| 1 | GND | GND |
| 2 | VCC | VCC |
| 3 | GND | `RESET` |
| 4 | `DEMP` | GND |
| 5 | `BCK` | `MCK` |
| 6 | `SD` | `ACCESS` |
| 7 | `LRCK` | `SNDCLK` |
| 8 | GND | GND |
| 9 | `ATIM0` | `ATIM2` |
| 10 | GND | GND |
| 11 | None | `ARD` |
| 12 | `AWRL` | `AFC0` |
| 13 | `AFC1` | `AWRU` |
| 14 | `AIRQ` | `AWAIT` |
| 15 | `AD1` | `AD0` |
| 16 | GND | GND |
| 17 | `AD3` | `AD2` |
| 18 | `AD5` | `AD4` |
| 19 | `AD7` | `AD6` |
| 20 | `AD9` | `AD8` |
| 21 | VCC | VCC |
| 22 | GND | GND |
| 23 | `AD11` | `AD10` |
| 24 | `AD13` | `AD12` |
| 25 | `AD15` | `AD14` |
| 26 | GND | GND |
| 27 | `AA3` | `AA2` |
| 28 | `AA5` | `AA4` |
| 29 | `AA13` | `AA12` |
| 30 | `ACS2` | `AA14` |
| 31 | GND | GND |
| 32 | `MVR2` (see below) | `MVR7` |
| 33 | `MVR4` | `MVR5` |
| 34 | `MVR2` | `MVR3` |
| 35 | `MVR0` | `MVR1` |
| 36 | `MVG6` | `MVG7` |
| 37 | `MVG4` | `MVG5` |
| 38 | `MVG2` | `MVG3` |
| 39 | `MVG0` | `MVG1` |
| 40 | `MVB6` | `MVB7` |
| 41 | `MVB4` | `MVB5` |
| 42 | `MVB2` | `MVB3` |
| 43 | `MVB0` | `MVB1` |
| 44 | `MVPRT` | GND |
| 45 | `DTCLK` | `VOF` |
| 46 | `VSYNC` | `HSYNC` |
| 47 | VCC | VCC |
| 48 | VCC | VCC |
| 49 | GND | GND |
| 50 | GND | GND |

- A32 is printed `MVR2`, the same as A34. `MVR6` is missing from the sequence here and present on
  the card connector.
- B45 is printed `VOF`. The card connector has `VOE` beside its sync lines (E103 B47).
- B3 `RESET` is the board reset ([clock, reset and mode](#clock-reset-and-mode)).

## MPEG card

E103 (`N630`, 100 pins) carries the card's bus: the address lines `SA0..SA18` from the SH-1, the
interface chip's second data bus `SDL0..SDL15`, the strobes `SRD` and `SWRL` and the selects `SCS6`
and `MACS`. It also carries the card's audio and video to the main board, the reset, and four SH-1
inputs, whose roles the service manual gives ([SH1 board IC101][SM], printed page 64).

| SH-1 pin | Function | Signal | Role |
| --- | --- | --- | --- |
| 97, PB0 | TIOCA2 | `MPEG A IRQ` | MPEG audio interrupt, 10K pull-up |
| 98, PB1 | TIOCB2 | `MPEG V IRQ` | MPEG video interrupt, 10K pull-up |
| 53, PA0 | TIOCA0 | `TIOCA0` | MPEG audio data request, 10K pull-up |
| 64, PA10 | TIOCA1 | `TIOCA1` | MPEG video data request, 10K pull-up |

- Task 9's card checks use TIOCA1 and TIOCA0 as DMA requests. Each falling edge moves one word to
  the card, on channel 2 to `0x0a10001e` or on channel 3 to `0x0a180000`
  ([card checks](cdblock/extensions.md#card-checks)).
- The firmware reads the card extension from `0x0e000000`, through CS6
  ([expansion extension loader](cdblock/extensions.md#expansion-extension-loader)), and `E2` copies
  the rest of the card ROM from `0x0e005000` ([Get MPEG ROM](cdblock/extensions.md#get-mpeg-rom)).
- The connector carries the address lines only up to `SA18`, 512 KB. The card cannot tell apart
  addresses that differ above that, so its 512 KB ROM repeats every 512 KB from `0x0e000000`.
- Yabause sends SH-1 accesses from `0x0a100000` on to the card's registers. The startup card test
  sets up windows at `0x0a100000` and `0x0a180000`
  ([reset and startup](cdblock/structure.md#reset-and-startup)), and task 8 writes `0x0a10001a`
  ([MPEG task](cdblock/structure.md#mpeg-task)).

| Pin | Side A | Side B |
| --- | --- | --- |
| 1 | GND | GND |
| 2 | `TIOCA1` | `MPEG A IRQ` |
| 3 | `SRD` | `MPEG V IRQ` |
| 4 | `TIOCA0` | `SWRL` |
| 5 | GND | GND |
| 6 | `SA18` | `SA17` |
| 7 | `SA16` | `SA15` |
| 8 | `SA14` | `SA13` |
| 9 | `SA12` | `SA11` |
| 10 | `SA10` | `SA9` |
| 11 | `SA8` | `SA7` |
| 12 | `SA6` | `SA5` |
| 13 | `SA4` | `SA3` |
| 14 | `SA2` | `SA1` |
| 15 | `SA0` | GND |
| 16 | GND | GND |
| 17 | `SDL15` | `SDL14` |
| 18 | `SDL13` | `SDL12` |
| 19 | `SDL11` | `SDL10` |
| 20 | `SDL9` | `SDL8` |
| 21 | `SDL7` | `SDL6` |
| 22 | `SDL5` | `SDL4` |
| 23 | `SDL3` | `SDL2` |
| 24 | `SDL1` | `SDL0` |
| 25 | GND | GND |
| 26 | `MALRCLK` | `SNDCLK` |
| 27 | `MABICK` | `MASDATAI` |
| 28 | VCCA | VCCA |
| 29 | GND | GND |
| 30 | `MACS` | `RESET` |
| 31 | `SCS6` | GND |
| 32 | `WTRS` | `FDACK` |
| 33 | GND | GND |
| 34 | `MVCS` | `MVR7` |
| 35 | `MVR6` | `MVR5` |
| 36 | `MVR4` | `MVR3` |
| 37 | `MVR2` | `MVR1` |
| 38 | `MVR0` | `MVG7` |
| 39 | `MVG6` | `MVG5` |
| 40 | `MVG4` | `MVG3` |
| 41 | `MVG2` | `MVG1` |
| 42 | `MVG0` | `MVB7` |
| 43 | `MVB6` | `MVB5` |
| 44 | `MVB4` | `MVB3` |
| 45 | `MVB2` | `MVB1` |
| 46 | `MVB0` | `MVPRT` |
| 47 | `DTCLK` | `VOE` |
| 48 | `HSYNC` | `VSYNC` |
| 49 | VCCA | VCCA |
| 50 | GND | GND |

## Test pads and other pins

| SH-1 pin | Function | Signal | Connection |
| --- | --- | --- | --- |
| 109, PB10 | Input, also RxD1 | `TEST` | TP3, 4.7K pull-up |
| 110, PB11 | TxD1 | `TEST DATA` | TP2 |
| 112, PB13 | SCK1 | `TCLK` | TP1 |
| 60, PA7 | Output | `RESET` | Reset of the interface chip, and TP5 |
| 63, PA9 | Output | `IRQOUT` | Not connected, its pull-up is not fitted |
| 87..90, 92..95 | PC0..PC7 | `VCD` on PC5 | Tied to ground |
| 56, PA3 | Input | | Tied to VCC on the schematic, with C105 to ground. The IC101 table, and the schematic's pin label, give it as not connected |
| 48, 62, 65, 102, 103, 105 | CS0, PA8, PA11, PB4, PB5, PB7 | | Not connected |

- Reset reads PB10 as bit 2 of the byte at `0x05ffffc2`. High selects normal startup, and TP3
  grounded at reset selects the diagnostic and serial monitor path
  ([reset and startup](cdblock/structure.md#reset-and-startup)).
- On that path TP2 and TP1 first carry the diagnostic report: two bytes from SCI1 in clocked
  synchronous mode, TP1 the clock, at 50,000 bit/s (BRR1 99 at 20 MHz). Once TP3 reads high again,
  the monitor runs asynchronous 8N1 at about 9600 bps (BRR1 `0x41`, 9470 bps), sending on TP2 and
  receiving on TP3, since PB10 becomes RxD1 ([serial monitor](cdblock/structure.md#serial-monitor)).
- TP4 is ground and TP6 the `WRL` strobe.
- CDB106 boards with a 20-pin drive tie PC0 high instead ([drive strap](firmware-revisions.md#drive-strap)).
- The service manual names pin 63 `IRQOUT`, a spare that goes low during interrupt processing
  ([SH1 board IC101][SM], printed page 64). The firmware sets PA9 up as a port output instead,
  PACR1 mode 00 ([firmware pin setup](#firmware-pin-setup)).
- PC5 (`VCD`) is an input that tells whether a VCD is connected, low for a CD drive and high for a
  VCD ([SH1 board IC101][SM], printed page 64). No firmware revision reads it. CDB104 and CDB105
  read no Port C pin, and CDB106 and YGR022 read only PC0.

## Firmware pin setup

Startup programs the SH-1's pins to match this wiring. It writes the Port A and Port B data,
direction and function registers as longwords at `0x05d2..0x05de`, with GBR at `0x05ffff80`.

| Registers | Written at | Value | Effect |
| --- | --- | --- | --- |
| PADR, PBDR | `0x05d2` | `0xf67b`, `0x0000` | PA7 low, holding the interface chip in reset |
| PAIOR, PBIOR | `0x05d6` | `0x5bf6`, `0x3af0` | PA7 and PB4..PB7 outputs, PB6 (`DEMP`) among them. PB2, PB3 and PB10 inputs |
| PACR1, PACR2 | `0x05da` | `0xff22`, `0xbf1a` | DREQ1, DACK1, DREQ0 and DACK0 on PA15..PA12, TIOCA1 on PA10, RD, WRH and WRL on PA6..PA4, CS6 on PA2, RAS on PA1, TIOCA0 on PA0. PA7 and PA9 port pins |
| PBCR1, PBCR2 | `0x05de` | `0x5a8a`, `0x008a` | IRQ7 and IRQ6 on PB15 and PB14, SCK1 and SCK0 on PB13 and PB12, TxD1 on PB11, TxD0 and RxD0 on PB9 and PB8, TIOCB3 on PB3, TIOCB2 and TIOCA2 on PB1 and PB0. PB10, PB2 and PB4..PB7 port pins |

- The interface setup `startup_interface_setup` (`0x07e0`) sets PA7, releasing the interface chip,
  just before it writes the interface registers.
- The serial monitor path changes PB10 to RxD1 at `monitor_rxd1_select` (`0x0a60`), after the
  `TEST` input has returned high ([test pads](#test-pads-and-other-pins)).
- The mode values follow the SH7034 manual's PFC tables ([SH7034 notes](sh7034.md)).

[SM]: https://segaretro.org/images/4/4e/Sega_Service_Manual_-_Sega_Saturn_(PAL)_-_013-1_-_June_1995.pdf
[GDEMU]: https://gdemu.wordpress.com/details/saturn-details/
[SX-H8]: https://segaxtreme.net/threads/this-idea-a-had.5269/
[TM-PINS]: https://assemblergames.org/viewtopic.php?t=40345
[YMIR-YGR]: https://github.com/ymir-emu/Ymir/blob/main/libs/ymir-core/include/ymir/hw/cdblock/ygr.hpp
[YAB-YGR]: https://github.com/Yabause/yabause/blob/master/yabause/src/ygr.c
