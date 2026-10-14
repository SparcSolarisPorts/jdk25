v53: repair the v52 interpreter/mixed continuation GC regression

Native v52 results:
- Vector alignment smoke passes in C1, mixed, C2 and the lower VIS setting.
- Basic compiled continuations and compiled suspended-stack GC pass.
- Interpreter and mixed continuations crash during G1's stack-chunk scan after
  the first yield. The chained run correctly did not start the remaining tests.

The v52 anchor change wrote saved I6/I7 into the canonical entry spill area
before copying the interpreted continuation. A bottom interpreted frame can
extend/relocate that window, leaving its live locals across the canonical
entry save area. Those writes can corrupt the locals copied into the chunk.
The new full-width fields/entry-layout change was not necessary.

v53 removes the v52 register-slot restoration and the additional entry fields,
and restores the exact v51 entry layout and fill_continuation_entry code.
It keeps the v52 vector and deferred-PC/deopt-state fixes.

Instead of writing canonical stack memory, the SPARC anchor helper follows the
existing flushed native window chain until its next FP equals entry.entry_fp.
It publishes that live physical SP with the entry's PC. A monotonically growing
window chain bounds traversal; invalid chains fail with a named guarantee.
No stack word is modified. The normal frame constructors recognize enterSpecial
and recover canonical metadata SP as FP - ContinuationEntry::size(), so stack
roots use the correct oop-map offsets despite the physical window relocation.
PC is published before the selected SP.

Host validation:
- The actual new helper body compiled with mocks and followed an unrelocated
  entry and three relocated entries, even when the canonical link slot contained
  a fake truncated pointer. A full before/after stack comparison confirmed that
  every stack word, including all live locals, remained unchanged.
- Canonical metadata recovery from the full-width FP matched every layout.
- The actual v52 frame::patch_pc and vector helper checks still pass.
- The entry PD header, shared entry header and entry generator are byte-for-byte
  identical to v51; vector source/rules are byte-for-byte identical to v52.
- Cumulative ZIP source retention, source hashes and CRC checked.
No Solaris compilation or native continuation execution occurred locally.

Apply this cumulative ZIP over v52, then rebuild and run the existing smokes:

  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-continuation-repro.sh &&
      bash tests/run-mixed-yield-repro.sh &&
      bash tests/run-vector-memory-alignment-repro.sh &&
      bash tests/rerun-priority-crashes-v52.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

Stop at any failing smoke. If continuation GC still fails, print the full
hs_err report from the newly created continuation-test-results directory.
The focused jtreg list still contains 26 unchanged cases. Its timeout and
concurrency settings are unchanged. Native confirmation remains required.
