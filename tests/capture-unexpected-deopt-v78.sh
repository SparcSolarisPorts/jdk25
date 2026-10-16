#!/usr/bin/env bash
# Replay the original first failing jtreg action with a bounded GDB signal ring.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build=${JDK25_BUILD:-"$root/build/solaris-sparcv9-server-release"}
jdk=${JDK25_IMAGE:-"$build/images/jdk"}
prior=${1:-"$root/priority-1-2-rerun-20261016-221049"}
[[ "$prior" == /* ]] || prior="$PWD/$prior"
timeout_cmd=$(command -v gtimeout || command -v timeout || true)
gdb_cmd=${JDK25_GDB:-$(command -v gdb || command -v ggdb || true)}
[[ -n "$timeout_cmd" && -n "$gdb_cmd" ]] || {
  echo 'GNU timeout and GDB with Python support are required. Set JDK25_GDB if needed.' >&2; exit 1;
}
[[ -x "$jdk/bin/java" ]] || { echo "Missing Java: $jdk/bin/java" >&2; exit 1; }
"$gdb_cmd" --batch --nx -ex 'python import gdb; print("GDB Python available")' > /tmp/jdk25-gdb-python-check.log 2>&1 || {
  cat /tmp/jdk25-gdb-python-check.log; exit 1;
}
jtreg=${JDK25_JTREG_HOME:-${JT_HOME:-}}
if [[ -z "$jtreg" && -f "$build/spec.gmk" ]]; then
  jtreg=$(gawk '$1 == "JT_HOME" { sub(/^[^=]*=[[:space:]]*/, ""); print; exit }' "$build/spec.gmk")
fi
[[ -f "$jtreg/lib/jtreg.jar" && -f "$jtreg/lib/javatest.jar" ]] || {
  echo 'Set JDK25_JTREG_HOME to the jtreg directory.' >&2; exit 1;
}
class_file=$(find "$prior/work/classes" -type f -path '*/compiler/codecache/stress/UnexpectedDeoptimizationAllTest.class' -print | head -1)
[[ -n "$class_file" ]] || { echo "Missing retained test classes under $prior/work/classes" >&2; exit 1; }
classes=${class_file%/compiler/codecache/stress/UnexpectedDeoptimizationAllTest.class}
whitebox="$classes/test/lib"
if [[ ! -f "$whitebox/jdk/test/whitebox/WhiteBox.class" ]]; then
  wb=$(find "$prior/work" -type f -path '*/jdk/test/whitebox/WhiteBox.class' -print | head -1)
  [[ -n "$wb" ]] || { echo 'Missing compiled WhiteBox.class' >&2; exit 1; }
  whitebox=${wb%/jdk/test/whitebox/WhiteBox.class}
fi
jta="$prior/work/compiler/codecache/stress/UnexpectedDeoptimizationAllTest.d/main.0.jta"
[[ -f "$jta" ]] || { echo "Missing original jtreg argument file: $jta" >&2; exit 1; }
out=$(mktemp -d "$root/unexpected-deopt-gdb-$(date +%Y%m%d-%H%M%S)-XXXXXX") || exit 1
mkdir -p "$out/scratch"
ulimit -c 0
cp "$root/tests/gdb-deopt-ring.py" "$out/capture.py"
cat > "$out/commands.gdb" <<GDB
set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debug-file-directory $jdk/lib/server:$build/support/modules_libs/java.base/server:$build/hotspot/variant-server/libjvm
source $out/capture.py
handle SIGSEGV stop noprint pass
handle SIGBUS stop noprint pass
handle SIGILL stop noprint pass
handle SIGABRT stop noprint pass
catch signal SIGSEGV SIGBUS SIGILL SIGABRT
commands
silent
python capture_deopt_signal()
continue
end
run
GDB
{
  uname -a
  "$gdb_cmd" --version | head -2
  echo "Image: $jdk"
  echo "Original run: $prior"
  echo "Class directory: $classes"
  echo "WhiteBox root: $whitebox"
  echo 'Mode: original platform-thread/non-segmented action; all caught signals passed onward'
} > "$out/environment.txt" 2>&1
classpath="$classes:$classes/test/lib:$root/test/lib:$root/test/hotspot/jtreg:$jtreg/lib/javatest.jar:$jtreg/lib/jtreg.jar"
echo "GDB capture: $out; wall-clock cap 180 seconds"
(
  cd "$out/scratch" || exit 1
  JDK25_GDB_OUT="$out" "$timeout_cmd" --kill-after=10s 180s \
    "$gdb_cmd" --batch --nx -q -x "$out/commands.gdb" --args "$jdk/bin/java" \
    "-Dtest.jdk=$jdk" "-Dcompile.jdk=$jdk" -Dtest.timeout.factor=4.0 \
    -Dtest.vm.opts= -Dtest.tool.vm.opts= -Dtest.compiler.opts= -Dtest.java.opts= \
    "-Dtest.root=$root/test/hotspot/jtreg" \
    -Dtest.name=compiler/codecache/stress/UnexpectedDeoptimizationAllTest.java \
    "-Dtest.classes=$classes" "-Dtest.src=$root/test/hotspot/jtreg/compiler/codecache/stress" \
    "-Dtest.class.path=$classes:$classes/test/lib:$root/test/hotspot/jtreg" \
    "-Dtest.nativepath=$build/images/test/hotspot/jtreg/native" \
    "-Djava.library.path=$build/images/test/hotspot/jtreg/native" \
    --add-modules java.base,java.management --add-exports java.base/jdk.internal.misc=ALL-UNNAMED \
    -classpath "$classpath" "-Xbootclasspath/a:$whitebox" \
    -XX:+UnlockDiagnosticVMOptions -XX:+WhiteBoxAPI -XX:+IgnoreUnrecognizedVMOptions \
    -XX:-DeoptimizeRandom \
    '-XX:CompileCommand=dontinline,compiler.codecache.stress.Helper$TestCase::method' \
    -XX:-SegmentedCodeCache "-XX:ErrorFile=$out/hs_err_pid%p.log" \
    com.sun.javatest.regtest.agent.MainWrapper "$jta"
) > "$out/gdb-console.log" 2>&1
rc=$?
printf 'gdb/timeout exit=%s\nDebugger status alone does not establish a test pass.\n' "$rc" > "$out/results.txt"
[[ ! -f "$out/inferior-exit.txt" ]] || cat "$out/inferior-exit.txt" >> "$out/results.txt"
[[ $rc != 124 && $rc != 137 ]] || echo 'Capture timed out; not a pass.' >> "$out/results.txt"
# Select only diagnostics: no test classes, old work directories, or core files.
if command -v zip >/dev/null 2>&1; then
  (cd "$out" && find . -type f \( -name '*.log' -o -name '*.txt' -o -name '*.gdb' \) -print | zip -q evidence.zip -@)
  echo "Text evidence: $out/evidence.zip"
fi
cat "$out/results.txt"
tail -12 "$out/gdb-console.log"
echo "Results: $out"
exit "$rc"
