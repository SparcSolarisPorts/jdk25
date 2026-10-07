# JDK 25 Solaris/SPARC continuation candidate (v30)

This is an experimental source candidate for the attached JDK 25 tree. It
re-enables VMContinuations and implements missing entry/yield native wrappers.
It is not yet a runtime-validated SPARC continuation port.

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
