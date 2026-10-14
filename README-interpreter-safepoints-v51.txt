v51: SPARC interpreter safepoint bit checks

Native evidence: priority-1-2-rerun-20261014-005029, original unchanged
TestStackBangMonitorOwned.java. Its body prints TEST PASSED and STATUS:Passed,
but VM shutdown does not complete. With diagnostics passed explicitly through
jtreg, the safepoint timeout identifies Thread-1 nid 28 as the running thread.
The test source leaves that daemon spinning on volatile do_monitor_acquire
when method_entered is false. Prior pstack captures show the same worker in
interpreter-generated code. The Signal Dispatcher waiting for Threads_lock
is downstream of the stalled safepoint, not the identified running thread.

Root cause in source: JDK25 SafepointMechanism uses page-aligned good/bad
addresses for its polling page and low bit 1 in its separate polling word.
Two SPARC interpreter checks mask poll_bit() in polling_page_offset(), which
cannot identify an armed page because the low address bit is zero.

Change both checks to polling_word_offset():
- InterpreterMacroAssembler::dispatch_Lbyte_code (including loop branches).
- TemplateTable::_return (interpreter return safepoint check).

C1/C2 polling-page memory loads remain intact: those deliberately dereference
the page to trigger a fault and must continue using the page address. Existing
MacroAssembler::safepoint_poll already uses the correct polling word.
No jtreg source or timeout is changed. Compiler tiers, OSR, and continuation
fast paths retain their existing behavior.

Host validation: extracted actual changed emitter fragments compiled with
recording assembler stubs under g++ -std=c++17 -Wall -Wextra -Werror. Both
checks distinguished armed and disarmed polling words across three aligned
page addresses. Replacing word offset with the former page offset made the
same check fail. Audited SPARC sources for remaining poll-bit/page-offset
combinations. New runner shell syntax passed. No native Solaris execution
or full HotSpot compilation has been performed locally.

New smoke: InterpreterSafepointSpinSmoke keeps a daemon in a call-free volatile
spin loop while main requests five full GCs, then stops and joins it. Runner
covers -Xint and mixed mode with spin excluded and OSR disabled only for this
reproduction. Each process is bounded by GNU timeout at 30 seconds plus a
five-second kill grace. Default explicit-GC behavior is required.

Apply the cumulative ZIP at the repository root, rebuild, then run:

  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-interpreter-safepoint-repro.sh &&
      JDK25_SAFEPOINT_DIAGNOSTICS=1 bash tests/rerun-priority-1-2.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

The complete selected priority list has 25 cases. Native confirmation before
v51 is 24 cases passed across the preceding runs, with the stack-bang shutdown
timeout still unresolved. v51's expected correction needs native validation.
The ZIP also includes v50's native-confirmed JNI TLS fix and v50a's corrected
diagnostic collector.
