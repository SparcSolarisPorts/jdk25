#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
out=$(mktemp -d "$root/full-gc-entry-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
mkdir -p "$out/classes"
ulimit -c 0
"$jdk/bin/javac" --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -d "$out/classes" "$root/tests/ContinuationFullGCEntrySmoke.java" > "$out/compile.log" 2>&1 || {
  cat "$out/compile.log"; exit 1;
}
status=0
for mode in interpreter c1 mixed c2; do
  flags=()
  case "$mode" in
    interpreter) flags=(-Xint) ;;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1) ;;
    mixed) flags=(-Xbatch) ;;
    c2) flags=(-Xcomp -XX:-TieredCompilation) ;;
  esac
  echo "Running $mode mounted full GC; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" \
    --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
    -Xms32m -Xmx256m -XX:+UseG1GC -XX:-ExplicitGCInvokesConcurrent \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" "${flags[@]}" \
    -cp "$out/classes" ContinuationFullGCEntrySmoke > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" | tee -a "$out/results.txt"
  tail -8 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
if command -v zip >/dev/null 2>&1; then
  (cd "$out" && find . -type f \( -name '*.log' -o -name 'results.txt' \) -print | zip -q evidence.zip -@)
  echo "Text evidence: $out/evidence.zip"
fi
echo "Results: $out"
exit "$status"
