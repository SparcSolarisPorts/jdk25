v86: Solaris/SPARC Panama native linker through libffi
====================================================
Implementation
This enables the existing JDK 25 libffi-backed implementation of the public
java.lang.foreign.Linker API on Solaris/SPARC64. Applications call the normal
Linker.nativeLinker(), downcallHandle(), upcallStub(), defaultLookup() and
canonicalLayouts() APIs. No application JNI wrapper or special CABI property
is needed. The SPARC V9 ABI marshalling and executable closures are supplied
by libffi's existing SPARC64 backend, including register windows and stack bias.

This is the libffi implementation, not a new optimized HotSpot assembly linker.
ForeignGlobals::is_foreign_linker_supported() intentionally remains false:
that flag describes optimized HotSpot stubs. Returning true would incorrectly
bypass Java's FallbackLinker selection and reach unimplemented SPARC stubs.
The regression explicitly verifies public nativeLinker() selects FallbackLinker
without overriding jdk.internal.foreign.CABI on Solaris.

Changes
- Default fallback-linker=true for Solaris/sparcv9. Preserve explicit configure
  overrides, Zero defaults, and other platforms' existing defaults.
- Probe libffi executable-closure symbols as well as ffi_call at configure time.
- Ensure Solaris libsyslookup records libc/libdl/libm dependencies, so the public
  default lookup can find both strlen and cos.
- Normalize small integral results at the C bridge boundary. libffi returns
  integers smaller than ffi_arg in a full-word buffer; Java allocates only the
  declared layout size. Directly using Java's byte/short/int buffer overruns it
  and reads the wrong end of the word on big-endian SPARC. Downcalls now use a
  temporary ffi_arg and copy exactly the declared width. Upcalls perform the
  reverse conversion, including signed extension. Float and struct returns
  retain their distinct libffi representations.
- Decode heap offsets as the jlong Java actually stores, not int (which reads
  the wrong half on big endian). Release critical arrays with copy-back AND
  release, rather than JNI_COMMIT, which can retain copied buffers.
- Preserve existing Java-thread attachment during upcalls. Attach/detach only
  foreign threads that this bridge attaches. Bound local references with a JNI
  local frame for repeated callbacks; handle bridge exceptions explicitly.
- Supply a pinned libffi 3.4.8 source-build script (SHA-256 checked), a quoted
  configure script, libffi license, and a bounded native FFM regression matrix.
  Bundling libffi.so.8 uses the existing JDK copy mechanism and origin runpath.

Coverage and limits
The existing libffi backend supports primitive and pointer arguments/results,
by-value structs, variable argument functions, callbacks and captured errno.
Its upstream restriction on by-value unions remains: those layouts are rejected
with IllegalArgumentException. This package does not claim complete optimized
HotSpot Panama support or remove that restriction. Downcalls use JNI/libffi
transitions and may cost more than optimized platform stubs.

Native fixtures test signed byte/short/int/long and unsigned char16 returns,
float bit patterns, double, pointer and void returns, integer and FP register/
stack overflow, mixed arguments, small mixed-field structs, large hidden-buffer
struct returns, variadic int/double calls, captured errno, nonzero heap offsets
and untouched guards, reentrant callbacks, foreign pthread callbacks, narrow
callback returns, struct callbacks, and libc/libm default lookups.

Host validation actually completed
Built the changed complete fallbackLinker.c as a shared library with GCC C11,
-Wall -Wextra -Werror (unused JNI parameters exempted), and system libffi.so.8.
Used a downloaded/checksummed Linux/x86-64 JDK 25 and forced its CABI to FALLBACK
only for host testing. All 76 checks passed separately under interpreter, C1,
mixed and C2. The same 76 checks passed with -Xcheck:jni and no JNI warnings.
A control run using its optimized Linux linker passed the corresponding 75
checks. These are real FFM/ffi_call/closure tests, not mocked Java execution.
Additional compiled actual-C helper tests passed 84 signed/unsigned conversions
with surrounding-buffer guards under UBSan; a separate big-endian byte-position
model covers 1/2/4-byte results. Configure-default selection, configure argument quoting/failure propagation,
and shell syntax were checked. The packaged four-mode runner was also run
end to end against the actual host fallback backend and passed all modes. Solaris/SPARC build and ABI execution are still REQUIRED.

First native run (after extracting the cumulative ZIP at repository root)
  cd ~/git/jdk25
  bash tests/build-libffi-v86.sh &&
    bash tests/configure-panama-v86.sh &&
    if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
      bash tests/run-panama-native-repro.sh
    else
      ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
      tail -40 /tmp/jdk25-build.log
    fi

The dependency installs under ~/tools/libffi-3.4.8-sparcv9 without root access.
The configure script preserves the working JDK21 boot, jtreg, Google Test,
DTrace, symbols, version and vendor settings. No build JOBS override is added.
Overrides: LIBFFI_HOME, BOOT_JDK, JTREG_HOME, GTEST_HOME, LOG_DIR. For the test
runner: JDK25_IMAGE and JDK25_NATIVE_CC. Tests use the newly built image, not
the currently installed /usr/jdk/instances/jdk-25 image. Each of four modes
has a 180-second cap, a PASS marker and exit-code check; cores are disabled.
Send the printed text-only evidence.zip for any native failure. After a pass,
rerun the existing gtest, focused jtreg and continuation matrices, then the
broader test/jdk/java/foreign suite. No upstream test exclusions were added.

References
- JDK source: src/java.base/share/classes/jdk/internal/foreign/CABI.java
- JDK source: src/java.base/share/classes/jdk/internal/foreign/abi/fallback/
- libffi v3.4.8: src/sparc/ffi64.c and src/sparc/v9.S
  https://github.com/libffi/libffi/tree/v3.4.8/src/sparc
- SPARC V9 ABI overview:
  https://docs.oracle.com/cd/E53394_01/html/E61689/advanced-2.html

Prior native evidence preserved
v85 compiled successfully on Solaris. All 5 Unsafe alignment modes, all 7
Marlin checksum modes and all continuation regression scripts passed in the
2026-10-18 run. The previous v83 native gtest result was 24 applicable wrappers
passed, 6 inapplicable. Those passes precede the new Panama integration.
