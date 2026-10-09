#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/mixed-yield-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/VirtualThreadMixedYieldSmoke.java" || exit 1
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || {
  echo "GNU timeout (or gtimeout) is required to bound each JVM run" >&2
  exit 1
}
rc=0
for mode in mixed c1 c2; do
  flags=()
  case "$mode" in
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) flags=(-Xbatch -XX:-TieredCompilation -XX:CompileThreshold=100);;
  esac
  echo "Running $mode with interpreted yield0; log: $out/$mode.log"
  "$timeout_cmd" --signal=QUIT --kill-after=30s 180s \
    "$jdk/bin/java" -Xmx256m "${flags[@]}" \
    '-XX:CompileCommand=exclude,jdk.internal.vm.Continuation::yield0' \
    -XX:+PrintCompilation "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    -cp "$out/classes" VirtualThreadMixedYieldSmoke > "$out/$mode.log" 2>&1
  result=$?
  printf '%s exit=%s\n' "$mode" "$result" >> "$out/results.txt"
  if ((result == 124 || result == 137)); then
    echo "$mode TIMEOUT: JVM failed to exit; this is not a PASS"
  fi
  if ((result)); then tail -60 "$out/$mode.log";rc=1;else tail -1 "$out/$mode.log";fi
 done
echo "Results: $out"
exit "$rc"
