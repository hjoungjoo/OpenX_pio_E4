# OnStepX Communication Protocol

Baseline: current working tree using the current OnStepX source and `Config.h`.

Korean version: `communication_protocol.md`

This document summarizes how OnStepX communicates with external programs, WiFi clients, Bluetooth SPP, ST4/SHC, and the internal command queue. The full command list is maintained in `COMMAND_REFERENCE.md`.

## Current Build Baseline

Important communication-related settings in the current configuration:

| Item | Current value | Meaning |
| --- | --- | --- |
| `PINMAP` | `MF_OOZOO_E4` | User board pinmap |
| `SERIAL_RADIO` | `WIFI_ACCESS_POINT` | ESP32 WiFi AP command channel enabled |
| `ST4_INTERFACE` | `ON` | ST4 physical input enabled |
| `ST4_HAND_CONTROL` | `ON` | SHC/hand-control function enabled on the ST4 port |
| `SERIAL_BT_MODE` | default `OFF` | Bluetooth SPP is off in the current default setup |
| `MOUNT_TYPE` | `ALTAZM_UNL` | Alt-Az unlimited mount |
| Axis1/Axis2 driver | `TMC2209` | Mount axes enabled |

`SERIAL_RADIO WIFI_ACCESS_POINT` expands through `Config.defaults.h` into `SERIAL_IP_MODE WIFI_ACCESS_POINT`, `WEB_SERVER ON`, `OPERATIONAL_MODE WIFI`, and `AP_ENABLED true`.

## Protocol Layers

OnStepX command communication separates physical channels from command parsing.

```mermaid
flowchart LR
  Client["External client"]
  Transport["Physical/virtual channel"]
  Wrapper["SerialWrapper"]
  Buffer["Buffer"]
  Processor["CommandProcessor"]
  Telescope["Telescope::command()"]
  Subsystem["Mount / Guide / Goto / Park / Site / Focuser / Features"]

  Client --> Transport --> Wrapper --> Buffer --> Processor --> Telescope --> Subsystem
```

Main implementation files:

| Role | File |
| --- | --- |
| Command-channel task creation/polling | `src/libApp/commands/ProcessCmds.cpp` |
| Command frame buffer/parser | `src/lib/commands/BufferCmds.cpp` |
| Channel abstraction | `src/lib/commands/SerialWrapper.cpp` |
| Command dispatch | `src/telescope/Telescope.command.cpp` |
| WiFi TCP serial stream | `src/lib/serial/Serial_IP_Wifi.cpp` |
| WiFi AP/STA management | `src/lib/wifi/WifiManager.cpp` |
| ST4/SHC detection and guide handling | `src/telescope/mount/st4/St4.cpp` |
| ST4 serial link | `src/lib/serial/Serial_ST4_Master.cpp` |
| Internal command queue | `src/lib/serial/Serial_Local.cpp`, `src/libApp/commands/CommandBroker.cpp` |

## Command Frames

Basic commands use LX200-style ASCII frames.

| Format | Description |
| --- | --- |
| `:CC...#` | Normal command frame |
| `;CC...CCS#` | Frame with checksum and sequence character |
| `0x06` | LX200 special status request |

The parser ignores spaces, LF, and CR. The internal command buffer is 80 bytes, and a command becomes ready when `#` is received.

### Command and Parameter Split

`Buffer::getCmd()` treats one or two characters after `:` or `;` as the command code. The rest is passed as the parameter string.

Examples:

| Original frame | Command | Parameter |
| --- | --- | --- |
| `:GVP#` | `GV` | `P` |
| `:Mn#` | `M` | `n` |
| `:SX9A,12.3#` | `SX` | `9A,12.3` |

## Checksum Frames

Checksum frames start with `;`. `Buffer::add()` verifies the final two checksum characters and one sequence character, then leaves only the command for processing.

On error, it internally takes the `:0x06 0#` checksum-failure response path, and `CommandProcessor` replies with `CK_FAIL`.

When the response also requires a checksum, `CommandProcessor::appendChecksum()` appends a two-digit hexadecimal byte sum, then the sequence character, then closes the frame with `#`.

