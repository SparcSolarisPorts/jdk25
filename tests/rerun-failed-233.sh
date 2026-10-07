#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 1
jobs=${JDK25_TEST_JOBS:-8}
jtreg="JOBS=$jobs;TIMEOUT_FACTOR=4;RETAIN=fail,error"
if [[ -n ${JCSTRESS_JAR:-} ]]; then
  [[ -f "$JCSTRESS_JAR" ]] || { printf 'Missing JCSTRESS_JAR: %s\n' "$JCSTRESS_JAR" >&2; exit 1; }
  jtreg="$jtreg;JAVA_OPTIONS=-Djdk.test.lib.artifacts.jcstress-tests-all=$JCSTRESS_JAR"
fi
gmake test-only JOBS="$jobs" TEST_JOBS="$jobs" \
  TEST="$(cat "$root/jdk25-failed-233.txt")" JTREG="$jtreg" \
  2>&1 | tee /tmp/jdk25-failed-233-v23.log
exit "${PIPESTATUS[0]}"
