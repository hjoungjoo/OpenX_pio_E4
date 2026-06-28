# Building OnStepX from VS Code

This workspace keeps the Arduino sketch layout and drives builds with `arduino-cli`.
The VS Code tasks call `tools/arduino-cli.ps1`, which finds `arduino-cli.exe` from:

1. `ARDUINO_CLI`
2. `arduino-cli` on `PATH`
3. Arduino IDE 2.x default install paths

## One-time setup

Open VS Code in this folder, then run:

```powershell
Ctrl+Shift+P -> Tasks: Run Task -> OnStepX: Setup ESP32 toolchain
```

That task installs/updates:

- ESP32 Arduino core from Espressif's package index
- `TMCStepper`, required by the current `DRIVER_TMC_STEPPER` setting

If other OnStepX features are enabled later, install any new libraries listed by
the compiler errors with:

```powershell
Ctrl+Shift+P -> Tasks: Run Task -> OnStepX: Install current libraries
```

or directly:

```powershell
arduino-cli lib install "LibraryName"
```

## Build

Use the default build task:

```powershell
Ctrl+Shift+B
```

or run:

```powershell
Ctrl+Shift+P -> Tasks: Run Build Task -> OnStepX: Build (ESP32 MF_OOZOO_E4)
```

The default board is:

```text
esp32:esp32:esp32:PartitionScheme=huge_app
```

Use one of the plain `esp32:esp32:*` choices only if the installed ESP32 core
does not recognize the `huge_app` partition option.

## Upload

First find the port:

```powershell
Ctrl+Shift+P -> Tasks: Run Task -> OnStepX: Board list
```

Then upload:

```powershell
Ctrl+Shift+P -> Tasks: Run Task -> OnStepX: Upload (ESP32 MF_OOZOO_E4)
```

When prompted, enter the serial port, for example `COM5`.

## Serial monitor

```powershell
Ctrl+Shift+P -> Tasks: Run Task -> OnStepX: Serial monitor
```

The monitor task uses `115200`, matching the current `SERIAL_A_BAUD_DEFAULT`
and `SERIAL_DEBUG_BAUD` values.
