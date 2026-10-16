#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
# The plain v70 cases already reproduce the failure without a JVMTI agent.
# Interpreted yield0 is a diagnostic control, not a production workaround.
JDK25_SINGLE_CARRIER_AGENTS=plain \
JDK25_SINGLE_CARRIER_MODES='c1 c2 c1-yield0-interpreted c2-yield0-interpreted' \
  bash "$root/tests/run-single-carrier-sleep-repro.sh"
