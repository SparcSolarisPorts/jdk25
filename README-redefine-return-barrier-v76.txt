v76: class-redefinition return-barrier diagnostics
=================================================
Native results received:
- Normal C2-enabled build, nine C2 startup probes and both SuspendResume tests
  passed after v75. This confirms the spill-mask probe fix on those runs.
- The new 26-case archive has 24 final passes, one final failure and one case
  still unfinished in the captured archive (UnexpectedDeoptimizationAllTest).
  It has no final batch summary. Do not count the unfinished test as a pass.
- RedefineRunningMethods failed in its original -Xint run: SIGSEGV at
  Continuation::prepare_thaw+0x50, address 0x18, during return-barrier thaw.
  This is separate from C2 startup. The same test passed in an earlier run.

v76 does not claim to fix that new intermittent crash. It retains all fixes
and adds debug-only logging of frozen, prepare-top/prepare-barrier,
prepare-parent and thawed transitions: thread, continuation entry, continuation,
tail, done flag, empty flag and parent chunk. These logs can distinguish a
missing initial tail from an empty retained tail with no remaining parent.
Two product guarantees report these missing-chunk states before dereference;
they do not convert them into success or bypass a return barrier.

The focused runner uses the unchanged upstream RedefineRunningMethods test,
including its agent and interpreter run. It does not add compiler exclusions,
disable redefinition/GC, or weaken assertions. It requests 16 test jobs, although
only this one upstream case is selected. The whole run is capped at 15 minutes.
It disables core dumps only in its own subprocess tree and packages selected
text logs/JTRs, with a 4000-line head/tail cap per selected work file. Full logs
remain on the Solaris host. Code-cache stress is not rerun by this runner.

After extracting over the source tree:
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    JDK25_TEST_JOBS=16 bash tests/capture-redefine-continuation-v76.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
Send the resulting evidence.zip. It contains only selected text, not class
files, heap dumps, cores or the whole jtreg work directory.

Validation on host: actual transition helper compiled against mocks for
absent/present continuation and chunks, no dereference when tracing is off;
null checks ordered before dereference; runner shell syntax; cumulative archive
CRC/SHA and source retention. Full SPARC compilation/native verification pending.
The C2 v75 fix is retained. The v68 monitor fallback limitation is unchanged.
