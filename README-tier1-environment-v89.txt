v89: forward the test environment, verify it, and control code-cache page size
===========================================================================
Native evidence from hotspot-tier1-v88-20261027-181802-e_fo5k9j:
  40 formerly unsuccessful cases passed, including TestIntrinsicsRegStress,
  Test8004741 and TestPrintCodeCacheOption.
  Two code-cache sizing cases failed.
  82 selected cases did not report completion before the harness failed.

Why v88 did not contain the memory cascade
----------------------------------------
My v88 runner set JAVA_TOOL_OPTIONS for the harness, but omitted jtreg's
-e:JAVA_TOOL_OPTIONS option. jtreg deliberately filters the test environment.
Thus the JVMs that run tests did NOT receive the promised default limits.
This was a runner bug; lowering the harness heap alone could not fix it.

The collected fatal reports establish the distinction directly:
- JDK21 harness pid1166: MaxRAM=2g and ActiveProcessorCount=8 on command line,
  initial heap 67108864, max heap 536870912.
- JDK25 test agent pid1185: those environment flags absent, initial heap
  2113929216 (2016 MiB), max heap 27883732992 (26592 MiB).
- Numerous other test agents show the same oversized default heaps.

Correction: pass -e:JAVA_TOOL_OPTIONS explicitly to jtreg. This reaches
compile agents, test agents, othervm actions and nested Java children unless
an individual test deliberately removes/overrides that environment.
Existing explicit test heap flags still take precedence over ergonomic
RAM-percentage defaults. No VM heap allocator changes are made in v89.

A standalone jtreg preflight now checks a real test VM and a nested child:
  MaxRAM=2147483648, default max heap <=600 MiB (nominally 512 MiB), CPUs=8.
The main batch will not start if either process fails this check. The
preflight is a separate suite outside HotSpot tier groups; it does not
remove, replace or count as one of the 124 cases. Its logs are collected
if it fails. User-supplied conflicting JAVA_TOOL_OPTIONS can intentionally
cause this guard to stop; do not bypass it before reviewing the values.

Code-cache sizing failures
--------------------------
The compiler-count control in v88 got CheckSegmentedCodeCache past its first
failure, but Solaris large-page alignment exposed the next exact-size
assertion: three explicitly requested 10 MiB segments became three 12 MiB
segments, so the reserved total was 36 MiB instead of the expected 30 MiB.
The CLI test similarly rounded its 75 MiB / 125 MiB segments upward and
exceeded the explicitly requested 200 MiB total (204 MiB after alignment).

These tests check fixed byte-size relationships, not large-page placement.
Add -XX:-UseLargePages to their spawned sizing-test VMs, alongside the existing
CICompilerCount=2. No expected values, negative cases or failure assertions
are removed. Normal installed JVM large-page defaults and dedicated
large-page tests remain unchanged. There are no new HotSpot runtime source
changes relative to v88; only two test Java sources change.

Runner corrections
------------------
- Explicit jtreg environment forwarding and a tested preflight.
- Parse "Tests found: 2,441" as 2441, rather than 2, in both count locations.
- Keep 24 jobs, max retained idle pool 24, timeout factor 1, two-hour total cap
  including the preflight and enumeration, live statuses and ten-second
  progress heartbeat. No build JOBS override.
- Solaris swap snapshots run through a shell, which can launch either a
  native command or a script; failures are recorded rather than stopping
  the controller.
- Both the old v88 entry point and the new v89 entry point use the corrected
  implementation. New result directories are named hotspot-tier1-v89-*.

Validation performed on the Linux host
-------------------------------------
- Used real jtreg 8+2 and a SHA256-verified Linux JDK25.0.5+8.
- Negative check without -e:JAVA_TOOL_OPTIONS failed the actual jtreg preflight.
- Positive check with forwarding passed the same test plus its nested JVM.
- Ran the complete Python controller against a small real jtreg suite:
  preflight, enumeration, main action, progress counts and successful exit.
- Verified ungrouped 124 and comma-grouped 2,441 / 12,345 count formats.
- Ten valid exact-size code-cache child command combinations passed on the
  host, covering tiered, non-tiered and C1-only modes. The 10+10+10 MiB
  explicit-segment case reported exactly 31457280 bytes.
- Shell/Python syntax and cumulative ZIP CRC/source SHA256 checked.
These checks do not constitute a Solaris/SPARC run. The two code-cache
cases and the interrupted cases still require native verification.

After extracting at ~/git/jdk25, rerun the original 124 unsuccessful cases:
  cd ~/git/jdk25
  bash tests/run-hotspot-tier1-v89.sh --failed

No rebuild is required if your v88 images/test-image build already succeeded:
the runtime sources are unchanged, and jtreg compiles the changed Java tests.
To run all tier1 later, omit --failed.

If a preflight or batch fails, collect diagnostics from its printed directory:
  python3 tests/collect-hotspot-tier1-evidence.py <results-directory>
Send tier1-text-evidence.zip, not cores or compiler replay dumps.
