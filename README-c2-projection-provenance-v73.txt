v73: C2 projection provenance diagnostics (not a root-cause fix)
==============================================================
Native v72 verification is now confirmed: eight plain/JVMTI single-carrier
modes passed with zero pin events and all 16 v59 regression modes passed.
The suspension batch has instead failed twice during VMProps startup, before
either selected test ran. The v69 Block_Array guard reports index=4294967295,
old=64. The native stack and previously captured GCM disassembly locate the
call in the matcher projection unmapping loop during C2 runtime-stub generation.
This rules out capacity arithmetic as the whole explanation: its input is bad.

This diagnostic package retains all cumulative fixes and adds SPARC-only
projection validation at insertion, after matching releases old node storage,
and before GCM unmaps each projection. Debug compilation logs identify compile
ID, runtime stub, list position/count, node address, index, unique-node limit,
and input/output counts. Arena ownership and null are checked before node
fields are read. No virtual node dump is attempted on a damaged object.
A bad node fails at the earlier boundary instead of allocating a huge array.
No index is clamped, node skipped, or compiler disabled. This is diagnostic;
the invalid-index root cause remains unresolved.

The startup capture now enables the projection log and includes matcher/node
native object disassembly. It still captures only text, disables cores in its
own process, caps each startup at 30 seconds, and preserves default JVM options.
Three modes and three repeats give a maximum nominal startup runtime of about
five minutes, plus bounded disassembly capture. Use one repeat for three probes.

After extracting into the JDK source tree:
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    JDK25_JTREG_HOME=/export/home/solaris/tools/jtreg-8.2.1/jtreg \
      JDK25_STARTUP_REPEATS=1 bash tests/capture-c2-startup.sh \
      priority-1-2-rerun-20261016-012229
  else
    tail -80 /tmp/jdk25-build.log
  fi
Send the resulting text-only evidence.zip. Do not rerun the long batch until
startup is understood. Diagnostics can change timing; a passing probe alone
will not establish that the original defect is fixed.

Host validation: compiled the actual verifier body with mocks for valid nodes,
null/foreign pointers and corrupt indices, including the observed UINT_MAX.
Checked that insertion/GCM validation precedes mapping, shell syntax, archive
CRC/SHA and cumulative source retention. Full SPARC build/native testing pending.
The v68 monitor-driven unmounting fallback limitation remains unchanged.
