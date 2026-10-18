#!/usr/bin/env bash
# Preserve the working Solaris configuration, adding the libffi FFM backend.
# No build-job overrides. No privileged installation.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
[[ $(uname -s) == SunOS && $(uname -p) == sparc ]] || { echo 'Run on Solaris/SPARC.' >&2; exit 1; }
ffi=${LIBFFI_HOME:-"$HOME/tools/libffi-3.4.8-sparcv9"}
boot=${BOOT_JDK:-/usr/jdk/jdk-21}
jtreg=${JTREG_HOME:-"$HOME/tools/jtreg-8.2.1/jtreg"}
gtest=${GTEST_HOME:-"$HOME/tools/googletest-1.14.0"}
[[ -f "$ffi/include/ffi.h" && -f "$ffi/lib/libffi.so.8" ]] || { echo "Missing libffi at $ffi; run bash tests/build-libffi-v86.sh first." >&2; exit 1; }
[[ -x "$boot/bin/java" && -f "$jtreg/lib/jtreg.jar" && -f "$gtest/googletest/include/gtest/gtest.h" ]] || { echo 'Missing boot JDK, jtreg or Google Test; check overrides.' >&2; exit 1; }
log=${LOG_DIR:-/tmp}/jdk25-panama-configure.log
mkdir -p "$(dirname "$log")"
echo "Configuring FFM native linker; log: $log"
if bash configure \
    --with-boot-jdk="$boot" --with-jvm-variants=server --enable-dtrace \
    --with-native-debug-symbols=internal --disable-warnings-as-errors \
    --disable-java-warnings-as-errors --with-jtreg="$jtreg" --with-gtest="$gtest" \
    DATE=/usr/gnu/bin/date STRIP=/usr/gnu/bin/gstrip \
    OBJCOPY=/usr/gnu/bin/objcopy CXXFILT=/usr/gnu/bin/c++filt \
    --with-version-string=25.0.5+1 '--with-vendor-name=OpenJDK Solaris SPARC' \
    --enable-fallback-linker --enable-libffi-bundling \
    --with-libffi-include="$ffi/include" --with-libffi-lib="$ffi/lib" \
    > "$log" 2>&1; then
  echo 'Configuration passed; next build images test-image.'
else
  rc=$?; tail -80 "$log"; exit "$rc"
fi
