# JDK 25 Solaris/SPARC continuation candidate (v40)

v40 corrects the v39 smoke-test compilation failure. The test previously
imported jdk.internal.org.objectweb.asm, which is unavailable in the user's
JDK 25 image. ConstantDynamicNullSmoke now writes a minimal Java 11 class
file using only public java.io APIs. The generated methods still use real
CONSTANT_Dynamic entries and ldc_w, with the same null/non-null identity,
bootstrap-cache and GC checks. The runner no longer needs ASM exports or
an external library. This changes the test and runner, not HotSpot sources.
All cumulative v39 source fixes remain included.

Validation: the self-contained test passed in host interpreter, C1, mixed
and C2 modes, each checking 80000 null/non-null pairs and GC. The generated
class is verified and loaded by the host JVM; these checks do not prove
native SPARC execution passes. Shell syntax, cumulative patch dry run,
ZIP CRC and source SHA-256 checks passed.

Replace tests/ConstantDynamicNullSmoke.java and tests/run-condy-null-repro.sh
from this ZIP and rerun:

```bash
cd ~/git/jdk25
bash tests/run-condy-null-repro.sh
```

No further JDK rebuild is needed for this test correction if the v39 image
was already rebuilt. The five-minute watchdog per mode remains enabled.
After the smoke test, use tests/rerun-priority-1-2.sh and the evidence collector
as described below for native jtreg validation of the null-sentinel fix.

## Included v39 changes

v39 responds to priority-1-2-rerun-20261008-015735-evidence.zip. Native v38
results are 10 passes, 13 failures and 2 timeout errors. TestLargeMonitorOffset
now passes after v37's OSR displacement correction. All four continuation
smoke modes pass. The separately pasted native run confirms all four process
reaper modes (400 subprocess completions) pass and Forge exits at its EULA
check without the previous process-reaper StackOverflowError. Full server
startup/gameplay remains untested. UnexpectedDeoptimizationAllTest passes this
run, but CTW java_base_2 crashes again while deoptimizing on a handshake.
Neither intermittent issue is declared fully fixed.

v39 corrects the cached interpreter reference-constant path in
TemplateTable::fast_aldc. Universe::the_null_sentinel_addr() now points at an
OopHandle. Loading its first pointer yields the OopStorage slot address,
not the sentinel object. The old comparison therefore failed to translate a
cached null constant into Java null and could return the sentinel object.
The first runtime-resolved load already returns null, so the defect appears
when later loads reuse the interpreter cache. The jtreg validateResult error
message itself dereferences the expected null and masks the mismatch with a
NullPointerException. The test and its expectations remain unchanged.

The emitter now resolves the handle through resolve_oop_handle with the
native-root load barrier before comparing it with the resolved constant.
This matches the handle indirection in the current x86/aarch64 implementations.
The cached constant fast path is retained, and ordinary non-null references
still preserve identity. No compiler or VM feature was disabled.

Validation: nine extracted-emitter ASan/UBSan cases passed for runtime null,
cached sentinel and ordinary object references across three relocated sentinel
addresses. ConstantDynamicNullSmoke passed in all four host Java 17 modes,
each checking 80000 null/non-null constant pairs, bootstrap-cache reuse and GC.
run-condy-null-repro.sh compiles with the JDK image and runs interpreter, C1,
mixed and C2, with a 300-second watchdog per mode and separate result logs.
Host checks do not validate generated SPARC instructions or establish that
the entire native TestConstantDynamic test now passes. Native reruns are needed.
Shell syntax, cumulative patch dry run, ZIP CRC and source SHA-256 checks passed.

priority-1-2-status-v39.csv records all 25 actual native v38 outcomes. All cases
remain selected in the direct runner with timeout factor 4. The remaining
unsafe alignment, C2 range-check, compiled reserved-stack, small-stack startup,
class-space placement, large-page selection, pretouch-accounting and timeout
failures remain unresolved, along with the intermittent CTW crash.

After installing the archive:

```bash
cd ~/git/jdk25
if gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1; then
  bash tests/run-condy-null-repro.sh
  bash tests/rerun-priority-1-2.sh
  latest_results=$(ls -dt "$PWD"/priority-1-2-rerun-*/ | head -1)
  bash tests/collect-priority-evidence.sh "$latest_results"
else
  tail -80 /tmp/jdk25-build.log
fi
```

## Included v38 changes

v38 includes all v37 source changes plus a Forge launcher correction for the
reported process-reaper StackOverflowError during shutdown. The launcher now
exports -Djdk.lang.processReaperUseDefaultStackSize=true through JDK_JAVA_OPTIONS,
so the Java process launched by Forge's run.sh uses the normal VM thread stack
rather than the reaper's small dedicated stack. Existing JDK_JAVA_OPTIONS,
user_jvm_args.txt, Forge argument files and server arguments are preserved.
The process reaper continues running; C1, C2, continuations and compact object
headers retain their existing configuration. The launcher continues to check
compact-header support before invoking Forge.

This is a supported process-reaper stack configuration, targeted at the
observed small-stack failure. The native trace has no full Java stack, so
confirmation on Solaris is required before calling the Forge shutdown fixed.
The Java property is documented in OpenJDK's ProcessHandleImpl implementation:
https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/lang/ProcessHandleImpl.java

New ProcessReaperSmoke.java starts 100 bounded subprocesses per mode and checks
waitFor, ProcessHandle.onExit, nonzero exit status, captured output and uncaught
thread exceptions. run-process-reaper-repro.sh runs interpreter, C1, mixed and
C2 with compact headers, records OS thread-stack diagnostics, and has both
Java completion deadlines and a 300-second whole-process watchdog per mode.
The main test passed 400 subprocess completions across the four host Java 17
modes. Host execution does not validate SPARC frames or JDK 25 compact headers.
Launcher checks passed with existing Java options, server/JDK paths containing
spaces, forwarded server arguments and FORGE_TRACE=1. Shell syntax checks,
cumulative patch dry run, ZIP CRC and source SHA-256 checks passed.

After installing the archive, run:

```bash
cd ~/git/jdk25
if gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1; then
  bash tests/run-process-reaper-repro.sh &&
  bash tests/run-forge-with-jdk25.sh \
    "$HOME/Downloads/forge26.3servertest/forge26.3servertest"
else
  tail -80 /tmp/jdk25-build.log
fi
```

The launcher change itself works with the existing JDK image; rebuilding
applies the cumulative HotSpot changes, including v37's C1 displacement fixes.
Forge's EULA check is independent: review and accept eula.txt yourself if you
agree. This archive leaves the server's EULA file untouched.

## Included v37 changes and native results

v37 responds to priority-1-2-rerun-20261008-013011-evidence.zip, including
its actual jtreg Java sources. Native v36 results: 9 passes, 14 failures and
2 timeout errors. ReservedStackTest now passes. CTW java_base_2 passes in
this run; it has varied between runs, so remains a regression selection.
The separate compiled reserved-stack test still fails.

