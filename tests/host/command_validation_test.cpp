#include "src/lib/commands/BufferCmds.h"
#include "src/lib/commands/CommandValidation.h"
#include <cassert>
#include <cstring>
#include <initializer_list>

int main() {
  Buffer buffer;
  for (int i = 0; i < 100; ++i) {
    buffer.add('#');
    assert(!buffer.ready());
  }
  for (const char c : ":GVP#") if (c != '\0') buffer.add(c);
  assert(buffer.ready());
  assert(std::strcmp(buffer.getCmd(), "GV") == 0);
  assert(std::strcmp(buffer.getParameter(), "P") == 0);
  buffer.flush();
  assert(!buffer.ready());

  double value = 123.0;
  for (const char* text : {"", "nan", "NaN", "inf", "-inf", "1e999", "1e-999", "12junk", "12,3"}) {
    assert(!commandValidation::finiteDouble(text, value));
    assert(value == 123.0);
  }
  assert(commandValidation::finiteDouble("250.5", value) && value == 250.5);

  using commandValidation::IndexResult;
  int number = 7;
  const char* valueText = nullptr;
  for (const char* text : {"0,1", "-1,1", "258,1", "259,1", "999999999999999999999,1"}) {
    assert(commandValidation::parameterIndex(text, 20, number, valueText) == IndexResult::OutOfRange);
    assert(number == 7 && valueText == nullptr);
  }
  for (const char* text : {",1", "2x,1", "2", "x,1"}) {
    assert(commandValidation::parameterIndex(text, 20, number, valueText) == IndexResult::InvalidFormat);
  }
  assert(commandValidation::parameterIndex("2,12.5", 20, number, valueText) == IndexResult::Valid);
  assert(number == 2 && commandValidation::finiteDouble(valueText, value) && value == 12.5);
}
