#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/condy-null-results-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/ConstantDynamicNullSmoke.java" > "$out/compile.log" 2>&1 || {
  tail -40 "$out/compile.log"
  exit 1
}
failed=0
for mode in interpreter c1 mixed c2; do
  flags=()
  case "$mode" in
    interpreter) flags=(-Xint);;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  echo "Running $mode"
  # Bound hangs during startup, constant resolution, compilation and shutdown.
  "$jdk/bin/java" "${flags[@]}" -Xmx256m \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    -cp "$out/classes" ConstantDynamicNullSmoke > "$out/$mode.log" 2>&1 &
  vm_pid=$!
  (
    for ((tick=0; tick<60; tick++)); do
      kill -0 "$vm_pid" 2>/dev/null || exit 0
      sleep 5
    done
    echo "Watchdog: $mode exceeded 300 seconds" > "$out/$mode.timeout"
    kill -TERM "$vm_pid" 2>/dev/null || exit 0
    sleep 5
    kill -KILL "$vm_pid" 2>/dev/null || true
  ) &
  watchdog_pid=$!
  wait "$vm_pid"
  rc=$?
  kill "$watchdog_pid" 2>/dev/null || true
  wait "$watchdog_pid" 2>/dev/null || true
  if [[ -f "$out/$mode.timeout" ]]; then rc=124; cat "$out/$mode.timeout"; fi
  echo "$mode exit=$rc" >> "$out/results.txt"
  if ((rc == 0)) && grep -q '^PASS:' "$out/$mode.log"; then
    grep '^PASS:' "$out/$mode.log"
  else
    tail -40 "$out/$mode.log"
    failed=1
  fi
done
echo "Results: $out"
exit "$failed"