v37 fixes two C1 displacement bugs in c1_LIRAssembler_sparc.cpp:
* OSR monitor copying now materializes the monitor address when either word
  lies outside the signed 13-bit immediate range. It preserves I0, which
  subsequent local-variable copying needs. The uploaded TestLargeMonitorOffset
  declares 1000 long locals, placing its monitor around 16 KB into the OSR
  buffer. Previously release builds could encode a truncated displacement,
  copying unrelated data into the compiled monitor's oop slot. Its observed
  G1 oop-copy crash is consistent with that defect, but a native rerun must
  establish whether this is its complete cause.
* Both C1 immediate load/store range checks now parenthesize the conditional
  addend. The previous expression tested 0 or wordSize regardless of the
  actual displacement and could incorrectly choose an immediate instruction
  for an out-of-range address.

The extracted OSR emitter passed 42 host ASan/UBSan checks covering both
monitor words, multiple monitors, immediate-range boundaries, 1000-long-local
geometry, maximum local counts and preservation of the OSR buffer pointer.
These checks simulate address emission; they do not execute SPARC instructions.
No HotSpot SPARC build or native jtreg run is available here. The cumulative
patch dry run, ZIP CRC and source SHA-256 checks passed.

priority-1-2-status-v37.csv records all 25 native v36 outcomes. All selections
remain in the runner. No test expectations or VM features were disabled.
The other 13 failures and 2 errors remain unresolved: unsafe access alignment,
constant-dynamic C1 results, C2 long range checks, compiled reserved-stack
handling, small-stack initialization, virtual-thread/deoptimization stress,
class-space placement, large-page selection, stack-pretouch accounting and
JNI/stack-bang timeouts. These require separate fixes and native validation.

Rebuild and rerun:

```bash
cd ~/git/jdk25
if gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1; then
  bash tests/run-continuation-repro.sh
  bash tests/rerun-priority-1-2.sh
  latest_results=$(ls -dt "$PWD"/priority-1-2-rerun-*/ | head -1)
  bash tests/collect-priority-evidence.sh "$latest_results"
else
  tail -80 /tmp/jdk25-build.log
fi
```

The direct runner retains timeout factor 4, logs output to its results folder,
and preserves failing/error artifacts. It returns jtreg's exit code.

## Earlier v36 changes

v36 responds to jdk25-priority-v35-evidence.zip. Native v35 confirms both
new fixes: TestAllocateHeapAtMultiple and TestNativeStack pass, and all six
small-heap compressed-oop smoke modes pass at the expected 3 GB/unscaled
and 5 GB/scaled addresses. The selected jtreg run still has seven passes,
16 failures and two timeout errors because CTW java_base_2 and virtual-thread
code-cache stress failed again after passing in the previous run.

The CTW crash is now in JavaThread::deoptimize_marked_methods on VM Thread,
not in native diagnostic printing. The register-window constructor receives
a null SP and faults at address 0x70. Source review found that frame::sender
still used its pre-continuation implementation: it had no chunk dispatch or
return-barrier handling. That omission can walk a synthetic return barrier
as an ordinary native frame. The crash report does not prove that this is
the CTW failure's complete cause; native reruns are required.

v36 adds the continuation dispatch used by the other ports while retaining
SPARC register-window map updates:
* Frames already in a chunk use stackChunkOopDesc::sender.
* At a mounted return barrier, continuation-aware walks enter the remaining
  chunk; carrier-only walks recover the real ContinuationEntry frame.
* Carrier entry recovery keeps younger_sp for SPARC's saved O7/PC location
  and shifts the register map to the actual entry window.
* Native stack iteration calls StackWatermarkSet::on_iteration when requested
  and outside a chunk, matching other supported continuation ports.
* safe_for_sender resolves return barriers to the actual continuation entry
  instead of treating them as ordinary compiled frames.
* Returning from a mounted chunk to its carrier uses SPARC's explicit
  SP/unextended-SP/FP/PC constructor in shared continuation.cpp. The generic
  three-void-pointer constructor is debug-only on this port.

A second correction makes the interpreter and compiled reserved-stack return
checks compare unbiased SP (architectural SP + STACK_BIAS) with the shared
runtime's reserved_stack_activation address. Previously the 2047-byte bias
could delay re-enabling the guard and throwing the deferred overflow. This
corrects an address-representation mismatch, without changing guard sizes
or disabling ReservedStackAccess. It does not claim all overflow tests fixed.

Validation: 32 extracted reserved-stack comparison cases passed under
ASan/UBSan at, below and above the activation address, including high stack
addresses. 14 cases from the edited sender_raw/sender functions passed a
host ASan/UBSan model covering native/entry/upcall frames, barrier-to-entry,
barrier-to-chunk, in-chunk traversal, chunk exit and stack iteration hooks.
The tests check that a return barrier never takes the normal window
constructor. These are dispatch checks, not native register-window or GC
validation. Leak detection is disabled for sandbox process inspection limits.
Cumulative patch dry run, ZIP CRC and source SHA-256 validation passed.

The unchanged direct runner retains all 25 selections with timeout factor 4.
priority-1-2-status-v36.csv records the v35 native results. No failures are
claimed fixed until native reruns pass. The C1 GC crash is still the same
invalid G1 oop location; virtual-thread stress still has corrupted L2=0x24
in compiled parkNanos after a continuation return. The stack-walk correction
addresses a definite integration omission, but is not proof of their cause.
Unsafe-access, reserved-stack, constant-dynamic, range-check, memory-layout
and timeout failures remain open. No features or test assertions are disabled.

```sh
cd ~/git/jdk25
if gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1; then
  bash tests/run-continuation-repro.sh
  bash tests/rerun-priority-1-2.sh
else
  tail -80 /tmp/jdk25-build.log
fi
```

After the rerun, collect its evidence using the result directory printed by
jtreg:

```sh
bash tests/collect-priority-evidence.sh /path/to/priority-1-2-rerun-results
```

The collector includes logs/reports and the selected Java test sources plus
native JNI companions and edited sources. It excludes cores,
compiled classes and executables. Attach the printed evidence ZIP.

Prior changes and historical evidence follow.

# JDK 25 Solaris/SPARC continuation candidate (v35)

v35 responds to jdk25-priority-v34-evidence.zip. The native v34 rerun has
seven passes, 16 failures and two timeout errors among 25 selected cases.
All four recursive-locking selections, both CTW selections and code-cache
stress passed. TestNativeStack now exits normally instead of crashing, but
its output lacks native frames, so that jtreg test is still failed.

Two new source corrections:
* Compressed object pointers: all six SPARC assembler encode/decode overloads
  use CompressedOops::shift() instead of LogMinObjAlignmentInBytes. A heap
  below 4 GB can select shift=0. Previously generated code divided the
  reference by eight while shared C++ decoded it without scaling. The
  TestAllocateHeapAtMultiple report shows heap c0000000..c2000000 and the
  malformed pointer 183a0415 in java_lang_Thread::set_thread_status. Null
  handling, scaled heaps, nonzero bases and optimized compiler paths remain.
* Native stack walking: link_or_null reads the caller's saved FP from the
  caller's register-save window, after a readability/alignment check.
  Returning link() repeated the current FP, so os::is_first_C_frame always
  rejected an otherwise valid chain. Native and continuation link() behavior
  is unchanged. The previous empty-frame crash correction is retained.

