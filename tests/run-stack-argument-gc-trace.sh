#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
out="$root/stack-argument-gc-trace-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out/classes"
"$jdk/bin/javac" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -d "$out/classes" "$root/tests/StackArgumentThawSmoke.java" || exit 1
status=0
for mode in compressed uncompressed; do
  flags=()
  [[ "$mode" == uncompressed ]] && flags+=(-XX:-UseCompressedOops)
  echo "Running $mode GC trace; log: $out/$mode.runtime.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" \
    --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
    -Xmx256m -Xbatch -Xcomp -XX:-TieredCompilation "${flags[@]}" \
    '-XX:CompileCommand=dontinline,StackArgumentThawSmoke::*' \
    "-Xlog:continuations=debug:file=$out/$mode.runtime.log:uptime,level,tags" \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    -cp "$out/classes" StackArgumentThawSmoke gc > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" | tee -a "$out/results.txt"
  tail -15 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
if command -v zip >/dev/null 2>&1; then
  zip -q -j "$out/evidence.zip" "$out"/*.log "$out/results.txt"
  echo "Logs only: $out/evidence.zip"
fi
echo "Results: $out"
exit "$status"
