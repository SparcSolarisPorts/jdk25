#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/header-test-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/ArrayHeaderSmoke.java" || exit "$?"
status=0
for mode in interpreter c1 c2; do
  case "$mode" in
    interpreter) mode_flags=(-Xint);;
    c1) mode_flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) mode_flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  for header in normal no-ccp no-compression compact compact-no-coops; do
    case "$header" in
      normal) header_flags=(-XX:-UseCompactObjectHeaders);;
      no-ccp) header_flags=(-XX:-UseCompactObjectHeaders -XX:-UseCompressedClassPointers);;
      no-compression) header_flags=(-XX:-UseCompactObjectHeaders -XX:-UseCompressedOops -XX:-UseCompressedClassPointers);;
      compact) header_flags=(-XX:+UseCompactObjectHeaders);;
      compact-no-coops) header_flags=(-XX:+UseCompactObjectHeaders -XX:-UseCompressedOops);;
    esac
    label="$mode-$header"
    printf '\nRunning %s\n' "$label"
    "$jdk/bin/java" -XX:+UnlockExperimentalVMOptions -XX:+UnlockDiagnosticVMOptions \
      -Xmx256m "${mode_flags[@]}" "${header_flags[@]}" \
      "-XX:ErrorFile=$out/hs_err_${label}_pid%p.log" \
      -cp "$out/classes" ArrayHeaderSmoke 2>&1 | tee "$out/$label.log"
    rc=${PIPESTATUS[0]}
    printf '%s exit=%s\n' "$label" "$rc" >> "$out/results.txt"
    if ((rc != 0)); then status=1; fi
  done
done
"$jdk/bin/java" -Xbatch -XX:-TieredCompilation -XX:LockingMode=0 -Xmx256m \
  "-XX:ErrorFile=$out/hs_err_monitor_pid%p.log" -cp "$out/classes" ArrayHeaderSmoke \
  2>&1 | tee "$out/monitor-only.log"
rc=${PIPESTATUS[0]}
printf 'monitor-only exit=%s\n' "$rc" >> "$out/results.txt"
if ((rc != 0)); then status=1; fi
printf '\nResults: %s\n' "$out/results.txt"
exit "$status"
