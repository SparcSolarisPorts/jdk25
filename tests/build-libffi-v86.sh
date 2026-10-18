#!/usr/bin/env bash
# Build a pinned 64-bit libffi for Solaris/SPARC without root access.
set -euo pipefail
[[ $(uname -s) == SunOS && $(uname -p) == sparc ]] || { echo 'Run on Solaris/SPARC.' >&2; exit 1; }
command -v gmake >/dev/null 2>&1 || { echo "GNU make (gmake) is required." >&2; exit 1; }
prefix=${LIBFFI_HOME:-"$HOME/tools/libffi-3.4.8-sparcv9"}
if [[ -f "$prefix/include/ffi.h" && -f "$prefix/lib/libffi.so.8" ]]; then
  echo "Existing libffi: $prefix"; exit 0
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/jdk25-libffi-XXXXXX")
log="$work/build.log"
archive="$work/libffi-3.4.8.tar.gz"
echo "Building libffi 3.4.8; log: $log"
curl --fail --location --retry 2 --output "$archive" \
  https://github.com/libffi/libffi/releases/download/v3.4.8/libffi-3.4.8.tar.gz > "$log" 2>&1
expected=bc9842a18898bfacb0ed1252c4febcc7e78fa139fd27fdc7a3e30d9d9356119b
actual=$(digest -a sha256 "$archive")
[[ "$actual" == "$expected" ]] || { echo 'libffi archive checksum mismatch' >&2; exit 1; }
if (
  # Bash suppresses errexit inside an if-tested subshell. Check each command
  # explicitly so configure/build failure cannot fall through to installation.
  cd "$work" || exit "$?"
  gzip -dc "$archive" | tar -xf - || exit "$?"
  cd libffi-3.4.8 || exit "$?"
  MAKE=gmake CC="${JDK25_NATIVE_CC:-gcc}" CFLAGS='-m64 -O2' LDFLAGS=-m64 \
    bash configure --prefix="$prefix" --libdir="$prefix/lib" \
      --disable-static --disable-dependency-tracking || exit "$?"
  gmake || exit "$?"
  gmake install || exit "$?"
  cp LICENSE "$prefix/LICENSE.libffi" || exit "$?"
) >> "$log" 2>&1; then
  echo "Installed libffi: $prefix"
  file "$prefix/lib/libffi.so.8"
else
  rc=$?; tail -80 "$log"; exit "$rc"
fi
