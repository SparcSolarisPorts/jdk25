#!/usr/bin/env bash
# Updated implementation also serves the original v88 entry point.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec python3 "$here/run-hotspot-tier1-v88.py" "$@"
