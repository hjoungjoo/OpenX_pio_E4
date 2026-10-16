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
python3 tests/host/stepdir_transition_test.py
python3 tests/host/upstream_safety_test.py
```

The pulse test extracts the current firmware's tracking, guide and coordinate
functions, substitutes a deterministic clock and hardware stubs, and checks
240 timing cases across Alt/Az, Alt/Alt and equatorial mounts. It also checks
overlapping axes, guide changes during a periodic calculation, reversal and
abort. It also checks 800 trajectory derivatives across both non-equatorial
mount types, five compensation modes, directions and tracking offsets. The
refraction and pointing corrections in this fixture are synthetic; they expose
asymmetric endpoint handling without claiming real atmospheric accuracy.
Input changes across yields and non-finite rate rejection are covered as well.
All four tests enable AddressSanitizer and UndefinedBehaviorSanitizer.

The step/dir transition test compiles the current frequency and mode-switch
functions and checks requested rates across microstep ratios, acceleration,
deceleration, repeated rates, stop/restart and backlash. It covers PULSE,
SQUARE and DEDGE waveforms, including the regression where a new tracking
rate numerically equals the previous coarse-microstep pulse rate. ISR boundary
arrival and hardware are stubbed; it does not measure vibration or step loss.

The upstream safety test compiles the actual NV volume and CRC implementation
with an in-memory device. It checks repeated reset requests, durable flushes,
I/O failures, timeouts and cancelled MCU resets. It also covers numeric/model
coefficient validation, alignment round trips and fallback, pole orientation,
runtime Sync settings (including failed-save preservation), and home/park abort.
No physical device is accessed by these host tests.

In a ptrace-based sandbox, use `ASAN_OPTIONS=detect_leaks=0` if LeakSanitizer
cannot enumerate threads. This does not replace a device output timing test.
