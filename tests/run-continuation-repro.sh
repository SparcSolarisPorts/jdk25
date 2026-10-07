#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/continuation-test-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -d "$out/classes" "$root/tests/ContinuationSmoke.java" \
  "$root/tests/ContinuationFastPath.java" || exit "$?"
status=0
for test in interpreter mixed compiled compiled-gc; do
  args=()
  case "$test" in
    interpreter) flags=(-Xint); main=ContinuationSmoke;;
    mixed) flags=(-Xbatch); main=ContinuationSmoke;;
    compiled) flags=(-Xcomp -XX:-TieredCompilation); main=ContinuationFastPath;;
    compiled-gc) flags=(-Xcomp -XX:-TieredCompilation); main=ContinuationFastPath; args=(gc);;
  esac
  printf '\nRunning %s\n' "$test"
  "$jdk/bin/java" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
    -XX:+UnlockExperimentalVMOptions -XX:+VMContinuations -Xmx256m \
    "${flags[@]}" "-XX:ErrorFile=$out/hs_err_${test}_pid%p.log" \
    -cp "$out/classes" "$main" "${args[@]}" 2>&1 | tee "$out/$test.log"
  rc=${PIPESTATUS[0]}
  printf '%s exit=%s\n' "$test" "$rc" >> "$out/results.txt"
  if ((rc != 0)); then status=1; fi
done
printf '\nResults: %s\n' "$out/results.txt"
exit "$status"
