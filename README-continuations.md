# JDK 25 Solaris/SPARC continuation candidate (v9)

This is an experimental source candidate for the attached JDK 25 tree. It
re-enables VMContinuations and implements missing entry/yield native wrappers.
It is not yet a runtime-validated SPARC continuation port.

v9 addresses the attached normal-startup SIGILL in RuntimeStub::C1 Runtime
is_instance_of_blob. SPARC's C1 generator had no case for is_instance_of_id,
so it generated an explicit unimplemented-entry trap. The new assembly leaf
stub implements Class.isInstance using the existing SPARC fast and secondary
subtype checks, handles null objects and primitive mirrors, and returns the
boolean through the SPARC C calling convention. It does not call C++ or
safepoint. This is the only added/changed HotSpot source relative to v8:
cpu/sparc/c1_Runtime1_sparc.cpp.

The supplied v8 log shows interpreter-only version startup reached the version
output; normal startup still failed in C1. Neither establishes continuation
freeze/thaw correctness. All earlier continuation/fast-path fixes are included.

## Apply and build

The archive contains full replacement files with repository paths. It includes
the access-flag and field-type fixes from v2/v3 and replaces v4's disabled
continuation default. Save any independent local edits before overwriting.

From the JDK 25 repository:

```bash
unzip -o /path/to/jdk25-sparc-continuations-v9.zip
gmake hotspot 2>&1 | tee /tmp/build25-hotspot.log
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
remain unverified. Legacy SPARC locking still pins synchronized sections; this
candidate does not implement lightweight locking or asynchronous preemption.
It also does not address the separate source-21/--enable-preview build error in
the JDK build makefiles, which were not included in the attached source archives.