## Reply Format

Command handlers have two basic reply modes.

| Mode | Behavior |
| --- | --- |
| Numeric reply | Success returns `1`, failure returns `0`; normally without `#` |
| String reply | Returns the response payload followed by `#` |

When command handling finishes with `numericReply == true`, `CE_NONE` or `CE_1` becomes `1`, and all other errors become `0`. Commands with string replies usually set `numericReply=false`.

The last command error can be queried with `:GE#`, returning a two-digit numeric string.

## Error Code Summary

Error codes are defined in `src/lib/commands/CommandErrors.h`.

| Code | Symbol | Meaning |
| --- | --- | --- |
| 00 | `CE_NONE` | No error |
| 01 | `CE_0` | Command was handled but false/fail |
| 02 | `CE_CMD_UNKNOWN` | Unknown command |
| 03 | `CE_REPLY_UNKNOWN` | Invalid reply |
| 04 | `CE_PARAM_RANGE` | Parameter out of range |
| 05 | `CE_PARAM_FORM` | Parameter format error |
| 06 | `CE_ALIGN_FAIL` | Alignment failed |
| 07 | `CE_ALIGN_NOT_ACTIVE` | Alignment is not active |
| 08 | `CE_NOT_PARKED_OR_AT_HOME` | Not parked or at home |
| 09 | `CE_PARKED` | Already parked |
| 10 | `CE_PARK_FAILED` | Park failed |
| 11 | `CE_NOT_PARKED` | Not parked |
| 12 | `CE_NO_PARK_POSITION_SET` | No park position set |
| 13 | `CE_GOTO_FAIL` | Goto failed |
| 14 | `CE_LIBRARY_FULL` | Library storage full |
| 15 | `CE_SLEW_ERR_BELOW_HORIZON` | Target is below horizon |
| 16 | `CE_SLEW_ERR_ABOVE_OVERHEAD` | Overhead limit exceeded |
| 17 | `CE_SLEW_ERR_IN_STANDBY` | Slew attempted in standby |
| 18 | `CE_SLEW_ERR_IN_PARK` | Slew attempted while parked |
| 19 | `CE_SLEW_IN_SLEW` | Already in goto/slew |
| 20 | `CE_SLEW_ERR_OUTSIDE_LIMITS` | Outside configured limits |
| 21 | `CE_SLEW_ERR_HARDWARE_FAULT` | Hardware fault |
| 22 | `CE_SLEW_IN_MOTION` | Already moving |
| 23 | `CE_SLEW_ERR_UNSPECIFIED` | Other slew error |
| 24 | `CE_NULL` | Internal use, suppress last-error update |
| 25 | `CE_1` | Explicit true/success |

## WiFi Command Channels

The current configuration uses ESP32 WiFi Access Point mode. Actual SSID, password, and IP values come from `Config.h`, `Config.defaults.h`, and NV-stored settings.

### Ports

The default `SERIAL_SERVER` is `BOTH`, so WiFi command channels use these TCP ports:

| Channel | Port | Role |
| --- | --- | --- |
| `SERIAL_SIP` | `9999` | Standard command port |
| `SERIAL_PIP1` | `9996` | Persistent command port |
| `SERIAL_PIP2` | `9997` | Persistent command port |
| `SERIAL_PIP3` | `9998` | Persistent command port |

`SerialWrapper::begin()` opens the standard port at `9999` and persistent ports at `9996`-`9998`. Each port is based on `WiFiServer`, and `IPSerial::available()` accepts clients and reads command bytes.

### Client Behavior

After opening a TCP connection, clients can send ASCII commands such as `:GVP#`, `:GVD#`, or `:Mn#` directly. Replies are sent back on the same TCP connection.

Recommended behavior:

- Always terminate commands with `#`.
- By default, send the next command only after receiving the previous reply.
- Persistent ports are useful for long-lived connections, but long idle/no-data connections can still be closed by timeout.
- For mount-motion commands, use `:GE#` to inspect failure causes.

