#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 1
build="$root/build/solaris-sparcv9-server-release"
jdk=${JDK25_IMAGE:-"$build/images/jdk"}
spec="$build/spec.gmk"
jtreg_home=${JT_HOME:-$(gawk '$1 == "JT_HOME" { sub(/^[^=]*=[[:space:]]*/, ""); print; exit }' "$spec")}
runner_jdk=$(gawk '$1 == "JTREG_JDK" { sub(/^[^=]*=[[:space:]]*/, ""); print; exit }' "$spec")
runner=${JTREG_RUNNER_JAVA:-"$runner_jdk/bin/java"}
[[ -f "$jtreg_home/lib/jtreg.jar" && -x "$runner" ]] || {
  echo "Cannot locate jtreg or its runner; check JT_HOME and JTREG_JDK in $spec" >&2
  exit 1
}
tests=()
while IFS= read -r test; do
  test=${test%$'\r'}
  [[ -n "$test" ]] && tests+=("${test#jtreg:}")
done < "$root/jdk25-priority-1-2-remaining.txt"
((${#tests[@]} > 0)) || { echo "Empty test selection" >&2; exit 1; }
out="$root/priority-1-2-rerun-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"
printf '%s\n' "${tests[@]}" > "$out/tests.txt"
echo "Running ${#tests[@]} selected cases; log: $out/run.log"
"$runner" -Xmx512m -jar "$jtreg_home/lib/jtreg.jar" \
  -jdk:"$jdk" -agentvm -conc:"${JDK25_TEST_JOBS:-16}" \
  -javaoptions:"-XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation -XX:LogFile=$out/hotspot_pid%p.xml" \
  -timeoutFactor:4 -retain:fail,error -verbose:summary \
  -nativepath:"$build/images/test/hotspot/jtreg/native" \
  -w:"$out/work" -r:"$out/report" \
  "${tests[@]}" > "$out/run.log" 2>&1
rc=$?
tail -60 "$out/run.log"
echo "jtreg exit=$rc"
echo "Results: $out"
exit "$rc"