Validation: 280 cases from the actual edited assembler functions passed a
host emission model under ASan/UBSan: shift 0/3/4, null/non-null, aliased and
separate registers, zero/nonzero bases. Extracted link_or_null and shared
is_first_C_frame code passed valid-chain, root and unreadable-slot checks.
Leak detection was disabled because the host sandbox cannot inspect process
threads; address and undefined-behavior sanitizers remained enabled.
The Java smoke program also passed locally in Java 17 source-launch mode.
These checks do not replace a Solaris/SPARC build and native execution.

New tests/run-compressed-oops-repro.sh exercises 32 MB heaps in interpreter,
C1 and C2 modes at requested heap bases 3 GB and 5 GB, logging the selected
compressed-oop mode, with reference identity, object payloads and full GC.
Heap placement is a request; inspect the logged actual base and mode.

The direct jtreg runner retains all 25 cases, including the seven passes as
regressions. priority-1-2-status-v35.csv records the new results and unresolved
cases. The other unsafe, C1 GC, constant-dynamic, range-check compilation,
reserved-stack, page-size, compression-layout, pretouch and timeout failures
are not claimed fixed by this archive. No jtreg assertions are weakened.

```sh
cd ~/git/jdk25
if gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1; then
  bash tests/run-compressed-oops-repro.sh
  bash tests/rerun-priority-1-2.sh
else
  tail -80 /tmp/jdk25-build.log
fi
```

Prior changes and historical evidence follow.

# JDK 25 Solaris/SPARC continuation candidate (v34)

This is an experimental source candidate for the attached JDK 25 tree. It
re-enables VMContinuations and implements missing entry/yield native wrappers.
It is not yet a runtime-validated SPARC continuation port.

v34 responds to jdk25-priority-1-2-evidence.zip. The native v33 run has
41 passes, 23 failures, two timeouts reported as errors and seven tests not
meeting platform requirements. All continuation smoke modes and the native
arraycopy/header smoke matrix passed before this run.

Two concrete source corrections:
* C2 legacy locking: inflated-monitor enter and unlock's owner-reacquisition
  CAS now load JavaThread::monitor_owner_id, matching JDK25 ObjectMonitor's
  int64 owner representation. The old code installed the JavaThread pointer,
  which the shared notify/ownership checks reject. Four C2 recursive-locking
  cases failed with IllegalMonitorStateException in LockingMode=1; the mode=0
  action passed. Stack-lock CAS and lightweight-lock fast paths are retained.
* Solaris native frame reporting: os::current_frame now returns frame() when
  its first C frame is unwalkable, rather than calling the SP-dereferencing
  window constructor with nullptr. Both CTW compiler-thread crash reports
  show frame::frame +4 reading address 0x70. TestNativeStack reports the same
  failure while printing a JNI warning on a native attached thread. This
  fixes the diagnostic crash; underlying CTW compilation issues may remain.

Validation: 18 cases using extracted owner-CAS emitter code passed an ASan /
UBSan host model with empty, same-owner and other-owner monitors, including
64-bit IDs. The extracted current_frame path returns an initialized empty
frame for an unwalkable native stack and follows its sender when walkable.
The direct rerunner's mock harness preserves #id arguments and propagates
jtreg failure exit status. Native Solaris/SPARC validation is still required.

The archive includes priority-1-2-status-v34.csv with all 25 unsuccessful cases
and their observed causes, plus jdk25-priority-1-2-remaining.txt and a direct
rerunner. It reads JT_HOME/JTREG_JDK from spec.gmk and passes test names as an
argument array, preserving #id selections. It does not depend on the inactive
make test wrapper. It keeps concurrency 16 (JDK25_TEST_JOBS can override),
timeout factor 4, and retained failure/error output, without streaming the log.

```sh
if gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1; then
  bash tests/rerun-priority-1-2.sh
else
  tail -80 /tmp/jdk25-build.log
fi
```

v34 does not claim all 25 cases are fixed. The other failures include unsafe
memory access faults, G1/oop corruption, virtual-thread deoptimization,
reserved-stack handling, constant-dynamic behavior, compression/page-size
expectations and compilation deadlines. The two errors are actual timeouts,
not missing native libraries. Further native evidence is needed after the
confirmed source corrections; no tests are removed from the rerun list.

v33 responds to the native output from 20261007-232916 and the full
continuation-test-results-20261007-231504 archive. All nine string-equality
modes now pass (2,554,500 checks each). Compiled continuation and compiled-GC
still pass. The five interpreted array-header modes pass. C1 and C2 modes
fail overlapping int arraycopy, independently of header configuration.
Interpreter/mixed continuations fail after pass 0, in monitor unlock after GC.

Two source corrections:
* The conjoint int and long arraycopy stubs omitted array_overlap_test.
  They now redirect lower/equal destinations and non-overlapping ranges to
  the existing forward copy entry. Reverse bulk copying remains enabled for
  upward overlap. This fixes the reproducible int copy (source=1, dest=0,
  count=2), which backward copying turns into two copies of the last element.
* Interpreter thaw payload padding was not reflected in metadata relocation.
  Saved pointers into the payload (locals, expression stack, monitors) now
  follow the FP-relative displacement. Pointers into the register save area
  retain SP-relative relocation. The previous code pointed one word too low
  when the source FP/SP displacement was odd. This is a definite mismatch in
  the v31 alignment change; native validation is still required to establish
  whether it resolves the supplied unlock crash. No locking option is disabled.

The native report shows BUS_ADRALN at address 0x71d during monitor unlock;
its invalid mark value is consistent with corrupted state, not a reason to
turn off lightweight locking. v33 leaves the compiled continuation fast path
and the proven string-equality correction in place. Forge now reaches its
EULA check without the old String.equals crash, but its process-reaper thread
reports StackOverflowError on shutdown. Server runtime is not yet validated.

Validation: 180,960 cases using extracted metadata relocation code pass under
ASan/UBSan, including odd/even frame layout, payload/window pointers and stack
bias. The new int/long arraycopy regression passes on host JDK17 with C1 and
C2, and checks all source/destination positions 0 through 11 and lengths 0
through 24, both overlap directions and distinct arrays. These tests do not
execute a rebuilt Solaris/SPARC VM. Native build and repro runs are required.

After extracting in the source root:

```sh
python3 tests/configure-release-version.py
gmake images test-image JOBS=8 > /tmp/jdk25-build.log 2>&1
bash tests/run-arraycopy-repro.sh
bash tests/run-header-matrix.sh
bash tests/run-continuation-repro.sh
```

The uploaded native log still says -internal because the release-version
configuration step is not present in its command transcript. The helper above
changes release metadata while preserving the native build settings.

v32 addresses the Forge crash in C2 String.equals with compact headers enabled.
The SPARC array_equals emitter assumed every byte/char array data address was
8-byte aligned. Compact headers can make that address 4 mod 8. It now peels a
4-byte prefix if both addresses have that alignment and at least four bytes
remain, then retains the existing 8-byte bulk loop and tail comparison.
Short or differently aligned inputs use a bounded byte loop. This applies to
C2 String.equals (Latin1 and UTF16) and byte/char Arrays.equals.
The exact crash instruction still needs hs_err_pid29035.log to confirm that
this defect caused the supplied SIGBUS; the source defect is independently
reproducible in an emitted-instruction host model.

