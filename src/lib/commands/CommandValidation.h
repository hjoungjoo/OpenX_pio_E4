#pragma once

#include <cerrno>
#include <cmath>
#include <cstdlib>

namespace commandValidation {

// Parse the entire value before allowing a command to change runtime or NV state.
inline bool finiteDouble(const char* text, double& value) {
  char* end;
  errno = 0;
  const double candidate = strtod(text, &end);
  if (end == text || *end != '\0' || errno == ERANGE || !std::isfinite(candidate)) return false;
  value = candidate;
  return true;
}

enum class IndexResult { Valid, InvalidFormat, OutOfRange };

inline IndexResult parameterIndex(const char* text, int maximum, int& number, const char*& valueText) {
  char* end;
  errno = 0;
  const long candidate = strtol(text, &end, 10);
  if (end == text || *end != ',') return IndexResult::InvalidFormat;
  if (errno == ERANGE || candidate < 1 || candidate > maximum) return IndexResult::OutOfRange;
  number = static_cast<int>(candidate);
  valueText = end + 1;
  return IndexResult::Valid;
}

} // namespace commandValidation
