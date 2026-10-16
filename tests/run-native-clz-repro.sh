#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cxx=${JDK25_NATIVE_CXX:-g++}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
command -v "$cxx" >/dev/null 2>&1 || { echo "Native C++ compiler not found: $cxx" >&2; exit 1; }
out=$(mktemp -d "$root/native-clz-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
"$cxx" --version > "$out/compiler.txt" 2>&1
if ! "$timeout_cmd" --kill-after=5s 60s "$cxx" -m64 -std=c++17 -O2 -pthread \
    "$root/tests/NativeClzSmoke.cpp" -o "$out/native-clz" > "$out/build.log" 2>&1; then
  tail -40 "$out/build.log"
  echo "Compilation failed; results: $out"
  exit 1
fi
"$timeout_cmd" --kill-after=5s 60s "$out/native-clz" > "$out/run.log" 2>&1
rc=$?
printf 'native-clz exit=%s\n' "$rc" | tee "$out/results.txt"
cat "$out/run.log"
if command -v zip >/dev/null 2>&1; then
  zip -q -j "$out/evidence.zip" "$out/compiler.txt" "$out/build.log" "$out/run.log" "$out/results.txt"
  echo "Evidence: $out/evidence.zip"
fi
echo "Results: $out"
exit "$rc"