After extraction and rebuild, run:

```sh
python3 tests/configure-release-version.py
gmake images test-image JOBS=8
bash tests/run-compact-string-repro.sh
bash tests/run-forge-with-jdk25.sh "$HOME/Downloads/forge26.3servertest/forge26.3servertest"
```

Validation: the regression checks Latin1/UTF16 String.equals and byte/char
Arrays.equals for lengths 0 through 129 and every mismatch position, with
2,554,500 checks passing on host JDK17. An interpreter of the actual changed
emitter checks all address alignments, prefix/bulk/tail mismatches and delay
slots; it also verifies compact aligned inputs retain doubleword loads.
Neither check executes the rebuilt Solaris/SPARC VM; native validation remains
required. The EULA message is independent and should be handled by reading
eula.txt and accepting only if you agree to its terms.

v31 adds a launcher that selects this JDK image explicitly and checks
-XX:+UseCompactObjectHeaders before starting Forge. This option already exists
in this 64-bit JDK 25 source; an "Unrecognized VM option" error indicates that
the launched executable must be checked. The helper sets JAVA_HOME and PATH.
If run.sh contains an absolute Java path, run with FORGE_TRACE=1 and correct
that path in the server launcher. Compact-header VM tests still need to pass.

The release-version helper reuses CONFIGURE_COMMAND_LINE from spec.gmk,
keeps platform/toolchain/bootstrap settings and configures the source version
with +1 and no -internal prerelease suffix. This is release-style metadata,
not Oracle certification or an official upstream release. It uses the vendor
name "OpenJDK Solaris SPARC". Review with --print-only if desired.

Commands after extracting this archive in the source tree:

```sh
python3 tests/configure-release-version.py
gmake images test-image JOBS=8
bash tests/run-continuation-repro.sh
bash tests/run-header-matrix.sh
bash tests/run-forge-with-jdk25.sh "$HOME/Downloads/forge26.3servertest/forge26.3servertest"
```

Native v30 results: compiled and compiled-GC pass; interpreter and mixed abort
when pass 8 starts, after passes 0 through 7 return. Both anchor and flushed
stack addresses are eight bytes out of alignment for a V9 native window.
v31 inserts padding above the interpreted register-save area when chunk
packing leaves an odd FP/SP word displacement, preserving FP-relative payload
pointers while aligning both native SP and FP. It reserves up to two words per
frame and aligns the saved Llast_SP native window address. Diagnostic window
walking accepts word alignment so a remaining failure can show the bad chain.
The fatal anchor guarantee remains enabled. This correction is experimental.

Validation: 1,160 cases using extracted layout and copy code passed an ASan /
UBSan host model checking alignment, live payloads, save-area separation,
FP-relative pointers and allocation bounds. The launcher passed a mock check
of executable selection and argument forwarding. Prior host continuation
checks pass. These checks do not execute Solaris/SPARC instructions; native
interpreter/mixed and compact-header results remain required.

v30 responds to continuation-test-results-20261007-033608. On native v29,
compiled and compiled-GC both passed the full supplied reproduction test.
Interpreter and mixed aborted in JavaFrameAnchor::capture_last_Java_pc with
"bad stack!"; both reports contain eight completed System.gc cycles before
the abort. This suggests repeated yield/resume progressed and the remaining
failure is near final completion. The reports could not print a usable stack
trace, so that timing interpretation is not a confirmed call-site diagnosis.

The bottom interpreted frame now returns with I5 pointing to the relocated
physical entry window. Its RESTORE(I5, 0, SP) must refill the same save area
that slow thaw moved below the canonical entry SP. Returning with the original
SP could refill stale entry I/L registers. Entry cleanup explicitly resets SP
to the canonical continuation-entry address after the window has been restored,
then accesses metadata and returns to the carrier. Ordinary interpreted-frame
sender-SP behavior and compiled freeze/thaw eligibility are unchanged.

If the anchor still fails, it prints the anchor SP, current flushed SP and up
to 24 bounded window links using SafeFetch before retaining the fatal guarantee.
ContinuationSmoke prints the starting/returned pass numbers to distinguish
resume, completion and subsequent-GC failures in the next evidence archive.

Validation: eight cases using extracted bottom-frame patch and cleanup code
passed a host model that refills the relocated entry window and verifies stale
canonical data would fail. All earlier relocation, window-chain, PC and native
call/refill checks passed; ContinuationSmoke compiles with the host JDK 17.
Cumulative patch dry-run and ZIP CRC / source SHA-256 checks passed. These checks
do not execute Solaris/SPARC code. v30 still needs native build and all four
reproduction modes; the interpreter fix remains a candidate.

v29 responds to continuation-test-results-20261007-024031. All four modes
still aborted on v28. Interpreter/mixed reached Boolean.equals with corrupt
metadata, compiled crashed in Continuation.enter with its receiver equal to
one, and compiled-GC crashed in the return-barrier stub. In the latter report,
G2_thread contained an oop and the attempted entry pointer contained the test's
0x1020304050607080 sentinel. The top Java frame began only 16 bytes above the
stub's SP, inside its 128-byte L/I save area.

The thaw stub now rotates to a separate native window for prepare_thaw and
thaw_entry. The second native window has a full ABI save/home area plus result
storage BELOW the whole reserved Java-frame region. C call spills/refills can
therefore no longer overwrite restored Java frames or read Java spills as the
stub's cached thread pointer. Integer/oop return values stay in the native
window's I0; F0 has a dedicated slot above the ABI argument-home area.
Return barriers recover the actual entry register window before assigning its
canonical SP. After slow thaw, the native window's I6 is patched to the entry's
relocated physical SP before RESTORE, so a window underflow reads the relocated
entry save area. Exception-handler lookup also gets its own native window.

Validation: 64 sequences extracted from the changed emitter passed a host
model that forces window spills/refills, clobbers C-call volatile registers,
relocates the entry save area, copies Java frames and checks integer/FP results.
The v28 relocation, PC and window-chain checks also passed. These models do not
execute SPARC instructions or Solaris trap handlers. Patch dry-run and ZIP CRC /
source SHA-256 checks passed. Native build and all four reproduction modes are
still required; this is another unverified runtime candidate, not a passing port.

v28 responds to continuation-test-results-20261007-021251:
interpreter and mixed crashed in Cont thaw, compiled reported lost/duplicated
resume, and compiled-GC crashed walking a frozen chunk in handle_deopted().

* Remove the synthetic own-PC and reverse-window links from Java frame words
  16/17. Those words are not reserved for continuation metadata and can contain
  compiler spills. Move/copy only the 16 architectural L/I save words when
  relocating a caller window.
* Record the top resume PC and actual bottom window SP in ContinuationEntry,
  above its ABI save/home area. Slow thaw records the relocated entry window,
  which can differ from the canonical entry SP when interpreter locals extend
  into the caller. The thaw stub follows saved I6 links to reconstruct windows
  without overwriting live Java frame data.
* Initialize the chunk walker PC from chunk->pc(); obtain each sender PC from
  the younger frame's saved I7 plus eight. Follow saved I6 rather than assuming
  that a CodeBlob frame size locates an extended caller window. Saved I5
  recovers a compiled sender's unextended SP after an interpreted callee.
