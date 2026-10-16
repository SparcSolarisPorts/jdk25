v74: include generated kill projections in C2 provenance capture
==============================================================
The v73 check caught a projection outside the current node arena at post-match,
position 0 of 4, in C2 Runtime new_instance. It also stopped jmod build tools,
so the runtime capture did not execute. This is earlier evidence, not a fix.

ADLC-generated DEF/KILL projections append directly to Node_List and bypass
Matcher::push_projection. v74 checks new projections immediately after Expand
returns, covering that route. It also checks before old-space reclamation.
Ownership failures now report whether the pointer is in the old node arena,
compiler arena or resource area, plus matcher/current Compile and arena pointers.
No out-of-arena object fields or virtual methods are read by this diagnostic.

This distinguishes a bad allocation at expansion from later damage or stale
storage before its evidence is erased. The checks remain SPARC-only. Existing
Block_Array overflow protection and all cumulative fixes are retained. No
projection is skipped, relocated blindly or clamped. Root cause is pending.

To complete packaging despite C2 startup failure, temporarily limit just the
build-tool JVMs to C1 using a command-local JAVA_TOOL_OPTIONS assignment. This
does not remove C2 from libjvm or change normal runtime defaults. Run the next
capture without that environment assignment so C2 is tested normally:

  if JAVA_TOOL_OPTIONS=-XX:TieredStopAtLevel=1 \
      gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    JDK25_JTREG_HOME=/export/home/solaris/tools/jtreg-8.2.1/jtreg \
      JDK25_STARTUP_REPEATS=1 bash tests/capture-c2-startup.sh \
      priority-1-2-rerun-20261016-012229
  else
    tail -80 /tmp/jdk25-build.log
  fi

The capture emits a text-only evidence.zip; three startup probes are each
bounded to 30 seconds, followed by bounded object disassembly captures. Send
that ZIP. A crash is useful evidence; a passing probe alone is not a fix.

Host validation: actual verifier-body mock test, ordering/Expand hook checks,
shell syntax, cumulative retention and archive CRC/SHA. Solaris build pending.
Native v72 already passed eight single-carrier modes (zero pin events) and all
16 continuation regressions. The suspension cases are still untested on v72
because VMProps startup failed. The v68 monitor fallback limitation remains.
