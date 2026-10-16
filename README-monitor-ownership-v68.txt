v68: prevent false-success monitor preemption on SPARC

Evidence from priority-1-2-rerun-20261016-000114:
  10 passed
   5 failed
   9 test timeouts
   2 without final results when the outer batch ended
The two unfinished cases were GetOwnedMonitorInfoTest and SuspendResume1.
The two aborts in this run were deliberate JVMTI FatalError calls after the
virtual thread unexpectedly terminated (JVMTI_ERROR_THREAD_NOT_ALIVE), not
repeats of the earlier C2/libc startup SIGSEGV.

Concrete correctness defect:
  SPARC does not generate StubRoutines::cont_preempt_stub().
  Continuation::try_preempt previously still called freeze_preempt_entry().
  On success, patch_return_pc_with_preempt_stub installed a null target.
  ObjectMonitor treats freeze_ok as suspension and returns before acquiring
  the contended monitor / completing the wait. Without the machine-code
  diversion, Java then executes with an incomplete monitor operation.

Change:
  Check for a missing preempt cleanup stub BEFORE the freeze and JVMTI
  unmount transition. Return freeze_unsupported, allowing ObjectMonitor's
  existing blocking fallback to complete the operation normally. No
  continuation frames are frozen or lock stacks moved on that path.

IMPORTANT LIMIT:
  This is an interim correctness fix, not an implementation of monitor-driven
  unmounting. A virtual thread blocked in a monitor can retain its carrier.
  Ordinary yield/resume, compiled fast freeze/thaw, C1/C2, lightweight locking,
  and compact headers remain enabled. The old interpreter preemption adapter
  is still a placeholder; generating a non-null cleanup stub alone would not
  complete the missing native/interpreter/runtime resume integration.
  Tests specifically requiring unmounted monitor waits may still time out.
  None of the nine existing timeout cases is declared fixed.

The new smoke checks actual monitor ownership after contention, wait/notify,
interruption and yield for platform and virtual threads in interpreter, C1,
mixed and C2 modes. Worker exceptions are propagated; stuck cases fail via a
120-second process timeout. The five failed jtreg cases are rerun unchanged
in the focused runner, with 16 jobs by default and a 15-minute outer limit.

Apply the cumulative ZIP over ~/git/jdk25, then:

  cd ~/git/jdk25
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-virtual-monitor-ownership-repro.sh &&
      bash tests/run-v59-regressions.sh &&
      JDK25_TEST_JOBS=16 bash tests/rerun-monitor-ownership-v68.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

Host validation: Java smoke compiles on the available JDK17 compiler using
reflection only for virtual-thread creation; shell runners pass bash -n.
The source guard is checked to precede the unmount transition and freeze.
This Linux host cannot build or run the Solaris/SPARC JVM. Native test
outcomes are pending; do not interpret packaging checks as runtime passes.
