v88: tier1 evidence, SPARC string registers, C1 exception checking, test setup
===========================================================================
The 20261026-223718 run selected 2441 cases and reported 1417 passes, 58
failures and 66 errors before the JDK21 jtreg harness aborted. It did not
reach the two-hour cap. These results are not 124 independently established
VM regressions, and none of the unsuccessful cases is claimed passed yet.

Evidence reviewed
-----------------
All 124 non-passed JTRs and all 80 collected fatal reports were inspected.
70 reports are native allocation failures. The other 10 are SIGBUS with
BUS_OBJERR and si_errno=12 (ENOMEM), including the JDK21 harness itself.
Several VM instances requested 2016 MiB initial / 26592 MiB maximum heaps.
There are also failed G1 thread creations and failed libnio/ld.so mappings.
The default jtreg idle agent pool can retain twice the test concurrency,
while additional child VMs run. Aggregate anonymous-memory commitments can
exhaust Solaris backing resources even while physical free RAM looks high.
The original evidence collector did not find swap in PATH; this is corrected.

The included tier1-triage-v88.csv accounts for every unsuccessful case:
  65 direct resource exhaustion records
  10 more correlated to resource crashes by process ID
   2 process-launch errors during the resource failure cascade
  41 unresolved timeout/communication records, requiring a fresh run
   6 distinct correctness/test-setup cases covered below
Resource correlation is not a substitute for rerun results.

Corrections
-----------
1. C2 fast String compression/inflation used $$FloatRegister for regD operands.
   ADLC double encodings interleave the lower/upper banks: encoding 1 means
   F32, not physical F1. The incorrect conversion could overwrite live float
   registers. Decode with reg_to_DoubleFloatRegister_object, as other SPARC
   double rules do. The inflater's fpmerge source pairs are constrained to
   regD_low because fpmerge reads single registers (F0..F31). The destination
   pairs can still use upper double registers. VIS fast paths remain enabled.
   This addresses TestIntrinsicsRegStress's third check failing with -Infinity.

2. C1 do_Throw could choose direct unwind even with AbortVMOnException enabled.
   That bypasses Runtime1's exception lookup and debug_check_abort. When the
   flag is present, use exception lookup, just as for JVMTI exception events.
   Default exception unwinding remains unchanged. The original diagnostic test
   keeps its fatal-abort assertion and its C1 compilation flags.

3. Test8004741 called Thread.stop(), which is unsupported on JDK25. Replace
   that operation with a small JVMTI agent's StopThread call. Retain the actual
   asynchronous ThreadDeath stress, compilation requirement, six successful
   interruptions and both original test actions. test-image builds the new
   libTest8004741 automatically from the jtreg native source tree. No test is
   excluded to hide this old API problem.

4. Three code-cache tests use fixed, small code heaps, but non-nmethod compiler
   buffers grow with compiler thread count on a 256-thread machine. Set
   CICompilerCount=2 in their spawned sizing-test JVMs, independent of CPU
   count. All original startup, output, segment-size and negative assertions
   remain. This changes tests, not the installed JVM's compiler-thread defaults.

Runner
------
The new runner keeps 24 concurrent tests, timeoutFactor=1 and a two-hour total
cap including enumeration. It uses a fresh work/report directory each time.
It bounds the retained idle agent pool to 24 and sets inherited ergonomic
VM defaults with JAVA_TOOL_OPTIONS:
  MaxRAM=2g, InitialRAMPercentage=1.5625, MaxRAMPercentage=25,
  ActiveProcessorCount=8
This produces roughly 32 MiB initial / 512 MiB max default heaps and prevents
all concurrent VMs sizing themselves from the entire host's memory/256 CPUs.
Explicit test -Xmx/-Xms/processor settings override these defaults. Existing
JAVA_TOOL_OPTIONS are appended so intentional user settings take precedence.
There is no heap fixed with -Xmx in test VMs. The runner JVM itself is 512 MiB.
C1, C2, OSR, continuations and all selected assertions remain enabled.
The "Picked up JAVA_TOOL_OPTIONS" startup diagnostic is expected.

The progress bar refreshes every ten seconds even if no test finishes. Raw
Passed/FAILED/Error lines appear live and are also saved in run.log. The bar
counts reported completions; platform-inapplicable tests are not passes.
Solaris swap snapshots are retained every thirty seconds. Failure/timeout or
Ctrl-C cleanup terminates the whole runner process group, including child VMs.
Build JOBS is not changed. Nothing is installed system-wide by this patch.

Validation completed here (Linux host, not a Solaris VM build)
------------------------------------------------------------
- Compiled the actual SPARC double-register decoder: 992 scratch-write/live-
  float cases under UBSan; checked the AD operands and fpmerge constraints.
- Compiled the actual updated JVMTI agent with strict warnings and ran the
  updated Test8004741 on a checksummed Linux JDK25.0.5+8: all six required
  asynchronous ThreadDeath catches completed, exit=0.
- Ran the unchanged TestIntrinsicsRegStress on that Linux JVM as a test
  control: all four checks passed. This does not execute SPARC machine code.
- Checked fixed-size valid/invalid code-cache child commands with 256 reported
  processors and CICompilerCount=2: expected startup/diagnostic results.
- Verified ergonomic defaults on a real JDK25 JVM and explicit 64m / 1g -Xmx
  overrides. No minimum-heap conflict is introduced.
- Runner tests: live statuses, heartbeat during silence, nonzero exit status,
  whole-process-group timeout; Python/shell syntax checked.
- ZIP CRC, cumulative-source coverage and SHA-256 checks completed.
Native SPARC build, C1 AbortVMOnException, corrected VIS code and full tier1
results remain pending. The 41 unresolved timeouts may still expose bugs or
need individual timing investigation. A green full run must demonstrate that.

Run after extracting at the repository root
------------------------------------------
  cd ~/git/jdk25
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-hotspot-tier1-v88.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

Optional faster focused verification of all 124 originally unsuccessful cases:
  bash tests/run-hotspot-tier1-v88.sh --failed

If anything fails, collect only bounded text evidence from the printed results:
  python3 tests/collect-hotspot-tier1-evidence.py <results-directory>
The collector never reads cores or heap dumps. Send tier1-text-evidence.zip.
