#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
out=$(mktemp -d "$root/redefine-continuation-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
# Prevent huge cores in this capture and its children only.
ulimit -c 0
echo "Original redefinition test; ${JDK25_TEST_JOBS:-16} jobs; 15-minute batch cap"
JDK25_TEST_LIST="$root/jdk25-redefine-continuation-v76.txt" \
JDK25_RESULTS_DIR="$out" JDK25_CONTINUATION_TRACE=1 \
JDK25_TEST_JOBS="${JDK25_TEST_JOBS:-16}" \
  "$timeout_cmd" --kill-after=15s 15m bash "$root/tests/rerun-priority-1-2.sh"
rc=$?
[[ $rc != 124 && $rc != 137 ]] || echo 'Batch limit reached; unfinished test is not a pass.'
evidence="$out/text-evidence"
mkdir -p "$evidence"
for f in "$out/run.log" "$out/tests.txt" "$root/source-sha256.json"; do
  [[ ! -f "$f" ]] || cp "$f" "$evidence/"
done
if [[ -d "$out/work" ]]; then
  while IFS= read -r f; do
    rel=${f#"$out"/}
    dst="$evidence/$rel"
    mkdir -p "$(dirname "$dst")"
    lines=$(wc -l < "$f")
    if ((lines > 4000)); then
      { head -2000 "$f"; echo '--- middle omitted; full log retained on host ---'; tail -2000 "$f"; } > "$dst"
    else
      cp "$f" "$dst"
    fi
  done < <(find "$out/work" -type f \( -name '*.jtr' -o -name 'continuations-*.log' -o -name 'hs_err*.log' \) -print)
fi
printf 'jtreg exit=%s\n' "$rc" > "$evidence/results.txt"
if command -v zip >/dev/null 2>&1; then
  (cd "$evidence" && find . -type f -print | zip -q "$out/evidence.zip" -@)
  echo "Text evidence: $out/evidence.zip"
fi
echo "Results: $out"
exit "$rc"
