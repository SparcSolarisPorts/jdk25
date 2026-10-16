#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build=${JDK25_BUILD:-"$root/build/solaris-sparcv9-server-release"}
jdk=${JDK25_IMAGE:-"$build/images/jdk"}
native="$build/images/test/hotspot/jtreg/native"
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
out=$(mktemp -d "$root/single-carrier-sleep-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
mkdir -p "$out/classes"
ulimit -c 0
if ! "$timeout_cmd" --kill-after=5s 60s "$jdk/bin/javac" -d "$out/classes" \
    "$root/tests/SingleCarrierSleepSmoke.java" > "$out/compile.log" 2>&1; then
  cat "$out/compile.log"
  echo "Compilation failed; results: $out"
  exit 1
fi
status=0
for agent in plain jvmti; do
  if [[ "$agent" == jvmti && ! -f "$native/libSuspendResume2.so" ]]; then
    echo "Missing native agent: $native/libSuspendResume2.so" | tee -a "$out/results.txt"
    status=1
    continue
  fi
  for mode in interpreter c1 mixed c2; do
    flags=()
    case "$mode" in
      interpreter) flags+=(-Xint);;
      c1) flags+=(-Xbatch -XX:TieredStopAtLevel=1);;
      mixed) flags+=(-Xbatch);;
      c2) flags+=(-Xbatch -XX:-TieredCompilation -XX:CompileThreshold=100);;
    esac
    [[ "$agent" != jvmti ]] || flags+=("-agentpath:$native/libSuspendResume2.so")
    name="$agent-$mode"
    echo "Running $name; log: $out/$name.log"
    "$timeout_cmd" --kill-after=5s 60s "$jdk/bin/java" \
      -Xmx256m -Djdk.virtualThreadScheduler.parallelism=1 \
      -Djdk.virtualThreadScheduler.maxPoolSize=1 \
      "${flags[@]}" "-XX:ErrorFile=$out/hs_err_${name}_pid%p.log" \
      -cp "$out/classes" SingleCarrierSleepSmoke "$out/$name.jfr" \
      > "$out/$name.log" 2>&1
    rc=$?
    printf '%s exit=%s\n' "$name" "$rc" | tee -a "$out/results.txt"
    tail -12 "$out/$name.log"
    [[ $rc == 0 ]] || status=1
  done
done
if command -v zip >/dev/null 2>&1; then
  zip -q -j "$out/evidence.zip" "$out"/*.log "$out/results.txt"
  echo "Evidence: $out/evidence.zip (text only; JFR recordings remain in the results directory)"
fi
echo "Results: $out"
exit "$status"
