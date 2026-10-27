v90: implementation fixes with the original code-cache checks restored
======================================================================
Native v89 completed all 124 selected cases: 118 passed, four failed, two
errors. The environment preflight passed and the harness completed normally.
This release targets the four functional failures. The two timeouts remain
unresolved and get a separate diagnostic timing run, without editing tests.

1. Code-cache page geometry (VM fix, not a test workaround)
---------------------------------------------------------
Solaris selected multi-megabyte pages for code cache segments. Rounding the
explicit 75M,50M,75M sizes made a 204M sum exceed the explicit 200M cache.
Likewise three 10M segments became a 36M cache instead of exactly 30M.

CodeCache::initialize_heaps now selects the largest supported code-page size
compatible with explicitly requested cache and enabled segment boundaries.
Aligned configurations retain the preferred large pages. Incompatible input
boundaries select a smaller supported page size rather than silently
inflating explicit byte sizes. Disabled profiled-heap folding is accounted
for first. Existing size, minimum-space and platform-limit validations remain.
No global large-page option or normal compiler thread default is disabled.

The ZIP restores CheckSegmentedCodeCache.java and CodeCacheCLITestCase.java
byte-for-byte from the pre-v88 originals, removing both CICompilerCount=2
and -XX:-UseLargePages additions. These files are included even though their
final bytes equal the baseline, so extracting the ZIP replaces the edited
copies. The runtime patch is validated against their original assertions.

This release adds no further edits to existing test cases. The cumulative
ZIP retains earlier port work, including the separately identified v88
Test8004741 JVMTI compatibility update; it does not claim every historical
test file in the cumulative port is identical to upstream.

2. CDS map logging / UTF-16 character printing
--------------------------------------------
Both CDSMapTest and DeterministicDump crashed in the same place:
fieldDescriptor::print_on_for, fieldDescriptor.cpp:137, while logging a static
Java char. The captured character was 0xfffd. isprint() accepts an unsigned
char value or EOF, not arbitrary 16-bit UTF-16. Solaris ctype's table lookup
went beyond its valid range and faulted. The new guard limits classification
to values <=255 and preserves the full numeric character value in the log.
This repairs the field-printing implementation; neither CDS test is edited.

3. SPARC CPU capability reporting
--------------------------------
SPARC filled _features_string but left Abstract_VM_Version::_cpu_info_string
empty. WhiteBox.getCPUFeatures() reads cpu_info_string(), so jtreg believed
the T8 had no AES and selected the unsupported-AES test. The child VM actually
supports AES and therefore correctly did not emit an "AES unavailable"
warning. The later WhiteBox registration error was in that wrongly selected
test's child path; it is not evidence that the CPU lacks AES.

Publish the detected SPARC features through both CPU-info interfaces.
On AES hardware the unchanged unsupported-config test should become
platform-inapplicable. That is not a pass and must be reported as such.
The focused selection also includes the unchanged supported-AES test to
check the applicable path. Hardware without AES must continue to select
the unsupported test. No CPU features or AES intrinsics are disabled.

4. Two timed-out cases are not claimed fixed
-------------------------------------------
TestAlignVectorFuzzer#CompileOnly consumed ~120 seconds CPU in its main
thread, in Unsafe.putInt from testUU_unsafe_BasIH. Its source executes a
10,000-call verification block before checking the soft time allowance;
the sampled loop range was ~6090 and hand unrolling reached 16. Native
fallback operations under compile-only can make this block expensive.
ConvF2HFIdealizationTests's parent was waiting for its child test VM; the
parent dump alone does not establish a hang or locate a compiler defect.
Do not infer either test passed, and do not change their checks/workload.

--timing isolates just these two tests with timeoutFactor=4, still within
the two-hour batch cap. This is diagnostic extra time, not a VM performance
fix or a test-source change. A pass would establish completion under those
settings; it would not demonstrate the original two-minute target was met.
The normal --failed/all-tier1 runs keep timeoutFactor=1 and 24 test jobs.

Host validation (not native Solaris execution)
---------------------------------------------
- Compiled the actual code-cache sizing/validation control flow and new page
  selector with an OS/compiler fixture under UBSan: 270 geometry, fallback,
  disabled-heap, preserved-large-page and invalid-input checks passed.
- Compiled the actual changed T_CHAR printing block with a bounded ctype-table
  fixture: all 65536 UTF-16 values preserved numeric output and stayed in range.
- The unchanged CPUInfo Java parser recognized AES when the published hardware
  string contained it and rejected it when absent. Checked the native API
  wiring to cpu_info_string(). This does not execute SPARC feature discovery.
- Original code-cache sources verified byte-for-byte; no weakened assertions.
- Runner selection/syntax, cumulative source coverage, ZIP CRC and SHA256 checked.
Native rebuild and focused test results remain required.

Run after extracting at ~/git/jdk25
----------------------------------
  cd ~/git/jdk25
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-hotspot-tier1-v90.sh --remaining
    bash tests/run-hotspot-tier1-v90.sh --timing
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

--remaining selects seven cases: the four functional failures, two restored
code-cache checks and the supported-AES counterpart. --timing selects only
the two timed-out compiler cases. The preflight remains separate from counts.
To rerun all 124 original unsuccessful cases instead, use --failed.
Build JOBS is not overridden.

For any unsuccessful batch:
  python3 tests/collect-hotspot-tier1-evidence.py <printed-results-directory>
Send the text evidence ZIP, not cores.
