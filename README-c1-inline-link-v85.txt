v85: resolve the SPARC C1 MacroAssembler::mov link failure
========================================================
v84 introduced a direct MacroAssembler::mov(Register, Register) call in
share/c1/c1_LIRGenerator.cpp but included only c1_MacroAssembler.hpp.
That provides the declaration, not the SPARC inline definition, which lives
in asm/macroAssembler.inline.hpp. The translation unit compiled but emitted
an unresolved out-of-line call. Both production and gtest libjvm link against
that same object and therefore failed with the same missing symbol.

Correction: include asm/macroAssembler.inline.hpp inside the existing SPARC
include guard. This also makes the other assembler inline definitions used
by the operation available. No generated access algorithm or flags changed.
No clean or reconfigure should be necessary; the changed source is rebuilt.

The 576 recorded-emitter cases still pass. Their original mock assembler
could not detect a missing real inline header. Added an explicit production
inline-header check so that omission is caught by the host checker.
Cumulative ZIP CRC and source hashes verified. Solaris linking and execution
remain pending; the host checker does not constitute a full native VM build.

After extracting at repository root, use the same command:
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-unsafe-alignment-repro.sh &&
      bash tests/run-marlin-osr-repro.sh &&
      bash tests/run-v59-regressions.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi
Build concurrency uses your existing configured defaults.
