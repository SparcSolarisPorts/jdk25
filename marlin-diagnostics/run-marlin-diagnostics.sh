#!/usr/bin/env bash
# Diagnostic comparison only; no JVM/compiler source changes or installation.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
jdk=${JDK25_IMAGE:-/usr/jdk/instances/jdk-25}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -x "$jdk/bin/java" && -x "$jdk/bin/javac" && -n "$timeout_cmd" ]] || {
  echo 'Need the JDK25 image (set JDK25_IMAGE) and GNU timeout.' >&2; exit 1;
}
out=$(mktemp -d "$PWD/marlin-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
mkdir -p "$out/classes"
ulimit -c 0
"$jdk/bin/java" -version > "$out/version.log" 2>&1
cat "$out/version.log"
"$jdk/bin/javac" -d "$out/classes" "$here/MarlinOsrSmoke.java" > "$out/compile.log" 2>&1 || {
  cat "$out/compile.log"; exit 1;
}
if [[ -x "$jdk/bin/javap" ]]; then
  "$timeout_cmd" --kill-after=5s 30s "$jdk/bin/javap" -p -c -l \
    sun.java2d.marlin.Renderer > "$out/renderer-bytecode.log" 2>&1
fi
baseline=''
overall=0
for mode in interpreter c1 c1-profiled mixed no-osr c2; do
  flags=()
  case "$mode" in
    interpreter) flags=(-Xint) ;;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1 -XX:CompileThreshold=100) ;;
    c1-profiled) flags=(-Xbatch -XX:TieredStopAtLevel=2 -XX:CompileThreshold=100) ;;
    mixed) flags=(-Xbatch) ;;
    no-osr) flags=(-Xbatch -XX:-UseOnStackReplacement) ;;
    c2) flags=(-Xbatch -XX:-TieredCompilation -XX:CompileThreshold=100) ;;
  esac
  echo "Running $mode; cap 120s; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 120s "$jdk/bin/java" \
    -Djava.awt.headless=true -Xmx256m -XX:+PrintCompilation \
    "-Dmarlin.resultFile=$out/$mode.crc.txt" \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" \
    "${flags[@]}" -cp "$out/classes" MarlinOsrSmoke "${JDK25_MARLIN_ROUNDS:-4}" > "$out/$mode.log" 2>&1
  rc=$?
  marker=''
  if [[ -f "$out/$mode.crc.txt" ]]; then marker=$(cat "$out/$mode.crc.txt"); fi
  status='FAIL or incomplete'
  if [[ "$rc" == 0 && -n "$marker" ]]; then
    if [[ "$mode" == interpreter ]]; then baseline="$marker"; fi
    if [[ -n "$baseline" && "$marker" == "$baseline" ]]; then
      status=PASS
    elif [[ -z "$baseline" ]]; then
      status='Completed; interpreter reference unavailable'
      overall=1
    else
      status='FAIL pixel checksum differs'
      overall=1
    fi
  else
    overall=1
  fi
  printf '%s exit=%s status=%s crc=%s\n' "$mode" "$rc" "$status" "${marker:-none}" | tee -a "$out/results.txt"
  if [[ "$status" != PASS ]]; then tail -18 "$out/$mode.log"; fi
  # Retain evidence that the actual renderer got compiled, including OSR (%).
  sed -n '/sun.java2d.marlin.Renderer/p' "$out/$mode.log" > "$out/$mode.renderer-compilation.log"
done
if command -v zip >/dev/null 2>&1; then
  (cd "$out" && find . -type f \( -name '*.log' -o -name '*.txt' \) -print | zip -q evidence.zip -@)
  echo "Text evidence: $out/evidence.zip"
fi
cat "$out/results.txt"
echo "Results: $out"
exit "$overall"
