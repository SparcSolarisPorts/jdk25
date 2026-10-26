#!/usr/bin/env bash
# Full tier1, or the original unsuccessful cases with --failed. No build JOBS override.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec python3 "$here/run-hotspot-tier1-v88.py" "$@"