* Correct the SPARC raw-PC convention at freeze/thaw patch and anchor sites.
  frame::raw_pc() already subtracts eight; convert back to a resume address
  before the patcher encodes I7. This removes a double subtraction that could
  return to the suspended call again.

Compiled bulk freeze/thaw remains enabled for eligible frames. Window rebuilding
currently searches the forward chain for each child (quadratic with thawed depth);
this candidate prioritizes correct frame contents and is not a performance claim.

Validation: 516 relocation cases, 169 emitted-sequence/window-stream cases and
8 normal/deoptimized PC patch cases passed with host AddressSanitizer and UBSan.
The checks use extracted changed C++ and a model of emitted instructions; they
do not execute SPARC instructions or Solaris register-window traps. Cumulative
patch dry-run, ZIP CRC and source SHA-256 checks passed. Native build and all
four continuation reproduction modes remain required; v28 is unverified there.

v27 corrects the access-control mistake in v26: interpreter_frame_locals()
is private in frame.hpp. All three chunk-stream boundary uses now call the
public interpreter_frame_local_at(0) plus one. Its out-of-line definition in
frame.cpp returns interpreter_frame_locals() plus the offset of local zero
(zero on SPARC). The declaration and definition are present in the supplied
JDK 25 sources, avoiding both the missing inline definition and private access.
The v26 build stopped during compilation; no continuation tests ran.
Validation: audited public/private declarations, the implementation and the
SPARC local-index offset; cumulative patch dry-run and ZIP verification passed.
Native Solaris/SPARC compilation and execution are still pending.

v26 fixes the v25 link failure reported for instanceStackChunkKlass.o. The SPARC
chunk stream called ContinuationHelper::InterpretedFrame::frame_bottom with only
its declaration visible in several compilation units. All three uses now call
the already included frame::interpreter_frame_locals() accessor plus one, which
has the same heap-relative/stack-absolute semantics. This removes the helper
header dependency rather than adding an inline-header include cycle.
The v25 build stopped at linking, so it supplied no new runtime test results.
Validation: checked equivalence against both inline definitions and verified the
cumulative patch and ZIP. A native SPARC rebuild remains required.

v25 responds to the four v24 continuation crash reports. The rebuild succeeded,
but interpreter/mixed runs crashed on a GC worker in handle_deopted() with a
null CodeBlob (load at offset 0xb0). Both compiled runs crashed in slow freeze
reading the saved I6 at offset 0x70 from a frame SP of 0x7fe.

The yield stub previously embedded an absolute PC from its temporary CodeBuffer.
That address does not track installation of the native nmethod; the compiled
report even classified its anchor PC as adapter code. v25 uses RDPC at runtime.
FLUSHW alone also excludes the currently executing window. A temporary SAVE,
FLUSHW, RESTORE now spills the yield window itself before publishing its anchor.

Interpreted packing changed caller.sp() without moving the caller register save
area or its synthetic own-PC slot. The source interpreter layout also places
locals in the caller frame: copying an interpreted frame crosses the caller's
save area and can overwrite already relativized metadata. v25 relocates the
17-word save/PC region and snapshots/restores it across these overlapping copies
in freeze and interpreted thaw. It preserves the caller's pre-extension SP for
I5, uses the normal SPARC sender constructor for adapter/deopt handling, and
stops interpreted chunk iteration at the bottom frame's local-data boundary.

These are source-backed candidate repairs, not verified Solaris runtime fixes.
The actual relocation helper passed 516 overlapping heap/native and
interpreted/compiled cases with host address/undefined-behavior sanitizers.
Leak detection was disabled because the host sandbox prevents its /proc scan.
The cumulative patch dry-run and ZIP CRC/content hashes passed. Native SPARC
compilation, GC, register-window traps, continuation resumption and fast-path
execution still require the following rebuild and reproducer.

v24 fixes a build regression introduced by the v22 NULL cleanup. Four C1
patchable AddressLiteral placeholders now explicitly use (address)nullptr;
untyped nullptr is ambiguous between the address and jobject constructors.
The latest build output contains two such errors in c1_CodeStubs_sparc.cpp;
the audit found two more calls in c1_LIRAssembler_sparc.cpp. This version keeps
the v23 continuation changes. The failed rebuild provided no runtime results.
Validation: checked all AddressLiteral null placeholders, compiled the extracted
constructor overloads on the host, and verified the cumulative patch and ZIP.
A Solaris/SPARC rebuild is still required.

v23 uses the supplied pre-rebuild evidence archive (105 crash reports) to repair
additional SPARC continuation defects. These reports came from older binaries
and do not verify either v22 or v23.

44 reports identify Continuation.doYield; 28 directly show instruction 81e80000
(RESTORE) at the faulting PC. The unwind loop compared live SP to the canonical
entry SP. SPARC c2i adapters explicitly extend SP without adding a register
window. The loop can therefore miss the entry window and restore through the
carrier stack. v23 identifies the entry by its stable FP (canonical entry SP
plus ContinuationEntry::size()), then resets SP to the canonical entry SP before
cleanup. This retains the real register-window restore chain.

The interpreted freeze code also mistook its own I5_savedSP for its own SP.
The interpreter and frame.cpp show that I5_savedSP belongs to the sender.
Using it as the copy boundary skips this frame's save area, including live
interpreter registers and the synthetic own-PC slot. v23 copies from physical
SP, uses that convention in the chunk iterator, and stops the sender-SP setter
from replacing the frame's own unextended SP. The two stackChunk frame-count
crashes in the archive are consistent with invalid frozen frame metadata;
this is a candidate explanation, not a verified diagnosis of both crashes.

Validation: audited against SPARC c2i frame extension and interpreter saved-SP
code; checked a 512-case register-window/adapter-extension semantic model;
compiled the reflection-based ContinuationSmoke on host JDK 17; checked shell
syntax. Native SPARC execution and actual continuation tests remain required.
The host model does not validate OS register-window traps or freeze/thaw GC.

Use v27 instead of v26 for the next rebuild. From the repository after extraction:

```bash
gmake images test-image JOBS=8 && bash tests/run-continuation-repro.sh
bash tests/run-header-matrix.sh
bash tests/rerun-failed-233.sh
bash tests/collect-failure-evidence.sh
```

The continuation reproducer covers interpreter/mixed execution and compiled
full/partial thaw, with an additional suspended-stack GC run. Product execution
alone does not prove fast-path entry; use the existing fastdebug trace guidance
in tests/ContinuationFastPath.java to confirm that separately.


v22 fixes defects identified while reviewing the 233 unsuccessful jtreg cases.
It is cumulative over v21 and preserves continuation fast paths, lightweight
locking, C1/C2, G1 barriers and optimized arithmetic stubs.

Changes in v22:
- Compact headers: read the narrow klass from the mark word in interpreter,
  C1, C2 and inline-cache checks. Initialize the class prototype header during
  fast allocation, preserve the absence of a klass gap, clear instance fields
  from the actual header boundary, and account for the extra instruction in
  inline-cache alignment and dynamic-call return offsets.
