#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/small-stack-results-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/SmallStackStartupSmoke.java" > "$out/compile.log" 2>&1 || {
  tail -40 "$out/compile.log"
  exit 1
}
# Ask the VM for its accepted minimum; an invalid size must be rejected.
"$jdk/bin/java" -Xss1k -version > "$out/minimum.log" 2>&1
probe_rc=$?
minimum_k=$(sed -n 's/.*Specify at least \([0-9][0-9]*\)k.*/\1/p' "$out/minimum.log" | head -1)
if ((probe_rc == 0)) || [[ -z "$minimum_k" ]]; then
  echo "VM did not reject the tiny -Xss value with a supported minimum."
  cat "$out/minimum.log"
  exit 1
fi
echo "VM minimum Java stack: ${minimum_k}k"
failed=0
for mode in interpreter c1 mixed c2; do
  flags=()
  case "$mode" in
    interpreter) flags=(-Xint);;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  echo "Running $mode"
  # Bound hangs during startup, stack execution, compilation and shutdown.
  "$jdk/bin/java" "${flags[@]}" "-Xss${minimum_k}k" -Xmx256m -Xlog:os+thread=info \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    -cp "$out/classes" SmallStackStartupSmoke > "$out/$mode.log" 2>&1 &
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
