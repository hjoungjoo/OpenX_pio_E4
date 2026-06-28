# Building OnStepX with PlatformIO

This project keeps the original Arduino sketch layout and uses `platformio.ini`
to tell PlatformIO which files to build.

## Environment

Default environment:

```text
onstepx_esp32_mf_oozoo_e4
```

Current target:

- ESP32 Dev Module compatible board
- `MF_OOZOO_E4` pinmap from `Config.h`
- `huge_app.csv` partition layout
- `TMCStepper` library
- serial monitor at `115200`
- PlatformIO `platformio/espressif32@6.7.0` with Arduino-ESP32 `2.0.16`

`platformio_deps.cpp` exists only to help PlatformIO's Library Dependency Finder
see the ESP32 built-in libraries used through OnStepX headers.

## VS Code

Install the PlatformIO IDE extension, then open this folder. PlatformIO should
detect `platformio.ini` automatically.

Useful commands:

```text
PlatformIO: Build
PlatformIO: Upload
PlatformIO: Monitor
PlatformIO: Clean
```

The workspace also has VS Code tasks that call `tools/pio.ps1`, so
`Ctrl+Shift+B` runs a PlatformIO build even if `pio.exe` is not on `PATH`.

## Upload Port

PlatformIO usually auto-detects the ESP32 serial port. If it does not, add this
to the environment in `platformio.ini`:

```ini
upload_port = COM5
monitor_port = COM5
```

Replace `COM5` with the port shown by PlatformIO or Windows Device Manager.

## Debug

Software serial monitoring works over USB. True breakpoints require an ESP32
JTAG debugger such as ESP-Prog. After wiring the debugger, uncomment the
`debug_tool` lines in `platformio.ini`.