- C1 arrays: pass the header size in bytes instead of truncating to whole heap
  words. A 20-byte uncompressed-klass header was rounded down to 16, causing
  body clearing to overwrite the array length. A 12-byte compact header has
  the same problem. Clear the first four payload bytes separately, then clear
  aligned eight-byte words. Do not select aligned copy stubs when the array
  payload base is only four-byte aligned.
- Monitor-only locking: admit SPARC LockingMode=0 after auditing interpreter,
  C1, C2 and synchronized JNI paths, which already use runtime monitor locking.
- Source convention: remove the reported legacy null tokens from port source
  and shared files. C++ pointers use nullptr, integer JNI slots and DTrace use 0.

Validation completed here: combined SPARC/G1 ADLC generation passed (15 existing
unused-operand warnings); ArrayHeaderSmoke passed all nine combinations of
interpreter/C1/C2 and normal/no-CCP/no-compression on Linux/x86 JDK 17. This
validates the test oracle, not the patched SPARC JVM. Compact-header execution
and the entire native build require the Solaris/SPARC machine.

This archive does not claim all 233 cases are fixed. failure-status-233.csv has
one row for every case with observed output and the required next step. 29 cases
failed before running jcstress because its jar was missing; 24 lacked the native
gtest library. Remaining continuation/JVMTI crashes, timeouts and independent
compiler expectations require reruns and retained evidence.

From ~/git/jdk25 after extracting the ZIP into the repository:

```bash
gmake images test-image JOBS=8 && bash tests/run-header-matrix.sh
bash tests/rerun-failed-233.sh
bash tests/collect-failure-evidence.sh
```

The header matrix runs 15 header/compiler combinations and monitor-only locking,
with separate logs and crash reports. The 233-case rerun uses the normal VM
configuration; it does not exclude cases or disable optimizations. The evidence
collector locates crash reports rather than assuming a scratch-directory name,
and collects failed .jtr results, header-matrix results and build/rerun logs.
Preserve the existing crash logs with the collector before rerunning tests if
possible, as jtreg can reuse scratch directories.

See TEST-DEPENDENCIES.md for missing test dependencies. To pass a resolved
jcstress artifact to the rerun:

```bash
JCSTRESS_JAR=/absolute/path/to/jcstress-tests-all.jar bash tests/rerun-failed-233.sh
```

v21 adapts SPARC multiplyToLen to the JDK 25 five-argument runtime ABI.
The supplied crypto tests crash in StubRoutines::multiplyToLen. The shared C2
caller and OptoRuntime signature now pass x, xlen, y, ylen and z; the old SPARC
stub still consumed I5 as a sixth zlen argument. The stub now initializes I5
with xlen + ylen before selecting any multiplication kernel. VIS3/MPMUL and the
other optimized paths remain enabled. Only cpu/sparc/stubGenerator_sparc.cpp
changes relative to v20; all earlier fixes are retained.

BigIntegerMultiplySmoke independently checks 2700 products with base-256
schoolbook arithmetic, including odd/even, unequal and MPMUL-sized operands.
It passed on Linux/x86 JDK 17 with C2 enabled. Solaris/SPARC build and runtime
validation remain required. Run it with the newly built JDK:

```bash
build/solaris-sparcv9-server-release/images/jdk/bin/java \
  -Xbatch -XX:-TieredCompilation tests/BigIntegerMultiplySmoke.java
```

The broader 32-job run also exhausted Solaris swap/tmpfs capacity. Diagnose
with swap -s, swap -l and df -h /tmp, preserve crash logs before cleanup, and
repeat the crypto reproducer at one job before returning to the full suites.

v20 fixes an out-of-range C2 G1 pre-barrier branch in the supplied javac
ClassReader.classSigToType crash. At 0xffffffff5f87a3a0, CBCOND word 32d50940
branches to 0xffffffff5f879cc8. The intended pre-barrier stub begins at
0xffffffff5f87acc8 with the old-reference load, null check and SATB enqueue.
The required displacement is +2344 bytes, beyond CBCOND's +2044-byte limit;
its 10-bit word displacement wraps by 4096 bytes into unrelated method code.
That explains reaching the byte-array store with pointer-valued index registers.

C2 pre-barriers now emit CMP, a 19-bit-displacement conditional branch, and a
NOP delay slot to their deferred stub entry. Other short branches remain enabled.
The archive retains v19's CAS constraint fix and all earlier changes. Only
cpu/sparc/gc/g1/g1BarrierSetAssembler_sparc.cpp changes relative to v19.
The supplied instruction was decoded locally and branch-range boundaries checked;
Solaris/SPARC build and execution still need validation on the target machine.

Rebuild images and test-image, then repeat the java_naming jtreg test with C2
and G1 enabled. Do not disable UseCBCond or tiered compilation for that check.

v19 fixes the supplied C2 ConcurrentHashMap.transfer SIGSEGV. The G1 reference
CAS rules wrote the Boolean result before the post-write barrier, while their
register constraints permitted that result to reuse an input register. The
crash uses L0 both as the CASA address and as the result; MOV 1,L0 destroys the
address. The post barrier then calculates its card from 1. This gives exactly
0xffffffff557f0000, the reported fault address. Both g1CompareAndSwapP_bool and
g1CompareAndSwapN_bool now declare TEMP_DEF res, preventing the result from
sharing an instruction input. This covers strong and weak reference CAS.

ADLC successfully generated the combined SPARC/G1 matcher, including result
MachTempNode constraints for both strong and weak variants. The new
ConcurrentHashMapResizeSmoke test passed with G1/C2 on Linux/x86 JDK 17 with
compressed oops enabled and disabled. This host cannot compile or run the
Solaris/SPARC JVM; rebuild and reproduce the jtreg test on that machine.
Only cpu/sparc/gc/g1/g1_sparc.ad changes relative to v18. All previous changes,
including continuation fast paths, lightweight locking, and the javadoc build
fix, remain included.

Targeted validation after rebuilding images and test-image:

```bash
mkdir -p /tmp/jdk25-cas-test
build/solaris-sparcv9-server-release/images/jdk/bin/javac \
  -d /tmp/jdk25-cas-test tests/ConcurrentHashMapResizeSmoke.java
build/solaris-sparcv9-server-release/images/jdk/bin/java \
  -Xbatch -XX:+UseG1GC -XX:-TieredCompilation -Xmx256m \
  -cp /tmp/jdk25-cas-test ConcurrentHashMapResizeSmoke
build/solaris-sparcv9-server-release/images/jdk/bin/java \
  -Xbatch -XX:+UseG1GC -XX:-TieredCompilation -XX:-UseCompressedOops -Xmx256m \
  -cp /tmp/jdk25-cas-test ConcurrentHashMapResizeSmoke
```

v18 fixes generation after the helper compilation succeeded with v17. The Java 25
runtime rejected Check$CheckContext from the interim compiler because it was built
as Java 21 preview bytecode (65.65535). Java 25 accepts preview bytecode only for
its own release (69.65535). Solaris generators now run the normal JDK 25 compiler,
jdeps, and javadoc modules, with exports translated to their normal module names.
They no longer receive INTERIM_LANGTOOLS_ARGS or interim-module paths. Runtime
--enable-preview remains for current-release preview classes. Helper compilation
continues using the working interim compiler with Java 25 source/platform modules.
Non-Solaris generator arguments retain their original interim module selection.

