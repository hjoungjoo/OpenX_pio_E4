"""Test current StepDir frequency/mode functions without motor hardware.

The ISR's arrival at a microstep-aligned boundary is simulated explicitly.
Timer and driver calls are stubbed; this is not a physical smoothness test.
Run with Python 3 and g++ (ASan and UBSan enabled).
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src/lib/axis/motor/stepDir/StepDir.cpp").read_text()


def extract(signature):
    start = SOURCE.index(signature)
    end = SOURCE.index("{", start) + 1
    depth = 1
    while depth:
        if SOURCE[end] == "{":
            depth += 1
        elif SOURCE[end] == "}":
            depth -= 1
        end += 1
    return SOURCE[start:end]


PREFIX = r'''
#include <cmath>
#include <iostream>
#include <cassert>
using std::isnan; using std::isinf;
#define OFF 0
#define DEBUG 0
#define PULSE 1
#define SQUARE 2
#define DEDGE 3
#define HAL_MAXRATE_LOWER_LIMIT 40
#define Y
#define VF(...)
#define V(...)
#define VLF(...)
void noInterrupts() {} void interrupts() {}
unsigned long millis() { return 1; }
enum MicrostepModeControl {MMC_TRACKING, MMC_SLEWING, MMC_SLEWING_REQUEST,
 MMC_SLEWING_PAUSE, MMC_SLEWING_READY, MMC_TRACKING_READY};
struct Tasks {void setPeriodSubMicros(int, unsigned long) {}} tasks;
struct Driver {
 bool modeSwitchAllowed=true, modeSwitchFastAllowed=false;
 int microsteps=64, ratio=16;
 void modeMicrostepTracking() { microsteps=64; }
 int modeMicrostepSlewing() { microsteps=64/ratio; return ratio; }
};
struct StepDirMotor {
 bool ready=true, enabled=true, inBacklash=false, sync=false, fast=false;
 float backlashFrequency=3200, currentFrequency=0, lastFrequency=0;
 int stepSize=1, step=1, direction=0, dirRev=1, dirFwd=0, taskHandle=1;
 unsigned long lastPeriod=0,lastPeriodSet=0,switchStartTimeMs=0;
 MicrostepModeControl microstepModeControl=MMC_TRACKING;
 Driver storage; Driver* driver=&storage;
 void stopStepTimerAndClearPulse() {
   lastPeriod=lastPeriodSet=0; currentFrequency=lastFrequency=0; step=0;
 }
 bool enableMoveFast(bool v) {fast=v; return true;}
 void setFrequencySteps(float);
 void modeSwitch();
 float getFrequencySteps();
 float logicalRate() {return getFrequencySteps()*(64.0f/driver->microsteps);}
};
'''

MAIN = r'''
void expectRate(StepDirMotor& motor, float requested) {
  // Timer periods are rounded to 1/16 us (including SQUARE's half-period).
  const float tolerance=std::abs(requested)*0.001f+0.01f;
  if (std::abs(motor.logicalRate()-std::abs(requested)) >= tolerance)
    std::cerr << "ratio=" << motor.driver->ratio << " requested=" << requested
      << " actual=" << motor.logicalRate() << " mode="
      << motor.microstepModeControl << " microsteps=" << motor.driver->microsteps << '\n';
  assert(std::abs(motor.logicalRate()-std::abs(requested)) < tolerance);
  assert(motor.step == (requested > 0 ? 1 : requested < 0 ? -1 : 0));
}
void enterSlew(StepDirMotor& motor, int sign, int ratio) {
  motor.driver->ratio=ratio;
  motor.driver->modeSwitchAllowed=ratio!=1;
  motor.setFrequencySteps(sign*10240);
  motor.setFrequencySteps(sign*10240);
  assert(motor.microstepModeControl==MMC_SLEWING_REQUEST);
  // Model the ISR reaching a position divisible by the microstep ratio.
  motor.microstepModeControl=MMC_SLEWING_PAUSE;
  motor.setFrequencySteps(sign*10240);
  assert(motor.microstepModeControl==MMC_SLEWING);
  assert(motor.driver->microsteps==64/ratio);
  expectRate(motor, sign*10240);
}
int main() {
  int cases=0;
  for (int sign : {1,-1}) for (int ratio : {1,2,4,16,64}) {
    // Regression: incoming tracking-microstep rate numerically equals the
    // previous *physical* pulse rate. It must still decelerate by ratio.
    StepDirMotor motor;
    enterSlew(motor,sign,ratio);
    const float requested=sign*10240.0f/ratio;
    for(int tick=0;tick<100;tick++) motor.setFrequencySteps(requested);
    expectRate(motor,requested);
    if(ratio>1) assert(motor.driver->microsteps==64);
    ++cases;

    // Repeating a speed, adjacent speeds, deceleration and stopping must
    // retain the requested rate across both microstep modes.
    StepDirMotor sweep;
    enterSlew(sweep,sign,ratio);
    for(float speed : {10240.0f,10240.0f,9000.0f,7000.0f,6400.0f,
                      3200.0f,641.0f,640.0f,160.0f,0.0f}) {
      for(int tick=0;tick<3;tick++) sweep.setFrequencySteps(sign*speed);
      expectRate(sweep,sign*speed);
      ++cases;
    }
    assert(sweep.driver->microsteps==64);
    assert(sweep.lastPeriod==0);
    sweep.setFrequencySteps(-sign*160);
    expectRate(sweep,-sign*160);
    ++cases;

    // A fresh acceleration after stop must not retain a stale rate cache.
    enterSlew(sweep,sign,ratio);
    expectRate(sweep,sign*10240);
    ++cases;
  }
  // Backlash override uses the same units; returning to tracking must not
  // mistake the override for the caller's requested frequency.
  StepDirMotor backlash;
  backlash.inBacklash=true;
  backlash.setFrequencySteps(160);
  expectRate(backlash,3200);
  backlash.inBacklash=false;
  backlash.setFrequencySteps(160);
  expectRate(backlash,160);
  ++cases;
  for(float invalid : {NAN,INFINITY,-INFINITY}) {
    backlash.setFrequencySteps(invalid);
    assert(backlash.lastPeriod==0);
    backlash.setFrequencySteps(160);
    expectRate(backlash,160);
    ++cases;
  }
  backlash.enabled=false;
  backlash.setFrequencySteps(160);
  assert(backlash.lastPeriod==0);
  backlash.enabled=true;
  backlash.setFrequencySteps(160);
  expectRate(backlash,160);
  ++cases;
  std::cout << cases << " rate/mode cases passed\n";
}
'''


def main():
    functions = "\n".join(extract(signature) for signature in (
        "void StepDirMotor::setFrequencySteps(float frequency)",
        "void StepDirMotor::modeSwitch()",
        "float StepDirMotor::getFrequencySteps()",
    ))
    with tempfile.TemporaryDirectory(prefix="onstep-transition-") as directory:
        cpp = Path(directory) / "test.cpp"
        binary = Path(directory) / "test"
        cpp.write_text(PREFIX + functions + MAIN)
        for wave in ("PULSE", "SQUARE", "DEDGE"):
            subprocess.run([
                "g++", "-std=c++17", "-Wall", "-Wextra", "-g", "-O1",
                "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                f"-DSTEP_WAVE_FORM={wave}", str(cpp), "-o", str(binary),
            ], check=True)
            print(wave, flush=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
