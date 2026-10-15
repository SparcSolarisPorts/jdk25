#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build="$root/build/solaris-sparcv9-server-release"
jdk=${JDK25_IMAGE:-"$build/images/jdk"}
native=${JDK25_NATIVE_PATH:-"$build/images/test/hotspot/jtreg/native"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo "GNU timeout required" >&2; exit 1; }
[[ -f "$native/libVThreadPinner.so" ]] || { echo "Missing $native/libVThreadPinner.so; build test-image first" >&2; exit 1; }
out="$root/pinning-helper-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-modules jdk.management -sourcepath "$root/test/lib" \
  -d "$out/classes" "$root/tests/PinningHelperSmoke.java" || exit 1
status=0
for mode in interpreter c1 mixed c2; do
  flags=()
  case "$mode" in
    interpreter) flags+=(-Xint);;
    c1) flags+=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) flags+=(-Xbatch -XX:-TieredCompilation -XX:CompileThreshold=100);;
  esac
  echo "Running $mode; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" \
    --enable-native-access=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED \
    -Djava.library.path="$native" -Xmx256m "${flags[@]}" \
    -cp "$out/classes" PinningHelperSmoke > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" >> "$out/results.txt"
  tail -20 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
echo "Results: $out"
exit "$status"
