v71: identify the compiled frame that pins a single carrier

Evidence from evidence-3.zip (v70 diagnostic):
  Interpreter: passed, both plain and with the SuspendResume2 agent.
  C1, mixed, C2: failed in all six runs, including the three without an agent.
  All 20 workers initially started. One worker then accumulated about 500
  sleep cycles while the other 19 stayed at one cycle.
  Compiled cases recorded 500-503 jdk.VirtualThreadPinned events with reason
  "Native or VM frame on stack". Interpreter cases recorded zero pin events.

This isolates a compiled continuation-yield/frame-walk problem independent
of the JVMTI suspension functions. JFR shows the subsequent park stack,
not the exact frame rejected earlier by the freeze or pin walk. The evidence
does not yet establish which frame or PC needs correction. This release
does not claim to fix that single-carrier starvation.

Source changes:
- Add SPARC-PIN diagnostics, gated by -Xlog:continuations=debug, immediately
  before the four frame-based native-pin returns. They name the rejection
  reason, method (where available), frame kind, PC, SP, unextended SP and FP.
  No frame is reclassified or allowed to freeze by these diagnostic hooks.
- Remove the duplicated safepoint pin-query architecture block. The first
  block included SPARC; the duplicate immediately following it excluded
  SPARC and called Unimplemented(). Keep the first block, so supported
  architectures normalize the frame pointer exactly once. This is a concrete
  safepoint-path fix, not a proven explanation for the ordinary sleep failure.

The focused runner compares C1 and C2 with the normal compiled yield0 path
and with only Continuation::yield0 excluded from compilation. These latter
cases are explicitly named *-yield0-interpreted diagnostic controls. They
are NOT a production workaround or a change to the original jtreg tests.
The normal C1/C2 cases must eventually pass with no exclusions.

Rebuild after extracting the cumulative ZIP, then run only these four cases:

  cd ~/git/jdk25
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-single-carrier-pin-trace.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

Send the emitted evidence.zip. It includes the new *.frames.log files, the
JFR event text, and all four exit statuses. It contains no core files or
JFR binaries. If the normal cases reproduce the failure, exit=1 for the
runner is expected even if its diagnostic controls pass. Every JVM still
has a 60-second hard limit plus five seconds for forced termination.
The eight-case v70 runner remains available as run-single-carrier-sleep-repro.sh.

Validation here:
- The actual safepoint preprocessor branch was extracted and compiled under
  SPARC, X86, AARCH64 and RISCV64 defines; each normalized FP once.
- Java diagnostic compiles; both shell runners pass bash -n.
- All 802 prior block-array host checks still pass.
- Cumulative ZIP CRC/source SHA-256 and retention checks pass.
This Linux host cannot build/run Solaris/SPARC HotSpot. Native verification,
including v69's intermittent C2-startup change, remains pending.

All v69 fixes and v70 diagnostic files are retained. The v68 monitor blocking
fallback remains: ordinary continuation fast paths stay enabled, while full
monitor-driven unmounting still needs its missing assembly integration.
