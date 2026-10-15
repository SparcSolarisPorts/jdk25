#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo "GNU timeout required" >&2; exit 1; }
out="$root/stack-argument-thaw-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED -d "$out/classes" "$root/tests/StackArgumentThawSmoke.java" || exit 1
status=0
for mode in interpreter c1 mixed c2 c2-gc; do
  args=()
  flags=(-Xbatch '-XX:CompileCommand=dontinline,StackArgumentThawSmoke::*')
  case "$mode" in
    c1) flags+=(-Xcomp -XX:TieredStopAtLevel=1);;
    c2) flags+=(-Xcomp -XX:-TieredCompilation);;
    c2-gc) flags+=(-Xcomp -XX:-TieredCompilation); args=(gc);;
    interpreter) flags=(-Xint);;
  esac
  echo "Running $mode; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
    -Xmx256m "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" "${flags[@]}" -cp "$out/classes" StackArgumentThawSmoke "${args[@]}" > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" >> "$out/results.txt"
  tail -20 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
echo "Results: $out"
exit "$status"
