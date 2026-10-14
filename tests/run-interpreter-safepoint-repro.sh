#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo "GNU timeout or gtimeout required" >&2; exit 1; }
out="$root/interpreter-safepoint-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/InterpreterSafepointSpinSmoke.java" || exit 1
status=0
for mode in interpreter mixed; do
  flags=(-Xint)
  if [[ $mode == mixed ]]; then
    flags=(-Xbatch -XX:-UseOnStackReplacement
      '-XX:CompileCommand=exclude,InterpreterSafepointSpinSmoke::spin')
  fi
  echo "Running $mode; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 30s "$jdk/bin/java" \
    -Xmx128m -XX:+SafepointTimeout -XX:SafepointTimeoutDelay=2000 \
    "${flags[@]}" -cp "$out/classes" InterpreterSafepointSpinSmoke \
    > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" >> "$out/results.txt"
  cat "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
echo "Results: $out"
exit "$status"
