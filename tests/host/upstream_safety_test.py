"""Upstream safety regressions using real functions and a simulated NV device.

No hardware is accessed. CRC and NvVolume are compiled in full; command blocks,
parsers, coordinate transforms and abort handlers are extracted from the tree.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text()


def block(text, marker, body_only=False):
    start = text.index(marker)
    brace = text.index('{', start)
    end, depth = brace + 1, 1
    while depth:
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
        end += 1
    return text[brace + 1:end - 1] if body_only else text[start:end]


def function(path, signature):
    return block(read(path), signature)


prefix = r'''
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <cerrno>
#include <cassert>
#include <iostream>
#include <array>
#include "src/lib/nv/NvVolume.h"
#include "src/telescope/mount/coordinates/Align.bounds.h"
using std::isfinite;
#define VLF(...)
#define DLF(...)
#define DL1(...)
#define AXIS2_TANGENT_ARM_CORRECTION OFF
#define CRC_YIELD_BYTES 0
#define HAL_RESET() (++resetCalls)
enum CommandError {CE_NONE,CE_0,CE_PARAM_FORM,CE_PARAM_RANGE,CE_SLEW_ERR_OUTSIDE_LIMITS};
enum PierSide {PIER_SIDE_NONE,PIER_SIDE_EAST,PIER_SIDE_WEST};
constexpr int ALTAZM=3,ALTALT=4,GEM=1,FORK=2;
enum {HS_NONE,HS_HOMING,PS_UNPARKED,PS_PARKING};
unsigned long clockMs=0;
int resetCalls=0;
unsigned long millis(){return clockMs;}
struct {void yield(unsigned long n){clockMs+=n;}} tasks;
struct MemoryDevice: NvDevice {
 std::array<uint8_t,512> bytes{},durable{};
 bool writeFail=false,commitFail=false,stalled=false,pending=false;
 int polls=0,commits=0;
 uint32_t sizeBytes()const override{return bytes.size();}
 IoStatus read(uint16_t a,void* p,uint16_t n)override{
   if(a+n>bytes.size())return IoStatus::OutOfRange;
   memcpy(p,bytes.data()+a,n);return IoStatus::Ok;
 }
 IoStatus write(uint16_t a,const void* p,uint16_t n)override{
   if(writeFail)return IoStatus::IoError;
   if(a+n>bytes.size())return IoStatus::OutOfRange;
   memcpy(bytes.data()+a,p,n);return IoStatus::Ok;
 }
 bool hasCommit()const override{return true;}
 IoStatus commit()override{++commits;if(commitFail)return IoStatus::IoError;pending=true;return IoStatus::Ok;}
 bool commitDone()const override{return !pending;}
 void poll()override{++polls;if(!stalled && pending && polls>=2){durable=bytes;pending=false;}}
} device;
NvVolume volume;
struct KvPartition {
 enum class Status {Ok,Error};
 bool fail=false;int writes=0;
 template<class T>Status put(uint32_t,const T&){++writes;return fail?Status::Error:Status::Ok;}
} kvStore;
struct Nv {
 NvVolume& volume(){return ::volume;}
 MemoryDevice& active(){return device;}
 void poll(){device.poll();}
 KvPartition& kv(){return kvStore;}
} nvService;
Nv& nv(){return nvService;}
struct Convert {bool atof2(char*,double*,bool=true);} convert;
struct Axis {float backlash=0;void setBacklash(float x){backlash=x;}} axis1,axis2;
struct Mount {
 bool trackingOn=false;int trackingCalls=0;
 void tracking(bool b){trackingOn=b;++trackingCalls;}
 struct {struct {float axis1=1,axis2=2;} backlash;} settings;
} mount;
struct Home {int state=HS_HOMING;bool failed=false,wasTracking=true;void requestAborted();} home;
struct Park {
 int state=PS_PARKING;bool wasTracking=true;uint32_t nvKey=1;
 struct {int state=PS_PARKING;} settings;
 void requestAborted();
} park;
struct {struct {double latitude=37;} location;} site;
'''

align_header = read('src/telescope/mount/coordinates/Align.hs.h')
prefix += align_header[align_header.index('typedef struct Coordinate'):align_header.index('#if ALIGN_MAX_NUM_STARS > 1')]
prefix += align_header[align_header.index('typedef struct AlignModel'):align_header.index('class GeoAlign')]
prefix += r'''
struct Transform {
 int mountType=GEM;
 bool isEquatorial(){return mountType==GEM || mountType==FORK;}
 Coordinate instrumentToMount(double,double,PierSide=PIER_SIDE_NONE,double=0);
} transform;
struct GeoAlign {
 AlignModel model{};bool modelIsReady=true;int mountType=ALTAZM;
 float cosLat=0,sinLat=1;
 CommandError setCoefficient(float&,const char*,float,bool=false);
 void observedPlaceToMount(Coordinate*);
 void mountToObservedPlace(Coordinate*);
};
struct Limits {
 struct SyncLimitSettings {float pole=85,axis1=OFF,axis2=OFF;} syncSettings;
 struct {float pastMeridianE=0,pastMeridianW=0;} settings;
 uint32_t nvKey=1,syncNvKey=2;
 float getSyncPoleLimit(){return syncSettings.pole==OFF?90:syncSettings.pole;}
 CommandError validateSyncPole(double);
 bool setSync(char*,CommandError*);
} limits;
'''

# Compile full real storage implementation with the real CRC header, omitting
# only its scheduler include; CRC yielding is disabled for this host fixture.
crc = re.sub(r'^#(?:include "../tasks/OnTask.h"|pragma once)\s*$', '', read('src/lib/math/Crc.h'), flags=re.M)
nv_source = re.sub(r'^#include.*$', '', read('src/lib/nv/NvVolume.cpp'), flags=re.M)
functions = crc + nv_source
for path, signature in [
    ('src/lib/convert/Convert.cpp', 'bool Convert::atof2('),
    ('src/telescope/mount/coordinates/Align.model.cpp', 'CommandError GeoAlign::setCoefficient('),
    ('src/telescope/mount/coordinates/Align.hs.cpp', 'void GeoAlign::observedPlaceToMount('),
    ('src/telescope/mount/coordinates/Align.hs.cpp', 'void GeoAlign::mountToObservedPlace('),
    ('src/telescope/mount/coordinates/Transform.cpp', 'Coordinate Transform::instrumentToMount('),
    ('src/telescope/mount/limits/Limits.cpp', 'CommandError Limits::validateSyncPole('),
    ('src/telescope/mount/home/Home.cpp', 'void Home::requestAborted('),
    ('src/telescope/mount/park/Park.cpp', 'void Park::requestAborted('),
]:
    functions += '\n' + function(path, signature)
commands = read('src/telescope/Telescope.command.cpp')
for name, marker in [('nvReset', '// :ENVRESET#'), ('mcuReset', '// :ERESET#')]:
    code = commands[commands.index(marker):]
    functions += '\nvoid ' + name + '(char* reply, CommandError* commandError){\n'
    functions += 'bool numeric=true;bool* numericReply=&numeric;\n'
    functions += block(code, 'if (command[1]', body_only=True) + '\n}\n'
functions += '\nbool Limits::setSync(char* parameter, CommandError* commandError){\n'
functions += block(read('src/telescope/mount/limits/Limits.command.cpp'),
                   "if (command[1] == 'X' && parameter[0] == 'E')", body_only=True)
functions += '\nreturn true;\n}\n'

main = r'''
void prepareStorage(){
 device=MemoryDevice();volume=NvVolume();clockMs=0;resetCalls=0;
 assert(volume.init(device)==NvVolume::Status::Ok);
 assert(volume.formatBegin("TEST",1)==NvVolume::Status::Ok);
 assert(volume.formatAddPartition("SETTINGS",0));
 assert(volume.formatCommit()==NvVolume::Status::Ok);
 assert(volume.mount()==NvVolume::Status::Ok);
 device.polls=0;
}
void storageTests(){
 prepareStorage();const auto before=device.bytes;
 for(int i=0;i<4;i++){
   assert(volume.invalidateNextMount()==NvVolume::Status::Ok);
   assert(memcmp(before.data(),device.bytes.data(),14)==0);
   assert(volume.mount()!=NvVolume::Status::Ok);
 }
 char reply[128]{};CommandError error=CE_NONE;
 prepareStorage();nvReset(reply,&error);
 assert(error==CE_NONE && strstr(reply,"will be cleared"));
 assert(device.polls>=2 && !device.pending && device.bytes==device.durable);
 device.bytes=device.durable;assert(volume.mount()!=NvVolume::Status::Ok);
 for(int failure=0;failure<3;failure++){
   prepareStorage();error=CE_NONE;
   device.writeFail=failure==0;device.commitFail=failure==1;device.stalled=failure==2;
   nvReset(reply,&error);assert(error==CE_0 && strstr(reply,"failed"));
   if(device.stalled)assert(clockMs==30000);
 }
 prepareStorage();error=CE_NONE;mcuReset(reply,&error);
 assert(error==CE_NONE && resetCalls==1 && device.polls>=2);
 prepareStorage();error=CE_NONE;device.stalled=true;mcuReset(reply,&error);
 assert(error==CE_0 && resetCalls==0);
 std::cout<<"NV repeated reset, durable flush, I/O failure and timeout checks passed\n";
}
void parsingTests(){
 double d=42;
 for(const char* s:{"","+","-",".","+.","-.","1.2.3","nan","1x"}){
   char text[32];strcpy(text,s);assert(!convert.atof2(text,&d));assert(d==42);
 }
 for(const char* s:{"0","-1.25","+.5","123."}){
   char text[32];strcpy(text,s);assert(convert.atof2(text,&d));assert(d==atof(s));
 }
 GeoAlign align;float coefficient=0.01f;
 for(const char* s:{"","+","1x","999999999999999999999999","16385"}){
   assert(align.setCoefficient(coefficient,s,AlignBounds::cone)!=CE_NONE);
   assert(coefficient==0.01f);
 }
 assert(align.setCoefficient(coefficient,"16384",AlignBounds::cone)==CE_NONE);
 assert(coefficient==AlignBounds::cone);
 assert(align.setCoefficient(coefficient,"360",AlignBounds::phase,true)==CE_NONE);
 assert(coefficient==AlignBounds::phase);
 assert(!AlignBounds::valid(NAN,AlignBounds::index));
 assert(!AlignBounds::valid(INFINITY,AlignBounds::index));
 std::cout<<"numeric parsing and alignment coefficient bounds checks passed\n";
}
void coordinateTests(){
 constexpr double tolerance=1e-5;
 for(int type:{GEM,ALTAZM,ALTALT})for(double lat:{-37.0,37.0}){
   transform.mountType=type;site.location.latitude=lat;
   const double pole=(lat>=0 || type==ALTAZM)?Deg90:-Deg90;
   for(PierSide side:{PIER_SIDE_EAST,PIER_SIDE_WEST})for(double delta:{-0.4,0.0,0.4}){
     auto c=transform.instrumentToMount(0.7,pole+delta*tolerance,side,tolerance);
     assert(c.pierSide==side);
     assert(fabs(c.a1-(side==PIER_SIDE_WEST?0.7-Deg180:0.7))<1e-12);
   }
   auto c=transform.instrumentToMount(0.7,pole+2*tolerance,PIER_SIDE_WEST,tolerance);
   assert(c.pierSide==(pole>0?PIER_SIDE_WEST:PIER_SIDE_EAST));
 }
 transform.mountType=GEM;limits.syncSettings.pole=85;
 assert(limits.validateSyncPole(degToRad(85))==CE_NONE);
 assert(limits.validateSyncPole(degToRad(86))==CE_SLEW_ERR_OUTSIDE_LIMITS);
 assert(limits.validateSyncPole(degToRad(-86))==CE_SLEW_ERR_OUTSIDE_LIMITS);
 limits.syncSettings.pole=OFF;assert(limits.validateSyncPole(degToRad(89))==CE_NONE);
 transform.mountType=ALTAZM;limits.syncSettings.pole=85;
 assert(limits.validateSyncPole(degToRad(89))==CE_NONE);
 GeoAlign align;
 align.model.azmCor=arcsecToRad(200);align.model.altCor=arcsecToRad(-300);
 align.model.doCor=arcsecToRad(80);align.model.ax1Cor=arcsecToRad(100);
 int count=0;
 for(int type:{ALTAZM,ALTALT,GEM})for(double elevation:{-80.0,0.0,60.0,85.0}){
   align.mountType=type;
   Coordinate c{};c.pierSide=PIER_SIDE_EAST;
   c.h=c.z=c.aa1=0.8;c.d=c.a=c.aa2=degToRad(elevation);
   align.observedPlaceToMount(&c);align.mountToObservedPlace(&c);
   const double x=type==ALTAZM?c.z:type==ALTALT?c.aa1:c.h;
   const double y=type==ALTAZM?c.a:type==ALTALT?c.aa2:c.d;
   assert(fabs(x-0.8)*cos(degToRad(elevation))<arcsecToRad(0.3));
   assert(fabs(y-degToRad(elevation))<arcsecToRad(0.3));++count;
 }
 // A non-finite inverse must fall back to finite index-only coordinates.
 align.mountType=ALTAZM;align.model.azmCor=NAN;
 Coordinate c{};c.z=0.8;c.a=1.0;c.pierSide=PIER_SIDE_EAST;
 align.observedPlaceToMount(&c);
 assert(fabs(c.z-(0.8-align.model.ax1Cor))<1e-6 && c.a==1.0);
 std::cout<<count<<" alignment round trips, non-finite fallback, pole orientation and Sync limit checks passed\n";
}
void abortTests(){
 for(bool wasTracking:{false,true}){
   mount=Mount();home=Home();park=Park();
   home.wasTracking=wasTracking;park.wasTracking=wasTracking;
   home.requestAborted();park.requestAborted();
   assert(home.failed && home.state==HS_NONE && park.state==PS_UNPARKED);
   assert(park.settings.state==PS_UNPARKED);
   assert(!mount.trackingOn && mount.trackingCalls==0);
   assert(axis1.backlash==1 && axis2.backlash==2);
 }
 std::cout<<"home/park abort keeps tracking disabled and restores backlash\n";
}
void syncSettingsTests(){
 limits=Limits();kvStore=KvPartition();
 auto set=[](const char* s){char p[32];strcpy(p,s);CommandError e=CE_NONE;assert(limits.setSync(p,&e));return e;};
 assert(set("EH,85.5")==CE_NONE && limits.getSyncPoleLimit()==85.5);
 assert(set("EI,12.25")==CE_NONE && limits.syncSettings.axis1==12.25);
 assert(set("EJ,30")==CE_NONE && limits.syncSettings.axis2==30);
 int writes=kvStore.writes;
 for(const char* s:{"EH,59","EH,91","EI,-1","EI,31","EJ,31","EI,.","EI,+","EH,"})
   assert(set(s)!=CE_NONE);
 assert(kvStore.writes==writes);
 kvStore.fail=true;
 assert(set("EI,1")==CE_0 && limits.syncSettings.axis1==12.25);
 assert(set("EH,60")==CE_0 && limits.getSyncPoleLimit()==85.5);
 kvStore.fail=false;
 assert(set("EH,90")==CE_NONE && limits.syncSettings.pole==OFF);
 assert(set("EI,0")==CE_NONE && limits.syncSettings.axis1==OFF);
 assert(set("EJ,0")==CE_NONE && limits.syncSettings.axis2==OFF);
 std::cout<<"runtime Sync settings, invalid input and failed-save preservation checks passed\n";
}
int main(){storageTests();parsingTests();coordinateTests();abortTests();syncSettingsTests();}
'''

with tempfile.TemporaryDirectory(prefix='onstep-safety-test-') as tmp:
    cpp, binary = Path(tmp) / 'test.cpp', Path(tmp) / 'test'
    cpp.write_text(prefix + functions + main)
    subprocess.run(['g++', '-std=c++17', '-O0', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I' + str(ROOT), '-I' + str(ROOT / 'tests/host'),
                    str(cpp), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
