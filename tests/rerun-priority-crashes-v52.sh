#!/usr/bin/env bash
# Keep the original jtreg cases/options. Limit concurrent stress VMs and
# bound the entire batch in addition to each test's existing jtreg timeout.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo "GNU timeout required" >&2; exit 1; }
JDK25_TEST_LIST="$root/jdk25-priority-crashes-v52.txt" \
JDK25_TEST_JOBS="${JDK25_TEST_JOBS:-2}" JDK25_SAFEPOINT_DIAGNOSTICS=0 \
  "$timeout_cmd" --kill-after=15s 45m bash "$root/tests/rerun-priority-1-2.sh"
rc=$?
if [[ $rc == 124 || $rc == 137 ]]; then
  echo "Batch reached its wall-clock limit; unfinished cases are not passes." >&2
fi
exit "$rc"
