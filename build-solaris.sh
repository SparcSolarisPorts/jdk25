#!/bin/bash
# Build script for Solaris.
# Boot JDK can be overridden: BOOT_JDK=/usr/jdk/jdk-24 ./build-solaris.sh (default: JDK 21)

set -e

BOOT_JDK="${BOOT_JDK:-/usr/jdk/jdk-21}"

cd ~/git/jdk25

bash configure \
    --with-boot-jdk="$BOOT_JDK" \
    --with-jvm-variants=server \
    --enable-dtrace \
--with-native-debug-symbols=internal \
    --disable-warnings-as-errors \
  --disable-java-warnings-as-errors \
    --with-jtreg="$HOME/tools/jtreg-8.2.1/jtreg" \
    DATE=/usr/gnu/bin/date \
    STRIP=/usr/gnu/bin/gstrip \
    OBJCOPY=/usr/gnu/bin/objcopy \
    CXXFILT=/usr/gnu/bin/c++filt

gmake images
