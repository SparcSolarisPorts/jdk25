v80: SafeFetch fault PC and high-address class encoding endpoint
==============================================================
Observed Solaris results
- jcstress: all 29 jtreg categories passed, exit 0.
- gtest: 20 wrappers passed, 4 failed, 6 inapplicable.
- NMT detail/summary crashed at NMT.location_printing_mmap_1_vm.
- NMT off crashed later at os.test_print_hex_dump_vm.
- GTestWrapper reported CompressedKlass.basics_vm's endpoint assertion,
  then crashed at GuardedMemory.unmapped_vm. These are wrapper counts,
  not counts of all individual native assertions or tests still to run.

SafeFetch correction
The Solaris/SPARC static assembly put _SafeFetch32_fault and
_SafeFetchN_fault on retl. The memory load was in retl's delay slot,
whose saved fault PC is four bytes later. The shared POSIX handler only
accepts an exact match to the fault symbol. The deliberate unreadable-memory
probes therefore bypassed SafeFetch recovery and crashed the native test.
Move each load onto the fault symbol, followed by retl/nop. Error-return
continuations remain retl/mov. ucontext_set_pc already restores PC and nPC.
Both 32-bit and native-width loads are fixed. No signals are ignored and
no fault is converted into a successful read.
The supplied offsets (0x13a4168 and 0x13a4178, 16 bytes apart) and failing
unreadable-memory probes are consistent with the two old SafeFetch loads;
exact native symbolization is still pending.

Compressed class endpoint correction
CompressedKlass.basics_vm reported actual Klass range end
0xffffffff51000000 above encoding end 0x10000000. The encoding endpoint
was computed by adding a full encoding span to a high Solaris LP64 base;
the sum wrapped around uintptr_t. Actual class addresses can remain valid
while the theoretical full encoding interval extends beyond address space.
Clip the public metadata endpoint to UINTPTR_MAX and use that same endpoint
in debug initialization checks. The last byte is conservatively excluded;
it cannot contain an aligned Klass. Encoding/decoding, reservations, base,
shift and generated load instructions are unchanged. This shared arithmetic
fix also handles overflow on other platforms without changing normal sums.

Validation here
- Actual assembly interpreted by a host PC/nPC/delay-slot model: 16 valid and
  invalid read/default-value cases passed. Original source rejects the fault
  label check, confirming the check detects the old defect.
- Actual encoding_range_end C++ function compiled with undefined-behavior
  sanitizer: 64 endpoint combinations passed against 128-bit arithmetic.
  Original source fails on high bases. Debug assertion uses the same helper.
- Bash syntax and mocked rerun command/timeout status paths checked.
- Cumulative ZIP CRC and all source SHA-256 entries verified.
No Solaris/SPARC execution is possible on this host. These are source fixes
awaiting native confirmation, not a claim that the full gtest suite now passes.
All prior VM fixes and continuation fast paths are retained.

Apply the cumulative ZIP at repository root, then:
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/rerun-gtest-v80.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
Build parallelism uses your existing make defaults; test concurrency defaults
16, overridable by JDK25_TEST_JOBS. Full gtest directory, 30-minute cap,
no exclusions. Send the text-only evidence.zip on failure. A successful run
may reveal tests previously hidden by the aborted wrappers; keep their logs.
The existing JDK25_TEST_JOBS=16 bash tests/rerun-priority-crashes-v52.sh
can be used afterward to check the earlier 26-case regression batch.
