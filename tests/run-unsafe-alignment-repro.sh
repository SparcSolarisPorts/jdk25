#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/unsafe-alignment-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-exports java.base/jdk.internal.misc=ALL-UNNAMED \
  -d "$out/classes" "$root/tests/UnsafeAlignmentSmoke.java" || exit 1
failed=0
for mode in interpreter c1 mixed c2; do
  flags=()
  case "$mode" in
    interpreter) flags=(-Xint);;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    mixed) flags=(-Xbatch);;
    c2) flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  echo "Running $mode; log: $out/$mode.log"
  "$jdk/bin/java" --add-exports java.base/jdk.internal.misc=ALL-UNNAMED \
    "${flags[@]}" -Xshare:off -Xmx128m \
    -XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation "-XX:LogFile=$out/compilation_${mode}.xml" \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    -cp "$out/classes" UnsafeAlignmentSmoke > "$out/$mode.log" 2>&1 &
  pid=$!
  (sleep "${JDK25_SMOKE_TIMEOUT:-300}"; if kill -0 "$pid" 2>/dev/null; then
    echo "TIMEOUT: $mode" >> "$out/$mode.log"; kill -TERM "$pid" 2>/dev/null
    sleep 5; kill -KILL "$pid" 2>/dev/null
  fi) & watchdog=$!
  wait "$pid"; rc=$?
  kill "$watchdog" 2>/dev/null; wait "$watchdog" 2>/dev/null
  echo "$mode exit=$rc" >> "$out/results.txt"
  if ((rc == 0)); then tail -3 "$out/$mode.log"; else tail -40 "$out/$mode.log"; failed=1; fi
 done
 echo "Results: $out"
 exit "$failed"
