v72: refreeze after a partial thaw
=================================
The v71 native trace identifies the rejected non-Java frame as
~Stub::cont return barrier. All four C1/C2 cases, including interpreted-yield0
controls, produced this rejection. This is a synthetic continuation boundary,
not proof that a real JNI call pinned the virtual thread.

On SPARC the physical entry window may be relocated below the canonical entry
SP during a partial thaw. If a mounted frame yields again before the remaining
callers thaw, the slow freeze walker must stop at the saved return-barrier PC.
The numeric frame-bottom comparison alone can miss this boundary. Constructing
a sender then treats the return-barrier stub as a non-Java frame and returns
freeze_pinned_native, which can monopolize a single scheduler carrier.

The new SPARC-only check finalizes the freeze at that saved barrier before
constructing a sender. The existing finalization handles the frozen chunk tail.
Ordinary Java callers, genuine native frames, nested continuation entries and
the existing geometric boundary retain their paths. This does not disable C1,
C2, OSR, compiled yield0, partial thaw, or continuation fast paths.

Validation completed on the Linux host:
- Actual recursive-freeze function body: 2210 interpreted/compiled layouts,
  SPARC and generic builds, plus real Java/native and own/nested entry controls.
- Existing relocated-entry, fresh-chunk argument and C2 array-growth host checks.
- Shell syntax and cumulative archive CRC/SHA-256 checks.
These checks use mocks and do not validate generated SPARC assembly or live GC.
Native Solaris verification is required before calling the defect fixed.

After extracting over the source tree:
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-single-carrier-sleep-repro.sh &&
      bash tests/run-v59-regressions.sh &&
      JDK25_TEST_JOBS=16 bash tests/rerun-suspend-resume-v72.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi

The single-carrier runner uses its normal eight modes (plain/JVMTI and
interpreter/C1/mixed/C2). The two upstream suspension tests retain their original
scheduler and test options. Each batch is bounded; unfinished cases are not
passes. The suspension batch defaults to 16 jobs with a 15-minute outer limit.

Unchanged limitations: monitor-driven unmounting still uses the v68 blocking
fallback when no preempt stub exists; that can pin a carrier. The v69 C2 array
growth change still needs native stress validation. This package is cumulative.
