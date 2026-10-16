v78: bounded live capture for the remaining code-cache stress crash
=================================================================
Native v77 verification: normal build, all four mounted full-GC modes, the 16
continuation regression modes returned success, and the original redefinition
jtreg case passed. The mixed-yield console excerpt for mixed mode showed a
compilation line rather than the PASS text; exit status was zero. Its full
log/PASS marker can be checked separately.

The next completed 26-case batch reported 25 passes and one failure:
compiler/codecache/stress/UnexpectedDeoptimizationAllTest.java. It failed in
its first platform-thread/non-segmented action after about 44 seconds, exit 11.
No HotSpot crash report appeared in the supplied result text/work scan. The
retained core was only 64 bytes and pstack rejected it as not an ELF core.
There is no usable fault PC/stack yet. This package does not invent a VM fix.
All v77 VM sources are unchanged; no rebuild is needed for this capture.

New runner: tests/capture-unexpected-deopt-v78.sh
- Reuses the compiled original test and WhiteBox classes, and the original
  main.0.jta argument file in the retained failed run.
- Replays that first action under GDB, preserving its WhiteBox, dontinline,
  DeoptimizeRandom and non-segmented-cache options. C2 stays enabled. The
  existing WhiteBox class root is appended to the boot path instead of a
  scratch-directory copy of the same class.
- Requests the existing fourfold timeout factor; the diagnostic debugger
  process itself is bounded to 180 seconds plus a 10-second kill grace.
- Catches SIGSEGV/SIGBUS/SIGILL/SIGABRT, records stack/register/instruction and
  signal info, then passes each signal onward. JVMs intentionally use some of
  these signals, so an isolated recorded signal is not proof of a fatal bug.
- Retains the last eight signal records in a small ring file. GDB may exit zero
  even if the JVM dies; debugger status alone is explicitly not a test pass.
- Disables cores only for its subprocess tree and packages selected text only.
- Uses --nx to avoid local debugger init scripts. Requires GDB with Python.

Run without rebuilding:
  JDK25_JTREG_HOME=/export/home/solaris/tools/jtreg-8.2.1/jtreg \
    bash tests/capture-unexpected-deopt-v78.sh \
    priority-1-2-rerun-20261016-221049

Send the new evidence.zip. If GDB is not on PATH, set JDK25_GDB to its executable.
Missing tools/classes are reported before launching the test. A debugger timeout
or clean debugger exit is not an all-pass jtreg result. After any future fix,
the original upstream test still needs to complete all four actions.

Host validation: Bash syntax, GDB helper Python syntax, command/option review,
cumulative source retention and archive CRC/SHA-256. Solaris/GDB execution is
pending; no SPARC machine or GDB runtime is available in the host workspace.
The v75 C2 spill-mask fix and v77 single-owner GC-root fix are retained.
The v68 monitor-driven unmounting fallback limitation remains unchanged.
