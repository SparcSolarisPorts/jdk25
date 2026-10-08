#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
out="$root/compressed-oop-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/CompressedOopsSmoke.java" || exit 1
failed=0
for mode in interpreter c1 c2; do
  flags=()
  case "$mode" in
    interpreter) flags=(-Xint);;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    c2) flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  for base in 3g 5g; do
    name="$mode-$base"
    echo "Running $name"
    "$jdk/bin/java" "${flags[@]}" -Xshare:off -Xms32m -Xmx32m \
      -XX:+UseCompressedOops "-XX:HeapBaseMinAddress=$base" \
      -Xlog:gc+heap+coops=debug "-XX:ErrorFile=$out/hs_err_${name}_pid%p.log" \
      -cp "$out/classes" CompressedOopsSmoke > "$out/$name.log" 2>&1
    rc=$?
    echo "$name exit=$rc" >> "$out/results.txt"
    if ((rc == 0)); then tail -4 "$out/$name.log"; else tail -40 "$out/$name.log"; failed=1; fi
  done
done
echo "Results: $out"
exit "$failed"
