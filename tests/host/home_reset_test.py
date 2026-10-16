"""Exercise the actual home reset with simulated counters and coordinate limits."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'src/telescope/mount/home/Home.cpp').read_text()
start = source.index('CommandError Home::reset(')
end = source.index('// get the home position', start)
reset = source[start:end]

fixture = r'''
#include <cassert>
#include <cmath>
#include <iostream>
#define ON 1
#define OFF 0
#define GOTO_FEATURE ON
#define MOUNT_HOME_AT_OFFSETS OFF
#define MOUNT_ENABLE_IN_STANDBY OFF
#define TRACKING_RATE_DEFAULT_HZ 60
#define DLF(...)
#define VF(...)
#define V(...)
#define VLF(...)
enum CommandError {CE_NONE, CE_SLEW_IN_MOTION, CE_SLEW_ERR_OUTSIDE_LIMITS};
enum {GS_NONE, GU_NONE=0, GU_HOME_GUIDE, HS_HOMING=1, CR_MOUNT=0};
double hzToSidereal(double x){return x;}
double arcsecToRad(double x){return x*3.141592653589793/648000;}
float degToRadF(float x){return x*3.141592653589793/180;}
struct Coordinate {double a1=1,a2=2;};
struct Axis {
 double counter=123,coordinate=4,backlash=0; int resets=0,aborts=0; bool fail=false;
 int resetPosition(double x){++resets;if(fail)return 1;counter=x;return 0;}
 void autoSlewAbort(){++aborts;}
 void setBacklash(double x){backlash=x;}
 void setFrequencySlew(float){}
} axis1,axis2;
struct {
 bool absolute=false,trackingOn=true,syncFromOnStepToEncoders=false,powered=true;
 float trackingRate=99,trackingRateOffsetRA=3,trackingRateOffsetDec=4;
 int captures=0; double nominal1=7,nominal2=8;
 struct {struct {float axis1=1,axis2=2;} backlash;} settings;
 bool hasAbsoluteEncoders(){return absolute;}
 void tracking(bool b){trackingOn=b;}
 void enable(bool b){powered=b;}
 void captureNominalIndexPositions(){++captures;nominal1=axis1.coordinate;nominal2=axis2.coordinate;}
} mount;
struct {
 bool enabled=true,software=true,sync=true; int reject=0,checks=0,writes=0;
 bool isEnabled(){return enabled;}
 bool hasSoftwareLimits(){return software;}
 bool hasSyncAxisLimits(){return sync;}
 CommandError validateInstrumentCoordinate(int axis,double){
   ++checks;assert(writes==0);return axis==reject?CE_SLEW_ERR_OUTSIDE_LIMITS:CE_NONE;
 }
 CommandError setInstrumentCoordinate(int axis,double x,bool){
   ++writes;(axis==1?axis1:axis2).coordinate=x;return CE_NONE;
 }
} limits;
struct {int state=0,alignResets=0;bool firstGoto=false;void alignReset(){++alignResets;}} goTo;
struct {int state=0,stops=0;void stop(){++stops;}} guide;
struct {bool trusted=false;void setTrusted(bool b){trusted=b;}} startupAuthority;
struct {void yieldMicros(int){}} tasks;
struct {struct {struct {int sign=-1;} latitude;} locationEx;} site;
struct Home {
 int state=0;bool offsets=false;
 struct {struct {double senseOffset=10;} axis1,axis2;} settings;
 void init(){} bool useOffset(){return offsets;}
 Coordinate getPosition(int){return {};}
 CommandError reset(bool=true,bool=false,bool=false);
} home;
void fresh(){axis1={};axis2={};mount={};limits={};goTo={};guide={};startupAuthority={};home={};}
void preserved(){
 assert(axis1.counter==123 && axis2.counter==123);
 assert(axis1.resets==0 && axis2.resets==0);
 assert(mount.captures==0 && mount.nominal1==7 && mount.nominal2==8);
}
'''

cases = r'''
int main(){
 constexpr bool restricted=AXIS1_WRAP==OFF && AXIS1_SECTOR_GEAR==OFF && AXIS2_TANGENT_ARM==OFF;
 // Every ordinary reset with absolute sources must preserve coordinates and references.
 for(bool sync:{false,true})for(bool full:{false,true}){
   fresh();mount.absolute=true;limits.sync=sync;
   assert(home.reset(full)==CE_NONE);preserved();
   assert(axis1.coordinate==4 && axis2.coordinate==4 && limits.writes==0);
   assert(!mount.trackingOn && !startupAuthority.trusted);
 }
 // Absolute startup establishes mapping; later authoritative resets only capture its reference.
 fresh();mount.absolute=true;
 assert(home.reset(true,false,true)==CE_NONE);
 assert(axis1.counter==0 && axis2.counter==0 && limits.writes==2 && mount.captures==1);
 assert(!startupAuthority.trusted);
 fresh();mount.absolute=true;
 assert(home.reset(true,true)==CE_NONE);
 assert(axis1.counter==123 && axis2.counter==123 && limits.writes==0);
 assert(mount.captures==1 && startupAuthority.trusted);
 // In-range sync changes mapping only; wrapping/sector/tangent mounts retain full reset.
 fresh();assert(home.reset()==CE_NONE);
 assert(axis1.coordinate==1 && axis2.coordinate==2 && limits.writes==2);
 assert(!mount.trackingOn && !mount.powered && goTo.firstGoto && goTo.alignResets==1);
 assert(mount.trackingRateOffsetRA==0 && mount.trackingRateOffsetDec==0);
 assert(!startupAuthority.trusted);
 if(restricted){preserved();assert(limits.checks==2 && mount.syncFromOnStepToEncoders);}
 else{assert(axis1.counter==0 && axis2.counter==0 && mount.captures==1 && limits.checks==0);}
 // Reject either axis before modifying either coordinate/counter/nominal reference.
 if(restricted)for(int bad:{1,2})for(bool full:{false,true}){
   fresh();limits.reject=bad;
   assert(home.reset(full)==CE_SLEW_ERR_OUTSIDE_LIMITS);preserved();
   assert(limits.checks==bad && limits.writes==0 && axis1.coordinate==4 && axis2.coordinate==4);
   assert(!mount.syncFromOnStepToEncoders && !startupAuthority.trusted);
   assert(!mount.trackingOn && mount.powered==!full);
 }
 // Disabling any prerequisite restores counter initialization.
 for(int disabled=0;disabled<3;++disabled){
   fresh();if(disabled==0)limits.enabled=false;else if(disabled==1)limits.software=false;else limits.sync=false;
   assert(home.reset()==CE_NONE);
   assert(axis1.counter==0 && axis2.counter==0 && mount.captures==1 && limits.checks==0);
 }
 // Sensed homing may establish a new reference and apply signed sensor offsets.
 fresh();home.offsets=true;home.state=HS_HOMING;limits.reject=2;
 assert(home.reset(false,true)==CE_NONE);
 assert(axis1.counter==0 && axis2.counter==0 && mount.captures==1 && startupAuthority.trusted);
 assert(std::abs(axis1.coordinate-(1-arcsecToRad(10)))<1e-12);
 assert(std::abs(axis2.coordinate-(2+arcsecToRad(10)))<1e-12);
 assert(goTo.alignResets==0 && mount.powered);
 // Busy motion must be aborted/rejected before changing position or tracking.
 fresh();goTo.state=1;
 assert(home.reset()==CE_SLEW_IN_MOTION);preserved();
 assert(axis1.aborts==1 && axis2.aborts==1 && mount.trackingOn && limits.writes==0);
 for(int state:{int(GU_HOME_GUIDE),2}){
   fresh();guide.state=state;
   assert(home.reset()==CE_SLEW_IN_MOTION);preserved();
   assert(guide.stops==(state==GU_HOME_GUIDE) && mount.trackingOn && limits.writes==0);
 }
 // A failed counter reset must not write coordinates or grant startup trust.
 for(int bad:{1,2}){
   fresh();(bad==1?axis1:axis2).fail=true;
   assert(home.reset(true,true)==CE_SLEW_IN_MOTION);
   assert(limits.writes==0 && mount.captures==0 && !startupAuthority.trusted && !mount.powered);
 }
 std::cout << "Home reset coordinate/reference preservation passed\n";
}
'''

with tempfile.TemporaryDirectory(prefix='onstep-home-reset-') as temp:
    path = Path(temp)
    cpp = path / 'home_reset.cpp'
    cpp.write_text(fixture + reset + cases)
    for mode, flags in {'normal': (0, 0, 0), 'wrap': (1, 0, 0),
                        'sector': (0, 1, 0), 'tangent': (0, 0, 1)}.items():
        exe = path / mode
        defines = [f'-D{name}={value}' for name, value in zip(
            ('AXIS1_WRAP', 'AXIS1_SECTOR_GEAR', 'AXIS2_TANGENT_ARM'), flags)]
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-no-pie', *defines, str(cpp), '-o', str(exe)], check=True)
        print(f'{mode}:', flush=True)
        subprocess.run([str(exe)], check=True)
