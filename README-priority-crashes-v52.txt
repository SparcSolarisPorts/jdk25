HISTORICAL v52 NOTE: its entry-slot restoration caused a native GC regression.
That anchor/layout change is superseded by v53; see README-anchor-regression-v53.txt.
The vector/deoptimization changes remain.

v52: fixes targeting the four highest-priority groups from the 233-case rerun

Native evidence was read from priority-1-2-rerun-20261014-012127.zip.
Recorded results: 124 passed, 93 failed, 14 timeout errors and two unfinished.
Missing dependencies account for 29 jcstress and 24 gtest failures.
The entire 25-case priority 1-2 batch had passed before this broader run.

1. JVMTI continuation frame walking
The interpreter can relocate the physical ContinuationEntry register window
for its locals. Canonical entry save slots can then contain overwritten data.
After successful freeze, unwind_frames publishes that canonical SP as its
anchor; JVMTI subsequently walks it. Crashes show frame::frame reading through
a caller SP with lost high bits. v52 saves entry I6/I7 in separate non-oop
metadata on entry, restores the canonical caller link/PC before publishing
that anchor, and publishes PC before SP. The actual entry-window size, metadata
offsets and generated OopMaps remain derived from ContinuationEntry::size().
Native confirmation that this resolves the crash cluster is still required.

2. C2 vector SIGBUS
The TestBiMorphicMismatchedMemSegment crash has BUS_ADRALN at
0x1ff7efe36. Instruction 0xd13c2010 is STDF at L0+16; L0 ends in 0x26.
The eight-byte vector load/store rules used LDDF/STDF without checking the
arbitrary byte offsets allowed by the Vector API's MemorySegment operations.
v52 computes the actual address, keeps the aligned instruction fast path,
and uses big-endian byte assembly/disassembly for other alignments. Zero-vector
stores use the same alignment split. ADLC operands declare temporary registers
and killed condition codes, and these variable-size rules no longer claim
four-byte instruction sizes.
The raw FP/integer bit transfers need VIS3. On older VIS settings the matcher
uses the existing Java/scalar fallback for vector memory operations; no vector
API operation is skipped. Default T8 VIS3 paths retain compiled vector support.
No fixed stack scratch slot or ABI home area is overwritten.

3. Deoptimization
ContYieldBreakPointTest crashes at address 0x78 in frame::patch_pc while slow
thaw rebuilds a compiled frame. The younger window has not been installed yet.
v52 defers that physical PC store when thread is null and younger_sp is null;
slow thaw patches the return PC once its younger window exists and publishes
the top resume PC at finish_thaw. It now recognizes deoptimization from the
new hardware PC rather than the unchanged logical PC, preserving the original
PC for oop maps. This also targets the deoptimization stress failure, whose
signal-11 exit did not include an hs_err in the uploaded archive. That stress
failure is not claimed resolved until its native rerun passes.

4. Suspend/monitor/event timeouts
The focused batch includes the unfinished GetOwnedMonitorInfo/SuspendResume1
cases plus failed JVMTI continuation, frame-pop, stack-trace, monitor and
thread-state cases. The frame-anchor and thaw/deopt corrections address shared
stack-walking defects on these paths. No independent handshake/monitor fix has
been invented from a timeout status alone. Remaining timeouts will need native
stacks from the new build; their resolution is not yet confirmed.

Validation performed locally:
- SPARC ADLC generated the matcher successfully (existing unused operands only).
- Actual vector helper bodies executed under a recording/semantic assembler
  stub: all 8 alignments, exact raw bits (including NaN payload), surrounding
  guards, and zero stores passed.
- Actual frame::patch_pc body compiled with HotSpot stubs: deferred thaw,
  native physical patch, original-PC preservation and deopt-state checks passed.
- Actual ContinuationEntryPD restore code preserved full-width caller links
  and adjacent slots; saved metadata offsets lie beyond the ABI spill area.
- Shell syntax, cumulative source retention, ZIP CRC and source hashes checked.
No full Solaris HotSpot compilation or native jtreg execution occurred locally.

New native vector smoke covers byte and float-backed MemorySegments at every
alignment in C1, mixed, C2, and a deliberately lower VIS setting. Each process
has a 120-second limit. Focused original jtreg batch: 26 cases, two concurrent
jobs by default, existing timeoutFactor=4, additional 45-minute batch ceiling.
The earlier runner and all original tests remain unchanged by default.

Apply the cumulative ZIP at the repository root and run:

  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-vector-memory-alignment-repro.sh &&
      bash tests/run-continuation-repro.sh &&
      bash tests/run-mixed-yield-repro.sh &&
      bash tests/rerun-priority-crashes-v52.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

For tier counts and complete unresolved membership, see
v52-unresolved-tier-membership.txt. The groups were resolved recursively from
this repository's TEST.groups, including subtraction rules. Each selected
#id case counts separately; dependencies and unfinished cases count as unresolved.
All unresolved: tier1=45, tier2=6, tier3=11, tier4=18, outside tiers=29.
Excluding missing dependencies: tier1=39 (including 2 unfinished), tier2=6,
tier3=11, tier4=0. These tier numbers are test-group classifications, not
severity rankings, and include the AArch64 test that was selected on SPARC.
