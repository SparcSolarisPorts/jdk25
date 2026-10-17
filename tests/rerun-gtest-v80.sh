#!/usr/bin/env bash
# Run all gtest jtreg wrappers; no rebuild or configure changes here.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 1
build=${JDK25_BUILD:-"$root/build/solaris-sparcv9-server-release"}
jdk=${JDK25_IMAGE:-"$build/images/jdk"}
jtreg=${JDK25_JTREG_HOME:-${JT_HOME:-"$HOME/tools/jtreg-8.2.1/jtreg"}}
runner=${JTREG_RUNNER_JAVA:-/usr/jdk/jdk-21/bin/java}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" && -x "$runner" && -x "$jdk/bin/java" && -f "$jtreg/lib/jtreg.jar" ]] || {
  echo 'Missing GNU timeout, runner JDK, test JDK or jtreg installation.' >&2; exit 1;
}
out=$(mktemp -d "$root/gtest-v80-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
echo "Running all gtest wrappers with ${JDK25_TEST_JOBS:-16} test jobs; cap 30 minutes"
echo "Log: $out/run.log"
"$timeout_cmd" --kill-after=15s 30m \
  "$runner" -Xmx512m -jar "$jtreg/lib/jtreg.jar" \
  -jdk:"$jdk" -agentvm -conc:"${JDK25_TEST_JOBS:-16}" -timeoutFactor:4 \
  -retain:fail,error -verbose:summary \
  -nativepath:"$build/images/test/hotspot/jtreg/native" \
  -w:"$out/work" -r:"$out/report" \
  test/hotspot/jtreg/gtest > "$out/run.log" 2>&1
rc=$?
printf 'jtreg/timeout exit=%s\n' "$rc" > "$out/results.txt"
if [[ "$rc" == 124 || "$rc" == 137 ]]; then
  echo 'Wall-clock limit reached; unfinished tests are not passes.' >> "$out/results.txt"
fi
# Package text diagnostics only, never cores, native libraries or class files.
if command -v zip >/dev/null 2>&1; then
  (cd "$out" && find . -type f \( -name '*.jtr' -o -name '*.log' -o -name '*.txt' -o -name '*.xml' \) -print | zip -q evidence.zip -@)
  echo "Text evidence: $out/evidence.zip"
fi
tail -50 "$out/run.log"
cat "$out/results.txt"
echo "Results: $out"
exit "$rc"
