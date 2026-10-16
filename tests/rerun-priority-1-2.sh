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
done < "${JDK25_TEST_LIST:-$root/jdk25-priority-1-2-remaining.txt}"
((${#tests[@]} > 0)) || { echo "Empty test selection" >&2; exit 1; }
out=${JDK25_RESULTS_DIR:-"$root/priority-1-2-rerun-$(date +%Y%m%d-%H%M%S)"}
mkdir -p "$out"
printf '%s\n' "${tests[@]}" > "$out/tests.txt"
echo "Running ${#tests[@]} selected cases; log: $out/run.log"
diagnostic_options=()
if [[ ${JDK25_SAFEPOINT_DIAGNOSTICS:-0} == 1 ]]; then
  # jtreg filters the environment of /othervm children. Pass these through
  # its VM option interface so the tested JVM actually receives them.
  diagnostic_options+=( -vmoption:-XX:+SafepointTimeout
    -vmoption:-XX:SafepointTimeoutDelay=2000 )
fi
if [[ ${JDK25_CONTINUATION_TRACE:-0} == 1 ]]; then
  diagnostic_options+=( '-vmoption:-Xlog:continuations=debug:file=continuations-%p.log:uptime,level,tags' )
fi
"$runner" -Xmx512m -jar "$jtreg_home/lib/jtreg.jar" \
  -jdk:"$jdk" -agentvm -conc:"${JDK25_TEST_JOBS:-16}" \
  -timeoutFactor:4 -retain:fail,error -verbose:summary \
  -nativepath:"$build/images/test/hotspot/jtreg/native" \
  -w:"$out/work" -r:"$out/report" \
  "${diagnostic_options[@]}" \
  "${tests[@]}" > "$out/run.log" 2>&1
rc=$?
tail -60 "$out/run.log"
echo "jtreg exit=$rc"
echo "Results: $out"
exit "$rc"