GNU make expansion checks passed: correct target/platform/runtime, no interim
module references on Solaris generator launches, normal javac exports, and retained
preview support. All HotSpot files are unchanged from v17. Java 25 generation and
Solaris execution are not available on this host and require the next build check.

v14 implements SPARC lightweight locking (LockingMode=2) in the interpreter,
C1, C2, and synchronized JNI wrapper paths. VM initialization now accepts mode 2
instead of replacing it with legacy locking. The fast path updates the mark-word
lock bits with CAS and records oops on the JavaThread LockStack. Adjacent recursive
locks push/pop stack entries; full stacks, nonadjacent recursion, inflated monitors,
and failed CAS use the shared runtime. Slow unlocks retain the complete lock stack.
Object-monitor-table caches are cleared before acquisition when enabled. Explicit
acquire/release barriers are emitted; object, BasicLock, and thread registers survive.
C1 unlock uses O7, which is outside the C1 register allocator; I7 holds the frame's
return address. Only named temporaries are clobbered in C2 and JNI helpers.

The warning is removed by implementing the selected mode, not by hiding the message.
This source candidate still requires a Solaris/SPARC build and runtime validation.
No .gmk files are changed.

v13 changes Solaris/SPARC compressed class-space placement to use the existing
Metaspace OS-selected mapping fallback, keeping compressed class pointers enabled.
The supplied javac failure reports a 166344-byte native malloc failure despite
roughly 105 GiB of free physical RAM. Class space starts at 0x10c000000, just
above native allocations near 0x10b9c5fe0. This suggests the low-address class
mapping obstructs growth of the Solaris brk-based native heap. This patch avoids
that explicit low-address probe; validation on Solaris is still needed to confirm
the diagnosis. SPARC already implements nonzero-base class pointer encoding.
No .gmk files are changed, and the continuation fast path remains included.

v12 adds vmreg_sparc.inline.hpp to the C2 barrier register-save implementation,
providing the inline definition of Register::as_VMReg() required by v11.
No .gmk files are changed.

v11 fixes the C2 G1 barrier runtime-call register preservation implicated by
the attached HashMap.putVal crash. Normal -version startup now succeeded on
the user's v10 build. The javac crash occurred at the return polling load,
with G2 different from the current JavaThread; its last runtime call was the
G1 post-write barrier. That barrier used call_VM_leaf(G2_thread, ...), which
cannot cache the JavaThread in a register that the C call itself may clobber.

SaveLiveRegisters now always saves/restores G2, and places saved registers
after all 16 V9 register-save words plus 6 outgoing argument-home words.
G1 C2 stubs marshal their two arguments and call the non-safepointing leaf
runtime directly under that save scope. The shared save area protects G2
across the call without an invalid global-register thread-cache argument.
The only added HotSpot files relative to v10 are:
* cpu/sparc/gc/shared/barrierSetAssembler_sparc.cpp
* cpu/sparc/gc/g1/g1BarrierSetAssembler_sparc.cpp

This corrects concrete source defects and matches the crash evidence; SPARC
compilation/runtime validation is still required. All continuation fast-path
changes remain included. The javadoc source/preview mismatch is addressed by v18.

## Apply and build

The archive contains full replacement files with repository paths. It includes
the access-flag and field-type fixes from v2/v3 and replaces v4's disabled
continuation default. Save any independent local edits before overwriting.

From the JDK 25 repository:

```bash
unzip -o /path/to/jdk25-sparc-continuations-v19.zip
gmake images 2>&1 | tee /tmp/build25.log
build/solaris-sparcv9-server-release/jdk/bin/java -Xint -version
build/solaris-sparcv9-server-release/jdk/bin/java -version
```

Do not pass `-XX:-VMContinuations`. Both launches should finish without a fatal
error. Check the second launch for compiler initialization warnings; printing a
version alone does not establish that C1 and C2 are working.

## Changes

* Generate enterSpecial/doYield wrappers before the normal JNI wrapper path.
  Register enterSpecial's nmethod, interpreter entry, thaw return PC, cleanup PC,
  exception entry and doYield stub with the shared continuation runtime.
* Include continuation and chunk oop fields in entry-frame GC maps.
* Put the continuation fields after the V9 window-save and argument-home areas
  so register spilling cannot corrupt the parent, continuation or chunk fields.
* Flush windows before freeze; unwind real windows on successful yield and
  rebuild them when mounting thawed frames.
* Use 64-bit loads/stores for intx held-monitor counts and the saved parent count.
* Store intra-chunk window links in words, matching their readers. Relocate
  interpreter stack/locals pointers, preserve extended-SP information and fix
  the descending-locals copy boundary.
* Keep a chunk frame's own PC separate from its architectural saved I7 sender PC.
* Enable compiled bulk freeze and full/partial bulk thaw through
  UseContinuationFastPath. Freeze stores relative I6 window links and separate
  own PCs; thaw restores biased I6 links and patches the last callee's I7 to the
  entry PC or return barrier. Rebuild live windows in linear time.
* Check SPARC freeze eligibility by walking the actual frames, because this
  assembler does not maintain fastpath markers at every interpreter boundary.
  Fall back for interpreted/deoptimized frames, held locks, preemption, extended
  frames, or nonzero continuation-entry argument size. Fast thaw checks compiled
  window geometry and uses the existing GC/JVMTI/PreserveFramePointer guards.
* Allocate a separate fast chunk rather than merge into a nonempty SPARC chunk.
  Empty chunks can be reused. GC-processed chunks retain the slow thaw path.
* Correct native-wrapper frame-size units and skip the actual doYield frame on
  freeze. Resume at the thawed top frame's own PC without popping its window.
* Add the missing ForwardException rule to sparc.ad.

The included patch is cumulative relative to the original attached jdk25.zip;
use the full files when your tree already has v2/v3/v4.

## Lightweight locking tests

Compile with the working JDK 21, then run the new JDK 25 VM. Require PASS and
verify that PrintFlagsFinal reports LockingMode=2 without the unsupported-mode warning.

```bash
mkdir -p continuation-test-classes
/usr/jdk/jdk-21/bin/javac -d continuation-test-classes tests/LightweightLockingSmoke.java
build/solaris-sparcv9-server-release/jdk/bin/java -XX:+PrintFlagsFinal -version 2>&1 | ggrep LockingMode
build/solaris-sparcv9-server-release/jdk/bin/java -Xint -XX:LockingMode=2 -Xmx128m -cp continuation-test-classes LightweightLockingSmoke
build/solaris-sparcv9-server-release/jdk/bin/java -XX:TieredStopAtLevel=1 -Xbatch -XX:LockingMode=2 -Xmx128m -cp continuation-test-classes LightweightLockingSmoke
build/solaris-sparcv9-server-release/jdk/bin/java -XX:-TieredCompilation -Xbatch -XX:LockingMode=2 -Xmx128m -cp continuation-test-classes LightweightLockingSmoke
build/solaris-sparcv9-server-release/jdk/bin/java -XX:LockingMode=2 -Xmx128m -cp continuation-test-classes LightweightLockingSmoke virtual
```

