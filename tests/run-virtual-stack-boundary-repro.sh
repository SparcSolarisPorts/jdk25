#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo "GNU timeout required" >&2; exit 1; }
out="$root/virtual-stack-boundary-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED -d "$out/classes" "$root/tests/VirtualStackBoundarySmoke.java" || exit 1
status=0
for mode in interpreter c1 mixed c2; do
  flags=(-Xbatch '-XX:CompileCommand=dontinline,VirtualStackBoundarySmoke::*')
  case "$mode" in
    c1) flags+=(-Xcomp -XX:TieredStopAtLevel=1);;
    c2) flags+=(-Xcomp -XX:-TieredCompilation);;
    interpreter) flags=(-Xint);;
  esac
  echo "Running $mode; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
    -Xmx256m "${flags[@]}" -cp "$out/classes" VirtualStackBoundarySmoke > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" >> "$out/results.txt"
  tail -20 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
echo "Results: $out"
exit "$status"
