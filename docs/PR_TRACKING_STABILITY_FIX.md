# Tracking Stability Fix PR Notes

## PR Title

Fix Alt/Az tracking-rate spikes caused by shared mount coordinate reuse

## Summary

This PR fixes intermittent Alt/Az tracking-rate spikes observed after unpark, goto, one-star alignment, and sidereal tracking start.

The confirmed root cause was shared coordinate state reuse inside `Mount::poll()`. The tracking-rate calculation used the mutable `Mount::current` member across yield points. While `Mount::poll()` was yielding, another status, command, or web path could call `getMountPosition()` / `getPosition()` and overwrite `current` with a coordinate mode that did not include valid equatorial `h/d` values. When `Mount::poll()` resumed, the tracking-rate calculation could briefly use `h=0` and `d=0`, producing a one-cycle tracking spike.

The fix snapshots `current` into a local `trackingCurrent` value immediately after `updatePosition(CR_MOUNT_ALL)` and uses that local copy for the rest of the tracking-rate calculation.

Runtime diagnostic logs that were added during investigation have been removed for normal operation. The tracking stability fix remains.

## User-Visible Issue

During field testing, both altitude and azimuth motors produced intermittent ticking sounds and small telescope shakes while tracking. The issue appeared at non-periodic intervals, and the two axes did not always exhibit the same cadence.

The mount generally continued operating because existing safety logic prevented extreme motion, but the source of the disturbance was still present.

## Investigation Summary

Temporary field diagnostics were used to rule out low-level timing causes:

- ESP32 dual-core scheduling was active.
- Axis 1 and Axis 2 StepDir tasks were using hardware timers.
- The site sidereal clock was using a hardware timer.
- WebServer activity was separated from the Arduino setup/loop core.
- StepDir frequency clamp was not active during the event.
- Backlash takeup was not active during the event.
- Guide input was inactive.
- Tracking safety limiter was not active.

The key failing diagnostic sample showed:

```text
raw1=1.641294
raw2=0.000000
cur={h=0.000000,d=0.000000,a=70.x,z=114.x,...}
```

Normal samples immediately before and after the spike had valid equatorial coordinates around:

```text
h=-20.x deg
d=27.x deg
```

This proved the motor tick was caused by bad tracking-rate input coordinates, not by the motor driver, hardware timer, WiFi task, or backlash compensation.

## Root Cause

The original tracking path in `Mount::poll()` used the shared `current` member throughout the calculation:

```cpp
updatePosition(CR_MOUNT_ALL);
double altitude = current.a;
double declination = current.d;

transform.mountToTopocentric(&current);
...
Y;
Coordinate ahead = current;
Coordinate behind = current;
```

`Y` allows cooperative task scheduling. During that yield, another code path could call:

```cpp
Coordinate Mount::getMountPosition(CoordReturn coordReturn) {
  updatePosition(coordReturn);
  return current;
}
```

For Alt/Az mounts, `CR_MOUNT` can validly return native mount coordinates without also filling equatorial `h/d`. That is fine for the caller, but unsafe if `Mount::poll()` later resumes and assumes `current` still contains the earlier `CR_MOUNT_ALL` result.

## Implementation

`Mount::poll()` now copies `current` into a local coordinate snapshot immediately after `updatePosition(CR_MOUNT_ALL)`:

```cpp
updatePosition(CR_MOUNT_ALL);
Coordinate trackingCurrent = current;
```

The rest of the tracking-rate calculation now uses `trackingCurrent` for:

- altitude / declination / altitude2 source values
- topocentric conversion
- Alt/Az or Alt/Alt conversion
- `ahead` and `behind` coordinate generation
- pier-side sign handling

This keeps a single tracking-rate calculation internally consistent even if status, website, or command handlers query the mount position while `Mount::poll()` is yielding.

## Final Runtime State

The temporary investigation logs have been removed from the final runtime code:

- no `DBG: Track` periodic logs
- no `DBG: TrackSpike` logs
- no ESP32 core startup debug log
- no StepDir hardware timer debug log
- no Site clock hardware timer debug log
- no WebServer core debug log
- no tracking diagnostic config remains in `Extended.config.h`
- `DEBUG` is back to `OFF`

`SERIAL_A_BAUD_DEFAULT` remains at `460800`, matching the current test/communication setup.

## Files Changed

- `Config.h`
  - Keeps `SERIAL_A_BAUD_DEFAULT` at `460800`.

- `src/telescope/mount/Mount.cpp`
  - Uses local `trackingCurrent` snapshot during Alt/Az tracking-rate calculation.
  - Uses `trackingCurrent.pierSide` when applying Axis 2 sign handling.
  - Keeps the existing tracking formula and safety limit behavior unchanged.

- `src/lib/axis/motor/stepDir/StepDir.cpp`
  - Removes temporary StepDir frequency diagnostic logging that was used during investigation.

- `docs/PR_TRACKING_STABILITY_FIX.md`
  - Documents the issue, root cause, final fix, and validation evidence.

## Validation

### Build

PlatformIO build passed after removing the temporary diagnostics:

```text
Environment: onstepx_esp32_mf_oozoo_e4
Result: SUCCESS
RAM:   19.3% (63300 / 327680 bytes)
Flash: 39.1% (1229925 / 3145728 bytes)
```

### Pre-Fix Field Evidence

Before the snapshot fix, repeated spike pairs were observed:

```text
raw1=1.641294
raw2=0.000000
cur={h=0.000000,d=0.000000,a=70.x,z=114.x,...}
```

This caused the next motor update to briefly drive Axis 1 faster and Axis 2 to zero:

```text
a1Hz=438.873
a2Hz=0.000
```

### Post-Fix Field Evidence

After the snapshot fix, the provided field log contained 107 tracking samples.

Observed results:

- `TrackSpike`: 0
- `raw2=0`: 0
- `a2Hz=0`: 0
- tracking limiter active: 0
- `raw1` range: `1.718749 .. 1.796203`
- `raw2` range: `0.696679 .. 0.704466`
- Axis 1 Hz range: `458.321 .. 479.171`
- Axis 2 Hz range: `186.452 .. 188.421`
- maximum raw Axis 1 delta vs previous output: about `0.005024`
- maximum raw Axis 2 delta vs previous output: about `0.000655`

The remaining rate movement is gradual and consistent with Alt/Az tracking geometry as the target moves. The previous one-cycle collapse of Axis 2 to zero was not observed.

## Review Notes

The behavior change is intentionally narrow:

- It does not change the tracking-rate formula.
- It does not change motor ISR timing.
- It does not change StepDir stepping behavior.
- It does not change backlash behavior.
- It does not add runtime diagnostic output.
- It only prevents a shared coordinate object from being reused after it may have been modified by another path.

## Suggested Test Plan

1. Build with PlatformIO.
2. Upload to the ESP32 controller.
3. Set time/location.
4. Unpark.
5. Goto an alignment star.
6. Complete one-star alignment.
7. Start sidereal tracking.
8. Keep AP/Web status access active to exercise `getMountPosition()` while tracking.
9. Verify:
   - no audible tick/shake during tracking,
   - no Axis 2 one-cycle stop,
   - no sudden jump in tracking behavior while web/status polling is active.
