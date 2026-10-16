v69: bound SPARC C2 Block_Array growth before allocation and zeroing

The report from priority-1-2-rerun-20261016-002547 repeats the earlier
pre-test startup failure, not the monitor-ownership failure fixed by v68.
Both startup crashes occur while C2 builds its runtime stubs:
  PhaseCFG::global_code_motion -> Block_Array::grow -> libc memset.
The selected 26 jtreg tests did not run on either failed startup.

Evidence and limits:
The second report has memset destination I0=0x10b0128b8, current block
cursor I3=0x10b3fffc0, and remaining count I2=0x7ffc12700. The dumped loop
advances that cursor as it subtracts from the count. Their sum gives:
  0x7ffc12700 + (0x10b3fffc0 - 0x10b0128b8) = 0x7fffffe08
That is exactly uint32_t(1 - 64) * 8. The first crash gives the same value.
This is consistent with a capacity shrinking from 64 entries to 1 and the
unsigned difference becoming a huge zero-fill count. It does not, by itself,
prove why the capacity calculation failed, or establish a libc/GCC bug.

Patch:
- On SPARC, calculate the next capacity by bounded unsigned doubling rather
  than next_power_of_2's native CLZ helper. Other architectures retain that
  helper.
- Check overflow before each doubling and require new capacity > old capacity
  before calling Arena::Arealloc.
- Use the checked local capacity and difference for reallocation and zeroing;
  publish _blocks and _size afterwards.
- Handle an initially empty array's first allocation without treating its
  successful one-entry initialization as a growth failure.
- Include index/old/new in the capacity-guarantee diagnostic if an invariant
  is violated, rather than performing an enormous memory write.

No compiler, GC, locking or continuation option is disabled. The v68 monitor
fallback and every previous cumulative source change are retained. Full
monitor-driven unmounting remains incomplete, as documented in v68.

New diagnostics and verification:
- check-block-array-growth-host.py extracts the actual patched grow body and
  runs 402 SPARC-branch and 400 generic-branch checks with guarded mock arena
  allocations: old entries, zero tail, bounds, zero initial capacity and
  overflow rejection. Both passed on this Linux host.
- NativeClzSmoke.cpp checks runtime __builtin_clz and __builtin_clzll results
  around all nonzero power-of-two boundaries on eight concurrent native
  threads. It passed here; Solaris/SPARC execution is pending. Its results
  diagnose the helper, not the entire C2 startup path.
- run-native-clz-repro.sh builds/runs that native test with 60-second compile
  and execution limits, writes the compiler version and produces a small
  text-only evidence.zip. Override JDK25_NATIVE_CXX with the path to the C++
  compiler used for HotSpot if plain g++ is a different compiler.
- Existing capture-c2-startup.sh captures the rebuilt block.o disassembly and
  repeats VMProps startup. Set JDK25_STARTUP_REPEATS=10 for 30 total startups.
  A pass in a finite startup sample does not prove the intermittent crash is
  eliminated. The full 26-case rerun is still required.

After extracting the cumulative ZIP over ~/git/jdk25:

  cd ~/git/jdk25
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-native-clz-repro.sh &&
      JDK25_JTREG_HOME=/export/home/solaris/tools/jtreg-8.2.1/jtreg \
      JDK25_STARTUP_REPEATS=10 \
        bash tests/capture-c2-startup.sh priority-1-2-rerun-20261016-002547 &&
      JDK25_TEST_JOBS=16 bash tests/rerun-priority-crashes-v52.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

Send the native-clz and c2-startup evidence ZIPs plus the jtreg summary.
The startup runner normally finishes quickly; its hard limits still apply
individually to every launch. The jtreg batch retains its 45-minute limit.
Native verification of this source patch is pending; no startup crash or
remaining jtreg timeout is declared resolved yet.
