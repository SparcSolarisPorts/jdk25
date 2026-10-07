#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/compact-string-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/CompactStringEqualsSmoke.java" || exit "$?"
status=0
for mode in interpreter c1 c2; do
  case "$mode" in
    interpreter) flags=(-Xint);;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  for header in normal compact compact-no-coops; do
    case "$header" in
      normal) headers=(-XX:-UseCompactObjectHeaders);;
      compact) headers=(-XX:+UseCompactObjectHeaders);;
      compact-no-coops) headers=(-XX:+UseCompactObjectHeaders -XX:-UseCompressedOops);;
    esac
    label="$mode-$header"
    "$jdk/bin/java" -Xmx256m "${flags[@]}" "${headers[@]}" \
      "-XX:ErrorFile=$out/hs_err_${label}_pid%p.log" \
      -cp "$out/classes" CompactStringEqualsSmoke 2>&1 | tee "$out/$label.log"
    rc=${PIPESTATUS[0]}
    printf '%s exit=%s\n' "$label" "$rc" >> "$out/results.txt"
    if ((rc != 0)); then status=1; fi
  done
done
printf '\nResults: %s\n' "$out/results.txt"
exit "$status"