Repeat the three platform modes with `-XX:+UseObjectMonitorTable`. The test covers
recursive locking, sixteen distinct nested locks (overflow), nonadjacent recursion,
hash-code inflation, exception exits, contended updates, wait/notify, and GC.
Virtual mode additionally sleeps and collects while holding recursive locks.
Platform test expectations passed here on x86 JDK 17 in interpreter/C1/C2 modes.
Virtual mode cannot run on that host VM.

For synchronized native wrappers, compile the optional JNI library on Solaris:

```bash
/usr/gcc/15/bin/g++ -m64 -shared -fPIC \
  -I/usr/jdk/jdk-21/include -I/usr/jdk/jdk-21/include/solaris \
  tests/LightweightLockingSmoke.cpp -o continuation-test-classes/libLightweightLockingSmoke.so
build/solaris-sparcv9-server-release/jdk/bin/java -XX:LockingMode=2 -Xmx128m \
  -Djava.library.path=continuation-test-classes -cp continuation-test-classes LightweightLockingSmoke native
```

For direct yield and carrier migration while holding recursive lightweight locks:

```bash
/usr/jdk/jdk-21/bin/javac --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -d continuation-test-classes tests/LightweightContinuationSmoke.java
build/solaris-sparcv9-server-release/jdk/bin/java -XX:LockingMode=2 -Xmx128m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes LightweightContinuationSmoke
build/solaris-sparcv9-server-release/jdk/bin/java -XX:LockingMode=2 -Xmx128m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes LightweightContinuationSmoke migration
```

Repeat direct mode with `-Xcomp -XX:-TieredCompilation` and a fastdebug VM's
`-Xlog:continuations=trace` to check freeze_fast/thaw_fast execution. Require PASS;
a mounted continuation must own its locks, and a suspended one must leave no locks
on the carrier's LockStack. These continuation and native tests are not host-validated.

`tests/check_lightweight_sequences.py` models the actual helper instruction-call
sequences, including SPARC delay slots, recursion, underflow/overflow, and injected
CAS/inflation races. 160000 cases passed, with debug clearing and monitor caches
both enabled and disabled. This checks semantics, not binary encodings or hardware.

## G1 C2 regression test

Compile the included test using the working JDK 21 compiler, then run with
the new JDK 25 binary and C2 enabled:

```bash
mkdir -p continuation-test-classes
/usr/jdk/jdk-21/bin/javac -d continuation-test-classes tests/G1BarrierSmoke.java
build/solaris-sparcv9-server-release/jdk/bin/java \
  -XX:-CreateCoredumpOnCrash -Xmx64m -XX:+UseG1GC -Xbatch \
  -cp continuation-test-classes G1BarrierSmoke
```

The HashMap update/readback and GC stress test passed on the host x86 JDK 17.
That confirms its expectations, not the SPARC barrier patch. A host-side layout
check verified disjoint window/home/save areas with 1..96 saved slots.

## C1 Class.isInstance regression test

Once normal startup succeeds:

```bash
/usr/jdk/jdk-21/bin/javac -d continuation-test-classes tests/C1InstanceOfSmoke.java
build/solaris-sparcv9-server-release/jdk/bin/java \
  -XX:TieredStopAtLevel=1 -Xbatch \
  -XX:CompileCommand=dontinline,C1InstanceOfSmoke::test \
  -cp continuation-test-classes C1InstanceOfSmoke
```

Require PASS. Repeat with TieredStopAtLevel=3 and normal tiered compilation.
The test covers concrete/inherited classes, interfaces, reference/primitive
arrays, primitive Class mirrors, null objects and null-mirror exceptions.
It passed locally on the x86 host JDK 17 C1 JVM. That validates the test's
expected results, not the new SPARC instructions.

## Staged runtime tests

The reflection-based smoke test can be compiled by the working JDK 21 compiler.
Run one stage at a time and retain the first failure and its hs_err file.

```bash
mkdir -p continuation-test-classes
/usr/jdk/jdk-21/bin/javac -d continuation-test-classes tests/ContinuationSmoke.java

build/solaris-sparcv9-server-release/jdk/bin/java -Xint -Xmx64m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes ContinuationSmoke direct

build/solaris-sparcv9-server-release/jdk/bin/java -Xint -Xmx64m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes ContinuationSmoke migration

build/solaris-sparcv9-server-release/jdk/bin/java -Xint -Xmx64m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes ContinuationSmoke virtual
```

The direct test checks eight yields, resumption, completion, recursive live
locals and GC while suspended. Migration resumes on a different platform thread
on every pass. The virtual test checks creation, repeated sleep/resume and join.

After all interpreted tests pass, repeat them with `-XX:TieredStopAtLevel=1`,
then `-XX:TieredStopAtLevel=3`, then normal tiered compilation. Run each case in a
new JVM. jtreg's continuation and virtual-thread suites are still required before
claiming broad correctness; these smoke tests are only the first gate.

## Compiled fast-path test

After startup and interpreted tests pass, compile the typed test with JDK 21:

```bash
/usr/jdk/jdk-21/bin/javac --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -d continuation-test-classes tests/ContinuationFastPath.java
```

Use a **fastdebug** build for trace logging; the fast-path trace messages use
HotSpot's develop logging and are absent from product builds. Run each command
in a fresh JVM. Small/deep recursive stacks exercise full and partial thaw.

```bash
JAVA=build/solaris-sparcv9-server-fastdebug/jdk/bin/java
$JAVA -Xcomp -XX:-TieredCompilation -Xmx128m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -Xlog:continuations=trace:file=/tmp/continuation-fast.log \
  -cp continuation-test-classes ContinuationFastPath

ggrep -E 'freeze_fast SPARC|thaw_fast partial:' /tmp/continuation-fast.log

$JAVA -Xcomp -XX:-TieredCompilation -Xmx64m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes ContinuationFastPath gc

$JAVA -Xcomp -XX:-TieredCompilation -XX:-UseContinuationFastPath -Xmx128m \
  --add-exports java.base/jdk.internal.vm=ALL-UNNAMED \
  -cp continuation-test-classes ContinuationFastPath
```

Require PASS in all three runs and both freeze_fast and thaw_fast messages in
the first log. A PASS alone does not prove that the fast path ran. Repeat with
C1 (`-Xcomp -XX:TieredStopAtLevel=1`) and normal tiered compilation. The GC test
checks suspended-stack roots and exercises slow fallback after GC processes a
chunk; it is not expected to remain entirely on the fast path.

## Validation and remaining limits

The actual JDK 25 ADLC was compiled locally and successfully generated the SPARC
matcher, including the Op_ForwardException production. The ZIP was checked for
CRC integrity and source-path/content correspondence. A host-side geometry
check covered 10,000 randomized full/partial window relocation cases; this does
not execute generated SPARC instructions or validate GC maps.

HotSpot C++ compilation and SPARC execution were not available locally. Startup,
yield/resume, GC, migration, compiled frames and exception propagation therefore
remain unverified. Lightweight locking is implemented in v14; explicit legacy
mode still pins synchronized sections. Asynchronous preemption is not implemented.
It also does not address the separate source-21/--enable-preview build error in
the JDK build makefiles, which were not included in the attached source archives.
