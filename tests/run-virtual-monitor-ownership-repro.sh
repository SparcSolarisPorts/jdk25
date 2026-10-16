#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
out=$(mktemp -d "$root/virtual-monitor-ownership-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
mkdir -p "$out/classes"
"$jdk/bin/javac" -d "$out/classes" "$root/tests/VirtualMonitorOwnershipSmoke.java" || exit 1
status=0
for mode in interpreter c1 mixed c2; do
  flags=()
  case "$mode" in
    interpreter) flags+=(-Xint);;
    c1) flags+=(-Xbatch -XX:TieredStopAtLevel=1);;
    mixed) flags+=(-Xbatch);;
    c2) flags+=(-Xbatch -XX:-TieredCompilation);;
  esac
  echo "Running $mode; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" -Xmx256m \
    "${flags[@]}" "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    -cp "$out/classes" VirtualMonitorOwnershipSmoke > "$out/$mode.log" 2>&1
  rc=$?
  printf '%s exit=%s\n' "$mode" "$rc" | tee -a "$out/results.txt"
  tail -15 "$out/$mode.log"
  [[ $rc == 0 ]] || status=1
done
if command -v zip >/dev/null 2>&1; then
  zip -q -j "$out/evidence.zip" "$out"/*.log "$out/results.txt"
  echo "Evidence: $out/evidence.zip"
fi
echo "Results: $out"
exit "$status"
