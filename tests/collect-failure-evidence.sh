#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
stamp=$(date +%Y%m%d-%H%M%S)
list="$root/jdk25-evidence-$stamp.txt"
archive="$root/jdk25-evidence-$stamp.tar.gz"
grep_cmd=grep
command -v ggrep >/dev/null 2>&1 && grep_cmd=ggrep
tar_cmd=tar
command -v gtar >/dev/null 2>&1 && tar_cmd=gtar
: > "$list"
while IFS= read -r name; do printf '%s\n' "$name" >> "$list"; done \
  < <(find build/solaris-sparcv9-server-release/test-support -type f -name 'hs_err_pid*.log')
while IFS= read -r name; do
  if "$grep_cmd" -qE '^execStatus=(Failed|Error)|^test result: (Failed|Error)' "$name"; then
    printf '%s\n' "$name" >> "$list"
  fi
done < <(find build/solaris-sparcv9-server-release/test-support -type f -name '*.jtr')
for name in /tmp/build25.log /tmp/jdk25-failed-233-v22.log /tmp/jdk25-jtreg-all.log; do
  if [[ -f "$name" ]]; then
    cp "$name" "$root/jdk25-evidence-$stamp-$(basename "$name")"
    printf 'jdk25-evidence-%s-%s\n' "$stamp" "$(basename "$name")" >> "$list"
  fi
done
while IFS= read -r name; do printf '%s\n' "$name" >> "$list"; done \
  < <(find . -path './header-test-results-*/*' -type f)
"$tar_cmd" -czf "$archive" -T "$list"
printf '%s\n' "$archive"
