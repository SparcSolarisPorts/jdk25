#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
if (($# != 1)); then
  echo "Usage: bash tests/collect-priority-evidence.sh /path/to/priority-1-2-rerun-results" >&2
  exit 1
fi
results=$(cd "$1" && pwd)
[[ -d "$results/work" ]] || { echo "Missing $results/work" >&2; exit 1; }
stage=$(mktemp -d /tmp/jdk25-priority-evidence.XXXXXX)
mkdir -p "$stage/results" "$stage/source"
while IFS= read -r -d '' file; do
  rel=${file#"$results/"}
  mkdir -p "$stage/results/$(dirname "$rel")"
  # Bound noisy text logs while retaining both the start and failure tail.
  # XML compilation logs and core dumps are excluded by the find filter.
  bytes=$(ls -ln "$file" | gawk '{print $5}')
  if ((bytes > 4194304)); then
    {
      head -c 1048576 "$file"
      printf '\n--- middle omitted: original %s bytes; first/last 1 MiB retained ---\n' "$bytes"
      tail -c 1048576 "$file"
    } > "$stage/results/$rel"
  else
    cp "$file" "$stage/results/$rel"
  fi
done < <(find "$results" -type f \( -name '*.jtr' -o -name '*.log' -o -name 'summary.txt' -o -name 'tests.txt' \) -print0)
while IFS= read -r test; do
  test=${test%$'\r'}
  test=${test#jtreg:}
  test=${test%%#*}
  [[ -f "$root/$test" ]] || continue
  mkdir -p "$stage/source/$(dirname "$test")"
  cp "$root/$test" "$stage/source/$test"
  # JNI tests can delegate important behavior to a native companion.
  for file in "$root/$(dirname "$test")"/*.{c,cpp,h,hpp}; do
    [[ -f "$file" ]] || continue
    cp "$file" "$stage/source/$(dirname "$test")/"
  done
done < "$root/jdk25-priority-1-2-remaining.txt"
for rel in src/hotspot/cpu/sparc/frame_sparc.cpp src/hotspot/cpu/sparc/frame_sparc.hpp src/hotspot/cpu/sparc/frame_sparc.inline.hpp src/hotspot/share/runtime/continuation.cpp src/hotspot/cpu/sparc/macroAssembler_sparc.cpp src/hotspot/cpu/sparc/interp_masm_sparc.cpp src/hotspot/os/solaris/os_solaris.cpp src/hotspot/share/jfr/jni/jfrJavaSupport.cpp src/hotspot/share/jfr/dcmd/jfrDcmds.cpp src/hotspot/share/prims/unsafe.cpp src/hotspot/share/c1/c1_LIRGenerator.cpp src/hotspot/share/opto/library_call.cpp src/hotspot/os/posix/os_posix.cpp src/hotspot/os_cpu/solaris_sparc/os_solaris_sparc.cpp src/hotspot/cpu/sparc/compressedKlass_sparc.cpp src/hotspot/cpu/sparc/sparc.ad; do
  [[ -f "$root/$rel" ]] || continue
  mkdir -p "$stage/source/$(dirname "$rel")"
  cp "$root/$rel" "$stage/source/$rel"
done
archive="$root/$(basename "$results")-evidence.zip"
# A unique result directory normally gives a new archive; refuse stale ZIP entries.
[[ ! -e "$archive" ]] || { echo "Archive already exists: $archive; collected files remain in $stage" >&2; exit 1; }
(cd "$stage" && zip -qr "$archive" results source)
echo "Evidence: $archive"
echo "Collected files: $stage"
