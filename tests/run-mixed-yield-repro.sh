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
    --add-opens=java.base/java.lang=ALL-UNNAMED \
    --add-opens=java.base/jdk.internal.vm=ALL-UNNAMED \
    -XX:+UnlockDiagnosticVMOptions -XX:+ShowHiddenFrames \
    '-XX:CompileCommand=exclude,jdk.internal.vm.Continuation::yield0' \
    -XX:+PrintCompilation "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    "-Xlog:continuations=debug:file=$out/$mode.continuations.log:uptime,tid,tags" \
    "-DmixedYield.pidFile=$out/$mode.pid" \
    -cp "$out/classes" VirtualThreadMixedYieldSmoke > "$out/$mode.log" 2>&1 &
  run_pid=$!
  # Capture unmounted virtual-thread stacks while the Java watchdog is alive.
  # Each attach command is bounded independently of the target JVM.
  (
    sleep 15
    [[ -s "$out/$mode.pid" ]] || exit 0
    vm_pid=$(cat "$out/$mode.pid")
    [[ "$vm_pid" =~ ^[0-9]+$ ]] || exit 0
    kill -0 "$vm_pid" 2>/dev/null || exit 0
    "$timeout_cmd" --kill-after=5s 15s "$jdk/bin/jcmd" "$vm_pid" \
      Thread.vthread_scheduler > "$out/$mode.scheduler.log" 2>&1
    "$timeout_cmd" --kill-after=5s 15s "$jdk/bin/jcmd" "$vm_pid" \
      Thread.dump_to_file -overwrite -format=json "$out/$mode.threads.json" \
      > "$out/$mode.dump.log" 2>&1
    if command -v pstack >/dev/null 2>&1; then
      "$timeout_cmd" --kill-after=5s 15s pstack "$vm_pid" \
        > "$out/$mode.pstack.log" 2>&1
    fi
  ) &
  capture_pid=$!
  wait "$run_pid"
  result=$?
  kill "$capture_pid" 2>/dev/null || true
  wait "$capture_pid" 2>/dev/null || true
  printf '%s exit=%s\n' "$mode" "$result" >> "$out/results.txt"
  if ((result == 124 || result == 137)); then
    echo "$mode TIMEOUT: JVM failed to exit; this is not a PASS"
  fi
  if ((result)); then tail -60 "$out/$mode.log";rc=1;else tail -1 "$out/$mode.log";fi
 done
echo "Results: $out"
exit "$rc"
