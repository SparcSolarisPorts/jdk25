#!/usr/bin/env bash
# Capture Solaris native stacks from the actual test process tree before jtreg
# kills a timed-out child. No timeout changes or test-result overrides.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
[[ $(uname -s) == SunOS ]] || { echo "Run this on Solaris" >&2;exit 1; }
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" && -x /usr/bin/pstack ]] || {
  echo "Requires /usr/bin/pstack and GNU timeout (or gtimeout)" >&2;exit 1;
}
out="$root/native-timeout-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"
cat > "$out/tests.txt" <<'TESTS'
jtreg:test/hotspot/jtreg/runtime/jni/getCreatedJavaVMs/TestGetCreatedJavaVMs.java
jtreg:test/hotspot/jtreg/compiler/uncommontrap/TestStackBangMonitorOwned.java
TESTS
# These product options warn about a stuck safepoint without aborting the VM.
# JAVA_TOOL_OPTIONS also reaches JNI-created VMs in native child executables.
JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-XX:+SafepointTimeout -XX:SafepointTimeoutDelay=2000" \
JDK25_TEST_LIST="$out/tests.txt" JDK25_TEST_JOBS=2 \
  bash "$root/tests/rerun-priority-1-2.sh" > "$out/runner.log" 2>&1 &
runner_pid=$!
echo "Running two timeout cases; native captures: $out"
# Fresh process-tree snapshots avoid guessing the native child PID.
for delay in 60 120 120; do
  sleep "$delay"
  kill -0 "$runner_pid" 2>/dev/null || break
  tag=$(date +%H%M%S)
  ps -e -o pid= -o ppid= -o args= > "$out/processes-$tag.txt"
  gawk -v root="$runner_pid" '
    { pid[NR]=$1; parent[$1]=$2; command[$1]=$0 }
    END {
      child[root]=1
      for (pass=0;pass<NR;pass++) {
        changed=0
        for (i=1;i<=NR;i++) if (!child[pid[i]] && child[parent[pid[i]]]) {
          child[pid[i]]=1;changed=1
        }
        if (!changed) break
      }
      # Include every descendant: native test executable names need not
      # contain "java" or the legacy "exeGetCreatedJavaVMs" prefix.
      for (i=1;i<=NR;i++) if (child[pid[i]]) print pid[i]
    }' "$out/processes-$tag.txt" > "$out/pids-$tag.txt"
  while IFS= read -r pid; do
    "$timeout_cmd" --kill-after=5s 20s /usr/bin/pstack "$pid" > "$out/pstack-$tag-$pid.txt" 2>&1
  done < "$out/pids-$tag.txt"
done
wait "$runner_pid"
rc=$?
tail -60 "$out/runner.log"
echo "Native stack evidence: $out"
exit "$rc"
