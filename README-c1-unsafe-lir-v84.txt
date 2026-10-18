v84: keep SPARC C1 Unsafe alignment paths inside one LIR operation
================================================================
Native evidence
The Marlin matrix from 2026-10-18 reproduces a SIGSEGV in C1 level-3
OSR compilation 249, Renderer._endRendering @335. Interpreter, C1 levels
1 and 2, mixed without OSR, and standalone C2 all pass with the SAME pixel
checksum 00078fa8f416029f. The failing mixed run undergoes several C2
uncommon traps and subsequent C1 OSR compilations before crashing.
This is a new application/compiler regression; the prior gtest and jcstress
passes do not establish that this path is correct.

Source defect addressed
The v43 C1 primitive Unsafe fallback emits alignment branches across many
ordinary LIR instructions inside one HIR block. Linear scan sees straight-line
instruction positions, not those internal paths. Interval splitting can insert
spill/reload moves between those instructions; a branch can skip the moves
needed to preserve other live values. High-register-pressure compiled/OSR code
can therefore receive stale register or spill contents. A successful small
alignment smoke does not rule this out. The native crash is consistent with
this defect, but confirmation of the causal fix requires the Solaris rerun.

Change
- One SPARC-only LIR opcode now encapsulates the complete primitive access.
- Explicit input/temp/output operands protect the address, value and scratch
  register throughout the operation. The load uses the allocator-rewritten
  result operand, rather than a duplicate uncolored copy.
- The alignment test and aligned hardware load/store remain. The byte fallback
  is emitted only for misaligned addresses. Its internal labels are generated
  AFTER register allocation; no allocator spill/reload can land inside them.
- Floating-point bit reinterpretation uses the existing unconditional spill
  conversion before a store or after a load, outside the internal branches.
- Reference, volatile, atomic and raw OSR-buffer accesses retain their existing
  paths. This changes plain primitive Unsafe access generation, not OSR itself.
- No compiler, tier, OSR, intrinsic, continuation path or upstream test disabled.

Validation and limits
Compiled the actual new C++ operation against a recording assembler with
-Wall -Wextra -Werror and undefined-behavior sanitizer. Executed 576 emitted
load/store cases: six primitive types, eight address alignments, six bit patterns,
unchanged surrounding memory and unrelated registers, signed short/int results,
and allocator-rewritten output operands. Checked visitor input/temp/output
contracts and absence of the previous multi-instruction alignment branches.
Shell syntax checked. Native Solaris/SPARC compilation and execution are pending;
the recording assembler is not a full VM build or a SPARC machine-code test.

Run after extracting the cumulative ZIP at repository root
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-unsafe-alignment-repro.sh &&
      bash tests/run-marlin-osr-repro.sh &&
      bash tests/run-v59-regressions.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

Build jobs use your existing configuration. The Marlin modes run sequentially
with a 120-second cap each, and compare their pixel checksums to the interpreter
in that SAME run. It includes C1 full profiling (TieredStopAtLevel=3), the mode
missing from the first matrix. The OSR-disabled mode is a diagnostic control,
not a permanent launcher setting. The script defaults to the newly built image;
JDK25_IMAGE can select another image explicitly. It creates a small text-only
evidence.zip in the printed marlin-results directory. Send that evidence if
mixed still fails; also retry the original PureBench workload after a pass.
The v83 native result is recorded: all 24 applicable gtest wrappers passed,
with 6 cases inapplicable on that run. All earlier cumulative fixes remain.
