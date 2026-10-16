
    
  
#!/bin/bash
# Configure and build Solaris/SPARC JDK images and native test images.
# Defaults match the working Solaris configuration, including Google Test.
# Overrides: BOOT_JDK, JDK_SOURCE_DIR, JTREG_HOME, GTEST_HOME, LOG_DIR.
# jcstress is supplied separately to jtreg; it has no configure option.

set -euo pipefail

BOOT_JDK="${BOOT_JDK:-/usr/jdk/jdk-21}"
JDK_SOURCE_DIR="${JDK_SOURCE_DIR:-$HOME/git/jdk25}"
JTREG_HOME="${JTREG_HOME:-$HOME/tools/jtreg-8.2.1/jtreg}"
GTEST_HOME="${GTEST_HOME:-$HOME/tools/googletest-1.14.0}"
LOG_DIR="${LOG_DIR:-/tmp}"

cd "$JDK_SOURCE_DIR"

[[ -x "$BOOT_JDK/bin/java" ]] || { echo "Missing boot JDK: $BOOT_JDK" >&2; exit 1; }
[[ -f "$JTREG_HOME/lib/jtreg.jar" ]] || { echo "Missing jtreg: $JTREG_HOME" >&2; exit 1; }
[[ -f "$GTEST_HOME/googletest/include/gtest/gtest.h" ]] || {
    echo "Missing Google Test source: $GTEST_HOME" >&2
    echo 'Install Google Test v1.14.0 or set GTEST_HOME to its source directory.' >&2
    exit 1
}
mkdir -p "$LOG_DIR"
configure_log="$LOG_DIR/jdk25-gtest-configure.log"
build_log="$LOG_DIR/jdk25-gtest-build.log"

echo "Configuring; log: $configure_log"
if bash configure \
    --with-boot-jdk="$BOOT_JDK" \
    --with-jvm-variants=server \
    --enable-dtrace \
    --with-native-debug-symbols=internal \
    --disable-warnings-as-errors \
    --disable-java-warnings-as-errors \
    --with-jtreg="$JTREG_HOME" \
    DATE=/usr/gnu/bin/date \
    STRIP=/usr/gnu/bin/gstrip \
    OBJCOPY=/usr/gnu/bin/objcopy \
    CXXFILT=/usr/gnu/bin/c++filt \
    --with-version-string=25.0.5+1 \
    '--with-vendor-name=OpenJDK Solaris SPARC' \
    --with-gtest="$GTEST_HOME" \
    > "$configure_log" 2>&1; then
    echo 'Configuration passed'
else
    rc=$?
    tail -80 "$configure_log"
    exit "$rc"
fi

echo "Building images and test-image; log: $build_log"
if gmake images test-image > "$build_log" 2>&1; then
    echo 'Build passed — JDK and native test images are ready'
else
    rc=$?
    tail -80 "$build_log"
    exit "$rc"
fi