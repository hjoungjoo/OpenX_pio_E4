#line 1 "D:\\SVN\\telescope\\oozoo\\FW\\OnStepX\\src\\plugins\\website\\libApp\\misc\\Misc.h"
// -----------------------------------------------------------------------------------
// Misc functions to help with commands, etc.
#pragma once

#include "../../Common.h"

// convert hex to int, returns -1 on error
int hexToInt(String s);

// convert time to compact byte representation for intervalometer
uint8_t timeToByte(float t);

// convert compact byte representation to time for intervalometer
float byteToTime(uint8_t b);

// copy a string and always terminate the destination buffer
void strncpyex(char* dst, const char* src, size_t size);

// return temperature string with proper value and units for this locale
void localeTemperature(char* temperatureStr);

// return pressure string with proper value and units for this locale
void localePressure(char* pressureStr);

// return humidity string with proper value and units for this locale
void localeHumidity(char* humidityStr);
