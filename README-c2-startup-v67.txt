C2 startup capture v67 — diagnostics, no VM source changes

The latest 26-case batch did not execute its selected tests. The VM crashed
while jtreg was obtaining JDK properties, approximately 75 ms after startup,
in C2 runtime-stub generation (PhaseCFG::global_code_motion -> libc memset).
This is separate from the 16 continuation regression cases that passed on
v66, including compressed and uncompressed suspended-stack GC.

The crash site alone does not identify whether the cause is a corrupted
allocation/length, native compiler output, or another memory error. Reducing
test concurrency or disabling C2 would not establish a fix.

Extract this ZIP over the JDK source directory, then run:

  cd ~/git/jdk25
  bash tests/capture-c2-startup.sh priority-1-2-rerun-20261015-233450

No rebuild is needed. The earlier jtreg work directory supplies the VMProps
classes; the built JDK image is used by absolute path. JT_HOME is read from
build/solaris-sparcv9-server-release/spec.gmk, or set JDK25_JTREG_HOME.

This replays the VMProps command three times for each of three configurations:
  default: original ergonomic heap and compiler settings
  bounded: -Xms32m -Xmx256m
  nmt:     original heap with NativeMemoryTracking=detail

C2 and tiered compilation remain enabled in all configurations. The bounded
and NMT cases are diagnostic comparisons, not proposed workarounds. Each
launch has a 30-second limit plus a 5-second forced termination allowance;
nine launches usually finish quickly and have a worst-case budget of about
5.25 minutes. Disassembly capture adds up to 105 seconds. To run one repeat
per configuration instead, set JDK25_STARTUP_REPEATS=1.

Output is quiet apart from launch status and short failure tails. The runner
captures gcm.o, block.o and arena.o disassembly when GNU objdump is installed,
and creates c2-startup-results-*/evidence.zip containing text only. No cores,
JDK binaries or whole jtreg work trees are included. Core dumps are disabled
only in this runner's shell and its children. Send evidence.zip; if transfer
is unavailable, paste results.txt and the failing case's hs_err_pid*.log.

Validation here: shell syntax and a mocked runner check for failure exit
propagation, nine launches, required VMProps output and core-file exclusion.
This Linux host cannot validate SPARC native behavior. This package contains
no claimed C2 fix and does not replace the v66 cumulative VM source package.
