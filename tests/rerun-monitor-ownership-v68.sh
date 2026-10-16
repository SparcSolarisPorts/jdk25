#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
echo "Monitor ownership batch: ${JDK25_TEST_JOBS:-16} jobs; wall-clock limit 15 minutes"
JDK25_TEST_LIST="$root/jdk25-monitor-ownership-v68.txt" \
JDK25_TEST_JOBS="${JDK25_TEST_JOBS:-16}" JDK25_SAFEPOINT_DIAGNOSTICS=0 \
  "$timeout_cmd" --kill-after=15s 15m bash "$root/tests/rerun-priority-1-2.sh"
rc=$?
if [[ $rc == 124 || $rc == 137 ]]; then
  echo 'Batch reached its wall-clock limit; unfinished cases are not passes.' >&2
fi
exit "$rc"
