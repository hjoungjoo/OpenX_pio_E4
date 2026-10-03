#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test_binary=$(mktemp /tmp/onstepx-command-test.XXXXXX)
trap 'rm -f "$test_binary"' EXIT
"${CXX:-c++}" -std=c++17 -g -O1 -Wall -Wextra \
  -fsanitize=address,undefined -fno-sanitize-recover=all \
  -Itests/host -I. tests/host/command_validation_test.cpp \
  src/lib/commands/BufferCmds.cpp -o "$test_binary"
"$test_binary"
