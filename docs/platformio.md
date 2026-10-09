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
- serial monitor and firmware USB command port at `230400` (10.28z onward)
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

## Host regression checks

With Python 3 and a host C++17 compiler installed:

```sh
bash tools/test_commands.sh
python3 tests/host/tracking_pulse_test.py
```

The pulse test extracts the current firmware's tracking, guide and coordinate
functions, substitutes a deterministic clock and hardware stubs, and checks
240 timing cases across Alt/Az, Alt/Alt and equatorial mounts. It also checks
overlapping axes, guide changes during a periodic calculation, reversal and
abort. Both tests enable AddressSanitizer and UndefinedBehaviorSanitizer.
In a ptrace-based sandbox, use `ASAN_OPTIONS=detect_leaks=0` if LeakSanitizer
cannot enumerate threads. This does not replace a device output timing test.
