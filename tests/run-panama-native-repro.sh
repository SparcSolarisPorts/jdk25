#!/usr/bin/env bash
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -x "$jdk/bin/java" && -x "$jdk/bin/javac" && -n "$timeout_cmd" ]] || { echo 'Need the built JDK25 image and GNU timeout.' >&2; exit 1; }
out=$(mktemp -d "$root/panama-native-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
mkdir -p "$out/classes"
ulimit -c 0
"$jdk/bin/java" -version > "$out/version.log" 2>&1
# Solaris/SPARC fixture must match the LP64 JDK. The C compiler needs no JDK headers.
cc=${JDK25_NATIVE_CC:-gcc}
if ! "$cc" -m64 -std=c11 -O2 -Wall -Wextra -Werror -fPIC -shared -pthread \
    "$root/tests/panama-native-v86.c" -o "$out/libpanamaNative.so" > "$out/compile-native.log" 2>&1; then
  cat "$out/compile-native.log"; exit 1
fi
file "$out/libpanamaNative.so" > "$out/native-file.log" 2>&1
ldd "$jdk/lib/libfallbackLinker.so" > "$out/linker-ldd.log" 2>&1
if ! "$jdk/bin/javac" -d "$out/classes" "$root/tests/PanamaNativeSmoke.java" > "$out/compile-java.log" 2>&1; then
  cat "$out/compile-java.log"; exit 1
fi
failed=0
for mode in interpreter c1 mixed c2; do
  case "$mode" in
    interpreter) flags=(-Xint);;
    c1) flags=(-Xbatch -XX:TieredStopAtLevel=1);;
    mixed) flags=(-Xbatch);;
    c2) flags=(-Xbatch -XX:-TieredCompilation);;
  esac
  echo "Running $mode Panama; cap 180s; log: $out/$mode.log"
  "$timeout_cmd" --kill-after=5s 180s "$jdk/bin/java" \
    --enable-native-access=ALL-UNNAMED -Dpanama.requireFallback=true -Xmx256m \
    "-XX:ErrorFile=$out/hs_err_${mode}_pid%p.log" "${flags[@]}" \
    -cp "$out/classes" PanamaNativeSmoke "$out/libpanamaNative.so" > "$out/$mode.log" 2>&1
  rc=$?
  if [[ "$rc" == 0 ]] && grep -q '^PASS: Panama native linker,' "$out/$mode.log"; then
    echo "$mode exit=0 PASS" | tee -a "$out/results.txt"
    tail -2 "$out/$mode.log"
  else
    echo "$mode exit=$rc FAIL or incomplete" | tee -a "$out/results.txt"
    tail -50 "$out/$mode.log"; failed=1
  fi
done
if command -v zip >/dev/null 2>&1; then
  (cd "$out" && find . -type f \( -name '*.log' -o -name '*.txt' \) -print | zip -q evidence.zip -@)
  echo "Text evidence: $out/evidence.zip"
fi
echo "Results: $out"
exit "$failed"
