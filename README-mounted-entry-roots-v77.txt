v77: give mounted continuation-entry roots a single owner
========================================================
The new v76 capture timed out in the original -Xint redefinition test. It did
not hit either missing-chunk guard. It completed many yield/resume cycles, then
stopped responding immediately after G1 full-GC compaction around 3.017 seconds.
No further transition logs appeared before jtreg timed out at 720 seconds;
jstack could not attach. The trace alone does not identify the blocked function.

Source inspection identifies a concrete duplicate-root defect in the SPARC
entry stub. sparc_continuation_enter_setup marks ContinuationEntry::_cont and
::_chunk as oop-map roots. JavaThread::oops_do_no_frames already walks the
mounted entry chain and applies the GC closure to exactly those same slots.
The x86, AArch64 and RISC-V entry setup routines use sized empty OopMaps here.

The fix removes just the two SPARC set_oop entries. It keeps the sized OopMap,
its registration at call sites, the continuation entry, and the generic thread
root traversal. Root fields are still marked/updated through JavaThread.
Other frame roots and saved-register handling are unchanged. This prevents the
same physical slot being adjusted twice during a full compacting GC: after the
first adjustment a second visit can interpret a new address as an old one and
forward it again. That is consistent with the corrupted continuation/chunk
state observed after compaction and the previous prepare_thaw crash. Native
confirmation is required; it is not a claim that every redefinition issue is fixed.

New native regression: ContinuationFullGCEntrySmoke performs explicit G1 full
GC while two nested continuation entries are mounted, while only the outer is
mounted, and while both are suspended. It checks live object graphs, aliases,
identity and 32 yield/resume checkpoints in interpreter, C1, mixed and C2 modes.
Each mode has a 120-second cap. This complements older tests whose explicit
GC was primarily between continuation runs, with no mounted entry to rescan.

The original focused redefinition runner remains unchanged in test selection
and JVM compilation mode. It now attempts bounded pstack/jcmd capture after
30 seconds if the matching test child is still alive. Text-only output includes
those captures; cores remain disabled in this runner's process tree.

After extracting:
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-full-gc-entry-repro.sh &&
      bash tests/run-v59-regressions.sh &&
      JDK25_TEST_JOBS=16 bash tests/capture-redefine-continuation-v76.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
Send the full-GC and redefinition text evidence ZIPs if any case fails.

Host validation: compiled actual SPARC setup and the actual JavaThread entry
root loop against a compacting-GC model. Across eight nesting depths each root
slot is adjusted once; the v76 map reproduces double adjustment. New Java smoke
syntax compiled against API stubs (not executed on host). Shell syntax, archive
CRC/SHA and cumulative retention passed. Native SPARC compilation/execution pending.

Previously confirmed: v75 normal build, nine C2 startup probes, both suspension
tests; v72 eight single-carrier modes with zero pin events and all 16 continuation
regressions. The prior full 26-case archive had 24 passes, a redefinition crash
and an unfinished code-cache stress case; it was not a completed all-pass batch.
The v68 monitor-driven unmounting fallback limitation remains unchanged.
