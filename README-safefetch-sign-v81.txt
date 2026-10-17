v81: signed SafeFetch32 result for the Solaris/SPARC V9 ABI
==========================================================
Native v80 results now complete instead of crashing at unreadable-memory
probes. SafeFetch negative/read-failure probes pass, including tests without
Thread::current() and at a safepoint. All three NMT modes finish with just:
  os.safefetch32_positive_vm
  os.safefetch32_positive_current_null_vm
The generic wrapper additionally reports CompressedKlass.basics_vm.
Its detailed assertion block was absent from the three pasted chunks; the
failed-test name alone does not establish whether v80's range fix was used
by the gtest library or whether another assertion is now failing.
Do not claim that compressed-class failure is fixed by this version.

Exact observed signed-result failure
  expected uint64_t(int32_t(pattern)): 18446744072296967117
  actual:                              2882382797
These are the sign-extended and zero-extended forms of the same 32-bit word.
SPARC V9 requires signed int return values to be sign-extended in the output
register. SafeFetch32's assembly used ld (zero extension). Change to ldsw
(sign extension), retaining v80's precise fault label, retl/nop and recovery
continuation. SafeFetchN stays ldx; no VM feature is disabled.
The old host model checked fault recovery and unsigned data bits but missed
this return-register ABI requirement. Its expanded check now requires ldsw
and exercises positive/negative words, the exact native failure, native-width
patterns and error returns (96 cases). It rejects the v80 zero-extending load.

Host checks
- 96 actual-source assembly control-flow/signed-result model cases passed.
- 64 compiled actual-source high-address encoding endpoint cases retained.
- Bash syntax of full-suite rerun; cumulative archive CRC/SHA-256 retention.
No SPARC execution was performed here. The real gtests remain the validation.
All earlier patches are retained; only the SafeFetch assembly changes since v80.

After extracting the cumulative ZIP, first print the missing class assertion:
  ggrep -n -B 5 -A 25 -E 'test_compressedKlass.cpp:|\[ RUN      \] CompressedKlass.basics_vm' \
    gtest-v80-results-20261017-005218-5NtN0a/work/gtest/GTestWrapper.jtr

Then rebuild and rerun all gtest wrappers:
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/rerun-gtest-v80.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
Build jobs use the user's existing defaults. Tests use 16 jobs and a
30-minute cap. Use the existing full-suite runner: no extra rerun script needed.
Please send the small text-only evidence.zip produced by the runner if a
failure remains; it retains whole result files and avoids gaps in pasted logs.
