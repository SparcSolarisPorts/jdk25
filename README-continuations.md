# JDK 25 Solaris/SPARC continuation candidate (v17)

This is an experimental source candidate for the attached JDK 25 tree. It
re-enables VMContinuations and implements missing entry/yield native wrappers.
It is not yet a runtime-validated SPARC continuation port.

v17 corrects the Solaris javadoc helper compilation's platform-class selection.
The v16 source/target change removed the unnamed-variable error, but CreateSymbols
then could not find java.lang.classfile. Source/target 25 alone does not select
Java 25 platform APIs when the interim compiler runs against the boot JDK image.
This rule now uses TARGET_RELEASE_NEWJDK_UPGRADED, which JavaCompilation.gmk defines
as source/target 25 plus --upgrade-module-path $(JDK_OUTPUTDIR)/modules --system none.
The generated helpers continue to run with the already-built JDK 25 executable.
The existing interim compiler flags and exports remain, and JavaCompilation.gmk
itself is unchanged. All HotSpot files are byte-for-byte unchanged from v16.

GNU make expansion checks passed for the Solaris target/module selection and the
unchanged non-Solaris path. Actual Java 25 compilation and Solaris execution are
not available on this host. The current build must contain the compiled Java 25
platform modules, including java.base/java/lang/classfile. If the next build still
reports missing packages, retain the failing javac command/argument files as well
as its log so the final module search path can be inspected.

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
changes remain included. The javadoc source/preview mismatch is addressed by v17.

## Apply and build

The archive contains full replacement files with repository paths. It includes
the access-flag and field-type fixes from v2/v3 and replaces v4's disabled
continuation default. Save any independent local edits before overwriting.

From the JDK 25 repository:

```bash
unzip -o /path/to/jdk25-sparc-continuations-v17.zip
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
