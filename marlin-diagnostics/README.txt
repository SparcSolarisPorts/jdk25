Solaris/SPARC JDK25 Marlin / C1 OSR crash diagnostics
===================================================
This package has NO JVM source changes and does not change an installation,
compiler defaults, profiles or the previous cumulative v83 patch.

Observed in the supplied PureBench crash report (twice reproducible):
- C1 level-2 OSR compilation of sun.java2d.marlin.Renderer._endRendering,
  bytecode entry 808. Fault at compiled method +0x1300 on AWT-EventQueue-0.
- SIGSEGV/SEGV_MAPERR address 0x000004010ba1fd58.
- Nearby register O4=0x000000010ba1fd58, L6=0x0000040000000000:
  their sum is the bad address; L6 equals 1024 << 32.
- Faulting instruction is a signed word load via the computed Unsafe address.
  That identifies an invalid generated address; the origin of the misplaced
  value (OSR transfer, spills, arithmetic or another compiled producer) has
  not yet been established. Do not claim an OSR fix from this evidence alone.

Run from ~/git/jdk25 after extracting:
  bash marlin-diagnostics/run-marlin-diagnostics.sh
Default image: /usr/jdk/instances/jdk-25 (the failing installed JDK).
To use the newly built image instead:
  JDK25_IMAGE="$PWD/build/solaris-sparcv9-server-release/images/jdk" \
    bash marlin-diagnostics/run-marlin-diagnostics.sh

The script compiles a pure Java, headless BufferedImage/Graphics2D AA stroke
and fill workload: no display or PureBench jar needed. It runs six modes,
sequentially, each capped at 120 seconds:
  interpreter, C1 level 1, C1 profiled level 2, mixed, OSR-disabled control, C2.
It compares each completed raster checksum with the interpreter's result.
The OSR-disabled mode is diagnostic only; this script never installs that
flag as a workaround or alters C1/C2/OSR settings permanently.
Checksums are also written separately to avoid interleaving with compilation
output. A timeout, missing baseline or missing result never counts as PASS.
Source bytecode/local tables for the installed Renderer are saved, as are
renderer compilation records (look for '%' indicating an OSR compilation).
Core files are disabled for these subprocesses; hs_err logs are retained.
The final marlin-results-*/evidence.zip contains selected text only.
Send that ZIP. If the workload passes in every mode, that does not prove
PureBench's crash was fixed: compare the compilation records to see whether
it exercised the same OSR entry; the workload may need enlargement.
JDK25_MARLIN_ROUNDS=12 increases the default four frames without changing
geometry or timeout. The matrix is not a replacement for the original app.

Temporary per-launch isolation for the original GUI app:
  /usr/jdk/instances/jdk-25/bin/java \
    '-XX:CompileCommand=exclude,sun.java2d.marlin.Renderer::_endRendering' \
    -jar "$HOME/Downloads/PureBench(1).jar"
This interprets just the named method and keeps the rest of the VM's JITs
available; it can be slower and is not a source fix. Report whether the app
opens and can repaint normally with this flag. No setting is saved.

Host validation: Java source compiles with JDK17; interpreted and default
compiled runs produce identical CRC 001eb20d01197f9d for four frames on
Linux/x86. That host CRC is not hardcoded as the native oracle. Bash syntax
and mocked six-mode success, native-process error, checksum mismatch and
continued collection paths pass. No Solaris/SPARC execution is available here.