## Bluetooth SPP Channel

In the current default configuration, `SERIAL_BT_MODE` is `OFF`. ESP32 `BluetoothSerial`-based SPP command channels become available when `SERIAL_RADIO BLUETOOTH` or a separate `SERIAL_BT_MODE SLAVE` setting is selected.

The SPP channel is not gamepad HID. It is a Bluetooth terminal or SPP remote sending OnStep command strings.

A temporary build that kept WiFi AP while adding SPP succeeded, but real operation still needs field testing because ESP32 WiFi and Bluetooth share the 2.4GHz RF path and can introduce latency or disconnects.

## ST4 and SHC

The current configuration uses `ST4_INTERFACE ON` and `ST4_HAND_CONTROL ON`.

ST4 operates in two ways.

1. Normal ST4 input: reads RA/DEC direction pins and calls `guide.startAxis1/2()` and `guide.stopAxis1/2()`.
2. Smart Hand Controller: when RA+ 12.5Hz tone and RA- tone are detected, DEC pins become clock/data outputs and the `SerialST4Master` link starts.

When SHC is active, the `St4Comm` task calls `serialST4.poll()` at about 100us intervals. One byte exchange requires 24 polls, and comments indicate about 4200bps.

Single-byte guide commands from SHC are handled directly:

| Code | Action |
| --- | --- |
| `14` | East guide |
| `15` | West guide |
| `16` | North guide |
| `17` | South guide |
| `18`, `19` | Axis1 guide stop |
| `20`, `21` | Axis2 guide stop |

The current working tree includes the default `ST4_SHC_TONE_LOSS_MS` delay of 1500ms so short SHC tone dropouts do not immediately deactivate the link. This value can be overridden from `Config.h` if needed.

## Internal Command Channel

`SERIAL_LOCAL` is not an external port. It is a Stream used by the firmware to send commands to itself. For example, ST4 hand-control button combinations reuse existing LX200 commands with calls such as `SERIAL_LOCAL.transmit(":B+#")`.

`CommandBroker` is a queue that reduces internal command request/reply collisions.

| Item | Default |
| --- | --- |
| Queue slots | `8` |
| Command length | `40` |
| Reply length | `80` |
| Default timeout | `100ms` |
| Task period | `3ms` |

When an internal feature needs to wait for a reply, prefer `commandBroker.request()` instead of mixing direct `SERIAL_LOCAL.receive()` calls.

## Command Dispatch Order

`Telescope::command()` dispatches commands to subsystems in this order:

1. Command-processing plugins
2. Mount
3. Guide
4. GPIO expansion
5. Mount status
6. Goto
7. Park
8. Library
9. Site
10. Limits
11. Home
12. PEC
13. Axis1
14. Axis2
15. Rotator
16. Focuser
17. Auxiliary features
18. Telescope common commands

The first handler that returns `true` is considered to have handled the command.

## Representative Commands

See `COMMAND_REFERENCE.md` for the detailed command table. Common development/test commands:

| Command | Meaning |
| --- | --- |
| `:GVP#` | Query product name |
| `:GVN#` | Query firmware version |
| `:GVH#` | Query hardware/pinmap string |
| `:GE#` | Query last command error code |
| `:Mn#`, `:Ms#`, `:Me#`, `:Mw#` | Manual motion at current guide rate |
| `:Qn#`, `:Qs#`, `:Qe#`, `:Qw#` | Stop guide/slew in that direction |
| `:Q#` | Stop all slew/goto motion |
| `:RG#`, `:RC#`, `:RM#`, `:RF#` | Guide rate presets |

## Gamepad/Remote Extension View

Bluetooth in the current source is an SPP command channel, not HID gamepad input. Direct gamepad support requires adding a HID host layer and mapping button/stick events into one of:

- Direct `guide.startAxis1/2()` and `guide.stopAxis1/2()` calls
- Existing `:Mn#`/`:Qn#` command families through `SERIAL_LOCAL` or `CommandBroker`

The safety design must include input-loss timeout, stop-on-release, policy for input during goto, and maximum guide-rate limits.
