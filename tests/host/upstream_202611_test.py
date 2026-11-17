"""November upstream integration checks using real firmware functions.

Clock, GPIO, motor reports and scheduler are simulated. No device is accessed.
Run with Python 3 and g++; all executable fixtures use ASan and UBSan.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text()


def block(text, marker):
    start = text.index(marker)
    brace = text.index('{', start)
    end, depth = brace + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def function(path, signature):
    return block(read(path), signature)


COMMON = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <functional>
#include <iostream>
#include <vector>
#include <array>
using std::isnan;
#define ON 1
#define OFF 0
#define VF(...)
#define V(...)
#define VL(...)
#define VLF(...)
#define DLF(...)
'''


def run(name, code, defines=(), extra=()):
    with tempfile.TemporaryDirectory(prefix='onstep-november-') as tmp:
        cpp, binary = Path(tmp) / 'test.cpp', Path(tmp) / 'test'
        cpp.write_text(COMMON + code)
        subprocess.run(['g++', '-std=c++17', '-O0', '-g',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        '-I' + str(ROOT), '-I' + str(ROOT / 'tests/host'),
                        *['-D' + d for d in defines], str(cpp),
                        *[str(ROOT / p) for p in extra], '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print(name + ' passed', flush=True)


guide_prefix = r'''
#define GOTO_FEATURE ON
#define AXIS2_SLEW_RATE_PERCENT 100
#define DIR_BOTH 0
enum GuideAction {GA_NONE,GA_BREAK,GA_FORWARD,GA_REVERSE,GA_HOME,GA_SPIRAL};
enum GuideState {GU_NONE,GU_PULSE_GUIDE,GU_GUIDE,GU_SPIRAL_GUIDE,GU_HOME_GUIDE,GU_HOME_GUIDE_ABORT};
enum GuideRateSelect {GR_CUSTOM,GR_1X,GR_MAX};
enum CommandError {CE_NONE,CE_SLEW_IN_MOTION,CE_SLEW_ERR_OUTSIDE_LIMITS,
 CE_SLEW_ERR_IN_PARK,CE_SLEW_ERR_IN_STANDBY,CE_SLEW_ERR_HARDWARE_FAULT};
constexpr int GS_NONE=0,PS_UNPARKED=0,PS_PARKED=1,PIER_SIDE_WEST=1;
unsigned long clockMs=0;unsigned long millis(){return clockMs;}
float degToRadF(float value){return value*M_PI/180;}
struct Axis {
 bool slewing=false;int stops=0,aborts=0;
 bool isSlewing(){return slewing;}bool motionError(int){return false;}
 void autoSlewAbort(){++aborts;}void autoSlewStop(){++stops;}
 void setPowerDownOverrideTime(unsigned long){}void setFrequencySlew(float){}
} axis1,axis2;
struct Mount {
 bool slewing=false,enabled=false,fault=false;int enables=0,updates=0,immediate=0;
 float trackingRateAxis1=1,trackingRateAxis2=0;
 bool isSlewing(){return slewing||axis1.slewing||axis2.slewing;}
 bool isEnabled(){return enabled;}void enable(bool s){enabled=s;++enables;}
 bool motorFault(){return fault;}void update(bool b=false){++updates;immediate+=b;}
} mount;
struct {bool allowed=true;bool isMotionAllowed(){return allowed;}bool isError(){return false;}} limits;
struct {int state=GS_NONE,aborts=0;void abort(){++aborts;}} goTo;
struct {int state=PS_UNPARKED;} park;
struct {CommandError error=CE_NONE;CommandError validateManualMotion(){return error;}} startupAuthority;
struct {void wake(){}void soundAlert(){}} mountStatus;
struct {void guideDone(bool){}} home;
struct Guide {
 GuideState state=GU_NONE;GuideAction guideActionAxis1=GA_NONE,guideActionAxis2=GA_NONE;
 float rateAxis1=0,rateAxis2=0,selectedRate=1;int pierSide=0;
 unsigned long guideFinishTimeAxis1=0,guideFinishTimeAxis2=0;
 struct {int axis1RateSelect=3,axis2RateSelect=3;} settings;
 bool validAxis1(GuideAction){return true;}bool validAxis2(GuideAction){return true;}
 void abort(){}void spiralPoll(){}void backlashEnableControl(bool){}
 void axis1AutoSlew(GuideAction){axis1.slewing=true;}
 void axis2AutoSlew(GuideAction){axis2.slewing=true;}
 float rateSelectToRate(GuideRateSelect,int){return selectedRate;}
 void finalizeTimeLimit(unsigned long&){}
 CommandError validate(int,GuideAction,bool=false);
 CommandError startAxis1(GuideAction,GuideRateSelect,unsigned long,bool);
 CommandError startAxis2(GuideAction,GuideRateSelect,unsigned long,bool);
 void stopAxis1(GuideAction=GA_BREAK,bool=false);
 void stopAxis2(GuideAction=GA_BREAK,bool=false);
 void stop(){stopAxis1();stopAxis2();}void poll();
} guide;
void reset(){guide=Guide();mount=Mount();axis1=Axis();axis2=Axis();goTo.state=GS_NONE;
 goTo.aborts=0;park.state=PS_UNPARKED;limits.allowed=true;startupAuthority.error=CE_NONE;clockMs=0;}
'''
guide_functions = '\n'.join(function('src/telescope/mount/guide/Guide.cpp', s) for s in [
    'CommandError Guide::startAxis1(', 'CommandError Guide::startAxis2(',
    'void Guide::stopAxis1(', 'void Guide::stopAxis2(',
    'CommandError Guide::validate(', 'void Guide::poll()'])
guide_main = r'''
int main(){
 for(int which:{1,2}){
  auto start=[&](bool pulse){return which==1?guide.startAxis1(GA_FORWARD,GR_1X,200,pulse):
   guide.startAxis2(GA_FORWARD,GR_1X,200,pulse);};
  for(GuideState state:{GU_GUIDE,GU_SPIRAL_GUIDE,GU_HOME_GUIDE,GU_HOME_GUIDE_ABORT}){
   reset();guide.state=state;assert(start(true)==CE_SLEW_IN_MOTION);assert(mount.enables==0);
  }
  reset();goTo.state=1;assert(start(true)==CE_SLEW_IN_MOTION && goTo.aborts==0 && mount.enables==0);
  reset();mount.slewing=true;assert(start(true)==CE_SLEW_IN_MOTION && mount.enables==0);
  reset();limits.allowed=false;assert(start(true)==CE_SLEW_ERR_OUTSIDE_LIMITS && mount.enables==0);
  reset();startupAuthority.error=CE_SLEW_ERR_OUTSIDE_LIMITS;
  assert(start(false)==CE_SLEW_ERR_OUTSIDE_LIMITS && mount.enables==0);
  reset();assert(start(true)==CE_NONE && guide.state==GU_PULSE_GUIDE && mount.immediate==1);
  guide.selectedRate=16;assert(start(false)==CE_NONE && guide.state==GU_GUIDE);
  assert(guide.rateAxis1==0 && guide.rateAxis2==0);
  Axis& axis=which==1?axis1:axis2;axis.slewing=true;
  (which==1?guide.rateAxis1:guide.rateAxis2)=1; // stale pulse must not hide an actual slew
  if(which==1)guide.stopAxis1(GA_BREAK,true);else guide.stopAxis2(GA_BREAK,true);
  assert(axis.aborts==1 && guide.rateAxis1==0 && guide.rateAxis2==0);
  assert((which==1?guide.guideActionAxis1:guide.guideActionAxis2)==GA_BREAK);
  reset();axis.slewing=true; // actual GoTo axis, with no active guide action
  if(which==1)guide.stopAxis1();else guide.stopAxis2();
  assert(axis.stops==1);axis.slewing=false;
  const int before=mount.updates;guide.poll();
  assert(guide.state==GU_NONE && guide.guideActionAxis1==GA_NONE && guide.guideActionAxis2==GA_NONE);
  assert(mount.updates>before); // stop completion must run even in GU_NONE
 }
}
'''
run('guide mode isolation, pulse/manual handoff and GoTo stop completion', guide_prefix + guide_functions + guide_main)

brake_prefix = r'''
#define MOUNT_PRESENT
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define MOUNT_BRAKE_PIN 10
#define MOUNT_BRAKE_RELEASE_STATE HIGH
#define MOUNT_BRAKE_HOLD_STATE LOW
#define MOUNT_BRAKE_STARTUP_DELAY 250
#define MOUNT_BRAKE_RELEASE_DELAY 500
#define MOUNT_BRAKE_HOLD_DELAY 100
constexpr int TS_NONE=0;
unsigned long clockMs=0;unsigned long millis(){return clockMs;}
std::array<int,32> gpio{};std::vector<int> writes;
void digitalWriteEx(int pin,int state){assert(pin>=0 && pin<32);gpio[pin]=state;writes.push_back(pin*2+state);}
void pinModeEx(int,int){}
struct Motor {bool enabled=true,ready=true;};
struct Axis {
 Motor data;Motor* motor=&data;bool fault=false;
 bool motorFault(){return fault;}bool isEnabled(){return data.enabled;}
 void enable(bool state){data.enabled=state;}
} axis1,axis2;
struct {bool driver=false;} initError;
std::function<void()> onYield;
struct Tasks {
 bool success=true;void (*monitor)()=nullptr;
 int add(int,int,bool,int,void (*fn)(),const char*){monitor=fn;return success;}
 void yield(unsigned long ms){clockMs+=ms;if(onYield)onYield();if(monitor)monitor();}
} tasks;
struct Mount {
 bool brakeMonitoring=false,brakeReleased=false,brakeFaultLatched=false;int trackingState=1;
 void initBrake();void beginBrake();void releaseBrake();void engageBrake();void latchBrakeFault();
 bool motorFault();bool isEnabled();void enable(bool);void update(){}
} mount;
void reset(){mount=Mount();axis1.data=Motor();axis2.data=Motor();axis1.fault=axis2.fault=false;
 initError.driver=false;tasks=Tasks();onYield=nullptr;clockMs=0;gpio.fill(-1);writes.clear();}
'''
brake_functions = re.sub(r'^#include.*$', '', read('src/telescope/mount/Mount.brake.cpp'), flags=re.M)
brake_functions += '\n' + function('src/telescope/mount/Mount.cpp', 'void Mount::enable(')
brake_functions += '\n' + function('src/telescope/mount/Mount.h', 'inline bool isEnabled()').replace('inline bool isEnabled()', 'bool Mount::isEnabled()')
brake_main = r'''
int main(){
 reset();
 #if MOUNT_BRAKE == ON
 mount.initBrake();assert(gpio[10]==LOW && !mount.isEnabled());mount.beginBrake();
 assert(mount.isEnabled() && !mount.motorFault());
 #if MOUNT_BRAKE_HOLD_PIN != OFF
 assert(gpio[10]==LOW && gpio[MOUNT_BRAKE_HOLD_PIN]==LOW && clockMs==850);
 #else
 assert(gpio[10]==HIGH && clockMs==750);
 for(int write:writes)assert(write/2==10);
 #endif
 axis2.fault=true;assert(mount.motorFault());axis2.fault=false;
 assert(mount.motorFault() && !mount.isEnabled() && gpio[10]==LOW);
 mount.enable(true);assert(!axis1.data.enabled && !axis2.data.enabled);
 for(int failure:{0,1,2,3}){
  reset();mount.initBrake();
  if(failure==0)initError.driver=true;
  if(failure==1)axis1.data.ready=false;
  if(failure==2)tasks.success=false;
  if(failure==3)axis2.data.enabled=false;
  mount.beginBrake();assert(mount.motorFault() && !mount.isEnabled() && gpio[10]==LOW);
 }
 for(unsigned long failureAt:{250UL,750UL,850UL}){
  reset();mount.initBrake();onYield=[&](){if(clockMs>=failureAt)axis1.fault=true;};
  mount.beginBrake();
  if(clockMs>=failureAt){assert(mount.motorFault() && !mount.isEnabled() && gpio[10]==LOW);}
 }
 reset();mount.initBrake();mount.beginBrake();mount.enable(false);mount.enable(true);
 assert(!mount.isEnabled() && !axis1.data.enabled && gpio[10]==LOW);
 #else
 assert(mount.isEnabled());mount.enable(false);assert(!mount.isEnabled());
 mount.enable(true);assert(mount.isEnabled() && writes.empty());
 axis1.fault=true;assert(mount.motorFault());axis1.fault=false;assert(!mount.motorFault());
 #endif
}
'''
for enabled, hold in [(0, 0), (1, 0), (1, 11)]:
    run(f'brake startup, faults and disable (enabled={enabled}, hold={hold})',
        brake_prefix + brake_functions + brake_main,
        [f'MOUNT_BRAKE={enabled}', f'MOUNT_BRAKE_HOLD_PIN={hold}'])

mode_prefix = r'''
#include "src/lib/commands/BufferCmds.h"
constexpr int GEM=1,FORK=2,ALTAZM=3,ALTALT=4,PS_PARKED=1;
struct {int mountType=GEM;} transform;
struct {bool isTracking(){return true;}bool isHome(){return false;}} mount;
struct {int state=0;} park;
struct {bool alignDone(){return true;}} goTo;
struct {float pressure=NAN,temperature=NAN;float getPressure(){return pressure;}
 float getTemperature(){return temperature;}} weather;
double degToRad(double d){return d*M_PI/180;}
struct Transform {double trueRefrac(double);double apparentRefrac(double);float cotf(float);};
void query(char* command,char* parameter,char* reply,bool* numericReply,bool* suppressFrame){
'''
status = read('src/telescope/mount/status/Status.command.cpp')
mode_functions = block(status, "if (command[1] == 'W' && parameter[0] == 0)") + '\n'
mode_functions += block(status, "if (command[1] == 'w' && parameter[0] == 0)") + '\n}\n'
for signature in ['double Transform::trueRefrac(', 'double Transform::apparentRefrac(', 'float Transform::cotf(']:
    mode_functions += function('src/telescope/mount/coordinates/Transform.cpp', signature) + '\n'
mode_main = r'''
int main(){
 for(int type:{GEM,FORK,ALTAZM,ALTALT}){
  transform.mountType=type;
  for(bool ack:{false,true}){
   Buffer buffer;if(ack)buffer.add(6);else for(char c:":Gw#")if(c)buffer.add(c);
   char reply[80]{};bool numeric=true,suppress=false;
   query(buffer.getCmd(),buffer.getParameter(),reply,&numeric,&suppress);
   assert(!numeric && suppress && strlen(reply)==1);
   assert(reply[0]==(type==GEM||type==FORK?'P':'A'));
  }
  char command[]="GW",parameter[]="",reply[80]{};bool numeric=true,suppress=false;
  query(command,parameter,reply,&numeric,&suppress);
  assert(!numeric && !suppress && strlen(reply)==3 && reply[1]=='T' && reply[2]=='1');
  assert(reply[0]==(type==GEM?'G':type==FORK?'P':'A'));
 }
 Transform t;
 for(bool measured:{false,true}){
  weather.pressure=measured?980:NAN;weather.temperature=measured?2:NAN;
  const double below=t.trueRefrac(degToRad(-1));
  for(double d:{-90.0,-10.0,-5.11,-5.1099,-2.0,-1.0}){
   assert(t.trueRefrac(degToRad(d))==below);
   assert(std::isfinite(t.apparentRefrac(degToRad(d))));
  }
  for(int d=-90;d<=90;d++)assert(std::isfinite(t.trueRefrac(degToRad(d))));
 }
}
'''
run('LX200 ACK/current geometry, Alt-Alt status and below-horizon refraction',
    mode_prefix + mode_functions + mode_main, extra=['src/lib/commands/BufferCmds.cpp'])

wifi_prefix = r'''
#define ESP32
struct {int changes=0;void setSleep(bool value){assert(!value);++changes;}} WiFi;
'''
wifi_function = function('src/lib/wifi/WifiManager.cpp', 'static void applyWifiPerformanceMode()')
wifi_main = r'''
int main(){applyWifiPerformanceMode();assert(WiFi.changes==EXPECTED);}
'''
for high, allow, expected in [(1, False, 1), (1, True, 0), (0, False, 0)]:
    defines = [f'WIFI_HIGH_PERFORMANCE={high}', f'EXPECTED={expected}']
    if allow:
        defines.append('WIFI_MANAGER_ALLOW_SLEEP')
    run(f'WiFi sleep option precedence (performance={high}, allow={allow})',
        wifi_prefix + wifi_function + wifi_main, defines)
