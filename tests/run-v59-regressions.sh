#!/usr/bin/env bash
# Run independent groups even when an earlier group fails.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 1
status=0
for test in run-virtual-stack-boundary-repro.sh run-stack-argument-thaw-repro.sh run-continuation-repro.sh run-mixed-yield-repro.sh; do
  printf '\nRunning %s\n' "$test"
  bash "tests/$test"
  rc=$?
  printf '%s exit=%s\n' "$test" "$rc"
  [[ $rc == 0 ]] || status=1
done
exit "$status"
