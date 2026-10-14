#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo "GNU timeout required" >&2; exit 1; }
out="$root/vector-memory-alignment-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-modules jdk.incubator.vector -d "$out/classes" "$root/tests/VectorMemoryAlignmentSmoke.java" || exit 1
status=0
for mode in c1 mixed c2 older-vis; do
  flags=(-Xbatch)
  case "$mode" in
    c1) flags+=(-XX:TieredStopAtLevel=1);;
    c2) flags+=(-XX:-TieredCompilation -XX:CompileThreshold=100);;
    older-vis) flags+=(-XX:-TieredCompilation -XX:UseVIS=2);;
  esac
  echo "Running $mode; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" --add-modules jdk.incubator.vector \
    -Xmx256m "${flags[@]}" -cp "$out/classes" VectorMemoryAlignmentSmoke > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" >> "$out/results.txt"
  tail -20 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
echo "Results: $out"
exit "$status"
