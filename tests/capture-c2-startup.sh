#!/usr/bin/env bash
# Replay jtreg's VMProps startup separately from the selected tests.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build=${JDK25_BUILD:-"$root/build/solaris-sparcv9-server-release"}
jdk=${JDK25_IMAGE:-"$build/images/jdk"}
prior=${1:-"$root/priority-1-2-rerun-20261015-233450"}
[[ "$prior" == /* ]] || prior="$PWD/$prior"
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
[[ -n "$timeout_cmd" ]] || { echo 'GNU timeout required' >&2; exit 1; }
[[ -x "$jdk/bin/java" ]] || { echo "Missing Java: $jdk/bin/java" >&2; exit 1; }
jtreg=${JDK25_JTREG_HOME:-}
if [[ -z "$jtreg" && -f "$build/spec.gmk" ]]; then
  jtreg=$(awk '$1 == "JT_HOME" { sub(/^[^=]*=[[:space:]]*/, ""); print; exit }' "$build/spec.gmk")
fi
[[ -f "$jtreg/lib/jtreg.jar" && -f "$jtreg/lib/javatest.jar" ]] || {
  echo 'Set JDK25_JTREG_HOME to the jtreg installation directory.' >&2; exit 1;
}
extra="$prior/work/extraPropDefns"
[[ -d "$extra/classes" && -d "$extra/bootClasses" ]] || {
  echo "Missing VMProps classes under $extra; pass the failed results directory." >&2; exit 1;
}
repeats=${JDK25_STARTUP_REPEATS:-3}
[[ "$repeats" =~ ^[1-9][0-9]*$ && "$repeats" -le 10 ]] || {
  echo 'JDK25_STARTUP_REPEATS must be 1 through 10.' >&2; exit 1;
}
out=$(mktemp -d "$root/c2-startup-results-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
# Core files are unnecessary for this small text capture; do not change the parent shell.
ulimit -c 0
{
  uname -a
  echo "JDK: $jdk"
  echo "Prior run: $prior"
  command -v gcc >/dev/null 2>&1 && gcc --version
  [[ ! -f "$jdk/release" ]] || cat "$jdk/release"
  [[ ! -f "$root/source-sha256.json" ]] || cat "$root/source-sha256.json"
} > "$out/environment.txt" 2>&1
status=0
for mode in default bounded nmt; do
  flags=()
  [[ "$mode" != bounded ]] || flags+=(-Xms32m -Xmx256m)
  [[ "$mode" != nmt ]] || flags+=(-XX:NativeMemoryTracking=detail)
  for ((n=1; n<=repeats; n++)); do
    case_dir="$out/$mode-$n"
    mkdir -p "$case_dir"
    echo "Running $mode startup $n/$repeats; log: $case_dir/run.log"
    (
      cd "$case_dir" || exit 1
      "$timeout_cmd" --kill-after=5s 30s "$jdk/bin/java" \
        -classpath "$jtreg/lib/javatest.jar:$jtreg/lib/jtreg.jar:$extra/classes" \
        "-Xbootclasspath/a:$extra/bootClasses" \
        -Dtest.vm.opts= -Dtest.tool.vm.opts= -Dtest.compiler.opts= -Dtest.java.opts= \
        "-Dtest.jdk=$jdk" "-Dcompile.jdk=$jdk" -Dtest.timeout.factor=4.0 \
        "-Dtest.nativepath=$build/images/test/hotspot/jtreg/native" \
        "-Dtest.root=$root/test/hotspot/jtreg" \
        "-Djava.library.path=$build/images/test/hotspot/jtreg/native" \
        -XX:+UnlockDiagnosticVMOptions -XX:+LogVMOutput -XX:-DisplayVMOutput \
        -XX:LogFile=vmprops.flags.final.vm.log -XX:+PrintFlagsFinal -XX:+WhiteBoxAPI \
        "-XX:ErrorFile=$case_dir/hs_err_pid%p.log" "${flags[@]}" \
        --add-exports java.base/jdk.internal.foreign=ALL-UNNAMED \
        --add-exports java.base/jdk.internal.misc=ALL-UNNAMED \
        com.sun.javatest.regtest.agent.GetJDKProperties \
        "--output-file=$case_dir/vm.properties" --system-properties \
        --modules=boot-layer requires.VMProps
    ) > "$case_dir/run.log" 2>&1
    rc=$?
    if [[ $rc == 0 && ! -s "$case_dir/vm.properties" ]]; then
      echo "VM exited without creating VMProps output." >> "$case_dir/run.log"
      rc=1
    fi
    printf '%s-%s exit=%s\n' "$mode" "$n" "$rc" | tee -a "$out/results.txt"
    if [[ $rc != 0 ]]; then
      status=1
      tail -8 "$case_dir/run.log"
    fi
  done
done
objdump_cmd=$(command -v gobjdump || command -v objdump || true)
if [[ -n "$objdump_cmd" ]]; then
  for object in gcm block arena; do
    file="$build/hotspot/variant-server/libjvm/objs/$object.o"
    [[ -f "$file" ]] || continue
    "$timeout_cmd" --kill-after=5s 30s "$objdump_cmd" -dr -C "$file" \
      > "$out/$object.disassembly.txt" 2>&1
    printf '%s disassembly exit=%s\n' "$object" "$?" >> "$out/capture-status.txt"
  done
else
  echo 'No gobjdump/objdump available; native disassembly not captured.' > "$out/capture-status.txt"
fi
if command -v zip >/dev/null 2>&1; then
  # Explicit text-only selection: never include cores, binaries or test work trees.
  (cd "$out" && find . -type f \( -name '*.txt' -o -name '*.log' -o -name '*.properties' \) \
    -print | zip -q evidence.zip -@)
  echo "Evidence: $out/evidence.zip"
fi
cat "$out/results.txt"
echo "Results: $out"
exit "$status"
