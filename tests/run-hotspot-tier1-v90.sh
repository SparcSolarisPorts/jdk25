#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec python3 "$here/run-hotspot-tier1-v88.py" "$@"
