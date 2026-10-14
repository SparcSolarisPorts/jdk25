Partial rerun 20261014-012127: 233 selected cases

Recorded completed results: 124 passed, 93 failed, 14 error.
Two selected cases have no completed result in either run.log or a .jtr:
serviceability/jvmti/GetOwnedMonitorInfo/GetOwnedMonitorInfoTest.java
serviceability/jvmti/vthread/SuspendResume1/SuspendResume1.java#default
The archive does not establish which process prevented the harness ending.

Of the 93 failures, 29 are unresolved jcstress artifacts and 24 are missing
gtest native libraries. Those 53 tests remain untested for VM correctness.
The other 40 failures and 14 errors require investigation; they are not all
confirmed VM bugs. Error entries are timeouts in this run.

High-priority evidence:
- Three JVMTI continuation tests crash with bad addresses in frame::frame or
  frame::patch_pc. Their native stack pointers show loss of the high 32 bits.
- DynamicCodeGeneratedTest crashes in frame::frame as well.
- TestBiMorphicMismatchedMemSegment has SIGBUS in C2-generated Java code.
- UnexpectedDeoptimizationAllTest, which passed the smaller 25-case run,
  exits with signal 11 in this broader run. No hs_err for it is in this ZIP.
- ArrayUnsafeOpTest has a native mmap allocation failure requesting about
  2 GB during VM startup. Resource pressure may confound some broad-run
  results; repeat affected cases with low concurrency before classifying.
- Other failures include vector API, JVMTI events/state/monitor handling,
  code-cache options, cryptographic flag expectations, JNI virtual-thread
  missing-unlock warnings, NMT output and large-page argument validation.

Suggested order: frame walking/JVMTI continuation crashes, C2 SIGBUS and
intermittent deoptimization crash, then monitor/suspend timeouts. Provision
gtest and jcstress separately. The original jtreg tests are unchanged.

Lists use jtreg:test/hotspot/jtreg/... entries compatible with the existing
JDK25_TEST_LIST runner. Do not rerun jcstress at 16 concurrent wrapper jobs.
Use low concurrency for memory-heavy or timeout investigations.
